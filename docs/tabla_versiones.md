# Historial de Versiones - Linceus Assistant

Este documento registra los cambios realizados en cada versión del chatbot siguiendo la estrategia de [versionado semántico](sprints/S2/Versionado.md).

---

## Resumen de Versiones

| Versión | Fecha | Épica | Descripción |
|---------|-------|-------|-------------|
| v1.0.0 | 2024-12 | Base | Versión inicial con datos de ejemplo de Rasa |
| v1.1.0 | 2024-12 | Infraestructura | Conexión con base de datos Supabase |
| v1.2.0 | 2024-12 | Asignaturas | Consulta de asignaturas por código o nombre |
| v1.2.1 | 2024-12 | Asignaturas | Mejoras UX: fuzzy matching y contexto |
| v1.2.2 | 2024-12 | Asignaturas | Rapidfuzz + búsqueda tolerante a acentos |
| v1.3.0 | 2024-12 | Asignaturas | Consultas filtradas con NLU puro |
| v1.3.1 | 2024-12 | Asignaturas | Lógica singular/plural + filtro créditos |
| v1.3.2 | 2026-01 | Asignaturas | Simplificación: eliminar intent redundante + ejemplos NLU |
| v1.4.0 | 2026-01 | Infraestructura | Soporte multi-titulación con contexto académico |
| v1.4.1 | 2026-01 | Asignaturas | Listar todas las asignaturas + slot contexto_dominio |
| v1.4.2 | 2026-01 | Infraestructura | Reorganización por épicas + helpers de contexto |
| v1.4.3 | 2026-01 | General | Intent pedir_ayuda para mostrar capacidades del bot |
| v1.4.4 | 2026-01 | Asignaturas | Ver todas: reutilizar filtros de consulta anterior |
| v2.0.0 | 2026-02 | Infraestructura | Migración completa a Text-to-SQL con Ollama |

---

## Detalle por Versión

### v1.0.0 - Versión Inicial
**Fecha:** Diciembre 2024  
**Tipo:** MAJOR - Primera versión funcional

**Cambios:**
- Configuración inicial del proyecto Rasa
- Intents básicos: `greet`, `goodbye`, `bot_challenge`, `mood_great`, `mood_unhappy`
- Respuestas predefinidas de ejemplo
- Pipeline NLU por defecto de Rasa
- Estructura base del proyecto

**Archivos principales:**
- `config.yml` - Pipeline NLU básico
- `domain.yml` - Intents y respuestas de ejemplo
- `data/nlu/general.yml` - Datos de entrenamiento básicos

---

### v1.1.0 - Conexión con Base de Datos
**Fecha:** Diciembre 2024  
**Tipo:** MINOR - Nueva funcionalidad dentro de infraestructura

**Cambios:**
- Integración con Supabase (PostgreSQL + pgvector)
- Clase `DatabaseConnection` para gestión de conexiones
- Action `action_test_supabase` para verificar conectividad
- Configuración de variables de entorno (`.env`)
- Estructura de tablas: `asignaturas`, `titulaciones`, `departamentos`

**Archivos principales:**
- `actions/actions.py` - Lógica de conexión a BD
- `.env` - Variables de configuración
- `endpoints.yml` - Configuración del action server

---

### v1.2.0 - Épica Asignaturas
**Fecha:** Diciembre 2024  
**Tipo:** MAJOR - Nueva épica funcional

**Cambios:**
- Intent `consultar_asignatura` con entidades `codigo_asignatura` y `nombre_asignatura`
- Intent `pregunta_seguimiento` para follow-ups sin repetir código
- Intent `pedir_info_asignatura` para consultas genéricas
- Búsqueda por código exacto o nombre parcial (LIKE)
- Consulta de atributos específicos: créditos, curso, duración, tipología, departamento
- Slots para mantener contexto: `ultimo_codigo_consultado`, `ultimo_nombre_asignatura`
- Rules para gestión de diálogo

**Archivos principales:**
- `data/nlu/asignaturas.yml` - Datos de entrenamiento
- `actions/asignaturas.py` - Lógica de consulta
- `actions/db.py` - Módulo de conexión a BD
- `data/rules.yml` - Reglas de diálogo

**Funcionalidades:**
- ✅ Consultar información general de una asignatura
- ✅ Consultar atributos específicos (créditos, curso, etc.)
- ✅ Preguntas de seguimiento sobre última asignatura
- ✅ Búsqueda por nombre parcial

