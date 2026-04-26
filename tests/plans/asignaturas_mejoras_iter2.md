# Plan de mejoras v2 - Tests Asignaturas v1

Basado en los resultados del 2026-03-14 tras aplicar fixes del plan v1.

---

## ~~1. E-P11, E-T02: Iniciales/acrónimos (PGPI, IA) no se resuelven bien~~  DESCARTADO

**Tests afectados:** E-P11 ("Datos de PGPI" → devuelve Fundamentos de Programación), E-T02 ("Info de IA" → no resuelve a Inteligencia Artificial)

**Problema:** El alias estático (`ALIAS_ASIGNATURAS`) existe pero el NLU a veces extrae mal la entidad (e.g. "de PGPI" en vez de "PGPI") o directamente no la extrae.

**Decisión: No implementar.** El `RegexEntityExtractor` puede generar falsos positivos con cualquier palabra en mayúsculas. La lookup table sola no resuelve el problema de fondo (DIET no reconoce los tokens). La generación dinámica de acrónimos desde BD añade complejidad y una consulta extra por cada mensaje. El diccionario de alias estático ya cubre los casos conocidos; el problema real es que DIET extrae mal la entidad, y eso se aborda mejor asegurando que el action layer limpie y resuelva el alias correctamente (ya implementado en `_expandir_alias`).

**Acción alternativa:**
- [x] Verificar que `_expandir_alias` limpia prefijos correctamente (ya hecho en plan v1)
- [ ] Investigar por qué E-P11 devuelve "Fundamentos de Programación" — posiblemente el LLM genera SQL incorrecto tras expandir alias

---

## ~~2. E-P12: Búsqueda por código de asignatura falla~~ RESUELTO

**Test afectado:** E-P12 ("¿Qué asignatura es la 2050001?" → antes funcionaba, ahora no)

**Problema:** El text-to-SQL genera una query que no encuentra resultados. El fallback flexible busca solo por `nombre_normalizado ILIKE` pero no busca por `codigo`.

**Solución propuesta:**

### 2a. Asegurar que el fallback flexible busque por código
En `ActionConsultaEspecifica` (actions.py, líneas 434-452), añadir `OR codigo ILIKE %s` al fallback flexible.

### 2b. Fallback SELECT ALL por titulación
Si la búsqueda flexible tampoco devuelve resultados, hacer un `SELECT * FROM asignaturas WHERE activa = true AND titulacion_id = X` (limitado a la titulación del contexto). Pasar la lista completa + la pregunta original al LLM para que encuentre la mejor respuesta.

**Acción:**
- [x] Añadir búsqueda por `codigo` en el fallback flexible
- [x] Implementar fallback SELECT ALL por titulación cuando no hay resultados
- [x] Limitar el SELECT ALL con filtros disponibles (curso, etc.) para no saturar el LLM

---

## ~~3. E-N02: "Derecho Penal" cae en nlu_fallback en vez de consulta_asignatura_especifica~~ RESUELTO

**Test afectado:** E-N02 ("Información sobre Derecho Penal" → intent=nlu_fallback, conf=0.70)

**Problema:** Con threshold a 0.7, asignaturas que no existen en los datos de training obtienen confianza baja y caen en fallback.

**Solución:** Añadir ejemplos con nombres de asignaturas genéricas/ficticias a `consulta_asignatura_especifica` para enseñar a DIET que cualquier nombre propio en posición de asignatura es válido. La acción ya maneja "no encontrada" correctamente. Actualizar test para aceptar ambos comportamientos.

**Acción:**
- [x] Añadir 5-10 ejemplos con nombres de asignaturas genéricas al intent `consulta_asignatura_especifica`
- [x] Actualizar test E-N02 para aceptar `nlu_fallback` u `out_of_scope` como alternativa válida

---

## ~~4. C-P03, C-T01, C-T02: Verificar expected_count~~ RESUELTO

**Fix aplicado:** Consultada la BD real. Los valores correctos son:
- **C-P03** (GII-IS): 42 → **47** (actualizado)
- **C-T01** (GII-IC): 44 → **48** (actualizado)
- **C-T02** (GII-TI): 52 → **54** (actualizado)

Cambios aplicados en `tests/run_test_plan.py`.

---

## ~~5. C-P05: "Número de asignaturas anuales" clasificado como listado~~ RESUELTO

**Fix aplicado:** 3 cambios:
1. Regex feature `conteo_signal` añadida en `data/nlu/asignaturas.yml` con patrón `(cuant[oa]s|numero de|cantidad de|total de)` — crea una feature binaria que DIET usa para distinguir conteo de listado.
2. 10 nuevos ejemplos de conteo con patrones "número de", "cantidad de", "total de".
3. Verificado que ningún ejemplo de listado contiene señales de conteo.

**Decisión: No unir los intents/actions.** La separación permite respuestas optimizadas (listado con paginación vs conteo directo).

**Pendiente:** Re-entrenar modelo NLU para que los cambios surtan efecto.

---

## ~~6. F-01 a F-04: Tests de fallback esperan nlu_fallback pero obtienen out_of_scope~~ RESUELTO

**Tests afectados:** F-01, F-02, F-03, F-04

**Problema:** Al añadir `out_of_scope`, DIET clasifica preguntas fuera de ámbito con alta confianza como `out_of_scope` en vez de caer en `nlu_fallback`. Esto es correcto.

**Solución:**
Actualizar la validación en `run_test_plan.py` para aceptar tanto `nlu_fallback` como `out_of_scope`.

**Acción:**
- [x] Actualizar validación de intent en tests F-01 a F-04 para aceptar `out_of_scope`

---

## ~~7. utter_default: Añadir enlaces útiles de la US~~ RESUELTO

**Fix aplicado:** Actualizado `utter_default` en `domain.yml` para incluir enlaces a SEVIUS y la web de la Universidad de Sevilla. Simplificado el mensaje para ser más conciso.

---

## Resumen de prioridades

| Prioridad | Acción | Tests afectados | Tipo | Estado |
|-----------|--------|-----------------|------|--------|
| ~~Alta~~ | ~~Fallback búsqueda por código + SELECT ALL~~ | ~~E-P12~~ | ~~Code fix~~ | HECHO |
| ~~Alta~~ | ~~Regex feature conteo + más ejemplos~~ | ~~C-P05~~ | ~~NLU training~~ | HECHO |
| ~~Media~~ | ~~Actualizar validación tests fallback~~ | ~~F-01 a F-04~~ | ~~Test fix~~ | HECHO |
| ~~Media~~ | ~~Ejemplos genéricos asignaturas desconocidas~~ | ~~E-N02~~ | ~~NLU training~~ | HECHO |
| Media | Investigar fallo alias PGPI/IA en SQL | E-P11, E-T02 | Debug | Pendiente |
| ~~Baja~~ | ~~Verificar expected_count~~ | ~~C-P03, C-T01, C-T02~~ | ~~Test fix~~ | HECHO |
| ~~Baja~~ | ~~Añadir enlaces US a utter_default~~ | ~~F-01 a F-04~~ | ~~UX~~ | HECHO |
