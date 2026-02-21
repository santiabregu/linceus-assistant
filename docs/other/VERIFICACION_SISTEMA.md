# ✅ Verificación de Consistencia - Sistema Text-to-SQL

## Estado: CORREGIDO ✅

Todos los archivos están ahora sincronizados correctamente.

---

## 📋 Checklist de Consistencia

### ✅ domain.yml

**Intents declarados:**
- ✅ `greet`, `goodbye`, `affirm`, `deny`, `mood_great`, `mood_unhappy`, `bot_challenge`, `pedir_ayuda`
- ✅ `cambiar_contexto_academico`, `consultar_contexto_academico`
- ✅ `consultar_asignatura` (legacy)
- ✅ `consultar_asignatura_db` ⭐ **NUEVO**
- ✅ `pregunta_seguimiento`
- ✅ `consultar_asignaturas_filtradas`
- ✅ `pedir_mas_resultados`

**Actions declaradas:**
- ✅ `action_llm_preprocess`
- ✅ `action_test_supabase`
- ✅ `action_cambiar_contexto`, `action_consultar_contexto`
- ✅ `action_consultar_asignatura` (legacy)
- ✅ `action_consultar_asignatura_db` ⭐ **NUEVO**
- ✅ `action_pregunta_seguimiento`
- ✅ `action_consultar_asignaturas_filtradas`
- ✅ `action_mostrar_todas` (legacy)
- ✅ `action_mostrar_todas_asignaturas` ⭐ **NUEVO**

**Slots críticos:**
- ✅ `contexto_centro` (default: "ETSII")
- ✅ `contexto_titulacion`
- ✅ `contexto_dominio`
- ✅ `ultimo_codigo_consultado`
- ✅ `ultimo_nombre_asignatura`
- ✅ `ultimos_resultados_asignaturas` ⭐ **NUEVO**

**Responses:**
- ✅ `utter_greet`, `utter_goodbye`, `utter_iamabot`, `utter_happy`, `utter_cheer_up`, `utter_did_that_help`, `utter_ayuda`
- ✅ `utter_pedir_codigo`, `utter_no_contexto`, `utter_consultar_asignatura`

---

### ✅ data/rules.yml

**Reglas configuradas:**

1. ✅ **Generales:**
   - Saludar (`greet` → `utter_greet`)
   - Despedirse (`goodbye` → `utter_goodbye`)
   - Bot challenge (`bot_challenge` → `utter_iamabot`)
   - Ayuda (`pedir_ayuda` → `utter_ayuda`)

2. ✅ **Contexto académico:**
   - Cambiar contexto (`cambiar_contexto_academico` → `action_cambiar_contexto`)
   - Consultar contexto (`consultar_contexto_academico` → `action_consultar_contexto`)

3. ✅ **Asignaturas:**
   - Legacy: `consultar_asignatura` → `action_consultar_asignatura`
   - **⭐ NUEVO**: `consultar_asignatura_db` → `action_consultar_asignatura_db`
   - Seguimiento: `pregunta_seguimiento` → `action_pregunta_seguimiento`
   - Filtradas: `consultar_asignaturas_filtradas` → `action_consultar_asignaturas_filtradas`
   - Más resultados: `pedir_mas_resultados` → `action_mostrar_todas_asignaturas`

---

### ✅ data/stories.yml

**Stories configuradas:**

1. ✅ **Generales:**
   - Usuario contento
   - Usuario triste (se anima / sigue triste)

2. ✅ **Asignaturas:**
   - ⭐ **NUEVO**: Consulta específica text-to-sql
   - ⭐ **NUEVO**: Consulta general asignaturas
   - ⭐ **NUEVO**: Consulta con seguimiento
   - ⭐ **NUEVO**: Mostrar todas las asignaturas
   - Legacy: Consultar asignatura legacy

---

### ✅ data/nlu/asignaturas.yml

**Intents con ejemplos de entrenamiento:**

1. ✅ `consultar_asignatura` (legacy) - 187 ejemplos
2. ✅ `pregunta_seguimiento` - 35 ejemplos
3. ✅ `consultar_asignaturas_filtradas` - 69 ejemplos
4. ✅ **⭐ NUEVO** `consultar_asignatura_db` - 50+ ejemplos
   - Consultas específicas: "cuántos créditos tiene Redes", "qué es IS2"
   - Consultas generales: "asignaturas de primero", "cuántas optativas"
5. ✅ `pedir_mas_resultados` - 16 ejemplos

**Regex patterns:**
- ✅ `codigo_asignatura`: `\b20\d{5}\b`
- ✅ `filtro_creditos`: `\b(6|12|4\.5|9)\b`

---

## 🔄 Flujos de Trabajo

### Flujo 1: Consulta Específica (Text-to-SQL)

