import time
from flask import Blueprint, jsonify, request
from admin.db import query, query_one, execute_returning, execute, normalizar
from admin.us_directorio_scraper import (
    obtener_departamentos_de_centro,
    buscar_profesores,
    obtener_perfil_profesor,
    PAUSA,
)

bp = Blueprint("profesores", __name__)

SIN_DEPTO_KEY = "__sin_departamento__"


# ──────────────────────────────────────────────────────────────────────────
#  Lecturas
# ──────────────────────────────────────────────────────────────────────────

@bp.route("/profesores")
def get_profesores():
    departamento_id = request.args.get("departamento_id")
    centro_id = request.args.get("centro_id")
    sin_depto = request.args.get("sin_departamento") == "1"

    sql = """
        SELECT p.id, p.nombre, p.apellidos, p.nombre_completo, p.email,
               p.despacho, p.categoria_academica, p.enlace_perfil,
               p.orcid, p.web_personal, p.telefono,
               p.departamento_id, p.centro_id,
               d.siglas AS departamento_siglas, d.nombre AS departamento_nombre,
               c.nombre AS centro_nombre
        FROM profesores p
        LEFT JOIN departamentos d ON p.departamento_id = d.id
        LEFT JOIN centros c ON COALESCE(p.centro_id, d.centro_id) = c.id
    """
    conds, params = [], []
    if departamento_id:
        conds.append("p.departamento_id = %s")
        params.append(departamento_id)
    if sin_depto and centro_id:
        conds.append("p.departamento_id IS NULL AND p.centro_id = %s")
        params.append(centro_id)
    elif centro_id and not departamento_id:
        conds.append("(d.centro_id = %s OR p.centro_id = %s)")
        params.extend([centro_id, centro_id])
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY p.apellidos, p.nombre"
    return jsonify(query(sql, params))


@bp.route("/profesores/<profesor_id>")
def get_profesor_detail(profesor_id):
    row = query_one("""
        SELECT p.*,
               d.siglas AS departamento_siglas, d.nombre AS departamento_nombre,
               c.nombre AS centro_nombre
        FROM profesores p
        LEFT JOIN departamentos d ON p.departamento_id = d.id
        LEFT JOIN centros c ON COALESCE(p.centro_id, d.centro_id) = c.id
        WHERE p.id = %s
    """, (profesor_id,))
    if not row:
        return jsonify({"error": "No encontrado"}), 404
    return jsonify(row)


@bp.route("/departamentos")
def get_departamentos():
    centro_id = request.args.get("centro_id")
    sql = """
        SELECT d.id, d.siglas, d.nombre, d.codigo_us, d.centro_id, d.activo,
               c.nombre AS centro_nombre,
               (SELECT COUNT(*) FROM profesores p WHERE p.departamento_id = d.id) AS num_profesores
        FROM departamentos d
        LEFT JOIN centros c ON c.id = d.centro_id
    """
    params = []
    if centro_id:
        sql += " WHERE d.centro_id = %s"
        params.append(centro_id)
    sql += " ORDER BY d.nombre"
    return jsonify(query(sql, params))


@bp.route("/centros/<centro_id>/departamentos")
def get_departamentos_de_centro(centro_id):
    """
    Lista departamentos del centro + bucket virtual "Sin departamento" con
    los profesores que tienen centro_id asignado pero departamento NULL.
    """
    if not query_one("SELECT id FROM centros WHERE id = %s", (centro_id,)):
        return jsonify({"error": "Centro no encontrado"}), 404

    deptos = query("""
        SELECT d.id, d.siglas, d.nombre, d.codigo_us, d.activo,
               (SELECT COUNT(*) FROM profesores p WHERE p.departamento_id = d.id) AS num_profesores
        FROM departamentos d
        WHERE d.centro_id = %s
        ORDER BY d.nombre
    """, (centro_id,))

    sin_depto = query_one("""
        SELECT COUNT(*) AS num_profesores
        FROM profesores
        WHERE departamento_id IS NULL AND centro_id = %s
    """, (centro_id,))

    return jsonify({
        "departamentos": deptos,
        "sin_departamento": {
            "key": SIN_DEPTO_KEY,
            "num_profesores": sin_depto["num_profesores"] if sin_depto else 0,
        },
    })


# ──────────────────────────────────────────────────────────────────────────
#  Enrich helpers (DB upserts)
# ──────────────────────────────────────────────────────────────────────────

