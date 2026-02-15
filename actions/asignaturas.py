"""
Actions de Rasa para consultas de asignaturas.
Arquitectura con 3 intents separados + Text-to-SQL dinámico.
"""

from typing import Any, Text, Dict, List, Optional
from rapidfuzz import fuzz, process
import json
import re
import unicodedata

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


# ============================================================================
# UTILIDADES
# ============================================================================

TITULACIONES_DISPONIBLES = (
    "• **Ingeniería del Software** (IS)\n"
    "• **Tecnologías Informáticas** (TI)\n"
    "• **Ingeniería de Computadores** (IC)"
)


def comprobar_titulacion(tracker, dispatcher) -> Optional[str]:
    """
    Comprueba si hay titulación seleccionada.
    Si no la hay, pide al usuario que la indique y devuelve None.
    Si la hay, devuelve el código de titulación.
    """
    titulacion = tracker.get_slot("contexto_titulacion")
    if not titulacion:
        dispatcher.utter_message(
            text=f"Antes de consultar asignaturas, necesito saber tu titulación:\n\n"
                 f"{TITULACIONES_DISPONIBLES}\n\n"
                 f"Dime cuál cursas."
        )
        return None
    return titulacion

def normalizar_texto(texto: str) -> str:
    """Normaliza texto para búsqueda (sin tildes, minúsculas, sin espacios extra)."""
    if not texto:
        return ""
    # Quitar tildes
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    # Minúsculas y espacios
    texto = texto.lower().strip()
    texto = re.sub(r'\s+', ' ', texto)
    return texto


def extraer_nombre_asignatura(tracker) -> Optional[str]:
    """Extrae el nombre de asignatura del mensaje actual."""
    # Primero intentar extraer de entidades
    for entity in tracker.latest_message.get('entities', []):
        if entity.get('entity') == 'nombre_asignatura':
            return entity.get('value')
    
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
        contexto_titulacion = comprobar_titulacion(tracker, dispatcher)
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
        nombre_asignatura = extraer_nombre_asignatura(tracker)
        
        # Detectar si es pregunta de seguimiento (sin nombre explícito)
        es_seguimiento = self._es_seguimiento(pregunta, nombre_asignatura)
        
        if es_seguimiento and ultimo_nombre:
            nombre_asignatura = ultimo_nombre
            print(f"   → Usando contexto previo: {nombre_asignatura}")
        
        if not nombre_asignatura:
            dispatcher.utter_message(
                text="No pude identificar la asignatura. ¿Puedes decirme el nombre?"
            )
            return []

        # Generar SQL con Ollama
        resultado_sql = generar_sql_especifica(
            pregunta=pregunta,
            nombre_asignatura=nombre_asignatura,
            contexto_titulacion=contexto_titulacion
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
            from .text_to_sql import _inyectar_filtro_titulacion
            sql_flexible = """
                SELECT codigo, nombre, curso, creditos, duracion, tipologia, 
                       es_formacion_basica, es_optativa 
                FROM asignaturas 
                WHERE activa = true AND nombre_normalizado ILIKE %s
            """
            sql_flexible = _inyectar_filtro_titulacion(sql_flexible, contexto_titulacion)
            nombre_norm = f"%{normalizar_texto(nombre_asignatura)}%"
            exito, resultados = ejecutar_query(sql_flexible, [nombre_norm])
            
            if not exito or not resultados:
                dispatcher.utter_message(
                    text=f"No encontré ninguna asignatura llamada '{nombre_asignatura}'."
                )
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

        return [
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
        contexto_titulacion = comprobar_titulacion(tracker, dispatcher)
        if not contexto_titulacion:
            return []

        print(f"\n{'='*60}")
        print(f"📋 CONSULTA LISTADO: {pregunta}")
        print(f"   Titulación: {contexto_titulacion}")
        print(f"{'='*60}")

        # Generar SQL con Ollama
        resultado_sql = generar_sql_listado(
            pregunta=pregunta,
            contexto_titulacion=contexto_titulacion
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
            return [SlotSet("ultimos_resultados_asignaturas", resultados)]

        return []


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
        contexto_titulacion = comprobar_titulacion(tracker, dispatcher)
        if not contexto_titulacion:
            return []

        print(f"\n{'='*60}")
        print(f"🔢 CONSULTA CONTEO: {pregunta}")
        print(f"   Titulación: {contexto_titulacion}")
        print(f"{'='*60}")

        # Generar SQL con Ollama
        resultado_sql = generar_sql_conteo(
            pregunta=pregunta,
            contexto_titulacion=contexto_titulacion
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

        return []


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

