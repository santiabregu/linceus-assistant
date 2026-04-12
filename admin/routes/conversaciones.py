from flask import Blueprint, jsonify, request
from admin.db import query

bp = Blueprint("conversaciones", __name__)


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
