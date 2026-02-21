"""
Actions de Rasa para consultas de asignaturas.
Arquitectura con 3 intents separados + Text-to-SQL dinámico.
"""

from typing import Any, Text, Dict, List, Optional, Tuple
import json
import re
import unicodedata
from .gemini_client import llamar_gemini

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from .text_to_sql import (
    generar_sql_especifica,
    generar_sql_listado,
    generar_sql_conteo,
    ejecutar_query,
    ejecutar_count,
    generar_respuesta_natural
)

from .config import BotConfig
from .db import db_client


# ============================================================================
# UTILIDADES
# ============================================================================

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
            # Si hay un turno previo pendiente, guardarlo
            if turno_actual.get("user"):
                turnos.append(turno_actual)
            turno_actual = {"user": evento.get("text", ""), "bot": ""}
        elif evento.get("event") == "bot" and turno_actual.get("user"):
            # Solo guardar la primera respuesta del bot por turno
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

    titulacion_en_mensaje = _detectar_titulacion_con_llm(mensaje) if mensaje else None
    titulacion = titulacion_en_mensaje or tracker.get_slot("contexto_titulacion")

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
    Si se detectó titulación inline, valida que la entidad no sea parte del nombre de la titulación."""
    for entity in tracker.latest_message.get('entities', []):
        if entity.get('entity') == 'nombre_asignatura':
            valor = entity.get('value', '')
            # Si se detectó titulación en el mensaje, validar que la entidad
            # no sea basura (parte del nombre de la titulación)
            if titulacion_detectada_en_mensaje and valor:
                valor_lower = normalizar_texto(valor)
                # Descartar si es demasiado corto o parece parte de titulación
                fragmentos_titulacion = [
                    'software', 'computador', 'telematic', 'informatica',
                    'ingenieria', 'grado', 'tecnolog'
                ]
                if len(valor_lower) < 4 or any(f in valor_lower for f in fragmentos_titulacion):
                    print(f"   ⚠ Entidad NLU descartada (parece titulación): '{valor}'")
                    return None
            return valor
    
    # Si no hay entidad, el LLM lo extraerá del texto
    return None


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
        ultimo_codigo = tracker.get_slot("ultimo_codigo_consultado")
        ultimo_nombre = tracker.get_slot("ultimo_nombre_asignatura")

        print(f"\n{'='*60}")
        print(f"🔍 CONSULTA ESPECÍFICA: {pregunta}")
        print(f"   Contexto: {contexto_titulacion}")
        print(f"   Última asignatura: {ultimo_nombre} ({ultimo_codigo})")
        print(f"{'='*60}")

        # Extraer nombre de asignatura
        titulacion_inline = len(eventos_contexto) > 0  # Si hay eventos, se detectó del mensaje
        nombre_asignatura = extraer_nombre_asignatura(tracker, titulacion_inline)
        
        # Detectar si es pregunta de seguimiento (sin nombre explícito)
        es_seguimiento = self._es_seguimiento(pregunta, nombre_asignatura)
        
        if es_seguimiento and ultimo_nombre:
            nombre_asignatura = ultimo_nombre
            print(f"   → Usando contexto previo: {nombre_asignatura}")
        
        # Si no hay entidad, dejar que el LLM extraiga del texto completo
        if not nombre_asignatura:
            print(f"   → Sin entidad NLU, el LLM extraerá de la pregunta completa")

        # Generar SQL con LLM
        resultado_sql = generar_sql_especifica(
            pregunta=pregunta,
            nombre_asignatura=nombre_asignatura,
            contexto_titulacion=contexto_titulacion,
            historial=historial
        )

        print(f"   SQL generada: {resultado_sql.get('sql', '')[:100]}...")
        print(f"   Parámetros: {resultado_sql.get('parametros', [])}")

        # Ejecutar query
        exito, resultados = ejecutar_query(
            resultado_sql['sql'],
            resultado_sql.get('parametros', [])
        )

        if not exito or not resultados:
            # Intentar búsqueda más flexible (con filtro de titulación)
            if nombre_asignatura:
                from .text_to_sql import _inyectar_filtro_titulacion, _expandir_alias
                nombre_expandido = _expandir_alias(nombre_asignatura)
                sql_flexible = """
                    SELECT codigo, nombre, curso, creditos, duracion, tipologia, 
                           es_formacion_basica, es_optativa 
                    FROM asignaturas 
                    WHERE activa = true AND nombre_normalizado ILIKE %s
                """
                sql_flexible = _inyectar_filtro_titulacion(sql_flexible, contexto_titulacion)
                nombre_norm = f"%{normalizar_texto(nombre_expandido)}%"
                exito, resultados = ejecutar_query(sql_flexible, [nombre_norm])
            
            if not exito or not resultados:
                msg = f"No encontré ninguna asignatura llamada '{nombre_asignatura}'." if nombre_asignatura else "No pude identificar la asignatura en tu pregunta. ¿Puedes decirme el nombre?"
                dispatcher.utter_message(text=msg)
                return []

        # Tomar el primer resultado (más relevante)
        asignatura = resultados[0]

        # Generar respuesta natural con Ollama
        respuesta = generar_respuesta_natural(
            pregunta=pregunta,
            datos=asignatura,
            tipo='especifica'
        )

        dispatcher.utter_message(text=respuesta)

        return eventos_contexto + [
            SlotSet("ultimo_codigo_consultado", asignatura.get('codigo')),
            SlotSet("ultimo_nombre_asignatura", asignatura.get('nombre'))
        ]

    def _es_seguimiento(self, pregunta: str, nombre_extraido: str) -> bool:
        """Detecta si es una pregunta de seguimiento (usa contexto previo)."""
        if nombre_extraido:
            return False
        
        pregunta_lower = pregunta.lower()
        
        # Patrones de seguimiento
        patrones_seguimiento = [
            r'^y\s+(cuantos|que|cual|es|tiene)',
            r'^(esa|esta|la)\s+',
            r'^(creditos|curso|duracion|tipo)',
            r'cuantos creditos tiene\??$',
            r'es (obligatoria|optativa)\??$',
            r'de que (curso|cuatrimestre) es\??$',
        ]
        
        for patron in patrones_seguimiento:
            if re.search(patron, pregunta_lower):
                return True
        
        return False


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

        dispatcher.utter_message(text=respuesta)

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

        dispatcher.utter_message(text=respuesta)

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

