# Plan de Implementación - LinceUS Assistant

## Estado Actual del Proyecto

### Funcional
- Conexión a Supabase (PostgreSQL + pgvector) via `actions/db.py`
- Cliente Ollama HTTP (`actions/ollama_client.py`) - llama3.2:3b, respuestas en 2-4s
- Gestión de contexto académico (`actions/contexto.py`) - cambio de titulación/centro
- Configuración centralizada (`actions/config.py`)
- Training data NLU (~295 ejemplos entre asignaturas, contexto y general)
- Frontend demo básico (widget HTML/JS)
- Búsqueda fuzzy con rapidfuzz y caché en memoria

### Roto / Incompleto
- **6-7 funciones críticas sin implementar en `asignaturas.py`** - el action server crashea
- No hay modelo Rasa entrenado (`models/` vacío)
- No hay tests end-to-end
- 0% de RAG implementado
- 0% de épicas de Profesores, Horarios, Trámites

---

## Arquitectura Recomendada

```
┌─────────────────────────────────────────────────────────┐
│                     FRONTEND (React)                     │
│              Widget conversacional embebido               │
└──────────────────────┬──────────────────────────────────┘
                       │ REST API / WebSocket
┌──────────────────────▼──────────────────────────────────┐
│                   RASA SERVER                             │
│  ┌─────────────────────────────────────────────────┐     │
│  │ Pipeline NLU:                                    │     │
│  │  WhitespaceTokenizer → RegexFeaturizer →         │     │
│  │  CountVectors → DIETClassifier(150) →            │     │
│  │  FallbackClassifier(0.6)                         │     │
│  ├─────────────────────────────────────────────────┤     │
│  │ Políticas de Diálogo:                            │     │
│  │  RulePolicy → MemoizationPolicy → TEDPolicy      │     │
│  └─────────────────────────────────────────────────┘     │
└──────────────────────┬──────────────────────────────────┘
                       │ Intent + Entities + Slots
┌──────────────────────▼──────────────────────────────────┐
│              RASA ACTION SERVER (Python)                  │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Asignaturas  │  │  Profesores  │  │   Horarios   │   │
│  │   Action     │  │   Action     │  │   Action     │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                 │                 │            │
│  ┌──────▼─────────────────▼─────────────────▼────────┐   │
│  │          CAPA DE ORQUESTACIÓN (LLM)               │   │
│  │  1. Clasificar consulta (específica/general)      │   │
│  │  2. Extraer filtros con heurísticas + LLM         │   │
│  │  3. Generar respuesta natural con Ollama          │   │
│  └──────┬────────────────────────────────┬───────────┘   │
│         │                                │               │
│  ┌──────▼──────────┐          ┌──────────▼───────────┐   │
│  │  Supabase DB    │          │  Ollama (llama3.2)   │   │
│  │  PostgreSQL +   │          │  NLU + Generación    │   │
│  │  pgvector       │          │  + RAG synthesis     │   │
│  └─────────────────┘          └──────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

### División de Responsabilidades

| Componente | Responsabilidad |
|---|---|
| **Rasa DIET** | Clasificación de intenciones + extracción de entidades básicas |
| **Rasa Policies** | Gestión de diálogo multi-turn, reglas, contexto de slots |
| **Ollama llama3.2:3b** | Clasificación de consultas, extracción de filtros, generación de respuestas naturales |
| **Ollama llama3:latest** | RAG synthesis (planes docentes), razonamiento complejo |
| **Supabase PostgreSQL** | Datos estructurados (asignaturas, profesores, horarios, trámites) |
| **Supabase pgvector** | Embeddings de planes docentes y trámites (búsqueda semántica) |
| **Custom Actions** | Orquestación: recibir intent → consultar DB/RAG → formatear con LLM |

### Pipeline de Consulta Ejemplo

**Pregunta:** *"¿Qué asignaturas optativas de 6 créditos hay en cuarto?"*

```
1. Usuario envía mensaje
2. Rasa DIET → intent: consultar_asignatura_db
                entities: {filtro_tipologia: "OPTATIVA", filtro_creditos: 6, filtro_curso: 4}
