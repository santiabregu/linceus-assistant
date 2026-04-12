from flask import Blueprint, jsonify, request
from admin.db import query, query_one, execute_returning

bp = Blueprint("centros", __name__)


@bp.route("/centros")
def get_centros():
    return jsonify(query("""
        SELECT id, codigo, nombre, nombre_corto, activo,
               (SELECT COUNT(*) FROM titulaciones t WHERE t.centro_id = c.id) AS num_titulaciones
        FROM centros c
        ORDER BY nombre
    """))


@bp.route("/centros", methods=["POST"])
def crear_centro():
    data = request.get_json(silent=True) or {}
    codigo = data.get("codigo", "").strip()
    nombre = data.get("nombre", "").strip()
    if not codigo or not nombre:
        return jsonify({"error": "codigo y nombre son obligatorios"}), 400

    if query_one("SELECT id FROM centros WHERE codigo = %s", (codigo,)):
        return jsonify({"error": f"Ya existe un centro con codigo '{codigo}'"}), 409

    row = execute_returning("""
        INSERT INTO centros (id, codigo, nombre, nombre_corto, activo)
        VALUES (gen_random_uuid(), %s, %s, %s, true)
        RETURNING id, codigo, nombre, nombre_corto
    """, (codigo, nombre, data.get("nombre_corto", "").strip() or nombre))

    return jsonify(row), 201
