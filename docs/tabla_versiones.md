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

## Próximas Versiones Planificadas

| Versión | Épica | Descripción |
|---------|-------|-------------|
| v2.0.0 | Horarios | Consulta de horarios por asignatura/grupo |
| v3.0.0 | Profesores | Información sobre profesorado |
| v4.0.0 | Trámites | Documentación administrativa |
| v5.0.0 | RAG | Respuestas basadas en documentos con embeddings |
