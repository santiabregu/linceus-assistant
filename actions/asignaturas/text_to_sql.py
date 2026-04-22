"""
Módulo Text-to-SQL para consultas de asignaturas.
Usa Gemini API para generar queries SQL seguras a partir de lenguaje natural.
"""

import re
import json
from typing import Dict, Any, List, Optional, Tuple
from ..shared.gemini_client import llamar_gemini as llamar_llm
from ..shared.db import db_client


# ============================================================================
# SCHEMA DE LA BASE DE DATOS (para el prompt de Ollama)
# ============================================================================

ASIGNATURAS_SCHEMA = """
CREATE TABLE asignaturas (
    id UUID PRIMARY KEY,
    titulacion_id UUID,                    -- FK a titulaciones
    departamento_id UUID,                  -- FK a departamentos
    codigo VARCHAR(20),                    -- Ej: "2050001"
    nombre VARCHAR(200),                   -- Ej: "Fundamentos de Programación"
    curso INTEGER,                         -- 1, 2, 3 o 4
    creditos DECIMAL(4,1),                 -- 6.0 o 12.0
    duracion VARCHAR(10),                  -- 'A' (anual), 'C1' (1er cuatri), 'C2' (2º cuatri)
    tipologia VARCHAR(50),                 -- 'OBLIGATORIA', 'OPTATIVA', 'FORMACION_BASICA', 'TFG'
    es_formacion_basica BOOLEAN,
    es_optativa BOOLEAN,
    nombre_normalizado VARCHAR(200),       -- nombre en minúsculas sin tildes
    activa BOOLEAN DEFAULT true
);

-- Valores de ejemplo:
-- curso: 1, 2, 3, 4
-- creditos: 6, 12
-- duracion: 'A', 'C1', 'C2'
-- tipologia: 'OBLIGATORIA', 'OPTATIVA', 'FORMACION_BASICA', 'TFG'
"""

# Columnas permitidas para SELECT (seguridad)
COLUMNAS_PERMITIDAS = {
    'codigo', 'nombre', 'curso', 'creditos', 'duracion', 
    'tipologia', 'es_formacion_basica', 'es_optativa', 'titulacion_id'
}

# Columnas permitidas para filtrar en WHERE
COLUMNAS_FILTRABLES = {
    'codigo', 'nombre', 'curso', 'creditos', 'duracion', 
    'tipologia', 'es_formacion_basica', 'es_optativa', 
    'titulacion_id', 'activa', 'nombre_normalizado'
}


def _subquery_titulacion(codigo_titulacion: str) -> str:
    """Genera subquery para filtrar por titulación usando su código."""
    return f"(SELECT id FROM titulaciones WHERE codigo = '{codigo_titulacion}' LIMIT 1)"


def _inyectar_filtro_titulacion(sql: str, codigo_titulacion: str) -> str:
    """
    Inyecta filtro de titulación en una query SQL.
    Si la query ya contiene filtro de titulacion_id, no lo añade.
    Busca 'WHERE activa = true' primero; si no está, inserta tras cualquier WHERE.
    """
    if not codigo_titulacion:
        return sql
    if 'titulacion_id' in sql.lower():
        return sql
    subquery = _subquery_titulacion(codigo_titulacion)
    sql_lower = sql.lower()

    # Caso 1: hay 'WHERE activa = true' → insertar a continuación
    idx = sql_lower.find('where activa = true')
    if idx != -1:
        insert_pos = idx + len('WHERE activa = true')
        return sql[:insert_pos] + f" AND titulacion_id = {subquery}" + sql[insert_pos:]

    # Caso 2: hay WHERE pero sin 'activa = true' → insertar al comienzo del WHERE
    idx_where = sql_lower.find(' where ')
    if idx_where != -1:
        insert_pos = idx_where + len(' where ')
        return sql[:insert_pos] + f"titulacion_id = {subquery} AND " + sql[insert_pos:]

    return sql

