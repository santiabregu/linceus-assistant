"""
Módulo Text-to-SQL para consultas de profesores.
Usa Gemini API para generar queries SQL seguras a partir de lenguaje natural.
"""

import re
import json
import sys
import os
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from actions.shared.gemini_client import llamar_gemini as llamar_llm
from actions.shared.db import db_client


# ============================================================================
# SCHEMA DE LA BASE DE DATOS (para el prompt del LLM)
# ============================================================================

PROFESORES_SCHEMA = """
CREATE TABLE profesores (
    id UUID PRIMARY KEY,
    departamento_id UUID,                  -- FK a departamentos
    nombre VARCHAR(100),                   -- Ej: "Juan Antonio"
    apellidos VARCHAR(200),                -- Ej: "Parejo Maestre"
    nombre_completo VARCHAR(300),          -- GENERATED: "Parejo Maestre, Juan Antonio"
    nombre_normalizado VARCHAR(300),       -- nombre en minúsculas sin tildes
    email VARCHAR(100),                    -- Ej: "japarejo@us.es"
    telefono VARCHAR(20),                  -- Ej: "954553873"
    despacho VARCHAR(100),                 -- Ej: "F1.52"
    edificio VARCHAR(100),                 -- Ej: "F"
    planta VARCHAR(20),                    -- Ej: "1"
    web_personal VARCHAR(200),
    orcid VARCHAR(50),
    categoria_academica VARCHAR(100),      -- Ej: "Catedrático de Universidad"
    enlace_perfil VARCHAR(500),
    activo BOOLEAN DEFAULT true
);

CREATE TABLE departamentos (
    id UUID PRIMARY KEY,
    codigo VARCHAR(20),
    nombre VARCHAR(200),                   -- Ej: "Departamento de Lenguajes y Sistemas Informáticos"
    siglas VARCHAR(10),                    -- Ej: "LSI", "CCIA", "DTE", "MA1"
    activo BOOLEAN DEFAULT true
);

CREATE TABLE tutorias (
    id UUID PRIMARY KEY,
    profesor_id UUID,                      -- FK a profesores
    dia_semana INTEGER,                    -- 1=Lunes, 2=Martes, 3=Miércoles, 4=Jueves, 5=Viernes
    hora_inicio TIME,
    hora_fin TIME,
    ubicacion VARCHAR(100),
    modalidad VARCHAR(20),                 -- "presencial", "online", "mixta"
    enlace_online VARCHAR(300),
    curso_academico VARCHAR(10),
    cuatrimestre VARCHAR(10),
    notas TEXT,
    activa BOOLEAN DEFAULT true
);

CREATE TABLE profesor_asignatura (
    id UUID PRIMARY KEY,
    profesor_id UUID,                      -- FK a profesores
    asignatura_id UUID,                    -- FK a asignaturas
    curso_academico VARCHAR(10),
    grupo VARCHAR(20),
    es_coordinador BOOLEAN,
    tipo_docencia VARCHAR(50)              -- "teoria", "practicas", "laboratorio"
);

CREATE TABLE asignaturas (
    id UUID PRIMARY KEY,
    titulacion_id UUID,                    -- FK a titulaciones
    nombre VARCHAR(200),
    nombre_normalizado VARCHAR(200),
    codigo VARCHAR(20),
    activa BOOLEAN DEFAULT true
);

CREATE TABLE titulaciones (
    id UUID PRIMARY KEY,
    codigo VARCHAR(20),                    -- Ej: 'GII-IS', 'GII-TI', 'GII-IC'
    nombre VARCHAR(200),
    activa BOOLEAN DEFAULT true
);

-- Valores de ejemplo:
-- departamentos.siglas: 'LSI', 'CCIA', 'DTE', 'MA1'
-- titulaciones.codigo: 'GII-IS', 'GII-TI', 'GII-IC'
-- dia_semana: 1 (Lunes), 2 (Martes), 3 (Miércoles), 4 (Jueves), 5 (Viernes)
-- categoria_academica: 'Catedrático de Universidad', 'Profesor Titular de Universidad', 'Contratado Doctor', 'Profesor Ayudante Doctor', 'Asociado'
"""

# Tablas permitidas en las queries generadas
TABLAS_PERMITIDAS = {
    'PROFESORES', 'DEPARTAMENTOS', 'TUTORIAS',
    'PROFESOR_ASIGNATURA', 'ASIGNATURAS', 'TITULACIONES',
    'HORARIOS', 'GRUPOS_CLASE',
}

