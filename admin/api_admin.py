"""
API REST para el panel de administración de LinceUS.
Conecta directamente a la misma BD PostgreSQL/Supabase del chatbot.
"""

import os
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras

load_dotenv()

app = Flask(__name__)
CORS(app)


def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_DATABASE"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def query(sql, params=None):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        conn.close()


def execute(sql, params=None):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            conn.commit()
    finally:
        conn.close()


# ─── Centros ────────────────────────────────────────────────────────────────

@app.route("/api/admin/centros")
def get_centros():
    rows = query("""
        SELECT id, codigo, nombre, nombre_corto, activo,
               (SELECT COUNT(*) FROM titulaciones t WHERE t.centro_id = c.id) AS num_titulaciones
        FROM centros c
        ORDER BY nombre
    """)
    return jsonify(rows)


# ─── Titulaciones ───────────────────────────────────────────────────────────

@app.route("/api/admin/titulaciones")
def get_titulaciones():
    centro_id = request.args.get("centro_id")
    sql = """
        SELECT t.id, t.codigo, t.nombre, t.nombre_corto, t.tipo,
               t.plan_estudios_anio, t.creditos_totales, t.duracion_anios,
               t.requisito_idioma, t.activa,
               c.nombre AS centro_nombre,
               (SELECT COUNT(*) FROM asignaturas a WHERE a.titulacion_id = t.id) AS num_asignaturas
        FROM titulaciones t
        LEFT JOIN centros c ON c.id = t.centro_id
    """
    params = []
    if centro_id:
        sql += " WHERE t.centro_id = %s"
        params.append(centro_id)
    sql += " ORDER BY t.nombre"
    return jsonify(query(sql, params))


# ─── Asignaturas ────────────────────────────────────────────────────────────

@app.route("/api/admin/asignaturas")
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


@app.route("/api/admin/asignaturas/<asignatura_id>")
def get_asignatura_detail(asignatura_id):
    rows = query("""
        SELECT a.*, t.nombre AS titulacion_nombre, t.codigo AS titulacion_codigo
        FROM asignaturas a
        LEFT JOIN titulaciones t ON t.id = a.titulacion_id
        WHERE a.id = %s
    """, (asignatura_id,))
    if not rows:
        return jsonify({"error": "No encontrada"}), 404
    return jsonify(rows[0])


# ─── Planes docentes y chunks ──────────────────────────────────────────────

@app.route("/api/admin/planes_docentes")
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


@app.route("/api/admin/planes_docentes/<plan_id>/chunks")
def get_chunks(plan_id):
    rows = query("""
        SELECT id, seccion, subseccion, contenido, metadata,
               LENGTH(contenido) AS longitud
        FROM planes_docentes_chunks
        WHERE plan_docente_id = %s
        ORDER BY seccion, subseccion
    """, (plan_id,))
    return jsonify(rows)


# ─── Profesores ─────────────────────────────────────────────────────────────

@app.route("/api/admin/profesores")
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


@app.route("/api/admin/departamentos")
def get_departamentos():
    rows = query("""
        SELECT d.siglas AS departamento, COUNT(p.id) AS num_profesores
        FROM departamentos d
        LEFT JOIN profesores p ON p.departamento_id = d.id
        WHERE d.activo = true
        GROUP BY d.siglas
        ORDER BY d.siglas
    """)
    return jsonify(rows)


# ─── Horarios ───────────────────────────────────────────────────────────────

@app.route("/api/admin/horarios")
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


# ─── Grupos de clase ────────────────────────────────────────────────────────

@app.route("/api/admin/grupos")
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


# ─── Conversaciones (log) ──────────────────────────────────────────────────

@app.route("/api/admin/conversaciones")
def get_conversaciones():
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)

    count_rows = query("SELECT COUNT(*) AS total FROM conversation_log")
    total = count_rows[0]["total"] if count_rows else 0

    rows = query("""
        SELECT id, session_id, user_message, bot_response,
               NULL::TEXT AS intent,
               NULL::DOUBLE PRECISION AS confidence,
               created_at
        FROM conversation_log
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """, (limit, offset))
    return jsonify({"total": total, "rows": rows})


# ─── Feedback ───────────────────────────────────────────────────────────────

@app.route("/api/admin/feedback")
def get_feedback():
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)

    count_rows = query("SELECT COUNT(*) AS total FROM feedback")
    total = count_rows[0]["total"] if count_rows else 0

    rows = query("""
        SELECT id, session_id, rating, comment, last_user_message, last_bot_response, created_at
        FROM feedback
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """, (limit, offset))
    return jsonify({"total": total, "rows": rows})


# ─── Estadísticas generales ────────────────────────────────────────────────

@app.route("/api/admin/stats")
def get_stats():
    stats = {}
    for table, key in [
        ("centros", "centros"),
        ("titulaciones", "titulaciones"),
        ("asignaturas", "asignaturas"),
        ("profesores", "profesores"),
        ("grupos_clase", "grupos"),
        ("horarios", "horarios"),
        ("planes_docentes", "planes_docentes"),
        ("planes_docentes_chunks", "chunks"),
        ("conversation_log", "conversaciones"),
        ("feedback", "feedback"),
    ]:
        try:
            r = query(f"SELECT COUNT(*) AS c FROM {table}")
            stats[key] = r[0]["c"]
        except Exception:
            stats[key] = 0
    return jsonify(stats)


# ─── Health check ───────────────────────────────────────────────────────────

@app.route("/api/admin/health")
def health():
    try:
        conn = get_conn()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
