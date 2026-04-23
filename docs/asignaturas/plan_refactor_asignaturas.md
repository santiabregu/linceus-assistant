# Plan de refactor — Actions del chatbot Linceus

> Documento preparado durante el cierre del TFG. Analiza los 4 módulos de Actions (`asignaturas`, `horarios`, `profesores`, `contexto`), con foco en **escalabilidad**, **deuda técnica** y **delimitación de responsabilidades** (qué vive en cada módulo y por qué). El objetivo no es rehacer nada grande — es cerrar el proyecto con un mapa claro y una lista corta de refactors de alto impacto.

## 0. Índice

- [1. Alcance](#1-alcance)
- [2. Mapa global de responsabilidades](#2-mapa-global-de-responsabilidades)
- [3. Módulo `asignaturas/`](#3-módulo-asignaturas)
- [4. Módulo `horarios/`](#4-módulo-horarios)
- [5. Módulo `profesores/`](#5-módulo-profesores)
- [6. Módulo `contexto/`](#6-módulo-contexto)
- [7. Deuda técnica transversal](#7-deuda-técnica-transversal)
- [8. Prioridad de cierre](#8-prioridad-de-cierre)
- [9. Notas para la memoria del TFG](#9-notas-para-la-memoria-del-tfg)

## 1. Alcance

- [actions/asignaturas/actions.py](../../actions/asignaturas/actions.py) (~1200 líneas)
- [actions/asignaturas/text_to_sql.py](../../actions/asignaturas/text_to_sql.py) (~920 líneas)
- [actions/horarios/actions.py](../../actions/horarios/actions.py) (~570 líneas)
- [actions/profesores/actions.py](../../actions/profesores/actions.py) (~620 líneas)
- [actions/contexto/actions.py](../../actions/contexto/actions.py) (~210 líneas)
- Diccionarios [ALIAS_ASIGNATURAS + TITULACION_MAP](../../actions/shared/config.py)
- Feedback real del piloto en [knowledge_base/feedback/](../../knowledge_base/feedback/)

## 2. Mapa global de responsabilidades

La dificultad principal hoy no es la cantidad de código sino **saber dónde vive cada cosa**. Este es el reparto propuesto como fuente de verdad (lo que YA está funcionando y conviene conservar):

| Pregunta del usuario | Módulo responsable | Entry Action |
|----------------------|--------------------|--------------|
| "Cuántos créditos tiene ADDA" | `asignaturas` | `ActionConsultaEspecifica` |
| "Optativas de 4º" | `asignaturas` | `ActionConsultaListado` |
| "Cuántas obligatorias hay" | `asignaturas` | `ActionConsultaConteo` |
| "Cómo se evalúa DP1" | `asignaturas` (RAG plan docente) | `ActionConsultaEspecifica` |
| "Horario de 2º grupo 1" | `horarios` | `ActionConsultaHorario` |
| **"A qué hora tengo FP" / "Dónde es ADDA"** | **`asignaturas`** (se redirige desde horarios si detecta asignatura) | `ActionConsultaEspecifica` |
| "Profesores de DP1" | `profesores` | `ActionConsultaProfesor` |
| "Correo de Parejo" | `profesores` | `ActionConsultaProfesor` |
| "Tutorías de Ruiz Cortés" | `profesores` | `ActionConsultaProfesor` |
| "Cambiar a GII-IS" | `contexto` | `ActionCambiarContexto` |

### 2.1 El caso crítico: **horario de asignatura**

Es la frontera más frágil. La situación actual:

1. Si el NLU clasifica la pregunta como `consulta_horario`, entra [ActionConsultaHorario](../../actions/horarios/actions.py#L430).
2. Dentro, se detecta si el mensaje menciona una asignatura (via entidad NLU + fallback alias). Si sí → `return ActionConsultaEspecifica().run(...)` ([horarios/actions.py:507-511](../../actions/horarios/actions.py#L507-L511)).
3. En `ActionConsultaEspecifica` hay otra detección por keywords (`_PALABRAS_HORARIO_ASIGNATURA`) que decide llamar a `_responder_horario_asignatura` ([asignaturas/actions.py:557](../../actions/asignaturas/actions.py#L557)), que **vuelve a importar funciones de `horarios`** para las queries.

Esto funciona pero tiene **doble detección** (una en cada módulo) y un **ciclo de imports** entre `asignaturas` y `horarios`. Es la mayor fuente de duplicación del proyecto.

**Decisión propuesta (ver R1 en §3):** la consulta "horario de asignatura X" se queda en `asignaturas/` como Action dedicado, NO en `horarios/`. Razones:

- El input crítico es la **asignatura** (resuelta por el pipeline de `asignaturas`, que es el más maduro: NLU → alias → fuzzy BD → seguimiento).
- La tabla `horarios` es simplemente un JOIN más sobre `asignaturas`; no aporta lógica propia cuando el foco es una asignatura concreta.
- Evita el reenvío `ActionConsultaHorario → ActionConsultaEspecifica` y el ciclo de imports.

`horarios/` queda como dueño único de **"horario personal por curso+grupo"**, que es un caso de uso distinto (input = curso+grupo, output = parrilla semanal).

### 2.2 Reutilización cross-módulo

Lo que conviene seguir compartiendo:

- `ALIAS_ASIGNATURAS` (en `shared/config.py`) — consumido por los 3 módulos de dominio.
- `comprobar_titulacion`, `_contar_turnos_desde_slot` (en `asignaturas/actions.py`) — importados por `horarios` y podrían por `profesores`. **Deberían moverse a `shared/`** (ver D3).
- `resolver_asignatura` (pipeline completo) — `profesores` ya lo reutiliza ([profesores/actions.py:131-148](../../actions/profesores/actions.py#L131-L148)) y es el patrón correcto.

## 3. Módulo `asignaturas/`

### 3.1 Lo que conservar

- **Pipeline en capas de `resolver_asignatura`** ([actions.py:359-465](../../actions/asignaturas/actions.py#L359-L465)): NLU → alias → seguimiento → fuzzy BD → ILIKE → fallback fuzzy. Bien ordenado (seguimiento antes del fuzzy).
- **Validación SQL** en [text_to_sql.py:606](../../actions/asignaturas/text_to_sql.py#L606): lista negra + whitelist de tablas/columnas + `%s`. Suficiente para el TFG.
- **Separación 3 intents** (`especifica` / `listado` / `conteo`): prompts simples, fácil de explicar en la memoria.
- **Cortocircuito heurística → LLM** en `_clasificar_necesita_rag` ([text_to_sql.py:251](../../actions/asignaturas/text_to_sql.py#L251)).
- **Fallbacks SQL predefinidos** si el LLM cae.

### 3.2 Problemas observados (evidencia del piloto)

| # | Problema | Evidencia |
|---|----------|-----------|
| P1 | Pérdida de contexto entre turnos ("esa asignatura") | [72], [80] |
| P2 | Follow-up cross-módulo de horarios no siempre engancha | [sesion 177622 int. 10] |
| P3 | Chunks de bibliografía interpretados como profesorado | [24] |
| P4 | Alias de letra única chocan con asignaturas reales | [60], [sesion int. 12] |
| P7 | Acrónimo `PD` ambiguo entre Programación Declarativa / DP abreviado | [62] |

### 3.3 Deuda técnica

**Alta — merece tocarse:**

1. **`_PALABRAS_HORARIO_ASIGNATURA` hardcodeada** ([actions.py:520](../../actions/asignaturas/actions.py#L520)). Duplica el trabajo del NLU. Eliminarla separando en Action dedicado (ver R1).
2. **`_extraer_multiples_nombres`** ([actions.py:177](../../actions/asignaturas/actions.py#L177)) solo usa aliases, no fuzzy BD. "DP1 y Modelado" falla. Bajo impacto.
3. **Duplicación de consulta "SELECT nombre FROM asignaturas"** en `_resolver_nombre_desde_texto` y `_sugerencias_asignatura`. Cachear a nivel de proceso.

**Media — legibilidad:**

4. **`ActionConsultaEspecifica.run` = 200 líneas** con 4 flujos en cascada ([actions.py:683-880](../../actions/asignaturas/actions.py#L683-L880)). Partir en `_try_multi`, `_try_horario`, `_try_rag`, `_respond_sql`.
5. **`_expandir_alias`** tiene `for _ in range(3)` ([text_to_sql.py:206](../../actions/asignaturas/text_to_sql.py#L206)). Magic number; usar `while cambió`.

**Baja — dejar como está:**

6. Diccionario `ALIAS_ASIGNATURAS` hardcoded. **Merece conservarse** (ver §3.4).
7. Prompts separados por intent. Unificar quitaría claridad.

### 3.4 ¿Tiene sentido mantener los aliases hardcoded?

**Sí.** Tres motivos:

- **Determinismo:** "ADDA", "DP1", "PSG2" son los aliases oficiales que usa todo el mundo en Sevilla. Son **fuente de verdad**, no heurística.
- **Ya hay fallback dinámico:** si un alias no está listado, `_parece_acronimo` + `_buscar_por_acronimo_en_bd` ([text_to_sql.py:158](../../actions/asignaturas/text_to_sql.py#L158)) lo genera desde los nombres de la BD. El diccionario es happy-path; el auto-acrónimo es el fallback.
- **Escalable entre titulaciones:** la BD tiene `titulacion_id`, el filtro se inyecta en todas las queries. Añadir otra titulación (p.ej. Matemáticas) es cargar sus asignaturas; los aliases nuevos se auto-detectan.

Lo que **no** escala son las **listas de keywords de intención** (`_PALABRAS_HORARIO_ASIGNATURA`, `_PALABRAS_RAG`). Ahí sí conviene LLM o — mejor — separar en intents NLU.

## 4. Módulo `horarios/`

### 4.1 Lo que conservar

- **Queries parametrizadas** a `horarios JOIN grupos_clase JOIN asignaturas` con filtros dinámicos (día, cuatrimestre). Limpias.
- **`_tiene_referencia_letra_dni`** ([horarios/actions.py:95](../../actions/horarios/actions.py#L95)): detecta "letra T del DNI" y pide número de grupo. Resuelve un fallo real del piloto (sesion 177622 int. 12).
- **Heurística de stop-words para alias cortos** ([horarios/actions.py:486-498](../../actions/horarios/actions.py#L486-L498)): exige contexto ("asignatura de", "horario de") para aliases como `e`, `c`, `t`. Correcta.
- **Follow-up por slot reciente** ([horarios/actions.py:513-547](../../actions/horarios/actions.py#L513-L547)): hereda curso/grupo del slot si faltan. Bien pensado.

### 4.2 Problemas observados

| # | Problema | Evidencia |
|---|----------|-----------|
| P2 | "Dime la de todos los grupos" tras horario de SI no engancha | [sesion 177622 int. 10] |
| P9 | Doble detección asignatura entre horarios y asignaturas | ver §2.1 |
| P10 | Llamar a `ActionConsultaEspecifica().run()` desde otro Action es frágil (paso de responsabilidad implícito) | [horarios/actions.py:510-511](../../actions/horarios/actions.py#L510-L511) |

### 4.3 Deuda técnica

**Alta:**

1. **Doble detección de asignatura** (aquí + en `asignaturas`). Ciclo de imports entre módulos. Resuelve con R1.
2. **Reenvío a `ActionConsultaEspecifica.run()`**: acoplamiento fuerte. Un día cambiará la firma y romperá. Preferible un router explícito en [actions/actions.py](../../actions/actions.py) (entry point de Rasa) o intents NLU separados.

**Media:**

3. **`ALIAS_ASIGNATURAS.get(alias.lower())`** directo en `_query_asignatura` ([horarios/actions.py:186](../../actions/horarios/actions.py#L186)) — no pasa por `_expandir_alias`. Si el alias no está en el dict, falla silenciosamente. Unificar.
4. **`NOMBRES_TITULACION` local** ([horarios/actions.py:30-34](../../actions/horarios/actions.py#L30-L34)) duplica `BotConfig.NOMBRES_TITULACIONES`. Usar el central.

**Baja:**

5. **URL del PDF hardcodeada** ([horarios/actions.py:28](../../actions/horarios/actions.py#L28)). A config si se quiere, pero es estable.

### 4.4 Propuesta de reparto post-refactor

Tras aplicar **R1**:

- `horarios/` mantiene solo `ActionConsultaHorario` para **"horario personal por curso+grupo"**.
- Las funciones `_query_asignatura`, `_query_grupos_de_asignatura`, `_datos_asignatura_a_texto`, `_generar_respuesta_horario` se mueven — o mejor, se **exportan limpiamente** — y las usa el nuevo Action en `asignaturas/`.
- Se elimina toda la detección de asignatura en `ActionConsultaHorario` (líneas 474-511) y el reenvío a `ActionConsultaEspecifica`.
- El NLU se encarga del routing vía intents separados (`preguntar_horario_personal` vs `preguntar_horario_asignatura`).

## 5. Módulo `profesores/`

### 5.1 Lo que conservar

- **Pipeline RAG específico** ([profesores/actions.py:260-357](../../actions/profesores/actions.py#L260-L357)): buscar en plan docente por keyword + match en tabla profesores + filtrado por intersección. Es el patrón correcto para "profesora Belén que da FP".
- **Clasificador RAG con LLM** ([profesores/actions.py:193-255](../../actions/profesores/actions.py#L193-L255)): decide si el nombre es suficientemente ambiguo como para necesitar plan docente. Muy buena decisión de diseño.
- **Reutilizar `resolver_asignatura`** del módulo asignaturas ([profesores/actions.py:138-148](../../actions/profesores/actions.py#L138-L148)): ejemplo de buena composición cross-módulo.
- **Filtrado por similitud** ([profesores/actions.py:572-591](../../actions/profesores/actions.py#L572-L591)) vía `clasificar_por_normalizado`: evita falsos positivos tipo "Joaquín Peña" → "Joaquín Borrego".
- **`_enriquecer_con_tutorias`** ([profesores/actions.py:362-420](../../actions/profesores/actions.py#L362-L420)): segunda query solo si hizo falta. Eficiente.

### 5.2 Problemas observados

| # | Problema | Evidencia |
|---|----------|-----------|
| P11 | "Profesores de EGC" devuelve autores de libros (Kästner, Saake) | [24] — problema del RAG chunking, no de este módulo |
| P12 | "Tutorías del profesor Parejo" no desambigua entre los 2 Parejo | [38], [49], [50] |
| P13 | "Y bedilia?" (follow-up) cae a fallback | [43] — NLU no extrae entidad |

### 5.3 Deuda técnica

**Alta:**

1. **`sys.path.insert` y carga cruzada** ([profesores/actions.py:33-42](../../actions/profesores/actions.py#L33-L42)): importa text_to_sql desde `knowledge_base/profesores_data/`. Asqueroso y frágil — rompe si se reestructura la carpeta. **Mover el text_to_sql a `actions/profesores/text_to_sql.py`** como hace `asignaturas`.
2. **`_extraer_nombre_profesor_con_llm`** ([profesores/actions.py:106-128](../../actions/profesores/actions.py#L106-L128)): llamada LLM síncrona extra dentro del flujo. Latencia acumulada si ya estamos llamando al clasificador RAG + generador SQL + respuesta natural. Considerar skipearla si el NLU ya extrajo algo.

**Media:**

3. **`_contar_turnos_desde_slot` duplicada** en asignaturas y profesores. Mover a `shared/` (ver D3).
4. **`_normalizar` duplicada** en 3 módulos (asignaturas, horarios, profesores). Ya existe `normalizar_texto` en asignaturas. Centralizar.

**Baja:**

5. **Mensajes de sugerencia largos** — cuando hay varios Parejo, construye una lista "¿quizás te refieres a X o Y?". Podría dar botones Rasa, pero requiere cambios en el frontend.

## 6. Módulo `contexto/`

### 6.1 Lo que conservar

- **Fuzzy matching con cutoff 70** sobre `TITULACION_MAP` ([contexto/actions.py:60-65](../../actions/contexto/actions.py#L60-L65)): correcto en el 90% de los casos.
- **Ruta separada para listar titulaciones** (`ActionConsultaTitulaciones`): query a BD con conteo de asignaturas. Útil.
- **Consultar contexto actual** (`ActionConsultarContexto`): estado legible para el usuario.

### 6.2 Problemas observados

| # | Problema | Evidencia |
|---|----------|-----------|
| P8 | "Ingeniería de la Salud" → GII-IS (fuzzy demasiado permisivo) | [52] |
| P14 | "Ingenieria del software" + typos aceptados (bien), pero cualquier texto con "software" también (mal) | [77], [88] — aceptado sin ambigüedad |

### 6.3 Deuda técnica

**Media:**

1. **Cutoff de 70 demasiado bajo**: "Ingeniería de la Salud" vs "Ingeniería del Software" comparten mucho texto. Subirlo a 85 o **exigir match exacto en el código** (`GII-IS`, `IS`) antes del fuzzy.
2. **`TITULACION_MAP` hardcodeado** con 21 entradas. Igual que con aliases de asignaturas, **tiene sentido conservarlo** porque los códigos son estables y los alias coloquiales ("software", "TI") no se generan solos. Pero si se añade otra titulación hay que tocar este dict → **dejar TODO con comentario**.
3. **Mensaje de error** ([contexto/actions.py:93-103](../../actions/contexto/actions.py#L93-L103)) lista solo las 3 titulaciones activas hoy. Debería leerlas de BD como hace `_cargar_titulaciones_desde_bd` en asignaturas. Pequeño pero reduce divergencias.

**Baja:**

4. `ActionCambiarContexto` mezcla detección de entidad + fuzzy + respuesta. OK por tamaño, no hace falta trocear.

### 6.4 Escalabilidad

Añadir una titulación nueva hoy requiere:

1. Cargar sus asignaturas en BD (automático).
2. Añadir entradas al `TITULACION_MAP` de `contexto` (manual).
3. Añadir entrada a `NOMBRES_TITULACIONES` en `shared/config.py` (manual).
4. Revisar `ALIAS_ASIGNATURAS` para colisiones de alias entre titulaciones (manual).

Es razonable para un TFG. Para producción real convendría que los pasos 2 y 3 se deriven automáticamente de la tabla `titulaciones` de la BD.

## 7. Deuda técnica transversal

Código duplicado o patrones inconsistentes entre módulos. Cada ítem tiene su etiqueta D#.

- **D1 — `_normalizar` duplicada** en `asignaturas`, `horarios`, `profesores`. Mover a `shared/matching.py` (ya existe el archivo).
- **D2 — `_detectar_grupo` duplicada** en `asignaturas/actions.py:33` y `horarios/actions.py:75` con firmas ligeramente distintas (una devuelve "Grupo 1" string, otra int). Unificar a una sola con parámetro de formato.
- **D3 — `_contar_turnos_desde_slot` duplicada** en asignaturas y profesores. Mover a `shared/`.
- **D4 — `comprobar_titulacion` vive en `asignaturas/actions.py`** y lo importa `horarios`. Debería estar en `shared/`. Profesores no lo usa y probablemente debería.
- **D5 — `NOMBRES_TITULACION` duplicado** en `horarios/actions.py:30` y `shared/config.py:30`. Usar solo el central.
- **D6 — Patrón de prompt LLM repetido** (roles + reglas + "No saludes" + "máximo 1500 caracteres") en `asignaturas.generar_respuesta_natural`, `asignaturas._generar_respuesta_rag`, `horarios._generar_respuesta_horario`, `profesores.generar_respuesta_natural`. Plantilla común en `shared/prompts.py`.
- **D7 — Imports cruzados `asignaturas ↔ horarios`**: `horarios` importa `comprobar_titulacion` de asignaturas y, al reenviar al Action, importa `ActionConsultaEspecifica`. Asignaturas a su vez importa `_query_asignatura` de horarios. **Ciclo**. Rompibles con R1 + D4.
- **D8 — `sys.path.insert` en profesores** para importar text_to_sql desde `knowledge_base/`. Muy sucio. Ver §5.3.1.
- **D9 — Prints de debug en producción** (emojis, separadores `'='*60`) repartidos por los 4 módulos. No son deuda real pero llenan logs. Al menos unificar a `logger.py` (que ya existe en shared).

## 8. Prioridad de cierre

Ordenado por coste/beneficio considerando que el TFG se está cerrando.

### 8.1 Must (resuelven problemas observados) — 2-4h

- [ ] **R1 — Crear Action dedicado de horario de asignatura en `asignaturas/`.**
  - Nuevo `ActionConsultaHorarioAsignatura` en `asignaturas/actions.py` (o archivo aparte).
  - Mueve la lógica de `_responder_horario_asignatura` actual ([asignaturas/actions.py:557-663](../../actions/asignaturas/actions.py#L557-L663)) al nuevo Action.
  - Elimina la detección keyword `_PALABRAS_HORARIO_ASIGNATURA` + el bloque condicional en `ActionConsultaEspecifica.run` ([asignaturas/actions.py:762-799](../../actions/asignaturas/actions.py#L762-L799)).
  - En `horarios/ActionConsultaHorario` elimina la detección de asignatura + el reenvío a `ActionConsultaEspecifica` ([horarios/actions.py:474-527](../../actions/horarios/actions.py#L474-L527)).
  - El NLU distingue intents `preguntar_horario_personal` (curso+grupo) y `preguntar_horario_asignatura` (asignatura).
  - Las funciones `_query_asignatura`, `_datos_asignatura_a_texto`, `_generar_respuesta_horario` **se quedan en `horarios/`** como utilidades exportables — el nuevo Action las importa sin ciclos (el import solo va en una dirección: asignaturas → horarios).
  - **Beneficio:** elimina doble detección (P9), rompe ciclo de imports (D7), quita ~80 líneas de keywords hardcoded.
  - **Riesgo:** medio — hay que tocar NLU training data y routing.

- [ ] **R2 — Bloquear aliases de letra única en `_expandir_alias`.**
  - En [text_to_sql.py:188](../../actions/asignaturas/text_to_sql.py#L188), si `len(nombre_lower) == 1`, devolver el original sin expandir (o flag de "ambiguo" → el Action pide más contexto).
  - Generaliza el parche actual que solo vive en `ActionConsultaEspecifica` horario.
  - **Beneficio:** resuelve P4 (fallos con "T", "C", "E") en los 3 módulos a la vez.
  - **Riesgo:** bajo — ~5 líneas.

### 8.2 Should (limpieza con alto ROI) — 1-2h cada uno

- [ ] **R3 — Endurecer fuzzy de `ActionCambiarContexto`.**
  - Subir `score_cutoff` a 85 en [contexto/actions.py:64](../../actions/contexto/actions.py#L64).
  - Añadir check previo: si el texto contiene palabras que NO están en ningún alias ("salud"), rechazar antes de llamar al fuzzy.
  - Resuelve P8.

- [ ] **R4 — Extraer utilidades transversales a `shared/`.**
  - Mueve `_normalizar`, `_detectar_grupo`, `_contar_turnos_desde_slot`, `comprobar_titulacion` a `shared/matching.py` + `shared/slots.py`.
  - Cubre D1-D4.

- [ ] **R5 — Mover `profesores/text_to_sql`** de `knowledge_base/` a `actions/profesores/text_to_sql.py`.
  - Elimina el `sys.path.insert`. Cubre D8.

### 8.3 Could (lectura, no cambia comportamiento)

- [ ] **R6 — Partir `ActionConsultaEspecifica.run`** en métodos privados (`_try_multi`, `_try_rag`, `_respond_sql`) tras R1.
- [ ] **R7 — Plantilla común de prompts** en `shared/prompts.py`. Cubre D6.
- [ ] **R8 — Caché de `SELECT nombre FROM asignaturas`** por titulación. Cubre §3.3.3.

### 8.4 Won't (deuda aceptada, documentada en memoria)

- **W1 — Mantener `ALIAS_ASIGNATURAS` y `TITULACION_MAP` hardcoded.** Son datos de dominio estables; el fallback dinámico ya está (`_buscar_por_acronimo_en_bd`).
- **W2 — Mantener 3 Actions separados** en asignaturas (`especifica`/`listado`/`conteo`).
- **W3 — Validación SQL artesanal.** `sqlglot` añade dependencia y latencia sin ROI.
- **W4 — RAG confundiendo bibliografía con profesorado (P3).** Es problema de chunking, no del módulo.
- **W5 — Prints de debug.** Funcional, no merece la pena.

## 9. Notas para la memoria del TFG

- La arquitectura del sistema es **intencionalmente híbrida**: diccionario estático para datos de dominio estables (alias de asignaturas, códigos de titulación) + LLM/fuzzy para lenguaje natural variable. Esto no es deuda, es diseño.
- Los 4 módulos están **bien separados por responsabilidad**, con una única excepción: **horario de asignatura** vive en dos sitios a la vez. R1 resuelve este nudo.
- El feedback del piloto valida la arquitectura: los fallos observados están en la **capa de detección de intención** (keywords), en el **RAG** (chunking), y en el **fuzzy del contexto** — no en la capa SQL ni en el pipeline de resolución de entidades.
- Escalabilidad: añadir una titulación nueva requiere cargar asignaturas en BD + actualizar 2 diccionarios. Añadir un atributo nuevo (p.ej. `idioma_impartición`) solo requiere tocar el schema y el prompt de `generar_sql_*`. Añadir un tipo nuevo de consulta (p.ej. "aulas libres") requiere un nuevo módulo siguiendo el mismo patrón — ya hay 4 ejemplos.
- La evolución natural es: reemplazar las heurísticas residuales de keywords por intents NLU entrenados (lo que hace R1), y no rediseñar la capa SQL ni el pipeline de aliases.

### 9.1 Si solo queda tiempo para un cambio

**R1**. Resuelve el único problema arquitectónico real (doble detección + ciclo de imports) y se defiende solo en la memoria como "deuda identificada durante el piloto y resuelta en el cierre".

### 9.2 Si quedan dos

**R1 + R2**. R2 son ~5 líneas y cierra un fallo observado directamente en las conversaciones reales.

### 9.3 Si quedan tres

**R1 + R2 + R3**. R3 resuelve el mapeo incorrecto "Ingeniería de la Salud" → GII-IS que también está en el feedback.
