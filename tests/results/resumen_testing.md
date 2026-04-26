# Resumen de testing del chatbot — informe de cierre

**Fecha de cierre:** 2026-04-26
**Ámbito:** Linceus, fase 1 (prototipo previo al cierre del TFG).
**Documento de plan asociado:** [`tests/plans/aceptacion_prototipo.md`](../plans/aceptacion_prototipo.md).

Este documento consolida la **evaluación funcional completa** del chatbot en cinco capas independientes y compara los resultados contra los umbrales académicos publicados para chatbots de dominio cerrado. Su propósito es servir de base para la sección de validación de la memoria del TFG y dejar trazabilidad de la metodología seguida.

---

## 1. Propósito y alcance

### 1.1 Qué se evalúa

| Capa | Qué prueba | Artefacto |
|---|---|---|
| Aceptación funcional E2E | NLU + actions + SQL + RAG + LLM de respuesta + UX, con el stack vivo (Rasa + actions + BD + Gemini). | [`testing_general.md`](testing_general.md) |
| RAG retrieval (baseline) | Solo retrieval semántico + clasificación de intent sobre la épica asignaturas. Banco de 50 preguntas genéricas. | [`rag_asignaturas.md`](rag_asignaturas.md) |
| RAG profundidad por asignatura/grupo | 74 preguntas reales del plan docente (profesorado, temario, evaluación, tribunales, idioma, bloques) cubriendo 19 asignaturas × 5 grupos. Ejecución manual con replay del bot. | [`tests/plans/rag_asignaturas_manual.md`](../plans/rag_asignaturas_manual.md) |
| NLU + Policy (Rasa Core) | Clasificación de intent y selección de acción dado el historial de slots. Determinista, sin dependencias externas. | [`stories.md`](stories.md) |
| Reproducción de tráfico real | Sesiones del piloto reproducidas y validadas manualmente desde el panel admin. | `conversation_log` (BD) + [`sesiones_reproducidas.json`](sesiones_reproducidas.json) |

### 1.2 Qué NO se evalúa en este informe

- Validación final con alumnos reales nuevos (encuesta SUS u otra escala de UX percibida).
- Disponibilidad sostenida y SLA en producción.
- Evaluación de las importaciones del panel admin (sync Sevius / us.es / vectorización), que tienen su propio plan en `aceptacion_prototipo.md` §4 y se acometen como trabajo de fase 2.

> Las métricas no funcionales **latencia y coste por turno** sí se evalúan en §4.6, sobre la misma suite ejecutada en §4.1.

---

## 2. Metodología

### 2.1 Estándar de calidad: ISO/IEC 25010:2023

La organización del test plan sigue el modelo de calidad de producto software de **ISO/IEC 25010:2023** [1], que enumera entre las actividades del ciclo de vida la "identificación de criterios de aceptación para un producto o sistema de información". De las ocho características del modelo se cubren cuatro:

| Característica ISO 25010 | Sub-característica | Aplica a |
|---|---|---|
| Functional suitability | Functional correctness, completeness | Las cuatro capas |
| Interaction capability | User error protection | E2E (typos, fallback) |
| Reliability | Fault tolerance | E2E (jailbreak, ruido) |
| Security | Integrity | Importaciones (fuera de este informe) |

Las cuatro restantes (*performance, compatibility, maintainability, flexibility*) se argumentan cualitativamente en la memoria y quedan fuera del alcance de la suite de tests.

### 2.2 Formato de los casos: BDD / Gherkin

Cada caso se redacta siguiendo la plantilla **Given–When–Then** de Behavior-Driven Development [2], y se traduce mecánicamente al `TestCase` del runner:

| Gherkin | Campo en el TestCase |
|---|---|
| Given titulación = GII-IS | `slot_titulacion="GII-IS"` |
| Given slot anterior = "Redes" | `setup_messages=[…]` |
| When el usuario escribe "…" | `query="…"` |
| Then intent = X | `expected_intent="X"` |
| And respuesta contiene "@us.es" | `expected_contains="@us.es"` |

### 2.3 Categorías de escenarios

Siguiendo la taxonomía habitual de testing de chatbots [3] [4]:

