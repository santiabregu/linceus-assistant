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

### D-010: Action `ActionConsultaHorario` basada en BD + LLM

**Problema:** Decidir si la action de Rasa consulta los horarios desde la BD o desde los archivos Markdown, y si la respuesta se genera con LLM o con templates.
**Decisión:** La action consulta directamente la BD (`aulas`, `grupos_clase`, `horarios`) mediante queries parametrizadas y genera la respuesta con Gemini (igual que `ActionConsultaEspecifica` en asignaturas).
**Justificación:** La BD permite filtros flexibles (por día, asignatura, cuatrimestre) sin parsear texto. El LLM genera respuestas naturales coherentes con el resto del chatbot. Los archivos Markdown se usan solo como fallback humano, no en runtime.
**Capacidades implementadas:**
- Consulta por curso + grupo: "¿Qué horario tiene 2º grupo 1?"
- Filtro por día de la semana: "¿Qué clases hay los lunes en primero?"
- Filtro por cuatrimestre: "Horario del cuatrimestre 1 de segundo"
- Búsqueda por asignatura en todos los cursos/grupos: "¿En qué aula tengo FP?"
- Pide grupo si hay varios disponibles, o lo asume si solo hay uno
**Archivos:** `actions/horarios/__init__.py`, `actions/horarios/actions.py`

### D-011: Datos NLU para intent `consulta_horario`

**Problema:** Se necesitan ejemplos de entrenamiento para que DIET clasifique correctamente las preguntas sobre horarios.
**Decisión:** Crear `data/nlu/horarios.yml` con ~115 ejemplos que cubren: consulta de horario por curso/grupo, filtro por día, consulta de aula de asignatura, consulta de hora, variaciones coloquiales, y ~25 ejemplos de preguntas de seguimiento (follow-up) dentro del contexto de horarios.
**Archivos:** `data/nlu/horarios.yml`, `domain.yml` (intent + action), `data/rules.yml` (regla), `actions/actions.py` (import)

---

## Iteración 4 (2026-03-28): Multi-intent y mejoras conversacionales

### D-012: Multi-intent nativo de DIET con `ActionMultiIntent`

**Problema:** El usuario puede formular preguntas que combinan varias intenciones en una sola frase, ej: "Cambiar a IS y dime el horario de segundo grupo 1" o "¿Cuántos créditos tiene Redes y qué horario tiene segundo?". Implementar esto sin soporte nativo requeriría heurísticas frágiles en el pipeline.
**Decisión:** Usar el soporte nativo de multi-intent de DIET añadiendo en `config.yml`:
```yaml
- name: WhitespaceTokenizer
  intent_tokenization_flag: true
  intent_split_symbol: "+"
```
Los intents compuestos se definen en `domain.yml` como `cambiar_contexto_academico+consulta_horario`, etc. Se crea `ActionMultiIntent` que:
1. Descompone el intent compuesto por `+`
2. Ejecuta la lógica de cada sub-intent (funciones internas, no actions Rasa)
3. Recoge los datos crudos (JSON) de cada sub-ejecutor
4. Genera UNA sola respuesta unificada con el LLM
**Alternativas descartadas:**
- Dispatcher personalizado (inspeccionar trackers entre acciones): inviable en Rasa sin hackear el core.
- Respuestas múltiples concatenadas: el usuario recibe 2 mensajes separados, experiencia peor.
- Pipeline de reglas con stories multi-step: combinatoria explosiva (N intents × M intents = N² stories).
**Intents implementados:** 6 combinaciones (cambiar_contexto×{horario,especifica,listado,conteo}, horario×especifica, especifica×listado).
**Archivos:** `actions/multi_intent/actions.py`, `actions/multi_intent/__init__.py`, `data/nlu/multi_intent.yml`, `config.yml`, `domain.yml`, `data/rules.yml`, `actions/actions.py`

### D-013: Respuesta unificada del multi-intent via LLM (no concatenación)

