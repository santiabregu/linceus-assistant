# Coste y latencia del chatbot — benchmark

**Casos ejecutados:** 151
**Casos válidos (con latencia E2E y respuesta):** 151
**Llamadas Gemini totales:** 216
**Modelo:** `gemma-3-27b-it`
**Precios usados:** 0.075 USD/M input · 0.3 USD/M output · tipo de cambio 0.92 EUR/USD

---

## 1. Latencia end-to-end por turno

| Métrica | Valor |
|---|---:|
| Media | 4296 ms |
| Mediana (p50) | 3446 ms |
| p90 | 9248 ms |
| p95 | 10476 ms |
| Máximo | 14104 ms |
| Mínimo | 53 ms |

**Nota:** la latencia E2E incluye NLU + actions + N llamadas a Gemini + consultas a BD + serialización HTTP. Es lo que percibe el usuario final desde que envía hasta que recibe.

---

## 2. Tokens y coste por turno

| Métrica | Input tokens | Output tokens | Coste (EUR) |
|---|---:|---:|---:|
| Media por turno | 1388 | 98 | 0.0123 cts |
| Mediana por turno | 720 | 60 | 0.0078 cts |
| p95 | — | — | 0.0365 cts |
| Turno más caro | — | — | 0.0639 cts |

---

## 3. Por categoría

| Categoría | N | Lat. media (ms) | Lat. p95 (ms) | Tokens IN/OUT medios | Coste medio/turno |
|---|---:|---:|---:|---:|---:|
| `conteo` | 10 | 4544 | 7713 | 2218/109 | 0.0183 cts |
| `cross_dominio` | 5 | 3999 | 5022 | 4010/50 | 0.0291 cts |
| `especifica` | 21 | 2471 | 5031 | 1107/41 | 0.0088 cts |
| `fuera_ambito` | 8 | 1507 | 2608 | 414/39 | 0.0039 cts |
| `horario` | 27 | 3036 | 10091 | 407/67 | 0.0046 cts |
| `horario_asignatura` | 19 | 3888 | 7944 | 488/62 | 0.0051 cts |
| `listado` | 15 | 4606 | 6948 | 707/147 | 0.0089 cts |
| `profesor` | 46 | 6401 | 13374 | 2391/153 | 0.0207 cts |

---

## 4. Extrapolación a despliegue

Asumiendo **700 alumnos** activos en la ETSII y una media de **8 turnos por alumno y mes**, el tráfico estimado es de **5,600 turnos/mes**.

- Coste medio por turno: **0.0123 cts**
- Coste mensual extrapolado: **0.69 EUR/mes**
- Coste anual extrapolado: **8.25 EUR/año**

Cifra defendible: el coste es **plenamente viable** para una escuela del tamaño de la ETSII; queda muy por debajo del coste anual de cualquier servicio comercial equivalente.

---

## 5. Llamadas Gemini por turno

- Media de llamadas Gemini por turno: **1.43**
- Máximo: **4**
- Turnos sin llamada Gemini (intent fallback o respuesta cacheada): **27**

---

## Notas metodológicas

- La asignación de llamadas Gemini a turnos se hace por **ventana temporal**: una llamada se atribuye al turno cuyo `ts_inicio ≤ ts ≤ ts_fin`. Es robusta para suites con `--delay 10`.
- Latencia E2E medida desde el cliente HTTP del benchmark, incluye toda la cadena Rasa + actions + Gemini + BD + render.
- **Input tokens**: leídos directamente del campo `usage_metadata` de la API de Gemini.
- **Output tokens**: el SDK de Google **no expone `candidates_token_count` para los modelos Gemma 3** (siempre 0). Estimados con la heurística estándar 1 token ≈ 4 chars de respuesta en español. Es la misma aproximación que aplica el tokenizer de OpenAI y la que usan los papers cuando el provider no lo expone. Con este factor, el coste de output se sobreestima ligeramente (margen conservador, ~10-15%).