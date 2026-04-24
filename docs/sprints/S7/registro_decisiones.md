# Registro de decisiones - Sprint 7

## Contexto

Sprint centrado en el **panel de administración** del chatbot: una UI web para gestionar centros, titulaciones, asignaturas, planes docentes, profesores y departamentos desde el navegador, sin tocar la BD a mano. Se reemplazan los scripts puntuales por flujos interactivos de scraping + inserción, y se unifican las fuentes externas (Sevius, us.es) como motores de enriquecimiento.

---

## Iteración 1 (2026-04-17): Estructura del panel admin y fuentes de datos

### D-037: Navegación jerárquica Centro → Titulación → Asignatura

**Problema:** Los datos del chatbot están estructurados en 4 niveles (centro, titulación, asignatura, plan docente) y no había UI. Acceder a la info requería queries SQL directas.
**Decisión:** Panel admin SPA con navegación en cascada que espeja la realidad de la BD: home lista centros como tarjetas, click en centro → titulaciones del centro, click en titulación → asignaturas agrupadas por curso, click en asignatura → modal con detalle + lista de planes docentes. Breadcrumb siempre visible con enlaces para volver.
**Justificación:** Refleja la realidad del dominio (un centro ofrece titulaciones, una titulación contiene asignaturas) y minimiza clics respecto a un menú plano.
**Archivos:** `admin/routes/{centros,titulaciones,asignaturas}.py`, `frontend/admin.{html,js,css}`

### D-038: Sevius como fuente de verdad para centros/titulaciones/asignaturas

**Problema:** La web de la US tiene varios sistemas; hay que elegir cuál consumir para cada entidad. Sevius (`sevius4.us.es`) tiene el listado oficial de programas y proyectos docentes; us.es tiene los planes de estudios.
**Decisión:**
- **Centros**: Sevius (select `<option>` del form principal) → `codigo_sevius` + nombre.
- **Titulaciones**: Sevius filtrado por `codcentro` → `codigo` + nombre.
- **Asignaturas**: Sevius filtrado por `codcentro + titulacion` → `codigo` (7 dígitos) + nombre.
- **Enriquecimiento asignaturas** (curso, créditos, tipología, formación básica): www.us.es/estudiar → plan de estudios del grado, cruzado por código de asignatura.
**Justificación:** Sevius es el origen canónico del código de 7 dígitos que se usa en todos los demás sistemas (horarios, proyectos docentes). us.es es la única fuente fiable para el plan de estudios estructurado.
**Archivos:** `admin/sevius_scraper.py` (`obtener_centros`, `obtener_titulaciones`, `obtener_asignaturas`), `admin/us_scraper.py` (`buscar_grado`, `obtener_plan_estudios`)

### D-039: Flujo "preview primero, insert después" para scraping

**Problema:** Los scripts antiguos hacían scraping + inserción en una sola ejecución. Si algo iba mal (código incorrecto, duplicados), era costoso deshacerlo.
**Decisión:** Todos los scrapers exponen endpoints de preview (`/api/admin/sevius/centros`, `.../titulaciones`, `.../asignaturas`) que solo consultan la fuente externa y devuelven JSON sin tocar la BD. El usuario confirma en la UI antes de disparar el endpoint de `/sync` que inserta. Los `sync` son idempotentes: saltan entidades ya existentes por código.
**Justificación:** Separa "ver qué hay fuera" de "escribir en BD", permitiendo al admin validar antes de modificar estado. Coherente con D-005 (horarios) y D-019 (profesores) en sprints previos.
**Archivos:** `admin/routes/sevius.py` (preview), `admin/routes/{centros,titulaciones,asignaturas}.py` (`/sync`)

---

## Iteración 2 (2026-04-18): Vectorización de planes docentes desde el admin

### D-040: Reutilización del pipeline RAG existente desde el admin

**Problema:** El script `crear_carpetas_asignaturas.py` descubría grupos en Sevius y descargaba PDFs; `rag/pipeline.py` vectorizaba. Ambos eran CLI separados, sin UI ni coordinación.
**Decisión:** Refactorizar la lógica de scraping de grupos y descarga de PDF a `admin/sevius_scraper.py` (`obtener_grupos_asignatura`, `descargar_proyecto_pdf`) y consumirla desde un nuevo endpoint `POST /planes_docentes/vectorize` que orquesta: scrape grupos → descarga PDF a `knowledge_base/proyectos_docentes/<titulacion>/<Nombre (codigo)>/Grupo X/` → llama a `rag.pipeline.procesar_pdf()` (inalterado).
**Justificación:** No reescribir el pipeline RAG (extracción + chunking + embeddings + insert), solo exponerlo vía HTTP. El script CLI sigue funcionando; ahora también hay versión admin.
**Archivos:** `admin/sevius_scraper.py` (scraping helpers), `admin/routes/planes_docentes.py` (orquestación)

### D-041: Modal de selección por asignatura con todos los grupos incluidos

**Problema:** Cada asignatura puede tener 1-4 grupos con planes docentes distintos (ej. IS 4 grupos → 4 PDFs). Si el admin vectoriza una asignatura, ¿quiere todos los grupos o puede elegir?
**Decisión:** La UI deja elegir **qué asignaturas** vectorizar, pero dentro de cada asignatura **todos los grupos se vectorizan siempre**. El modal muestra todas las asignaturas de la titulación como checkboxes; las ya vectorizadas para el curso actual aparecen deshabilitadas con badge "Ya vectorizada" (detectadas por `planes_docentes.estado_rag='completado'` + `curso_academico='2025-26'`).
**Justificación:** Decidir por grupo añade fricción sin valor: la vectorización es barata (~30s por grupo) y tener todos los grupos permite comparar bibliografía/evaluación entre ellos en el chatbot. Saltar duplicados se delega al pipeline RAG existente (hash SHA256 → `sin_cambios`).
**Archivos:** `admin/routes/planes_docentes.py` (`/vectorizables`, `/vectorize`), `frontend/admin.js` (`abrirFormVectorizar`)

### D-042: Scraping síncrono con spinner, no cola de fondo

**Problema:** Vectorizar N asignaturas × M grupos puede tardar minutos (cada PDF: descarga + extracción + embeddings batch). ¿Bloquear la UI o ejecutar en segundo plano?
**Decisión:** Ejecución síncrona con spinner. El POST bloquea hasta terminar y devuelve un resumen por asignatura/grupo. Sin colas, sin job IDs, sin polling.
**Justificación:** Simplicidad. El admin lo ejecuta desde su máquina una vez al inicio del curso; no hay concurrencia real. Si a futuro se nota fricción, se migra a background tasks.
**Riesgo conocido:** Flask dev server es monohilo; durante un `/vectorize` largo, otras peticiones del admin se bloquean. Aceptable en producción detrás de nginx con múltiples workers.
**Archivos:** `admin/routes/planes_docentes.py`

---

