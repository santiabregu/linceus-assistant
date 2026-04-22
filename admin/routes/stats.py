from flask import Blueprint, jsonify
from admin.db import query, get_conn

bp = Blueprint("stats", __name__)


@bp.route("/stats")
def get_stats():
    stats = {}
    for table, key in [
        ("centros", "centros"),
        ("titulaciones", "titulaciones"),
        ("asignaturas", "asignaturas"),
        ("profesores", "profesores"),
        ("grupos_clase", "grupos"),
        ("horarios", "horarios"),
        ("planes_docentes", "planes_docentes"),
        ("planes_docentes_chunks", "chunks"),
        ("conversation_log", "conversaciones"),
        ("feedback", "feedback"),
    ]:
        try:
            stats[key] = query(f"SELECT COUNT(*) AS c FROM {table}")[0]["c"]
        except Exception:
            stats[key] = 0
    return jsonify(stats)


@bp.route("/health")
def health():
    try:
        conn = get_conn()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