def _upsert_departamento(nombre: str, slug: str, centro_id: str | None) -> str:
    """
    Busca departamento por codigo_us (slug). Si existe, actualiza centro_id
    si esta a NULL. Si no existe, lo crea con siglas autogeneradas.
    Devuelve el id.
    """
    row = query_one(
        "SELECT id, centro_id FROM departamentos WHERE codigo_us = %s LIMIT 1",
        (slug,),
    )
    if row:
        if centro_id and not row["centro_id"]:
            execute(
                "UPDATE departamentos SET centro_id = %s WHERE id = %s",
                (centro_id, row["id"]),
            )
        return row["id"]

    # Fallback: match por nombre normalizado
    row = query_one(
        "SELECT id, centro_id FROM departamentos WHERE LOWER(nombre) = LOWER(%s) LIMIT 1",
        (nombre,),
    )
    if row:
        execute(
            "UPDATE departamentos SET codigo_us = %s, centro_id = COALESCE(centro_id, %s) WHERE id = %s",
            (slug, centro_id, row["id"]),
        )
        return row["id"]

    # Crear nuevo departamento con siglas autogeneradas (primera letra de cada palabra)
    siglas = "".join(p[0] for p in nombre.split() if p and p[0].isalpha()).upper()[:10] or slug[:10].upper()
    uni = query_one("SELECT id FROM universidades LIMIT 1")
    nuevo = execute_returning("""
        INSERT INTO departamentos (id, universidad_id, centro_id, nombre, siglas, codigo_us, activo)
        VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, true)
        RETURNING id
    """, (uni["id"] if uni else None, centro_id, nombre, siglas, slug))
    return nuevo["id"]


def _upsert_profesor(perfil: dict, departamento_id: str | None, centro_id: str | None) -> dict:
    """
    Upsert de un profesor segun el perfil scrapeado.
    Matching: email -> nombre_normalizado.
    Nunca sobreescribe campos ya poblados con NULL.
    Devuelve {"accion": "creado"|"actualizado"|"sin_cambios", "profesor_id": ...}.
    """
    email = perfil.get("email")
    nombre_completo = perfil.get("nombre_completo") or ""
    nombre_norm = normalizar(nombre_completo)
    nombre = perfil.get("nombre") or nombre_completo
    apellidos = perfil.get("apellidos") or ""

    existente = None
    if email:
        existente = query_one("SELECT * FROM profesores WHERE LOWER(email) = LOWER(%s) LIMIT 1", (email,))
    if not existente and nombre_norm:
        existente = query_one(
            "SELECT * FROM profesores WHERE nombre_normalizado = %s LIMIT 1",
            (nombre_norm,),
        )

    if existente:
        # Actualizar solo campos que vienen del scrape y no rompen datos existentes
        execute("""
            UPDATE profesores
            SET nombre = COALESCE(NULLIF(%s, ''), nombre),
                apellidos = COALESCE(NULLIF(%s, ''), apellidos),
                email = COALESCE(email, %s),
                categoria_academica = COALESCE(%s, categoria_academica),
                enlace_perfil = COALESCE(%s, enlace_perfil),
                departamento_id = COALESCE(%s, departamento_id),
                centro_id = COALESCE(%s, centro_id)
            WHERE id = %s
        """, (
            nombre, apellidos, email, perfil.get("categoria"), perfil.get("enlace_perfil"),
            departamento_id, centro_id, existente["id"],
        ))
        return {"accion": "actualizado", "profesor_id": existente["id"]}

    nuevo = execute_returning("""
        INSERT INTO profesores (
            id, departamento_id, centro_id,
            nombre, apellidos, email,
            categoria_academica, enlace_perfil,
            activo
        ) VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, true)
        RETURNING id
    """, (
        departamento_id, centro_id,
        nombre, apellidos, email,
        perfil.get("categoria"), perfil.get("enlace_perfil"),
    ))
    return {"accion": "creado", "profesor_id": nuevo["id"] if nuevo else None}