**Problema:** Al ejecutar 2 sub-intents (ej: cambio de contexto + consulta de horario), se generaban 2 respuestas separadas (cada sub-action llamaba a su propio LLM). Esto produce una experiencia de chatbot fragmentada e inconsistente.
**Decisión:** Los sub-ejecutores de `ActionMultiIntent` devuelven **datos crudos en JSON** (sin llamar al LLM), y solo al final se hace **una única llamada al LLM** con todos los datos combinados para generar una respuesta fluida e integrada.
**Justificación:** Una sola respuesta natural es mejor UX. El LLM recibe el contexto completo (cambio de titulación + datos de horario) y puede integrarlos de forma coherente.
**Archivos:** `actions/multi_intent/actions.py` (`_generar_respuesta_unificada`)

### D-014: Regla "no saludes" en todos los prompts LLM

**Problema:** Gemini prepend "¡Hola!" o "Buenos días," a todas las respuestas aunque se le pidiera ser directo, lo que resultaba en un saludo artificial en cada mensaje del bot.
**Decisión:** Añadir explícitamente en todos los prompts de sistema enviados al LLM (4 prompts: horarios, asignatura específica, listado, multi-intent): `"No saludes (nada de "Hola!", "Buenos dias", etc.) — ve directo a la respuesta"`.
**Archivos:** `actions/horarios/actions.py`, `actions/asignaturas/actions.py`, `actions/multi_intent/actions.py`

### D-015: Corrección tipología `TRONCAL` → `OBLIGATORIA` en prompts LLM

**Problema:** Los prompts de `text_to_sql.py` especificaban las tipologías válidas incluyendo `TRONCAL`, que no existe en la BD (tabla `asignaturas`, campo `tipologia`). El LLM generaba queries con `tipologia='TRONCAL'` que devolvían 0 resultados.
**Decisión:** Actualizar los 3 prompts de `text_to_sql.py` para listar solo los valores reales del enum: `OBLIGATORIA`, `OPTATIVA`, `FORMACION_BASICA`, `TFG`. Añadir además el mapeo explícito `troncal → OBLIGATORIA` en el prompt para que el LLM traduzca correctamente el lenguaje coloquial del usuario.
**Archivos:** `actions/asignaturas/text_to_sql.py`

### D-016: Detección heurística de seguimiento (follow-up) basada en recencia de slots

**Problema:** Las preguntas de seguimiento ("¿y el profesor?", "¿cuántas horas de lab tiene?", "¿qué días es?") no mencionan la asignatura explícitamente. El bot caía en fallback o usaba fuzzy matching que a veces elegía la asignatura incorrecta.
**Decisión:** Implementar detección heurística basada en **recencia de slots**: si no hay entidad `nombre_asignatura` en el mensaje actual pero el slot `ultimo_codigo_consultado` fue establecido en los últimos ≤3 turnos, se asume seguimiento y se usa esa asignatura como contexto. Se añade la función auxiliar `_contar_turnos_desde_slot(tracker, slot_name)` en ambas actions (asignaturas y horarios).
**Alternativas descartadas:**
- Lista de regex de palabras de seguimiento ("y", "también", "su", "qué días"...): frágil, idioma-dependiente, requiere mantenimiento constante.
- LLM para clasificar si es follow-up: demasiado lento, añade latencia a cada turno aunque no sea seguimiento.
**Pipeline final en `resolver_asignatura`:** NLU entity → alias dict → heuristic follow-up (slot ≤3 turnos) → fuzzy matching.
**Justificación del orden:** La heurística antes que fuzzy evita que fuzzy "robe" el contexto activo cuando el usuario hace una pregunta ambigua sin nombrar la asignatura.
**Archivos:** `actions/asignaturas/actions.py`, `actions/horarios/actions.py`

### D-017: Slot `ultima_action_ejecutada` para refinamiento de grupo