---

### v1.2.1 - Mejoras UX Asignaturas
**Fecha:** Diciembre 2024  
**Tipo:** PATCH - Correcciones y mejoras

**Cambios:**
- **Fuzzy matching**: Tolerancia a errores ortográficos en atributos
  - Usa `difflib.get_close_matches` con cutoff 0.7
  - Ejemplo: "obligatioria" → "obligatoria" → campo `tipologia`
- **Nueva action** `action_pedir_info_asignatura`:
  - Si hay contexto previo → muestra info de última asignatura
  - Si no hay contexto → pide nombre o código de forma natural
- **Respuestas variadas**: Múltiples variaciones para evitar respuestas robóticas
  - `utter_greet`: 3 variaciones
  - `utter_pedir_codigo`: 3 variaciones
- **Ampliación de ATRIBUTO_MAP**: Más sinónimos y variantes
- **Refactorización**: Separación de código en módulos (`db.py`, `asignaturas.py`)

**Archivos modificados:**
- `actions/asignaturas.py` - Fuzzy matching + nueva action
- `actions/actions.py` - Imports actualizados
- `domain.yml` - Respuestas variadas
- `data/rules.yml` - Nueva regla para `pedir_info_asignatura`

**Mejoras de UX:**
- ✅ Tolera typos como "creditoss", "obligatioria", "duracion"
- ✅ Contexto conversacional mejorado
- ✅ Respuestas más naturales y variadas

---

### v1.2.2 - Rapidfuzz y Búsqueda Mejorada
**Fecha:** Diciembre 2024  
**Tipo:** PATCH - Mejora de precisión en búsquedas

**Cambios:**
- **Migración a rapidfuzz**: Reemplazo de `difflib` por `rapidfuzz` para fuzzy matching
  - 10-100x más rápido
  - Mejor precisión con algoritmo `WRatio`
  - Score cutoff: 70% para atributos, 60% para nombres
- **Normalización de texto**: Función `normalizar_texto()` que elimina acentos
  - "Fundamentos de Programacion" encuentra "Fundamentos de Programación"
- **Búsqueda inteligente de nombres**:
  - Primero intenta LIKE en BD
  - Si no encuentra, aplica fuzzy matching sobre todas las asignaturas
- **Detección de cambio de asignatura**: 
  - Palabras clave: "otra", "diferente", "cambiar"
  - Limpia contexto y pide nueva asignatura
- **Más ejemplos NLU**: Nombres de asignaturas sueltos como intent válido

**Archivos modificados:**
- `actions/asignaturas.py` - Rapidfuzz + normalización
- `data/nlu/asignaturas.yml` - Ejemplos con nombres sueltos
- `requirements.txt` - Añadido `rapidfuzz>=3.0.0`

**Mejoras de UX:**
- ✅ Busca asignaturas sin importar acentos
- ✅ Detecta "quiero otra asignatura" y limpia contexto
- ✅ Mejor tolerancia a typos en nombres largos

---

### v1.3.0 - Consultas Filtradas con NLU Puro
**Fecha:** Diciembre 2024  
**Tipo:** MINOR - Nueva funcionalidad escalable

**Cambios:**
- **Nuevas entidades para filtros**:
  - `filtro_curso`: primero, segundo, 1º, 2º, etc.
  - `filtro_tipologia`: obligatoria, optativa, formación básica
  - `filtro_duracion`: anual, primer/segundo cuatrimestre
  - `filtro_titulacion`: nombre de la carrera
- **Nueva action `ActionConsultarAsignaturasFiltradas`**: 
  - Extrae filtros desde slots de Rasa (sin dependencias externas)
  - Construye queries SQL parametrizadas de forma segura
  - Formatea respuestas con descripción del filtro aplicado
- **Nuevo intent `consultar_asignaturas_filtradas`**: 
  - 55+ ejemplos con entidades anotadas
  - Patrones combinados: curso + tipología + duración + titulación

**Decisión de diseño:**
- Se mantiene `gemini_client.py` para uso futuro en RAG
- Para filtros estructurados, NLU puro es más rápido, gratis y sin dependencias
- Escalable: añadir filtro = añadir entidad + ejemplos NLU