## Iteración 3 (2026-04-19): Épica Profesores — pivote a us.es como fuente unificada

### D-043: us.es directorio PDI como fuente canónica (reemplaza scrapers por departamento)

**Problema:** En S6 se implementaron 4 scrapers independientes (LSI, DTE, CCIA, MA1), cada uno con la estructura HTML de su web departamental. Problemas:
- Cobertura desigual: MA1 sin email directo (50/65), CCIA sin apellidos separados, DTE con email ofuscado.
- Cada nueva web de departamento requiere un scraper nuevo.
- La asignación departamental era **hardcodeada** en cada scraper (todos los de CCIA iban a `departamento_id=CCIA`).
- No hay manera de saber si un profe cambió de departamento sin cruzar fuentes.
**Decisión:** Adoptar `https://www.us.es/trabaja-en-la-us/directorio/personal-docente-e-investigador` como **fuente de verdad única** para nombre, departamento, centro, email y categoría. Los scrapers antiguos se conservan en `knowledge_base/profesores_data/` como fuentes de **enriquecimiento** (despacho, teléfono, ORCID, web personal), pero no se ejecutan en el flujo admin nuevo.
**Justificación:** us.es es el registro oficial de PDI (5.028 profesores), con formato homogéneo y URL estable por profesor (`/directorio/<slug>`). El formulario de búsqueda acepta filtros por centro y departamento (`?title_1=&title_2=&page=N`), lo que permite scrapear recortes manejables (~1.500 por centro grande) en vez de los 5k totales.
**Archivos:** `admin/us_directorio_scraper.py` (nuevo)

### D-044: Uso del filtro "Centro" del buscador us.es para acotar alcance

**Problema:** El listado sin filtro tiene 5.028 entradas paginadas → ~250 páginas. Recorrer todo + visitar cada perfil es inviable (horas).
**Decisión:** Siempre buscar con el filtro `title_2=<nombre del centro>` (campo "Centro" del formulario). El servidor devuelve solo los profesores de ese centro (ej. ETSII: 1.583 resultados, ~80 páginas). Para enriquecer un departamento concreto se añade `title_1=<nombre del departamento>` y se filtra aún más.
**Observación:** El filtro de "Centro" es **coincidencia parcial** ("escuela tecnica" o "escuela superior de ingenieria informatica" funcionan). No usa códigos, sino texto. El admin puede ajustarlo en el modal.
**Archivos:** `admin/us_directorio_scraper.py` (`buscar_profesores`)

### D-045: Página del centro como índice de departamentos

**Problema:** us.es no tiene endpoint `/departamentos`. Hay que saber qué deptos pertenecen a qué centro para la navegación Centro → Depto → Profe.
**Decisión:** Scrapear `https://www.us.es/centros/<centro-slug>` y extraer la lista de enlaces `/centros/departamentos/<slug>` bajo la sección "Departamentos ubicados en el centro". Esto da el mapeo centro→deptos autoritativo.
**Ejemplo ETSII:** devuelve 4 deptos (ATC, CCIA, LSI, MA1). **Nótese** que DTE (Tecnología Electrónica) no aparece: pertenece a ETSI (Ingeniería), no a ETSII. En S6 se había incluido DTE por error; en S7 se drop-ea para este scope.
**Archivos:** `admin/us_directorio_scraper.py` (`obtener_departamentos_de_centro`)

### D-046: Campos nuevos en BD: `departamentos.centro_id`, `.codigo_us`, `centros.codigo_us`, `profesores.centro_id`

**Problema:** El schema S6 no conectaba `departamentos` con `centros` (ambos colgaban de `universidades`). Tampoco había slug para re-matching con us.es. Un profesor "sin departamento" no tenía forma de apuntar a su centro.
**Decisión:** 4 columnas nuevas (todas nullable):
```sql
ALTER TABLE departamentos ADD COLUMN centro_id uuid REFERENCES centros(id);
ALTER TABLE departamentos ADD COLUMN codigo_us varchar;
ALTER TABLE centros       ADD COLUMN codigo_us varchar;
ALTER TABLE profesores    ADD COLUMN centro_id uuid REFERENCES centros(id);
```
`codigo_us` almacena el slug de us.es (`ciencias-de-la-computacion-e-inteligencia-artificial`, etc.) para re-identificar la entidad en futuros scrapes sin depender del nombre textual. `profesores.centro_id` permite modelar profes con `departamento_id = NULL` pero pertenecientes a un centro (bucket "Sin departamento" en la UI).
**Justificación:** Un join-table `profesor_centros` era overkill (un profe tiene exactamente un centro en la práctica; los casos multi-centro del directorio listan EIP + ETSII, pero EIP es transversal). Añadir FK directa es suficiente y más simple.
**Alternativas descartadas:**
- Deducir centro desde `departamento` (sin FK): no sirve para profes sin departamento.
- Join table `profesor_centros`: complica queries y UI por un caso que no aporta.
**Archivos:** migración SQL ejecutada manualmente en Supabase (abril 2026)

### D-047: Backfill SQL manual para existentes de ETSII (una vez)

**Problema:** Los profesores y departamentos ya existentes en BD (importados en S6) no tenían `centro_id`. Ejecutar enriquecimiento desde la UI los enlazaría, pero el scrape tarda minutos.
**Decisión:** Script SQL one-shot para vincular los 4 deptos ETSII (CCIA, LSI, MA1, ATC) a su centro, fijar sus `codigo_us` desde la lista conocida de us.es, y propagar `centro_id` a todos los profesores cuyo `departamento_id` apunta a uno de ellos. DTE se deja sin vincular (se droppea del scope).
```sql
UPDATE departamentos SET centro_id = (SELECT id FROM centros WHERE codigo='ETSII'),
                         codigo_us = CASE siglas ... END
WHERE siglas IN ('CCIA','LSI','MA1','ATC');

UPDATE centros SET codigo_us='escuela-tecnica-superior-de-ingenieria-informatica'
WHERE codigo='ETSII';

UPDATE profesores p SET centro_id=d.centro_id FROM departamentos d
WHERE p.departamento_id=d.id AND p.centro_id IS NULL AND d.centro_id IS NOT NULL;
```
**Justificación:** Restaura la consistencia de ~250 profesores S6 en segundos sin re-scrapear. Los enriquecimientos futuros via UI operarán sobre datos ya consistentes.
**Archivos:** SQL ejecutado manualmente; documentado aquí para reproducibilidad.

### D-048: Upsert por `email` con fallback a `nombre_normalizado`

