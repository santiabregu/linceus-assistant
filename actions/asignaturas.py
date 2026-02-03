# Actions relacionadas con la épica de Asignaturas
# v2.0.0 - Sistema Text-to-SQL integrado para consultas dinámicas

from typing import Any, Text, Dict, List, Optional, Tuple
from rapidfuzz import fuzz, process
import unicodedata
import json
import re
from decimal import Decimal

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from .db import db_client
from .config import BotConfig
from .ollama_client import llamar_ollama, verificar_ollama_activo


# =============================================================================
# CACHE DE ASIGNATURAS POR SESIÓN/TITULACIÓN
# =============================================================================

def cargar_asignaturas_titulacion(
    contexto_centro: str,
    contexto_titulacion: str = None
) -> List[Dict[str, Any]]:
    """
    Carga TODAS las asignaturas de una titulación específica.

    Esta función se llama UNA VEZ por sesión cuando el usuario
    hace su primera consulta sobre asignaturas.

    Args:
        contexto_centro: Código del centro (ej: "ETSII")
        contexto_titulacion: ID de titulación (opcional)

    Returns:
        Lista con ~50 asignaturas de esa titulación
    """
    if db_client is None:
        print("❌ No hay conexión a BD")
        return []

    conn = db_client.get_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor()

        # Query para obtener TODAS las asignaturas activas de la titulación
        if contexto_titulacion:
            query = """
                SELECT
                    codigo, nombre, curso, creditos, duracion, tipologia,
                    es_formacion_basica, es_optativa, titulacion_id
                FROM asignaturas
                WHERE activa = true AND titulacion_id = %s
                ORDER BY curso, nombre
            """
            cursor.execute(query, (contexto_titulacion,))
            print(f"🔍 Cargando asignaturas de titulacion_id: {contexto_titulacion}")
        else:
            # Si no hay titulación, filtrar por CÓDIGO de centro
            query = """
                SELECT DISTINCT
                    a.codigo, a.nombre, a.curso, a.creditos, a.duracion, a.tipologia,
                    a.es_formacion_basica, a.es_optativa, a.titulacion_id
                FROM asignaturas a
                JOIN titulaciones t ON a.titulacion_id = t.id
                JOIN centros c ON t.centro_id = c.id
                WHERE a.activa = true AND c.codigo = %s
                ORDER BY a.curso, a.nombre
            """
            cursor.execute(query, (contexto_centro,))
            print(f"🔍 Cargando asignaturas de centro código: '{contexto_centro}'")

        resultados = cursor.fetchall()

        # Convertir a diccionarios
        asignaturas = []
        for r in resultados:
            asignaturas.append({
                "codigo": r[0],
                "nombre": r[1],
                "curso": r[2],
                "creditos": r[3],
                "duracion": r[4],
                "tipologia": r[5],
                "es_formacion_basica": r[6],
                "es_optativa": r[7],
                "titulacion_id": r[8]
            })

        cursor.close()

        print(f"✅ Asignaturas cargadas en memoria: {len(asignaturas)} (titulación: {contexto_titulacion or contexto_centro})")

        return asignaturas

    except Exception as e:
        print(f"❌ Error cargando asignaturas: {e}")
        return []
    finally:
        conn.close()