**Archivos modificados:**
- `actions/asignaturas.py` - Action con mapeos de normalización
- `data/nlu/asignaturas.yml` - Ejemplos con entidades anotadas
- `domain.yml` - Nuevas entidades y slots de filtro

**Arquitectura:**
```
Usuario: "obligatorias de primero"
    ↓
NLU extrae: filtro_tipologia="obligatorias", filtro_curso="primero"
    ↓
Action normaliza: tipologia="Obligatoria", curso=1
    ↓
SQL: SELECT ... WHERE tipologia = %s AND curso = %s
```

---

### v1.3.1 - Lógica Singular/Plural y Filtro de Créditos
**Fecha:** Diciembre 2024  
**Tipo:** PATCH - Mejoras de precisión NLU y nuevas funcionalidades

**Cambios:**
- **Distinción singular vs plural**:
  - "Redes es obligatoria?" → `consultar_asignatura` (específica)
  - "asignaturas obligatorias" → `consultar_asignaturas_filtradas` (listado)
- **ActionPreguntaSeguimiento mejorada**:
  - Detecta si hay nombre en el mensaje → busca ESA asignatura
  - Si no hay nombre → usa contexto previo
  - Arregla: "Redes es obligatoria?" tras consultar otra asignatura
- **Fallback de extracción de nombres**:
  - Función `extraer_posible_nombre_del_mensaje()`
  - Busca palabras capitalizadas ignorando palabras comunes
  - Permite recuperar nombres no detectados por NLU
- **Nuevo filtro de créditos**:
  - Entidad `filtro_creditos` + slot
  - "asignaturas de 6 créditos" ahora funciona
  - Regex: `\b(6|12|4\.5|9)\b`
- **Regex para códigos de asignatura**:
  - `\b20\d{5}\b` → solo códigos de 7 dígitos
  - Evita que "6" se confunda con código
- **Fallback en filtros**:
  - Si NLU no extrae entidades, busca filtros en el texto
  - Mapeos sin acentos para compatibilidad con `normalizar_texto()`

**NLU mejorado:**
- +20 ejemplos de "X es obligatoria?" con nombres variados
- +7 ejemplos de seguimiento con pronombres ("esa", "su")
- Comentarios claros en cada sección del NLU

**Archivos modificados:**
- `actions/asignaturas.py` - Lógica de detección + fallbacks
- `data/nlu/asignaturas.yml` - Ejemplos singular/plural + regex
- `domain.yml` - Entidad y slot `filtro_creditos`

**Flujo de decisión:**
```
Usuario dice algo con "asignatura" o nombre
    ↓
¿Hay nombre mencionado? → Sí → Buscar ESA asignatura
    ↓ No
¿Hay contexto previo? → Sí → Usar contexto
    ↓ No
¿Hay palabras capitalizadas? → Sí → Intentar como nombre
    ↓ No
Pedir que especifique
```

---

### v1.3.2 - Simplificación de Intents
**Fecha:** Enero 2026  
**Tipo:** PATCH - Refactorización y limpieza

**Cambios:**
- **Eliminado intent `pedir_info_asignatura`**: Era un caso de uso artificial (nadie dice "quiero preguntarte sobre una asignatura" sin dar el nombre)
- **Eliminada `ActionPedirInfoAsignatura`**: ~55 líneas de código innecesario
- **Limpieza de archivos**:
  - `domain.yml` - Eliminado intent y action
  - `rules.yml` - Eliminada rule asociada
  - `stories.yml` - Eliminada story del flujo
  - `nlu/asignaturas.yml` - Eliminados 16 ejemplos del intent
  - `actions/asignaturas.py` - Eliminada clase completa
- **Nuevos ejemplos NLU para cambio de asignatura**:
  - "y [Fundamentos de Programación] cuántos [créditos] tiene?"
  - "y [Redes] de qué [curso] es?"
  - "ahora dime de [Criptografía]"
  - +4 variaciones más

**Justificación:**
- El flujo `pedir_info_asignatura` → esperar → `consultar_asignatura` era innecesario
- Los usuarios siempre mencionan la asignatura directamente
- Simplifica el modelo NLU (menos intents = mejor clasificación)
- El cambio de asignatura en contexto ya estaba soportado por `ActionConsultarAsignatura`

