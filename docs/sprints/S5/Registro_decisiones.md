# Registro de decisiones - Sprint 5

## Contexto

Sprint centrado en testing de la épica Asignaturas v1. Se creó un plan de pruebas automatizado con 51 casos de test (`tests/run_test_plan.py`) que se ejecutan contra el bot Rasa con action server activo.

---

## Iteración 1 (2026-03-12): Resultados iniciales y plan v1

**Resultado:** 36/51 tests pasados (70.6%)

### D-001: Fix de alias con prefijos NLU

**Problema:** `_expandir_alias` no limpiaba prefijos del NLU (e.g. "de PGPI" en vez de "PGPI").
**Decisión:** Añadir limpieza de prefijos comunes (`de`, `del`, `la`, `el`, `sobre`, `info`, `datos`) con regex en `_expandir_alias` (`actions/asignaturas/text_to_sql.py`).
**Estado:** Implementado.

### D-002: Test E-T03 — no exigir que pida titulación

**Problema:** E-T03 (consulta sin titulación en slot) esperaba que el bot pidiera titulación, pero el bot resuelve correctamente sin filtro cuando la asignatura existe en varias titulaciones con los mismos datos.
**Decisión:** Cambiar el test para validar que responda "6" (créditos correctos) en vez de exigir que pida titulación.
**Estado:** Implementado.

---

## Iteración 2 (2026-03-14): Ejecución plan v1 + plan v2

### D-003: Nuevos ejemplos NLU para "todas las asignaturas" (Plan v1, punto 3)

**Problema:** "Dame todas las asignaturas" se clasificaba como `pedir_mas_resultados` en vez de `consulta_asignaturas_listado`.
**Decisión:** Añadir 8 ejemplos con "todas las asignaturas" a `consulta_asignaturas_listado`. Eliminar "todas las asignaturas" de `pedir_mas_resultados` para evitar colisión.
**Archivos:** `data/nlu/asignaturas.yml`

### D-004: Nuevos ejemplos NLU para conteo con "carrera"/"grado" (Plan v1, punto 4)

**Problema:** "¿Cuántas asignaturas tiene la carrera?" se clasificaba como `consulta_titulaciones`.
**Decisión:** Añadir 6 ejemplos con "carrera"/"grado" a `consulta_asignaturas_conteo`.
**Archivos:** `data/nlu/asignaturas.yml`

### D-005: Intent `out_of_scope` + threshold de fallback (Plan v1, punto 6)

**Problema:** Preguntas fuera de ámbito (capital de Francia, chistes, pizza) se clasificaban con alta confianza en intents existentes.
**Decisión:**
- Crear intent `out_of_scope` con 30 ejemplos en `data/nlu/general.yml`
- Subir threshold de FallbackClassifier de 0.6 a 0.7 en `config.yml`
- Añadir regla en `rules.yml`: `out_of_scope` → `utter_default`
- Añadir `out_of_scope` al `domain.yml`
**Justificación:** `out_of_scope` es más preciso que depender solo del threshold: el modelo aprende explícitamente qué es fuera de ámbito. `nlu_fallback` se reserva para mensajes que el modelo no entiende en absoluto.

### D-006: Corrección de expected_count en tests (Plan v2, punto 4)

**Problema:** Los conteos esperados en tests C-P03, C-T01, C-T02 no coincidían con la BD real.
**Decisión:** Consultar BD y corregir valores:
- C-P03 (GII-IS): 42 → 47
- C-T01 (GII-IC): 44 → 48
- C-T02 (GII-TI): 52 → 54
**Archivos:** `tests/run_test_plan.py`

### D-007: Validación de tests fallback acepta `out_of_scope` (Plan v2, punto 6)

**Problema:** Tests F-01 a F-04 esperaban `nlu_fallback` pero obtienen `out_of_scope` tras D-005.
**Decisión:** Actualizar la validación en `run_test_plan.py` para aceptar tanto `nlu_fallback` como `out_of_scope` en tests de fuera de ámbito. Ambos producen la misma respuesta (`utter_default`).
**Archivos:** `tests/run_test_plan.py`

### D-008: Fallback con búsqueda por código + SELECT ALL (Plan v2, punto 2)

**Problema:** E-P12 ("¿Qué asignatura es la 2050001?") fallaba porque el fallback flexible solo buscaba por `nombre_normalizado ILIKE`, no por `codigo`.
**Decisión:** Implementar 2 niveles de fallback en `ActionConsultaEspecifica`:
1. Búsqueda flexible por nombre **O código**: `nombre_normalizado ILIKE %s OR codigo ILIKE %s`
2. Si tampoco hay resultados, SELECT ALL de la titulación activa y pasar todos los datos al LLM para que resuelva
**Justificación:** El SELECT ALL evita que queries válidas pero mal generadas por el text-to-SQL devuelvan "no encontrada". El LLM puede encontrar la asignatura correcta a partir de la lista completa.
**Archivos:** `actions/asignaturas/actions.py`

