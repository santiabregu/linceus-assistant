# Flujo completo del sistema Linceus Assistant

## Flujo completo: mensaje → respuesta

### FASE 1: NLU Pipeline (config.yml)

```
Mensaje usuario
      │
      ▼
WhitespaceTokenizer          → divide en tokens
RegexFeaturizer              → detecta patrones (ej: "cuántas" → conteo_signal)
LexicalSyntacticFeaturizer   → features sintácticas (mayúscula? número? prefijo?)
CountVectorsFeaturizer word  → bag-of-ngrams por palabras (1-2 ngrams)
CountVectorsFeaturizer char  → bag-of-ngrams por caracteres (1-4 ngrams, resistente a typos)
DIETClassifier               → clasifica intent + extrae entidades simultáneamente
EntitySynonymMapper          → normaliza sinónimos ("IS" → "GII-IS")
FallbackClassifier           → si confianza < 0.7 → intent = nlu_fallback
```

**Resultado:** `intent: consulta_asignatura_especifica` + `entity: nombre_asignatura = "Redes"`

---

### FASE 2: Política de diálogo → selección de acción

| Policy | Qué hace |
|---|---|
| **RulePolicy** | Reglas deterministas 1-a-1. "Si intent=X → action=Y". Maneja la mayoría de asignaturas. |
| **MemoizationPolicy** | Si el flujo coincide exactamente con una story de training, lo replica. |
| **TEDPolicy** | Transformer con historial de 5 turnos para flujos multi-turno complejos. |
| **UnexpecTEDIntentPolicy** | Detecta intents "raros" dado el contexto actual. |

La `RulePolicy` detecta la regla:
```yaml
intent: consulta_asignatura_especifica → action: action_consulta_especifica
```
Y hace HTTP POST al **action server** en `:5055`.

---

### FASE 3: `ActionConsultaEspecifica.run()` — actions/asignaturas/actions.py

```
1. extraer texto + historial reciente (últimos 2 turnos)
2. comprobar_titulacion()
      ├─ lee slot "contexto_titulacion"
      ├─ si vacío → llama Gemini (temp=0.0) para detectarla desde el mensaje
      └─ si no encuentra ninguna → utter_pedir_titulacion + ABORT
3. extraer_nombre_asignatura()    → busca entity "nombre_asignatura" en el mensaje NLU
4. _es_seguimiento()              → ¿es pregunta de continuación sin subject? ("¿y es obligatoria?")
5. _expandir_alias("Redes")
      ├─ busca en dict ALIAS_ASIGNATURAS
      ├─ si parece acrónimo → _buscar_por_acronimo_en_bd()
      └─ si no → devuelve el original

   ─── Si NO hubo entity NLU ───────────────────────────────────────────────────
6a. Scanear dict ALIAS_ASIGNATURAS sobre texto completo (regex word boundary)
6b. _resolver_nombre_desde_texto(pregunta, titulacion)   ← FUZZY #1 (rapidfuzz)
      ├─ SELECT nombre FROM asignaturas WHERE titulacion = 'GII-IS'
      ├─ Estrategia 1: pregunta completa vs todos los nombres (partial_ratio ≥ 85)
      └─ Estrategia 2: ventanas de 2–6 palabras contiguas (partial_ratio ≥ 75)
   ─────────────────────────────────────────────────────────────────────────────
```

---

### FASE 4: `generar_sql_especifica()` — actions/asignaturas/text_to_sql.py

```
1. _clasificar_necesita_rag(pregunta)
      ├─ _necesita_rag_heuristica() → ¿contiene palabras como "profesor", "examen", "temario"?
      └─ si no → llama Gemini (temp=0.0, 5 tokens) → true/false

2. Si necesita_rag = FALSE (caso "créditos"):
      ├─ construye prompt con schema SQL + pregunta + entidad
      ├─ llama Gemini (temp=0.0, 100 tokens) → devuelve JSON: {sql, parametros, atributo_solicitado}
      ├─ validar_sql():
      │     ├─ rechaza INSERT/UPDATE/DELETE/DROP/UNION SELECT/OR 1=1...
      │     ├─ solo permite tablas: asignaturas, titulaciones
      │     └─ solo permite columnas de la whitelist
      └─ _inyectar_filtro_titulacion() → añade "AND titulacion_id = (SELECT id ... WHERE codigo='GII-IS')"

3. Si necesita_rag = TRUE (caso "¿quién imparte?"):
      └─ → ver FASE RAG más abajo
```

---

### FASE 5: `ejecutar_query()` → PostgreSQL/Supabase