**Problema:** Al cruzar datos de us.es con profes ya existentes (S6), hay que decidir cuándo crear vs. actualizar. El nombre en us.es va todo en mayúsculas sin estructura ("ABRAHAM MARQUEZ ALCAIDE"); los existentes pueden tener nombre/apellidos separados por coma.
**Decisión:** Matching en 2 pasos:
1. Buscar por `LOWER(email) = LOWER(<email us.es>)`. us.es casi siempre da email → alto recall.
2. Si no hay match, buscar por `nombre_normalizado = normalizar(nombre_completo_us)`.
3. Si ninguno matchea → INSERT nuevo registro.
**Política de actualización:** Nunca sobrescribir campos ya poblados con NULL/vacío del scrape. Se usa `COALESCE` para cada campo: `SET despacho = COALESCE(despacho, %s)`. Esto preserva el detalle rico de los scrapers S6 (despacho, teléfono, ORCID, web personal) incluso cuando us.es no lo da.
**Archivos:** `admin/routes/profesores.py` (`_upsert_profesor`)

### D-049: Separación heurística nombre/apellidos para profes nuevos

**Problema:** us.es da el nombre como "NOMBRE APELLIDO1 APELLIDO2" en mayúsculas, sin coma. En S6 (D-021) se decidió no separar para CCIA/MA1 por la misma razón. Pero ahora queremos separar siempre que se pueda para que `nombre_completo = apellidos || ', ' || nombre` quede bien.
**Decisión:** Heurística ligera en el scraper:
- 1 palabra → nombre completo, apellidos vacío
- 2 palabras → primera = nombre, segunda = apellido
- 3 palabras → primera = nombre, 2-3 = apellidos
- 4+ palabras → 1-2 = nombre compuesto, resto = apellidos
Se aplica **solo al crear** registros nuevos. Registros existentes con separación previa (S6, LSI/DTE con coma) no se tocan (`COALESCE(NULLIF(%s,''), nombre)`).
**Limitación conocida:** Falla con apellidos compuestos tipo "DE LA FUENTE" o "DEL CASTILLO". Aceptable: el impacto es cosmético (el campo `nombre_completo` sale raro), las búsquedas usan `nombre_normalizado` que es robusto a esto.
**Archivos:** `admin/us_directorio_scraper.py` (`_split_nombre_apellidos`)

### D-050: Auto-creación de departamentos ausentes

**Problema:** Durante el enriquecimiento, un profe puede declarar un departamento que no está en la BD (ej. ingeniería química en un scrape de ETSI). ¿Fallar y pedir al admin crearlo manualmente, o auto-crear?
**Decisión:** Auto-crear. Si `_upsert_departamento` recibe un slug de us.es que no existe en BD (ni match por `codigo_us` ni por nombre), hace INSERT con `siglas` = iniciales del nombre (primer char de cada palabra, máx 10 chars), `codigo_us` = slug, `centro_id` = centro del scrape.
**Justificación:** El admin nunca se bloquea. Si las siglas autogeneradas son feas, las edita a mano después. Mejor tener el profe vinculado correctamente que perder el dato por una pre-condición.
**Archivos:** `admin/routes/profesores.py` (`_upsert_departamento`)

---

## Iteración 4 (2026-04-19): UI del panel de profesores

### D-051: Vista jerárquica Centro → Departamento → Profesor, con bucket "Sin departamento"

**Problema:** La pestaña "Profesores" en S6 era una tabla plana con filtro de departamento en dropdown. Mal UX: no se ve la estructura organizativa, no hay forma de añadir enriquecimientos, y los profes sin departamento (import erróneo, directorio us.es) no aparecían en ninguna vista.
**Decisión:** Navegación que espeja D-037:
- **Nivel 1:** Tarjetas de centros (reutiliza `GET /centros`). Cada tarjeta muestra nº de profesores y nº de titulaciones.
- **Nivel 2:** Tarjetas de departamentos del centro + **tarjeta especial "Sin departamento"** con fondo rayado (`depto-sin` CSS) si hay profes con `departamento_id IS NULL AND centro_id = <este>`.
- **Nivel 3:** Tabla de profesores del departamento (o del bucket "Sin departamento") con click a modal de detalle.
- **Botón "Enriquecer desde us.es"** visible en Nivel 2 (enriquece el centro entero: descubre deptos + scrape PDI) y en Nivel 3 (enriquece solo ese departamento).
**Archivos:** `frontend/admin.js` (`loadProfesores`, `loadDepartamentosCentro`, `loadProfesoresDepto`, `loadProfesoresSinDepto`), `frontend/admin.css` (`.entity-card.depto-sin`)

### D-052: Modal de enriquecimiento con slug editable

**Problema:** El slug del centro en us.es (`escuela-tecnica-superior-de-ingenieria-informatica`) es largo y no evidente. Hardcodearlo acopla el admin a ETSII; pedirlo siempre al admin es molesto; generarlo del nombre funciona pero puede fallar.
**Decisión:** El modal de enriquecimiento precarga el slug desde `centros.codigo_us` si existe, y si no, lo genera a partir del nombre con una normalización JS simple (quitar acentos, lower, sustituir no-alphanum por `-`). El admin puede editarlo antes de lanzar. Tras un enriquecimiento exitoso, el slug se guarda en `centros.codigo_us` para no preguntar la próxima vez.
**Justificación:** Convierte la primera ejecución en "edita una vez, funciona para siempre", sin bloquear al admin si el centro no está aún registrado en us.es con slug canónico.
**Archivos:** `frontend/admin.js` (`abrirEnrichCentro`, `normalizarSlug`)

---

## Resultado final

### Endpoints nuevos del admin (Sprint 7)

| Recurso | Método | Ruta | Función |
|---------|--------|------|---------|
| Centros | POST | `/centros` | Crear centro desde preview Sevius |
| Centros | POST | `/centros/<id>/enrich_profesores` | Scrape us.es + upsert deptos/profes |
| Centros | DELETE | `/centros/<id>` | Borrar centro y dependientes |
| Titulaciones | POST | `/titulaciones/sync` | Sync desde Sevius |
| Asignaturas | POST | `/asignaturas/sync` | Sync desde Sevius |
| Asignaturas | POST | `/asignaturas/enrich` | Enriquecer con us.es plan estudios |
| Asignaturas | DELETE | `/asignaturas/<id>` | Borrar asignatura |
| Planes docentes | GET | `/planes_docentes/vectorizables` | Lista con flag `ya_vectorizada` |
| Planes docentes | POST | `/planes_docentes/vectorize` | Scrape grupos + descarga + vectoriza |
| Profesores | GET | `/centros/<id>/departamentos` | Lista deptos + bucket "Sin depto" |
| Profesores | POST | `/departamentos/<id>/enrich_profesores` | Enrich de un depto concreto |
| Sevius preview | GET | `/sevius/{centros,titulaciones,asignaturas}` | Sin tocar BD |

### Fuentes de datos consolidadas

| Entidad | Fuente primaria | Enriquecimiento |
|---------|-----------------|-----------------|
| Centros | Sevius (form select) | us.es centro page (para `codigo_us`) |
| Titulaciones | Sevius (form select por centro) | — |
| Asignaturas | Sevius (form select por titulación) | us.es /estudiar (curso, créditos, tipología) |
| Planes docentes | Sevius form POST (PDFs) | — |
| Departamentos | us.es /centros/`<centro>` | auto-creación si falta |
| Profesores | us.es /directorio PDI | scrapers S6 (despacho, teléfono, ORCID) |