# Columnas permitidas en SELECT
COLUMNAS_PERMITIDAS_PROFESOR = {
    'id', 'nombre', 'apellidos', 'nombre_completo', 'nombre_normalizado',
    'email', 'telefono', 'despacho', 'edificio', 'planta',
    'web_personal', 'orcid', 'categoria_academica', 'enlace_perfil',
    'activo', 'departamento_id',
    # De departamentos
    'codigo', 'siglas',
    # De tutorias
    'dia_semana', 'hora_inicio', 'hora_fin', 'ubicacion', 'modalidad',
    'enlace_online', 'curso_academico', 'cuatrimestre', 'notas', 'activa',
    # De profesor_asignatura
    'profesor_id', 'asignatura_id', 'grupo', 'es_coordinador', 'tipo_docencia',
    # Funciones y alias
    'count', 'count(*)',
}


# ============================================================================
# GENERACIÓN DE SQL
# ============================================================================

def generar_sql_profesor(
    pregunta: str,
    nombre_profesor: str = None,
    nombre_asignatura: str = None,
    nombre_departamento: str = None,
    historial: str = "",
    contexto_titulacion: str = None,
) -> Dict[str, Any]:
    """
    Genera una query SQL para consultas sobre profesores.

    `contexto_titulacion` es el código de la titulación activa (p.ej. 'GII-IS').
    Cuando se pasa, el LLM añade filtro por titulación a los JOINs con
    `asignaturas` para evitar ambigüedad cuando un mismo nombre existe en
    varias titulaciones (p.ej. 'Estadística' en IS y en TI).

    Returns:
        Dict con 'sql', 'parametros', 'explicacion', 'valido'
    """
    contexto_conv = ""
    if historial:
        contexto_conv = f"\nCONTEXTO CONVERSACIÓN PREVIA:\n{historial}\n"

    entidades = ""
    if nombre_profesor:
        entidades += f'PROFESOR MENCIONADO: "{nombre_profesor}"\n'
    if nombre_asignatura:
        entidades += f'ASIGNATURA MENCIONADA: "{nombre_asignatura}"\n'
    if nombre_departamento:
        entidades += f'DEPARTAMENTO MENCIONADO: "{nombre_departamento}"\n'
    if contexto_titulacion:
        entidades += f'TITULACIÓN ACTIVA: "{contexto_titulacion}"\n'

    instruccion_titulacion = ""
    if contexto_titulacion:
        instruccion_titulacion = (
            f"\n11. FILTRAR POR TITULACIÓN: cuando se hace JOIN con `asignaturas`, "
            f"añade también JOIN con `titulaciones` y filtra por "
            f"`t_tit.codigo = '{contexto_titulacion}'` (usa alias t_tit para titulaciones). "
            f"Evita ambigüedad entre asignaturas homónimas de distintas titulaciones.\n"
            f"   Ejemplo: FROM profesor_asignatura pa "
            f"JOIN asignaturas a ON pa.asignatura_id = a.id "
            f"JOIN titulaciones t_tit ON a.titulacion_id = t_tit.id "
            f"WHERE a.nombre_normalizado ILIKE %s AND t_tit.codigo = '{contexto_titulacion}'"
        )

    prompt = f"""Eres un experto en SQL. Genera una query SELECT para responder una pregunta sobre profesores universitarios.

SCHEMA:
{PROFESORES_SCHEMA}
{contexto_conv}
PREGUNTA: "{pregunta}"
{entidades}

INSTRUCCIONES:
1. Usa JOINs cuando necesites datos de varias tablas (profesores + departamentos, profesores + tutorias, etc.)
2. Para buscar por nombre de profesor usa MÚLTIPLES formatos (nombre_normalizado tiene formato "apellidos, nombre" en minúsculas sin tildes):
   WHERE (p.nombre_normalizado ILIKE %s OR LOWER(p.nombre || ' ' || p.apellidos) ILIKE %s OR LOWER(p.apellidos || ' ' || p.nombre) ILIKE %s)
   Pasa el MISMO parámetro 3 veces en el array de parametros.
3. Para buscar por asignatura usa JOIN con profesor_asignatura y asignaturas, buscando por nombre_normalizado ILIKE %s
4. Si piden tutorías, haz JOIN con tutorias WHERE activa = true
5. Siempre incluye WHERE p.activo = true para profesores
6. Usa alias: p para profesores, d para departamentos, t para tutorias, pa para profesor_asignatura, a para asignaturas, t_tit para titulaciones
7. Si piden profesores de un departamento, filtra por d.siglas = %s
8. Si no se menciona un profesor concreto pero sí una asignatura, busca todos los profesores de esa asignatura
9. Devuelve siempre: p.id, p.nombre, p.apellidos, p.email, p.telefono, p.despacho, p.categoria_academica, d.siglas AS departamento
10. Si piden tutorías incluye también: t.dia_semana, t.hora_inicio, t.hora_fin, t.ubicacion, t.modalidad{instruccion_titulacion}

RESPONDE SOLO CON JSON VÁLIDO:
{{
    "sql": "SELECT ... FROM profesores p LEFT JOIN departamentos d ON p.departamento_id = d.id WHERE ...",
    "parametros": ["%valor%"],
    "explicacion": "busca profesor por nombre parcial"
}}

JSON:"""

    try:
        respuesta = llamar_llm(
            prompt,
            timeout=120,
            options={
                "temperature": 0.0,
                "num_predict": 250,
                "top_p": 0.9,
            }
        )
        if respuesta:
            inicio = respuesta.find('{')
            fin = respuesta.rfind('}')

            if inicio != -1 and fin != -1 and fin > inicio:
                json_str = respuesta[inicio:fin+1]
                data = json.loads(json_str)
                sql_validada = validar_sql(data.get('sql', ''))
                if sql_validada:
                    data['sql'] = sql_validada
                    data['valido'] = True
                    return data
    except Exception as e:
        print(f"Error generando SQL profesor: {e}")

    # Fallback según entidades disponibles
    return _fallback_sql(
        nombre_profesor, nombre_asignatura, nombre_departamento,
        contexto_titulacion=contexto_titulacion,
    )