```
psycopg2.execute(sql, ["%redes%"])
      │
      ▼
filas = [{codigo, nombre, curso, creditos, duracion, tipologia}]
      │
      ├─ 0 resultados → retry con query flexible (nombre_normalizado ILIKE %s OR codigo ILIKE %s)
      │
      ├─ 0 resultados aún → _resolver_nombre_desde_texto(nombre, titulacion)   ← FUZZY #2
      │       ├─ mismas estrategias (partial_ratio ≥ 85 / ventanas ≥ 75)
      │       └─ si encuentra → nueva query ILIKE con el nombre corregido
      │
      ├─ 0 resultados aún → mensaje "No encontré asignatura X en GII-IS"
      │
      ├─ 0 resultados (sin nombre concreto) → SELECT ALL titulación + Gemini responde
      │
      └─ varios resultados → reordenar por token_set_ratio   ← FUZZY #3
              → toma el primero (mejor match semántico con la pregunta)
```

**Resumen de los 3 usos de rapidfuzz:**

| # | Cuándo | Qué compara | Score mínimo |
|---|---|---|---|
| **Fuzzy #1** | No hubo entity NLU | Pregunta completa / ventanas de palabras vs todos los nombres de la titulación | 85 / 75 |
| **Fuzzy #2** | Query SQL sin resultados | Nombre extraído vs todos los nombres de la titulación | 85 / 75 |
| **Fuzzy #3** | Query con múltiples filas | Nombre de cada resultado vs pregunta completa (`token_set_ratio`) | ordena, no filtra |

---

### FASE 5b: RAG (solo si `necesita_rag = True`)

```
buscar_en_plan_docente(pregunta, codigo="2050001") → rag/buscar.py
      │
      ├─ generar_embedding(pregunta) → Gemini embedding-001 (vector 2000 dims)
      ├─ _buscar_vectorial() → función pgvector en PostgreSQL (cosine similarity)
      │     └─ devuelve chunks del plan docente más similares semánticamente
      └─ si falla embedding → _buscar_por_keywords() (ILIKE con palabras clave)

_generar_respuesta_rag(pregunta, chunks, nombre)
      └─ Gemini (temp=0.3, 300 tokens) con los chunks como contexto
```

---

### FASE 6: `generar_respuesta_natural()` → Gemini → texto final

```
formatear_datos_para_prompt({codigo, nombre, creditos, ...})
      └─ "- Nombre: Redes de Computadores\n- Créditos: 6.0 ECTS\n..."

prompt a Gemini (temp=0.3, 200 tokens):
"Eres Linceus, asistente universitario. Responde SOLO con los datos dados..."

Respuesta: "Redes de Computadores tiene 6 créditos ECTS. Es obligatoria de 3º, segundo cuatrimestre."
```

---

### FASE 7: Dispatch + actualizar slots

```python
dispatcher.utter_message(text=respuesta, json_message={"data": asignatura})
return [
    SlotSet("ultimo_codigo_consultado", "2050001"),
    SlotSet("ultimo_nombre_asignatura", "Redes de Computadores")
]
```

Los slots permiten preguntas de seguimiento: "¿Es obligatoria?" usa `ultimo_nombre_asignatura` sin que el usuario repita el nombre.

---

## Las 4 Actions de asignaturas

| Action | Intent | Diferencia clave |
|---|---|---|
| `action_consulta_especifica` | `consulta_asignatura_especifica` | SELECT 1 fila, puede usar RAG |
| `action_consulta_listado` | `consulta_asignaturas_listado` | SELECT N filas + paginación (max 8, guarda resto en slot) |
| `action_consulta_conteo` | `consulta_asignaturas_conteo` | `SELECT COUNT(*)`, redirige a RAG si detecta palabras de plan docente |
| `action_mostrar_todas_asignaturas` | `pedir_mas_resultados` | Lee el slot `ultimos_resultados_asignaturas` y muestra todo |

---

## Actions de contexto

| Action | Intent | Qué hace |
|---|---|---|
| `action_cambiar_contexto` | `cambiar_contexto_academico` | Normaliza titulación con dict + rapidfuzz, actualiza slot `contexto_titulacion` |
| `action_consultar_contexto` | `consultar_contexto_academico` | Lee slots y muestra el contexto actual |
| `action_consulta_titulaciones` | `consulta_titulaciones` | JOIN titulaciones+centros+conteo de asignaturas |

---

## Cuántas veces llama a Gemini por pregunta (peor caso)

