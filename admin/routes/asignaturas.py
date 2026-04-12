from flask import Blueprint, jsonify, request
from admin.db import query, query_one, execute_returning, normalizar
from admin.sevius_scraper import (
    obtener_asignaturas as sevius_asignaturas,
)

bp = Blueprint("asignaturas", __name__)


@bp.route("/asignaturas")
def get_asignaturas():
    titulacion_id = request.args.get("titulacion_id")
    sql = """
        SELECT a.id, a.codigo, a.nombre, a.curso, a.creditos, a.duracion,
               a.tipologia, a.es_formacion_basica, a.es_optativa,
               a.nombre_normalizado, a.activa,
               t.nombre AS titulacion_nombre, t.codigo AS titulacion_codigo
        FROM asignaturas a
        LEFT JOIN titulaciones t ON t.id = a.titulacion_id
    """
    params = []
    if titulacion_id:
        sql += " WHERE a.titulacion_id = %s"
        params.append(titulacion_id)
    sql += " ORDER BY a.curso, a.nombre"
    return jsonify(query(sql, params))


@bp.route("/asignaturas/<asignatura_id>")
def get_asignatura_detail(asignatura_id):
    row = query_one("""
        SELECT a.*, t.nombre AS titulacion_nombre, t.codigo AS titulacion_codigo
        FROM asignaturas a
        LEFT JOIN titulaciones t ON t.id = a.titulacion_id
        WHERE a.id = %s
    """, (asignatura_id,))
    if not row:
        return jsonify({"error": "No encontrada"}), 404
    return jsonify(row)


@bp.route("/asignaturas/sync", methods=["POST"])
def sync_asignaturas():
    """
    Scrape Sevius e inserta en BD las asignaturas nuevas de una titulacion.
    Body: {"titulacion_id": "uuid", "codcentro": "3", "codigo_titulacion_sevius": "205"}
    """
    data = request.get_json(silent=True) or {}
    titulacion_id = data.get("titulacion_id", "").strip()
    codcentro = data.get("codcentro", "").strip()
    codigo_tit = data.get("codigo_titulacion_sevius", "").strip()

    if not titulacion_id or not codcentro or not codigo_tit:
        return jsonify({"error": "titulacion_id, codcentro y codigo_titulacion_sevius son obligatorios"}), 400

    if not query_one("SELECT id FROM titulaciones WHERE id = %s", (titulacion_id,)):
        return jsonify({"error": "Titulacion no encontrada"}), 404

    try:
        asigs_sevius = sevius_asignaturas(codcentro, codigo_tit)
    except Exception as e:
        return jsonify({"error": f"Error consultando Sevius: {e}"}), 502

    if not asigs_sevius:
        return jsonify({"error": "Sevius no devolvio asignaturas para esa combinacion"}), 404

    creadas, existentes = [], []
    for asig in asigs_sevius:
        if query_one("SELECT id FROM asignaturas WHERE codigo = %s", (asig["codigo"],)):
            existentes.append({"codigo": asig["codigo"], "nombre": asig["nombre"]})
            continue
        row = execute_returning("""
            INSERT INTO asignaturas (id, titulacion_id, codigo, nombre, nombre_normalizado, activa)
            VALUES (gen_random_uuid(), %s, %s, %s, %s, true)
            RETURNING id, codigo, nombre
        """, (titulacion_id, asig["codigo"], asig["nombre"], normalizar(asig["nombre"])))
        if row:
            creadas.append(row)

    return jsonify({
        "total_sevius": len(asigs_sevius),
        "creadas": creadas,
        "existentes": existentes,
    }), 201 if creadas else 200
