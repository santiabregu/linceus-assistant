from flask import Blueprint, jsonify, request
from admin.db import query, query_one, execute_returning, execute

bp = Blueprint("centros", __name__)


@bp.route("/centros")
def get_centros():
    return jsonify(query("""
        SELECT id, codigo, nombre, nombre_corto, codigo_sevius, activo,
               (SELECT COUNT(*) FROM titulaciones t WHERE t.centro_id = c.id) AS num_titulaciones
        FROM centros c
        ORDER BY nombre
    """))


@bp.route("/centros", methods=["POST"])
def crear_centro():
    data = request.get_json(silent=True) or {}
    codigo = data.get("codigo", "").strip()
    nombre = data.get("nombre", "").strip()
    codigo_sevius = data.get("codigo_sevius", "").strip()
    if not codigo or not nombre:
        return jsonify({"error": "codigo y nombre son obligatorios"}), 400

    if query_one("SELECT id FROM centros WHERE codigo = %s", (codigo,)):
        return jsonify({"error": f"Ya existe un centro con codigo '{codigo}'"}), 409

    uni = query_one("SELECT id FROM universidades LIMIT 1")
    if not uni:
        return jsonify({"error": "No hay ninguna universidad en la BD"}), 500

    row = execute_returning("""
        INSERT INTO centros (id, universidad_id, codigo, nombre, nombre_corto, codigo_sevius, activo)
        VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, true)
        RETURNING id, codigo, nombre, nombre_corto, codigo_sevius
    """, (uni["id"], codigo, nombre, data.get("nombre_corto", "").strip() or nombre,
          codigo_sevius or None))

    return jsonify(row), 201


@bp.route("/centros/<centro_id>", methods=["DELETE"])
def borrar_centro(centro_id):
    if not query_one("SELECT id FROM centros WHERE id = %s", (centro_id,)):
        return jsonify({"error": "Centro no encontrado"}), 404

    # Borrar hijos: asignaturas de titulaciones del centro, luego titulaciones
    tits = query("SELECT id FROM titulaciones WHERE centro_id = %s", (centro_id,))
    for t in tits:
        execute("DELETE FROM asignaturas WHERE titulacion_id = %s", (t["id"],))
    execute("DELETE FROM titulaciones WHERE centro_id = %s", (centro_id,))
    execute("DELETE FROM centros WHERE id = %s", (centro_id,))

    return jsonify({"ok": True})