def _fallback_sql(
    nombre_profesor: str = None,
    nombre_asignatura: str = None,
    nombre_departamento: str = None,
    contexto_titulacion: str = None,
) -> Dict[str, Any]:
    """Query fallback segura cuando el LLM falla."""

    if nombre_profesor:
        nombre_lower = nombre_profesor.lower()
        return {
            'sql': """SELECT p.id, p.nombre, p.apellidos, p.email, p.telefono,
                             p.despacho, p.edificio, p.planta, p.web_personal,
                             p.orcid, p.categoria_academica, p.enlace_perfil,
                             d.siglas AS departamento
                      FROM profesores p
                      LEFT JOIN departamentos d ON p.departamento_id = d.id
                      WHERE p.activo = true AND (
                          p.nombre_normalizado ILIKE %s
                          OR LOWER(p.nombre || ' ' || p.apellidos) ILIKE %s
                          OR LOWER(p.apellidos || ' ' || p.nombre) ILIKE %s
                          OR LOWER(p.apellidos || ', ' || p.nombre) ILIKE %s
                      )""",
            'parametros': [f'%{nombre_lower}%'] * 4,
            'explicacion': 'fallback - búsqueda por nombre (múltiples formatos)',
            'valido': True,
        }

    if nombre_asignatura:
        if contexto_titulacion:
            sql = """SELECT p.id, p.nombre, p.apellidos, p.email, p.telefono,
                            p.despacho, p.categoria_academica, d.siglas AS departamento,
                            pa.es_coordinador, pa.tipo_docencia, pa.grupo
                     FROM profesor_asignatura pa
                     JOIN profesores p ON pa.profesor_id = p.id
                     LEFT JOIN departamentos d ON p.departamento_id = d.id
                     JOIN asignaturas a ON pa.asignatura_id = a.id
                     JOIN titulaciones t_tit ON a.titulacion_id = t_tit.id
                     WHERE p.activo = true
                       AND a.nombre_normalizado ILIKE %s
                       AND t_tit.codigo = %s"""
            params = [f'%{nombre_asignatura.lower()}%', contexto_titulacion]
            explicacion = 'fallback - profesores por asignatura + titulación'
        else:
            sql = """SELECT p.id, p.nombre, p.apellidos, p.email, p.telefono,
                            p.despacho, p.categoria_academica, d.siglas AS departamento,
                            pa.es_coordinador, pa.tipo_docencia, pa.grupo
                     FROM profesor_asignatura pa
                     JOIN profesores p ON pa.profesor_id = p.id
                     LEFT JOIN departamentos d ON p.departamento_id = d.id
                     JOIN asignaturas a ON pa.asignatura_id = a.id
                     WHERE p.activo = true AND a.nombre_normalizado ILIKE %s"""
            params = [f'%{nombre_asignatura.lower()}%']
            explicacion = 'fallback - profesores por asignatura'
        return {
            'sql': sql,
            'parametros': params,
            'explicacion': explicacion,
            'valido': True,
        }

    if nombre_departamento:
        return {
            'sql': """SELECT p.id, p.nombre, p.apellidos, p.email, p.telefono,
                             p.despacho, p.categoria_academica, d.siglas AS departamento
                      FROM profesores p
                      JOIN departamentos d ON p.departamento_id = d.id
                      WHERE p.activo = true AND d.siglas = %s
                      ORDER BY p.apellidos, p.nombre""",
            'parametros': [nombre_departamento.upper()],
            'explicacion': 'fallback - profesores por departamento',
            'valido': True,
        }

    # Fallback genérico
    return {
        'sql': """SELECT p.id, p.nombre, p.apellidos, p.email, p.despacho,
                         p.categoria_academica, d.siglas AS departamento
                  FROM profesores p
                  LEFT JOIN departamentos d ON p.departamento_id = d.id
                  WHERE p.activo = true
                  ORDER BY p.apellidos, p.nombre LIMIT 20""",
        'parametros': [],
        'explicacion': 'fallback - lista general',
        'valido': True,
    }


