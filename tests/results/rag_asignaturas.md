# Resultados de pruebas RAG — Asignaturas v1

**Fecha:** 2026-03-16
**Archivo fuente:** `report_20260316_194239.md` / `results_20260316_194239.json`

## Resumen

| Métrica | Valor |
|---------|-------|
| Total casos | 50 |
| Pasados | 47 |
| Fallidos | 3 |
| Inconsistentes | 0 |
| **Tasa de éxito** | **94.0%** |
| Umbral (>=90%) | CUMPLIDO |

---

## Resultados por caso

| ID | Consulta | Intent detectado | Confianza | Runs OK | Estado | Notas |
|----|---------|-----------------|-----------|---------|--------|-------|
| E-P01 | ¿Cuántos créditos tiene Redes? | consulta_asignatura_especifica | 1.00 | 2/2 | PASS |  |
| E-P02 | ¿En qué curso está Cálculo? | consulta_asignatura_especifica | 1.00 | 2/2 | PASS |  |
| E-P03 | ¿Fundamentos de Programación es anual? | consulta_asignatura_especifica | 1.00 | 2/2 | PASS |  |
| E-P04 | ¿Estadística es obligatoria? | consulta_asignatura_especifica | 1.00 | 2/2 | PASS |  |
| E-P05 | ¿Criptografía es optativa? | consulta_asignatura_especifica | 1.00 | 2/2 | PASS |  |
| E-P06 | ¿De qué cuatrimestre es IA? | consulta_asignatura_especifica | 1.00 | 2/2 | PASS |  |
| E-P07 | Información sobre Sistemas Operativos | consulta_asignatura_especifica | 1.00 | 2/2 | PASS |  |
| E-P08 | Háblame de Diseño y Pruebas | consulta_asignatura_especifica | 1.00 | 3/3 | PASS |  |
| E-P09 | ¿Qué es ADDA? | consulta_asignatura_especifica | 1.00 | 3/3 | PASS |  |
| E-P10 | Dame info del TFG | consulta_asignatura_especifica | 1.00 | 2/2 | PASS |  |
| E-P11 | Datos de PGPI | consulta_asignatura_especifica | 1.00 | 3/3 | PASS |  |
| E-P12 | ¿Qué asignatura es la 2050001? | consulta_asignaturas_listado | 1.00 | 2/2 | PASS |  |
| E-S01 | ¿Y cuántos créditos tiene? | consulta_asignatura_especifica | 1.00 | 2/2 | PASS |  |
| E-S02 | ¿Es obligatoria? | consulta_asignatura_especifica | 1.00 | 2/2 | PASS |  |
| E-S03 | ¿Y esa de qué curso es? | consulta_asignatura_especifica | 1.00 | 2/2 | PASS |  |
| E-N01 | ¿Cuántos créditos tiene Biología? | consulta_asignatura_especifica | 1.00 | 2/2 | PASS |  |
| E-N02 | Información sobre Derecho Penal | consulta_asignatura_especifica | 1.00 | 2/2 | PASS |  |
| E-N03 | ¿Qué es Química Orgánica? | consulta_asignatura_especifica | 1.00 | 2/2 | PASS |  |
| E-T01 | ¿Cuántos créditos tiene Redes? | consulta_asignatura_especifica | 1.00 | 2/2 | PASS |  |
| E-T02 | Info de IA | consulta_asignatura_especifica | 1.00 | 0/2 | FAIL | Esperaba contener 'Inteligencia Artificial'. Response: 'no encontré ninguna asignatura llamada 'info de'...' |
| E-T04 | Dime sobre Redes en ingeniería del software | cambiar_contexto_academico | 0.72 | 0/3 | FAIL | Intent esperado=consulta_asignatura_especifica, obtenido=cambiar_contexto_academico |
| L-P01 | Dame las asignaturas de primero | consulta_asignaturas_listado | 1.00 | 2/2 | PASS |  |
| L-P02 | Asignaturas de cuarto | consulta_asignaturas_listado | 1.00 | 2/2 | PASS |  |
| L-P03 | ¿Qué optativas hay? | consulta_asignaturas_listado | 1.00 | 2/2 | PASS |  |
| L-P04 | Asignaturas anuales | consulta_asignaturas_listado | 1.00 | 2/2 | PASS |  |
| L-P05 | Asignaturas de formación básica | consulta_asignaturas_listado | 1.00 | 2/2 | PASS |  |
| L-P06 | Optativas de cuarto | consulta_asignaturas_listado | 1.00 | 2/2 | PASS |  |
| L-P07 | Obligatorias de segundo | consulta_asignaturas_listado | 1.00 | 2/2 | PASS |  |
| L-P08 | Asignaturas de tercero del primer cuatrimestre | consulta_asignaturas_listado | 1.00 | 3/3 | PASS |  |
| L-P09 | Asignaturas de 12 créditos | consulta_asignaturas_listado | 1.00 | 2/2 | PASS |  |
| L-P10 | Dame todas las asignaturas | consulta_asignaturas_listado | 1.00 | 2/2 | PASS |  |
| L-N01 | Optativas de primero | consulta_asignaturas_listado | 1.00 | 2/2 | PASS |  |
| L-N02 | Asignaturas de quinto curso | consulta_asignaturas_listado | 1.00 | 2/2 | PASS |  |
| L-T01 | Asignaturas de primero | consulta_asignaturas_listado | 1.00 | 2/2 | PASS |  |
| L-T02 | Optativas de cuarto | consulta_asignaturas_listado | 1.00 | 2/2 | PASS |  |
| L-T03 | Dame las asignaturas de segundo | consulta_asignaturas_listado | 1.00 | 2/2 | PASS |  |
| C-P01 | ¿Cuántas asignaturas hay en primero? | consulta_asignaturas_conteo | 1.00 | 2/2 | PASS |  |
| C-P02 | ¿Cuántas optativas hay en cuarto? | consulta_asignaturas_conteo | 1.00 | 2/2 | PASS |  |
| C-P03 | ¿Cuántas asignaturas tiene la carrera? | consulta_asignaturas_conteo | 1.00 | 2/2 | PASS |  |
| C-P04 | ¿Cuántas obligatorias de tercero? | consulta_asignaturas_conteo | 1.00 | 2/2 | PASS |  |
| C-P05 | Número de asignaturas anuales | consulta_asignaturas_listado | 1.00 | 0/2 | FAIL | Intent esperado=consulta_asignaturas_conteo, obtenido=consulta_asignaturas_listado |
| C-P06 | ¿Cuántas de 12 créditos hay? | consulta_asignaturas_conteo | 1.00 | 2/2 | PASS |  |
| C-N01 | ¿Cuántas optativas hay en primero? | consulta_asignaturas_conteo | 1.00 | 2/2 | PASS |  |
| C-N02 | ¿Cuántas asignaturas de quinto? | consulta_asignaturas_conteo | 1.00 | 2/2 | PASS |  |
| C-T01 | ¿Cuántas asignaturas tiene la carrera? | consulta_asignaturas_conteo | 1.00 | 2/2 | PASS |  |
| C-T02 | ¿Cuántas asignaturas tiene la carrera? | consulta_asignaturas_conteo | 1.00 | 2/2 | PASS |  |
| F-01 | ¿Cuál es la capital de Francia? | out_of_scope | 1.00 | 2/2 | PASS |  |
| F-02 | ¿Me puedes contar un chiste? | out_of_scope | 1.00 | 2/2 | PASS |  |
| F-03 | ¿Qué tiempo hará mañana? | out_of_scope | 1.00 | 2/2 | PASS |  |
| F-04 | Quiero pedir una pizza | out_of_scope | 1.00 | 2/2 | PASS |  |