# Mapeo de sinónimos para valores (normalización)
SINONIMOS_VALORES = {
    # Tipología
    'obligatoria': 'OBLIGATORIA',
    'obligatorias': 'OBLIGATORIA',
    'optativa': 'OPTATIVA',
    'optativas': 'OPTATIVA',
    'troncal': 'OBLIGATORIA',
    'troncales': 'OBLIGATORIA',
    'formacion basica': 'FORMACION_BASICA',
    'formación básica': 'FORMACION_BASICA',
    'basica': 'FORMACION_BASICA',
    'basicas': 'FORMACION_BASICA',
    # Duración
    'anual': 'A',
    'anuales': 'A',
    'primer cuatrimestre': 'C1',
    'primer cuatri': 'C1',
    'cuatrimestre 1': 'C1',
    '1er cuatrimestre': 'C1',
    'segundo cuatrimestre': 'C2',
    'segundo cuatri': 'C2',
    'cuatrimestre 2': 'C2',
    '2do cuatrimestre': 'C2',
    # Curso
    'primero': '1',
    'primer curso': '1',
    '1º': '1',
    'segundo': '2',
    'segundo curso': '2',
    '2º': '2',
    'tercero': '3',
    'tercer curso': '3',
    '3º': '3',
    'cuarto': '4',
    'cuarto curso': '4',
    '4º': '4',
}

# Importar diccionario unificado de alias desde config central
from ..shared.config import ALIAS_ASIGNATURAS


def _parece_acronimo(texto: str) -> bool:
    """Detecta si un texto parece un acrónimo/alias (corto, mayúsculas, sin espacios)."""
    limpio = texto.strip()
    if not limpio:
        return False
    # Acrónimos típicos: cortos y sin espacios (PGPI, IA, SO, ADDA, IS2, DP1)
    if len(limpio) <= 6 and ' ' not in limpio:
        return True
    # Todo mayúsculas independientemente de longitud
    if limpio == limpio.upper() and limpio.isalpha():
        return True
    return False


# Palabras que se ignoran al generar acrónimos (preposiciones, artículos, conjunciones)
_STOP_WORDS_ACRONIMO = {'de', 'del', 'la', 'el', 'las', 'los', 'y', 'e', 'en', 'a', 'al'}


def _generar_acronimo(nombre: str) -> str:
    """Genera el acrónimo de un nombre de asignatura (primera letra de cada palabra significativa)."""
    import unicodedata
    # Normalizar: quitar tildes y pasar a minúsculas
    texto = unicodedata.normalize('NFKD', nombre)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    palabras = texto.lower().split()
    return ''.join(p[0] for p in palabras if p not in _STOP_WORDS_ACRONIMO and len(p) > 1)


def _buscar_por_acronimo_en_bd(acronimo: str, titulacion: str = None) -> str | None:
    """
    Busca en la BD una asignatura cuyo acrónimo generado coincida con el input.
    Devuelve el nombre real de la asignatura o None.
    """
    from ..shared.db import db_client

    conn = db_client.get_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        sql = "SELECT nombre FROM asignaturas WHERE activa = true"
        params = []
        if titulacion:
            sql += " AND titulacion_id = (SELECT id FROM titulaciones WHERE codigo = %s LIMIT 1)"
            params.append(titulacion)
        cursor.execute(sql, params)
        nombres_bd = [row[0] for row in cursor.fetchall()]
        cursor.close()
    finally:
        conn.close()

    acronimo_lower = acronimo.lower().strip()
    for nombre_bd in nombres_bd:
        if _generar_acronimo(nombre_bd) == acronimo_lower:
            return nombre_bd
    return None


def _expandir_alias(nombre: str, titulacion: str = None) -> str:
    """
    Expande alias/abreviaturas al nombre real de la asignatura.
    Orden de prioridad:
      1. Tabla manual de alias conocidos
      2. Generación automática de acrónimos desde la BD
      3. Devuelve el nombre original sin cambios
    """
    if not nombre:
        return nombre
    nombre_lower = nombre.lower().strip()
    # 1. Buscar en tabla manual
    if nombre_lower in ALIAS_ASIGNATURAS:
        print(f"   → Alias manual: '{nombre}' → '{ALIAS_ASIGNATURAS[nombre_lower]}'")
        return ALIAS_ASIGNATURAS[nombre_lower]
    # Limpiar prefijos comunes del NLU iterativamente (ej: "Datos de PGPI" → "de PGPI" → "PGPI")
    import re
    limpio = nombre_lower
    for _ in range(3):  # máximo 3 pasadas
        nuevo = re.sub(r'^(de|del|la|el|las|los|sobre|info|datos)\s+', '', limpio).strip()
        if nuevo == limpio:
            break
        limpio = nuevo
    if limpio and limpio != nombre_lower and limpio in ALIAS_ASIGNATURAS:
        print(f"   → Alias manual (limpio): '{nombre}' → '{ALIAS_ASIGNATURAS[limpio]}'")
        return ALIAS_ASIGNATURAS[limpio]
    # 2. Si parece acrónimo, buscar por generación automática en BD
    texto_buscar = limpio if limpio != nombre_lower else nombre_lower
    if _parece_acronimo(texto_buscar):
        nombre_bd = _buscar_por_acronimo_en_bd(texto_buscar, titulacion)
        if nombre_bd:
            print(f"   → Acrónimo auto-detectado: '{nombre}' → '{nombre_bd}'")
            return nombre_bd
    return nombre