# ============================================================================
# VALIDACIÓN DE SEGURIDAD SQL
# ============================================================================

def validar_sql(sql: str) -> Optional[str]:
    """Valida que la SQL generada sea segura."""
    if not sql:
        return None

    sql_upper = sql.upper().strip()

    # Solo SELECT
    palabras_prohibidas = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE',
        'TRUNCATE', 'EXEC', 'EXECUTE', 'GRANT', 'REVOKE', '--', ';--',
        'UNION SELECT', 'OR 1=1', "OR '1'='1'", 'SLEEP(', 'BENCHMARK('
    ]

    for palabra in palabras_prohibidas:
        if palabra in sql_upper:
            print(f"⚠️ SQL rechazada: contiene '{palabra}'")
            return None

    if not sql_upper.startswith('SELECT'):
        print(f"⚠️ SQL rechazada: no empieza con SELECT")
        return None

    # Verificar tablas
    tablas_mencionadas = re.findall(r'FROM\s+(\w+)|JOIN\s+(\w+)', sql_upper)
    tablas_flat = [t for grupo in tablas_mencionadas for t in grupo if t]

    for tabla in tablas_flat:
        if tabla not in TABLAS_PERMITIDAS:
            print(f"⚠️ SQL rechazada: tabla no permitida '{tabla}'")
            return None

    # Limpiar placeholders
    sql = re.sub(r"'(%s)'", r'\1', sql)

    print(f"✅ SQL validada: {sql[:100]}...")
    return sql


# ============================================================================
# EJECUCIÓN SEGURA DE QUERIES
# ============================================================================

def ejecutar_query(sql: str, parametros: List = None) -> Tuple[bool, Any]:
    """Ejecuta una query SQL de forma segura."""
    # Verificar que el número de %s coincide con los parámetros
    num_placeholders = sql.count('%s')
    num_params = len(parametros) if parametros else 0
    if num_placeholders != num_params:
        print(f"⚠️ Mismatch: {num_placeholders} placeholders vs {num_params} parámetros")
        print(f"   SQL: {sql}")
        print(f"   Params: {parametros}")
        # Intentar ajustar: si sobran placeholders, replicar el último param
        if num_params > 0 and num_placeholders > num_params:
            parametros = list(parametros) + [parametros[-1]] * (num_placeholders - num_params)
            print(f"   → Ajustado a {len(parametros)} params")
        elif num_placeholders == 0 and num_params > 0:
            parametros = None
        else:
            return False, f"Mismatch de parámetros SQL: {num_placeholders} vs {num_params}"

    conn = db_client.get_connection()
    if not conn:
        return False, "Base de datos no disponible"

    try:
        cursor = conn.cursor()
        print(f"🔍 Ejecutando SQL: {sql[:200]}")
        print(f"   Params: {parametros}")

        if parametros:
            cursor.execute(sql, parametros)
        else:
            cursor.execute(sql)

        columnas = [desc[0] for desc in cursor.description] if cursor.description else []
        filas = cursor.fetchall()
        cursor.close()
        conn.close()

        resultados = [dict(zip(columnas, fila)) for fila in filas]
        return True, resultados

    except Exception as e:
        print(f"❌ Error ejecutando query: {e}")
        if conn:
            conn.close()
        return False, str(e)