3. ActionConsultarAsignaturaDB se activa
4. Si DIET no extrajo todas las entidades:
   → Ollama analiza la consulta y extrae filtros faltantes
5. Consulta SQL parametrizada con filtros
6. Ollama genera respuesta natural con los resultados
7. Rasa envía respuesta al usuario
```

---

## Fases de Implementación

---

### FASE 1: Hacer funcionar el sistema base (Épica Asignaturas)
> **Prioridad**: CRÍTICA | **Estimación**: Sprint actual

#### 1.1 Implementar funciones faltantes en `asignaturas.py`

**Funciones a implementar:**

```python
# 1. normalizar_texto(texto: str) -> str
#    Lowercase, quitar acentos, quitar caracteres especiales
#    Ej: "Ingeniería del Software" → "ingenieria del software"

# 2. analizar_consulta_unificado(pregunta: str, entities: dict) -> dict
#    Clasifica si la consulta es "especifica" (una asignatura) o "general" (listado)
#    Usa analizar_consulta_con_llm() como base + entidades de Rasa

# 3. extraer_filtros_heuristicas(pregunta: str) -> dict
#    Regex + keywords para extraer: curso, tipologia, creditos, duracion
#    Ej: "optativas de cuarto" → {filtro_tipologia: "OPTATIVA", filtro_curso: 4}

# 4. respuesta_template(asignatura: dict, atributo: str, pregunta: str) -> str
#    Usa Ollama para generar respuesta natural sobre UNA asignatura
#    Ej: "Fundamentos de Programación tiene 12 créditos y es de primer curso"

# 5. respuesta_template_count(count: int, filtros: dict) -> str
#    Formatea respuesta de conteo
#    Ej: "Hay 15 asignaturas optativas en cuarto curso"

# 6. respuesta_template_lista(asignaturas: list, filtros: dict, max: int) -> str
#    Formatea lista de asignaturas (muestra N primeras, indica si hay más)
```

#### 1.2 Implementar `ActionMostrarTodasAsignaturas`
- Declarada en `domain.yml` pero no implementada
- Debe mostrar los resultados restantes de `ultimos_resultados_asignaturas`

#### 1.3 Entrenar modelo Rasa
```bash
rasa train
```

#### 1.4 Test end-to-end
```bash
# Terminal 1: Action server
rasa run actions

# Terminal 2: Rasa shell
rasa shell

# Probar consultas:
# - "¿Qué es Fundamentos de Programación?"
# - "¿Cuántos créditos tiene IS2?"
# - "Dame las optativas de cuarto"
# - "¿Qué asignaturas hay en primer curso?"
```

#### Entregable Fase 1
- Sistema funcional de consultas de asignaturas
- Búsqueda por nombre (fuzzy), código, filtros combinados
- Respuestas naturales generadas por Ollama
- Contexto académico persistente

---

### FASE 2: Épica Profesores
> **Prioridad**: ALTA | **Dependencia**: Fase 1

#### 2.1 Training data NLU
- Crear `data/nlu/profesores.yml` con ~100 ejemplos
- Intenciones: `consultar_profesor`, `consultar_tutorias`
- Entidades: `nombre_profesor`, `nombre_departamento`

#### 2.2 Actualizar `domain.yml`
- Nuevos intents, entities, slots, actions
- Responses de fallback para profesores

#### 2.3 Implementar `actions/profesores.py`
```python
# ActionConsultarProfesor
#   - Buscar profesor por nombre (fuzzy match)
#   - Mostrar: despacho, email, departamento, asignaturas que imparte

