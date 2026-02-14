from typing import Any, Text, Dict, List, Optional
from rapidfuzz import fuzz, process
import json
import re
from decimal import Decimal
import unicodedata

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from .db import db_client
from .ollama_client import llamar_ollama


def cargar_asignaturas_titulacion(
    contexto_centro: str,
    contexto_titulacion: str = None
) -> List[Dict[str, Any]]:
    """Carga todas las asignaturas de una titulacion en memoria."""
    if db_client is None:
        return []

    conn = db_client.get_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor()

        if contexto_titulacion:
            query = """
                SELECT codigo, nombre, curso, creditos, duracion, tipologia,
                       es_formacion_basica, es_optativa, titulacion_id
                FROM asignaturas
                WHERE activa = true AND titulacion_id = %s
                ORDER BY curso, nombre
            """
            cursor.execute(query, (contexto_titulacion,))
        else:
            query = """
                SELECT DISTINCT a.codigo, a.nombre, a.curso, a.creditos, a.duracion,
                       a.tipologia, a.es_formacion_basica, a.es_optativa, a.titulacion_id
                FROM asignaturas a
                JOIN titulaciones t ON a.titulacion_id = t.id
                JOIN centros c ON t.centro_id = c.id
                WHERE a.activa = true AND c.codigo = %s
                ORDER BY a.curso, a.nombre
            """
            cursor.execute(query, (contexto_centro,))

        resultados = cursor.fetchall()
        cursor.close()

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

        print(f"Cargadas {len(asignaturas)} asignaturas en memoria")
        return asignaturas

    except Exception as e:
        print(f"Error cargando asignaturas: {e}")
        return []
    finally:
        conn.close()


