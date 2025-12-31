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

## Próximas Versiones Planificadas

| Versión | Épica | Descripción |
|---------|-------|-------------|
| v2.0.0 | Horarios | Consulta de horarios por asignatura/grupo |
| v3.0.0 | Profesores | Información sobre profesorado |
| v4.0.0 | Trámites | Documentación administrativa |
| v5.0.0 | RAG | Respuestas basadas en documentos con embeddings |