**Archivos modificados:**
- `actions/asignaturas.py` - Eliminada ActionPedirInfoAsignatura
- `data/nlu/asignaturas.yml` - Eliminado intent + añadidos ejemplos
- `data/rules.yml` - Eliminada rule
- `data/stories.yml` - Eliminada story
- `domain.yml` - Eliminado intent y action

---

### v1.4.0 - Soporte Multi-Titulación
**Fecha:** Enero 2026  
**Tipo:** MINOR - Nueva funcionalidad de infraestructura

**Cambios:**
- **Nuevo módulo `actions/config.py`**: Configuración centralizada del contexto académico
  - Clase `BotConfig` con defaults desde variables de entorno
  - Mapeo de códigos a nombres legibles (GII-IS → "Grado en Ing. Informática - Ing. del Software")
  - Soporte para override por slots de Rasa
- **Nuevo módulo `actions/contexto.py`**: Actions para gestión de contexto
  - `ActionCambiarContexto`: Permite cambiar de titulación en conversación
  - `ActionConsultarContexto`: Muestra el contexto académico actual
- **Nuevas variables de entorno** en `.env`:
  - `DEFAULT_UNIVERSIDAD_CODIGO=US`
  - `DEFAULT_CENTRO_CODIGO=ETSII`
  - `DEFAULT_TITULACION_CODIGO=GII-IS`
- **Filtro por titulación en queries**:
  - `buscar_asignatura()` ahora acepta `titulacion_codigo`
  - `ActionConsultarAsignatura` filtra por contexto
  - `ActionPreguntaSeguimiento` filtra por contexto
  - `ActionConsultarAsignaturasFiltradas` filtra por contexto
- **Nuevos intents** (ejemplos mínimos, no es prioridad):
  - `cambiar_contexto_academico`: "cambiar a Tecnologías Informáticas"
  - `consultar_contexto_academico`: "qué carrera estoy consultando"
- **Nuevos slots**:
  - `contexto_centro`: Centro seleccionado (override del default)
  - `contexto_titulacion`: Titulación seleccionada (override del default)

**Archivos nuevos:**
- `actions/config.py` - Configuración centralizada
- `actions/contexto.py` - Actions de contexto
- `data/nlu/contexto.yml` - Intents de contexto

**Archivos modificados:**
- `actions/asignaturas.py` - Import BotConfig + filtro titulación en queries
- `actions/actions.py` - Imports de nuevas actions
- `domain.yml` - +2 intents, +2 entities, +2 slots, +2 actions
- `data/rules.yml` - +2 rules para contexto
- `.env` - +3 variables de configuración

**Preparación para escalabilidad:**
- El sistema ahora puede soportar múltiples titulaciones (GII-IS, GII-TI, GII-IC, GII-SI)
- Por defecto usa Ingeniería del Software
- Los usuarios pueden cambiar de carrera en conversación

---

### v1.4.1 - Listar Todas las Asignaturas y Contexto de Dominio
**Fecha:** Enero 2026  
**Tipo:** PATCH - Mejoras funcionales

**Cambios:**
- **Soporte para listar TODAS las asignaturas sin filtro**:
  - Detecta patrones como "cuáles son las asignaturas", "todas las asignaturas", "asignaturas enteras"
  - Permite consulta sin filtro específico (muestra primeras 10 con opción de continuar)
- **Nuevo slot `contexto_dominio`**:
  - Indica si estamos hablando de asignaturas, profesores, horarios, etc.
  - Se setea automáticamente en todas las actions de asignaturas
  - Preparación para futura épica de Profesores (mismo contexto titulación, diferente dominio)
- **Todas las actions de asignaturas ahora retornan `SlotSet("contexto_dominio", "asignaturas")`**

**Archivos modificados:**
- `actions/asignaturas.py` - Detección de "listar todas" + contexto_dominio en todos los returns
- `domain.yml` - Nuevo slot contexto_dominio

**Flujo mejorado:**
```
Usuario: "cuáles son las asignaturas?"
    ↓
ActionConsultarAsignaturasFiltradas detecta patrón "listar todas"
    ↓
SQL: SELECT * FROM asignaturas WHERE titulacion_codigo = 'GII-IS' LIMIT 10
    ↓
Respuesta: Lista de asignaturas + mensaje "hay más, ¿quieres filtrar?"
    ↓
SlotSet: contexto_dominio = "asignaturas"
```

---

### v1.4.2 - Reorganización por Épicas y Helpers de Contexto
**Fecha:** Enero 2026  
**Tipo:** PATCH - Refactorización y mejoras de mantenibilidad

