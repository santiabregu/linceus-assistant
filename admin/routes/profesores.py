from flask import Blueprint, jsonify, request
from admin.db import query

bp = Blueprint("profesores", __name__)


@bp.route("/profesores")
def get_profesores():
    departamento = request.args.get("departamento")
    sql = """
        SELECT p.id, p.nombre, p.apellidos, p.email, p.despacho,
               p.categoria_academica, p.enlace_perfil,
               d.siglas AS departamento
        FROM profesores p
        LEFT JOIN departamentos d ON p.departamento_id = d.id
    """
    params = []
    if departamento:
        sql += " WHERE d.siglas = %s"
        params.append(departamento)
    sql += " ORDER BY apellidos, nombre"
    return jsonify(query(sql, params))


@bp.route("/departamentos")
def get_departamentos():
    return jsonify(query("""
        SELECT d.siglas AS departamento, COUNT(p.id) AS num_profesores
        FROM departamentos d
        LEFT JOIN profesores p ON p.departamento_id = d.id
        WHERE d.activo = true
        GROUP BY d.siglas
        ORDER BY d.siglas
    """))