# Palabras clave que indican que la pregunta requiere RAG (plan docente)
_PALABRAS_RAG = [
    'evalua', 'evaluacion', 'evaluación', 'califica', 'calificacion', 'calificación',
    'nota', 'notas', 'puntua', 'puntuacion', 'puntuación', 'porcentaje',
    'examen', 'examenes', 'exámenes', 'parcial', 'parciales', 'prueba',
    'temario', 'tema', 'temas', 'contenido', 'contenidos', 'programa',
    'bibliografia', 'bibliografía', 'libro', 'libros', 'material',
    'metodologia', 'metodología', 'metodo', 'método',
    'profesor', 'profesora', 'profesores', 'profesorado', 'docente', 'imparte',
    'coordinador', 'coordinadora', 'coordinadores', 'responsable',
    'horario', 'horarios', 'clase', 'clases', 'aula',
    'objetivo', 'objetivos', 'competencia', 'competencias',
    'actividad', 'actividades', 'practica', 'prácticas', 'práctica',
    'idioma', 'lengua', 'tribunal', 'tribunales',
    'aprueba', 'aprobar', 'suspender', 'convocatoria',
    'hora', 'horas', 'teoria', 'teoría', 'laboratorio',
    'quien da', 'quién da', 'quien enseña', 'quién enseña',
    'quien imparte', 'quién imparte', 'enseña', 'da clase',
]


def _necesita_rag_heuristica(pregunta: str) -> bool:
    """Detecta si la pregunta requiere RAG basándose en palabras clave."""
    pregunta_lower = pregunta.lower()
    return any(palabra in pregunta_lower for palabra in _PALABRAS_RAG)


def _clasificar_necesita_rag(pregunta: str, historial: str = "") -> bool:
    """
    Llama a Gemini para decidir si la pregunta requiere buscar en el plan docente (RAG).
    Separado de la generación SQL para mayor precisión.
    Usa la heurística como fallback si el LLM falla.
    """
    # Cortocircuito: si la heurística ya detecta RAG, no hace falta llamar al LLM
    if _necesita_rag_heuristica(pregunta):
        return True

    contexto = f"\nCONTEXTO PREVIO:\n{historial}\n" if historial else ""

    prompt = f"""Eres un clasificador. Decide si la siguiente pregunta requiere consultar el plan docente de una asignatura universitaria.

El plan docente contiene: profesorado, temario, evaluación, criterios de calificación, bibliografía, metodología, objetivos, competencias, actividades, horarios, idioma de impartición, tribunales de evaluación, horas de clase.

La ficha básica (NO requiere plan docente) solo tiene: nombre, código, créditos, curso, cuatrimestre, tipo (obligatoria/optativa/troncal).
{contexto}
Ejemplos que SÍ requieren plan docente:
- "quién da clase en el grupo 2" → true
- "cómo se aprueba" → true
- "de qué va el primer tema" → true
- "cuántas horas tiene" → true
- "en qué idioma se imparte" → true

Ejemplos que NO requieren plan docente:
- "cuántos créditos tiene" → false
- "es optativa o obligatoria" → false
- "en qué curso se da" → false

PREGUNTA: "{pregunta}"

Responde SOLO con: true o false"""

    try:
        respuesta = llamar_llm(
            prompt,
            timeout=30,
            options={"temperature": 0.0, "num_predict": 5}
        )
        if respuesta:
            respuesta_lower = respuesta.strip().lower()
            if 'true' in respuesta_lower:
                print(f"   → Clasificador RAG: true (LLM)")
                return True
            if 'false' in respuesta_lower:
                print(f"   → Clasificador RAG: false (LLM)")
                return False
    except Exception as e:
        print(f"   Error clasificando RAG: {e}")

    # Fallback a heurística
    print(f"   → Clasificador RAG: fallback a heurística")
    return _necesita_rag_heuristica(pregunta)


# ============================================================================
# GENERACIÓN DE SQL CON OLLAMA
# ============================================================================

