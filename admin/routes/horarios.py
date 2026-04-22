from flask import Blueprint, jsonify, request
from admin.db import query, query_one, execute
from admin.horarios_extractores import (
    EXTRACTORES,
    obtener_extractor,
    codigos_soportados,
)

bp = Blueprint("horarios", __name__)


@bp.route("/horarios/extractores")
def listar_extractores():
    """Devuelve los centros (por codigo) que soportan extraccion automatica."""
    return jsonify([
        {"centro_codigo": cod, "descripcion": info["descripcion"], "pdf_url": info.get("pdf_url")}
        for cod, info in EXTRACTORES.items()
    ])


@bp.route("/horarios/centros")
def centros_con_horarios():
    """Centros + numero de horarios + si soportan extraccion."""
    soportados = set(codigos_soportados())
    rows = query("""
        SELECT c.id, c.codigo, c.nombre, c.codigo_us,
               (SELECT COUNT(*) FROM horarios h
                JOIN grupos_clase gc ON gc.id = h.grupo_id
                JOIN asignaturas a ON a.id = gc.asignatura_id
                JOIN titulaciones t ON t.id = a.titulacion_id
                WHERE t.centro_id = c.id) AS num_horarios,
               (SELECT COUNT(*) FROM titulaciones t WHERE t.centro_id = c.id) AS num_titulaciones
        FROM centros c
        ORDER BY c.nombre
    """)
    for r in rows:
        r["extraccion_soportada"] = r["codigo"] in soportados
    return jsonify(rows)


@bp.route("/horarios/titulaciones")
def titulaciones_con_horarios():
    """Titulaciones del centro con numero de horarios por cada una."""
    centro_id = request.args.get("centro_id")
    if not centro_id:
        return jsonify({"error": "centro_id obligatorio"}), 400
    rows = query("""
        SELECT t.id, t.codigo, t.nombre, t.nombre_corto,
               (SELECT COUNT(*) FROM horarios h
                JOIN grupos_clase gc ON gc.id = h.grupo_id
                JOIN asignaturas a ON a.id = gc.asignatura_id
                WHERE a.titulacion_id = t.id) AS num_horarios,
               (SELECT COUNT(DISTINCT gc.codigo) FROM grupos_clase gc
                JOIN asignaturas a ON a.id = gc.asignatura_id
                WHERE a.titulacion_id = t.id) AS num_grupos
        FROM titulaciones t
        WHERE t.centro_id = %s
        ORDER BY t.nombre
    """, (centro_id,))
    return jsonify(rows)


@bp.route("/horarios")
def get_horarios():
    """
    Listado de horarios con filtros opcionales.
    Params: grupo_id, asignatura_id, titulacion_id, centro_id.
    """
    grupo_id = request.args.get("grupo_id")
    asignatura_id = request.args.get("asignatura_id")
    titulacion_id = request.args.get("titulacion_id")
    centro_id = request.args.get("centro_id")

    sql = """
        SELECT h.id, h.dia_semana,
               h.hora_inicio::TEXT AS hora_inicio,
               h.hora_fin::TEXT AS hora_fin,
               COALESCE(au.codigo, au.nombre) AS aula,
               h.notas AS tipo_sesion,
               g.codigo AS grupo_numero, g.cuatrimestre,
               a.id AS asignatura_id,
               a.nombre AS asignatura_nombre, a.codigo AS asignatura_codigo,
               a.curso,
               t.codigo AS titulacion_codigo, t.nombre AS titulacion_nombre
        FROM horarios h
        JOIN grupos_clase g ON g.id = h.grupo_id
        JOIN asignaturas a ON a.id = g.asignatura_id
        JOIN titulaciones t ON t.id = a.titulacion_id
        LEFT JOIN aulas au ON au.id = h.aula_id
    """
    params, conds = [], []
    if grupo_id:
        conds.append("h.grupo_id = %s"); params.append(grupo_id)
    if asignatura_id:
        conds.append("g.asignatura_id = %s"); params.append(asignatura_id)
    if titulacion_id:
        conds.append("a.titulacion_id = %s"); params.append(titulacion_id)
    if centro_id:
        conds.append("t.centro_id = %s"); params.append(centro_id)
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY a.curso, g.codigo, h.dia_semana, h.hora_inicio"
    return jsonify(query(sql, params))


@bp.route("/grupos")
def get_grupos():
    asignatura_id = request.args.get("asignatura_id")
    sql = """
        SELECT g.id, g.codigo AS numero, g.cuatrimestre,
               NULL::TEXT AS aula,
               a.nombre AS asignatura_nombre, a.codigo AS asignatura_codigo,
               (SELECT COUNT(*) FROM horarios h WHERE h.grupo_id = g.id) AS num_horarios
        FROM grupos_clase g
        JOIN asignaturas a ON a.id = g.asignatura_id
    """
    params = []
    if asignatura_id:
        sql += " WHERE g.asignatura_id = %s"; params.append(asignatura_id)
    sql += " ORDER BY a.nombre, g.codigo"
    return jsonify(query(sql, params))


@bp.route("/horarios/generar", methods=["POST"])
def generar_horarios():
    """
    Body: {"centro_id": "uuid", "curso_academico": "2025-26", "limpiar": bool}
    Busca un extractor por `centros.codigo` y lo ejecuta.
    """
    data = request.get_json(silent=True) or {}
    centro_id = data.get("centro_id", "").strip()
    curso = data.get("curso_academico", "2025-26").strip()
    limpiar = bool(data.get("limpiar"))

    if not centro_id:
        return jsonify({"error": "centro_id obligatorio"}), 400

    centro = query_one("SELECT id, codigo, nombre FROM centros WHERE id = %s", (centro_id,))
    if not centro:
        return jsonify({"error": "Centro no encontrado"}), 404

    extractor = obtener_extractor(centro["codigo"])
    if not extractor:
        return jsonify({
            "error": f"No hay extractor de horarios para el centro {centro['codigo']}.",
            "soportados": codigos_soportados(),
        }), 400

    try:
        resultado = extractor["funcion"](
            curso_academico=curso,
            limpiar=limpiar,
            centro_id=centro["id"],
        )
    except Exception as e:
        return jsonify({"error": f"Error ejecutando extractor: {e}"}), 500

    return jsonify(resultado)


@bp.route("/horarios", methods=["DELETE"])
def borrar_horarios():
    """
    Borra horarios/grupos_clase/aulas de un centro (y curso_academico opcional).
    Util antes de regenerar.
    """
    centro_id = request.args.get("centro_id")
    if not centro_id:
        return jsonify({"error": "centro_id obligatorio"}), 400
    curso = request.args.get("curso_academico")

    # Borrar horarios del centro (con filtro opcional de curso via grupos_clase)
    params = [centro_id]
    filtro_curso = ""
    if curso:
        filtro_curso = " AND gc.curso_academico = %s"
        params.append(curso)

    execute(f"""
        DELETE FROM horarios h
        USING grupos_clase gc, asignaturas a, titulaciones t
        WHERE h.grupo_id = gc.id AND gc.asignatura_id = a.id
          AND a.titulacion_id = t.id AND t.centro_id = %s{filtro_curso}
    """, params)

    execute(f"""
        DELETE FROM grupos_clase gc
        USING asignaturas a, titulaciones t
        WHERE gc.asignatura_id = a.id AND a.titulacion_id = t.id
          AND t.centro_id = %s{filtro_curso}
    """, params)

    execute("DELETE FROM aulas WHERE centro_id = %s", (centro_id,))
    return jsonify({"ok": True})