def buscar_en_memoria(
    nombre_o_codigo: str,
    asignaturas: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Busca una asignatura en la lista en memoria usando fuzzy matching.

    Args:
        nombre_o_codigo: Nombre o código a buscar
        asignaturas: Lista de asignaturas en memoria

    Returns:
        Asignatura encontrada o None
    """
    if not asignaturas:
        return None

    # 1. Búsqueda exacta por código (case-insensitive)
    for asig in asignaturas:
        if asig["codigo"].upper() == nombre_o_codigo.upper():
            print(f"✅ Match exacto por código: {asig['nombre']}")
            return asig

    # 2. Búsqueda exacta por nombre (case-insensitive)
    for asig in asignaturas:
        if asig["nombre"].upper() == nombre_o_codigo.upper():
            print(f"✅ Match exacto por nombre: {asig['nombre']}")
            return asig

    # 3. Fuzzy matching
    nombres = [a["nombre"] for a in asignaturas]
    codigos = [a["codigo"] for a in asignaturas]

    # Buscar por nombre
    matches_nombre = process.extract(
        nombre_o_codigo,
        nombres,
        scorer=fuzz.WRatio,
        limit=3
    )

    # Buscar por código
    matches_codigo = process.extract(
        nombre_o_codigo,
        codigos,
        scorer=fuzz.ratio,
        limit=3
    )

    # Elegir mejor match
    mejor_score = 0
    mejor_asig = None

    for match, score, idx in matches_nombre:
        if score > mejor_score and score >= 70:
            mejor_score = score
            mejor_asig = asignaturas[idx]

    for match, score, idx in matches_codigo:
        if score > mejor_score and score >= 75:
            mejor_score = score
            mejor_asig = asignaturas[idx]

    if mejor_asig:
        print(f"✅ Fuzzy match: {mejor_asig['nombre']} (score: {mejor_score})")
    else:
        print(f"❌ No encontrada: '{nombre_o_codigo}'")

    return mejor_asig


def filtrar_en_memoria(
    asignaturas: List[Dict[str, Any]],
    **filtros
) -> List[Dict[str, Any]]:
    """
    Filtra asignaturas en memoria según criterios.

    Args:
        asignaturas: Lista de asignaturas en memoria
        **filtros: curso=1, tipologia="OBLIGATORIA", duracion="C1", etc.

    Returns:
        Lista filtrada
    """
    resultados = asignaturas

    for key, value in filtros.items():
        if value is not None:
            resultados = [a for a in resultados if a.get(key) == value]

    print(f"🔍 Filtros {filtros} → {len(resultados)}/{len(asignaturas)} resultados")

    return resultados


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def limpiar_ansi(texto: str) -> str:
    """Elimina códigos de escape ANSI del texto."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\[\?[0-9;]*[a-zA-Z]|\[K|\[G)')
    return ansi_escape.sub('', texto)


# =============================================================================
# TEMPLATES DE RESPUESTA RÁPIDA (sin LLM)
# =============================================================================

def respuesta_template(asignatura: Dict[str, Any], atributo: str) -> str:
    """
    Genera respuesta directa sin LLM para casos simples.
    Mucho más rápido que llamar al LLM.
    """
    nombre = asignatura.get("nombre", "La asignatura")

    if atributo == "creditos":
        creditos = asignatura.get("creditos", "N/A")
        return f"{nombre} tiene {creditos} créditos ECTS."

    elif atributo == "tipo":
        tipologia = asignatura.get("tipologia", "").upper()
        es_formacion_basica = asignatura.get("es_formacion_basica", False)

        # Detectar si es de formación básica
        if es_formacion_basica or "BASICA" in tipologia or "FORMACION" in tipologia:
            return f"No, {nombre} es de formación básica."
        elif tipologia == "OBLIGATORIA":
            return f"Sí, {nombre} es obligatoria."
        elif tipologia == "OPTATIVA":
            return f"No, {nombre} es optativa."
        elif tipologia == "TRONCAL":
            return f"Sí, {nombre} es troncal (obligatoria)."
        else:
            return f"{nombre} es de tipo {tipologia.lower().replace('_', ' ')}."

    elif atributo == "curso":
        curso = asignatura.get("curso", "N/A")
        return f"{nombre} está en {curso}º curso."

    elif atributo == "cuatrimestre" or atributo == "duracion":
        duracion = asignatura.get("duracion", "")
        if duracion == "A":
            return f"{nombre} es anual."
        elif duracion == "C1":
            return f"{nombre} es del primer cuatrimestre."
        elif duracion == "C2":
            return f"{nombre} es del segundo cuatrimestre."
        else:
            return f"{nombre} tiene duración {duracion}."

    elif atributo == "general":
        codigo = asignatura.get("codigo", "")
        creditos = asignatura.get("creditos", "N/A")
        curso = asignatura.get("curso", "N/A")
        tipologia = asignatura.get("tipologia", "").upper()
        es_formacion_basica = asignatura.get("es_formacion_basica", False)

        # Tipo de asignatura más natural
        if es_formacion_basica:
            tipo_str = "de formación básica"
        elif tipologia == "OBLIGATORIA":
            tipo_str = "obligatoria"
        elif tipologia == "OPTATIVA":
            tipo_str = "optativa"
        elif tipologia == "TRONCAL":
            tipo_str = "troncal"
        else:
            tipo_str = tipologia.lower().replace("_", " ")

        return f"{nombre} ({codigo}) es una asignatura {tipo_str} de {curso}º curso con {creditos} créditos ECTS."

    # Fallback
    return f"{nombre}: {asignatura}"


def respuesta_template_lista(asignaturas: List[Dict], pregunta: str) -> str:
    """Genera respuesta para listas sin LLM."""
    n = len(asignaturas)

    if n == 0:
        return "No encontré asignaturas que cumplan los criterios."

    lineas = [f"Encontré {n} asignatura{'s' if n > 1 else ''}:\n"]

    for i, asig in enumerate(asignaturas[:10], 1):
        nombre = asig.get("nombre", "Sin nombre")
        codigo = asig.get("codigo", "")
        creditos = asig.get("creditos", "")
        curso = asig.get("curso", "")

        detalle = f"{i}. {nombre}"
        extras = []
        if codigo:
            extras.append(codigo)
        if curso:
            extras.append(f"{curso}º")
        if creditos:
            extras.append(f"{creditos} ECTS")
        if extras:
            detalle += f" ({', '.join(map(str, extras))})"
        lineas.append(detalle)

    if n > 10:
        lineas.append(f"\n... y {n - 10} más.")

    return "\n".join(lineas)


def respuesta_template_count(count: int, pregunta: str) -> str:
    """Genera respuesta para conteos sin LLM."""
    # Detectar contexto de la pregunta para respuesta más natural
    pregunta_lower = pregunta.lower()

    if "optativa" in pregunta_lower:
        return f"Hay {count} asignatura{'s' if count != 1 else ''} optativa{'s' if count != 1 else ''}."
    elif "obligatoria" in pregunta_lower:
        return f"Hay {count} asignatura{'s' if count != 1 else ''} obligatoria{'s' if count != 1 else ''}."
    elif "primero" in pregunta_lower or "primer" in pregunta_lower:
        return f"En primero hay {count} asignatura{'s' if count != 1 else ''}."
    elif "segundo" in pregunta_lower:
        return f"En segundo hay {count} asignatura{'s' if count != 1 else ''}."
    elif "tercero" in pregunta_lower:
        return f"En tercero hay {count} asignatura{'s' if count != 1 else ''}."
    elif "cuarto" in pregunta_lower:
        return f"En cuarto hay {count} asignatura{'s' if count != 1 else ''}."
    else:
        return f"Hay {count} asignatura{'s' if count != 1 else ''}."


def _convertir_decimales(obj):
    """Convierte objetos Decimal a float para serialización JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: _convertir_decimales(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convertir_decimales(item) for item in obj]
    return obj


def generar_respuesta_natural(
    pregunta_usuario: str,
    datos: Dict[str, Any],
    tipo_respuesta: str = "especifica"
) -> str:
    """
    Genera una respuesta natural usando el LLM basada en datos estructurados.

    Args:
        pregunta_usuario: Pregunta original del usuario
        datos: Datos estructurados de la BD
        tipo_respuesta: "especifica" | "lista" | "count"

    Returns:
        Respuesta natural generada por el LLM
    """

    # Convertir Decimals a float
    datos = _convertir_decimales(datos)

    if tipo_respuesta == "especifica":
        # Respuesta sobre una asignatura específica
        prompt = f"""Responde DIRECTAMENTE basándote en estos datos:

PREGUNTA: "{pregunta_usuario}"

DATOS:
{json.dumps(datos, indent=2, ensure_ascii=False)}

REGLAS:
1. Si preguntan "es obligatoria/optativa": Responde "Sí, es [tipología]" o "No, es [tipología]"
2. Si preguntan créditos: Di exactamente cuántos créditos tiene
3. Si preguntan curso: Di en qué curso está
4. Si preguntan "qué es": Da nombre completo, código, curso y créditos
5. NO seas ambiguo. Los datos son HECHOS, no opiniones
6. NO digas "para muchos estudiantes" o frases vagas
7. Sé breve (máximo 2 frases)

EJEMPLOS:
- "¿Redes es obligatoria?" + tipologia="OBLIGATORIA" → "Sí, Redes de Computadores es obligatoria."
- "¿Redes es obligatoria?" + tipologia="OPTATIVA" → "No, Redes de Computadores es optativa."
- "¿cuántos créditos tiene?" + creditos=6 → "Tiene 6 créditos ECTS."

Respuesta:"""

    elif tipo_respuesta == "lista":
        # Respuesta con lista de asignaturas
        num_resultados = len(datos) if isinstance(datos, list) else 1

        prompt = f"""Eres un asistente universitario amigable.

Pregunta del usuario: "{pregunta_usuario}"

Encontré {num_resultados} asignaturas:
{json.dumps(datos, indent=2, ensure_ascii=False)}

Genera una respuesta NATURAL que presente estos resultados de forma conversacional.

Reglas:
- Empieza con una frase natural ("Encontré X asignaturas...", "Aquí tienes las asignaturas...")
- Lista las asignaturas de forma clara pero natural
- Menciona detalles importantes (código, créditos, curso) de forma fluida
- Si son muchas (>5), menciona solo las primeras y di que hay más
- Usa lenguaje coloquial pero profesional

Respuesta:"""

    elif tipo_respuesta == "count":
        # Respuesta de conteo
        count = datos.get("count", 0) if isinstance(datos, dict) else datos

        prompt = f"""Eres un asistente universitario amigable.

Pregunta del usuario: "{pregunta_usuario}"

Resultado: Hay {count} asignaturas que cumplen los criterios.

Genera una respuesta BREVE y NATURAL que comunique este número de forma conversacional.

Ejemplos:
- "Hay 8 asignaturas en segundo cuatrimestre"
- "En primero tienes 10 asignaturas"
- "Son 6 optativas en total"

Respuesta (una sola frase):"""

    else:
        # Fallback
        return str(datos)

    try:
        respuesta = llamar_ollama(prompt, timeout=30)  # Aumentado para listas

        if respuesta and len(respuesta) > 10:
            print(f"✅ Respuesta natural generada: {respuesta[:100]}...\n")
            return respuesta

    except Exception as e:
        print(f"❌ Error generando respuesta natural: {e}")

    # Fallback: respuesta estructurada básica
    print("⚠️  Usando respuesta estructurada (fallback)")

    if tipo_respuesta == "especifica":
        if "nombre" in datos:
            return f"{datos['nombre']} - {datos.get('creditos', 'N/A')} ECTS, {datos.get('tipologia', 'N/A')}"

    elif tipo_respuesta == "lista":
        if isinstance(datos, list) and len(datos) > 0:
            lineas = [f"📋 Asignaturas encontradas ({len(datos)}):\n"]
            for i, item in enumerate(datos[:10], 1):
                nombre = item.get('nombre', 'N/A')
                creditos = item.get('creditos', 'N/A')
                codigo = item.get('codigo', '')
                lineas.append(f"{i}. {nombre} ({codigo}) - {creditos} ECTS")
            if len(datos) > 10:
                lineas.append(f"\n... y {len(datos) - 10} más")
            return "\n".join(lineas)

    elif tipo_respuesta == "count":
        count = datos.get("count", datos) if isinstance(datos, dict) else datos
        return f"Hay {count} asignaturas."

    return str(datos)


# =============================================================================
# TEXT-TO-SQL PARA ASIGNATURAS
# =============================================================================

def analizar_consulta_unificado(pregunta: str) -> Dict[str, Any]:
    """
    Analiza una consulta en UNA SOLA llamada al LLM.
    Combina clasificación + extracción de datos.

    Optimización: Reduce de 2-3 llamadas LLM a 1 sola.

    Returns:
        Dict con:
        - tipo: "especifica" o "general"
        - nombre_asignatura: str o None
        - atributo_solicitado: str o None
        - confianza: float
    """
    pregunta_lower = pregunta.lower()

    # =========================================================================
    # HEURÍSTICAS RÁPIDAS (sin LLM)
    # =========================================================================

    # Detectar códigos de asignatura (IS2, FP, etc.)
    codigo_match = re.search(r'\b([A-Z]{2,4}\d?)\b', pregunta)

    # Patrones específicos con extracción (con y sin tildes)
    patrones_especificos = [
        # Créditos
        (r'(?:cuántos|cuantos|cuanto)\s+(?:créditos|creditos)\s+tiene\s+(.+?)(?:\?|$)', "creditos"),
        (r'(?:créditos|creditos)\s+(?:de|tiene)\s+(.+?)(?:\?|$)', "creditos"),
        (r'(.+?)\s+tiene\s+(?:cuántos|cuantos|cuanto)\s+(?:créditos|creditos)', "creditos"),
        # Obligatoria/Optativa
        (r'(.+?)\s+es\s+(?:obligatoria|optativa)', "tipo"),
        (r'(?:es\s+obligatoria|es\s+optativa)\s+(.+?)(?:\?|$)', "tipo"),
        # Curso
        (r'(?:en\s+)?(?:qué|que)\s+curso\s+(?:está|esta)\s+(.+?)(?:\?|$)', "curso"),
        (r'(?:curso\s+de)\s+(.+?)(?:\?|$)', "curso"),
        # Qué es
        (r'(?:qué|que)\s+es\s+(.+?)(?:\?|$)', "general"),
        (r'(?:información|info)\s+(?:de|sobre)\s+(.+?)(?:\?|$)', "general"),
        # Cuatrimestre
        (r'(?:cuatrimestre|cuatri)\s+(?:de|tiene)\s+(.+?)(?:\?|$)', "cuatrimestre"),
    ]

    for patron, atributo in patrones_especificos:
        match = re.search(patron, pregunta_lower, re.IGNORECASE)
        if match:
            nombre = match.group(1).strip()
            # Limpiar nombre
            nombre = re.sub(r'^(la\s+asignatura\s+de|la\s+asignatura|asignatura)\s+', '', nombre)
            nombre = nombre.strip('?.,! ')

            if len(nombre) > 1:
                print(f"✅ Heurística específica: '{nombre}' → {atributo}")
                return {
                    "tipo": "especifica",
                    "nombre_asignatura": nombre,
                    "atributo_solicitado": atributo,
                    "confianza": 0.95,
                    "metodo": "heuristica"
                }

    # Si hay código detectado, es específica
    if codigo_match:
        codigo = codigo_match.group(1)
        # Detectar atributo
        atributo = "general"
        if "crédito" in pregunta_lower or "credito" in pregunta_lower:
            atributo = "creditos"
        elif "obligatoria" in pregunta_lower or "optativa" in pregunta_lower:
            atributo = "tipo"
        elif "curso" in pregunta_lower:
            atributo = "curso"

        print(f"✅ Heurística código: '{codigo}' → {atributo}")
        return {
            "tipo": "especifica",
            "nombre_asignatura": codigo,
            "atributo_solicitado": atributo,
            "confianza": 0.9,
            "metodo": "heuristica_codigo"
        }

    # Patrones claramente generales
    patrones_general = [
        r'(?:asignaturas|materias)\s+(?:de|del|en)\s+(?:primero|segundo|tercero|cuarto|1|2|3|4)',
        r'(?:cuántas|cuantas)\s+(?:asignaturas|optativas|obligatorias)',
        r'(?:lista|listado)\s+(?:de\s+)?(?:asignaturas|optativas|obligatorias)',
        r'(?:optativas|obligatorias)\s+(?:de|del|en)',
        r'(?:todas\s+las\s+)?asignaturas\s+(?:del\s+)?(?:primer|segundo)\s+cuatri',
    ]

    for patron in patrones_general:
        if re.search(patron, pregunta_lower):
            print(f"✅ Heurística general detectada")
            return {
                "tipo": "general",
                "nombre_asignatura": None,
                "atributo_solicitado": None,
                "confianza": 0.9,
                "metodo": "heuristica"
            }

    # =========================================================================
    # LLM: Solo si las heurísticas no funcionan
    # =========================================================================

    prompt = f"""Analiza esta consulta universitaria:

PREGUNTA: "{pregunta}"

Clasifica y extrae en JSON:
- tipo: "especifica" (UNA asignatura) o "general" (varias/filtros)
- nombre_asignatura: nombre o código mencionado (o null si general)
- atributo: "creditos"|"tipo"|"curso"|"cuatrimestre"|"general" (o null si general)

EJEMPLOS:
"cuántos créditos tiene Redes" → {{"tipo":"especifica","nombre_asignatura":"Redes","atributo":"creditos"}}
"asignaturas de primero" → {{"tipo":"general","nombre_asignatura":null,"atributo":null}}
"IS2 es obligatoria?" → {{"tipo":"especifica","nombre_asignatura":"IS2","atributo":"tipo"}}

JSON:"""

    try:
        salida = llamar_ollama(prompt, timeout=15)

        if not salida:
            raise Exception("Sin respuesta")

        # Extraer JSON
        match = re.search(r'\{[^{}]*"tipo"[^{}]*\}', salida)
        if match:
            data = json.loads(match.group(0))
            data["confianza"] = 0.8
            data["metodo"] = "llm"
            print(f"✅ LLM unificado: tipo={data.get('tipo')}, asig={data.get('nombre_asignatura')}")
            return data

    except Exception as e:
        print(f"⚠️ Error en LLM unificado: {e}")

    # Fallback: asumir general
    return {
        "tipo": "general",
        "nombre_asignatura": None,
        "atributo_solicitado": None,
        "confianza": 0.5,
        "metodo": "fallback"
    }


def clasificar_tipo_consulta_asignatura(pregunta: str) -> Dict[str, Any]:
    """
    Clasifica si una consulta sobre asignaturas es ESPECÍFICA o GENERAL.

    - ESPECÍFICA: Pregunta sobre UNA asignatura concreta
      Ejemplos: "cuántos créditos tiene Redes", "qué es IS2", "Redes es obligatoria?"

    - GENERAL: Pregunta sobre MÚLTIPLES asignaturas con filtros
      Ejemplos: "asignaturas de primero", "cuántas optativas hay", "asignaturas del segundo cuatri"

    Args:
        pregunta: Pregunta del usuario

    Returns:
        Dict con:
        - tipo: "especifica" o "general"
        - confianza: float 0-1
        - razon: explicación breve
    """

    # Heurística rápida ANTES de llamar al LLM
    pregunta_lower = pregunta.lower()

    # Patrones que SIEMPRE indican consulta específica
    patrones_especifica = [
        r'\bla asignatura\b',  # "la asignatura de X"
        r'\bcuántos créditos tiene\b',
        r'\bcuantos creditos tiene\b',
        r'\bqué es\b',
        r'\bque es\b',
        r'\bes obligatoria\b',
        r'\bes optativa\b',
        r'\b[A-Z]{2,}\b',  # Códigos como IS2, FP, etc.
    ]

    for patron in patrones_especifica:
        if re.search(patron, pregunta, re.IGNORECASE):
            return {"tipo": "especifica", "confianza": 0.9, "razon": "Heurística: patrón específico"}

    # Patrones que SIEMPRE indican consulta general
    patrones_general = [
        r'\basignaturas de\b',
        r'\bcuántas asignaturas\b',
        r'\bcuantas asignaturas\b',
        r'\boptativas de\b',
        r'\bobligatorias de\b',
    ]

    for patron in patrones_general:
        if re.search(patron, pregunta, re.IGNORECASE):
            return {"tipo": "general", "confianza": 0.9, "razon": "Heurística: patrón general"}

    # Si no hay coincidencia clara, usar LLM
    prompt = f"""Pregunta: "{pregunta}"

¿Pregunta sobre UNA asignatura o VARIAS?

UNA → {{"tipo":"especifica"}}
VARIAS → {{"tipo":"general"}}
"""

    try:
        salida = llamar_ollama(prompt, timeout=15)  # Reducido a 15s

        if not salida:
            raise Exception("LLM no devolvió respuesta")

        # Extraer JSON
        match = re.search(r'\{[^{}]*"tipo"[^{}]*\}', salida)
        if match:
            data = json.loads(match.group(0))
            print(f"🔍 Clasificación LLM: {data.get('tipo')} (confianza: {data.get('confianza')})")
            print(f"   Razón: {data.get('razon')}\n")
            return data

    except Exception as e:
        print(f"❌ Error en LLM: {e}")

    # Fallback final: asumir general
    return {"tipo": "general", "confianza": 0.5, "razon": "Fallback final"}


def extraer_datos_consulta_especifica(
    pregunta: str,
    contexto_centro: str = "ETSII",
    contexto_titulacion: str = None
) -> Dict[str, Any]:
    """
    Extrae nombre de asignatura y atributo solicitado de una consulta específica.

    Args:
        pregunta: Pregunta del usuario
        contexto_centro: Centro universitario
        contexto_titulacion: Titulación (opcional)

    Returns:
        Dict con:
        - nombre_asignatura: str
        - atributo_solicitado: "creditos"|"tipo"|"curso"|"cuatrimestre"|"general"|None
        - error: str si hubo error
    """

    prompt = f"""Extrae información de esta consulta sobre una asignatura específica.

CONTEXTO:
- Centro: {contexto_centro}
- Titulación: {contexto_titulacion or "No especificada"}

PREGUNTA: "{pregunta}"

EXTRAE:
1. nombre_asignatura: Nombre o código de la asignatura mencionada
2. atributo_solicitado: Qué quiere saber el usuario
   - "creditos": Si pregunta por créditos/ECTS
   - "tipo": Si pregunta si es obligatoria/optativa/básica
   - "curso": Si pregunta en qué curso está
   - "cuatrimestre": Si pregunta en qué cuatrimestre
   - "duracion": Si pregunta si es anual/cuatrimestral
   - "general": Si quiere información completa de la asignatura

EJEMPLOS:
- "cuántos créditos tiene Redes" → {{"nombre_asignatura": "Redes", "atributo_solicitado": "creditos"}}
- "Redes es obligatoria?" → {{"nombre_asignatura": "Redes", "atributo_solicitado": "tipo"}}
- "qué es IS2" → {{"nombre_asignatura": "IS2", "atributo_solicitado": "general"}}
- "en qué curso está Cálculo" → {{"nombre_asignatura": "Cálculo", "atributo_solicitado": "curso"}}

RESPONDE SOLO CON JSON:
{{"nombre_asignatura": "...", "atributo_solicitado": "..."}}

JSON:"""

    try:
        salida = llamar_ollama(prompt, timeout=20)

        if not salida:
            raise Exception("LLM no devolvió respuesta")

        # Extraer JSON
        match = re.search(r'\{[^{}]*"nombre_asignatura"[^{}]*\}', salida)
        if match:
            data = json.loads(match.group(0))
            print(f"📝 Extracción específica:")
            print(f"   Asignatura: {data.get('nombre_asignatura')}")
            print(f"   Atributo: {data.get('atributo_solicitado')}\n")
            return data

    except Exception as e:
        print(f"❌ Error extrayendo datos: {e}")
        return {"error": f"No pude extraer información: {e}"}

    return {"error": "No se pudo procesar la consulta"}


def generar_sql_consulta_general(
    pregunta: str,
    contexto_centro: str = "ETSII",
    contexto_titulacion: str = None
) -> Dict[str, Any]:
    """
    Genera SQL para consultas generales sobre asignaturas (con filtros).

    Args:
        pregunta: Pregunta del usuario
        contexto_centro: Centro universitario
        contexto_titulacion: Titulación (opcional)

    Returns:
        Dict con:
        - sql: Query SQL generada
        - tipo_query: "count"|"list"
        - error: str si hubo error
    """

    esquema_tabla = """
    Tabla: asignaturas
    Columnas:
    - codigo (VARCHAR): Código único de asignatura (ej: "2050001")
    - nombre (VARCHAR): Nombre completo
    - curso (INTEGER): Curso 1-4
    - creditos (DECIMAL): Créditos ECTS
    - duracion (VARCHAR): 'A' (Anual), 'C1' (Cuatrimestre 1), 'C2' (Cuatrimestre 2)
    - tipologia (VARCHAR): 'TRONCAL', 'OBLIGATORIA', 'OPTATIVA'
    - es_formacion_basica (BOOLEAN): Si es de formación básica
    - es_optativa (BOOLEAN): Si es optativa
    - activa (BOOLEAN): Si está activa
    - titulacion_id (UUID): FK a titulaciones

    Para filtrar por centro o titulación, hacer JOIN:
    JOIN titulaciones t ON asignaturas.titulacion_id = t.id
    JOIN centros c ON t.centro_id = c.id
    """

    prompt = f"""PREGUNTA: "{pregunta}"

TABLA: asignaturas (nombre, codigo, curso, creditos, duracion, tipologia, activa)

FILTROS:
- curso: 1-4 (primero=1, segundo=2, tercero=3, cuarto=4)
- tipologia: 'OBLIGATORIA', 'OPTATIVA', 'TRONCAL'
- duracion: 'A' (anual), 'C1' (1er cuatri), 'C2' (2do cuatri)
- SIEMPRE: activa=true

TIPO:
- "cuántas/cuántos" → COUNT(*), tipo_query="count"
- "cuáles/lista" → SELECT nombre,codigo,creditos,curso, tipo_query="list"

Responde SOLO este JSON (no ejemplos):
{{"sql":"SELECT...","tipo_query":"count o list"}}
"""

    try:
        salida = llamar_ollama(prompt, timeout=40)

        if not salida:
            raise Exception("LLM no devolvió respuesta")

        print(f"📤 Respuesta LLM completa: {salida}")

        sql = None
        tipo_query = None

        # Intentar parsear JSON directamente
        try:
            data = json.loads(salida)
            if "sql" in data:
                sql = data.get("sql", "").strip()
                tipo_query = data.get("tipo_query", "list").lower()
                print(f"✅ JSON parseado directamente")
            else:
                raise ValueError("No tiene campo 'sql'")
        except:
            # Extraer JSON con regex
            print(f"⚠️  Intentando extraer JSON con regex...")
            match = re.search(r'\{[^{}]*"sql"[^{}]*"tipo_query"[^{}]*\}', salida, re.DOTALL)

            if not match:
                # Intentar solo buscar el SQL y asumir tipo
                match_sql = re.search(r'"sql"\s*:\s*"([^"]+)"', salida)
                if match_sql:
                    sql = match_sql.group(1).strip()
                    tipo_query = "list"
                    print(f"✅ SQL extraído con regex: {sql}")
                else:
                    print(f"❌ No se pudo extraer SQL")
                    return {"error": f"No se encontró JSON válido en respuesta: {salida[:200]}"}
            else:
                json_text = match.group(0)
                print(f"📄 JSON extraído: {json_text}")
                try:
                    data = json.loads(json_text)
                    sql = data.get("sql", "").strip()
                    tipo_query = data.get("tipo_query", "list").lower()
                except json.JSONDecodeError as e:
                    print(f"❌ Error parseando JSON extraído: {e}")
                    return {"error": f"JSON malformado: {json_text}"}

        # Validación de seguridad (se ejecuta SIEMPRE)
        if not sql:
            return {"error": "No se pudo extraer el SQL"}

        sql_upper = sql.upper()
        palabras_prohibidas = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE"]
        if any(p in sql_upper for p in palabras_prohibidas):
            return {"error": "Query rechazada por seguridad"}

        if not sql_upper.startswith("SELECT"):
            return {"error": "Solo se permiten consultas SELECT"}

        print(f"✅ SQL generado:")
        print(f"   {sql}")
        print(f"   Tipo: {tipo_query}\n")

        return {"sql": sql, "tipo_query": tipo_query}

    except Exception as e:
        print(f"❌ Error generando SQL: {e}")
        return {"error": f"Error generando consulta: {e}"}


# =============================================================================
# ACTIONS - TEXT-TO-SQL PARA ASIGNATURAS
# =============================================================================

class ActionConsultarAsignaturaDB(Action):
    """
    Action principal para consultas dinámicas sobre asignaturas usando Text-to-SQL.

    Clasifica automáticamente si la consulta es:
    - ESPECÍFICA: Sobre una asignatura concreta → Busca la asignatura y devuelve info
    - GENERAL: Con filtros múltiples → Genera SQL dinámico

    Ejemplos específicas:
    - "cuántos créditos tiene Redes de Computadores"
    - "qué es IS2"
    - "Redes es obligatoria?"

    Ejemplos generales:
    - "asignaturas de primero"
    - "cuántas optativas hay en cuarto"
    - "asignaturas del segundo cuatrimestre"
    """

    def name(self) -> Text:
        return "action_consultar_asignatura_db"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        # Obtener contexto
        pregunta = tracker.latest_message.get("text", "")
        contexto_centro = tracker.get_slot("contexto_centro") or "ETSII"
        contexto_titulacion = tracker.get_slot("contexto_titulacion")

        if not pregunta:
            dispatcher.utter_message(text="No entendí tu pregunta. ¿Puedes reformularla?")
            return []

        print(f"\n{'='*80}")
        print(f"🎓 CONSULTA ASIGNATURA DB (MEMORIA)")
        print(f"   Pregunta: {pregunta}")
        print(f"   Centro: {contexto_centro}")
        print(f"   Titulación: {contexto_titulacion or 'N/A'}")
        print(f"{'='*80}\n")

        # =====================================================================
        # PASO 1: Cargar asignaturas en memoria (si no están ya cargadas)
        # =====================================================================
        asignaturas_memoria = tracker.get_slot("asignaturas_memoria")

        if not asignaturas_memoria:
            print("🔄 Primera consulta → Cargando TODAS las asignaturas en memoria...")
            asignaturas_memoria = cargar_asignaturas_titulacion(
                contexto_centro, contexto_titulacion
            )

            if not asignaturas_memoria:
                dispatcher.utter_message(text="No pude cargar las asignaturas. ¿Hay un problema con la conexión?")
                return []

            # Guardar en slot para futuras consultas
            slots_set = [SlotSet("asignaturas_memoria", asignaturas_memoria)]
        else:
            print(f"📦 Cache de sesión: {len(asignaturas_memoria)} asignaturas en memoria")
            slots_set = []

        # =====================================================================
        # PASO 2: Análisis UNIFICADO (1 sola llamada LLM o heurística)
        # =====================================================================
        analisis = analizar_consulta_unificado(pregunta)
        tipo_consulta = analisis.get("tipo", "general")

        print(f"📊 ANÁLISIS UNIFICADO: {tipo_consulta.upper()}")
        print(f"   Método: {analisis.get('metodo', 'N/A')}")
        print(f"   Confianza: {analisis.get('confianza', 'N/A')}")
        if analisis.get("nombre_asignatura"):
            print(f"   Asignatura: {analisis.get('nombre_asignatura')}")
            print(f"   Atributo: {analisis.get('atributo_solicitado')}")
        print()

        # =====================================================================
        # PASO 3: Procesar consulta (TODO en memoria, sin SQL)
        # =====================================================================
        if tipo_consulta == "especifica":
            slots_result = self._procesar_consulta_especifica_memoria(
                pregunta, analisis, asignaturas_memoria, dispatcher
            )
        else:
            slots_result = self._procesar_consulta_general_memoria(
                pregunta, analisis, asignaturas_memoria, dispatcher
            )

        return slots_set + slots_result

    def _procesar_consulta_especifica_memoria(
        self,
        pregunta: str,
        analisis: Dict[str, Any],
        asignaturas_memoria: List[Dict[str, Any]],
        dispatcher: CollectingDispatcher
    ) -> List[Dict[Text, Any]]:
        """
        Procesa consulta específica usando SOLO memoria (sin BD, sin LLM para respuesta).

        Args:
            pregunta: Pregunta original
            analisis: Resultado del análisis unificado
            asignaturas_memoria: Asignaturas cargadas en memoria (~50)
            dispatcher: Para enviar respuesta

        Returns:
            Lista de slots a actualizar
        """

        print("→ Procesando ESPECÍFICA en MEMORIA (sin BD, sin LLM)\n")

        # Ya tenemos los datos extraídos del análisis unificado
        nombre_asignatura = analisis.get("nombre_asignatura")
        atributo = analisis.get("atributo_solicitado") or analisis.get("atributo") or "general"

        if not nombre_asignatura:
            dispatcher.utter_message(text="No pude identificar la asignatura. ¿Puedes especificarla?")
            return []

        # Buscar en memoria (fuzzy matching)
        asignatura = buscar_en_memoria(nombre_asignatura, asignaturas_memoria)

        if not asignatura:
            dispatcher.utter_message(
                text=f"No encontré '{nombre_asignatura}' entre las asignaturas disponibles."
            )
            return []

        # Respuesta con template (sin LLM)
        respuesta = respuesta_template(asignatura, atributo)
        print(f"✅ Respuesta instantánea: {respuesta[:80]}...\n")

        dispatcher.utter_message(text=respuesta)

        return [
            SlotSet("ultimo_codigo_consultado", asignatura["codigo"]),
            SlotSet("ultimo_nombre_asignatura", asignatura["nombre"])
        ]

    def _procesar_consulta_general_memoria(
        self,
        pregunta: str,
        analisis: Dict[str, Any],
        asignaturas_memoria: List[Dict[str, Any]],
        dispatcher: CollectingDispatcher
    ) -> List[Dict[Text, Any]]:
        """
        Procesa consulta general usando SOLO memoria (sin BD, sin SQL, sin LLM).

        Ejemplos:
        - "asignaturas de primero"
        - "cuántas optativas hay"
        - "asignaturas del segundo cuatrimestre"

        Args:
            pregunta: Pregunta original
            analisis: Resultado del análisis unificado
            asignaturas_memoria: Asignaturas en memoria
            dispatcher: Para enviar respuesta

        Returns:
            Lista de slots a actualizar
        """

        print("→ Procesando GENERAL en MEMORIA (sin BD, sin SQL, sin LLM)\n")

        # Extraer filtros de la pregunta con heurísticas
        filtros = self._extraer_filtros_heuristicas(pregunta)

        print(f"🔍 Filtros detectados: {filtros}")

        # Aplicar filtros en memoria
        resultados = filtrar_en_memoria(asignaturas_memoria, **filtros)

        # Detectar si pide conteo
        pregunta_lower = pregunta.lower()
        es_count = any(p in pregunta_lower for p in ["cuántas", "cuantas", "cuántos", "cuantos"])

        if es_count:
            count = len(resultados)
            respuesta = respuesta_template_count(count, pregunta)
            print(f"✅ Count instantáneo: {count}\n")
            dispatcher.utter_message(text=respuesta)
            return []

        # Lista de resultados
        if not resultados:
            dispatcher.utter_message(text="No encontré asignaturas que cumplan esos criterios.")
            return []

        if len(resultados) <= 5:
            respuesta = respuesta_template_lista(resultados, pregunta)
            dispatcher.utter_message(text=respuesta)
            return []

        # Muchos resultados: mostrar primeros 5
        respuesta = respuesta_template_lista(resultados[:5], pregunta)
        dispatcher.utter_message(text=respuesta)
        dispatcher.utter_message(
            text=f"Hay {len(resultados) - 5} más. ¿Quieres verlas todas?"
        )

        return [SlotSet("ultimos_resultados_asignaturas", resultados)]

    def _extraer_filtros_heuristicas(self, pregunta: str) -> Dict[str, Any]:
        """
        Extrae filtros de una consulta general usando heurísticas (sin LLM).

        Args:
            pregunta: Pregunta del usuario

        Returns:
            Dict con filtros: {"curso": 1, "tipologia": "OBLIGATORIA", etc.}
        """
        pregunta_lower = pregunta.lower()
        filtros = {}

        # Curso
        if "primero" in pregunta_lower or "primer" in pregunta_lower or "1º" in pregunta_lower:
            filtros["curso"] = 1
        elif "segundo" in pregunta_lower or "2º" in pregunta_lower:
            filtros["curso"] = 2
        elif "tercero" in pregunta_lower or "tercer" in pregunta_lower or "3º" in pregunta_lower:
            filtros["curso"] = 3
        elif "cuarto" in pregunta_lower or "4º" in pregunta_lower:
            filtros["curso"] = 4

        # Tipología
        if "optativa" in pregunta_lower:
            filtros["tipologia"] = "OPTATIVA"
        elif "obligatoria" in pregunta_lower:
            filtros["tipologia"] = "OBLIGATORIA"
        elif "troncal" in pregunta_lower:
            filtros["tipologia"] = "TRONCAL"

        # Duración/Cuatrimestre
        if "primer cuatri" in pregunta_lower or "1er cuatri" in pregunta_lower or "c1" in pregunta_lower:
            filtros["duracion"] = "C1"
        elif "segundo cuatri" in pregunta_lower or "2do cuatri" in pregunta_lower or "c2" in pregunta_lower:
            filtros["duracion"] = "C2"
        elif "anual" in pregunta_lower:
            filtros["duracion"] = "A"

        return filtros

    def _procesar_consulta_especifica_optimizada(
        self,
        pregunta: str,
        analisis: Dict[str, Any],
        contexto_centro: str,
        contexto_titulacion: str,
        dispatcher: CollectingDispatcher
    ) -> List[Dict[Text, Any]]:
        """
        Procesa consultas específicas de forma OPTIMIZADA. (LEGACY - usar _memoria)

        Usa los datos ya extraídos por analizar_consulta_unificado()
        y templates para respuestas (sin llamar al LLM de nuevo).
        """

        print("→ Procesando como CONSULTA ESPECÍFICA (OPTIMIZADA)\n")

        # Ya tenemos los datos extraídos del análisis unificado
        nombre_asignatura = analisis.get("nombre_asignatura")
        atributo = analisis.get("atributo_solicitado") or analisis.get("atributo") or "general"

        if not nombre_asignatura:
            dispatcher.utter_message(text="No pude identificar la asignatura. ¿Puedes especificarla?")
            return []

        # Buscar asignatura en BD
        asignatura = self._buscar_asignatura(nombre_asignatura, contexto_centro, contexto_titulacion)

        if not asignatura:
            dispatcher.utter_message(
                text=f"No encontré la asignatura '{nombre_asignatura}' en {contexto_centro}."
            )
            return []

        # OPTIMIZACIÓN: Usar template en vez de LLM para respuesta
        respuesta = respuesta_template(asignatura, atributo)
        print(f"✅ Respuesta por template (sin LLM): {respuesta[:80]}...")

        dispatcher.utter_message(text=respuesta)

        return [
            SlotSet("ultimo_codigo_consultado", asignatura["codigo"]),
            SlotSet("ultimo_nombre_asignatura", asignatura["nombre"])
        ]

    def _procesar_consulta_especifica(
        self,
        pregunta: str,
        contexto_centro: str,
        contexto_titulacion: str,
        dispatcher: CollectingDispatcher
    ) -> List[Dict[Text, Any]]:
        """Procesa consultas sobre una asignatura específica. (LEGACY)"""

        print("→ Procesando como CONSULTA ESPECÍFICA\n")

        # Extraer nombre y atributo
        datos = extraer_datos_consulta_especifica(pregunta, contexto_centro, contexto_titulacion)

        if "error" in datos:
            dispatcher.utter_message(text=f"No pude entender tu consulta. {datos['error']}")
            return []

        nombre_asignatura = datos.get("nombre_asignatura")
        atributo = datos.get("atributo_solicitado", "general")

        if not nombre_asignatura:
            dispatcher.utter_message(text="No pude identificar la asignatura. ¿Puedes especificarla?")
            return []

        # Buscar asignatura en BD
        asignatura = self._buscar_asignatura(nombre_asignatura, contexto_centro, contexto_titulacion)

        if not asignatura:
            dispatcher.utter_message(
                text=f"No encontré la asignatura '{nombre_asignatura}' en {contexto_centro}."
            )
            return []

        # Formatear respuesta según atributo solicitado
        respuesta = self._formatear_respuesta_especifica(asignatura, atributo, pregunta)
        dispatcher.utter_message(text=respuesta)

        return [
            SlotSet("ultimo_codigo_consultado", asignatura["codigo"]),
            SlotSet("ultimo_nombre_asignatura", asignatura["nombre"])
        ]

    def _procesar_consulta_general(
        self,
        pregunta: str,
        contexto_centro: str,
        contexto_titulacion: str,
        dispatcher: CollectingDispatcher
    ) -> List[Dict[Text, Any]]:
        """Procesa consultas generales con filtros."""

        print("→ Procesando como CONSULTA GENERAL\n")

        # Generar SQL
        resultado_sql = generar_sql_consulta_general(pregunta, contexto_centro, contexto_titulacion)

        if "error" in resultado_sql:
            dispatcher.utter_message(text=f"No pude procesar tu consulta. {resultado_sql['error']}")
            return []

        sql = resultado_sql.get("sql")
        tipo_query = resultado_sql.get("tipo_query", "list")

        print(f"🔍 EJECUTANDO SQL:")
        print(f"   Query: {sql}")
        print(f"   Tipo: {tipo_query}\n")

        # Ejecutar SQL
        resultados = self._ejecutar_sql(sql)

        if resultados is None:
            dispatcher.utter_message(text="Hubo un error al consultar la base de datos.")
            return []

        # Formatear respuesta
        return self._formatear_respuesta_general(resultados, tipo_query, dispatcher, pregunta)

    def _buscar_asignatura(
        self,
        nombre: str,
        centro: str,
        titulacion: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Busca una asignatura por nombre o código usando búsqueda fuzzy + desambiguación con LLM.

        Estrategia:
        1. Buscar por código exacto
        2. Buscar con LIKE
        3. Si hay múltiples coincidencias o ninguna: usar fuzzy matching + LLM
        """

        if db_client is None:
            return None

        conn = db_client.get_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor()

            # 1. Intentar búsqueda por código exacto
            query = """
                SELECT codigo, nombre, curso, creditos, duracion, tipologia
                FROM asignaturas
                WHERE codigo = %s AND activa = true
            """
            cursor.execute(query, (nombre,))
            result = cursor.fetchone()

            if result:
                cursor.close()
                return self._result_to_dict(result)

            # 2. Buscar con LIKE
            query = """
                SELECT codigo, nombre, curso, creditos, duracion, tipologia
                FROM asignaturas
                WHERE LOWER(nombre) LIKE LOWER(%s) AND activa = true
            """

            if titulacion:
                query += " AND titulacion_id = %s"
                cursor.execute(query, (f"%{nombre}%", titulacion))
            else:
                cursor.execute(query, (f"%{nombre}%",))

            resultados = cursor.fetchall()

            # Si hay una sola coincidencia exacta, devolverla
            if len(resultados) == 1:
                cursor.close()
                return self._result_to_dict(resultados[0])

            # 3. Si hay múltiples o ninguna: fuzzy matching + LLM
            # Obtener todas las asignaturas activas
            query = """
                SELECT codigo, nombre, curso, creditos, duracion, tipologia
                FROM asignaturas
                WHERE activa = true
            """

            if titulacion:
                query += " AND titulacion_id = %s"
                cursor.execute(query, (titulacion,))
            else:
                cursor.execute(query)

            todas_asignaturas = cursor.fetchall()
            cursor.close()

            if not todas_asignaturas:
                return None

            # Convertir a diccionarios
            asignaturas_dict = [self._result_to_dict(r) for r in todas_asignaturas]

            # Usar fuzzy matching para encontrar las más similares
            nombres_asignaturas = [a["nombre"] for a in asignaturas_dict]
            codigos_asignaturas = [a["codigo"] for a in asignaturas_dict]

            # Buscar por nombre
            matches_nombre = process.extract(
                nombre,
                nombres_asignaturas,
                scorer=fuzz.WRatio,
                limit=5
            )

            # Buscar por código
            matches_codigo = process.extract(
                nombre,
                codigos_asignaturas,
                scorer=fuzz.ratio,
                limit=5
            )

            # Combinar y obtener las mejores coincidencias
            candidatos = []

            for match, score, idx in matches_nombre:
                if score >= 60:  # Umbral de similitud
                    candidatos.append({
                        "asignatura": asignaturas_dict[idx],
                        "score": score,
                        "tipo_match": "nombre"
                    })

            for match, score, idx in matches_codigo:
                if score >= 70:
                    # Evitar duplicados
                    asig = asignaturas_dict[idx]
                    if not any(c["asignatura"]["codigo"] == asig["codigo"] for c in candidatos):
                        candidatos.append({
                            "asignatura": asig,
                            "score": score,
                            "tipo_match": "codigo"
                        })

            # Ordenar por score
            candidatos.sort(key=lambda x: x["score"], reverse=True)

            if not candidatos:
                print(f"⚠️ No se encontraron coincidencias fuzzy para '{nombre}'")
                return None

            # Si hay solo un candidato con buen score, devolverlo
            if len(candidatos) == 1 or candidatos[0]["score"] > 90:
                print(f"✅ Coincidencia fuzzy: {candidatos[0]['asignatura']['nombre']} (score: {candidatos[0]['score']})")
                return candidatos[0]["asignatura"]

            # Si hay múltiples candidatos: usar LLM para desambiguar
            print(f"🤔 Múltiples coincidencias encontradas, usando LLM para desambiguar...")
            mejor_match = self._desambiguar_con_llm(nombre, candidatos[:3])  # Top 3

            return mejor_match

        except Exception as e:
            print(f"❌ Error buscando asignatura: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def _result_to_dict(self, result: tuple) -> Dict[str, Any]:
        """Convierte un resultado de BD a diccionario."""
        return {
            "codigo": result[0],
            "nombre": result[1],
            "curso": result[2],
            "creditos": result[3],
            "duracion": result[4],
            "tipologia": result[5]
        }

    def _desambiguar_con_llm(
        self,
        nombre_buscado: str,
        candidatos: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Usa el LLM para elegir la asignatura correcta entre múltiples candidatos.

        Args:
            nombre_buscado: Nombre/código que el usuario buscó
            candidatos: Lista de candidatos con sus scores

        Returns:
            La asignatura elegida o None
        """

        # Preparar lista de opciones
        opciones = []
        for i, cand in enumerate(candidatos, 1):
            asig = cand["asignatura"]
            opciones.append(
                f"{i}. {asig['nombre']} ({asig['codigo']}) - {asig['curso']}º curso"
            )

        opciones_texto = "\n".join(opciones)

        prompt = f"""Usuario buscó: "{nombre_buscado}"

Opciones:
{opciones_texto}

Responde SOLO con UN NÚMERO del 1 al {len(candidatos)} (o 0 si ninguna coincide).

Respuesta:"""

        try:
            salida = llamar_ollama(prompt, timeout=15)

            if not salida:
                raise Exception("LLM no devolvió respuesta")

            # Limpiar respuesta y buscar el primer dígito
            salida_limpia = salida.strip()

            # Buscar cualquier dígito en la respuesta
            match = re.search(r'(\d+)', salida_limpia)
            if match:
                num = int(match.group(1))

                print(f"🔍 LLM devolvió: '{salida_limpia}' → número: {num}")

                if num > 0 and num <= len(candidatos):
                    asignatura_elegida = candidatos[num - 1]["asignatura"]
                    print(f"✅ LLM eligió: {asignatura_elegida['nombre']}")
                    return asignatura_elegida
                elif num == 0:
                    print(f"⚠️ LLM indicó que ninguna coincide (0)")
                    return None

        except Exception as e:
            print(f"❌ Error en desambiguación LLM: {e}")

        # Fallback: devolver el mejor score
        print(f"⚠️ LLM no pudo desambiguar, usando mejor score")
        return candidatos[0]["asignatura"]

    def _ejecutar_sql(self, sql: str) -> Optional[List[Dict[str, Any]]]:
        """Ejecuta una query SQL y devuelve resultados."""

        if db_client is None:
            return None

        conn = db_client.get_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor()
            cursor.execute(sql)

            columnas = [desc[0] for desc in cursor.description] if cursor.description else []
            filas = cursor.fetchall()

            resultados = [dict(zip(columnas, fila)) for fila in filas]

            cursor.close()
            print(f"✅ Query ejecutada: {len(resultados)} resultados\n")

            return resultados

        except Exception as e:
            print(f"❌ Error ejecutando SQL: {e}")
            return None
        finally:
            conn.close()

    def _formatear_respuesta_especifica(
        self,
        asignatura: Dict[str, Any],
        atributo: str,
        pregunta_original: str = ""
    ) -> str:
        """
        Formatea la respuesta para una consulta específica usando LLM para naturalidad.
        """

        # Preparar datos según el atributo solicitado
        if atributo == "creditos":
            datos_respuesta = {
                "nombre": asignatura["nombre"],
                "creditos": asignatura["creditos"]
            }
        elif atributo == "tipo":
            datos_respuesta = {
                "nombre": asignatura["nombre"],
                "tipologia": asignatura["tipologia"]
            }
        elif atributo == "curso":
            datos_respuesta = {
                "nombre": asignatura["nombre"],
                "curso": asignatura["curso"]
            }
        elif atributo == "cuatrimestre" or atributo == "duracion":
            datos_respuesta = {
                "nombre": asignatura["nombre"],
                "duracion": asignatura["duracion"]
            }
        elif atributo == "duracion":
            datos_respuesta = {
                "nombre": asignatura["nombre"],
                "duracion": asignatura["duracion"]
            }
        else:  # general
            datos_respuesta = asignatura

        # Generar respuesta natural con LLM
        return generar_respuesta_natural(
            pregunta_usuario=pregunta_original,
            datos=datos_respuesta,
            tipo_respuesta="especifica"
        )

    def _formatear_respuesta_general(
        self,
        resultados: List[Dict[str, Any]],
        tipo_query: str,
        dispatcher: CollectingDispatcher,
        pregunta_original: str = ""
    ) -> List[Dict[Text, Any]]:
        """
        Formatea la respuesta para una consulta general.

        OPTIMIZACIÓN: Usa templates por defecto, LLM solo si es necesario.
        """

        # COUNT query - SIEMPRE usar template (rápido)
        if tipo_query == "count":
            if resultados and "count" in resultados[0]:
                count = resultados[0]["count"]
            else:
                count = len(resultados)

            # Template rápido (sin LLM)
            respuesta = respuesta_template_count(count, pregunta_original)
            print(f"✅ Count por template: {respuesta}")
            dispatcher.utter_message(text=respuesta)
            return []

        # Sin resultados
        if not resultados:
            dispatcher.utter_message(text="No encontré asignaturas que cumplan los criterios.")
            return []

        # Lista de resultados - usar template (rápido)
        if len(resultados) <= 5:
            respuesta = respuesta_template_lista(resultados, pregunta_original)
            print(f"✅ Lista por template (sin LLM)")
            dispatcher.utter_message(text=respuesta)
            return []

        # Muchos resultados: mostrar primeros 5
        respuesta = respuesta_template_lista(resultados[:5], pregunta_original)
        print(f"✅ Lista parcial por template (sin LLM)")
        dispatcher.utter_message(text=respuesta)
        dispatcher.utter_message(
            text=f"Hay {len(resultados) - 5} más. ¿Quieres verlas todas?"
        )

        return [SlotSet("ultimos_resultados_asignaturas", resultados)]

    def _formatear_lista_asignaturas(
        self,
        asignaturas: List[Dict[str, Any]],
        total: int = None
    ) -> str:
        """Formatea una lista de asignaturas."""

        lineas = []

        if total and total > len(asignaturas):
            lineas.append(f"📋 Mostrando {len(asignaturas)} de {total} asignaturas:\n")
        else:
            lineas.append(f"📋 Asignaturas encontradas ({len(asignaturas)}):\n")

        for i, asig in enumerate(asignaturas, 1):
            nombre = asig.get("nombre", "Sin nombre")
            codigo = asig.get("codigo", "")
            creditos = asig.get("creditos", "")
            curso = asig.get("curso", "")

            linea = f"{i}. **{nombre}**"

            detalles = []
            if codigo:
                detalles.append(codigo)
            if curso:
                detalles.append(f"{curso}º")
            if creditos:
                detalles.append(f"{creditos} ECTS")

            if detalles:
                linea += f" ({', '.join(map(str, detalles))})"

            lineas.append(linea)

        return "\n".join(lineas)


# =============================================================================
# ACTIONS - MOSTRAR TODOS LOS RESULTADOS
# =============================================================================

class ActionMostrarTodasAsignaturas(Action):
    """Muestra todos los resultados guardados de una consulta general previa."""

    def name(self) -> Text:
        return "action_mostrar_todas_asignaturas"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        resultados = tracker.get_slot("ultimos_resultados_asignaturas")

        if not resultados:
            dispatcher.utter_message(text="No hay resultados previos para mostrar.")
            return []

        # Formatear todos los resultados
        lineas = [f"📋 Todas las asignaturas ({len(resultados)}):\n"]

        for i, asig in enumerate(resultados, 1):
            nombre = asig.get("nombre", "Sin nombre")
            codigo = asig.get("codigo", "")
            creditos = asig.get("creditos", "")

            linea = f"{i}. **{nombre}**"
            if codigo:
                linea += f" ({codigo})"
            if creditos:
                linea += f" - {creditos} ECTS"

            lineas.append(linea)

        dispatcher.utter_message(text="\n".join(lineas))

        return [SlotSet("ultimos_resultados_asignaturas", None)]


# =============================================================================
# ACTIONS LEGACY (mantener compatibilidad)
# =============================================================================

class ActionConsultarAsignatura(Action):
    """Action legacy - redirige a ActionConsultarAsignaturaDB"""

    def name(self) -> Text:
        return "action_consultar_asignatura"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        # Delegar a la nueva action
        action_db = ActionConsultarAsignaturaDB()
        return action_db.run(dispatcher, tracker, domain)


class ActionPreguntaSeguimiento(Action):
    """Action legacy - mantener para compatibilidad"""

    def name(self) -> Text:
        return "action_pregunta_seguimiento"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        # Delegar a ActionConsultarAsignaturaDB que maneja todo
        action_db = ActionConsultarAsignaturaDB()
        return action_db.run(dispatcher, tracker, domain)


class ActionConsultarAsignaturasFiltradas(Action):
    """Action legacy - redirige a ActionConsultarAsignaturaDB"""

    def name(self) -> Text:
        return "action_consultar_asignaturas_filtradas"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        # Delegar a la nueva action
        action_db = ActionConsultarAsignaturaDB()
        return action_db.run(dispatcher, tracker, domain)


class ActionMostrarTodas(Action):
    """Action legacy - redirige a ActionMostrarTodasAsignaturas"""

    def name(self) -> Text:
        return "action_mostrar_todas"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        # Delegar a la nueva action
        action = ActionMostrarTodasAsignaturas()
        return action.run(dispatcher, tracker, domain)
