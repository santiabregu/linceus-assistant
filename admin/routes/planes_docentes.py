from flask import Blueprint, jsonify, request
from admin.db import query

bp = Blueprint("planes_docentes", __name__)


@bp.route("/planes_docentes")
def get_planes_docentes():
    asignatura_id = request.args.get("asignatura_id")
    sql = """
        SELECT pd.id, pd.curso_academico, pd.grupo, pd.coordinador_nombre,
               pd.url_documento, pd.estado_rag,
               a.nombre AS asignatura_nombre, a.codigo AS asignatura_codigo,
               (SELECT COUNT(*) FROM planes_docentes_chunks c WHERE c.plan_docente_id = pd.id) AS num_chunks
        FROM planes_docentes pd
        LEFT JOIN asignaturas a ON a.id = pd.asignatura_id
    """
    params = []
    if asignatura_id:
        sql += " WHERE pd.asignatura_id = %s"
        params.append(asignatura_id)
    sql += " ORDER BY pd.curso_academico DESC, a.nombre, pd.grupo"
    return jsonify(query(sql, params))


@bp.route("/planes_docentes/<plan_id>/chunks")
def get_chunks(plan_id):
    return jsonify(query("""
        SELECT id, seccion, subseccion, contenido, metadata,
               LENGTH(contenido) AS longitud
        FROM planes_docentes_chunks
        WHERE plan_docente_id = %s
        ORDER BY seccion, subseccion
    """, (plan_id,)))