def buscar_en_memoria(
    nombre_o_codigo: str,
    asignaturas: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Busca una asignatura en memoria usando fuzzy matching."""
    if not asignaturas:
        return None

    nombre_normalizado = normalizar_texto(nombre_o_codigo)
    print(f"  Buscando: '{nombre_o_codigo}' (normalizado: '{nombre_normalizado}')")

    # Busqueda exacta por codigo
    for asig in asignaturas:
        if asig["codigo"].upper() == nombre_o_codigo.upper():
            print(f"  ✓ Encontrada por código: {asig['nombre']}")
            return asig

    # Busqueda exacta por nombre (con normalizacion)
    for asig in asignaturas:
        if normalizar_texto(asig["nombre"]) == nombre_normalizado:
            print(f"  ✓ Encontrada exacta: {asig['nombre']}")
            return asig

    # Busqueda parcial (el nombre está contenido)
    for asig in asignaturas:
        nombre_asig_norm = normalizar_texto(asig["nombre"])
        if nombre_normalizado in nombre_asig_norm or nombre_asig_norm.startswith(nombre_normalizado):
            print(f"  ✓ Encontrada parcial: {asig['nombre']}")
            return asig

    # Fuzzy matching como último recurso
    nombres = [a["nombre"] for a in asignaturas]
    matches = process.extract(nombre_o_codigo, nombres, scorer=fuzz.WRatio, limit=3)

    for match, score, idx in matches:
        if score >= 70:
            print(f"  ✓ Encontrada fuzzy (score={score}): {asignaturas[idx]['nombre']}")
            return asignaturas[idx]

    print(f"  ✗ No encontrada")
    return None


def buscar_por_codigo(codigo: str, asignaturas: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Busca asignatura por codigo exacto."""
    for asig in asignaturas:
        if asig["codigo"] == codigo:
            return asig
    return None


def filtrar_en_memoria(asignaturas: List[Dict[str, Any]], **filtros) -> List[Dict[str, Any]]:
    """Filtra asignaturas en memoria segun criterios."""
    resultados = asignaturas
    for key, value in filtros.items():
        if value is not None:
            resultados = [a for a in resultados if a.get(key) == value]
    return resultados


def respuesta_template(asignatura: Dict[str, Any], atributo: str) -> str:

    """Genera respuesta directa usando LLM para procesar la pregunta y la salida de la respuesta
    Recibe la pregunta que se hizo y el atributo que se quiere responder, y devuelve la respuesta 
    procesada por el modelo de lenguaje 
    """ 

def analizar_consulta_con_llm(pregunta: str, contexto_asignatura: str = None) -> Dict[str, Any]:
    """
    Usa Ollama para analizar la consulta con contexto conversacional.
    El LLM entiende pronombres, seguimientos y cambios de tema.
    """

    # Construir contexto para el LLM
    if contexto_asignatura:
        contexto_str = f'CONTEXTO: La ultima asignatura consultada fue "{contexto_asignatura}".\n'
    else:
        contexto_str = "CONTEXTO: No hay asignatura previa en la conversacion.\n"

    prompt = f"""{contexto_str}PREGUNTA DEL USUARIO: "{pregunta}"

Analiza la consulta y responde SOLO con JSON valido:

{{
  "tipo": "especifica" o "general",
  "es_seguimiento": true/false,
  "nombre_asignatura": "nombre" o null,
  "atributo": "creditos"|"tipo"|"curso"|"duracion"|"general"
}}

REGLAS:
- tipo="especifica": pregunta sobre UNA asignatura concreta
- tipo="general": pregunta sobre VARIAS asignaturas (ej: "optativas de cuarto")
- es_seguimiento=true: si usa pronombres (esa, la, tiene) o continua tema anterior SIN nombrar asignatura nueva
- es_seguimiento=false: si menciona una asignatura nueva o no hay contexto
- nombre_asignatura: solo si menciona una asignatura NUEVA, null si es seguimiento
- atributo: que informacion pide (creditos, tipo, curso, duracion, o general si pide todo)

EJEMPLOS:
- "cuantos creditos tiene Redes" -> {{"tipo":"especifica","es_seguimiento":false,"nombre_asignatura":"Redes","atributo":"creditos"}}
- "y cuantos creditos tiene?" (con contexto) -> {{"tipo":"especifica","es_seguimiento":true,"nombre_asignatura":null,"atributo":"creditos"}}
- "es obligatoria?" (con contexto) -> {{"tipo":"especifica","es_seguimiento":true,"nombre_asignatura":null,"atributo":"tipo"}}
- "y Programacion?" (con contexto) -> {{"tipo":"especifica","es_seguimiento":false,"nombre_asignatura":"Programacion","atributo":"general"}}
- "asignaturas de primero" -> {{"tipo":"general","es_seguimiento":false,"nombre_asignatura":null,"atributo":null}}

JSON:"""

    try:
        salida = llamar_ollama(prompt, timeout=15)
        if salida:
            # Extraer JSON de la respuesta
            match = re.search(r'\{[^{}]*\}', salida)
            if match:
                data = json.loads(match.group(0))
                # Normalizar campos
                data["usar_contexto"] = data.get("es_seguimiento", False)
                data["atributo_solicitado"] = data.get("atributo", "general")
                data["metodo"] = "llm"
                print(f"LLM analisis: {data}")
                return data
    except Exception as e:
        print(f"Error en LLM: {e}")

    # Fallback basico si LLM falla
    return {
        "tipo": "general",
        "nombre_asignatura": None,
        "atributo_solicitado": None,
        "usar_contexto": False,
        "metodo": "fallback"
    }


def extraer_filtros_heuristicas(pregunta: str) -> Dict[str, Any]:
    """Extrae filtros de una consulta general."""


class ActionConsultarAsignaturaDB(Action):
    """Action principal para consultas de asignaturas.
    LLM recibe consulta + contexto (ultima asignatura)
    Crea una query en la base de datos o busca en memoria segun el tipo de consulta."""

    def name(self) -> Text:
        return "action_consultar_asignatura_db"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        pregunta = tracker.latest_message.get("text", "")
        contexto_centro = tracker.get_slot("contexto_centro") or "ETSII"
        contexto_titulacion = tracker.get_slot("contexto_titulacion")
        ultimo_codigo = tracker.get_slot("ultimo_codigo_consultado")
        ultimo_nombre = tracker.get_slot("ultimo_nombre_asignatura")

        if not pregunta:
            dispatcher.utter_message(text="No entendi tu pregunta. Puedes reformularla?")
            return []

        print(f"\n{'='*60}")
        print(f"CONSULTA: {pregunta}")
        print(f"Contexto: {contexto_centro}/{contexto_titulacion}")
        print(f"Ultima asignatura: {ultimo_nombre} ({ultimo_codigo})")
        print(f"{'='*60}\n")

        # Cargar asignaturas en memoria
        asignaturas_memoria = tracker.get_slot("asignaturas_memoria")
        slots_set = []

        if not asignaturas_memoria:
            asignaturas_memoria = cargar_asignaturas_titulacion(contexto_centro, contexto_titulacion)
            if not asignaturas_memoria:
                dispatcher.utter_message(text="No pude cargar las asignaturas.")
                return []
            slots_set.append(SlotSet("asignaturas_memoria", asignaturas_memoria))

        # Analizar consulta CON contexto (LLM entiende seguimientos)
        analisis = analizar_consulta_unificado(pregunta, ultimo_codigo, ultimo_nombre)
        tipo_consulta = analisis.get("tipo", "general")

        print(f"Analisis: {analisis}")

        if tipo_consulta == "especifica":
            result = self._procesar_especifica(
                pregunta, analisis, asignaturas_memoria, ultimo_codigo, dispatcher
            )
        else:
            result = self._procesar_general(
                pregunta, analisis, asignaturas_memoria, dispatcher
            )

        return slots_set + result

    def _procesar_especifica(
        self,
        pregunta: str,
        analisis: Dict[str, Any],
        asignaturas_memoria: List[Dict[str, Any]],
        ultimo_codigo: str,
        dispatcher: CollectingDispatcher
    ) -> List[Dict[Text, Any]]:

        nombre_asignatura = analisis.get("nombre_asignatura")
        atributo = analisis.get("atributo_solicitado") or "general"
        usar_contexto = analisis.get("usar_contexto", False)

        # Si es pregunta de seguimiento, usar el codigo del contexto
        if usar_contexto and ultimo_codigo:
            asignatura = buscar_por_codigo(ultimo_codigo, asignaturas_memoria)
            if not asignatura:
                dispatcher.utter_message(text="No recuerdo de que asignatura hablabamos. Dime el nombre.")
                return []
        elif nombre_asignatura:
            asignatura = buscar_en_memoria(nombre_asignatura, asignaturas_memoria)
            if not asignatura:
                dispatcher.utter_message(text=f"No encontre '{nombre_asignatura}' entre las asignaturas.")
                return []
        else:
            dispatcher.utter_message(text="No pude identificar la asignatura. Puedes especificarla?")
            return []

        respuesta = respuesta_template(asignatura, atributo) #esto tiene que estar procesada por el modelo ollama
        dispatcher.utter_message(text=respuesta)

        return [
            SlotSet("ultimo_codigo_consultado", asignatura["codigo"]),
            SlotSet("ultimo_nombre_asignatura", asignatura["nombre"])
        ]

    def _procesar_general(
        self,
        pregunta: str,
        analisis: Dict[str, Any],
        asignaturas_memoria: List[Dict[str, Any]],
        dispatcher: CollectingDispatcher
    ) -> List[Dict[Text, Any]]:

        filtros = extraer_filtros_heuristicas(pregunta)
        resultados = filtrar_en_memoria(asignaturas_memoria, **filtros)

        pregunta_lower = pregunta.lower()
        es_count = any(p in pregunta_lower for p in ["cuantas", "cuantos"])

        if es_count:
            respuesta = respuesta_template_count(len(resultados), pregunta)
            dispatcher.utter_message(text=respuesta)
            return []

        if not resultados:
            dispatcher.utter_message(text="No encontre asignaturas que cumplan esos criterios.")
            return []

        if len(resultados) <= 5:
            respuesta = respuesta_template_lista(resultados, pregunta)
            dispatcher.utter_message(text=respuesta)
            return []

        respuesta = respuesta_template_lista(resultados[:5], pregunta)
        dispatcher.utter_message(text=respuesta)
        dispatcher.utter_message(text=f"Hay {len(resultados) - 5} mas. Quieres verlas todas?")

        return [SlotSet("ultimos_resultados_asignaturas", resultados)]