**Problema:** Después de una consulta de asignatura específica (ej: "¿Quién da clase de ADDA?"), si el usuario dice "en el grupo 2", Rasa clasificaba como `consulta_horario` (detectaba "grupo") y devolvía el horario del grupo 2 en vez de la info de ADDA en el grupo 2.
**Decisión:** Añadir el slot `ultima_action_ejecutada` (tipo text) que se setea a `"action_consulta_especifica"` o `"action_consulta_horario"` en cada llamada. En `ActionConsultaHorario`, si el mensaje contiene **solo** información de grupo (sin curso ni asignatura) y `ultima_action_ejecutada == "action_consulta_especifica"` y hay slot reciente (≤3 turnos), redirigir a `ActionConsultaEspecifica` con el contexto actual + nuevo grupo.
**Justificación:** El slot es ligero (solo almacena un string) y no requiere training adicional. La condición triple (solo grupo + action previa + slot reciente) minimiza falsos positivos.
**Archivos:** `actions/horarios/actions.py`, `actions/asignaturas/actions.py`, `domain.yml` (slot)

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

**Intents multi-intent implementados:** 6 combinaciones (cambiar_contexto+{horario,especifica,listado,conteo}, horario+especifica, especifica+listado)

---

## Iteración 5 (2026-03-31): Épica Profesores — scraping y campos BD

### D-018: Campos adicionales en tabla `profesores`

**Problema:** El schema original de `profesores` no incluía categoría académica ni enlace al perfil del departamento, campos disponibles en las webs de los 4 departamentos y útiles para el usuario.
**Decisión:** Añadir 2 columnas: `categoria_academica VARCHAR(100)` (Catedrático, Titular, Contratado Doctor, etc.) y `enlace_perfil VARCHAR(500)` (URL del perfil en la web del departamento o en SISIUS).
**Justificación:** `categoria_academica` está disponible en los 4 departamentos (DTE, LSI, MA1, CCIA) y es información que los alumnos consultan. `enlace_perfil` permite al chatbot enlazar directamente al perfil del profesor.
**Archivos:** `sql/add_profesores_fields.sql`, `docs/other/db_tables.md`

### D-019: Scrapers independientes por departamento

**Problema:** Cada departamento tiene una web con tecnología y estructura HTML completamente distinta (WordPress/Elementor en LSI, Plone CMS en DTE, HTML estático en CCIA, SISIUS+Directorio US en MA1).
**Decisión:** Un scraper independiente por departamento (`scraper_lsi.py`, `scraper_dte.py`, `scraper_ccia.py`, `scraper_ma1.py`) que genera un JSON intermedio en `profesores/datos/{depto}.json`. Un script separado `insertar_profesores_db.py` lee los 4 JSON e inserta en BD.
**Justificación:** Misma separación de responsabilidades que en horarios (D-005). Permite re-ejecutar un solo scraper sin afectar a los demás. Los JSON intermedios facilitan la depuración y revisión manual antes de insertar.
**Archivos:** `profesores/scraper_lsi.py`, `profesores/scraper_dte.py`, `profesores/scraper_ccia.py`, `profesores/scraper_ma1.py`, `profesores/insertar_profesores_db.py`

### D-020: Email ofuscado en DTE reconstruido desde spans

**Problema:** La web del DTE ofusca los emails usando HTML: `<span>usuario</span><img alt="Arroba"/><span>dominio</span>` en vez de texto plano o `mailto:`.
**Decisión:** Reconstruir el email concatenando los `<span>` hijos del `div.dtepersonalcab`, ignorando el span con clase `dtepersonalcab` (que es el label "Correo electrónico:"), y uniendo con `@`.
**Resultado:** 77/77 emails extraídos correctamente.
**Archivos:** `profesores/scraper_dte.py` (`extraer_email`)

### D-021: Nombre/apellidos no separables en CCIA y MA1

