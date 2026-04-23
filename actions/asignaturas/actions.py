"""
Actions de Rasa para consultas de asignaturas.
Arquitectura con 3 intents separados + Text-to-SQL dinámico.
"""

from typing import Any, Text, Dict, List, Optional, Tuple
import json
import re
import unicodedata
from ..shared.gemini_client import llamar_gemini

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from .text_to_sql import (
    generar_sql_listado,
    generar_sql_conteo,
    ejecutar_query,
    ejecutar_count,
    generar_respuesta_natural,
    _expandir_alias,
)

from ..shared.config import BotConfig, ALIAS_ASIGNATURAS
from ..shared.db import db_client


# ============================================================================
# UTILIDADES
# ============================================================================

def _detectar_grupo(texto: str) -> Optional[str]:
    """
    Detecta si el usuario menciona un grupo específico en su mensaje.
    Devuelve el grupo en formato BD (ej. 'Grupo 1') o None.

    Patrones reconocidos: 'grupo 1', 'grupo 2', 'g1', 'g2',
    'del grupo 3', 'en el grupo 1', etc.
    """
    if not texto:
        return None
    texto_lower = texto.lower()
    # Patrón explícito: "grupo X"
    match = re.search(r'\bgrupo\s+(\d+)\b', texto_lower)
    if match:
        return f"Grupo {match.group(1)}"
    # Patrón abreviado: "g1", "g2", "g3" (solo si no forma parte de otra palabra)
    match = re.search(r'\bg(\d+)\b', texto_lower)
    if match:
        return f"Grupo {match.group(1)}"
    return None


def normalizar_texto(texto: str) -> str:
    """Normaliza texto para búsqueda (sin tildes, minúsculas, sin espacios extra)."""
    if not texto:
        return ""
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    texto = texto.lower().strip()
    texto = re.sub(r'\s+', ' ', texto)
    return texto


def obtener_historial_reciente(tracker, max_turnos: int = 2) -> str:
    """
    Extrae los últimos turnos de conversación del tracker de Rasa.
    Devuelve un string con formato "Usuario: ... / Bot: ..." para dar contexto al LLM.
    Solo incluye turnos de usuario y respuestas del bot (no eventos internos).
    """
    eventos = tracker.events
    turnos = []
    turno_actual = {}

    for evento in eventos:
        if evento.get("event") == "user":
            if turno_actual.get("user"):
                turnos.append(turno_actual)
            turno_actual = {"user": evento.get("text", ""), "bot": ""}
        elif evento.get("event") == "bot" and turno_actual.get("user"):
            if not turno_actual.get("bot"):
                turno_actual["bot"] = evento.get("text", "")

    # No incluir el turno actual (ya es la pregunta que estamos procesando)
    # Los turnos relevantes son los anteriores al último
    turnos_previos = turnos[-max_turnos:] if turnos else []

    if not turnos_previos:
        return ""

    lineas = []
    for t in turnos_previos:
        lineas.append(f"Usuario: {t['user']}")
        if t['bot']:
            # Truncar respuestas largas del bot para no saturar el prompt
            bot_text = t['bot'][:200] + "..." if len(t['bot']) > 200 else t['bot']
            lineas.append(f"Bot: {bot_text}")
    return "\n".join(lineas)


def _contar_turnos_desde_slot(tracker, slot_name: str) -> int:
    """
    Cuenta turnos de usuario desde la última vez que se seteó el slot.
    Usado para determinar si el slot es reciente (seguimiento) o stale.
    """
    turnos = 0
    for event in reversed(tracker.events):
        if event.get("event") == "user":
            turnos += 1
        if event.get("event") == "slot" and event.get("name") == slot_name:
            return turnos
    return 999


def _cargar_titulaciones_desde_bd() -> List[Dict]:
    """
    Obtiene todas las titulaciones activas de la BD.
    Devuelve lista de dicts con 'codigo' y 'nombre'.
    Devuelve lista vacía si hay error de conexión.
    """
    try:
        conn = db_client.get_connection()
        if not conn:
            return []
        cursor = conn.cursor()
        cursor.execute(
            "SELECT codigo, nombre FROM titulaciones WHERE activa = true ORDER BY nombre"
        )
        filas = cursor.fetchall()
        cursor.close()
        conn.close()
        return [{"codigo": f[0], "nombre": f[1]} for f in filas]
    except Exception as e:
        print(f"Error cargando titulaciones: {e}")
        return []


def _construir_botones_titulaciones() -> List[Dict[str, str]]:
    """Construye botones de titulaciones disponibles para Rasa."""
    titulaciones = _cargar_titulaciones_desde_bd()
    if titulaciones:
        return [
            {"title": f"{t['nombre']} ({t['codigo']})", "payload": t['codigo']}
            for t in titulaciones
        ]
    # Fallback si la BD no está disponible
    return [
        {"title": "Ingeniería del Software (GII-IS)", "payload": "GII-IS"},
        {"title": "Tecnologías Informáticas (GII-TI)", "payload": "GII-TI"},
        {"title": "Ingeniería de Computadores (GII-IC)", "payload": "GII-IC"},
    ]


def comprobar_titulacion(
    tracker, dispatcher
) -> Tuple[Optional[str], List]:
    """
    Comprueba si el usuario ya eligió titulación.
    Si no, pide que la elija con botones.

    Devuelve (codigo_titulacion, eventos_rasa).
    """
    titulacion = tracker.get_slot("contexto_titulacion")

    if not titulacion:
        botones = _construir_botones_titulaciones()
        dispatcher.utter_message(
            text="Antes de consultar asignaturas, necesito saber tu titulación:",
            buttons=botones
        )
        return None, []

    return titulacion, []


