# Tests

Estructura:

```
tests/
├── plans/                      ← QUÉ se prueba (fichas de tests, no resultados)
│   ├── asignaturas_mejoras_iter1.md      Plan iteración 1 (tests SQL asignaturas)
│   ├── asignaturas_mejoras_iter2.md      Plan iteración 2 (continúa iter1)
│   └── rag_asignaturas_manual.md         Plantilla vacía para tests RAG manuales
│
├── test_stories.yml            Stories para `rasa test core`
├── test_rag.py                 Script de sanity-check del retrieval RAG
├── run_test_plan.py            Runner de tests end-to-end contra Rasa vía REST
│
└── results/                    ← SALIDA de la última ejecución (sobrescrita)
    ├── asignaturas.md          Resumen ejecutado de tests SQL
    ├── asignaturas.json        Datos en bruto del último `run_test_plan.py`
    ├── rag_asignaturas.md      Resumen ejecutado de tests RAG (asignaturas)
    └── stories.md              Resumen de `rasa test core` contra test_stories.yml
```

## Cómo se corre cada test

### 1. `rasa test core` — routing NLU + policy

Valida que los mensajes se clasifican al intent correcto y que el policy predice la acción correcta. **No** evalúa el texto de la respuesta. Rápido (~30s). No necesita action server ni BD.

```bash
TS=$(date +%Y%m%d_%H%M%S); OUT=tests/results/_tmp_stories_$TS
rasa test core \
  --stories tests/test_stories.yml \
  --model models/linceus_v4_7_9.tar.gz \
  --out "$OUT" \
  --fail-on-prediction-errors
# Consolidar el resumen en results/stories.md manualmente o con un script aparte.
# La carpeta $OUT tiene los PNG de confusion matrix + JSONs de métricas crudas.
```

### 2. `run_test_plan.py` — end-to-end SQL (asignaturas)

Envía mensajes reales al bot vía REST y valida el **texto** de la respuesta. Requiere Rasa server + action server corriendo.

```bash
# Terminales aparte:
rasa run --enable-api --cors "*"
rasa run actions

# Runner:
python tests/run_test_plan.py                    # todas las épicas
python tests/run_test_plan.py --only especifica  # solo un conjunto
python tests/run_test_plan.py --runs 3           # más repeticiones
```

Sobrescribe `tests/results/asignaturas.md` y `tests/results/asignaturas.json` en cada ejecución.

### 3. Tests RAG manuales

Plantilla en `plans/rag_asignaturas_manual.md`. Se rellena a mano y el resultado consolidado se guarda en `results/rag_asignaturas.md`.

### 4. Sanity-check RAG

```bash
python tests/test_rag.py
```

Comprueba que el retrieval vectorial devuelve chunks razonables para una pregunta dada (no valida respuestas LLM).

## Regla

- `plans/` no cambia entre ejecuciones (es la fuente de verdad de qué se prueba).
- `results/` contiene **solo la última ejecución** de cada tipo. No se guarda histórico; si necesitas comparar entre ejecuciones, usa git o exporta a otra carpeta fuera de `tests/`.