**Cambios:**
- **Reorganización de archivos con secciones por épica**:
  - `domain.yml`: Secciones para General, Contexto, Asignaturas, Profesores (futuro), Horarios (futuro)
  - `rules.yml`: Misma estructura con separadores
  - `stories.yml`: Misma estructura + nombres en español
- **Nuevos helpers en `config.py`**:
  - `get_titulacion_activa(tracker)`: Obtiene titulación del slot o default
  - `get_centro_activo(tracker)`: Obtiene centro del slot o default
- **Simplificación de actions**:
  - Las 3 actions de asignaturas ahora usan `BotConfig.get_titulacion_activa(tracker)`
  - Eliminado código repetitivo de lectura de contexto

**Archivos modificados:**
- `domain.yml` - Reorganizado con secciones
- `data/rules.yml` - Reorganizado con secciones + nombres en español
- `data/stories.yml` - Reorganizado con secciones + nombres en español
- `actions/config.py` - Nuevos helpers para tracker
- `actions/asignaturas.py` - Simplificado uso de contexto

**Antes vs Después:**
```python
# Antes (repetitivo en cada action):
titulacion = tracker.get_slot("contexto_titulacion") or BotConfig.get_default_titulacion()

# Después (limpio):
titulacion = BotConfig.get_titulacion_activa(tracker)
```

---

### v1.4.3 - Intent de Ayuda
**Fecha:** Enero 2026  
**Tipo:** PATCH - Nueva funcionalidad de usuario

**Cambios:**
- **Nuevo intent `pedir_ayuda`**: Responde cuando el usuario pregunta qué puede hacer el bot
- **Ejemplos NLU**: ~20 frases como "qué puedes hacer", "ayuda", "qué información tienes"
- **Response `utter_ayuda`**: Menú con las capacidades actuales del bot

**Archivos modificados:**
- `data/nlu/general.yml` - Nuevo intent pedir_ayuda
- `domain.yml` - Nuevo intent + response utter_ayuda
- `data/rules.yml` - Nueva rule para pedir_ayuda → utter_ayuda

**Ejemplo de respuesta:**
```
🎓 Soy Linceus, tu asistente de la ETSII. Puedo ayudarte con:

📚 Asignaturas:
• "Háblame de Redes de Computadores"
• "¿Cuántos créditos tiene IS2?"
• "¿Qué asignaturas obligatorias hay en primero?"

🎯 Contexto académico:
• "¿Qué carrera estoy consultando?"
• "Cambiar a Tecnologías Informáticas"
```

---

### v1.4.4 - Ver Todas las Asignaturas de Consulta Anterior
**Fecha:** Enero 2026  
**Tipo:** PATCH - Nueva funcionalidad

**Cambios:**
- **Nuevo intent `pedir_mas_resultados`**: Permite ver todos los resultados cuando el bot muestra "... y X más"
- **Nueva action `ActionMostrarTodas`**: Reutiliza los filtros de la consulta anterior
- **Nuevos slots `ultimos_filtros_*`**: Guardan curso, tipología, duración y créditos de la última consulta
- **Fix de tipología**: Valores en TIPOLOGIA_MAP ahora coinciden con BD (OBLIGATORIA, OPTATIVA, FORMACION_BASICA, TFG)

**Archivos modificados:**
- `domain.yml` - +1 intent, +4 slots, +1 action
- `data/nlu/asignaturas.yml` - +17 ejemplos del intent pedir_mas_resultados
- `data/rules.yml` - Nueva rule pedir_mas_resultados → action_mostrar_todas
- `actions/asignaturas.py` - Nueva ActionMostrarTodas + guardar filtros en slots
- `actions/actions.py` - Import de ActionMostrarTodas

**Flujo:**
```
Usuario: "dame las optativas de cuarto"
Bot: "Encontré 15 asignaturas... y 5 más. Di 'todas' para ver la lista completa."
    ↓ (guarda filtros: curso=4, tipologia=OPTATIVA)

Usuario: "todas"
Bot: "📚 Lista completa (15 asignaturas): 1. ... 2. ... 15. ..."
    ↓ (reutiliza los filtros guardados)
```

---

### v2.0.0 - Sistema Text-to-SQL con Ollama
**Fecha:** Febrero 2026
**Tipo:** MAJOR - Nueva arquitectura de procesamiento con LLM