| Llamada | Función | Tokens aprox. |
|---|---|---|
| 1 | `_detectar_titulacion_con_llm()` — si slot vacío | 20 |
| 2 | `_clasificar_necesita_rag()` — si heurística no fue suficiente | 5 |
| 3 | `generar_sql_*()` — generación SQL | 100 |
| 4 | `generar_respuesta_natural()` — respuesta final | 200 |

**Hasta 4 llamadas a la API por una sola pregunta.**

---

## Diagrama general completo

```
User message ("¿Cuántos créditos tiene Redes?")
         │
         ▼
[Rasa NLU Pipeline]
  WhitespaceTokenizer → RegexFeaturizer → LexicalSyntacticFeaturizer
  → CountVectorsFeaturizer(word) → CountVectorsFeaturizer(char)
  → DIETClassifier → EntitySynonymMapper → FallbackClassifier
         │
         │  intent: consulta_asignatura_especifica (0.95)
         │  entity: nombre_asignatura = "Redes"
         ▼
[Dialogue Policies] RulePolicy → action_consulta_especifica
         │
         │  HTTP POST → action server :5055
         ▼
[ActionConsultaEspecifica.run()]
  1. Extract text + conversation history
  2. comprobar_titulacion() → slot "GII-IS" found
  3. extraer_nombre_asignatura() → "Redes"
  4. _expandir_alias("Redes") → "Redes" (no alias match)
         │
         ▼
[text_to_sql.generar_sql_especifica()]
  1. _clasificar_necesita_rag() → Gemini API call → false
  2. Build SQL prompt
  3. Gemini API call → JSON con SQL + parametros
  4. validar_sql() → security check passes
  5. _inyectar_filtro_titulacion() → añade subquery titulacion_id
         │
         ▼
[ejecutar_query()]
  psycopg2 → PostgreSQL/Supabase
  → rows: [{codigo, nombre, curso, creditos, duracion, tipologia}]
         │
         │  (RAG branch skipped — necesita_rag=False)
         ▼
[generar_respuesta_natural()]
  formatear_datos_para_prompt() → texto legible
  Gemini API call (temperature=0.3) → respuesta en lenguaje natural
         │
         ▼
[dispatcher.utter_message()]
  text: "Redes de Computadores tiene 6 créditos ECTS..."
  json_message: {"data": {codigo, nombre, ...}}
  + SlotSet("ultimo_codigo_consultado", "2050001")
  + SlotSet("ultimo_nombre_asignatura", "Redes de Computadores")
         │
         ▼
  Response enviada al frontend widget
```

---

## Estructura de ficheros clave

```
linceus-assistant/
├── config.yml                  # NLU pipeline + Dialogue policies
├── domain.yml                  # Intents, entities, slots, responses, actions
├── endpoints.yml               # Action server URL (port 5055, 5-min timeout)
│
├── data/
│   ├── nlu/
│   │   ├── general.yml         # NLU: greet, goodbye, affirm, out_of_scope...
│   │   ├── asignaturas.yml     # NLU: 3 intents de asignaturas + pedir_mas_resultados
│   │   └── contexto.yml        # NLU: cambiar_contexto, consultar_contexto
│   ├── stories.yml             # Flujos multi-turno para TEDPolicy
│   └── rules.yml               # Reglas deterministas para RulePolicy
│
├── actions/
│   ├── actions.py              # Re-exporta todas las action classes
│   ├── asignaturas/
│   │   ├── actions.py          # 4 Action classes (Especifica, Listado, Conteo, MostrarTodas)
│   │   └── text_to_sql.py      # SQL via Gemini + validación + ejecución
│   ├── contexto/
│   │   └── actions.py          # ActionCambiarContexto, ActionConsultarContexto, ActionConsultaTitulaciones
│   └── shared/
│       ├── config.py           # BotConfig: defaults, slot helpers, name mappings
│       ├── db.py               # DatabaseConnection (psycopg2 → PostgreSQL)
│       ├── gemini_client.py    # llamar_gemini() → Google Gemini API (gemma-3-27b-it)
│       └── ollama_client.py    # llamar_ollama() → Ollama local (llama3.2:3b)
│
└── rag/
    ├── buscar.py               # buscar_en_plan_docente() — vectorial + keyword fallback
    ├── embeddings.py           # generar_embedding() → gemini-embedding-001 (2000 dims)
    ├── chunking.py             # PDF → chunks
    ├── extraer_pdf.py          # Extracción de texto de PDFs
    ├── db_vectores.py          # Almacenamiento/recuperación de vectores con pgvector
    └── pipeline.py             # Pipeline de ingestión offline
```