# ============================================================================
# FORMATEO Y RESPUESTA NATURAL
# ============================================================================

DIAS_NOMBRE = {1: "Lunes", 2: "Martes", 3: "Miércoles", 4: "Jueves", 5: "Viernes"}


def formatear_datos_para_prompt(datos: List[Dict]) -> str:
    """Convierte los datos crudos de la BD en texto legible para el prompt."""
    if not datos:
        return "No se encontraron resultados."

    lineas = []
    for prof in datos:
        partes = []
        nombre = prof.get('apellidos', '')
        if nombre:
            nombre += f", {prof.get('nombre', '')}"
        else:
            nombre = prof.get('nombre', prof.get('nombre_completo', '?'))
        partes.append(f"Nombre: {nombre}")

        for campo, label in [
            ('categoria_academica', 'Categoría'),
            ('departamento', 'Departamento'),
            ('email', 'Email'),
            ('telefono', 'Teléfono'),
            ('despacho', 'Despacho'),
            ('edificio', 'Edificio'),
            ('planta', 'Planta'),
            ('web_personal', 'Web personal'),
            ('orcid', 'ORCID'),
            ('enlace_perfil', 'Perfil'),
            ('grupo', 'Grupo'),
            ('tipo_docencia', 'Tipo docencia'),
        ]:
            val = prof.get(campo)
            if val:
                partes.append(f"{label}: {val}")

        if prof.get('es_coordinador'):
            partes.append("Es coordinador/a de la asignatura")

        # Tutorías (si vienen como campos de la query con JOIN)
        dia = prof.get('dia_semana')
        if dia:
            dia_nombre = DIAS_NOMBRE.get(dia, f"Día {dia}")
            h_ini = str(prof.get('hora_inicio', ''))[:5]
            h_fin = str(prof.get('hora_fin', ''))[:5]
            ubic = prof.get('ubicacion', '')
            mod = prof.get('modalidad', '')
            linea_tut = f"Tutoría: {dia_nombre} {h_ini}-{h_fin}"
            if ubic:
                linea_tut += f" ({ubic})"
            if mod and mod != 'presencial':
                linea_tut += f" [{mod}]"
            partes.append(linea_tut)

        lineas.append("\n".join(partes))

    return "\n\n---\n\n".join(lineas)


def generar_respuesta_natural(
    pregunta: str,
    datos: List[Dict],
    tutorias_no_disponibles: bool = False,
) -> str:
    """Genera respuesta natural usando el LLM.

    Si `tutorias_no_disponibles` es True, el prompt instruye al LLM para
    redirigir al usuario al email del profesor en vez de intentar responder
    sobre horarios de tutorías (la tabla `tutorias` está vacía, no los
    tenemos).
    """
    datos_texto = formatear_datos_para_prompt(datos)

    nota_tutorias = ""
    if tutorias_no_disponibles:
        nota_tutorias = (
            "\n- IMPORTANTE: Actualmente no tenemos registradas las tutorías de los "
            "profesores en nuestra base de datos. Si el usuario pregunta por horario "
            "o lugar de tutorías, indícalo claramente y sugiere contactar al profesor "
            "por email para preguntarle directamente (destaca el email). "
            "No inventes horarios ni ubicaciones de tutorías."
        )

    prompt = f"""Eres Linceus, un asistente universitario de la ETSII (Universidad de Sevilla).
Responde a la pregunta del usuario usando SOLO los datos proporcionados.

PREGUNTA DEL USUARIO: "{pregunta}"

DATOS DE PROFESORES:
{datos_texto}

REGLAS:
- Responde de forma natural, cercana y concisa
- Presenta la información de forma organizada y legible
- Usa markdown para formatear (negritas, listas)
- No inventes datos que no estén proporcionados
- Si no hay resultados, dilo amablemente y sugiere buscar de otra forma
- No repitas la pregunta del usuario
- No digas "según los datos" ni menciones la base de datos
- No saludes (nada de "¡Hola!", "Buenos días", etc.) — ve directo a la respuesta
- Si preguntan por email, despacho o tutorías, destaca esa información
- Si hay varios profesores, organízalos bien
- Si los datos incluyen tutorías, preséntalas agrupadas por día{nota_tutorias}

Respuesta:"""

    respuesta = llamar_llm(prompt, timeout=120, options={
        "temperature": 0.3,
        "num_predict": 400,
    })

    if respuesta:
        return respuesta.strip()

    # Fallback sin LLM
    return datos_texto