def generar_sql_especifica(
    pregunta: str,
    nombre_asignatura: str = None,
    contexto_titulacion: str = None,
    historial: str = ""
) -> Dict[str, Any]:
    """
    Genera una query SQL para obtener información de UNA asignatura específica.
    
    Args:
        pregunta: Pregunta del usuario en lenguaje natural
        nombre_asignatura: Nombre/código de la asignatura (si se extrajo)
        contexto_titulacion: ID de la titulación activa
        historial: Turnos previos de conversación para contexto
    
    Returns:
        Dict con 'sql', 'parametros', 'atributo_solicitado', 'explicacion'
    """
    
    contexto_conversacional = ""
    if historial:
        contexto_conversacional = f"""\nCONTEXTO DE LA CONVERSACIÓN PREVIA (usa esto para entender referencias implícitas):
{historial}\n"""

    # Clasificar si necesita RAG antes de generar SQL
    necesita_rag = _clasificar_necesita_rag(pregunta, historial)

    prompt = f"""Eres un experto en SQL. Tu tarea es generar una query SELECT para obtener información de UNA asignatura específica.

SCHEMA DE LA TABLA:
{ASIGNATURAS_SCHEMA}
{contexto_conversacional}
PREGUNTA DEL USUARIO: "{pregunta}"
{f'ASIGNATURA MENCIONADA: "{nombre_asignatura}"' if nombre_asignatura else ''}

INSTRUCCIONES:
1. Genera una query SELECT que obtenga la información pedida
2. Usa WHERE con ILIKE para buscar por nombre (tolerante a mayúsculas/tildes)
3. Siempre incluye: codigo, nombre, curso, creditos, duracion, tipologia
4. Si preguntan por un atributo específico (créditos, curso, etc.), también inclúyelo
5. Siempre añade: WHERE activa = true
6. Usa %s como placeholder para el nombre de la asignatura

RESPONDE SOLO CON JSON VÁLIDO:
{{
    "sql": "SELECT ... FROM asignaturas WHERE ...",
    "parametros": ["%valor%"],
    "atributo_solicitado": "creditos|curso|duracion|tipologia|general",
    "explicacion": "busca por nombre parcial"
}}

JSON:"""

    try:
        respuesta = llamar_llm(
            prompt,
            timeout=120,
            options={
                "temperature": 0.0,
                "num_predict": 100,
                "num_ctx": 384,
                "top_p": 0.9
            }
        )
        if respuesta:
            # Buscar JSON desde primera { hasta última }
            inicio = respuesta.find('{')
            fin = respuesta.rfind('}')

            if inicio != -1 and fin != -1 and fin > inicio:
                json_str = respuesta[inicio:fin+1]
                data = json.loads(json_str)
                # Validar la SQL generada
                sql_validada = validar_sql(data.get('sql', ''), tipo='select')
                if sql_validada:
                    data['sql'] = _inyectar_filtro_titulacion(sql_validada, contexto_titulacion)
                    data['valido'] = True
                    data['necesita_rag'] = necesita_rag
                    return data
    except Exception as e:
        print(f"Error generando SQL específica: {e}")
    
    # Fallback: query segura predefinida
    nombre_buscar = _expandir_alias(nombre_asignatura, contexto_titulacion) if nombre_asignatura else nombre_asignatura
    sql_fallback = """SELECT codigo, nombre, curso, creditos, duracion, tipologia,
                         es_formacion_basica, es_optativa
                  FROM asignaturas
                  WHERE activa = true AND (nombre_normalizado ILIKE %s OR codigo ILIKE %s)"""
    sql_fallback = _inyectar_filtro_titulacion(sql_fallback, contexto_titulacion)
    return {
        'sql': sql_fallback,
        'parametros': [f'%{nombre_buscar}%', f'%{nombre_buscar}%'] if nombre_buscar else ['%%', '%%'],
        'atributo_solicitado': 'general',
        'necesita_rag': necesita_rag,
        'explicacion': 'fallback - búsqueda por nombre',
        'valido': True
    }