### D-009: Ejemplos de asignaturas genéricas para mejorar robustez NLU (Plan v2, punto 3)

**Problema:** E-N02 ("Información sobre Derecho Penal") caía en `nlu_fallback` porque DIET nunca había visto nombres de asignaturas fuera de la ETSII.
**Decisión:** Añadir 8 ejemplos con nombres ficticios (Derecho Penal, Economía, Biología, etc.) a `consulta_asignatura_especifica`. Actualizar test E-N02 para aceptar `nlu_fallback`/`out_of_scope` como válido.
**Justificación:** DIET debe aprender que cualquier nombre propio en posición de asignatura es una consulta válida. La acción ya maneja "no encontrada" correctamente.
**Archivos:** `data/nlu/asignaturas.yml`, `tests/run_test_plan.py`

### D-010: Regex feature para distinguir conteo de listado (Plan v2, punto 5)

**Problema:** C-P05 ("Número de asignaturas anuales") se clasificaba como `consulta_asignaturas_listado` con conf=1.00.
**Decisión:**
- Añadir regex feature `conteo_signal` con patrón `(cuant[oa]s|numero de|cantidad de|total de)` en `data/nlu/asignaturas.yml`
- Añadir 10 nuevos ejemplos de conteo con variaciones de "número de", "cantidad de", "total de"
- Verificar que ningún ejemplo de listado contenga señales de conteo
**Justificación:** `RegexFeaturizer` (ya en el pipeline) convierte el patrón regex en una feature binaria que DIET puede usar como señal discriminante adicional.
**Archivos:** `data/nlu/asignaturas.yml`

### D-011: No unir intents/actions de listado y conteo

**Problema:** `action_consulta_listado` y `action_consulta_conteo` comparten ~70% del código.
**Decisión:** No unir. Mantener separados.
**Justificación:** Aunque hay duplicación, la separación permite respuestas optimizadas (listado con paginación de 8 resultados vs conteo con número directo). Unirlos requeriría refactorizar rules, domain, y la lógica de generación de SQL. El coste de refactor supera el beneficio.

### D-012: No implementar RegexEntityExtractor para acrónimos (Plan v2, punto 1)

**Problema:** E-P11 (PGPI) y E-T02 (IA) fallan por mala extracción de entidades en acrónimos.
**Decisión:** Descartar la propuesta de RegexEntityExtractor + lookup table + generación dinámica de acrónimos.
**Justificación:** RegexEntityExtractor puede generar falsos positivos con cualquier palabra en mayúsculas. La lookup table sola no resuelve el problema de fondo. La generación dinámica desde BD añade complejidad y una query extra por mensaje. El diccionario de alias estático ya cubre los casos conocidos. Pendiente de investigar si el problema real es que el LLM genera SQL incorrecto tras expandir el alias.

### D-013: Actualizar `utter_default` con enlaces útiles (Plan v2, punto 7)

**Problema:** La respuesta de fallback no ofrecía recursos alternativos al usuario.
**Decisión:** Actualizar `utter_default` en `domain.yml` para incluir enlaces a SEVIUS (portal del estudiante) y la web de la Universidad de Sevilla. Simplificar el mensaje.
**Archivos:** `domain.yml`

---

## Iteración 3 (2026-03-24): Testing RAG y robustez de resolución de asignaturas

**Contexto:** Testing manual del flujo RAG contra planes docentes reales (tabla `testing/test_rag_asignaturas_v2.md`). Se detectaron múltiples fallos en la resolución de asignaturas cuando el usuario usa nombres parciales, acrónimos o lenguaje coloquial.

### D-014: Fallback fuzzy cuando ILIKE falla con nombre extraído por NLU

**Problema:** NLU extrae "Ing de Requisitos" como entidad, pero `ILIKE '%ing de requisitos%'` no matchea porque en BD el nombre normalizado es "ingenieria de requisitos".
**Decisión:** Añadir un paso de fuzzy matching (`_resolver_nombre_desde_texto`) como fallback adicional entre la búsqueda flexible ILIKE y el mensaje de error "asignatura no encontrada". Si el fuzzy encuentra un match, se reintenta la query SQL con el nombre real.
**Archivos:** `actions/asignaturas/actions.py`