**Problema:** LSI y DTE usan formato "Apellidos, Nombre" (con coma), lo que permite separar campos. CCIA y MA1 usan "Nombre Apellido1 Apellido2" sin separador, y con nombres compuestos (José Luis, María del Carmen) es imposible separar automáticamente de forma fiable.
**Decisión:** Para CCIA y MA1, guardar el nombre completo en el campo `nombre` y dejar `apellidos` vacío. El trigger `trigger_normalizar_profesor` de la BD genera igualmente `nombre_normalizado` correcto para búsquedas. Para LSI y DTE, la coma permite separar correctamente.
**Alternativas descartadas:**
- Asumir primera palabra = nombre: falla con "José Luis Ruiz Reina" → nombre="José", apellidos="Luis Ruiz Reina".
- NLP para detección de nombres propios: overengineering para ~100 registros.
- Cruce con directorio US (tiene nombre en mayúsculas sin estructura): no aporta la separación.
**Impacto:** El campo `nombre_completo` (GENERATED = `apellidos || ', ' || nombre`) queda como `, Nombre Completo` para CCIA/MA1. Es aceptable porque las búsquedas usan `nombre_normalizado`, no `nombre_completo`. Se puede corregir manualmente si se necesita.
**Archivos:** `profesores/scraper_ccia.py`, `profesores/scraper_ma1.py`, `profesores/insertar_profesores_db.py`

### D-022: MA1 con doble enriquecimiento (SISIUS + Directorio US)

**Problema:** MA1 no tiene web propia funcional. SISIUS tiene el listado completo con ORCID y web personal, pero no tiene email directo (solo formulario). El Directorio US tiene email y teléfono pero hay que generar el slug del nombre.
**Decisión:** Pipeline de 3 pasos: (1) listado SISIUS → nombres + categoría + ID, (2) perfil SISIUS → ORCID, web personal, teléfono, (3) Directorio US → email, teléfono (solo si falta).
**Resultado:** 65 profesores, 50/65 con email (los 15 restantes no aparecen en el directorio US, probablemente por slug diferente o no estar dados de alta).
**Archivos:** `profesores/scraper_ma1.py`

### D-023: Trigger de BD genera `nombre_normalizado`, no el scraper

**Problema:** El script de inserción inicialmente enviaba `nombre_normalizado` calculado en Python. Pero la BD ya tiene un trigger `trigger_normalizar_profesor` que lo genera automáticamente al INSERT/UPDATE.
**Decisión:** No enviar `nombre_normalizado` en el INSERT. Dejar que el trigger de BD lo genere usando su función `normalizar_texto()`, garantizando consistencia con el resto de datos ya existentes.
**Archivos:** `profesores/insertar_profesores_db.py`

---

## Resultado scraping profesores

| Departamento | Profesores | Con email | Con despacho | Con categoría | Nombre separado |
|-------------|-----------|-----------|-------------|--------------|----------------|
| LSI | 92 | 92 | 92 | 92 | Sí (coma) |
| DTE | 77 | 77 | 53 | 73 | Sí (coma) |
| CCIA | 34 | 34 | 31 | 31 | No |
| MA1 | 65 | 50 | 0 | 50 | No |
| **Total** | **268** | **253** | **176** | **246** | |

---

## Iteración 6 (2026-04-01): Dockerización, frontend y piloto

### D-024: Dockerización con 3 contenedores (Rasa + Actions + Nginx)

**Problema:** El proyecto requería ejecutar manualmente 3 procesos separados (Rasa server, action server, frontend). Esto dificultaba la reproducibilidad y el despliegue.
**Decisión:** Orquestar con `docker-compose.yml` los 3 servicios:
- `rasa`: imagen oficial `rasa/rasa:3.6.21`, monta modelo/config/domain como volúmenes
- `actions`: build custom desde `Dockerfile.actions` (Python 3.10 + dependencias)
- `frontend`: `nginx:alpine` sirviendo los ficheros estáticos con config personalizada
**Archivos:** `docker-compose.yml`, `Dockerfile.actions`, `frontend/nginx.conf`

### D-025: Migración de `google-genai` a `google-generativeai`

**Problema:** Conflicto irreconciliable de dependencias: `supabase==2.3.0` requiere `websockets<12` (via `realtime`) y `google-genai` requiere `websockets>=13`. Ambos paquetes no pueden coexistir.
**Decisión:** Migrar de `google-genai` (SDK nuevo, basado en websockets) a `google-generativeai` (SDK REST, sin dependencia de websockets). La API cambia mínimamente: `genai.Client(api_key=...)` → `genai.configure(api_key=...)` + `genai.GenerativeModel(modelo)`.
**Alternativas descartadas:**
- Bajar versión de `google-genai`: todas las versiones requieren `websockets>=13`.
- Bajar versión de `supabase`: perdería funcionalidad y crearía otros conflictos.
**Archivos:** `requirements-actions.txt`, `actions/shared/gemini_client.py`, `rag/embeddings.py`

