"""
Endpoints de preview: consultan Sevius sin tocar la BD.
Utiles para que el admin explore antes de crear entidades.
"""

from flask import Blueprint, jsonify, request
from admin.sevius_scraper import (
    obtener_centros,
    obtener_titulaciones,
    obtener_asignaturas,
)

bp = Blueprint("sevius", __name__)


@bp.route("/sevius/centros")
def get_sevius_centros():
    try:
        return jsonify(obtener_centros())
    except Exception as e:
        return jsonify({"error": f"Error consultando Sevius: {e}"}), 502


@bp.route("/sevius/titulaciones")
def get_sevius_titulaciones():
    codcentro = request.args.get("codcentro")
    if not codcentro:
        return jsonify({"error": "Falta parametro codcentro"}), 400
    try:
        return jsonify(obtener_titulaciones(codcentro))
    except Exception as e:
        return jsonify({"error": f"Error consultando Sevius: {e}"}), 502


@bp.route("/sevius/asignaturas")
def get_sevius_asignaturas():
    codcentro = request.args.get("codcentro")
    titulacion = request.args.get("titulacion")
    if not codcentro or not titulacion:
        return jsonify({"error": "Faltan parametros codcentro y titulacion"}), 400
    try:
        return jsonify(obtener_asignaturas(codcentro, titulacion))
    except Exception as e:
        return jsonify({"error": f"Error consultando Sevius: {e}"}), 502