### Migración de datos S6 → S7

- 4 columnas añadidas (migración SQL manual en Supabase).
- Backfill SQL de `centro_id` para los 4 deptos ETSII (CCIA, LSI, MA1, ATC) y sus profesores existentes.
- DTE sale del scope (pertenece a ETSI, no ETSII); sus 77 profes quedan con `centro_id = NULL` hasta que se añada ETSI como centro gestionado.

---

## Iteración 5 (2026-04-23): Refactor de Actions tras auditoría con feedback del piloto

### D-053: Split del intent `consulta_asignatura_especifica` en dos intents (ficha vs horario)

**Problema:** El Action `ActionConsultaEspecifica` mezclaba dos flujos en cascada: ficha/plan docente (evaluación, temario, profesores, bibliografía…) y consulta de horario/aula de la asignatura. La detección entre flujos vivía en una lista hardcodeada `_PALABRAS_HORARIO_ASIGNATURA` (~30 strings en español). Paralelamente, `ActionConsultaHorario` (módulo horarios) reenviaba a `ActionConsultaEspecifica` cuando detectaba una asignatura en el mensaje — provocando **doble detección** y **ciclo de imports** entre los módulos.
**Decisión:** Separar a nivel de NLU:
- Nuevo intent `consulta_horario_asignatura` con ~70 ejemplos movidos desde `consulta_asignatura_especifica` (todas las preguntas sobre aula, día, hora, laboratorio de una asignatura concreta).
- Nuevo Action `ActionConsultaHorarioAsignatura` en `asignaturas/actions.py` que importa las utilidades de consulta SQL desde `horarios/` (import en una sola dirección: asignaturas → horarios).
- Eliminación de la lista `_PALABRAS_HORARIO_ASIGNATURA` y del bloque de reenvío en `ActionConsultaHorario`.
**Justificación:** Rasa ya clasificaba correctamente los intents con el modelo entrenado; la detección manual por keywords era deuda heredada de cuando el NLU no distinguía bien. El split elimina ~130 líneas de código duplicado/obsoleto y rompe el ciclo de imports.
**Archivos:** `data/nlu/asignaturas.yml` (nuevo intent), `data/rules.yml` (nueva regla), `data/stories.yml` (flujos cross-domain actualizados), `domain.yml`, `actions/asignaturas/actions.py`, `actions/horarios/actions.py` (bloque de reenvío borrado)

### D-054: Bloqueo de alias de letra única en `_expandir_alias`

**Problema:** Los alias `t`, `c`, `e` colisionan con asignaturas reales (Teledetección, Criptografía, Estadística) cuando el usuario los menciona en contextos no relacionados. Documentado en el piloto: "letra T del DNI" → Teledetección, "cristiano ronaldo" → match con `c` → Criptografía.
**Decisión:** En `_expandir_alias` (text_to_sql), si el input tiene longitud 1, devolver el nombre original sin expandir. El pipeline downstream decide qué hacer (pedir más contexto, fuzzy, etc.). Se conserva el parche ya existente en horarios para "letra del DNI" como refuerzo explícito.
**Justificación:** Los aliases de una letra son intrinsecamente ambiguos en lenguaje natural; prefiere "no encontré X" a "interpreté mal tu mensaje". Coste: 3 líneas.
**Archivos:** `actions/asignaturas/text_to_sql.py`

### D-055: Endurecimiento del fuzzy cutoff en `ActionCambiarContexto`

**Problema:** El cutoff 70 del fuzzy sobre `TITULACION_MAP` era demasiado permisivo. "Ingeniería de la Salud" matcheaba con "Ingeniería del Software" → GII-IS (observado en el piloto, interacción 52).
**Decisión:** Subir el cutoff a 85 y añadir lista de palabras bloqueantes (`salud`, `medicina`, etc.) que invalidan el match incluso si el score supera el umbral.
**Justificación:** Coste mínimo con impacto en un fallo reproducible del piloto. Mantener `TITULACION_MAP` hardcodeado se justifica en D-056.
**Archivos:** `actions/contexto/actions.py`

### D-056: `ALIAS_ASIGNATURAS` y `TITULACION_MAP` como datos de dominio estables

**Problema:** Durante la auditoría se evaluó si los diccionarios hardcodeados de aliases (ASIGNATURAS: ~200 entradas, TITULACIÓN: ~20) deberían generarse automáticamente desde la BD para escalar a otras titulaciones.
**Decisión:** Mantenerlos como están. Se consideran **datos de dominio**, no heurísticas:
- "DP1", "ADDA", "PSG2" son los aliases oficiales que usan los estudiantes de Sevilla. Son una fuente de verdad determinista, no una aproximación.
- Ya existe fallback dinámico: `_parece_acronimo` + `_buscar_por_acronimo_en_bd` genera aliases automáticos desde nombres de BD cuando el alias manual no existe.
- Escalabilidad: añadir una titulación nueva requiere cargar asignaturas en BD (automático) + actualizar `TITULACION_MAP` (manual, ~5 entradas). Aceptable para el TFG.
**Archivos:** `actions/shared/config.py` (sin cambios, decisión documentada)

### D-057: Multi-asignatura en `ActionConsultaHorarioAsignatura` — fallback por diseño

**Problema:** `_extraer_multiples_nombres` solo detecta múltiples asignaturas si **todas aparecen como alias** del diccionario. Preguntas como "horario de diseño y pruebas 1 y fundamentos de programación" (nombres completos) no se reconocen como multi — el pipeline resuelve una sola y el LLM puede alucinar datos de la otra.
**Decisión:** No extender la detección multi-asignatura a nombres completos en el Action de horario. En su lugar, cuando `_extraer_multiples_nombres` devuelve ≥2 resultados, `ActionConsultaHorarioAsignatura` responde pidiendo desambiguar:

> "Por ahora solo puedo mostrarte el horario de una asignatura a la vez. ¿De cuál quieres empezar: **DP1** o **FP**?"

Se evaluaron tres alternativas:
1. **NLU con múltiples entidades:** frágil — el extractor español ya falla en separar "diseño y pruebas 1 y fundamentos" correctamente.
2. **Split del texto por conectores `y`/`e`/`,`:** colisiona con nombres que contienen "y" en su propio título (p.ej. "Diseño **y** Pruebas").
3. **LLM extractor:** añade latencia a un flujo que ya hace múltiples llamadas al modelo.
**Justificación:** Prioridad a **precisión sobre cobertura**. Es preferible responder bien sobre una asignatura que arriesgar una respuesta inventada sobre dos. El comportamiento actual (desambiguar explícitamente) se defiende como decisión de diseño, no como limitación. En `ActionConsultaEspecifica` sí se mantiene la detección multi basada en aliases — ahí el RAG absorbe la ambigüedad mejor y los casos observados en el piloto (p.ej. "¿cómo se evaluaban DP1 y PSG2?") funcionan correctamente.
**Archivos:** `actions/asignaturas/actions.py` (`ActionConsultaHorarioAsignatura.run`)

