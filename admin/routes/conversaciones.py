from flask import Blueprint, jsonify, request
from admin.db import query, execute

bp = Blueprint("conversaciones", __name__)

# NOTA: requiere la columna `revisada BOOLEAN DEFAULT FALSE` en
# conversation_log. Crear una vez a mano:
#   ALTER TABLE conversation_log
#     ADD COLUMN revisada BOOLEAN NOT NULL DEFAULT FALSE;


@bp.route("/conversaciones")
def get_conversaciones():
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)
    total = query("SELECT COUNT(*) AS total FROM conversation_log")[0]["total"]
    rows = query("""
        SELECT id, session_id, user_message, bot_response,
               NULL::TEXT AS intent,
               NULL::DOUBLE PRECISION AS confidence,
               created_at
        FROM conversation_log
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """, (limit, offset))
    return jsonify({"total": total, "rows": rows})


@bp.route("/conversaciones/sesiones")
def get_sesiones():
    """Lista de sesiones agrupadas con conteo y preview."""
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    total = query("""
        SELECT COUNT(DISTINCT session_id) AS total FROM conversation_log
    """)[0]["total"]
    rows = query("""
        SELECT c.session_id,
               COUNT(*) AS num_mensajes,
               MIN(c.created_at) AS inicio,
               MAX(c.created_at) AS fin,
               (SELECT user_message FROM conversation_log c2
                WHERE c2.session_id = c.session_id
                ORDER BY c2.created_at ASC LIMIT 1) AS primer_mensaje,
               (SELECT user_message FROM conversation_log c3
                WHERE c3.session_id = c.session_id
                ORDER BY c3.created_at DESC LIMIT 1) AS ultimo_mensaje,
               BOOL_OR(c.revisada) AS revisada
        FROM conversation_log c
        GROUP BY c.session_id
        ORDER BY fin DESC
        LIMIT %s OFFSET %s
    """, (limit, offset))
    return jsonify({"total": total, "rows": rows})


@bp.route("/conversaciones/sesiones/<session_id>/revisada", methods=["PATCH"])
def set_sesion_revisada(session_id):
    """Marca / desmarca una sesión como revisada (todas sus filas)."""
    data = request.get_json(silent=True) or {}
    revisada = bool(data.get("revisada", True))
    execute(
        "UPDATE conversation_log SET revisada = %s WHERE session_id = %s",
        (revisada, session_id),
    )
    return jsonify({"session_id": session_id, "revisada": revisada})


@bp.route("/conversaciones/sesiones/<session_id>")
def get_sesion_detalle(session_id):
    """Mensajes de una sesion en orden cronologico."""
    rows = query("""
        SELECT id, user_message, bot_response, created_at
        FROM conversation_log
        WHERE session_id = %s
        ORDER BY created_at ASC
    """, (session_id,))
    return jsonify({"session_id": session_id, "mensajes": rows})


@bp.route("/feedback")
def get_feedback():
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)
    total = query("SELECT COUNT(*) AS total FROM feedback")[0]["total"]
    rows = query("""
        SELECT id, session_id, rating, comment, last_user_message, last_bot_response, created_at
        FROM feedback
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """, (limit, offset))
    return jsonify({"total": total, "rows": rows})
