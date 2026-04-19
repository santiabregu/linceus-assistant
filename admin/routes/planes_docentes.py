import re
from pathlib import Path
from flask import Blueprint, jsonify, request
from admin.db import query, query_one
from admin.sevius_scraper import obtener_grupos_asignatura, descargar_proyecto_pdf

bp = Blueprint("planes_docentes", __name__)

CURSO_ACADEMICO = "2025-26"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROYECTOS_DIR = PROJECT_ROOT / "knowledge_base" / "proyectos_docentes" / "ing_software"


def _sanitizar(nombre: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", nombre).strip()


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


@bp.route("/planes_docentes/vectorizables", methods=["GET"])
def listar_vectorizables():
    """
    Lista asignaturas de una titulacion con su estado de vectorizacion
    para el curso actual. No hace scraping, solo BD.
    Query: titulacion_id
    """
    titulacion_id = request.args.get("titulacion_id", "").strip()
    if not titulacion_id:
        return jsonify({"error": "titulacion_id obligatorio"}), 400

    rows = query("""
        SELECT a.id, a.codigo, a.nombre, a.curso,
               (SELECT COUNT(*) FROM planes_docentes pd
                WHERE pd.asignatura_id = a.id
                  AND pd.curso_academico = %s
                  AND pd.estado_rag = 'completado') AS planes_completados,
               (SELECT COUNT(*) FROM planes_docentes pd
                WHERE pd.asignatura_id = a.id
                  AND pd.curso_academico = %s) AS planes_totales
        FROM asignaturas a
        WHERE a.titulacion_id = %s AND a.activa = true
        ORDER BY a.curso, a.nombre
    """, (CURSO_ACADEMICO, CURSO_ACADEMICO, titulacion_id))

    for r in rows:
        r["ya_vectorizada"] = r["planes_completados"] > 0

    return jsonify({"curso_academico": CURSO_ACADEMICO, "asignaturas": rows})


@bp.route("/planes_docentes/vectorize", methods=["POST"])
def vectorizar_asignaturas():
    """
    Para cada asignatura seleccionada: scrapea grupos del curso actual en
    Sevius, descarga cada PDF y lo vectoriza. Salta grupos ya completados.

    Body: {
        "titulacion_id": "uuid",
        "codcentro": "3",
        "codigo_titulacion_sevius": "205",
        "asignatura_ids": ["uuid", ...]
    }
    """
    data = request.get_json(silent=True) or {}
    titulacion_id = data.get("titulacion_id", "").strip()
    codcentro = data.get("codcentro", "").strip()
    codigo_tit = data.get("codigo_titulacion_sevius", "").strip()
    asignatura_ids = data.get("asignatura_ids") or []

    if not titulacion_id or not codcentro or not codigo_tit or not asignatura_ids:
        return jsonify({"error": "titulacion_id, codcentro, codigo_titulacion_sevius y asignatura_ids son obligatorios"}), 400

    # Importar aqui para que la ruta cargue aunque falten dependencias del RAG
    from rag.pipeline import procesar_pdf

    placeholders = ",".join(["%s"] * len(asignatura_ids))
    asigs = query(
        f"SELECT id, codigo, nombre FROM asignaturas WHERE id IN ({placeholders}) AND titulacion_id = %s",
        tuple(asignatura_ids) + (titulacion_id,),
    )
    if not asigs:
        return jsonify({"error": "No se encontraron asignaturas"}), 404

    PROYECTOS_DIR.mkdir(parents=True, exist_ok=True)
    resultados = []

    for asig in asigs:
        res_asig = {
            "asignatura_id": asig["id"],
            "codigo": asig["codigo"],
            "nombre": asig["nombre"],
            "grupos": [],
            "error": None,
        }

        try:
            grupos = obtener_grupos_asignatura(codcentro, codigo_tit, asig["codigo"], CURSO_ACADEMICO)
        except Exception as e:
            res_asig["error"] = f"Error scrapeando Sevius: {e}"
            resultados.append(res_asig)
            continue

        if not grupos:
            res_asig["error"] = f"Sin grupos {CURSO_ACADEMICO} en Sevius"
            resultados.append(res_asig)
            continue

        carpeta_asig = PROYECTOS_DIR / _sanitizar(f"{asig['nombre']} ({asig['codigo']})")
        carpeta_asig.mkdir(parents=True, exist_ok=True)

        for grupo in grupos:
            g_res = {"grupo": grupo["nombre"], "estado": "pendiente", "accion": "", "chunks": 0}
            carpeta_grupo = carpeta_asig / _sanitizar(grupo["nombre"])
            carpeta_grupo.mkdir(parents=True, exist_ok=True)
            ruta_pdf = carpeta_grupo / "proyecto_docente.pdf"

            if not ruta_pdf.exists():
                if not grupo.get("proyecto"):
                    g_res["estado"] = "error"
                    g_res["accion"] = "Sevius no devolvio valor 'proyecto'"
                    res_asig["grupos"].append(g_res)
                    continue
                if not descargar_proyecto_pdf(grupo["proyecto"], ruta_pdf):
                    g_res["estado"] = "error"
                    g_res["accion"] = "Error descargando PDF"
                    res_asig["grupos"].append(g_res)
                    continue

            pdf_info = {
                "ruta_pdf": ruta_pdf,
                "codigo_asignatura": asig["codigo"],
                "nombre_asignatura": asig["nombre"],
                "grupo": grupo["nombre"],
            }
            try:
                r = procesar_pdf(pdf_info, dry_run=False, forzar=False)
                g_res["estado"] = r["estado"]
                g_res["accion"] = r["accion"]
                g_res["chunks"] = r.get("chunks", 0)
            except Exception as e:
                g_res["estado"] = "error"
                g_res["accion"] = f"Excepcion: {e}"

            res_asig["grupos"].append(g_res)

        resultados.append(res_asig)

    resumen = {
        "completado": sum(1 for r in resultados for g in r["grupos"] if g["estado"] == "completado"),
        "sin_cambios": sum(1 for r in resultados for g in r["grupos"] if g["estado"] == "sin_cambios"),
        "error": sum(1 for r in resultados for g in r["grupos"] if g["estado"] == "error"),
        "total_chunks": sum(g["chunks"] for r in resultados for g in r["grupos"]),
    }

    return jsonify({
        "curso_academico": CURSO_ACADEMICO,
        "resumen": resumen,
        "resultados": resultados,
    })