### D-058.b: RAG sin filtro por sección — la sección es solo señal de reranking

**Problema:** En el piloto, "el profesorado de algebra" devolvía "el plan docente indica que las clases se realizarán en inglés" en vez del listado de profesores. Diagnóstico: el retrieval aplicaba `WHERE seccion = 'profesorado'` en la búsqueda vectorial. Los nombres reales de profesores ("ANDRES ARMARIO SAMPALO…") estaban en chunks etiquetados como `bibliografia` o `evaluacion_grupo` por el chunker actual (que usa `_detectar_seccion` tomando la *última* cabecera encontrada en cada chunk, criterio frágil cuando dos secciones caen en el mismo trozo).

**Decisión:** Desactivar el filtro por sección en la query SQL. La búsqueda vectorial trae los N chunks más similares sin restricción. La sección se usa **solo como señal de reranking**: bonus positivo suave (+0.12 a +0.15) si la sección etiquetada coincide con el tipo de consulta, sin penalizaciones negativas. Se eliminó el `-0.30` que penalizaba `bibliografia` en consultas de profesorado, porque precisamente enmascaraba los chunks con nombres mal etiquetados.

**Alternativas descartadas:**
1. **Chunking por secciones (partir primero por cabeceras)**: arreglo raíz pero asume estructura PDF estable. El formato del proyecto docente de ETSII es consistente, pero otras escuelas/universidades pueden variar, y un fallo silencioso de parsing perdería chunks enteros.
2. **Etiquetado de sección con LLM** (pedir al modelo que marque cada chunk con una frase-descripción): coste y latencia altos en ingesta (~20k llamadas para reindexar todos los grados), etiquetas no deterministas, y no arregla la mezcla cuando un chunk tiene contenido de dos secciones — la IA sigue teniendo que elegir una.

**Justificación:** La decisión pragmática es "confiar en el embedding y usar la sección solo como señal débil". El coseno de `gemini-embedding-001` es lo bastante bueno para encontrar el chunk con nombres propios aunque su etiqueta de sección esté mal. Es robusto a futuros cambios de formato de PDF y no añade dependencias ni coste de ingesta. Coste total: 1 función eliminada + ajuste de pesos + un bloque condicional limpiado (~40 líneas menos en `rag/buscar.py`).

**Archivos:** `rag/buscar.py` (eliminada `_seccion_preferida`; `RERANK_WEIGHTS` rebalanceado)

### D-060: Poblar `profesor_asignatura` desde us.es (docencia estructurada)

**Problema:** La tabla `profesor_asignatura` estaba vacía y el chatbot no podía responder preguntas como "¿A qué hora son las tutorías de Administración de Empresas?" — requieren saber qué profesores imparten una asignatura para cruzar con la tabla `tutorias`. Las alternativas eran:
- Seguir tirando del RAG runtime para cada turno (3-4 llamadas LLM por consulta, alucinaciones conocidas P3 del piloto, latencia alta).
- Poblar `profesor_asignatura` offline con datos deterministas y hacer JOIN en SQL en runtime (1 query).

**Decisión:** Poblar offline desde `www.us.es/trabaja-en-la-us/directorio/<slug>`. Cada perfil PDI tiene una sección "Asignaturas que imparte" con una lista `<li><a href="/estudiar/.../grado-en-xxx/CODIGO">nombre</a></li>`. El **código** es el mismo `asignaturas.codigo` que tenemos en BD, así que el match es exacto — no fuzzy. El href indica también la titulación, así que se puede filtrar por grado.

**Sub-problema descubierto:** Los profes existentes (importados en S6 con scrapers por departamento: LSI, DTE, CCIA, MA1) tienen `enlace_perfil` apuntando a `departamento.us.es/lsi/profesor/...`, `cs.us.es/perfiles/...` o `investigacion.us.es/sisius/...` — **ninguno** apunta al directorio PDI de us.es. El scrape de docencia necesita el slug us.es. 0/95 profes ETSII tenían enlace us.es.

**Solución en dos pasos:**

1. **`POST /api/admin/centros/<id>/refresh_enlaces_us`**: para cada profe del centro sin enlace us.es, busca en el directorio PDI por `nombre_completo` y guarda el slug si encuentra exactamente 1 coincidencia fiable.
2. **`POST /api/admin/titulaciones/<id>/sync_docencia`**: para cada profe con enlace us.es, scrapea "Asignaturas que imparte" y hace upsert en `profesor_asignatura` solo para las asignaturas que pertenecen a la titulación elegida (filtro por `codigo`).

**Detalles de implementación:**

- **No usamos el filtro `centro_nombre` de la API us.es** aunque está disponible: ensucia el resultado incluyendo entradas placeholder como "PERSONAL DE ADMINISTRACIÓN Y SERVICIOS" como coincidencia. Se filtran por lista negra de slugs y se confía en la búsqueda por nombre.
- **UNIQUE constraint `(profesor_id, asignatura_id, curso_academico, grupo)`** ya existía en `profesor_asignatura`. us.es no da grupo, así que insertamos con `grupo = NULL`. En Postgres `NULL ≠ NULL` en UNIQUE, así que un `INSERT` ciego generaría duplicados; por eso se comprueba con `SELECT ... WHERE grupo IS NULL` antes de insertar.
- **Flujo síncrono con spinner** (coherente con D-042). ~95 perfiles × 0.3s pausa ≈ 30s por sync. Sin colas ni polling.
- **Botones UI**:
  - "Refrescar enlaces us.es" en la vista Profesores → Centro (junto a "Enriquecer desde us.es").
  - "Cargar docencia" en la vista Asignaturas → Titulación (junto a "Vectorizar planes docentes" y "Enriquecer datos").

**Alternativas descartadas:**
- **Pipeline RAG runtime** ([`_resolver_profesor_via_rag` en `actions/profesores/actions.py`](../../../actions/profesores/actions.py)): funciona pero trae alucinaciones (autores de bibliografía clasificados como profesorado, int. 24 del piloto) y añade 3-4 llamadas LLM por turno.
- **Añadir docencia al `enrich_profesores` existente** (D-043): mezcla datos estables (email, despacho, categoría) con datos de ciclo anual (docencia). Refrescar docencia cada curso obligaría a re-scrapear todo. Separar permite pipelines independientes.
- **Un único endpoint combinado "refresh + sync"**: por si el `refresh_enlaces` falla, no perdemos la oportunidad de sincronizar los que sí tienen enlace.