def _extraer_multiples_nombres(pregunta: str, titulacion: str) -> List[str]:
    """
    Detecta si la pregunta contiene múltiples asignaturas separadas por 'y', ',' o 'e'.
    Busca aliases conocidos y devuelve lista de nombres expandidos.
    Ej: "cómo se evalúa dp1 y psg2" → ["diseno y pruebas i", "proceso software y gestion ii"]
    Devuelve lista vacía si no detecta múltiples.
    """
    pregunta_lower = pregunta.lower()

    # Buscar todos los aliases que aparecen en la pregunta
    encontrados = []
    aliases_ordenados = sorted(ALIAS_ASIGNATURAS.keys(), key=len, reverse=True)
    texto_restante = pregunta_lower

    for alias in aliases_ordenados:
        pattern = r'\b' + re.escape(alias) + r'\b'
        if re.search(pattern, texto_restante):
            expandido = _expandir_alias(alias, titulacion)
            encontrados.append(expandido)
            # Quitar del texto para no matchear substrings
            texto_restante = re.sub(pattern, '', texto_restante, count=1)

    if len(encontrados) >= 2:
        print(f"   → Multi-asignatura detectada: {encontrados}")
        return encontrados
    return []


def extraer_nombre_asignatura(tracker, titulacion_detectada_en_mensaje: bool = False) -> Optional[str]:
    """Extrae el nombre de asignatura del mensaje actual.
    Si se detectó titulación inline, valida que la entidad no sea parte del nombre de la titulación.
    Si hay varias entidades nombre_asignatura, filtra ruido y devuelve la más relevante."""
    # Palabras genéricas que el NLU puede extraer como entidad pero no son asignaturas
    PALABRAS_RUIDO = {
        'info', 'información', 'informacion', 'datos', 'dame', 'dime',
        'hablame', 'háblame', 'sobre', 'del', 'de', 'la', 'el',
    }

    candidatas = []
    for entity in tracker.latest_message.get('entities', []):
        if entity.get('entity') == 'nombre_asignatura':
            valor = entity.get('value', '')
            if not valor:
                continue
            if titulacion_detectada_en_mensaje:
                valor_lower = normalizar_texto(valor)
                fragmentos_titulacion = [
                    'software', 'computador', 'telematic', 'informatica',
                    'ingenieria', 'grado', 'tecnolog'
                ]
                if len(valor_lower) < 4 or any(f in valor_lower for f in fragmentos_titulacion):
                    print(f"   ⚠ Entidad NLU descartada (parece titulación): '{valor}'")
                    continue
            # Filtrar palabras genéricas que no son nombres de asignaturas
            if valor.lower().strip() in PALABRAS_RUIDO:
                print(f"   ⚠ Entidad NLU descartada (ruido): '{valor}'")
                continue
            candidatas.append(valor)

    if not candidatas:
        return None

    # Limpiar palabras ruido del inicio/final de cada candidata
    # (ej. "Fundamentos de Programacion del" → "Fundamentos de Programacion")
    SUFIJOS_RUIDO = {'del', 'de', 'la', 'el', 'las', 'los', 'y', 'e'}
    candidatas_limpias = []
    for c in candidatas:
        palabras = c.split()
        while palabras and palabras[-1].lower() in SUFIJOS_RUIDO:
            palabras.pop()
        while palabras and palabras[0].lower() in SUFIJOS_RUIDO:
            palabras.pop(0)
        limpia = ' '.join(palabras)
        if limpia:
            candidatas_limpias.append(limpia)
    candidatas = candidatas_limpias if candidatas_limpias else candidatas

    if len(candidatas) == 1:
        return candidatas[0]
    # Si hay varias, devolver la más larga (más específica)
    mejor = max(candidatas, key=len)
    print(f"   → Múltiples entidades NLU: {candidatas} → eligiendo '{mejor}'")
    return mejor


# ============================================================================
# RAG: BÚSQUEDA EN PLANES DOCENTES
# ============================================================================

def _resolver_nombre_desde_texto(pregunta: str, titulacion: str) -> Optional[str]:
    """
    Intenta encontrar una asignatura en la BD a partir del texto libre del usuario.
    Usa fuzzy matching contra nombres reales de la BD.
    Estrategia: prueba ventanas de N palabras contiguas de la pregunta (de mayor a menor)
    para aislar el fragmento que más se parece a un nombre de asignatura real.
    Devuelve el nombre real de la asignatura o None.
    """
    from rapidfuzz import fuzz, process

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

    if not nombres_bd:
        return None

    nombres_norm = [normalizar_texto(n) for n in nombres_bd]

    # Estrategia 1: pregunta completa con partial_ratio
    pregunta_norm = normalizar_texto(pregunta)
    resultado = process.extractOne(
        pregunta_norm, nombres_norm,
        scorer=fuzz.partial_ratio,
        score_cutoff=85,
    )
    if resultado:
        return nombres_bd[resultado[2]]

    # Estrategia 2: ventanas de palabras contiguas (3 a 6 palabras)
    # Esto aísla fragmentos como "ing de requisitos" del ruido circundante
    palabras = pregunta_norm.split()
    mejor_score = 0
    mejor_idx = None
    for window_size in range(min(6, len(palabras)), 1, -1):
        for i in range(len(palabras) - window_size + 1):
            fragmento = ' '.join(palabras[i:i + window_size])
            res = process.extractOne(
                fragmento, nombres_norm,
                scorer=fuzz.partial_ratio,
                score_cutoff=75,
            )
            if res and res[1] > mejor_score:
                mejor_score = res[1]
                mejor_idx = res[2]
    if mejor_idx is not None:
        print(f"   → Fuzzy ventana: score={mejor_score} → '{nombres_bd[mejor_idx]}'")
        return nombres_bd[mejor_idx]

    return None