---

## Detalle de fallos

### E-T02

- **Query:** Info de IA
- **Intent esperado:** consulta_asignatura_especifica
- **Contiene esperado:** "Inteligencia Artificial"

- **Run 1**: intent=consulta_asignatura_especifica (conf=1.00), intent_ok=True, entity_ok=True, response_ok=False
  - Respuesta: No encontré ninguna asignatura llamada 'Info de' en Grado en Ingeniería Informática - Tecnologías Informáticas.
- **Run 2**: intent=consulta_asignatura_especifica (conf=1.00), intent_ok=True, entity_ok=True, response_ok=False
  - Respuesta: No encontré ninguna asignatura llamada 'Info de' en Grado en Ingeniería Informática - Tecnologías Informáticas.

### E-T04

- **Query:** Dime sobre Redes en ingeniería del software
- **Intent esperado:** consulta_asignatura_especifica
- **Contiene esperado:** "Redes"

- **Run 1**: intent=cambiar_contexto_academico (conf=0.72), intent_ok=False, entity_ok=True, response_ok=False
  - Respuesta: ✅ Cambiado a: Grado en Ingeniería Informática - Ingeniería del Software
- **Run 2**: intent=cambiar_contexto_academico (conf=0.72), intent_ok=False, entity_ok=True, response_ok=False
  - Respuesta: ✅ Cambiado a: Grado en Ingeniería Informática - Ingeniería del Software
- **Run 3**: intent=cambiar_contexto_academico (conf=0.72), intent_ok=False, entity_ok=True, response_ok=False
  - Respuesta: ✅ Cambiado a: Grado en Ingeniería Informática - Ingeniería del Software

### C-P05

- **Query:** Número de asignaturas anuales
- **Intent esperado:** consulta_asignaturas_conteo

- **Run 1**: intent=consulta_asignaturas_listado (conf=1.00), intent_ok=False, entity_ok=True, response_ok=True
  - Respuesta: Hay una asignatura disponible.
- **Run 2**: intent=consulta_asignaturas_listado (conf=1.00), intent_ok=False, entity_ok=True, response_ok=True
  - Respuesta: Hay una asignatura disponible.