**Escalabilidad:** Añadir una titulación nueva es automático — el endpoint `sync_docencia` solo necesita `titulacion_id` y opera contra el mapa `{codigo → asignatura_id}` de esa titulación. No hay código específico por grado.

**Archivos:**
- `admin/us_directorio_scraper.py` (nueva función `obtener_docencia(slug)`)
- `admin/routes/profesores.py` (2 endpoints nuevos: `refresh_enlaces_us`, `sync_docencia`)
- `frontend/admin.js` (2 modales: `abrirRefreshEnlaces`, `abrirCargarDocencia` + 2 botones en vistas existentes)

### D-061: Tutorías fuera del scope del TFG — redirección al email del profesor

**Problema:** La tabla `tutorias` está vacía. Preguntas como "a qué hora son las tutorías de DP1" ejecutaban una SQL generada por LLM con JOIN sobre `tutorias`, devolvían 0 filas y el bot respondía *"No encontré profesores asignados a Diseño y Pruebas I. Es posible que aún no se hayan cargado las asignaciones."* — mensaje engañoso porque los profesores SÍ están en `profesor_asignatura` (cargados por D-060); lo que falta son los horarios de tutorías.

**Por qué no se carga `tutorias`:** el directorio PDI de us.es **no contiene** horarios de tutorías. Las fuentes son las webs departamentales (LSI, DTE, CCIA, MA1), cada una con formato distinto — 4 scrapers específicos que dependen del HTML de cada depto. Mantener esa infraestructura solo para tutorías queda fuera del scope de cierre del TFG.

**Decisión:** Cuando la SQL devuelve 0 filas y hay contexto (asignatura o profesor), reintentar con un **fallback sin JOIN sobre `tutorias`**. Si ese segundo intento devuelve profesores, significa que existen datos básicos pero no tutorías. En ese caso el LLM de respuesta recibe un flag `tutorias_no_disponibles=True` que lo instruye a:
- No inventar horarios ni ubicaciones de tutorías.
- Indicar claramente que no se dispone del dato.
- Sugerir contactar al profesor por email (destacándolo).

**Justificación:**
- **Honestidad sobre inventar**: preferible "no lo sé, escríbele a X" que una respuesta fabricada.
- **Cero deuda técnica adicional** — los scrapers departamentales se dejan como están en `knowledge_base/profesores_data/` sin integrarlos al flujo admin.
- **Escalable**: si en el futuro se puebla `tutorias` (manual o via scraper), el flag se desactivará automáticamente al no dispararse el fallback.
- **Defendible**: el bot ofrece el camino real para obtener el dato (el email del profesor, ya enriquecido por D-043).

**Alternativas descartadas:**
- **Scrapear las 4 webs departamentales de ETSII**: coste alto (4 scrapers con código distinto), baja robustez, solo aporta tutorías que el profesor ya publica en su email de firma.
- **Responder con un mensaje hardcodeado "no tenemos tutorías"**: peor UX, el LLM ya tiene instrucciones claras vía prompt y adapta el fraseado al contexto de la pregunta.
- **Detectar "tutorías" por keywords en el Action**: no escala y hereda los problemas de la detección textual rígida que hemos ido eliminando en esta iteración.

**Archivos:** `actions/profesores/actions.py` (fallback SQL sin tutorías + flag al LLM), `knowledge_base/profesores_data/text_to_sql.py` (parámetro `tutorias_no_disponibles` en `generar_respuesta_natural`).

### D-062: "Profesores de X" al intent `consulta_profesor` — pipeline SQL → RAG como red de seguridad

**Problema:** Las preguntas "profesores de DP1", "el profesorado de EGC", "quién da FP", etc., estaban entrenadas en el intent `consulta_asignatura_especifica` y por tanto entraban por `ActionConsultaEspecifica`, que para esas preguntas dispara directamente RAG sobre el plan docente. Esto provocaba:
- Información inventada (autores de bibliografía interpretados como profesorado — int. 24 del piloto y reciente confirmación con "los profesores de egc" → Kästner/Saake).
- Cero uso de la tabla `profesor_asignatura` que acabábamos de poblar en D-060.
- Respuestas inconsistentes entre "horario de DP1" (via `profesor_asignatura`) y "profesores de DP1" (via plan docente RAG).

**Decisión:** Mover al intent `consulta_profesor` **todos los ejemplos** de NLU que pidan profesores/docencia de una asignatura, incluyendo:
- Ejemplos con entidad explícita: "profesores de X", "el profesorado de X", "quién da X", "quién imparte X", "quién coordina X", variantes largas, variantes con grupo.
- Follow-ups sin entidad: "y el profesorado", "y quién la imparte", "quién da esa asignatura" — antes eran follow-ups de `consulta_asignatura_especifica` y disparaban RAG. Ahora son follow-ups de `consulta_profesor` y el Action los resuelve contra `profesor_asignatura` usando el slot `ultimo_nombre_asignatura`.

**Pipeline resultante en `ActionConsultaProfesor`**:

1. **Routing inicial** — `_clasificar_necesita_rag` decide si la pregunta va directa al RAG. Dispara RAG si:
   - La pregunta menciona términos que corresponden a datos no modelados en la tabla: `coordinador`, `coordinadora`, `coordina`, `suplente`, `suplentes`. Es un **mapeo determinista término→fuente**, no heurística de intención: estos roles no existen en el schema relacional.
   - Hay nombre de profesor de 1 palabra ≤8 caracteres (ambigüedad típica de nombre de pila que el plan docente desambigua).
2. **SQL principal** — text-to-SQL con JOIN `profesor_asignatura + tutorias + profesores`.
3. **SQL sin tutorías** — si devuelve 0 (tabla `tutorias` vacía o sin match), reintenta sin ese JOIN. Si encuentra profesores, marca `tutorias_no_disponibles=True` y el LLM redirige al email (D-061).
4. **RAG del plan docente como red de seguridad** — último recurso, solo si la asignatura no está cargada en `profesor_asignatura`. Extrae nombres del PDF y hace match contra tabla `profesores`.

El RAG ya no es el flujo principal — es el fallback. Coincide con el criterio establecido: **usar datos estructurados siempre que existan, reservar RAG para lo que no se puede modelar en tablas**.

**Nota sobre el cortocircuito de palabras:** se consideró un clasificador LLM semántico para cubrir paráfrasis ("responsable de X", "quién lleva X") pero se descartó por simplicidad: añadía latencia y no cubría casos reales observados. Si aparecen paráfrasis recurrentes se extiende la lista de términos o se introduce el clasificador entonces.

**Justificación:** Separación limpia de intents por semántica de la pregunta: "información sobre la asignatura X" → ficha/plan docente; "profesores de la asignatura X" → tabla relacional. El argumento para memoria TFG es defendible: *"la tabla `profesor_asignatura` es fuente primaria (datos us.es oficiales). El pipeline RAG actúa como fallback cuando la asignatura no está cargada; desambigua profesores con nombres parciales ('Belén que da FP') y cubre asignaturas cuya docencia no aparece en el directorio PDI"*.

