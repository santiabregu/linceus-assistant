"""Benchmark de latencia y coste del chatbot.

Ejecuta toda la suite de testing_general (143 casos contables + los 10 TF que
están en la build de TestCases del runner) contra el bot vivo, mide:

  - Latencia E2E del turno (tiempo desde POST hasta respuesta).
  - Tokens y latencia de cada llamada Gemini interna (vía
    `LINCEUS_BENCH_METRICS` que escribe `actions/shared/gemini_client.py`).

Salidas (sobrescritas en cada corrida):
  - `tests/results/benchmark_turnos.jsonl`  (1 línea por turno: id, categoría,
    latencia_e2e_ms, ts_inicio, ts_fin, intent, ok)
  - `tests/results/benchmark_gemini.jsonl`  (1 línea por llamada Gemini con
    tokens + latencia, marcada con `turn_id`)
  - `tests/results/benchmark_progreso.txt`  (línea de estado para tail -f)

Uso:
  # Terminales aparte:
  rasa run --enable-api --cors "*"
  rasa run actions

  # Desde la raíz del proyecto:
  python -m tests.scripts.benchmark_costo_latencia --delay 10
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from tests.run_test_plan import build_test_cases, RasaClient  # noqa: E402

OUT_DIR = PROJECT_ROOT / "tests" / "results"
OUT_DIR.mkdir(parents=True, exist_ok=True)
TURNOS_PATH = OUT_DIR / "benchmark_turnos.jsonl"
GEMINI_PATH = OUT_DIR / "benchmark_gemini.jsonl"
PROGRESO_PATH = OUT_DIR / "benchmark_progreso.txt"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay", type=int, default=10,
                        help="Segundos entre turnos (default 10, evita rate-limit).")
    parser.add_argument("--rasa-url", default="http://127.0.0.1:5005",
                        help="URL del servidor Rasa.")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limitar número de casos (0 = todos).")
    args = parser.parse_args()

    # IMPORTANTE: el action server es el que loguea métricas Gemini, no este
    # script. Aquí solo verificamos que `LINCEUS_BENCH_METRICS` apunta al
    # mismo path. El action server tiene que arrancarse con esa env var
    # apuntando a `tests/results/benchmark_gemini.jsonl`.
    metrics_env = os.environ.get("LINCEUS_BENCH_METRICS")
    if metrics_env:
        print(f"[!] LINCEUS_BENCH_METRICS apunta a: {metrics_env}")
    else:
        print("[!] Recordatorio: lanza el action server con")
        print(f"    LINCEUS_BENCH_METRICS={GEMINI_PATH} rasa run actions")
        print("    o el JSONL de Gemini quedará vacío.")
        print()

    # Reset de los archivos de salida
    TURNOS_PATH.write_text("", encoding="utf-8")
    # NO toco GEMINI_PATH desde aquí — lo escribe el action server. Si quieres
    # empezar limpio, bórralo a mano antes de lanzar.

    cases = build_test_cases()
    if args.limit:
        cases = cases[: args.limit]
    print(f"[INFO] {len(cases)} casos cargados, delay={args.delay}s")

    client = RasaClient(args.rasa_url)
    print(f"[INFO] Conectado a {args.rasa_url}")

    t_global_start = time.perf_counter()
    for i, case in enumerate(cases, 1):
        sender_id = f"bench_{case.id}_{int(time.time())}"
        ts_inicio = datetime.now(timezone.utc).isoformat()

        try:
            client.new_conversation(sender_id)
            if case.slot_titulacion:
                client.set_slot(sender_id, "contexto_titulacion", case.slot_titulacion)
            if case.slot_ultimo_nombre:
                client.set_slot(sender_id, "ultimo_nombre_asignatura", case.slot_ultimo_nombre)
            for setup_msg in case.setup_messages:
                client.send_message(sender_id, setup_msg)
                time.sleep(1)

            # Marcador para correlacionar llamadas Gemini con este turno:
            # cada llamada Gemini tiene un `ts` y se cruza por ventana de tiempo.
            t_e2e_start = time.perf_counter()
            responses = client.send_message(sender_id, case.query)
            latencia_e2e_ms = int((time.perf_counter() - t_e2e_start) * 1000)
            ts_fin = datetime.now(timezone.utc).isoformat()

            nlu = client.parse_nlu(case.query)
            intent = nlu.get("intent", {}).get("name")

            num_chars_resp = sum(len(r.get("text", "")) for r in responses)
            ok = bool(responses) and any(r.get("text") for r in responses)

            registro = {
                "turn_id": sender_id,
                "case_id": case.id,
                "category": case.category,
                "subcategory": case.subcategory,
                "query": case.query,
                "ts_inicio": ts_inicio,
                "ts_fin": ts_fin,
                "latencia_e2e_ms": latencia_e2e_ms,
                "intent_detectado": intent,
                "respuesta_chars": num_chars_resp,
                "ok": ok,
            }
        except Exception as e:
            registro = {
                "turn_id": sender_id,
                "case_id": case.id,
                "category": case.category,
                "subcategory": case.subcategory,
                "query": case.query,
                "ts_inicio": ts_inicio,
                "ts_fin": datetime.now(timezone.utc).isoformat(),
                "latencia_e2e_ms": None,
                "intent_detectado": None,
                "respuesta_chars": 0,
                "ok": False,
                "error": str(e)[:200],
            }

        # Escribir incremental: si el script muere, lo ya hecho está salvado.
        with open(TURNOS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")

        elapsed = time.perf_counter() - t_global_start
        eta_s = int(elapsed / i * (len(cases) - i))
        progreso = (
            f"[{i}/{len(cases)}] {case.id} ({case.category}) "
            f"latencia={registro.get('latencia_e2e_ms', '—')}ms "
            f"ok={registro['ok']} "
            f"ETA={eta_s // 60}m{eta_s % 60}s"
        )
        print(progreso)
        PROGRESO_PATH.write_text(progreso + "\n", encoding="utf-8")

        if i < len(cases):
            time.sleep(args.delay)

    total_min = int((time.perf_counter() - t_global_start) / 60)
    final = f"[DONE] {len(cases)} turnos en {total_min} min. JSONL: {TURNOS_PATH}"
    print(final)
    PROGRESO_PATH.write_text(final + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