```
Usuario: "cuántos créditos tiene Redes"
  ↓
Intent: consultar_asignatura_db
  ↓
Rule: consultar_asignatura_db → action_consultar_asignatura_db
  ↓
Action:
  1. Clasifica como "específica"
  2. Extrae: nombre="Redes", atributo="creditos"
  3. Busca con fuzzy: "Redes de Computadores"
  4. Genera respuesta natural con LLM
  ↓
Respuesta: "Redes de Computadores tiene 6 créditos ECTS"
```

### Flujo 2: Consulta General (Text-to-SQL)

```
Usuario: "asignaturas de primero"
  ↓
Intent: consultar_asignatura_db
  ↓
Rule: consultar_asignatura_db → action_consultar_asignatura_db
  ↓
Action:
  1. Clasifica como "general"
  2. Genera SQL: SELECT ... WHERE curso=1 AND activa=true
  3. Ejecuta query
  4. Formatea con LLM (respuesta natural)
  ↓
Respuesta: "Aquí tienes las asignaturas de primer curso: 1. Cálculo..."
```

### Flujo 3: Mostrar Todos los Resultados

```
Usuario: "asignaturas de primero"
  ↓
Sistema: [Muestra primeros 5] "Hay 15 más. ¿Quieres verlas todas?"
  ↓
Usuario: "sí" / "todas" / "ver todas"
  ↓
Intent: pedir_mas_resultados
  ↓
Rule: pedir_mas_resultados → action_mostrar_todas_asignaturas
  ↓
Action: Lee slot ultimos_resultados_asignaturas y muestra todos
  ↓
Respuesta: [Lista completa de 20 asignaturas]
```

---

## ⚠️ Importante: Antes de Entrenar

### 1. Verificar que Ollama está corriendo

```bash
ollama list
ollama run llama3
```

### 2. Entrenar el modelo

```bash
rasa train
```

### 3. Validar configuración

```bash
rasa data validate
```

Debería mostrar:
```
✅ No issues found in domain, data, and config files.
```

---

## 🧪 Tests Recomendados

### Test 1: Consulta Específica con Fuzzy Match
```
Usuario: "cuántos créditos tiene Redes"
Esperado: Encuentra "Redes de Computadores" y devuelve créditos
```

### Test 2: Consulta General Simple
```
Usuario: "asignaturas de primero"
Esperado: Lista de asignaturas de 1º curso
```

### Test 3: Consulta General con Filtros
```
Usuario: "asignaturas obligatorias de tercero"
Esperado: SQL con WHERE curso=3 AND tipologia='Obligatoria'
```

### Test 4: Desambiguación
```
Usuario: "qué es Cálculo"
Esperado: Si hay "Cálculo I" y "Cálculo II", LLM desambigua
```

### Test 5: Ver Todos
```
Usuario: "asignaturas de primero"
Sistema: [Muestra 5] "Hay 15 más..."
Usuario: "todas"
Esperado: Muestra las 20 asignaturas completas
```

### Test 6: Búsqueda por Código
```
Usuario: "qué es 2050016"
Esperado: Encuentra por código exacto
```

### Test 7: Pregunta de Seguimiento
```
Usuario: "cuántos créditos tiene Redes"
Sistema: "Redes de Computadores tiene 6 créditos"
Usuario: "es obligatoria?"
Esperado: Usa contexto de última asignatura consultada
```

---

## 📊 Métricas de Calidad

### Intents
- ✅ Todos los intents en domain están en NLU
- ✅ Todos los intents en rules/stories están en domain
- ✅ Ejemplos suficientes (>15 por intent)

### Actions
- ✅ Todas las actions en rules/stories están en domain
- ✅ Todas las actions en domain están implementadas en `actions/*.py`

### Slots
- ✅ Todos los slots referenciados existen en domain
- ✅ Mappings correctos (custom/from_entity)

### Responses
- ✅ Todas las utterances usadas están definidas

---

## 🚀 Comandos para Iniciar

```bash
# Terminal 1: Actions server
rasa run actions

# Terminal 2: Rasa shell
rasa shell

# O Rasa interactive (para debugging)
rasa interactive
```

---

## 📝 Notas Adicionales

1. **Legacy vs Nuevo:**
   - `consultar_asignatura` → Flujo antiguo (mantener compatibilidad)
   - `consultar_asignatura_db` → **NUEVO sistema Text-to-SQL**

2. **Timeout de LLM:**
   - Clasificación: ~3-5s
   - Generación SQL: ~5-8s
   - Respuesta natural: ~5-10s
   - **Total: 15-25s** (puede ser lento en primer uso)

3. **Caché:**
   - Considerar implementar caché para consultas frecuentes
   - Ollama mantiene modelo en RAM después del primer uso

4. **Escalabilidad:**
   - Añadir nuevos contextos (profesores, horarios) requiere:
     - Nuevas actions en `asignaturas.py` (copiar patrón)
     - Nuevos intents en domain/NLU
     - Nuevas rules/stories

---

## ✅ Estado Final

**TODOS LOS ARCHIVOS SINCRONIZADOS CORRECTAMENTE**

El sistema está listo para entrenar y probar.