**Alternativas descartadas:**
- **Dejar el intent mezclado y delegar desde `ActionConsultaEspecifica`**: introduce un router implícito en medio del Action (más complejidad lógica, más difícil de seguir).
- **Exclusivamente SQL sin RAG**: pierde cobertura cuando `profesor_asignatura` no se ha cargado para una asignatura (caso que se da con asignaturas sin docencia declarada en us.es).

**Archivos:**
- `data/nlu/asignaturas.yml` (~40 ejemplos eliminados)
- `data/nlu/profesores.yml` (mismos ~40 ejemplos añadidos + nuevos follow-ups)
- `actions/profesores/actions.py` (RAG como tercer fallback tras SQL + SQL-sin-tutorías)

### D-063: Filtro por titulación uniforme en los 3 módulos

**Problema:** Los módulos `asignaturas` y `horarios` (a) llamaban a `comprobar_titulacion` al inicio de cada Action para pedir la titulación con botones si el usuario no la había elegido, y (b) inyectaban `titulacion_id` en cada SQL generada. `ActionConsultaProfesor` hacía las dos cosas a medias:
- Leía el slot pero no cortaba si era `None` — el Action corría igual.
- El text-to-SQL no filtraba por titulación — el prompt ni siquiera exponía la columna `asignaturas.titulacion_id`.

Con un solo grado cargado en `profesor_asignatura` el bug no se veía, pero al cargar GII-TI o GII-IC, "profesores de Estadística" podría mezclar profes de varias titulaciones.

**Decisión:** Dos cambios simultáneos para dejar los 3 módulos coherentes:

1. **Chequeo de titulación** — `comprobar_titulacion(tracker, dispatcher)` al inicio de `ActionConsultaProfesor`. Mismo patrón que los otros Actions.
2. **Filtro de titulación en SQL** — vía prompt, no vía post-proceso:
   - El schema del prompt ahora expone `asignaturas.titulacion_id` y añade la tabla `titulaciones`.
   - Nueva instrucción (solo se añade si llega `contexto_titulacion`): "cuando hagas JOIN con `asignaturas`, haz también JOIN con `titulaciones` filtrando por `t_tit.codigo = '<código>'`". El código va literal en el prompt porque es controlado por nosotros y así simplifica los parámetros.
   - El fallback SQL (`_fallback_sql` para "profesores por asignatura") también acepta `contexto_titulacion` y añade el JOIN con `titulaciones` cuando se le pasa.
   - El Action propaga `titulacion` a `generar_sql_profesor` y al `_fallback_sql` "sin tutorías".

**Justificación:** Inyectar el filtro vía prompt (no post-proceso como en `asignaturas`) es más simple aquí: sola llamada, el LLM entiende el schema, y la instrucción es determinista cuando temperature=0. No necesitamos el regex magic de `_inyectar_filtro_titulacion` porque no tenemos queries heredadas que adaptar.

**Alternativas descartadas:**
- **Post-proceso tipo `_inyectar_filtro_titulacion`**: demasiado invasivo para un prompt que ya se genera con instrucciones específicas.
- **Dejar solo el chequeo y el filtro como pendiente**: tras analizarlo resultó ser ~15 líneas, no un proyecto.

**Archivos:** `actions/profesores/actions.py` (~6 líneas), `knowledge_base/profesores_data/text_to_sql.py` (schema + instrucción condicional + rama de fallback).

### D-064: RAG de profesores como vectorial puro — sin double-check en BD

**Problema:** El pipeline establecido en D-062 tenía dos piezas que no envejecieron bien tras el despliegue:

1. **Clasificador LLM `_clasificar_necesita_rag`**: decidía en runtime si entrar al flujo RAG. Coste de latencia (una llamada extra por turno) y falsos negativos cuando el nombre del profesor era ambiguo sin ser corto.
2. **RAG "por keyword + cross-check en BD"** (antiguo `_resolver_profesor_via_rag`): usaba `_buscar_por_keywords` (no vectorial, no usa embeddings, no se beneficia del reranking D-058.b), y después cruzaba el texto recuperado contra la tabla `profesores` filtrando candidatos cuyo `nombre_normalizado` apareciera literalmente en los chunks. Resultado típico en producción (log de ejemplo):

   ```
   ⚠ RAG: ningún profesor de BD aparece en los chunks
   ⚠ RAG no dio resultados, cayendo a text-to-SQL
   ```

   El cruce descartaba respuestas válidas cuando el chunk contenía el nombre pero en otro formato (acentos, orden, abreviaturas).

**Decisión:** Simplificar el flujo RAG del Action de profesores a **búsqueda vectorial pura con reranking** (reutilizando `buscar_en_plan_docente`, mismo patrón que `ActionConsultaEspecifica`), y **eliminar el cross-check contra la tabla `profesores`**. El LLM de respuesta renderiza directamente desde los chunks.

**Estructura resultante del `run()`**:

1. **Atajo determinista** — si la pregunta menciona `coordinador`/`coordinadora`/`coordina`/`coordinan`/`suplente`/`suplentes` **y** la asignatura quedó resuelta aguas arriba → va directo al flujo RAG vectorial. No pasa por SQL. El mapeo término→fuente es el mismo de D-062 pero ahora es el único disparador explícito de RAG.
2. **Flujo SQL normal** (text-to-SQL + fallback por apellido + fallback sin JOIN tutorías) para el resto de preguntas. Sin cambios respecto a D-060/D-061/D-063.
3. **RAG vectorial como red de seguridad** — si la SQL devuelve cero filas y tenemos `codigo_asignatura`, dispara `buscar_en_plan_docente` y responde con un prompt específico para chunks (mismo estilo que `_generar_respuesta_rag` del módulo asignaturas).

Se elimina del Action:
- `_clasificar_necesita_rag` (clasificador LLM).
- La versión antigua de `_resolver_profesor_via_rag` basada en `_buscar_por_keywords` + consulta SQL contra `profesores` + filtrado por aparición textual.

Se añaden tres helpers mínimos en `actions/profesores/actions.py`:
- `_pregunta_menciona_rol_rag(pregunta)` — chequeo de keywords determinista.
- `_rag_chunks_plan_docente(pregunta, codigo, nombre)` — envoltorio de `buscar_en_plan_docente` con logs.
- `_generar_respuesta_rag(pregunta, chunks, nombre)` — prompt espejo del de asignaturas (reglas, formato, aviso sobre `[bibliografia]`).

**Justificación:**

