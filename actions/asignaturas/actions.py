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

from ..shared.config import BotConfig
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


def _detectar_titulacion_con_llm(mensaje: str) -> Optional[str]:
    """
    Usa el LLM para detectar si el mensaje del usuario menciona una titulación.
    Obtiene las titulaciones reales de la BD y las pasa al LLM en el prompt.
    Devuelve el código (ej. 'GII-IS') o None si no hay referencia.
    """
    if not mensaje:
        return None

    titulaciones = _cargar_titulaciones_desde_bd()
    if not titulaciones:
        return None

    lista_txt = "\n".join(
        f"- {t['codigo']}: {t['nombre']}" for t in titulaciones
    )
    codigos_validos = [t['codigo'] for t in titulaciones]

    codigos_str = ", ".join(codigos_validos)

    prompt = f"""Analiza el mensaje del usuario y determina si hace referencia a alguna de las siguientes titulaciones universitarias.

TITULACIONES DISPONIBLES (únicamente estas, no hay más):
{lista_txt}

Mensaje del usuario: "{mensaje}"

INSTRUCCIONES ESTRICTAS:
- Si el mensaje menciona o alude a una titulación de la lista, responde SOLO con su código exacto (ejemplos: {codigos_str}).
- Si no hay referencia a ninguna titulación de la lista, responde SOLO con: ninguna
- Está PROHIBIDO inventar o deducir titulaciones que no aparezcan en la lista. 
- No escribas nada más, ni puntos, ni explicaciones.

Respuesta:"""

    respuesta = llamar_gemini(prompt, timeout=120, options={"num_predict": 20, "temperature": 0.0})
    if not respuesta:
        return None

    respuesta_limpia = respuesta.strip().upper().replace(".", "").replace("\n", "")
    print(f"   → LLM titulación detection: '{respuesta_limpia}'")

    # Comprobar si la respuesta es un código válido
    if respuesta_limpia in codigos_validos:
        return respuesta_limpia

    # Tolerancia: el LLM a veces añade texto extra, buscar si hay algún código válido
    for codigo in codigos_validos:
        if codigo in respuesta_limpia:
            return codigo

    return None


def _construir_lista_titulaciones() -> str:
    """Construye el texto de titulaciones disponibles consultando la BD."""
    titulaciones = _cargar_titulaciones_desde_bd()
    if titulaciones:
        return "\n".join(
            f"• **{t['nombre']}** ({t['codigo']})"
            for t in titulaciones
        )
    # Fallback si la BD no está disponible
    return (
        "• **Ingeniería del Software** (GII-IS)\n"
        "• **Tecnologías Informáticas** (GII-TI)\n"
        "• **Ingeniería de Computadores** (GII-IC)"
    )


def comprobar_titulacion(
    tracker, dispatcher, mensaje: str = None
) -> Tuple[Optional[str], List]:
    """
    Comprueba si hay titulación disponible para la consulta.
    Primero intenta detectarla en el texto del mensaje (consultando la BD);
    si no, la lee del slot. Si no hay ninguna, pide al usuario que la indique.

    Devuelve (codigo_titulacion, eventos_rasa).
    - codigo_titulacion: str o None.
    - eventos_rasa: [SlotSet] si se detectó del mensaje, [] en caso contrario.
    """
    eventos: List = []

    titulacion_slot = tracker.get_slot("contexto_titulacion")

    # Solo detectar titulación del mensaje si el usuario NO tiene una ya asignada
    if not titulacion_slot and mensaje:
        titulacion_en_mensaje = _detectar_titulacion_con_llm(mensaje)
    else:
        titulacion_en_mensaje = None

    titulacion = titulacion_en_mensaje or titulacion_slot

    if titulacion_en_mensaje:
        eventos = [SlotSet("contexto_titulacion", titulacion_en_mensaje)]
        nombre = BotConfig.get_nombre_titulacion(titulacion_en_mensaje)
        print(f"   → Titulación detectada en mensaje: {nombre} ({titulacion_en_mensaje})")

    if not titulacion:
        lista = _construir_lista_titulaciones()
        dispatcher.utter_message(
            text=f"Antes de consultar asignaturas, necesito saber tu titulación:\n\n"
                 f"{lista}\n\n"
                 f"Dime cuál cursas."
        )
        return None, []

    return titulacion, eventos


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

    contexto = "\n\n---\n\n".join(
        f"[{c.get('seccion', 'general')}]\n{c['contenido']}\nMetadatos: {c.get('metadata', {})}"
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

Respuesta:"""

    respuesta = llamar_gemini(
        prompt,
        timeout=30,
        options={"temperature": 0.3, "num_predict": 300},
    )
    return respuesta.strip() if respuesta else None


# ============================================================================
# ACTION: CONSULTA ESPECÍFICA
# ============================================================================

class ActionConsultaEspecifica(Action):
    """
    Maneja consultas sobre UNA asignatura específica.
    
    Ejemplos:
    - "¿Cuántos créditos tiene Redes?"
    - "¿Qué es IS2?"
    - "¿En qué curso está Cálculo?"
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
        contexto_titulacion, eventos_contexto = comprobar_titulacion(tracker, dispatcher, pregunta)
        if not contexto_titulacion:
            return []

        print(f"\n{'='*60}")
        print(f"🔍 CONSULTA ESPECÍFICA: {pregunta}")
        print(f"   Contexto: {contexto_titulacion}")
        print(f"   Última asignatura: {tracker.get_slot('ultimo_nombre_asignatura')} ({tracker.get_slot('ultimo_codigo_consultado')})")
        print(f"{'='*60}")

        # Resolver asignatura con pipeline compartido
        asignatura, nombre_asignatura = resolver_asignatura(
            pregunta, tracker, contexto_titulacion
        )

        if not asignatura:
            if nombre_asignatura:
                nombre_titulacion = BotConfig.get_nombre_titulacion(contexto_titulacion)
                msg = f"No encontré ninguna asignatura llamada '{nombre_asignatura}' en {nombre_titulacion}."
                print(f"   ❌ Asignatura no encontrada: {nombre_asignatura}")
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
                # RAG necesario pero sin resultados → informar al usuario
                nombre = asignatura.get('nombre', 'esta asignatura')
                dispatcher.utter_message(
                    text=f"No he encontrado información detallada del plan docente de "
                         f"**{nombre}** en la titulación **{contexto_titulacion}**. "
                         f"¿Estás seguro de que esta asignatura pertenece a esa titulación?"
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
        contexto_titulacion, eventos_contexto = comprobar_titulacion(tracker, dispatcher, pregunta)
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
        contexto_titulacion, eventos_contexto = comprobar_titulacion(tracker, dispatcher, pregunta)
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

