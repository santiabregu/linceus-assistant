# Resumen — `rasa test core` sobre `tests/test_stories.yml`

**Fecha:** 2026-04-24 11:38
**Modelo:** `models/linceus_v4_7_9.tar.gz` (entrenado 2026-04-24 09:37, tras ampliar NLU con 117 ejemplos nuevos extraídos de `conversation_log`)
**Comando:**

```bash
rasa test core \
  --stories tests/test_stories.yml \
  --model models/linceus_v4_7_9.tar.gz \
  --fail-on-prediction-errors
```

Este fichero contiene **solo el resumen de la última ejecución**. Los artefactos crudos (`story_report.json`, matrices de confusión PNG, etc.) se generan en una carpeta temporal y no se versionan.

## Resultados globales

| Métrica | Valor |
|---|---|
| Conversaciones correctas | **44 / 44** |
| Acciones predichas correctamente | **158 / 158** |
| Accuracy (conversación) | 1.000 |
| Accuracy (acción) | 1.000 |
| Precision / Recall / F1 (weighted) | 1.00 / 1.00 / 1.00 |
| Stories fallidas | 0 |
| Stories con warnings | 0 |
| Exit code | 0 |

El flag `--fail-on-prediction-errors` habría devuelto exit ≠ 0 ante cualquier divergencia. Todas las stories se predijeron correctamente turn a turn.

## Métricas por acción

Soporte = nº de veces que esa acción aparecía como etiqueta correcta en las 44 stories (total 158).

| Acción | N | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| `action_listen` | 79 | 1.00 | 1.00 | 1.00 |
| `action_consulta_profesor` | 18 | 1.00 | 1.00 | 1.00 |
| `action_consulta_especifica` | 13 | 1.00 | 1.00 | 1.00 |
| `action_consulta_horario` | 9 | 1.00 | 1.00 | 1.00 |
| `action_consulta_listado` | 8 | 1.00 | 1.00 | 1.00 |
| `utter_greet` | 7 | 1.00 | 1.00 | 1.00 |
| `action_cambiar_contexto` | 7 | 1.00 | 1.00 | 1.00 |
| `action_consulta_horario_asignatura` | 5 | 1.00 | 1.00 | 1.00 |
| `action_consulta_conteo` | 4 | 1.00 | 1.00 | 1.00 |
| `action_mostrar_todas_asignaturas` | 2 | 1.00 | 1.00 | 1.00 |
| `utter_goodbye` | 2 | 1.00 | 1.00 | 1.00 |
| `action_consulta_titulaciones` | 1 | 1.00 | 1.00 | 1.00 |
| `action_consultar_contexto` | 1 | 1.00 | 1.00 | 1.00 |
| `utter_ayuda` | 1 | 1.00 | 1.00 | 1.00 |
| `utter_iamabot` | 1 | 1.00 | 1.00 | 1.00 |

## Cobertura por épica

Las 23 stories añadidas en esta iteración (10 horarios + 13 profesores, sobre una base previa de 21 stories de asignaturas y flujos básicos) cubren:

**Horarios**
- Horario personal con curso y grupo en la pregunta.
- Horario personal corto tras aclaración del bot (`mi horario` → `curso 3 grupo 2`).
- Follow-up a otro día (reuso de slots `ultimo_curso` / `ultimo_grupo`).
- Horario de asignatura por nombre completo, por alias y con grupo explícito.
- Cruce horario personal → horario de asignatura.
- Cambio de titulación entre dos consultas de horario.
- Asignatura específica seguida de horario de la misma.

**Profesores**
- Email / despacho por nombre del profesor.
- Profesores de una asignatura por alias y por nombre.
- Coordinador / suplente (atajo RAG — D-064).
- Tutorías por profesor y por asignatura.
- Tutorías con typo (`tutuorías de DP1`) — valida detección fuzzy de D-065.
- Profesores de un departamento.
- Follow-ups (`y quién coordina?`, `y su correo?`).
- Cross-domain: ficha de asignatura → `y quién la imparte?`.
- Profesor con asignatura como contexto (`email de Belén que da FP`).

## Comparación con la corrida anterior

Corrida anterior: `tests/results/rasa_stories_20260424_111625/` (11:16, antes del reentreno).

| Métrica | 11:16 | 11:38 |
|---|---:|---:|
| Conversaciones correctas | 44 / 44 | 44 / 44 |
| Acciones correctas | 158 / 158 | 158 / 158 |
| F1 weighted | 1.00 | 1.00 |

Reentrenar con los 117 ejemplos nuevos no ha degradado ninguna predicción sobre el set de stories. Validado el no-regresión.

## Alcance de esta validación — y qué NO prueba

`rasa test core --stories` evalúa dos capas:

1. **NLU**: ¿el mensaje del usuario se clasifica al intent correcto?
2. **Policy (Core)**: dado el histórico de intents + slots, ¿predice la acción correcta?

No evalúa:

- **Contenido textual** de las respuestas (qué dice el bot). Eso lo cubre `tests/run_test_plan.py`, que necesita action server + BD + Gemini corriendo.
- **Routing interno** de los actions (p. ej. que `consulta_profesor` con "coordinador" tome el atajo RAG, o que `_pregunta_sobre_tutorias` detecte el typo).
- **Alucinaciones** del LLM de respuesta.