# ActionConsultarTutorias
#   - Buscar tutorías del profesor
#   - Mostrar: horario, ubicación (despacho + edificio + planta)
```

#### 2.4 Actualizar stories y rules
- Flujos de diálogo para consultas de profesores
- Integración con contexto académico (profesores del departamento)

#### Entregable Fase 2
- Búsqueda de profesores por nombre/departamento
- Consulta de tutorías y despachos
- Integración con contexto de titulación

---

### FASE 3: Épica Horarios
> **Prioridad**: MEDIA | **Dependencia**: Fase 1 + 2

#### 3.1 Training data NLU
- Crear `data/nlu/horarios.yml` con ~80 ejemplos
- Intenciones: `consultar_horario_asignatura`, `consultar_disponibilidad_aula`
- Entidades: `dia_semana`, `hora`, `nombre_aula`

#### 3.2 Implementar `actions/horarios.py`
```python
# ActionConsultarHorario
#   - Buscar horarios de una asignatura/grupo
#   - Mostrar: día, hora inicio/fin, aula, profesor
#   - Formato tabla legible

# ActionConsultarAula
#   - Buscar disponibilidad de un aula
#   - Mostrar: slots libres/ocupados
```

#### 3.3 Lógica de cruce de datos
- Horario necesita JOIN de: grupos_clase + aulas + profesores + asignaturas
- Implementar consultas SQL optimizadas con JOINs

#### Entregable Fase 3
- Consulta de horarios por asignatura/grupo
- Disponibilidad de aulas
- Formato claro y legible

---

### FASE 4: RAG - Planes Docentes
> **Prioridad**: ALTA | **Dependencia**: Fase 1

#### 4.1 Pipeline de ingestión de documentos
```python
# scripts/ingest_planes_docentes.py
# 1. Descargar PDFs de planes docentes (o leer locales)
# 2. Extraer texto (PyPDF2 / pdfplumber)
# 3. Chunking inteligente por secciones:
#    - Evaluación, Contenidos, Metodología, Bibliografía, Competencias
# 4. Generar embeddings (sentence-transformers local)
#    - Modelo recomendado: paraphrase-multilingual-MiniLM-L12-v2 (768 dims)
#    - Alternativa: multilingual-e5-base (mejor para español)
# 5. Insertar en planes_docentes_chunks con pgvector
```

#### 4.2 Estrategia de Embeddings
- **Modelo**: `paraphrase-multilingual-MiniLM-L12-v2` (local, gratuito, 768 dims)
- **Chunk size**: 500-800 tokens con overlap de 100
- **Secciones**: Detectar automáticamente secciones del plan docente
- **Búsqueda**: Híbrida (semántica pgvector + keyword tsvector)

#### 4.3 Implementar `actions/rag.py`
```python
# buscar_en_planes_docentes(query: str, asignatura_id: str) -> list[dict]
#   1. Generar embedding de la query
#   2. Buscar top-5 chunks más similares (cosine similarity)
#   3. Filtrar por asignatura si se especifica
#   4. Devolver chunks con metadata (sección, página, score)