def generar_sql_listado(
    pregunta: str,
    contexto_titulacion: str = None,
    historial: str = ""
) -> Dict[str, Any]:
    """
    Genera una query SQL para listar asignaturas con filtros.
    
    Args:
        pregunta: Pregunta del usuario
        contexto_titulacion: UUID de la titulación activa
        historial: Turnos previos de conversación para contexto
    
    Returns:
        Dict con 'sql', 'parametros', 'filtros_aplicados', 'explicacion'
    """
    
    # Construir parte del WHERE para titulación (subquery por código)
    where_titulacion = f" AND titulacion_id = {_subquery_titulacion(contexto_titulacion)}" if contexto_titulacion else ""
    
    contexto_conversacional = ""
    if historial:
        contexto_conversacional = f"""\nCONTEXTO DE LA CONVERSACIÓN PREVIA (si la pregunta actual es ambigua, usa el contexto para deducir filtros implícitos como curso, tipología, etc.):
{historial}\n"""

    prompt = f"""Genera SQL para listar asignaturas según esta pregunta: "{pregunta}"
{contexto_conversacional}

TABLA asignaturas:
- curso: INTEGER (1, 2, 3, 4)
- tipologia: VARCHAR ('OPTATIVA', 'OBLIGATORIA', 'TRONCAL', 'FORMACION_BASICA')
- duracion: VARCHAR ('A', 'C1', 'C2')
- creditos: DECIMAL (6, 12)
- activa: BOOLEAN

MAPEO:
"primero/1º" → curso = 1
"segundo/2º" → curso = 2
"tercero/3º" → curso = 3
"cuarto/4º" → curso = 4
"optativa" → tipologia = 'OPTATIVA'
"obligatoria" → tipologia = 'OBLIGATORIA'
"anual" → duracion = 'A'

EJEMPLOS:

"dame las asignaturas del primero"
{{"sql": "SELECT codigo, nombre, curso, creditos, duracion, tipologia FROM asignaturas WHERE activa = true AND curso = 1{where_titulacion} ORDER BY nombre", "parametros": [], "filtros_aplicados": {{"curso": 1}}}}

"asignaturas optativas de cuarto"
{{"sql": "SELECT codigo, nombre, curso, creditos, duracion, tipologia FROM asignaturas WHERE activa = true AND curso = 4 AND tipologia = 'OPTATIVA'{where_titulacion} ORDER BY nombre", "parametros": [], "filtros_aplicados": {{"curso": 4, "tipologia": "OPTATIVA"}}}}

GENERA SOLO EL JSON (sin explicaciones):"""

    try:
        respuesta = llamar_llm(
            prompt, 
            timeout=120,
            options={
                "temperature": 0.0,      # Determinístico para SQL
                "num_predict": 120,      # Solo necesitamos ~250 chars de JSON
                "num_ctx": 384,          # Contexto reducido = más rápido
                "top_p": 0.9
            }
        )
        if respuesta:
            print(f"🔍 Respuesta cruda del LLM:\n{respuesta}\n")
            
            # Buscar JSON desde primera { hasta última }
            inicio = respuesta.find('{')
            fin = respuesta.rfind('}')
            
            if inicio != -1 and fin != -1 and fin > inicio:
                json_str = respuesta[inicio:fin+1]
                print(f"🔍 JSON extraído: {json_str}")
                data = json.loads(json_str)
                sql_validada = validar_sql(data.get('sql', ''), tipo='select')
                if sql_validada:
                    data['sql'] = _inyectar_filtro_titulacion(sql_validada, contexto_titulacion)
                    data['valido'] = True
                    return data
            else:
                print("❌ No se encontró JSON en la respuesta")
    except json.JSONDecodeError as e:
        print(f"❌ Error parseando JSON: {e}")
    except Exception as e:
        print(f"Error generando SQL listado: {e}")
    
    # Fallback: listar todas las asignaturas activas
    sql_base = "SELECT codigo, nombre, curso, creditos, duracion, tipologia FROM asignaturas WHERE activa = true"
    sql_base = _inyectar_filtro_titulacion(sql_base, contexto_titulacion)
    sql_base += " ORDER BY curso, nombre"
    
    return {
        'sql': sql_base,
        'parametros': [],
        'filtros_aplicados': {},
        'explicacion': 'fallback - lista todas las asignaturas',
        'valido': True
    }


