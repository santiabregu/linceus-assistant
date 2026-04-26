import time
from flask import Blueprint, jsonify, request
from admin.db import query, query_one, execute_returning, execute, normalizar
from admin.us_directorio_scraper import (
    obtener_departamentos_de_centro,
    buscar_profesores,
    obtener_perfil_profesor,
    obtener_docencia,
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


@bp.route("/profesores/<profesor_id>/asignaturas")
def get_asignaturas_de_profesor(profesor_id):
    """Asignaturas que imparte el profesor según profesor_asignatura."""
    rows = query("""
        SELECT a.id, a.codigo, a.nombre, a.curso, a.creditos, a.tipologia,
               t.nombre AS titulacion_nombre, t.codigo AS titulacion_codigo,
               pa.curso_academico, pa.grupo, pa.es_coordinador, pa.tipo_docencia
        FROM profesor_asignatura pa
        JOIN asignaturas a ON a.id = pa.asignatura_id
        LEFT JOIN titulaciones t ON t.id = a.titulacion_id
        WHERE pa.profesor_id = %s AND a.activa = true
        ORDER BY pa.curso_academico DESC, a.curso, a.nombre
    """, (profesor_id,))
    return jsonify(rows)


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


# ──────────────────────────────────────────────────────────────────────────
#  Refresh enlaces us.es (prerequisito para sync de docencia)
# ──────────────────────────────────────────────────────────────────────────

# Prefijo del directorio PDI de us.es usado para detectar profes ya vinculados.
_ENLACE_US_DIRECTORIO = "trabaja-en-la-us/directorio"


# Slugs "placeholder" que us.es devuelve en el listado genérico y NO son
# personas reales. Los filtramos siempre para evitar falsos positivos.
_SLUGS_BASURA = {
    "personal-de-administracion-y-servicios",
    "personal-docente-e-investigador",
}


def _buscar_slug_us_por_nombre(nombre_completo: str) -> str | None:
    """
    Busca al profesor en el directorio PDI de us.es por nombre y devuelve
    su slug si encuentra exactamente 1 coincidencia fiable.

    No usamos el filtro `centro_nombre` de la API us.es: el filtro devuelve
    entradas placeholder (p.ej. "PERSONAL DE ADMINISTRACIÓN Y SERVICIOS")
    que ensucian el match. Confiamos en la búsqueda por nombre.
    """
    if not nombre_completo:
        return None
    try:
        candidatos = buscar_profesores(nombre=nombre_completo, max_paginas=3)
    except Exception as e:
        print(f"  ⚠ Error buscando '{nombre_completo}' en us.es: {e}")
        return None

    # Filtrar slugs placeholder.
    candidatos = [c for c in candidatos if c["slug"] not in _SLUGS_BASURA]

    if len(candidatos) == 1:
        return candidatos[0]["slug"]

    # Varios candidatos: aceptar solo si hay match exacto por nombre normalizado.
    objetivo = normalizar(nombre_completo)
    exactos = [c for c in candidatos if normalizar(c["nombre"]) == objetivo]
    if len(exactos) == 1:
        return exactos[0]["slug"]

    return None


@bp.route("/centros/<centro_id>/refresh_enlaces_us", methods=["POST"])
def refresh_enlaces_us(centro_id):
    """
    Para cada profesor del centro cuyo `enlace_perfil` no apunta al directorio
    PDI de us.es, busca su slug en us.es por nombre y actualiza el enlace.

    Prerequisito para `sync_docencia`, que necesita el slug us.es para
    scrapear la sección "Asignaturas que imparte".
    """
    centro = query_one("SELECT * FROM centros WHERE id = %s", (centro_id,))
    if not centro:
        return jsonify({"error": "Centro no encontrado"}), 404

    profes = query("""
        SELECT p.id, p.nombre, p.apellidos,
               p.nombre_normalizado, p.enlace_perfil
        FROM profesores p
        WHERE (p.centro_id = %s OR p.departamento_id IN (
                  SELECT id FROM departamentos WHERE centro_id = %s
              ))
          AND p.activo = true
    """, (centro_id, centro_id))

    resueltos = 0
    ya_ok = 0
    no_encontrados = []

    for p in profes:
        enlace = p.get("enlace_perfil") or ""
        if _ENLACE_US_DIRECTORIO in enlace:
            ya_ok += 1
            continue

        # Construir el nombre a buscar desde nombre + apellidos o nombre_normalizado.
        # NO usar nombre_completo (campo GENERATED "Apellidos, Nombre") porque
        # puede venir como ", Nombre" cuando el apellido está vacío.
        nombre_busqueda = f"{p.get('nombre') or ''} {p.get('apellidos') or ''}".strip()
        if not nombre_busqueda:
            nombre_busqueda = p.get("nombre_normalizado") or ""
        if not nombre_busqueda:
            no_encontrados.append({"id": p["id"], "motivo": "sin nombre"})
            continue

        slug = _buscar_slug_us_por_nombre(nombre_busqueda)
        if not slug:
            no_encontrados.append({
                "id": p["id"],
                "nombre": nombre_busqueda,
                "motivo": "0 o varios resultados en us.es",
            })
            time.sleep(PAUSA)
            continue

        nuevo_enlace = f"https://www.us.es/trabaja-en-la-us/directorio/{slug}"
        execute(
            "UPDATE profesores SET enlace_perfil = %s WHERE id = %s",
            (nuevo_enlace, p["id"]),
        )
        resueltos += 1
        time.sleep(PAUSA)

    return jsonify({
        "centro": centro["nombre"],
        "total_profes": len(profes),
        "ya_con_enlace_us": ya_ok,
        "resueltos": resueltos,
        "no_encontrados": no_encontrados,
    })


# ──────────────────────────────────────────────────────────────────────────
#  Sync docencia: popula profesor_asignatura desde us.es
# ──────────────────────────────────────────────────────────────────────────

_CURSO_ACADEMICO_ACTUAL = "2025-26"


def _insert_profesor_asignatura(
    profesor_id: str,
    asignatura_id: str,
    curso_academico: str,
) -> bool:
    """
    Inserta una fila en profesor_asignatura si no existe ya.
    La constraint UNIQUE incluye `grupo`, que en Postgres NULL ≠ NULL, así
    que comprobamos manualmente antes de insertar para evitar duplicados.
    Devuelve True si se creó, False si ya existía.
    """
    existe = query_one("""
        SELECT 1 FROM profesor_asignatura
        WHERE profesor_id = %s
          AND asignatura_id = %s
          AND curso_academico = %s
          AND grupo IS NULL
        LIMIT 1
    """, (profesor_id, asignatura_id, curso_academico))
    if existe:
        return False

    execute_returning("""
        INSERT INTO profesor_asignatura
            (id, profesor_id, asignatura_id, curso_academico)
        VALUES (gen_random_uuid(), %s, %s, %s)
        RETURNING id
    """, (profesor_id, asignatura_id, curso_academico))
    return True


@bp.route("/titulaciones/<titulacion_id>/sync_docencia", methods=["POST"])
def sync_docencia(titulacion_id):
    """
    Popula la tabla profesor_asignatura para una titulación:
      1. Construye mapa {codigo_asignatura -> asignatura_id} de la titulación.
      2. Recorre los profesores del centro que tengan enlace de us.es.
      3. Scrapea su sección "Asignaturas que imparte".
      4. Por cada código que matchee con la titulación, upsertea la relación.

    Prerequisito: los profesores del centro deben tener enlace_perfil apuntando
    al directorio PDI de us.es. Si no, llamar antes a refresh_enlaces_us.
    """
    titulacion = query_one("""
        SELECT t.id, t.nombre, t.codigo, t.centro_id, c.nombre AS centro_nombre
        FROM titulaciones t
        LEFT JOIN centros c ON c.id = t.centro_id
        WHERE t.id = %s
    """, (titulacion_id,))
    if not titulacion:
        return jsonify({"error": "Titulación no encontrada"}), 404

    centro_id = titulacion.get("centro_id")
    if not centro_id:
        return jsonify({"error": "La titulación no tiene centro asociado"}), 400

    # 1. Mapa código -> id para la titulación
    asignaturas = query("""
        SELECT id, codigo
        FROM asignaturas
        WHERE titulacion_id = %s AND activa = true AND codigo IS NOT NULL
    """, (titulacion_id,))
    codigo_a_id = {a["codigo"]: a["id"] for a in asignaturas if a.get("codigo")}
    if not codigo_a_id:
        return jsonify({"error": "La titulación no tiene asignaturas con código"}), 400

    # 2. Profes del centro con enlace us.es
    profes = query("""
        SELECT p.id, p.nombre, p.apellidos, p.nombre_completo, p.enlace_perfil
        FROM profesores p
        WHERE (p.centro_id = %s OR p.departamento_id IN (
                  SELECT id FROM departamentos WHERE centro_id = %s
              ))
          AND p.activo = true
          AND p.enlace_perfil ILIKE %s
    """, (centro_id, centro_id, f"%{_ENLACE_US_DIRECTORIO}%"))

    if not profes:
        return jsonify({
            "error": "Ningún profesor del centro tiene enlace us.es. "
                     "Ejecuta primero refresh_enlaces_us."
        }), 400

    creadas = 0
    ya_existentes = 0
    no_matcheadas: list[dict] = []
    profes_con_docencia = 0
    errores: list[dict] = []

    for p in profes:
        enlace = p["enlace_perfil"]
        # Extraer slug del final del enlace
        slug = enlace.rstrip("/").rsplit("/", 1)[-1]

        try:
            docencia = obtener_docencia(slug)
        except Exception as e:
            errores.append({"profesor_id": p["id"], "error": str(e)})
            time.sleep(PAUSA)
            continue

        if docencia:
            profes_con_docencia += 1

        for asig in docencia:
            codigo = asig["codigo"]
            asignatura_id = codigo_a_id.get(codigo)
            if not asignatura_id:
                no_matcheadas.append({
                    "profesor_id": p["id"],
                    "codigo_us": codigo,
                    "nombre_us": asig["nombre"],
                    "titulacion_slug": asig["titulacion_slug"],
                })
                continue

            try:
                if _insert_profesor_asignatura(
                    p["id"], asignatura_id, _CURSO_ACADEMICO_ACTUAL,
                ):
                    creadas += 1
                else:
                    ya_existentes += 1
            except Exception as e:
                errores.append({
                    "profesor_id": p["id"],
                    "asignatura_id": asignatura_id,
                    "error": str(e),
                })

        time.sleep(PAUSA)

    return jsonify({
        "titulacion": titulacion["nombre"],
        "total_profes": len(profes),
        "profes_con_docencia": profes_con_docencia,
        "relaciones_creadas": creadas,
        "ya_existentes": ya_existentes,
        "no_matcheadas_en_titulacion": len(no_matcheadas),
        "ejemplos_no_matcheadas": no_matcheadas[:10],
        "errores": errores,
    })
