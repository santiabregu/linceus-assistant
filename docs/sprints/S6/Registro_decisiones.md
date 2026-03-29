# Registro de decisiones - Sprint 6

## Contexto

Sprint centrado en la épica de **Horarios y Aulas**: extraer los horarios oficiales del PDF de la ETSII, generar archivos Markdown estructurados, poblar las tablas `aulas`, `grupos_clase` y `horarios` en Supabase, e integrar la consulta de horarios en el chatbot Rasa.

---

## Iteración 1 (2026-03-28): Extracción de horarios del PDF

### D-001: Extracción del PDF con pdfplumber + filtrado de watermark

**Problema:** El PDF oficial (`horarios-grados-2025-26.pdf`) contiene un watermark "BORRADOR DE HORARIOS" en fuente tamaño 59 que contamina la extracción de tablas, mezclando letras sueltas (B, O, R, D, A...) con el contenido de las celdas.
**Decisión:** Usar `pdfplumber` con un filtro previo que descarta todos los `char` con `size >= 50` antes de llamar a `extract_tables()`. Esto elimina el watermark sin afectar el contenido real (tamaño 8-12).
**Alternativas descartadas:**
- `tabula-py`: no instalado, requiere Java.
- `camelot`: no instalado, requiere Ghostscript.
- Extracción manual: inviable para 51 páginas con ~100 tablas.
**Archivos:** `generar_horarios.py`

### D-002: Formato de código del PDF y filtrado por titulación

**Problema:** El PDF contiene horarios de 7 titulaciones diferentes (C, S, T, IN, SA, IA, DGTM). Solo necesitamos las 3 activas en Supabase.
**Decisión:** Parsear el código de la primera celda del header de cada tabla con el patrón `^(\d)([A-Z])(\d)-C([12])$` (ej: `1C1-C1` = curso 1, Computadores, grupo 1, cuatrimestre 1). Filtrar solo los grados con letra C, S o T.
**Resultado:** Se extraen exactamente 27 combinaciones curso/grupo (7 IC + 12 IS + 8 TI).
**Archivos:** `generar_horarios.py`

### D-003: Estructura de archivos Markdown por titulación/curso/grupo

**Problema:** Decidir cómo organizar los horarios extraídos para que sean consumibles tanto por Rasa (action) como por humanos.
**Decisión:** Generar archivos Markdown en `horarios_aulas/{computadores,software,tecnologias_informaticas}/cursoX_grupoY.md`. Cada archivo contiene ambos cuatrimestres (C1 y C2) con tablas Markdown estándar. El formato de celda es `ASIGNATURA (aula, labs)`.
**Justificación:** Markdown es legible por humanos, fácil de parsear programáticamente, y versionable en Git. La organización por carpetas facilita la navegación.
**Resultado:**
- `computadores/`: 7 archivos (cursos 1-4, hasta 3 grupos)
- `software/`: 12 archivos (cursos 1-4, hasta 4 grupos)
- `tecnologias_informaticas/`: 8 archivos (cursos 1-4, hasta 3 grupos)
**Archivos:** `generar_horarios.py`, `horarios_aulas/`

### D-004: Limpieza de artefactos del PDF (comas dobles, asteriscos)

**Problema:** El PDF usa `**` para indicar laboratorios compartidos y la extracción a veces genera comas dobles (`,,`) por separadores en el texto original.
**Decisión:** Aplicar limpieza post-extracción con regex: eliminar `**`/`*` de asignaturas, y reemplazar `,\s*,` por `,` en el resultado final.
**Archivos:** `generar_horarios.py`

---

## Iteración 2 (2026-03-28): Inserción en base de datos

### D-005: Script separado para inserción en BD

**Problema:** Decidir si la inserción en BD va dentro de `generar_horarios.py` o en un script aparte.
**Decisión:** Crear `insertar_horarios_db.py` separado. Lee los Markdown ya generados y los inserta en Supabase.
**Justificación:** Separación de responsabilidades. `generar_horarios.py` es PDF → Markdown (idempotente, sin dependencia de BD). `insertar_horarios_db.py` es Markdown → BD (requiere conexión a Supabase, tiene flag `--clean`). Permite re-ejecutar uno sin el otro.
**Archivos:** `insertar_horarios_db.py`

### D-006: Diccionario unificado de alias/abreviaturas

**Problema:** El PDF usa abreviaturas (ALN, CED, FP, ADDA, IISSI1...) pero la BD tiene nombres completos. Existían 3 diccionarios duplicados: `ALIAS_ASIGNATURAS` en `text_to_sql.py` (20 entradas), `ABREVIATURA_NOMBRE` en `insertar_horarios_db.py` (~80 entradas), y una lista hardcodeada en `actions/horarios/actions.py` (~50 entradas).
**Decisión:** Diccionario único `ALIAS_ASIGNATURAS` (93 entradas) en `actions/shared/config.py`. Los 3 consumidores importan de ahí. Para abreviaturas ambiguas entre titulaciones (ej: SSII = "Seguridad en Sistemas Informáticos" en IC/TI vs "Seguridad de Sistemas de Información" en IS), un diccionario adicional `ALIAS_POR_TITULACION` en el mismo fichero.
**Justificación:** Fuente única de verdad. Antes `text_to_sql.py` solo tenía 20 alias; ahora tiene acceso a los 93. Añadir un alias nuevo solo requiere tocar un fichero.
**Alternativas descartadas:**
- Generación automática de acrónimos a partir de los nombres en BD: demasiado frágil, no cubre abreviaturas coloquiales (EdC, FFI, IISSI1).
- Lookup en BD con fuzzy matching: lento y propenso a falsos positivos para abreviaturas de 2-3 letras.
**Archivos:** `actions/shared/config.py` (fuente), `actions/asignaturas/text_to_sql.py`, `actions/horarios/actions.py`, `insertar_horarios_db.py` (consumidores)

