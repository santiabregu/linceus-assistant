from flask import Blueprint, jsonify, request
from admin.db import query, query_one, execute_returning

bp = Blueprint("titulaciones", __name__)


@bp.route("/titulaciones")
def get_titulaciones():
    centro_id = request.args.get("centro_id")
    sql = """
        SELECT t.id, t.codigo, t.nombre, t.nombre_corto, t.tipo,
               t.plan_estudios_anio, t.creditos_totales, t.duracion_anios,
               t.requisito_idioma, t.activa,
               c.nombre AS centro_nombre,
               (SELECT COUNT(*) FROM asignaturas a WHERE a.titulacion_id = t.id) AS num_asignaturas
        FROM titulaciones t
        LEFT JOIN centros c ON c.id = t.centro_id
    """
    params = []
    if centro_id:
        sql += " WHERE t.centro_id = %s"
        params.append(centro_id)
    sql += " ORDER BY t.nombre"
    return jsonify(query(sql, params))


@bp.route("/titulaciones", methods=["POST"])
def crear_titulacion():
    data = request.get_json(silent=True) or {}
    centro_id = data.get("centro_id", "").strip()
    codigo = data.get("codigo", "").strip()
    nombre = data.get("nombre", "").strip()
    if not centro_id or not codigo or not nombre:
        return jsonify({"error": "centro_id, codigo y nombre son obligatorios"}), 400

    if not query_one("SELECT id FROM centros WHERE id = %s", (centro_id,)):
        return jsonify({"error": "Centro no encontrado"}), 404

    if query_one("SELECT id FROM titulaciones WHERE codigo = %s", (codigo,)):
        return jsonify({"error": f"Ya existe titulacion con codigo '{codigo}'"}), 409

    row = execute_returning("""
        INSERT INTO titulaciones (
            id, centro_id, codigo, nombre, nombre_corto, tipo,
            creditos_totales, duracion_anios, activa
        ) VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, true)
        RETURNING id, codigo, nombre, nombre_corto
    """, (
        centro_id, codigo, nombre,
        data.get("nombre_corto", "").strip() or nombre,
        data.get("tipo", "GRADO"),
        data.get("creditos_totales", 240),
        data.get("duracion_anios", 4),
    ))

    return jsonify(row), 201