# generar_respuesta_rag(query: str, chunks: list, pregunta_original: str) -> str
#   1. Construir prompt con contexto de los chunks
#   2. Usar llama3:latest (más potente) para síntesis
#   3. Incluir citación: "[Fuente: Plan docente de X, sección Evaluación]"
#   4. Si no hay info relevante: "No encontré información sobre eso en el plan docente"
```

#### 4.4 Training data y domain
- Intent: `consultar_plan_docente`
- Ejemplos: "¿Cómo se evalúa IS1?", "¿Qué bibliografía tiene ADDA?"
- Slot: `seccion_plan` (evaluación, contenidos, bibliografía, etc.)

#### 4.5 Prevención de alucinaciones
- Responder SOLO con información de los chunks recuperados
- Si similarity score < 0.5, indicar que no se encontró información
- Siempre citar fuente (asignatura + sección + curso académico)
- Prompt system: "Responde ÚNICAMENTE con la información proporcionada"

#### Entregable Fase 4
- Ingestión automática de planes docentes
- Búsqueda semántica funcional
- Respuestas con citación de fuentes
- 0% alucinaciones

---

### FASE 5: RAG - Trámites Administrativos
> **Prioridad**: MEDIA | **Dependencia**: Fase 4

#### 5.1 Ingestión de documentación de trámites
- Scraping/manual de información oficial US
- Chunking por procedimiento: matrícula, Erasmus, TFG, becas, etc.
- Embeddings con mismo modelo de Fase 4

#### 5.2 Implementar flujo de trámites
```python
# ActionConsultarTramite
#   1. Búsqueda semántica en tramites_chunks
#   2. Complementar con datos estructurados de tabla tramites
#   3. Mostrar: pasos, requisitos, documentos necesarios, plazos, URL oficial
```

#### 5.3 Training data
- Intent: `consultar_tramite`
- Ejemplos: "¿Cómo me matriculo?", "¿Qué necesito para Erasmus?"
- Entidades: `nombre_tramite`, `categoria_tramite`

#### Entregable Fase 5
- Guía paso a paso de procedimientos administrativos
- Links a documentación oficial
- Información de plazos y requisitos

---

### FASE 6: Mejoras de Calidad y Producción
> **Prioridad**: MEDIA | **Dependencia**: Fases 1-5

#### 6.1 Testing
- Tests unitarios para cada módulo de actions/
- Tests de integración (Rasa + Actions + DB)
- Tests de regresión NLU (precisión > 90%)
- Tests de seguridad: inyección SQL, prompt injection
- Tests de rendimiento: < 2s DB, < 5s RAG

#### 6.2 Frontend React
- Migrar de widget HTML a React
- Componentes: ChatWindow, MessageBubble, QuickReplies, TypingIndicator
- Responsive design
- Historial de conversación

#### 6.3 Performance
- Cache Redis/en-memoria para consultas frecuentes
- Precarga de modelo Ollama al iniciar
- Connection pooling para Supabase
- Procesamiento asíncrono para RAG

#### 6.4 Seguridad
- Consultas SQL parametrizadas (ya se usa en parte)
- Validación de input en todas las acciones
- Rate limiting
- Sanitización de prompts (anti prompt injection)

#### 6.5 Despliegue
- Docker Compose (Rasa + Action Server + Ollama)
- Variables de entorno para producción
- Logs estructurados
- Monitorización básica

---

## Resumen de Prioridades

| Fase | Nombre | Estado | Prioridad | Bloqueado por |
|------|--------|--------|-----------|---------------|
| **1** | Asignaturas (completar) | 60% hecho | CRÍTICA | Nada |
| **2** | Profesores | 0% | ALTA | Fase 1 |
| **3** | Horarios | 0% | MEDIA | Fase 1+2 |
| **4** | RAG Planes Docentes | 0% | ALTA | Fase 1 |
| **5** | RAG Trámites | 0% | MEDIA | Fase 4 |
| **6** | Calidad y Producción | 0% | MEDIA | Fases 1-5 |

## Próximo Paso Inmediato

**Implementar las funciones faltantes en `actions/asignaturas.py`** para desbloquear todo el sistema. Sin esto, el action server no arranca y nada funciona.

---

## Decisiones Técnicas Clave

### Rasa vs LLM: Enfoque Híbrido
- **Rasa** maneja: clasificación de intenciones, gestión de diálogo, slots, reglas
- **Ollama** maneja: comprensión profunda, extracción de filtros complejos, generación de respuestas naturales, RAG synthesis
- **Razón**: Rasa es determinista y rápido para flujos conocidos. Ollama aporta flexibilidad para variaciones lingüísticas

### Modelo por tarea
- **llama3.2:3b**: Consultas rápidas (clasificación, filtros, respuestas cortas) - 2-4s
- **llama3:latest**: RAG synthesis, razonamiento complejo - más lento pero más preciso

### Embeddings
- **Modelo**: `paraphrase-multilingual-MiniLM-L12-v2` (sentence-transformers)
- **Dimensiones**: 768 (coincide con schema pgvector actual)
- **Razón**: Local, gratuito, buen rendimiento en español, tamaño razonable

### Búsqueda
- **Asignaturas/Profesores**: Fuzzy search (rapidfuzz) + SQL parametrizado
- **Planes docentes/Trámites**: Búsqueda semántica (pgvector cosine similarity)
- **Híbrido**: Keyword (tsvector) + semántico para mejor recall
