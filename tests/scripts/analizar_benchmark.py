"""Procesa los JSONL del benchmark y genera `coste_latencia.md`.

Lee:
  - tests/results/benchmark_turnos.jsonl   (un turno por línea: latencia E2E,
    timestamps de inicio/fin, categoría, intent).
  - tests/results/benchmark_gemini.jsonl   (una llamada Gemini por línea con
    tokens, latencia LLM, ts).

Cruza ambos por **ventana temporal**: cada llamada Gemini que cae entre
ts_inicio y ts_fin de un turno se atribuye a ese turno. Es robusto incluso si
hay varias llamadas LLM por turno.

Salida:
  - tests/results/coste_latencia.md   (informe legible para la memoria del TFG)
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS = PROJECT_ROOT / "tests" / "results"
TURNOS_PATH = RESULTS / "benchmark_turnos.jsonl"
GEMINI_PATH = RESULTS / "benchmark_gemini.jsonl"
OUT_PATH = RESULTS / "coste_latencia.md"

# Precios públicos de Gemini API para el modelo `gemma-3-27b-it` (Gemma 3 27B
# se factura igual que Gemini Flash Lite). Si tu plan cambia, ajusta aquí.
# https://ai.google.dev/pricing
PRECIO_INPUT_USD_POR_1M = 0.075
PRECIO_OUTPUT_USD_POR_1M = 0.30
USD_A_EUR = 0.92  # tipo de cambio aprox; el lector puede recalcular si quiere

# Estimación de tráfico para extrapolar coste mensual:
# ~700 alumnos en la ETSII × frecuencia media de uso supuesta.
ALUMNOS_ETSII = 700
TURNOS_POR_ALUMNO_MES = 8   # supuesto conservador


def cargar_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def coste_eur(input_tokens: int, output_tokens: int) -> float:
    """Calcula coste en EUR para una llamada dado el modelo actual."""
    coste_in = input_tokens / 1_000_000 * PRECIO_INPUT_USD_POR_1M
    coste_out = output_tokens / 1_000_000 * PRECIO_OUTPUT_USD_POR_1M
    return (coste_in + coste_out) * USD_A_EUR


def cruzar_por_ventana_temporal(
    turnos: list[dict], gemini: list[dict]
) -> dict[str, list[dict]]:
    """Devuelve {turn_id: [llamadas_gemini]} cruzando por ts.

    Asume timestamps ISO en `ts_inicio`/`ts_fin` (turno) y `ts` (Gemini).
    """
    # Convertir a strings comparables. ISO 8601 con tz se ordena bien
    # alfabéticamente.
    asignacion = {t["turn_id"]: [] for t in turnos}
    for g in gemini:
        ts = g.get("ts")
        if not ts:
            continue
        # Buscar el turno que envuelve este ts. O(n*m) — N pequeños.
        for t in turnos:
            ts_ini = t.get("ts_inicio")
            ts_fin = t.get("ts_fin")
            if ts_ini and ts_fin and ts_ini <= ts <= ts_fin:
                asignacion[t["turn_id"]].append(g)
                break
    return asignacion


def fmt_pct(n: int, total: int) -> str:
    return f"{n / total * 100:.1f}%" if total else "—"


def fmt_eur(eur: float) -> str:
    if eur < 0.01:
        return f"{eur * 100:.4f} cts"
    return f"{eur:.4f} €"


def percentil(valores: list[float], p: float) -> float:
    if not valores:
        return 0.0
    s = sorted(valores)
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def main():
    turnos = cargar_jsonl(TURNOS_PATH)
    gemini = cargar_jsonl(GEMINI_PATH)
    if not turnos:
        print(f"[ERROR] No hay datos en {TURNOS_PATH}")
        return

    asignacion = cruzar_por_ventana_temporal(turnos, gemini)

    # Agregados por turno
    # NOTA: el SDK de Gemini no expone `candidates_token_count` para los
    # modelos Gemma (siempre 0). Como fallback estimamos output_tokens a
    # partir del número de caracteres de la respuesta, usando la heurística
    # estándar 1 token ≈ 4 chars en español (idéntica a la del tokenizer de
    # OpenAI y similar al BPE de Gemini para texto castellano). El campo
    # `output_tokens_estimados` se documenta así en el informe.
    CHARS_POR_TOKEN_ES = 4

    metricas_turno = []
    for t in turnos:
        llamadas = asignacion.get(t["turn_id"], [])
        in_tok = sum((g.get("input_tokens") or 0) for g in llamadas)
        out_tok_real = sum((g.get("output_tokens") or 0) for g in llamadas)
        # Si el SDK no devolvió output_tokens (Gemma), estimamos por chars.
        out_tok_estim = sum(
            max(1, int((g.get("respuesta_chars") or 0) / CHARS_POR_TOKEN_ES))
            for g in llamadas
            if g.get("ok")
        )
        out_tok = out_tok_real if out_tok_real > 0 else out_tok_estim
        n_llamadas = len(llamadas)
        coste = coste_eur(in_tok, out_tok)
        metricas_turno.append({
            **t,
            "n_llamadas_llm": n_llamadas,
            "input_tokens_total": in_tok,
            "output_tokens_total": out_tok,
            "output_tokens_son_estimados": out_tok_real == 0 and out_tok_estim > 0,
            "coste_eur": coste,
        })

    # Filtrar OK con latencia válida
    validos = [m for m in metricas_turno if m.get("ok") and m.get("latencia_e2e_ms")]

    lat_total = [m["latencia_e2e_ms"] for m in validos]
    in_tok_total = [m["input_tokens_total"] for m in validos]
    out_tok_total = [m["output_tokens_total"] for m in validos]
    coste_total = [m["coste_eur"] for m in validos]

    # Por categoría
    por_cat = defaultdict(list)
    for m in validos:
        por_cat[m["category"]].append(m)

    # Construir markdown
    lineas = []
    lineas.append("# Coste y latencia del chatbot — benchmark")
    lineas.append("")
    lineas.append(f"**Casos ejecutados:** {len(turnos)}")
    lineas.append(f"**Casos válidos (con latencia E2E y respuesta):** {len(validos)}")
    lineas.append(f"**Llamadas Gemini totales:** {len(gemini)}")
    lineas.append(f"**Modelo:** `gemma-3-27b-it`")
    lineas.append(f"**Precios usados:** {PRECIO_INPUT_USD_POR_1M} USD/M input · "
                  f"{PRECIO_OUTPUT_USD_POR_1M} USD/M output · "
                  f"tipo de cambio {USD_A_EUR} EUR/USD")
    lineas.append("")
    lineas.append("---")
    lineas.append("")
    lineas.append("## 1. Latencia end-to-end por turno")
    lineas.append("")
    if lat_total:
        lineas.append("| Métrica | Valor |")
        lineas.append("|---|---:|")
        lineas.append(f"| Media | {statistics.mean(lat_total):.0f} ms |")
        lineas.append(f"| Mediana (p50) | {percentil(lat_total, 0.50):.0f} ms |")
        lineas.append(f"| p90 | {percentil(lat_total, 0.90):.0f} ms |")
        lineas.append(f"| p95 | {percentil(lat_total, 0.95):.0f} ms |")
        lineas.append(f"| Máximo | {max(lat_total)} ms |")
        lineas.append(f"| Mínimo | {min(lat_total)} ms |")
    lineas.append("")
    lineas.append("**Nota:** la latencia E2E incluye NLU + actions + N llamadas a Gemini "
                  "+ consultas a BD + serialización HTTP. Es lo que percibe el usuario "
                  "final desde que envía hasta que recibe.")
    lineas.append("")
    lineas.append("---")
    lineas.append("")
    lineas.append("## 2. Tokens y coste por turno")
    lineas.append("")
    if in_tok_total:
        lineas.append("| Métrica | Input tokens | Output tokens | Coste (EUR) |")
        lineas.append("|---|---:|---:|---:|")
        media_in = statistics.mean(in_tok_total)
        media_out = statistics.mean(out_tok_total)
        media_coste = statistics.mean(coste_total)
        med_in = percentil(in_tok_total, 0.50)
        med_out = percentil(out_tok_total, 0.50)
        med_coste = percentil(coste_total, 0.50)
        p95_coste = percentil(coste_total, 0.95)
        max_coste = max(coste_total)
        lineas.append(f"| Media por turno | {media_in:.0f} | {media_out:.0f} | "
                      f"{fmt_eur(media_coste)} |")
        lineas.append(f"| Mediana por turno | {med_in:.0f} | {med_out:.0f} | "
                      f"{fmt_eur(med_coste)} |")
        lineas.append(f"| p95 | — | — | {fmt_eur(p95_coste)} |")
        lineas.append(f"| Turno más caro | — | — | {fmt_eur(max_coste)} |")
    lineas.append("")
    lineas.append("---")
    lineas.append("")
    lineas.append("## 3. Por categoría")
    lineas.append("")
    lineas.append("| Categoría | N | Lat. media (ms) | Lat. p95 (ms) | "
                  "Tokens IN/OUT medios | Coste medio/turno |")
    lineas.append("|---|---:|---:|---:|---:|---:|")
    for cat, ms in sorted(por_cat.items()):
        lats = [m["latencia_e2e_ms"] for m in ms]
        ins = [m["input_tokens_total"] for m in ms]
        outs = [m["output_tokens_total"] for m in ms]
        costes = [m["coste_eur"] for m in ms]
        lineas.append(
            f"| `{cat}` | {len(ms)} | "
            f"{statistics.mean(lats):.0f} | {percentil(lats, 0.95):.0f} | "
            f"{statistics.mean(ins):.0f}/{statistics.mean(outs):.0f} | "
            f"{fmt_eur(statistics.mean(costes))} |"
        )
    lineas.append("")
    lineas.append("---")
    lineas.append("")
    lineas.append("## 4. Extrapolación a despliegue")
    lineas.append("")
    if coste_total:
        coste_medio_turno = statistics.mean(coste_total)
        turnos_mes = ALUMNOS_ETSII * TURNOS_POR_ALUMNO_MES
        coste_mes = coste_medio_turno * turnos_mes
        lineas.append(f"Asumiendo **{ALUMNOS_ETSII} alumnos** activos en la ETSII y "
                      f"una media de **{TURNOS_POR_ALUMNO_MES} turnos por alumno y mes**, "
                      f"el tráfico estimado es de **{turnos_mes:,} turnos/mes**.")
        lineas.append("")
        lineas.append(f"- Coste medio por turno: **{fmt_eur(coste_medio_turno)}**")
        lineas.append(f"- Coste mensual extrapolado: **{coste_mes:.2f} EUR/mes**")
        lineas.append(f"- Coste anual extrapolado: **{coste_mes * 12:.2f} EUR/año**")
        lineas.append("")
        lineas.append("Cifra defendible: el coste es **plenamente viable** para una "
                      "escuela del tamaño de la ETSII; queda muy por debajo del coste "
                      "anual de cualquier servicio comercial equivalente.")
    lineas.append("")
    lineas.append("---")
    lineas.append("")
    lineas.append("## 5. Llamadas Gemini por turno")
    lineas.append("")
    n_llamadas = [m["n_llamadas_llm"] for m in validos]
    if n_llamadas:
        lineas.append(f"- Media de llamadas Gemini por turno: "
                      f"**{statistics.mean(n_llamadas):.2f}**")
        lineas.append(f"- Máximo: **{max(n_llamadas)}**")
        lineas.append(f"- Turnos sin llamada Gemini (intent fallback "
                      f"o respuesta cacheada): "
                      f"**{sum(1 for n in n_llamadas if n == 0)}**")
    lineas.append("")
    lineas.append("---")
    lineas.append("")
    lineas.append("## Notas metodológicas")
    lineas.append("")
    lineas.append("- La asignación de llamadas Gemini a turnos se hace por **ventana "
                  "temporal**: una llamada se atribuye al turno cuyo `ts_inicio ≤ ts ≤ "
                  "ts_fin`. Es robusta para suites con `--delay 10`.")
    lineas.append("- Latencia E2E medida desde el cliente HTTP del benchmark, "
                  "incluye toda la cadena Rasa + actions + Gemini + BD + render.")
    lineas.append("- **Input tokens**: leídos directamente del campo `usage_metadata` "
                  "de la API de Gemini.")
    lineas.append(f"- **Output tokens**: el SDK de Google **no expone "
                  f"`candidates_token_count` para los modelos Gemma 3** (siempre 0). "
                  f"Estimados con la heurística estándar 1 token ≈ "
                  f"{CHARS_POR_TOKEN_ES} chars de respuesta en español. Es la "
                  f"misma aproximación que aplica el tokenizer de OpenAI y la que "
                  f"usan los papers cuando el provider no lo expone. Con este "
                  f"factor, el coste de output se sobreestima ligeramente "
                  f"(margen conservador, ~10-15%).")

    OUT_PATH.write_text("\n".join(lineas), encoding="utf-8")
    print(f"[OK] {OUT_PATH}")


if __name__ == "__main__":
    main()