def generar_sql_conteo(
    pregunta: str,
    contexto_titulacion: str = None,
    historial: str = ""
) -> Dict[str, Any]:
    """
    Genera una query SQL COUNT para contar asignaturas.
    
    Args:
        pregunta: Pregunta del usuario
        contexto_titulacion: ID de la titulación activa
        historial: Turnos previos de conversación para contexto
    
    Returns:
        Dict con 'sql', 'parametros', 'filtros_aplicados', 'explicacion'
    """
    
    contexto_conversacional = ""
    if historial:
        contexto_conversacional = f"""\nCONTEXTO DE LA CONVERSACIÓN PREVIA (si la pregunta actual es ambigua, usa el contexto para deducir filtros implícitos):
{historial}\n"""

    prompt = f"""Eres un experto en SQL. Tu tarea es generar una query COUNT para contar asignaturas.

SCHEMA DE LA TABLA:
{ASIGNATURAS_SCHEMA}
{contexto_conversacional}
PREGUNTA DEL USUARIO: "{pregunta}"

EXTRAE LOS FILTROS DE LA PREGUNTA:
- curso: 1, 2, 3 o 4
- tipologia: OBLIGATORIA, OPTATIVA, TRONCAL, FORMACION_BASICA
- duracion: A, C1, C2
- creditos: 6 o 12

INSTRUCCIONES:
1. Genera SELECT COUNT(*) 
2. Añade filtros en WHERE según la pregunta
3. Siempre incluye: WHERE activa = true

RESPONDE SOLO CON JSON VÁLIDO:
{{
    "sql": "SELECT COUNT(*) FROM asignaturas WHERE ...",
    "parametros": [],
    "filtros_aplicados": {{"curso": 2, "tipologia": "OBLIGATORIA"}},
    "explicacion": "cuenta obligatorias de segundo"
}}

JSON:"""

    try:
        respuesta = llamar_llm(
            prompt, 
            timeout=120,
            options={
                "temperature": 0.0,
                "num_predict": 100,
                "num_ctx": 384,
                "top_p": 0.9
            }
        )
        if respuesta:
            # Buscar JSON desde primera { hasta última }
            inicio = respuesta.find('{')
            fin = respuesta.rfind('}')
            
            if inicio != -1 and fin != -1 and fin > inicio:
                json_str = respuesta[inicio:fin+1]
                data = json.loads(json_str)
                sql_validada = validar_sql(data.get('sql', ''), tipo='count')
                if sql_validada:
                    data['sql'] = _inyectar_filtro_titulacion(sql_validada, contexto_titulacion)
                    data['valido'] = True
                    return data
    except Exception as e:
        print(f"Error generando SQL conteo: {e}")
    
    # Fallback
    sql_base = "SELECT COUNT(*) FROM asignaturas WHERE activa = true"
    sql_base = _inyectar_filtro_titulacion(sql_base, contexto_titulacion)
    
    return {
        'sql': sql_base,
        'parametros': [],
        'filtros_aplicados': {},
        'explicacion': 'fallback - cuenta todas las asignaturas',
        'valido': True
    }


# ============================================================================
# VALIDACIÓN DE SEGURIDAD SQL
# ============================================================================

