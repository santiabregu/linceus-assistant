from flask import Blueprint, jsonify, request
from admin.db import query, query_one, execute_returning, execute, normalizar
from admin.sevius_scraper import (
    obtener_asignaturas as sevius_asignaturas,
)
from admin.us_scraper import buscar_grado, obtener_plan_estudios

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


@bp.route("/asignaturas/<asignatura_id>/profesores")
def get_profesores_de_asignatura(asignatura_id):
    """Profesores que imparten la asignatura según profesor_asignatura."""
    rows = query("""
        SELECT p.id, p.nombre, p.apellidos, p.nombre_completo, p.email,
               p.despacho, p.categoria_academica, p.enlace_perfil,
               d.siglas AS departamento_siglas, d.nombre AS departamento_nombre,
               pa.curso_academico, pa.grupo, pa.es_coordinador, pa.tipo_docencia
        FROM profesor_asignatura pa
        JOIN profesores p ON p.id = pa.profesor_id
        LEFT JOIN departamentos d ON d.id = p.departamento_id
        WHERE pa.asignatura_id = %s AND p.activo = true
        ORDER BY pa.curso_academico DESC, p.apellidos, p.nombre
    """, (asignatura_id,))
    return jsonify(rows)


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
            INSERT INTO asignaturas (id, titulacion_id, codigo, nombre, nombre_normalizado, curso, creditos, duracion, tipologia, es_formacion_basica, es_optativa, activa)  # noqa: E501
            VALUES (gen_random_uuid(), %s, %s, %s, %s, 0, 0, 'Anual', '', false, false, true)
            RETURNING id, codigo, nombre
        """, (titulacion_id, asig["codigo"], asig["nombre"], normalizar(asig["nombre"])))
        if row:
            creadas.append(row)

    return jsonify({
        "total_sevius": len(asigs_sevius),
        "creadas": creadas,
        "existentes": existentes,
    }), 201 if creadas else 200


@bp.route("/asignaturas/enrich", methods=["POST"])
def enrich_asignaturas():
    """
    Busca la titulacion en us.es, extrae el plan de estudios y actualiza
    curso, creditos y tipologia de las asignaturas existentes en BD.
    Body: {"titulacion_id": "uuid"}
    """
    data = request.get_json(silent=True) or {}
    titulacion_id = data.get("titulacion_id", "").strip()

    if not titulacion_id:
        return jsonify({"error": "titulacion_id es obligatorio"}), 400

    tit = query_one("SELECT id, nombre FROM titulaciones WHERE id = %s", (titulacion_id,))
    if not tit:
        return jsonify({"error": "Titulacion no encontrada"}), 404

    # Buscar la URL del grado en us.es
    try:
        url_grado = buscar_grado(tit["nombre"])
    except Exception as e:
        return jsonify({"error": f"Error buscando grado en us.es: {e}"}), 502

    if not url_grado:
        return jsonify({"error": f"No se encontro el grado '{tit['nombre']}' en us.es"}), 404

    # Extraer plan de estudios
    try:
        plan = obtener_plan_estudios(url_grado)
    except Exception as e:
        return jsonify({"error": f"Error extrayendo plan de estudios: {e}"}), 502

    if not plan:
        return jsonify({"error": "No se pudo extraer el plan de estudios de la pagina"}), 404

    # Indexar plan por codigo
    plan_por_codigo = {p["codigo"]: p for p in plan}

    # Actualizar asignaturas existentes
    asigs_bd = query(
        "SELECT id, codigo, nombre FROM asignaturas WHERE titulacion_id = %s",
        (titulacion_id,),
    )

    actualizadas, no_encontradas = [], []
    for asig in asigs_bd:
        datos = plan_por_codigo.get(asig["codigo"])
        if not datos:
            no_encontradas.append({"codigo": asig["codigo"], "nombre": asig["nombre"]})
            continue

        tipologia = datos["tipologia"]
        es_basica = "basica" in tipologia.lower() if tipologia else False
        es_optativa = "optativa" in tipologia.lower() if tipologia else False

        execute("""
            UPDATE asignaturas
            SET curso = %s, creditos = %s, tipologia = %s,
                es_formacion_basica = %s, es_optativa = %s
            WHERE id = %s
        """, (datos["curso"], datos["creditos"], tipologia,
              es_basica, es_optativa, asig["id"]))
        actualizadas.append({
            "codigo": asig["codigo"], "nombre": asig["nombre"],
            "curso": datos["curso"], "creditos": datos["creditos"],
            "tipologia": tipologia,
        })

    return jsonify({
        "url_grado": url_grado,
        "total_bd": len(asigs_bd),
        "actualizadas": actualizadas,
        "no_encontradas": no_encontradas,
    })


@bp.route("/asignaturas/<asignatura_id>", methods=["DELETE"])
def borrar_asignatura(asignatura_id):
    if not query_one("SELECT id FROM asignaturas WHERE id = %s", (asignatura_id,)):
        return jsonify({"error": "Asignatura no encontrada"}), 404

    execute("DELETE FROM asignaturas WHERE id = %s", (asignatura_id,))

    return jsonify({"ok": True})