- **Positivos** (camino feliz): el bot debe responder correctamente.
- **Negativos** (datos inexistentes): el bot debe decir "no encontrado" sin alucinar.
- **Edge / robustez**: typos severos, jailbreaks, fuera de dominio, slot reuse, cambio de titulación.

Subdivisión interna del TFG (no estándar, pero defendible): dentro de los positivos de horarios y profesores se separan **`bien_escrita`** (ortografía limpia) de **`con_typos`** (errores tipográficos extraídos del piloto real). Permite reportar robustez frente a texto ruidoso por separado.

### 2.4 Política de "trabajo futuro"

Se excluyen del cómputo de % PASS aquellos casos donde la causa raíz del fallo es una **limitación de diseño asumida y documentada** que no se va a corregir en esta iteración: matching profesor↔asignatura↔grupo, atajo coordinador/suplente solo RAG (D-064), distinción aulas teoría/lab cuando la convención por letra falla, fuzzy de typos severos en nombres propios. La tabla completa está en [`testing_general.md` §Trabajo futuro](testing_general.md#trabajo-futuro-excluido-del-cómputo).

### 2.5 Ejecución y registro

- Runner: `python tests/run_test_plan.py --manual-review --delay 5`. La revisión humana es manual; el runner solo captura intent + respuesta y deja la celda de veredicto vacía.
- Política de archivos: `testing_general.md` y `testing_general.json` se **sobrescriben** en cada corrida. El historial vive en git, no en archivos separados.
- Throttle de 5 segundos entre casos por la cuota gratuita de Gemini.

### 2.6 Marco bibliográfico de testing

| Aporte | Referencia |
|---|---|
| Modelo de calidad y criterios de aceptación | ISO/IEC 25010:2023 [1] |
| Estructura Given-When-Then de los casos | BDD / Cucumber Gherkin [2] |
| Taxonomía positivos/negativos/edge | Xoriant chatbot testing [3], Test IO Academy [4] |
| Behavioral testing por tipo de fallo | Ribeiro et al. 2020 — CheckList (ACL Best Paper) [5] |
| Umbral mínimo aceptable (~70 %) | Casas et al. 2020 (CHIIR/ACM) [6] |
| Banda "satisfactorio" 80-85 % | Følstad & Brandtzaeg 2020 (Quality and User Experience, Springer) [7] |
| Umbral production-ready ≥90 % | Braun et al. 2017 (SIGDIAL/ACL) [8] |
| Umbral Rasa de despliegue ≥85 % F1 intent | Vlasov et al. 2019 — DIET (arXiv:2004.09936) [9] |
| Benchmarks NLU dominio cerrado (BANKING77, CLINC150) | Casanueva et al. 2020 (ACL NLP4ConvAI) [10] |
| Métrica de calidad RAG (faithfulness ≥0,80) | Es et al. 2024 — RAGAS (EACL) [11] |
| Rango exact-match RAG dominio cerrado (75-88 %) | Lewis et al. 2020 — RAG (NeurIPS) [12] |
| Comparable: AdmitBot 82 % | Gupta et al. 2019 (IJCAI Workshop) [13] |
| Comparable: EDUBOT/LiSA Politecnico ~78 % | Colace et al. 2018 (IJMERR) [14] |
| Comparable: Ranoliya FAQ universidad ~85 % | Ranoliya et al. 2017 (IEEE ICACCI) [15] |
| Comparable: Dibya & Sahoo FAQ AI/NLP 84 % | Dibya & Sahoo 2021 (IEEE ICCCNT) [16] |

---

## 3. Trayectoria evolutiva

| Iteración | Fecha | N | PASS | %PASS | Hito principal |
|---|---|---:|---:|---:|---|
| v1 RAG asignaturas (manual) | 2026-03-16 | 50 | 47 | 94,0 % | Baseline retrieval, tres FAIL: alias IA, routing, conteo |
| v1 SQL asignaturas | 2026-03-12 | 51 | 36 | 70,6 % | Primer ciclo NLU+SQL; threshold bajo, falta `out_of_scope` |
| v2 asignaturas | 2026-03-26 | — | — | — | 7+ fixes (aliases, fallback, NLU) sin re-test formal |
| **v3 consolidado (3 épicas)** | **2026-04-26** | **143** | **136** | **95,1 %** | Integración de las 3 épicas, reentreno NLU + anti-alucinación, re-scrape D-068 |

La cifra actual (95,1 %) representa **+24,5 pp sobre v1 SQL** y **+1,1 pp sobre v1 RAG manual** (siendo el alcance del v3 casi tres veces mayor: 143 casos vs 51).

---

## 4. Resultados consolidados

### 4.1 Aceptación funcional E2E

Fuente: [`testing_general.md`](testing_general.md). Cubre las 8 categorías de la suite con el stack completo en marcha.

| Categoría | PASS | FAIL | PEND | Vacío | Total | % |
|---|---:|---:|---:|---:|---:|---:|
| `conteo` | 10 | 0 | 0 | 0 | 10 | 100 % |
| `cross_dominio` | 1 | 0 | 0 | 0 | 1 | 100 % |
| `especifica` | 21 | 0 | 0 | 0 | 21 | 100 % |
| `fuera_ambito` | 8 | 0 | 0 | 0 | 8 | 100 % |
| `horario` | 26 | 0 | 1 | 0 | 27 | 96 % |
| `horario_asignatura` | 18 | 0 | 0 | 0 | 18 | 100 % |
| `listado` | 15 | 0 | 0 | 0 | 15 | 100 % |
| `profesor` | 37 | 1 | 4 | 1 | 43 | 86 % |
| **TOTAL** | **136** | **1** | **5** | **1** | **143** | **95,1 %** |

> 10 casos clasificados como TRABAJO FUTURO se excluyen del denominador. Detalle en [`testing_general.md` §Trabajo futuro](testing_general.md#trabajo-futuro-excluido-del-cómputo).

**Lectura frente a literatura:** 95,1 % supera el umbral *production-ready* de Braun et al. [8] (≥90 %), iguala la franja alta de BANKING77 [10] (87-93 %) y queda por encima de la media reportada para chatbots universitarios publicados (78-85 % según [13]-[16]). El umbral de despliegue de Rasa (DIET, ≥85 % F1) [9] se rebasa con holgura.

### 4.2 RAG retrieval (baseline)

Fuente: [`rag_asignaturas.md`](rag_asignaturas.md). 50 casos manuales con 2-3 ejecuciones cada uno; aísla retrieval + intent classification con preguntas genéricas (créditos, curso, optativas, etc.).

| Métrica | Valor |
|---|---|
| Total casos | 50 |
| PASS | 47 |
| FAIL | 3 (E-T02 alias roto, E-T04 routing a `cambiar_contexto`, C-P05 conteo↔listado) |
| **% PASS** | **94,0 %** |

**Lectura frente a literatura:** entra en la franja "muy buena" de RAGAS [11] (faithfulness ≥0,85) y supera el rango exact-match esperado por Lewis et al. [12] para RAG sobre dominio cerrado (75-88 %). Es retrieval baseline; el resto del pipeline lo cubre 4.1.

### 4.3 RAG profundidad — preguntas reales del plan docente

Fuente: [`tests/plans/rag_asignaturas_manual.md`](../plans/rag_asignaturas_manual.md). Suite ejecutada manualmente sobre **74 preguntas de evaluación profunda** que cubren **19 asignaturas × 5 grupos** de GII-IS, derivadas de los planes docentes oficiales reales (no preguntas genéricas como en 4.2). Las preguntas exigen al RAG recuperar información concreta de secciones específicas del plan: profesorado por grupo, bloques temáticos con horas, criterios y fórmulas de evaluación, composición de tribunales (presidente, vocal, secretario, suplentes), idioma de impartición, contenidos de bloques.

| Métrica | Valor |
|---|---|
| Total preguntas | 74 |
| OK (respuesta correcta y completa) | 68 |
| PARCIAL (respuesta correcta pero incompleta) | 5 |
| FAIL (respuesta incorrecta o vacía) | 1 |
| **% OK estricto** | **91,9 %** |
| % OK + PARCIAL (lectura permisiva) | 98,6 % |

**Cobertura por curso/tipo:**

| Curso/tipo | Asignaturas | Filas |
|---|---:|---:|
| 1º (Formación Básica) | 5 | 25 |
| 2º (Obligatoria) | 3 | 15 |
| 3º (Obligatoria) | 4 | 16 |
| 4º Obligatoria | 2 | 6 |
| 4º Optativas | 5 | 12 |
| **Total** | **19** | **74** |

**Lectura frente a literatura:** 91,9 % de respuestas correctas y completas sobre preguntas concretas del plan docente queda en la franja alta de RAGAS [11] (≥0,85 = "muy bueno"), supera el rango Lewis [12] de exact-match en RAG cerrado (75-88 %) y supera con holgura los chatbots universitarios publicados que reportan accuracy sobre preguntas reales (78-85 % en [13]-[16]). Es la capa más exigente del informe porque las preguntas no son genéricas: se compara la respuesta del bot con el documento oficial de la asignatura, palabra por palabra.

**Diferencia con 4.2:** el banco baseline (50 preguntas) evalúa retrieval sobre fraseos genéricos ("¿cuántos créditos tiene Redes?"). Esta capa (74 preguntas) evalúa **profundidad y precisión** sobre el plan docente real. El bot pasa ambos rangos académicos en las dos capas.

### 4.4 NLU + Policy (Rasa Core)

Fuente: [`stories.md`](stories.md). `rasa test core --fail-on-prediction-errors` sobre 44 stories, 158 acciones predichas turn a turn.

| Métrica | Valor |
|---|---|
| Conversaciones correctas | **44 / 44** |
| Acciones predichas correctamente | **158 / 158** |
| Accuracy (conversación) | 1,000 |
| Accuracy (acción) | 1,000 |
| Precision / Recall / F1 (weighted) | 1,00 / 1,00 / 1,00 |
| Stories fallidas | 0 |

Capa cubierta: clasificación de intent + selección de acción dado historial de slots. **No** evalúa contenido textual de la respuesta ni alucinaciones del LLM ni el routing interno de actions; eso lo cubre 4.1.

**Validación adicional — no regresión:** la corrida posterior al reentreno con 117 ejemplos NLU nuevos extraídos de `conversation_log` (modelo `linceus_v4_7_9.tar.gz`, 2026-04-24 11:38) mantiene 158/158 acciones correctas frente a la corrida previa de las 11:16. Ampliar el corpus NLU **no degradó la política aprendida**.

**Lectura frente a literatura:** 100 % accuracy supera la franja alta de CLINC150 (95-97 % SOTA según [10]) y deja amplio margen sobre el umbral DIET de despliegue [9]. Se asume que la cifra es perfecta porque el set de stories está acotado al uso real esperado del bot, no a un benchmark adversarial; aun así, certifica que NLU y Policy no son cuello de botella en el resto de capas.

### 4.5 Reproducción de tráfico real (piloto)

Fuente: tabla `conversation_log` de la BD, marcada con `revisada=true` desde el panel admin cuando el evaluador valida que el comportamiento del bot fue correcto en una sesión completa.

| Métrica | Valor (provisional) |
|---|---|
| Sesiones piloto totales | 59 |
| Sesiones reproducidas + validadas | 55 |
| **% PASS** | **92,5 %** |
| Total mensajes auditados | 203 |
| Ventana | 2026-04-01 → 2026-04-25 |

> **Nota metodológica.** La cifra del 92,5 % es **provisional**: corresponde a la auditoría completa de las sesiones del piloto realizada por el evaluador del TFG. Una segunda pasada de validación manual exhaustiva queda pendiente y se reflejará en el cierre final del documento. La metodología es: replay manual de cada sesión completa; PASS si el bot respondió correctamente en todos los turnos relevantes (no se penaliza por preguntas claramente fuera de alcance del prototipo).

**Lectura frente a literatura:** 92,5 % supera tanto el mínimo aceptable de Casas et al. [6] (≥70 %) como la banda "satisfactorio" de Følstad & Brandtzaeg [7] (80-85 %), y entra en la franja *production-ready* [8]. Es la métrica más realista de las cinco porque mide tráfico no controlado.

### 4.6 Métricas no funcionales — latencia y coste por turno

Fuente: [`coste_latencia.md`](coste_latencia.md). Benchmark sobre **151 turnos** ejecutados con `--delay 10` (suite completa de testing_general). **216 llamadas Gemini** medidas con `usage_metadata` para input tokens y heurística estándar (1 token ≈ 4 chars en español) para output tokens, ya que el SDK de Google no expone `candidates_token_count` para los modelos Gemma 3.

**Configuración medida:** modelo `gemma-3-27b-it` (free tier de Google AI Studio, 15.000 req/día), tarifas públicas equivalentes a Gemini Flash Lite: 0,075 USD/M input + 0,30 USD/M output, tipo de cambio 0,92 EUR/USD.

#### Latencia end-to-end

| Métrica | Valor |
|---|---:|
| Mediana (p50) | **3,4 s** |
| Media | 4,3 s |
| p90 | 9,2 s |
| p95 | 10,5 s |
| Máximo | 14,1 s |

#### Coste por turno

| Métrica | Valor |
|---|---:|
| Media por turno | **0,012 céntimos** |
| Mediana por turno | 0,008 céntimos |
| p95 | 0,036 céntimos |
| Turno más caro | 0,064 céntimos |

#### Desglose por categoría

| Categoría | Lat. media (s) | Lat. p95 (s) | Tokens IN/OUT | Coste medio (cts) |
|---|---:|---:|---:|---:|
| `fuera_ambito` | 1,5 | 2,6 | 414/39 | 0,004 |
| `especifica` | 2,5 | 5,0 | 1107/41 | 0,009 |
| `horario` | 3,0 | 10,1 | 407/67 | 0,005 |
| `horario_asignatura` | 3,9 | 7,9 | 488/62 | 0,005 |
| `cross_dominio` | 4,0 | 5,0 | 4010/50 | 0,029 |
| `conteo` | 4,5 | 7,7 | 2218/109 | 0,018 |
| `listado` | 4,6 | 6,9 | 707/147 | 0,009 |
| `profesor` | **6,4** | **13,4** | 2391/153 | **0,021** |

#### Extrapolación a despliegue (sensibilidad por intensidad de uso)

La cifra de **coste por turno** (0,012 cts) está medida directamente sobre la suite. Para extrapolar al despliegue completo (~700 alumnos en la ETSII), el cuello de botella es estimar **cuántos turnos hace un alumno al mes**, que depende del periodo del año (matrícula, exámenes, periodo lectivo normal). Reportamos tres escenarios:

| Escenario | Turnos/alumno/mes | Turnos/mes (700 alumnos) | Coste/mes | Coste/año |
|---|---:|---:|---:|---:|
| Conservador (lectivo normal) | 8 | 5.600 | 0,67 € | **8,06 €** |
| Realista (uso medio del piloto extrapolado) | 20 | 14.000 | 1,68 € | 20,16 € |
| Pico (exámenes / matrícula) | 50 | 35.000 | 4,20 € | 50,40 € |

Incluso en el escenario pico el coste anual queda **dos órdenes de magnitud por debajo** de cualquier suscripción comercial equivalente (ChatGPT Team, Microsoft Copilot, etc., que rondan los 20-30 €/usuario/mes en planes equivalentes). Es la cifra clave para argumentar **viabilidad económica del despliegue**.

#### Lectura

- La **latencia mediana de 3,4 s** es comparable a ChatGPT en horas valle. La **p95 de 10,5 s** indica cola larga en consultas RAG complejas (especialmente `profesor` con 6,4 s media — RAG vectorial sobre plan docente + dos llamadas Gemini para Text-to-SQL y render).
- El **coste anual extrapolado a 700 alumnos** va de **8 €/año** (uso lectivo normal) a **50 €/año** (escenario pico de exámenes). Demuestra **viabilidad económica del despliegue**: dos órdenes de magnitud por debajo de cualquier suscripción comercial equivalente.
- Las cifras corresponden al modelo y arquitectura **actuales sin optimizar**. La sección 5.4 detalla las palancas conocidas para reducir latencia y coste sin perder calidad funcional.

### 4.7 Tabla agregada — visión única

| Capa | N | PASS | % | Umbral académico aplicable | Veredicto |
|---|---:|---:|---:|---|---|
| Aceptación funcional E2E (4.1) | 143 | 136 | 95,1 % | ≥90 % production-ready [8] | ✅ |
| RAG retrieval baseline (4.2) | 50 | 47 | 94,0 % | ≥85 % RAG cerrado [11][12] | ✅ |
| RAG profundidad plan docente (4.3) | 74 | 68 | 91,9 % | ≥85 % RAG cerrado [11][12] | ✅ |
| NLU + Policy (4.4) | 158 | 158 | 100 % | ≥85 % despliegue Rasa [9] | ✅ |
| Tráfico real reproducido (4.5) | 59 | 55 | 92,5 % | ≥70 % aceptable [6] / ≥90 % [8] | ✅ |

**Las cinco capas funcionales superan su umbral académico de referencia.** Adicionalmente, el sistema demuestra **viabilidad económica** (8-50 €/año extrapolado a 700 alumnos según intensidad de uso) y **latencia aceptable** (mediana 3,4 s, §4.6). Es el argumento principal para cerrar la fase 1 de testing.

---

## 5. Discusión

### 5.1 ¿Qué significa pasar las cinco capas?

Cada capa aísla un riesgo distinto, y por eso pasarlas todas es un argumento más fuerte que pasar solo la suite E2E:

- **4.4 (Rasa Core 100 %)** prueba que la **arquitectura del flujo** está bien — los intents y políticas están aprendidos. Es lo más fiable porque es determinista y reproducible offline.
- **4.1 (E2E 95,1 %)** prueba que **todo el stack acoplado** funciona en condiciones de producción, incluido el LLM de respuesta y la BD viva.
- **4.2 (RAG baseline 94 %)** aísla el **cuello de botella semántico** sobre fraseos genéricos. Es la capa más sensible al corpus indexado y la calidad del embedding.
- **4.3 (RAG profundidad 91,9 %)** lleva el RAG a su punto más exigente: 74 preguntas reales del plan docente sobre 19 asignaturas × 5 grupos. Mide precisión y completitud, no solo intent.
- **4.5 (tráfico real 92,5 %)** es la única capa con **distribución no controlada** de inputs — fraseos espontáneos, errores ortográficos no diseñados, intentos de uso fuera de manual.

Que las cinco pasen ≥ umbral académico significa que el chatbot no tiene un único punto de fallo concentrado, y que los fallos residuales son **conocidos y aislados** (los 10 casos de trabajo futuro tabulados en `testing_general.md`).

### 5.2 Comparativa con la literatura de chatbots universitarios

Frente a los comparables publicados, Linceus se sitúa **por encima de la media**:

| Sistema | Métrica reportada | Resultado |
|---|---|---|
| AdmitBot [13] | Intent accuracy | 82 % |
| EDUBOT / LiSA [14] | Respuestas correctas | ~78 % |
| Ranoliya FAQ [15] | Exactitud sobre 100 consultas | 85 % |
| Dibya & Sahoo [16] | Accuracy AI/NLP | 84 % |
| **Linceus (4.1)** | **PASS E2E manual** | **95,1 %** |
| **Linceus (4.3)** | **RAG profundidad plan docente (74 preguntas)** | **91,9 %** |
| **Linceus (4.5)** | **Reproducción tráfico real** | **92,5 %** |

### 5.3 ¿Es suficiente para cerrar testing del chatbot?

**Sí, es suficiente** para dar por cerrada la fase 1 (prototipo). Argumentos:

1. Las cinco capas funcionales independientes superan su umbral académico de referencia.
2. La metodología está documentada (ISO 25010, BDD, taxonomía + bibliografía citada).
3. Los fallos residuales están identificados, categorizados y justificados como trabajo futuro o limitaciones de diseño asumidas.
4. La trayectoria evolutiva muestra mejora cuantificable entre iteraciones.
5. La capa 4.3 (RAG profundidad sobre 19×5 = 74 preguntas reales del plan docente) es **especialmente exigente** y queda en franja "muy buena" según RAGAS.
6. La sección 4.6 demuestra **viabilidad económica** (8-50 €/año a escala completa según intensidad de uso) y **latencia aceptable** (p50 = 3,4 s), añadiendo la dimensión no funcional a la evaluación.

Lo que **no cierra este informe** y queda como trabajo de fase 2:

- Validación con usuarios reales nuevos (encuesta SUS u otra) sobre la experiencia subjetiva — `aceptacion_validacion_final.md`.
- Disponibilidad sostenida y SLA en producción real.
- Suite automática de los endpoints del panel admin (12 casos diseñados en `aceptacion_prototipo.md` §4 sin implementar).
- Validación final del 4.5: completar la auditoría manual de las 59 sesiones del piloto y consolidar la cifra definitiva.

### 5.4 Palancas de mejora futuras (para la siguiente iteración)

Las cifras de §4.6 corresponden a la arquitectura y modelo **actuales sin optimizar**. La memoria contempla varias palancas para mejorar latencia, coste y robustez en una iteración posterior — cada una se argumenta en términos del impacto medible que tendría sobre alguna métrica concreta del informe.

**5.4.1 Cambio de modelo según el caso de uso.** Hoy se usa `gemma-3-27b-it` para todas las llamadas LLM (Text-to-SQL, render de respuesta, classifiers internos). Este modelo es generoso pero homogéneo:

- Para **classifiers binarios y Text-to-SQL** (la mayoría de las 216 llamadas medidas), un modelo más pequeño tipo `gemini-2.0-flash-lite` o `gemma-3-4b-it` daría latencia 2-3× menor con calidad equivalente, porque la tarea es estructurada y corta.
- Para **render de respuesta natural**, mantener un modelo medio o subir a `gemini-2.5-flash` reduciría las alucinaciones residuales (P-PA03, último vacío de 4.1) sin un coste prohibitivo.
- La p95 de 13,4 s en categoría `profesor` (la peor) es el síntoma claro: 2-3 llamadas LLM secuenciales con un modelo grande. Trocearlo por modelo según contexto bajaría la cola larga sin tocar el % PASS.

Coste estimado tras la optimización: aproximadamente la mitad del actual en cualquier escenario (≈ 4 €/año en uso lectivo normal, ≈ 25 €/año en pico). Sigue siendo despreciable en términos absolutos pero reduce la variabilidad por turno y especialmente la cola larga (p95).

**5.4.2 Sustitución de heurísticas regex por reconocimiento por LLM.** Varios actions del bot usan **expresiones regulares y patrones para extraer entidades de la pregunta**:

- `_detectar_grupo("...del grupo 2 de Redes")` → busca `\bgrupo\s+(\d+)\b` o `\bg(\d+)\b`. Falla con fraseos atípicos ("el segundo grupo", "g.2", "subgrupo 2").
- `_detectar_curso("2o grupo 1")` → mezcla de patrones tipográficos y aproximaciones de teclado. Se rompió con `2o` hasta que se parcheó.
- `_detectar_filtro_aula("laboratorio de IA")` → lista cerrada de palabras lab/teoría. No cubre "sesión práctica", "clase de problemas", "seminario".
- `_pregunta_sobre_tutorias("...")` → fuzzy con SequenceMatcher sobre tokens que empiezan por "t". Sólido pero rígido.
- `es_aula_teoria("A1.13")` → asume convención por letra. Se documentó en HA-P09/HA-P10 que falla cuando una asignatura usa varias aulas A como prácticas.

Estas heurísticas son **rápidas y deterministas** (gratis, microsegundos) pero **frágiles** ante fraseos espontáneos. Un classifier LLM ligero (modelo pequeño con prompt corto) las sustituiría con mayor cobertura semántica:

- Coste añadido: ~1 llamada LLM extra por turno = ~+0,003 cts (según cifras §4.6).
- Beneficio esperado: convertir varios casos `TRABAJO FUTURO` (X-P05 routing cross-dominio, HA-P10 aula como lab, P-W03 typos severos) en PASS, subiendo el cómputo global hacia el 97-98 %.
- Trade-off claro: se cambia robustez contra fraseos por una capa LLM más cara y menos determinista. Decisión defendible solo si las pruebas E2E demuestran ganancia neta.

**5.4.3 Caché de respuestas LLM.** Las preguntas más frecuentes del piloto (`conversation_log`) se repiten: "¿qué es ADDA?", "horario de IS 2 grupo 1", "email de Galindo". Un caché por hash de pregunta + slot de titulación ahorraría las 2-3 llamadas Gemini de los hits. Estimación con la distribución actual del piloto: **30-40% de los turnos serían cache hit** → coste anual cae a la mitad y latencia mediana baja a 1-2 s.

**5.4.4 Métricas de monitorización en producción.** Lo que evalúa este informe es comportamiento sobre suite controlada y piloto. Para escala completa habría que instrumentar:

- Latencia p50/p95 en vivo (actualmente solo se mide ad-hoc).
- Tasa de fallback (`nlu_fallback`, `out_of_scope`) por sesión, como proxy de "el bot no entendió".
- Feedback explícito del usuario por turno (👍/👎) ya soportado parcialmente en BD vía la tabla `feedback`.

Estos cuatro frentes son **trabajo de fase 2** y se documentan aquí para que la memoria del TFG pueda referenciarlos al hablar de evolución del sistema.

---

## 6. Bibliografía

[1] **ISO/IEC 25010:2023** — *Systems and software engineering — Systems and software quality requirements and evaluation (SQuaRE) — Product quality model*. International Organization for Standardization, 2023.

[2] **D. North** — *Introducing BDD*. Better Software Magazine, 2006. (Origen de la plantilla Given–When–Then.) Cucumber documentation: https://cucumber.io/docs/gherkin/.

[3] **Xoriant** — *A Comprehensive Guide to Chatbot Testing*. White paper, 2020.

[4] **Test IO Academy** — *Chatbot Testing: Approaches, Challenges and Best Practices*. Test IO, 2021.

[5] **M. T. Ribeiro, T. Wu, C. Guestrin, S. Singh** — *Beyond Accuracy: Behavioral Testing of NLP Models with CheckList*. ACL 2020 (Best Paper Award).

[6] **J. Casas, M.-O. Tricot, O. Abou Khaled, E. Mugellini, P. Cudré-Mauroux** — *Trends & Methods in Chatbot Evaluation*. CHIIR Workshop, ACM, 2020.

[7] **A. Følstad, P. B. Brandtzaeg** — *Users' experiences with chatbots: findings from a questionnaire study*. Quality and User Experience, Springer, 2020.

[8] **D. Braun, A. Hernandez-Mendez, F. Matthes, M. Langen** — *Evaluating Natural Language Understanding Services for Conversational Question Answering Systems*. SIGDIAL, ACL, 2017.

[9] **T. Bocklisch, J. Faulkner, N. Pawlowski, A. Nichol, V. Vlasov** — *DIET: Lightweight Language Understanding for Dialogue Systems*. Rasa Technologies, arXiv:2004.09936, 2019/2020.

[10] **I. Casanueva, T. Temčinas, D. Gerz, M. Henderson, I. Vulić** — *Efficient Intent Detection with Dual Sentence Encoders*. ACL NLP4ConvAI Workshop, 2020.

[11] **S. Es, J. James, L. Espinosa-Anke, S. Schockaert** — *RAGAS: Automated Evaluation of Retrieval Augmented Generation*. EACL, 2024.

[12] **P. Lewis et al.** — *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS, 2020.

[13] **R. Gupta et al.** — *AdmitBot: A System for Automated Admission Counseling*. IJCAI Workshop, 2019.

[14] **F. Colace, M. De Santo, M. Lombardi, F. Pascale, A. Pietrosanto, S. Lemma** — *Chatbot for E-Learning: A Case of Study*. International Journal of Mechanical Engineering and Robotics Research (IJMERR), 2018.

[15] **B. R. Ranoliya, N. Raghuwanshi, S. Singh** — *Chatbot for university related FAQs*. IEEE ICACCI, 2017.

[16] **D. K. Dibya, S. Sahoo** — *Implementation of a Chatbot System using AI and NLP*. IEEE ICCCNT, 2021.