def validar_sql(sql: str, tipo: str = 'select') -> Optional[str]:
    """
    Valida que la SQL generada sea segura.
    
    Args:
        sql: Query SQL a validar
        tipo: 'select' o 'count'
    
    Returns:
        SQL validada/limpiada o None si es inválida
    """
    if not sql:
        return None
    
    sql_upper = sql.upper().strip()
    
    # 1. Solo permitir SELECT (nunca INSERT, UPDATE, DELETE, DROP, etc.)
    palabras_prohibidas = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 
        'TRUNCATE', 'EXEC', 'EXECUTE', 'GRANT', 'REVOKE', '--', ';--',
        'UNION SELECT', 'OR 1=1', "OR '1'='1'", 'SLEEP(', 'BENCHMARK('
    ]
    
    for palabra in palabras_prohibidas:
        if palabra in sql_upper:
            print(f"⚠️ SQL rechazada: contiene '{palabra}'")
            return None
    
    # 2. Debe empezar con SELECT
    if not sql_upper.startswith('SELECT'):
        print(f"⚠️ SQL rechazada: no empieza con SELECT")
        return None
    
    # 3. Solo puede acceder a la tabla 'asignaturas'
    # Buscar nombres de tabla después de FROM o JOIN
    tablas_mencionadas = re.findall(r'FROM\s+(\w+)|JOIN\s+(\w+)', sql_upper)
    tablas_flat = [t for grupo in tablas_mencionadas for t in grupo if t]
    
    tablas_permitidas = {'ASIGNATURAS', 'TITULACIONES'}
    for tabla in tablas_flat:
        if tabla not in tablas_permitidas:
            print(f"⚠️ SQL rechazada: tabla no permitida '{tabla}'")
            return None
    
    # 4. Para COUNT, verificar que sea COUNT(*)
    if tipo == 'count' and 'COUNT(*)' not in sql_upper and 'COUNT(' not in sql_upper:
        print(f"⚠️ SQL COUNT rechazada: no contiene COUNT")
        return None
    
    # 5. Verificar columnas en SELECT (excepto para COUNT(*))
    if tipo == 'select' and 'COUNT(*)' not in sql_upper:
        # Extraer columnas del SELECT
        match = re.search(r'SELECT\s+(.+?)\s+FROM', sql_upper, re.DOTALL)
        if match:
            columnas_str = match.group(1)
            if columnas_str.strip() != '*':
                columnas = [c.strip().split('.')[-1] for c in columnas_str.split(',')]
                columnas_upper = {c.upper() for c in columnas}
                columnas_permitidas_upper = {c.upper() for c in COLUMNAS_PERMITIDAS}
                
                for col in columnas_upper:
                    # Ignorar alias (AS ...) y funciones
                    col_limpia = col.split(' AS ')[0].strip()
                    if col_limpia and col_limpia not in columnas_permitidas_upper:
                        # Podría ser COUNT, etc. - permitir funciones
                        if not any(f in col_limpia for f in ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN']):
                            print(f"⚠️ SQL rechazada: columna no permitida '{col_limpia}'")
                            return None
    
    # 6. Limpiar placeholders: el LLM a veces genera '%s' en vez de %s
    #    psycopg2 gestiona el quoting, así que las comillas sobran
    sql = re.sub(r"'(%s)'", r'\1', sql)

    print(f"✅ SQL validada: {sql[:80]}...")
    return sql


# ============================================================================
# EJECUCIÓN SEGURA DE QUERIES
# ============================================================================

def ejecutar_query(sql: str, parametros: List = None) -> Tuple[bool, Any]:
    """
    Ejecuta una query SQL de forma segura.
    
    Args:
        sql: Query SQL validada
        parametros: Lista de parámetros para la query
    
    Returns:
        Tuple (exito: bool, resultados o mensaje_error)
    """
    if db_client is None:
        return False, "Base de datos no disponible"
    
    conn = db_client.get_connection()
    if not conn:
        return False, "No se pudo conectar a la base de datos"
    
    try:
        cursor = conn.cursor()
        
        if parametros:
            cursor.execute(sql, parametros)
        else:
            cursor.execute(sql)
        
        # Obtener nombres de columnas
        columnas = [desc[0] for desc in cursor.description] if cursor.description else []
        
        # Obtener resultados
        filas = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Convertir a lista de diccionarios
        resultados = []
        for fila in filas:
            resultado = {}
            for i, valor in enumerate(fila):
                if i < len(columnas):
                    resultado[columnas[i]] = valor
            resultados.append(resultado)
        
        return True, resultados
        
    except Exception as e:
        print(f"❌ Error ejecutando query: {e}")
        if conn:
            conn.close()
        return False, str(e)


def ejecutar_count(sql: str, parametros: List = None) -> Tuple[bool, int]:
    """
    Ejecuta una query COUNT y devuelve el número.
    
    Args:
        sql: Query COUNT validada
        parametros: Lista de parámetros
    
    Returns:
        Tuple (exito: bool, count o -1)
    """
    if db_client is None:
        return False, -1
    
    conn = db_client.get_connection()
    if not conn:
        return False, -1
    
    try:
        cursor = conn.cursor()
        
        if parametros:
            cursor.execute(sql, parametros)
        else:
            cursor.execute(sql)
        
        resultado = cursor.fetchone()
        count = resultado[0] if resultado else 0
        
        cursor.close()
        conn.close()
        
        return True, count
        
    except Exception as e:
        print(f"❌ Error ejecutando COUNT: {e}")
        if conn:
            conn.close()
        return False, -1


# ============================================================================
# GENERACIÓN DE RESPUESTA NATURAL (CENTRALIZADA)
# ============================================================================

DURACION_NOMBRES = {
    'A': 'Anual',
    'C1': 'Primer cuatrimestre',
    'C2': 'Segundo cuatrimestre'
}


def formatear_datos_para_prompt(datos: Any, tipo: str) -> str:
    """
    Convierte los datos crudos de la BD en texto legible para el prompt.
    No genera la respuesta final — solo prepara los datos.
    
    Args:
        datos: Resultado de la query (dict, list[dict], o int)
        tipo: 'especifica', 'listado', 'conteo'
    
    Returns:
        Texto con los datos formateados
    """
    if tipo == 'conteo':
        return f"RESULTADO: {datos} asignaturas encontradas."
    
    if tipo == 'especifica' and isinstance(datos, dict):
        lineas = []
        if datos.get('codigo'):
            lineas.append(f"- Código: {datos['codigo']}")
        if datos.get('nombre'):
            lineas.append(f"- Nombre: {datos['nombre']}")
        if datos.get('curso'):
            lineas.append(f"- Curso: {datos['curso']}º")
        if datos.get('creditos'):
            lineas.append(f"- Créditos: {datos['creditos']} ECTS")
        if datos.get('duracion'):
            dur = DURACION_NOMBRES.get(datos['duracion'], datos['duracion'])
            lineas.append(f"- Duración: {dur}")
        if datos.get('tipologia'):
            lineas.append(f"- Tipología: {datos['tipologia']}")
        return '\n'.join(lineas)
    
    if tipo == 'listado' and isinstance(datos, list):
        lineas = [f"Se encontraron {len(datos)} asignaturas:"]
        for asig in datos:
            nombre = asig.get('nombre', '?')
            curso = asig.get('curso', '?')
            creditos = asig.get('creditos', '?')
            tipologia = asig.get('tipologia', '?')
            duracion = DURACION_NOMBRES.get(asig.get('duracion', ''), '?')
            lineas.append(f"- {nombre} | {curso}º curso | {creditos} ECTS | {tipologia} | {duracion}")
        return '\n'.join(lineas)
    
    # Fallback: serializar como JSON legible
    return json.dumps(datos, ensure_ascii=False, default=str, indent=2)


def generar_respuesta_natural(
    pregunta: str,
    datos: Any,
    tipo: str = 'especifica'
) -> str:
    """
    Función CENTRALIZADA de generación de respuesta.
    Recibe la pregunta del usuario + los datos crudos de la BD,
    y deja que Ollama genere una respuesta natural.
    
    Args:
        pregunta: Pregunta original del usuario
        datos: Resultado de la query (dict, list, int, etc.)
        tipo: 'especifica' | 'listado' | 'conteo'
    
    Returns:
        Respuesta natural generada por el modelo
    """
    # Preparar datos como texto legible
    datos_texto = formatear_datos_para_prompt(datos, tipo)
    
    prompt = f"""Eres Linceus, un asistente universitario de la ETSII (Universidad de Sevilla).
Responde a la pregunta del usuario usando SOLO los datos proporcionados.

PREGUNTA DEL USUARIO: "{pregunta}"

DATOS OBTENIDOS DE LA BASE DE DATOS:
{datos_texto}

REGLAS:
- Responde de forma natural, cercana y concisa
- Si la pregunta es sobre un atributo concreto (créditos, curso, etc.), céntrate en ese dato
- Si es una lista, preséntala de forma organizada y legible
- Si es un conteo, responde con una frase natural
- No inventes datos que no estén en los datos proporcionados
- Si los datos están vacíos o no hay resultados, dilo amablemente
- Puedes usar markdown para formatear (negritas, listas)
- No repitas la pregunta del usuario
- No digas "según los datos" ni menciones la base de datos
- No saludes (nada de "¡Hola!", "Hola!", "Buenos días", etc.) — ve directo a la respuesta
- IMPORTANTE: Tu respuesta debe tener como MÁXIMO 1500 caracteres. Si hay mucha información, resume lo más relevante

Respuesta:"""

    try:
        respuesta = llamar_llm(
            prompt,
            timeout=120,
            options={
                "temperature": 0.3,
                "num_predict": 800,
                "num_ctx": 2048,
            }
        )
        if respuesta:
            return respuesta.strip()
    except Exception as e:
        print(f"Error generando respuesta natural: {e}")
    
    # Fallback si el LLM falla: respuesta básica legible
    return _fallback_respuesta(datos, tipo)


def _fallback_respuesta(datos: Any, tipo: str) -> str:
    """Genera una respuesta básica si Ollama no responde."""
    if tipo == 'conteo':
        return f"Hay **{datos}** asignaturas."
    
    if tipo == 'especifica' and isinstance(datos, dict):
        nombre = datos.get('nombre', 'La asignatura')
        curso = datos.get('curso', '?')
        creditos = datos.get('creditos', '?')
        tipologia = datos.get('tipologia', '').lower()
        return f"**{nombre}** es una asignatura {tipologia} de {curso}º curso con {creditos} créditos ECTS."
    
    if tipo == 'listado' and isinstance(datos, list):
        lineas = [f"Encontré **{len(datos)}** asignaturas:", ""]
        for asig in datos:
            lineas.append(f"- **{asig.get('nombre', '?')}** ({asig.get('curso', '?')}º, {asig.get('creditos', '?')} ECTS)")
        return '\n'.join(lineas)
    
    return "No pude generar una respuesta. ¿Puedes reformular tu pregunta?"