### D-007: Un grupo_clase por (asignatura, grupo), no por cuatrimestre

**Problema:** El primer intento creaba un `grupo_clase` por cada combinación (asignatura, grupo, cuatrimestre), lo que violaba el constraint UNIQUE `(asignatura_id, codigo, curso_academico, tipo)` para asignaturas anuales como FP que aparecen en C1 y C2.
**Decisión:** Un `grupo_clase` es único por (asignatura, grupo, tipo, curso_academico). Ambos cuatrimestres comparten el mismo `grupo_clase`. Los registros de `horarios` que apuntan a ese grupo indican en qué franja horaria y día se imparte.
**Archivos:** `insertar_horarios_db.py`

### D-008: Validación estricta de códigos de aula

**Problema:** Celdas complejas de 4º curso con asignaturas compartidas (ej: `TIS(2) / C(1)`, `PGPI(1) / GP`) generaban falsos positivos: asignaturas como `TIS(2)`, `PGPI`, `ASD` se insertaban como aulas. También fragmentos de parsing roto (`1) (A2.10`, `1día)`) acababan en la tabla `aulas`.
**Decisión:** Validación con regex estricto `^[A-Z]\d+\.\d+[a-z]?$` para códigos de aula. Solo se insertan códigos que coincidan con el patrón real de la ETSII (ej: H0.11, A2.14, G1.30b, F0.33a). Además, filtrar entradas donde la "asignatura" parseada coincide con un código de aula o empieza con dígito+paréntesis.
**Resultado:** De 93 "aulas" iniciales (con basura), se quedaron 50 aulas reales y limpias.
**Archivos:** `insertar_horarios_db.py`

### D-009: Clasificación automática de tipo de aula por edificio

**Problema:** La tabla `aulas` tiene un campo `tipo` (teoria/laboratorio/seminario).
**Decisión:** Deducir el tipo a partir de la letra del edificio en el código:
- Edificios A, H → `teoria` (aulas grandes de clase)
- Edificios B, F, G, I → `laboratorio` (aulas de prácticas/informática)
**Justificación:** Coincide con la distribución real de la ETSII: edificio H = salón de actos y aulas grandes, A = aulas de teoría, F/G = laboratorios de informática, B/I = laboratorios.
**Archivos:** `insertar_horarios_db.py`

---

## Iteración 3 (2026-03-28): Integración en Rasa

### D-010: Action `ActionConsultaHorario` basada en archivos Markdown

**Problema:** Decidir si la action de Rasa consulta los horarios desde la BD o desde los archivos Markdown.
**Decisión:** La action lee directamente los archivos Markdown. La BD se usa como fuente de verdad para consultas SQL avanzadas (futuro), pero para la action conversacional los Markdown son más rápidos y no requieren queries complejas con 3 JOINs.
**Capacidades implementadas:**
- Consulta por curso + grupo: "¿Qué horario tiene 2º grupo 1?"
- Filtro por día de la semana: "¿Qué clases hay los lunes en primero?"
- Filtro por cuatrimestre: "Horario del cuatrimestre 1 de segundo"
- Búsqueda por asignatura en todos los cursos/grupos: "¿En qué aula tengo FP?"
- Pide grupo si hay varios disponibles, o lo asume si solo hay uno
**Archivos:** `actions/horarios/__init__.py`, `actions/horarios/actions.py`

### D-011: Datos NLU para intent `consulta_horario`

**Problema:** Se necesitan ejemplos de entrenamiento para que DIET clasifique correctamente las preguntas sobre horarios.
**Decisión:** Crear `data/nlu/horarios.yml` con ~90 ejemplos que cubren: consulta de horario por curso/grupo, filtro por día, consulta de aula de asignatura, consulta de hora, y variaciones coloquiales.
**Archivos:** `data/nlu/horarios.yml`, `domain.yml` (intent + action), `data/rules.yml` (regla), `actions/actions.py` (import)

---

## Resultado final

| Tabla | Registros |
|-------|-----------|
| `aulas` | 50 (únicas, validadas) |
| `grupos_clase` | 267 |
| `horarios` | 753 |

**Por titulación:**
- GII-IS (Software): 299 horarios
- GII-TI (Tecnologías Informáticas): 245 horarios
- GII-IC (Computadores): 209 horarios

**Abreviaturas no resueltas (6):** EC, GP, MCG, PID, T, TIS — son asignaturas de otras titulaciones que aparecen en horarios compartidos de 4º de Software. No afectan a la funcionalidad.

---

## Pendiente

- Re-entrenar modelo NLU (`rasa train`) para activar el intent `consulta_horario`
- Testing e2e de la action de horarios contra el bot
- Valorar si migrar la action para consultar la BD directamente en vez de los Markdown
- Completar el mapeo de las 6 abreviaturas compartidas de 4º curso
