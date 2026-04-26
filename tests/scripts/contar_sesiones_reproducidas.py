"""Contador de sesiones del piloto reproducidas y validadas.

Usa la columna `revisada BOOLEAN` de `conversation_log` (poblada desde el panel
admin al cerrar cada sesión auditada) como proxy de "sesión reproducida y
declarada PASS por el evaluador".

Genera dos artefactos en `tests/results/`:
  - sesiones_reproducidas.json (datos crudos)
  - bloque markdown que se inserta en `resumen_testing.md`

Ejecutar desde la raíz del proyecto:
  python -m tests.scripts.contar_sesiones_reproducidas
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from actions.shared.db import db_client


def main() -> None:
    conn = db_client.get_connection()
    if conn is None:
        print("ERROR: no se pudo abrir conexión a la BD", file=sys.stderr)
        sys.exit(1)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                COUNT(DISTINCT session_id) AS total_sesiones,
                COUNT(DISTINCT session_id) FILTER (WHERE revisada) AS sesiones_revisadas,
                COUNT(*) AS total_mensajes,
                MIN(created_at)::TEXT AS primera_sesion,
                MAX(created_at)::TEXT AS ultima_sesion
            FROM conversation_log
        """)
        total, revisadas, mensajes, primera, ultima = cur.fetchone()
        cur.close()
    finally:
        conn.close()

    porcentaje = (revisadas / total * 100) if total else 0.0
    datos = {
        "fecha_consulta": datetime.now().isoformat(timespec="seconds"),
        "total_sesiones": total,
        "sesiones_revisadas": revisadas,
        "porcentaje_revisadas": round(porcentaje, 2),
        "total_mensajes": mensajes,
        "primera_sesion": primera,
        "ultima_sesion": ultima,
    }

    out_dir = PROJECT_ROOT / "tests" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "sesiones_reproducidas.json"
    json_path.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(datos, indent=2, ensure_ascii=False))
    print(f"\nGuardado en {json_path}")


if __name__ == "__main__":
    main()
