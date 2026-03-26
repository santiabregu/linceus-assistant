# Plan de mejoras - Tests Asignaturas v1

Basado en los resultados del 2026-03-12 (36/51 pasados, 70.6%).

---

## ~~1. Acronimos (PGPI, IA en cross-titulación)~~ RESUELTO

**Fix aplicado:** `_expandir_alias` ahora limpia prefijos del NLU ("de PGPI" → "pgpi") antes de buscar en el diccionario de alias. Los alias `pgpi` e `ia` ya existían, el problema era que NLU extraía la entidad con prefijo.

**E-T02 (IA en GII-TI):** El alias se expande correctamente a "inteligencia artificial", pero el LLM genera SQL que devuelve Fundamentos de Programación en vez de IA. Pendiente de verificar tras re-ejecutar con el fix de alias.

---

## ~~2. E-T03: Test de "pedir titulación"~~ RESUELTO

**Fix aplicado:** El bot detecta titulación del contexto vía `_detectar_titulacion_con_llm` o resuelve sin filtro (Redes existe con mismos datos en varias titulaciones). Test cambiado para validar que responda "6" (créditos correctos) en vez de exigir que pida titulación.

---

## ~~3. L-P10: "Dame todas las asignaturas" → intent `pedir_mas_resultados`~~ RESUELTO

**Problema:** La frase "Dame todas las asignaturas" se clasifica como `pedir_mas_resultados` (conf=1.00) en vez de `consulta_asignaturas_listado`. Esto es un problema de NLU: la palabra "todas" es ambigua.

**Fix aplicado:** Añadidos 8 ejemplos con "todas las asignaturas" a `consulta_asignaturas_listado`. Eliminado "todas las asignaturas" de `pedir_mas_resultados` para evitar colisión.

**Acción:**
- [x] Añadir ejemplos de training a `consulta_asignaturas_listado` con la palabra "todas": "Dame todas las asignaturas", "Quiero ver todas las asignaturas", "Listado completo de asignaturas"
- [x] Verificar que no colisione con los ejemplos de `pedir_mas_resultados`
- [ ] Re-entrenar el modelo NLU

---

## ~~4. C-P03, C-T01, C-T02: "¿Cuántas asignaturas tiene la carrera?" → intent `consulta_titulaciones`~~ RESUELTO

**Problema:** La frase se clasifica como `consulta_titulaciones` (conf=0.87) en vez de `consulta_asignaturas_conteo`. La palabra "carrera" confunde al NLU.

**Fix aplicado:** Añadidos 6 ejemplos con "carrera"/"grado" a `consulta_asignaturas_conteo`.

**Acción:**
- [x] Añadir ejemplos de training a `consulta_asignaturas_conteo`: "¿Cuántas asignaturas tiene la carrera?", "¿Cuántas asignaturas tiene el grado?", "Total de asignaturas de la carrera"
- [ ] Re-entrenar el modelo NLU

---

## ~~5. C-P04, C-P05: Conteo clasificado como listado~~ RESUELTO

**Tests afectados:** C-P04 ("¿Cuántas obligatorias de tercero?"), C-P05 ("Número de asignaturas anuales")

**Problema:** El NLU no distingue bien entre conteo y listado. Ambos usan filtros similares, la diferencia es "cuántas" vs "cuáles/dame".

**Fix aplicado:** Añadidos 11 ejemplos de conteo con patrones variados. Añadida regex feature `conteo_signal` para reforzar la distinción. Verificado que listado no contiene señales de conteo.

**Acción:**
- [x] Añadir más ejemplos de training a `consulta_asignaturas_conteo` con patrones variados: "¿Cuántas obligatorias de X?", "Número de asignaturas X"
- [x] Verificar que los ejemplos de `consulta_asignaturas_listado` no incluyan frases de conteo
- [ ] Re-entrenar el modelo NLU

---

## ~~6. F-01, F-02, F-04: Fallback no detectado~~ RESUELTO

**Tests afectados:**
- F-01: "¿Cuál es la capital de Francia?" → `consulta_asignatura_especifica` (conf=1.00)
- F-02: "¿Me puedes contar un chiste?" → `pedir_ayuda` (conf=0.95)
- F-04: "Quiero pedir una pizza" → `bot_challenge` (conf=0.86)

**Problema:** El modelo NLU clasifica preguntas fuera de ámbito con alta confianza en intents existentes. El threshold de fallback no es suficiente.

**Fix aplicado:** Creado intent `out_of_scope` con 30 ejemplos en `data/nlu/general.yml`. Subido threshold de fallback de 0.6 a 0.7 en `config.yml`. Añadida regla en `rules.yml` que mapea `out_of_scope` a `utter_default`. Añadido `out_of_scope` a `domain.yml`.

**Acción:**
- [x] Añadir más ejemplos de training en `nlu_fallback` o `out_of_scope` con preguntas genéricas
- [x] Considerar subir el threshold de fallback en config.yml (actualmente parece estar bajo)
- [x] Alternativa: añadir una capa de validación post-NLU que detecte respuestas fuera de ámbito
- [ ] Re-entrenar el modelo NLU

---

## Resumen de prioridades

| Prioridad | Acción | Tests afectados | Tipo | Estado |
|-----------|--------|-----------------|------|--------|
| ~~Media~~ | ~~Fix alias con prefijos NLU~~ | ~~E-P11,E-T02~~ | ~~Code fix~~ | HECHO |
| ~~Media~~ | ~~Ajustar test sin titulación~~ | ~~E-T03~~ | ~~Test fix~~ | HECHO |
| ~~Alta~~ | ~~Ejemplos conteo + carrera/grado~~ | ~~C-P03,C-P04,C-P05,C-T01,C-T02~~ | ~~NLU training~~ | HECHO (pendiente retrain) |
| ~~Alta~~ | ~~Intent out_of_scope + threshold 0.7~~ | ~~F-01,F-02,F-04~~ | ~~NLU training~~ | HECHO (pendiente retrain) |
| ~~Media~~ | ~~Ejemplos "todas" en listado~~ | ~~L-P10~~ | ~~NLU training~~ | HECHO (pendiente retrain) |