### D-026: Dependencias faltantes en Dockerfile.actions

**Problema:** El build del action server fallaba en runtime por módulos no encontrados: `psycopg2` (usado por `actions/shared/db.py`), `requests` (usado por scrapers en `profesores_data/`), y faltaba copiar el directorio `profesores_data/` (importado por `actions/profesores/actions.py`).
**Decisión:** Añadir `psycopg2-binary==2.9.9` y `requests>=2.31.0` al `requirements-actions.txt`. Añadir `COPY profesores_data/ profesores_data/` y `RUN python -m spacy download es_core_news_md` al `Dockerfile.actions`.
**Archivos:** `requirements-actions.txt`, `Dockerfile.actions`

### D-027: Frontend rediseñado siguiendo la identidad visual de www.us.es

**Problema:** El frontend original era una maqueta mínima sin parecido real con la web de la Universidad de Sevilla.
**Decisión:** Rediseñar `pagina-principal.html` y `pagina-principal.css` replicando la estructura de www.us.es:
- Barra superior roja con enlaces de utilidad (Universidad Digital, Secretaría virtual, etc.)
- Header con logo US + dropdown "Información para mí" + barra de búsqueda
- Navegación principal con 7 items y dropdowns que enlazan directamente a las secciones de www.us.es
- Footer con 4 columnas (contacto, redes sociales, acceso rápido)
- Tipografía Open Sans + Raleway, colores `#be0f2e` (rojo US), `#059f94` (teal)
**Archivos:** `frontend/pagina-principal.html`, `frontend/pagina-principal.css`

### D-028: Logging de conversaciones y feedback via Supabase REST API

**Problema:** Para el piloto con 2-3 usuarios, se necesita saber qué preguntan y recoger feedback, sin modificar la lógica de Rasa (domain, rules, actions).
**Decisión:** Implementar todo desde el frontend (JavaScript), llamando directamente a la REST API de Supabase con la anon key:
- Cada par mensaje-usuario/respuesta-bot se guarda automáticamente en tabla `conversation_log`
- Botón "Feedback" en el footer del chat widget que abre un panel con cuadro de texto, se guarda en tabla `feedback`
- Session ID único generado por sesión de chat para agrupar conversaciones
**Alternativas descartadas:**
- Custom Rasa action para logging: requería modificar domain.yml, rules y reentrenar. Invasivo e innecesario.
- TrackerStore de Rasa con PostgreSQL: configuración compleja, formato poco legible en la BD.
- Envío por email: dependencia de servicio SMTP externo, más complejo.
**Justificación:** La anon key de Supabase es pública por diseño (la seguridad la proporcionan las RLS policies). No se expone ningún secreto en el frontend.
**Tablas nuevas:** `conversation_log` (session_id, user_message, bot_response, created_at), `feedback` (session_id, rating, comment, last_user_message, last_bot_response, created_at)
**Archivos:** `frontend/chatbot-widget.js`, `frontend/pagina-principal.html`, `scripts/create_pilot_tables.sql`

---

## Pendiente

- Re-entrenar modelo NLU (`rasa train`) para activar los intents de horarios y multi-intent
- Testing e2e completo: horarios, seguimiento, multi-intent
- Completar el mapeo de las 6 abreviaturas compartidas de 4º curso (EC, GP, MCG, PID, T, TIS)
- Insertar los 268 profesores en Supabase (`python profesores/insertar_profesores_db.py`)
- NLU + actions para consultas sobre profesores
- Insertar tutorías de CCIA y DTE en tabla `tutorias`
- Crear tablas `conversation_log` y `feedback` en Supabase (ejecutar `scripts/create_pilot_tables.sql`)
- Despliegue en Render (o alternativa) para el piloto