**Cambios:**
- **Migración completa de Gemini a Ollama**:
  - Cliente HTTP optimizado (`ollama_client.py`) vs subprocess
  - Modelo `llama3.2:3b` (más rápido que llama3)
  - Velocidad mejorada: 2-4s por consulta (vs 20-30s anterior)
  - El modelo permanece cargado en memoria → no hay overhead de inicio
- **Sistema Text-to-SQL con clasificación automática**:
  - Distingue consultas específicas ("cuántos créditos tiene Redes") vs generales ("asignaturas de primero")
  - Generación dinámica de SQL con filtros complejos
  - Desambiguación inteligente con LLM cuando hay múltiples coincidencias
- **Búsqueda fuzzy mejorada**:
  - Búsqueda por código exacto, nombre parcial, y fuzzy matching
  - Tolerancia a errores ortográficos y falta de acentos
  - Cache de asignaturas en memoria por sesión (mejora rendimiento)
- **Respuestas naturales con LLM**:
  - Todas las respuestas pasan por el LLM para eliminar roboticidad
  - Formato conversacional natural
- **Nueva action `ActionLLMPreprocess`**: Preprocesa con LLM antes de Rasa NLU
- **Nueva action `ActionConsultarAsignaturaDB`**: Sistema Text-to-SQL completo
- **Eliminado `gemini_client.py`**: Completamente reemplazado por Ollama
- **Nuevos documentos**:
  - `docs/TEXT_TO_SQL_ASIGNATURAS.md` - Documentación del sistema
  - `SOLUCION_VELOCIDAD_OLLAMA.md` - Solución técnica para optimización
  - `VERIFICACION_SISTEMA.md` - Checklist de consistencia
  - `db_tables.md` - Esquema de base de datos
  - `iniciar_ollama.bat` - Script para iniciar Ollama correctamente

**Archivos principales modificados:**
- `actions/asignaturas.py` - Reescrito con sistema Text-to-SQL
- `actions/actions.py` - Añadida ActionLLMPreprocess
- `actions/ollama_client.py` - **NUEVO** Cliente HTTP para Ollama
- `actions/llm_interpreter.py` - **NUEVO** Interpretación con Llama
- `domain.yml` - Nuevos intents y slots para Text-to-SQL
- `data/nlu/asignaturas.yml` - Intent `consultar_asignatura_db`
- `data/rules.yml` - Reglas para nuevo flujo
- `data/stories.yml` - Stories para Text-to-SQL
- `config.yml` - Configuración optimizada
- `.gitignore` - Añadido directorio `old/`

**Arquitectura del sistema:**
```
Usuario: "cuántos créditos tiene Redes"
    ↓
1. Clasificación automática → "consulta específica"
    ↓
2. Extracción de datos → nombre="Redes", atributo="creditos"
    ↓
3. Búsqueda fuzzy → "Redes de Computadores" (score: 85%)
    ↓
4. Si múltiples coincidencias → LLM desambigua
    ↓
5. Formateo con LLM → "Redes de Computadores tiene 6 créditos ECTS"
```

**Mejoras de rendimiento:**
| Operación | Antes | Ahora | Mejora |
|-----------|-------|-------|--------|
| Llamada a LLM | 20-30s | 2-4s | **5-15x** |
| Consulta completa | 60-90s | 8-15s | **6-10x** |

**Funcionalidades nuevas:**
- ✅ Búsqueda fuzzy con desambiguación inteligente
- ✅ Clasificación automática de tipo de consulta
- ✅ Generación dinámica de SQL para consultas complejas
- ✅ Respuestas conversacionales naturales
- ✅ Cache de asignaturas en memoria
- ✅ Detección automática de contexto académico

**Modelos entrenados:**
- `models/linceus_v2_0_3.tar.gz` - Versión intermedia
- `models/linceus_v2_0_4.tar.gz` - Versión estable actual

---

## Próximas Versiones Planificadas

| Versión | Épica | Descripción |
|---------|-------|-------------|
| v2.0.0 | Horarios | Consulta de horarios por asignatura/grupo |
| v3.0.0 | Profesores | Información sobre profesorado |
| v4.0.0 | Trámites | Documentación administrativa |
| v5.0.0 | RAG | Respuestas basadas en documentos con embeddings |
