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

## Pendiente

- **Job queue para scrapes largos** (ETSII completo ≈ 8-10 min): migrar de síncrono a background + polling si la fricción se nota.
- **Vista de profesores por centro (no solo por depto)**: actualmente para ver "todos los profes de ETSII" hay que sumar mentalmente los deptos. Útil para búsquedas cruzadas.
- **Añadir ETSI como centro gestionado** para recuperar DTE sin romper la división.
- **Cruce us.es ↔ scrapers S6 como paso explícito**: hoy los scrapers antiguos no se invocan desde el admin; convertirlos en "enriquecimientos opcionales" que el admin dispara tras el enrich de us.es.
- **Vista Titulación → Profesores** (who teaches what) vía `profesor_asignatura`, ya en roadmap S6 pendiente.