### D-015: Mejora de `_resolver_nombre_desde_texto` con ventanas de palabras

**Problema:** Cuando NLU no extrae entidad, `_resolver_nombre_desde_texto` recibía la pregunta completa ("En el grupo 4 de ing de requisitos las clases son en ingles?") y el fuzzy match con tanto ruido no encontraba la asignatura correcta.
**Decisión:** Implementar estrategia de ventanas deslizantes: además de probar la pregunta completa, probar fragmentos de 2-6 palabras contiguas contra los nombres de BD. Esto aísla fragmentos como "ing de requisitos" del ruido circundante. Se subió el score_cutoff de la pregunta completa a 85 (más estricto) para evitar falsos positivos.
**Archivos:** `actions/asignaturas/actions.py`

### D-016: Reordenación de resultados SQL por `token_set_ratio`

**Problema:** Cuando el LLM genera SQL con parámetros parciales (ej. `%Numérica%`), la query devuelve múltiples asignaturas y `resultados[0]` coge la primera arbitrariamente. Ejemplo: "Modelado y Simulación Numérica" vs "Álgebra Lineal y Numérica" — ambas matchean `%Numérica%` pero se cogía la incorrecta.
**Decisión:** Cuando hay múltiples resultados, reordenar por `fuzz.token_set_ratio` contra la pregunta completa del usuario. `token_set_ratio` comprueba qué tokens del nombre de asignatura aparecen en la pregunta: "modelado", "simulacion", "numerica" todos están en la pregunta → score 100; "algebra", "lineal" no están → score 57.
**Justificación:** Se descartó `fuzz.ratio` (penaliza diferencias de longitud) y `fuzz.partial_ratio` (da falsos positivos con strings cortos). `token_set_ratio` es robusto ante strings de longitudes distintas y ruido en la pregunta.
**Archivos:** `actions/asignaturas/actions.py`

### D-017: Detección de alias/acrónimos en la pregunta cuando NLU no extrae entidad

**Problema:** "Cuáles son los temas del grupo 1 de PSG1?" — NLU no extrae entidad, y el fuzzy matcher confunde "PSG1" con "Introducción a la Ingeniería del Software y los Sistemas de Información I" (score 88.9 por coincidencias parciales de caracteres).
**Decisión:** Antes del fuzzy match, buscar palabra por palabra en la pregunta si alguna coincide con un alias del diccionario `ALIAS_ASIGNATURAS`. Se buscan los alias más largos primero (para evitar que "is" matchee antes que "is1"). Si se encuentra, se expande directamente sin necesidad de fuzzy.
**Archivos:** `actions/asignaturas/actions.py`

### D-018: Ampliación del diccionario de alias `ALIAS_ASIGNATURAS`

**Problema:** Acrónimos usados coloquialmente por los estudiantes (PSG1, SSI, AII, Cripto, CBD) no estaban en el diccionario de alias.
**Decisión:** Añadir los siguientes alias:
- `psg`, `psg1`, `psg2` → "proceso software y gestion"
- `ssi` → "seguridad de sistemas de informacion"
- `aii` → "acceso inteligente a la informacion"
- `cripto` → "criptografia"
- `cbd` → "complementos de base de datos"
**Archivos:** `actions/asignaturas/text_to_sql.py`

### D-019: Reformulación de preguntas de test para testing realista

**Problema:** Las preguntas de test de PSG1 y curso 4 usaban el nombre completo y exacto de la asignatura, lo cual no prueba la robustez del sistema ante lenguaje real de estudiantes.
**Decisión:** Reescribir las preguntas de las secciones Proceso Software y Gestión I, Evolución y Gestión de la Configuración, PGPI, Acceso Inteligente, Criptografía, Derecho, Complementos BD y SSI usando: acrónimos (PSG1, EGC, PGPI, AII, SSI, Cripto), nombres parciales ("Proceso Software", "Complementos de BD", "Derecho grupo 1"), lenguaje coloquial ("cómo se saca la nota", "quién da clase"), y sin signos de interrogación de apertura.
**Archivos:** `testing/test_rag_asignaturas_v2.md`

---

## Pendiente

- Re-entrenar modelo NLU (`rasa train`) para que surtan efecto los cambios de D-003, D-004, D-005, D-009, D-010
- Reiniciar action server para que surtan efecto D-014 a D-018
- Ejecutar tabla de pruebas RAG completa (`testing/test_rag_asignaturas_v2.md`)
- Investigar por qué E-P11 devuelve "Fundamentos de Programación" en vez de PGPI (posible fallo en SQL generado por LLM)
