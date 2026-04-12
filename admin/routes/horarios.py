from flask import Blueprint, jsonify, request
from admin.db import query

bp = Blueprint("horarios", __name__)


@bp.route("/horarios")
def get_horarios():
    grupo_id = request.args.get("grupo_id")
    asignatura_id = request.args.get("asignatura_id")
    sql = """
        SELECT h.id, h.dia_semana,
               h.hora_inicio::TEXT AS hora_inicio,
               h.hora_fin::TEXT AS hora_fin,
               COALESCE(au.codigo, au.nombre) AS aula,
               h.notas AS tipo_sesion,
               g.codigo AS grupo_numero, g.cuatrimestre,
               a.nombre AS asignatura_nombre, a.codigo AS asignatura_codigo
        FROM horarios h
        JOIN grupos_clase g ON g.id = h.grupo_id
        JOIN asignaturas a ON a.id = g.asignatura_id
        LEFT JOIN aulas au ON au.id = h.aula_id
    """
    params = []
    conditions = []
    if grupo_id:
        conditions.append("h.grupo_id = %s")
        params.append(grupo_id)
    if asignatura_id:
        conditions.append("g.asignatura_id = %s")
        params.append(asignatura_id)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY h.dia_semana, h.hora_inicio"
    return jsonify(query(sql, params))


@bp.route("/grupos")
def get_grupos():
    asignatura_id = request.args.get("asignatura_id")
    sql = """
        SELECT g.id,
               g.codigo AS numero,
               g.cuatrimestre,
               NULL::TEXT AS aula,
               a.nombre AS asignatura_nombre, a.codigo AS asignatura_codigo,
               (SELECT COUNT(*) FROM horarios h WHERE h.grupo_id = g.id) AS num_horarios
        FROM grupos_clase g
        JOIN asignaturas a ON a.id = g.asignatura_id
    """
    params = []
    if asignatura_id:
        sql += " WHERE g.asignatura_id = %s"
        params.append(asignatura_id)
    sql += " ORDER BY a.nombre, g.codigo"
    return jsonify(query(sql, params))