def _sugerencias_asignatura(texto: str, titulacion: str, n: int = 3) -> list[str]:
    """Devuelve hasta n nombres de asignaturas más parecidas al texto, sin threshold mínimo."""
    from rapidfuzz import fuzz, process

    conn = db_client.get_connection()
    if not conn:
        return []
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

    if not nombres_bd:
        return []

    nombres_norm = [normalizar_texto(n) for n in nombres_bd]
    texto_norm = normalizar_texto(texto)
    resultados = process.extract(texto_norm, nombres_norm, scorer=fuzz.token_set_ratio, limit=n)
    return [nombres_bd[r[2]] for r in resultados]


def resolver_asignatura(
    pregunta: str,
    tracker,
    contexto_titulacion: str,
    usar_seguimiento: bool = True,
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Resuelve una asignatura a partir de la pregunta del usuario.
    Pipeline completo compartido por todos los actions de asignaturas:
      NLU entity → seguimiento → alias → fuzzy BD → SQL flexible → fallbacks.

    Args:
        pregunta: Texto de la pregunta del usuario.
        tracker: Tracker de Rasa (para NLU entities y slots).
        contexto_titulacion: Código de la titulación activa.
        usar_seguimiento: Si True, intenta usar contexto previo para seguimiento.

    Returns:
        (asignatura_dict, nombre_usado):
          - asignatura_dict: dict con codigo, nombre, curso, creditos, etc. o None.
          - nombre_usado: nombre candidato que se intentó resolver (para mensajes de error).
    """
    from .text_to_sql import (
        ALIAS_ASIGNATURAS, _inyectar_filtro_titulacion, ejecutar_query,
    )

    # 1. Extraer nombre de NLU entities
    titulacion_inline = bool(tracker.get_slot("contexto_titulacion") != contexto_titulacion
                             if tracker.get_slot("contexto_titulacion") else False)
    nombre_asignatura = extraer_nombre_asignatura(tracker, titulacion_inline)

    # 2. Expandir alias/acrónimos
    if nombre_asignatura:
        nombre_expandido = _expandir_alias(nombre_asignatura, contexto_titulacion)
        if nombre_expandido != nombre_asignatura:
            print(f"   → Alias expandido: '{nombre_asignatura}' → '{nombre_expandido}'")
            nombre_asignatura = nombre_expandido

    # 3. Sin entidad NLU: buscar alias en el texto de la pregunta
    if not nombre_asignatura:
        pregunta_lower = pregunta.lower()
        for alias in sorted(ALIAS_ASIGNATURAS, key=len, reverse=True):
            if re.search(r'\b' + re.escape(alias) + r'\b', pregunta_lower):
                nombre_asignatura = _expandir_alias(alias, contexto_titulacion)
                print(f"   → Alias detectado en pregunta: '{alias}' → '{nombre_asignatura}'")
                break

    # 4. Heurística de seguimiento: si no se encontró nada Y hay asignatura reciente → follow-up
    #    Esto va ANTES del fuzzy matching para evitar que el fuzzy coja una asignatura incorrecta
    if usar_seguimiento and not nombre_asignatura:
        ultimo_nombre = tracker.get_slot("ultimo_nombre_asignatura")
        if ultimo_nombre:
            turnos = _contar_turnos_desde_slot(tracker, "ultimo_nombre_asignatura")
            if turnos <= 3:
                nombre_asignatura = ultimo_nombre
                print(f"   → Seguimiento heurístico: '{ultimo_nombre}' ({turnos} turnos atrás)")

    # 5. Fuzzy matching contra nombres reales en BD
    if not nombre_asignatura:
        nombre_asignatura = _resolver_nombre_desde_texto(pregunta, contexto_titulacion)
        if nombre_asignatura:
            print(f"   → Nombre resuelto por fuzzy BD: {nombre_asignatura}")

    if not nombre_asignatura:
        print(f"   → Sin nombre candidato para resolver")
        return None, None

    # 6. Buscar en BD con ILIKE flexible
    nombre_norm = f"%{normalizar_texto(nombre_asignatura)}%"
    sql = """SELECT codigo, nombre, curso, creditos, duracion, tipologia,
                    es_formacion_basica, es_optativa
             FROM asignaturas
             WHERE activa = true AND (nombre_normalizado ILIKE %s OR codigo ILIKE %s)"""
    sql = _inyectar_filtro_titulacion(sql, contexto_titulacion)
    exito, resultados = ejecutar_query(sql, [nombre_norm, nombre_norm])

    # 7. Fallback: fuzzy matching si ILIKE no dio resultados
    if not exito or not resultados:
        nombre_fuzzy = _resolver_nombre_desde_texto(nombre_asignatura, contexto_titulacion)
        if nombre_fuzzy:
            print(f"   → Fallback fuzzy: '{nombre_asignatura}' → '{nombre_fuzzy}'")
            nombre_fuzzy_norm = f"%{normalizar_texto(nombre_fuzzy)}%"
            sql_fuzzy = """SELECT codigo, nombre, curso, creditos, duracion, tipologia,
                                  es_formacion_basica, es_optativa
                           FROM asignaturas
                           WHERE activa = true AND nombre_normalizado ILIKE %s"""
            sql_fuzzy = _inyectar_filtro_titulacion(sql_fuzzy, contexto_titulacion)
            exito, resultados = ejecutar_query(sql_fuzzy, [nombre_fuzzy_norm])
            if exito and resultados:
                nombre_asignatura = nombre_fuzzy

    if not exito or not resultados:
        return None, nombre_asignatura

    # 8. Si hay múltiples resultados, reordenar por fuzzy match
    if len(resultados) > 1:
        from rapidfuzz import fuzz
        pregunta_norm = normalizar_texto(pregunta)
        resultados.sort(
            key=lambda r: fuzz.token_set_ratio(
                normalizar_texto(r.get('nombre', '')), pregunta_norm
            ),
            reverse=True
        )
        print(f"   → Reordenado por fuzzy: mejor match = '{resultados[0].get('nombre')}'")

    return resultados[0], nombre_asignatura


def _generar_respuesta_rag(
    pregunta: str, chunks: list, nombre_asignatura: str
) -> Optional[str]:
    """Genera respuesta natural a partir de chunks del plan docente."""
    if not chunks:
        return None

    def _chunk_header(c):
        label = c.get('_asignatura_label') or c.get('asignatura_nombre', '')
        seccion = c.get('seccion', 'general')
        return f"[{seccion}] ({label})" if label else f"[{seccion}]"

    contexto = "\n\n---\n\n".join(
        f"{_chunk_header(c)}\n{c['contenido']}\nMetadatos: {c.get('metadata', {})}"
        for c in chunks
    )

    prompt = f"""Eres Linceus, un asistente universitario de la ETSII (Universidad de Sevilla).
Responde a la pregunta del usuario usando SOLO la información del plan docente proporcionada.

PREGUNTA DEL USUARIO: "{pregunta}"
ASIGNATURA: {nombre_asignatura}

INFORMACIÓN DEL PLAN DOCENTE:
{contexto}

REGLAS:
- Responde de forma natural, cercana y concisa
- Usa solo la información proporcionada, no inventes datos
- Puedes usar markdown para formatear (negritas, listas)
- No menciones que consultaste un "plan docente" ni "chunks"
- No saludes (nada de "¡Hola!", "Hola!", "Buenos días", etc.) — ve directo a la respuesta
- Si la información no es suficiente para responder, dilo amablemente
- IMPORTANTE: Cada fragmento tiene una etiqueta de sección entre corchetes (ej. [profesorado], [bibliografia]).
  Los nombres en secciones [bibliografia] son AUTORES DE LIBROS, NO profesores de la asignatura.
  Solo menciona como profesores a personas de secciones [profesorado] o [coordinador].
- IMPORTANTE: Tu respuesta debe tener como MÁXIMO 1500 caracteres. Si hay mucha información, resume lo más relevante

Respuesta:"""

    respuesta = llamar_gemini(
        prompt,
        timeout=30,
        options={"temperature": 0.3, "num_predict": 800},
    )
    return respuesta.strip() if respuesta else None


# ============================================================================
# HELPER: RESPUESTA DE HORARIO DE ASIGNATURA
# ============================================================================
# La detección de intent vive en el NLU (intent `consulta_horario_asignatura`);
# este helper solo formula la respuesta a partir de una asignatura ya resuelta
# y un grupo opcional. Lo usan `ActionConsultaHorarioAsignatura` y
# potencialmente futuros Actions que necesiten formatear un horario puntual.


def _responder_horario_asignatura(
    pregunta: str, asignatura: dict, titulacion: str,
    grupo: Optional[str] = None,
) -> Optional[str]:
    """
    Consulta la tabla horarios para una asignatura y genera respuesta con LLM.
    Retorna la respuesta o None si no hay datos.
    """
    from ..horarios.actions import (
        _query_asignatura as query_horario_asig,
        _query_grupos_de_asignatura,
        _datos_asignatura_a_texto,
        _generar_respuesta_horario,
        ALIAS_ASIGNATURAS,
    )

    nombre = asignatura.get('nombre', '')
    nombre_norm = normalizar_texto(nombre)

    # Buscar alias que corresponda a esta asignatura
    alias_encontrado = None
    for alias, nombre_map in ALIAS_ASIGNATURAS.items():
        if nombre_map in nombre_norm or nombre_norm in nombre_map:
            alias_encontrado = alias
            break

    # Convertir grupo de "Grupo 1" a int si viene como string
    grupo_int = None
    if grupo:
        import re as _re
        m = _re.search(r'(\d+)', str(grupo))
        if m:
            grupo_int = int(m.group(1))

    if alias_encontrado:
        resultados = query_horario_asig(titulacion, alias_encontrado, grupo_int)
        if not resultados and grupo_int:
            # ¿Existe la asignatura pero no ese grupo?
            nombre_real, grupos = _query_grupos_de_asignatura(titulacion, alias_encontrado)
            if nombre_real and grupos and str(grupo_int) not in grupos:
                from ..shared.config import BotConfig
                nombre_tit = BotConfig.get_nombre_titulacion(titulacion)
                lista_grupos = ", ".join(grupos)
                return (f"**{nombre_real}** en {nombre_tit} no tiene grupo {grupo_int}. "
                        f"Grupos disponibles: {lista_grupos}.")
        datos_texto = _datos_asignatura_a_texto(resultados, alias_encontrado, titulacion)
    else:
        # Fallback: buscar directamente por nombre en la tabla horarios
        from ..shared.db import db_client
        conn = db_client.get_connection()
        if not conn:
            return None
        try:
            cur = conn.cursor()
            sql = """
                SELECT h.dia_semana, h.hora_inicio, h.hora_fin,
                       a.nombre, COALESCE(au.codigo, '') AS aula,
                       gc.codigo AS grupo, a.curso
                FROM horarios h
                JOIN grupos_clase gc ON h.grupo_id = gc.id
                JOIN asignaturas a ON gc.asignatura_id = a.id
                JOIN titulaciones t ON a.titulacion_id = t.id
                LEFT JOIN aulas au ON h.aula_id = au.id
                WHERE t.codigo = %s
                  AND a.nombre_normalizado ILIKE %s
                  AND h.activo = true
            """
            params = [titulacion, f"%{nombre_norm}%"]
            if grupo_int:
                sql += " AND gc.codigo = %s"
                params.append(str(grupo_int))
            sql += " ORDER BY gc.codigo, h.dia_semana, h.hora_inicio"
            cur.execute(sql, params)
            resultados = cur.fetchall()

            # Si hay filtro de grupo y vacio, consultar grupos disponibles
            grupos_disponibles: list = []
            if not resultados and grupo_int:
                cur.execute("""
                    SELECT DISTINCT gc.codigo
                    FROM grupos_clase gc
                    JOIN asignaturas a ON gc.asignatura_id = a.id
                    JOIN titulaciones t ON a.titulacion_id = t.id
                    WHERE t.codigo = %s AND a.nombre_normalizado ILIKE %s
                      AND gc.activo = true
                    ORDER BY gc.codigo
                """, (titulacion, f"%{nombre_norm}%"))
                grupos_disponibles = [r[0] for r in cur.fetchall()]
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error buscando horario por nombre: {e}")
            if conn:
                conn.close()
            return None
        if not resultados and grupo_int and grupos_disponibles:
            from ..shared.config import BotConfig
            nombre_tit = BotConfig.get_nombre_titulacion(titulacion)
            lista_grupos = ", ".join(grupos_disponibles)
            return (f"**{nombre}** en {nombre_tit} no tiene grupo {grupo_int}. "
                    f"Grupos disponibles: {lista_grupos}.")
        datos_texto = _datos_asignatura_a_texto(resultados, nombre, titulacion)

    if not resultados:
        return None

    return _generar_respuesta_horario(pregunta, datos_texto)


# ============================================================================
# ACTION: CONSULTA ESPECÍFICA
# ============================================================================

class ActionConsultaEspecifica(Action):
    """
    Maneja consultas sobre una o varias asignaturas.

    Ejemplos:
    - "¿Cuántos créditos tiene Redes?"
    - "¿Qué es IS2?"
    - "¿Cómo se evalúa DP1 y PSG2?"
    """

    def name(self) -> Text:
        return "action_consulta_especifica"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        pregunta = tracker.latest_message.get("text", "")
        historial = obtener_historial_reciente(tracker)
        contexto_titulacion, eventos_contexto = comprobar_titulacion(tracker, dispatcher)
        if not contexto_titulacion:
            return []

        print(f"\n{'='*60}")
        print(f"🔍 CONSULTA ESPECÍFICA: {pregunta}")
        print(f"   Contexto: {contexto_titulacion}")
        print(f"   Última asignatura: {tracker.get_slot('ultimo_nombre_asignatura')} ({tracker.get_slot('ultimo_codigo_consultado')})")
        print(f"{'='*60}")

        # ── Multi-asignatura: detectar si hay varias en la pregunta ──
        nombres_multi = _extraer_multiples_nombres(pregunta, contexto_titulacion)
        if len(nombres_multi) >= 2:
            return self._run_multi(
                nombres_multi, pregunta, historial,
                contexto_titulacion, eventos_contexto,
                tracker, dispatcher,
            )

        # Resolver asignatura con pipeline compartido
        asignatura, nombre_asignatura = resolver_asignatura(
            pregunta, tracker, contexto_titulacion
        )

        if not asignatura:
            if nombre_asignatura:
                nombre_titulacion = BotConfig.get_nombre_titulacion(contexto_titulacion)
                print(f"   ❌ Asignatura no encontrada: {nombre_asignatura}")
                sugerencias = _sugerencias_asignatura(nombre_asignatura, contexto_titulacion)
                if sugerencias:
                    lista = "\n".join(f"- {s}" for s in sugerencias)
                    msg = (
                        f"No encontré ninguna asignatura llamada '{nombre_asignatura}' en {nombre_titulacion}. "
                        f"¿Quizás te refieres a alguna de estas?\n{lista}"
                    )
                else:
                    msg = f"No encontré ninguna asignatura llamada '{nombre_asignatura}' en {nombre_titulacion}."
                dispatcher.utter_message(text=msg)
                return eventos_contexto
            else:
                # Sin nombre candidato: intentar fallback SELECT ALL + LLM
                from .text_to_sql import _inyectar_filtro_titulacion, ejecutar_query
                sql_all = """
                    SELECT codigo, nombre, curso, creditos, duracion, tipologia,
                           es_formacion_basica, es_optativa
                    FROM asignaturas
                    WHERE activa = true
                    ORDER BY curso, nombre
                """
                sql_all = _inyectar_filtro_titulacion(sql_all, contexto_titulacion)
                exito_all, resultados_all = ejecutar_query(sql_all, [])
                if exito_all and resultados_all:
                    print(f"   Fallback SELECT ALL: {len(resultados_all)} asignaturas de {contexto_titulacion}")
                    respuesta = generar_respuesta_natural(
                        pregunta=pregunta,
                        datos=resultados_all,
                        tipo='especifica'
                    )
                    dispatcher.utter_message(
                        text=respuesta,
                        json_message={"data": resultados_all[0] if len(resultados_all) == 1 else resultados_all},
                    )
                    return eventos_contexto + [
                        SlotSet("ultimo_nombre_asignatura", resultados_all[0].get('nombre') if len(resultados_all) == 1 else None)
                    ]
                dispatcher.utter_message(text="No pude identificar la asignatura en tu pregunta. ¿Puedes decirme el nombre?")
                return []

        # Horario/aula de asignatura → intent `consulta_horario_asignatura`
        # (ver ActionConsultaHorarioAsignatura al final de este archivo).

        # Clasificar si necesita RAG
        from .text_to_sql import _clasificar_necesita_rag
        necesita_rag = _clasificar_necesita_rag(pregunta, historial)

        # --- RAG: si la pregunta necesita plan docente ---
        if necesita_rag:
            codigo_rag = asignatura.get('codigo')
            grupo_detectado = _detectar_grupo(pregunta)
            print(f"   📚 Redirigiendo a búsqueda RAG para {asignatura.get('nombre')} (código={codigo_rag!r})")
            print(f"   📝 Pregunta RAG: {pregunta!r}")
            if grupo_detectado:
                print(f"   📎 Filtro por grupo: {grupo_detectado}")
            try:
                from rag.buscar import buscar_en_plan_docente
                chunks = buscar_en_plan_docente(
                    pregunta,
                    codigo_asignatura=codigo_rag,
                    grupo=grupo_detectado,
                )
                print(f"   📊 Chunks encontrados: {len(chunks) if chunks else 0}")
                if chunks:
                    for i, c in enumerate(chunks):
                        sim = c.get('similitud')
                        sim_str = f"{sim:.3f}" if sim is not None else "keyword"
                        print(f"     [{i+1}] sim={sim_str} | {c.get('seccion')} | {c.get('contenido','')[:60]}...")
                    respuesta_rag = _generar_respuesta_rag(
                        pregunta, chunks, asignatura.get('nombre')
                    )
                    if respuesta_rag:
                        dispatcher.utter_message(text=respuesta_rag)
                        return eventos_contexto + [
                            SlotSet("ultimo_codigo_consultado", codigo_rag),
                            SlotSet("ultimo_nombre_asignatura", asignatura.get('nombre')),
                            SlotSet("ultima_action_ejecutada", "consulta_especifica"),
                        ]
                # RAG necesario pero sin resultados → dar info básica de BD
                nombre = asignatura.get('nombre', 'esta asignatura')
                creditos = asignatura.get('creditos', '')
                curso = asignatura.get('curso', '')
                tipologia = asignatura.get('tipologia', '')
                info_basica = f"**{nombre}** es una asignatura"
                if creditos:
                    info_basica += f" de {creditos} créditos"
                if curso:
                    info_basica += f" de {curso}º curso"
                if tipologia:
                    info_basica += f" ({tipologia})"
                info_basica += "."
                dispatcher.utter_message(
                    text=f"{info_basica}\n\n"
                         f"No tengo información detallada del plan docente disponible "
                         f"para responder a tu pregunta sobre esta asignatura."
                )
                return eventos_contexto + [
                    SlotSet("ultimo_codigo_consultado", codigo_rag),
                    SlotSet("ultimo_nombre_asignatura", nombre),
                    SlotSet("ultima_action_ejecutada", "consulta_especifica"),
                ]
            except Exception as e:
                import traceback
                print(f"   ⚠ Error en RAG: {e}")
                print(traceback.format_exc())

        # --- Respuesta SQL (flujo original) ---
        respuesta = generar_respuesta_natural(
            pregunta=pregunta,
            datos=asignatura,
            tipo='especifica'
        )

        dispatcher.utter_message(
            text=respuesta,
            json_message={"data": asignatura},
        )

        return eventos_contexto + [
            SlotSet("ultimo_codigo_consultado", asignatura.get('codigo')),
            SlotSet("ultimo_nombre_asignatura", asignatura.get('nombre')),
            SlotSet("ultima_action_ejecutada", "consulta_especifica"),
        ]

    def _run_multi(
        self, nombres: List[str], pregunta: str, historial: str,
        titulacion: str, eventos_contexto: list,
        tracker, dispatcher,
    ) -> List[Dict[Text, Any]]:
        """Resuelve y responde sobre múltiples asignaturas en una sola consulta."""
        from .text_to_sql import _clasificar_necesita_rag, _inyectar_filtro_titulacion, ejecutar_query

        print(f"   📚 Multi-asignatura: {nombres}")
        necesita_rag = _clasificar_necesita_rag(pregunta, historial)
        grupo_detectado = _detectar_grupo(pregunta)
        all_chunks = []
        asignaturas_resueltas = []

        for nombre in nombres:
            # Buscar en BD
            nombre_norm = f"%{normalizar_texto(nombre)}%"
            sql = """SELECT codigo, nombre, curso, creditos, duracion, tipologia
                     FROM asignaturas
                     WHERE activa = true AND nombre_normalizado ILIKE %s"""
            sql = _inyectar_filtro_titulacion(sql, titulacion)
            exito, resultados = ejecutar_query(sql, [nombre_norm])
            if not exito or not resultados:
                print(f"   ⚠ Multi: '{nombre}' no encontrada")
                continue

            asig = resultados[0]
            asignaturas_resueltas.append(asig)
            print(f"   ✅ Multi: '{nombre}' → {asig.get('nombre')} ({asig.get('codigo')})")

            if necesita_rag:
                try:
                    from rag.buscar import buscar_en_plan_docente
                    chunks = buscar_en_plan_docente(
                        pregunta,
                        codigo_asignatura=asig.get('codigo'),
                        grupo=grupo_detectado,
                        limite=5,  # menos por asignatura para no saturar
                    )
                    if chunks:
                        # Etiquetar chunks con nombre de asignatura
                        for c in chunks:
                            c['_asignatura_label'] = asig.get('nombre')
                        all_chunks.extend(chunks)
                except Exception as e:
                    print(f"   ⚠ RAG error para {asig.get('nombre')}: {e}")

        if not asignaturas_resueltas:
            dispatcher.utter_message(
                text="No encontré ninguna de las asignaturas mencionadas."
            )
            return eventos_contexto

        # Si RAG recopiló chunks, generar respuesta combinada
        if all_chunks:
            nombres_str = " y ".join(a.get('nombre') for a in asignaturas_resueltas)
            respuesta = _generar_respuesta_rag(pregunta, all_chunks, nombres_str)
            if respuesta:
                dispatcher.utter_message(text=respuesta)
                return eventos_contexto + [
                    SlotSet("ultima_action_ejecutada", "consulta_especifica"),
                ]

        # Fallback: respuesta SQL con datos básicos
        respuesta = generar_respuesta_natural(
            pregunta=pregunta,
            datos=asignaturas_resueltas,
            tipo='especifica'
        )
        dispatcher.utter_message(text=respuesta)
        return eventos_contexto + [
            SlotSet("ultima_action_ejecutada", "consulta_especifica"),
        ]


# ============================================================================
# ACTION: LISTADO DE ASIGNATURAS
# ============================================================================

class ActionConsultaListado(Action):
    """
    Maneja consultas que piden LISTAR asignaturas con filtros.
    
    Ejemplos:
    - "Dame las optativas de cuarto"
    - "Asignaturas obligatorias de primero"
    - "¿Qué asignaturas hay en segundo?"
    """

    def name(self) -> Text:
        return "action_consulta_listado"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        pregunta = tracker.latest_message.get("text", "")
        historial = obtener_historial_reciente(tracker)
        contexto_titulacion, eventos_contexto = comprobar_titulacion(tracker, dispatcher)
        if not contexto_titulacion:
            return []

        print(f"\n{'='*60}")
        print(f"📋 CONSULTA LISTADO: {pregunta}")
        print(f"   Titulación: {contexto_titulacion}")
        print(f"{'='*60}")

        # Generar SQL con LLM
        resultado_sql = generar_sql_listado(
            pregunta=pregunta,
            contexto_titulacion=contexto_titulacion,
            historial=historial
        )

        print(f"   SQL generada: {resultado_sql.get('sql', '')[:100]}...")
        print(f"   Filtros detectados: {resultado_sql.get('filtros_aplicados', {})}")

        # Ejecutar query
        exito, resultados = ejecutar_query(
            resultado_sql['sql'],
            resultado_sql.get('parametros', [])
        )

        if not exito:
            dispatcher.utter_message(
                text="Hubo un problema al buscar las asignaturas. Por favor, intenta de nuevo."
            )
            return []

        if not resultados:
            dispatcher.utter_message(text="No encontré asignaturas con esos criterios.")
            return []

        # Paginación: mostrar máximo 8, guardar el resto
        MAX_MOSTRAR = 8
        hay_mas = len(resultados) > MAX_MOSTRAR
        datos_a_mostrar = resultados[:MAX_MOSTRAR] if hay_mas else resultados

        # Generar respuesta natural con Ollama
        respuesta = generar_respuesta_natural(
            pregunta=pregunta,
            datos=datos_a_mostrar,
            tipo='listado'
        )

        dispatcher.utter_message(
            text=respuesta,
            json_message={"data": datos_a_mostrar},
        )

        # Si hay más resultados, guardarlos para paginación
        if hay_mas:
            dispatcher.utter_message(
                text=f"Hay {len(resultados) - MAX_MOSTRAR} más. ¿Quieres ver todas?"
            )
            return eventos_contexto + [SlotSet("ultimos_resultados_asignaturas", resultados)]

        return eventos_contexto


# ============================================================================
# ACTION: CONTEO DE ASIGNATURAS
# ============================================================================

class ActionConsultaConteo(Action):
    """
    Maneja consultas que piden CONTAR asignaturas.
    
    Ejemplos:
    - "¿Cuántas asignaturas hay en primero?"
    - "¿Cuántas optativas de cuarto?"
    - "Número de obligatorias en segundo"
    """

    def name(self) -> Text:
        return "action_consulta_conteo"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        pregunta = tracker.latest_message.get("text", "")
        historial = obtener_historial_reciente(tracker)
        contexto_titulacion, eventos_contexto = comprobar_titulacion(tracker, dispatcher)
        if not contexto_titulacion:
            return []

        print(f"\n{'='*60}")
        print(f"🔢 CONSULTA CONTEO: {pregunta}")
        print(f"   Titulación: {contexto_titulacion}")
        print(f"{'='*60}")

        # Si la pregunta menciona una asignatura concreta y necesita RAG,
        # no es un COUNT de asignaturas sino una consulta de plan docente
        from .text_to_sql import _necesita_rag_heuristica
        if _necesita_rag_heuristica(pregunta):
            asignatura, nombre_usado = resolver_asignatura(
                pregunta, tracker, contexto_titulacion,
                usar_seguimiento=False,
            )
            if asignatura:
                codigo_rag = asignatura.get('codigo')
                nombre_rag = asignatura.get('nombre', nombre_usado)
                print(f"   → Redirigiendo a flujo RAG: pregunta sobre '{nombre_rag}'")
                grupo_detectado = _detectar_grupo(pregunta)
                if grupo_detectado:
                    print(f"   📎 Filtro por grupo: {grupo_detectado}")
                try:
                    from rag.buscar import buscar_en_plan_docente
                    chunks = buscar_en_plan_docente(
                        pregunta, codigo_asignatura=codigo_rag, grupo=grupo_detectado
                    )
                    print(f"   📊 Chunks encontrados: {len(chunks) if chunks else 0}")
                    if chunks:
                        respuesta_rag = _generar_respuesta_rag(pregunta, chunks, nombre_rag)
                        if respuesta_rag:
                            dispatcher.utter_message(text=respuesta_rag)
                            eventos_rag = [
                                SlotSet("ultimo_codigo_consultado", codigo_rag),
                                SlotSet("ultimo_nombre_asignatura", nombre_rag),
                            ]
                            if grupo_detectado:
                                eventos_rag.append(SlotSet("contexto_grupo", grupo_detectado))
                            return eventos_contexto + eventos_rag
                    dispatcher.utter_message(
                        text=f"No encontré información detallada del plan docente de "
                             f"**{nombre_rag}**. ¿Puedes reformular la pregunta?"
                    )
                    return eventos_contexto
                except Exception as e:
                    import traceback
                    print(f"   ⚠ Error en RAG: {e}\n{traceback.format_exc()}")

        # Generar SQL con LLM
        resultado_sql = generar_sql_conteo(
            pregunta=pregunta,
            contexto_titulacion=contexto_titulacion,
            historial=historial
        )

        print(f"   SQL generada: {resultado_sql.get('sql', '')}")
        print(f"   Filtros detectados: {resultado_sql.get('filtros_aplicados', {})}")

        # Ejecutar COUNT
        exito, count = ejecutar_count(
            resultado_sql['sql'],
            resultado_sql.get('parametros', [])
        )

        if not exito:
            dispatcher.utter_message(
                text="Hubo un problema al contar las asignaturas. Por favor, intenta de nuevo."
            )
            return []

        # Generar respuesta natural con Ollama
        respuesta = generar_respuesta_natural(
            pregunta=pregunta,
            datos=count,
            tipo='conteo'
        )

        dispatcher.utter_message(
            text=respuesta,
            json_message={"data": count},
        )

        return eventos_contexto


# ============================================================================
# ACTION: MOSTRAR TODAS (PAGINACIÓN)
# ============================================================================

class ActionMostrarTodasAsignaturas(Action):
    """
    Muestra todos los resultados guardados en el slot de paginación.
    Se activa con el intent 'pedir_mas_resultados'.
    """

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
            dispatcher.utter_message(
                text="No hay resultados pendientes de mostrar."
            )
            return []

        # Generar respuesta natural con Ollama para la lista completa
        respuesta = generar_respuesta_natural(
            pregunta="Muéstrame la lista completa de asignaturas",
            datos=resultados,
            tipo='listado'
        )

        dispatcher.utter_message(text=respuesta)

        # Limpiar el slot
        return [SlotSet("ultimos_resultados_asignaturas", None)]


# ============================================================================
# ACTION: HORARIO/AULA DE UNA ASIGNATURA
# ============================================================================

class ActionConsultaHorarioAsignatura(Action):
    """
    Consulta la tabla `horarios` para una asignatura concreta.

    Se activa por el intent `consulta_horario_asignatura`:
      - "¿A qué hora tengo FP?" / "aula de ADDA"
      - "horario de Redes grupo 1" / "¿dónde es SO grupo 3?"
      - Follow-ups sin entidad: "y en qué aula", "qué horario tiene esa" →
        usan `ultimo_nombre_asignatura`.

    Separado de `ActionConsultaEspecifica` (R1): el NLU distingue entre
    ficha/plan docente (evaluación, temario, profesores…) y horario (aula,
    día, hora). Esto elimina la lista `_PALABRAS_HORARIO_ASIGNATURA` y
    rompe el ciclo de imports `asignaturas ↔ horarios`.
    """

    def name(self) -> Text:
        return "action_consulta_horario_asignatura"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        pregunta = tracker.latest_message.get("text", "")
        contexto_titulacion, eventos_contexto = comprobar_titulacion(tracker, dispatcher)
        if not contexto_titulacion:
            return []

        print(f"\n{'='*60}")
        print(f"📅 HORARIO DE ASIGNATURA: {pregunta}")
        print(f"   Contexto: {contexto_titulacion}")
        print(f"{'='*60}")

        # Bloquear "letra del DNI" antes de resolver asignatura (las letras
        # sueltas chocan con alias, p.ej. T = Teledetección).
        from ..horarios.actions import _tiene_referencia_letra_dni
        grupo_detectado = _detectar_grupo(pregunta)
        if _tiene_referencia_letra_dni(pregunta) and not grupo_detectado:
            dispatcher.utter_message(
                text=("La asignación de grupos por letra del DNI varía cada curso y titulación. "
                      "¿Puedes indicar el **número de grupo** (1, 2, 3…)? Lo tienes en SEVIUS.")
            )
            return eventos_contexto

        # Multi-asignatura no soportado en horario: preferible pedir una
        # sola antes que devolver datos mezclados o alucinados por el LLM.
        nombres_multi = _extraer_multiples_nombres(pregunta, contexto_titulacion)
        if len(nombres_multi) >= 2:
            opciones = " o ".join(f"**{n}**" for n in nombres_multi[:3])
            dispatcher.utter_message(
                text=(f"Por ahora solo puedo mostrarte el horario de una asignatura a la vez. "
                      f"¿De cuál quieres empezar: {opciones}?")
            )
            return eventos_contexto

        asignatura, nombre_asignatura = resolver_asignatura(
            pregunta, tracker, contexto_titulacion
        )

        if not asignatura:
            nombre_titulacion = BotConfig.get_nombre_titulacion(contexto_titulacion)
            if nombre_asignatura:
                sugerencias = _sugerencias_asignatura(nombre_asignatura, contexto_titulacion)
                if sugerencias:
                    lista = "\n".join(f"- {s}" for s in sugerencias)
                    msg = (
                        f"No encontré ninguna asignatura llamada '{nombre_asignatura}' en {nombre_titulacion}. "
                        f"¿Quizás te refieres a alguna de estas?\n{lista}"
                    )
                else:
                    msg = f"No encontré ninguna asignatura llamada '{nombre_asignatura}' en {nombre_titulacion}."
                dispatcher.utter_message(text=msg)
            else:
                dispatcher.utter_message(
                    text="¿De qué asignatura quieres saber el horario? Dime su nombre o alias (p.ej. FP, ADDA, DP1)."
                )
            return eventos_contexto

        respuesta = _responder_horario_asignatura(
            pregunta, asignatura, contexto_titulacion, grupo_detectado
        )

        if respuesta:
            dispatcher.utter_message(text=respuesta)
        else:
            nombre_tit = BotConfig.get_nombre_titulacion(contexto_titulacion)
            dispatcher.utter_message(
                text=f"No encontré horarios de **{asignatura.get('nombre')}** en {nombre_tit}."
            )

        return eventos_contexto + [
            SlotSet("ultimo_codigo_consultado", asignatura.get('codigo')),
            SlotSet("ultimo_nombre_asignatura", asignatura.get('nombre')),
            SlotSet("ultima_action_ejecutada", "action_consulta_horario_asignatura"),
        ]