- **Evitar el LLM classifier**: el atajo por keywords ya cubría el 100% de los casos en que "coordinador/suplente" es disparador real; el clasificador añadía latencia (+1 turno al LLM) sin mejorar cobertura.
- **Vectorial > keyword**: la búsqueda vectorial con reranking por sección (D-058.b) está mejor probada, produce logs consistentes con el resto del sistema ("Rerank (profesorado)"), y aprovecha los embeddings ya pagados durante la ingesta.
- **No cruzar con BD**: filtrar los chunks por "tiene que aparecer un nombre que también esté en `profesores`" era defensivo pero introducía falsos negativos. El prompt del LLM ya incluye la regla de D-058.b ("los nombres en `[bibliografia]` son AUTORES, no profesores"); el filtrado duro extra era redundante y más frágil que la instrucción semántica. Si el usuario quiere datos de contacto del profesor (email, despacho, tutorías), formula una segunda pregunta y entra por el flujo SQL normal — que sigue siendo el primario.
- **Alineación con `ActionConsultaEspecifica`**: ambas acciones ahora usan la misma función de búsqueda y el mismo patrón de render desde chunks. Menos superficie divergente que mantener.

**Alternativas descartadas:**

- **Mantener el clasificador LLM, solo cambiar keyword→vectorial**: no justificaba la latencia extra una vez que el atajo por keywords cubre los casos reales observados.
- **Devolver chunks como dicts con forma de profesor y reutilizar `generar_respuesta_natural`**: pintar "pseudo-rows" (solo `nombre`/`apellidos` sin email/despacho) confundía al formateador, que asumía campos de BD. Más limpio usar un prompt específico de chunks.
- **Hacer el RAG vectorial también el flujo principal (no solo fallback)**: el feedback del usuario fue explícito sobre preservar el pipeline SQL existente. La tabla `profesor_asignatura` poblada en D-060 sigue siendo la fuente primaria.

**Relación con decisiones previas:**

- Reemplaza la implementación de D-062 para el flujo RAG sin alterar su tesis (SQL primario, RAG como red de seguridad).
- Preserva D-061 (redirección al email cuando no hay tutorías) y D-063 (filtro por titulación en el SQL).
- Consolida D-058.b (sección como señal de reranking, no de filtrado) como el único mecanismo que protege del problema "bibliografía interpretada como profesorado".

**Archivos:**
- `actions/profesores/actions.py` (-169 / +94 líneas: eliminación del clasificador LLM y del cross-check; adición de los tres helpers vectoriales).

**Problema:** Durante la validación del piloto aparecieron varias mal-clasificaciones aunque los intents estaban bien definidos:
- "Cual es la asignatura mas dificil?" → clasificado como `preguntar_hay_mas` (por la palabra "más").
- "Cuantos años dura la totulacion?" → clasificado como `consulta_asignaturas_listado` (el bot devuelve 46 asignaturas cuando la pregunta es una sola cifra).
- "Cuáles son todos los profesores de EGC?" → clasificado como `consulta_horario`.
Todos son casos donde la confianza del intent ganador era media y el margen sobre el segundo era estrecho. El pipeline las aceptaba en vez de dejarlas caer al fallback.

**Decisión:** Tres ajustes al pipeline de [`config.yml`](../../../config.yml):

1. **Añadir `SpacyNLP` + `SpacyTokenizer` + `SpacyFeaturizer`** usando `es_core_news_md`. Hasta ahora el DIETClassifier aprendía desde cero con bag-of-words (`CountVectorsFeaturizer`) sobre ~600-800 ejemplos. Con embeddings pre-entrenados, palabras con carga semántica como "mejor", "peor", "difícil", "fácil", "recomiendas" llegan al clasificador con su vector — empareja mejor preguntas subjetivas con `out_of_scope` y discrimina mejor los intents cercanos.
2. **`FallbackClassifier.threshold` subido de 0.7 → 0.8**. Casos con confianza entre 0.7 y 0.8 ya no se aceptan — caen al fallback y el usuario recibe el mensaje "puedo ayudarte con asignaturas/horarios/profesores".
3. **`FallbackClassifier.ambiguity_threshold` bajado de 0.15 → 0.10**. Más sensible a empates: si el top-1 y top-2 tienen una diferencia <0.10, se considera ambiguo → fallback. Cubre el caso "mas dificil" (compite entre `preguntar_hay_mas` y `consulta_asignaturas_listado` con margen pequeño).

Cambio cosmético adicional: `CountVectorsFeaturizer (char_wb)` con `min_ngram: 2` (antes 1). Los n-gramas de 1 carácter aportan ruido con poco valor discriminante.

**Justificación:** `spaCy es_core_news_md` ya está instalado en el contenedor de actions y es gratuito. Los umbrales de fallback los trae Rasa por defecto en 0.3/0.1 y los teníamos artificialmente altos; ajustarlos es una configuración de producto (cuánto preferimos un "no entiendo" sobre una respuesta mal clasificada). Para Linceus, preferimos fallar explícitamente antes que inventar.

**Alternativas descartadas:**
- **Subir `epochs` del DIETClassifier** (150 → 250): sin efecto apreciable con este tamaño de dataset, solo alarga el entrenamiento.
- **`use_masked_language_model: true`**: útil con ≥1000 ejemplos; en nuestro rango marginal.
- **Reentrenar desde `rasa/LaBSE`** (Transformer multilingüe): gran salto de calidad pero requiere GPU y 10× más tiempo de entrenamiento. No justificable para el cierre.

**Archivos:** `config.yml` (pipeline NLU)

### D-058: Ejemplos cortos `curso N grupo M` al intent `consulta_horario`

**Problema:** Cuando el bot pide "dime curso y grupo" y el usuario responde literalmente "curso 3 grupo 3", Rasa no tenía ningún ejemplo corto con ese patrón sin la palabra "horario". El mensaje caía en `consulta_asignatura_especifica` por similitud con otros ejemplos sueltos.
**Decisión:** Añadir ~22 ejemplos cortos al intent `consulta_horario` cubriendo "curso N grupo M", "Nº grupo M", "primero/segundo/tercero/cuarto grupo M" y variantes con "soy de" / "del curso N". Sin ellos el split de D-053 es incompleto: horarios personales mal clasificados acababan en el flujo de ficha.
**Justificación:** Es el input más natural del usuario tras una pregunta aclaratoria del bot. Cero coste, soluciona un fallo observado en la validación manual de D-053.
**Archivos:** `data/nlu/horarios.yml`

---

## Pendiente

- **Job queue para scrapes largos** (ETSII completo ≈ 8-10 min): migrar de síncrono a background + polling si la fricción se nota.
- **Vista de profesores por centro (no solo por depto)**: actualmente para ver "todos los profes de ETSII" hay que sumar mentalmente los deptos. Útil para búsquedas cruzadas.
- **Añadir ETSI como centro gestionado** para recuperar DTE sin romper la división.
- **Cruce us.es ↔ scrapers S6 como paso explícito**: hoy los scrapers antiguos no se invocan desde el admin; convertirlos en "enriquecimientos opcionales" que el admin dispara tras el enrich de us.es.
- **Vista Titulación → Profesores** (who teaches what) vía `profesor_asignatura`, ya en roadmap S6 pendiente.