def _scrape_y_guardar_profesores(
    centro_id: str,
    centro_nombre_us: str,
    departamento_id: str | None,
    departamento_nombre_us: str | None,
) -> dict:
    """
    Ejecuta la busqueda en el directorio PDI, visita cada perfil y hace upsert.
    """
    lista = buscar_profesores(
        centro_nombre=centro_nombre_us,
        departamento_nombre=departamento_nombre_us,
    )

    creados, actualizados, errores = 0, 0, []
    for i, item in enumerate(lista):
        try:
            perfil = obtener_perfil_profesor(item["slug"])
        except Exception as e:
            errores.append({"slug": item["slug"], "error": str(e)})
            continue

        # El departamento del profe puede diferir del filtro (sin_departamento, etc.)
        prof_depto_id = departamento_id
        if perfil.get("departamento_slug") and not departamento_id:
            prof_depto_id = _upsert_departamento(
                perfil["departamento_nombre"],
                perfil["departamento_slug"],
                centro_id,
            )

        try:
            res = _upsert_profesor(perfil, prof_depto_id, centro_id)
            if res["accion"] == "creado":
                creados += 1
            else:
                actualizados += 1
        except Exception as e:
            errores.append({"slug": item["slug"], "error": str(e)})

        time.sleep(PAUSA)

    return {
        "total_encontrados": len(lista),
        "creados": creados,
        "actualizados": actualizados,
        "errores": errores,
    }


# ──────────────────────────────────────────────────────────────────────────
#  Enrich endpoints
# ──────────────────────────────────────────────────────────────────────────

@bp.route("/centros/<centro_id>/enrich_profesores", methods=["POST"])
def enrich_centro(centro_id):
    """
    Body: {"codigo_us": "escuela-tecnica-superior-de-ingenieria-informatica",
           "nombre_us": "ESCUELA TECNICA SUPERIOR DE INGENIERIA INFORMATICA"}
    - Scrapea la lista de departamentos del centro en us.es.
    - Upsert de cada depto con centro_id.
    - Scrapea el directorio PDI filtrando por centro y enriquece/crea profesores.
    """
    data = request.get_json(silent=True) or {}
    codigo_us = data.get("codigo_us", "").strip()
    nombre_us = data.get("nombre_us", "").strip()

    centro = query_one("SELECT * FROM centros WHERE id = %s", (centro_id,))
    if not centro:
        return jsonify({"error": "Centro no encontrado"}), 404

    if not codigo_us:
        codigo_us = centro.get("codigo_us") or ""
    if not codigo_us:
        return jsonify({"error": "Falta codigo_us (slug) del centro en us.es"}), 400

    # Guardar/actualizar codigo_us del centro
    if centro.get("codigo_us") != codigo_us:
        execute("UPDATE centros SET codigo_us = %s WHERE id = %s", (codigo_us, centro_id))

    # 1. Scrapear departamentos del centro
    try:
        deptos_us = obtener_departamentos_de_centro(codigo_us)
    except Exception as e:
        return jsonify({"error": f"Error scrapeando centro: {e}"}), 502

    deptos_creados = []
    for d in deptos_us:
        _upsert_departamento(d["nombre"], d["slug"], centro_id)
        deptos_creados.append(d)

    # 2. Scrapear profesores del centro
    nombre_busqueda = nombre_us or centro.get("nombre") or ""
    try:
        res = _scrape_y_guardar_profesores(
            centro_id=centro_id,
            centro_nombre_us=nombre_busqueda,
            departamento_id=None,
            departamento_nombre_us=None,
        )
    except Exception as e:
        return jsonify({"error": f"Error scrapeando profesores: {e}"}), 502

    return jsonify({
        "centro": centro["nombre"],
        "departamentos_encontrados": deptos_creados,
        "profesores": res,
    })


@bp.route("/departamentos/<departamento_id>/enrich_profesores", methods=["POST"])
def enrich_departamento(departamento_id):
    """
    Enriquece solo los profesores de un departamento concreto.
    Requiere que el departamento tenga centro_id y codigo_us.
    """
    depto = query_one("""
        SELECT d.*, c.nombre AS centro_nombre
        FROM departamentos d LEFT JOIN centros c ON c.id = d.centro_id
        WHERE d.id = %s
    """, (departamento_id,))
    if not depto:
        return jsonify({"error": "Departamento no encontrado"}), 404
    if not depto.get("centro_id"):
        return jsonify({"error": "El departamento no tiene centro asociado"}), 400

    try:
        res = _scrape_y_guardar_profesores(
            centro_id=depto["centro_id"],
            centro_nombre_us=depto.get("centro_nombre") or "",
            departamento_id=departamento_id,
            departamento_nombre_us=depto["nombre"],
        )
    except Exception as e:
        return jsonify({"error": f"Error scrapeando profesores: {e}"}), 502

    return jsonify({
        "departamento": depto["nombre"],
        "profesores": res,
    })
