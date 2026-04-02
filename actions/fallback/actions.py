"""
Smart Fallback: cuando Rasa no clasifica un intent, Gemini analiza la pregunta
y decide si puede resolverla con los actions disponibles o responde directamente.
"""

import json
from typing import Any, Text, Dict, List, Optional
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from ..shared.gemini_client import llamar_gemini
from ..shared.db import db_client
from ..shared.config import BotConfig, ALIAS_ASIGNATURAS


# Actions disponibles que el fallback puede invocar
ACTIONS_DISPONIBLES = """
1. BUSCAR_ASIGNATURA: Busca info sobre una asignatura (creditos, descripcion, profesorado, evaluacion, etc.)
   Necesita: nombre_asignatura
2. BUSCAR_HORARIO: Busca horarios de un curso/grupo o de una asignatura
   Necesita: nombre_asignatura O (curso + grupo)
3. BUSCAR_PROFESOR: Busca info de contacto de un profesor (email, despacho, tutorias)
   Necesita: nombre_profesor
4. NINGUNO: La pregunta es charla general, saludo, o no tiene que ver con la universidad
"""

PROMPT_CLASIFICAR = """Eres Linceus, asistente de la ETSII (Universidad de Sevilla).

Un usuario ha hecho una pregunta que no se ha podido clasificar automaticamente.
Analiza la pregunta y decide que hacer.

Pregunta del usuario: "{pregunta}"

Contexto actual del usuario:
- Titulacion: {titulacion}
- Ultima asignatura consultada: {ultima_asignatura}

Actions disponibles:
{actions}

Responde SOLO con un JSON valido (sin markdown, sin ```):
{{
  "action": "BUSCAR_ASIGNATURA" | "BUSCAR_HORARIO" | "BUSCAR_PROFESOR" | "NINGUNO",
  "parametros": {{
    "nombre_asignatura": "nombre o abreviatura si aplica",
    "nombre_profesor": "nombre si aplica",
    "curso": "numero si aplica",
    "grupo": "numero si aplica"
  }},
  "respuesta_directa": "si action es NINGUNO, responde aqui de forma breve y amigable como Linceus. Maximo 2 frases."
}}"""


def _ejecutar_consulta_asignatura(nombre_asignatura: str, pregunta: str,
                                   tracker: Tracker) -> Optional[str]:
    """Busca info de una asignatura en BD + RAG y genera respuesta."""
    titulacion = BotConfig.get_titulacion_activa(tracker)

    # Expandir alias
    nombre_lower = nombre_asignatura.lower().strip()
    nombre_expandido = ALIAS_ASIGNATURAS.get(nombre_lower, nombre_asignatura)

    conn = db_client.get_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        # Buscar la asignatura en BD
        cur.execute(
            """SELECT a.codigo, a.nombre, a.creditos, a.tipologia, a.curso, a.duracion
               FROM asignaturas a
               JOIN titulaciones t ON a.titulacion_id = t.id
               WHERE t.codigo = %s
               AND (a.nombre_normalizado ILIKE %s OR a.nombre ILIKE %s)
               LIMIT 1""",
            (titulacion, f"%{nombre_expandido}%", f"%{nombre_expandido}%")
        )
        row = cur.fetchone()
        if not row:
            return None

        codigo, nombre, creditos, tipologia, curso, duracion = row
        info_basica = (f"Asignatura: {nombre} ({codigo}), "
                      f"{creditos} creditos, {tipologia}, "
                      f"curso {curso}, {duracion}")

        # Intentar RAG para mas detalle
        rag_contexto = ""
        try:
            from rag.buscar import buscar_en_plan_docente
            chunks = buscar_en_plan_docente(pregunta, codigo, limite=4)
            if chunks:
                rag_contexto = "\n\nInformacion del plan docente:\n"
                for c in chunks:
                    rag_contexto += f"- [{c.get('seccion', '')}] {c.get('contenido', '')}\n"
        except Exception:
            pass

        # Generar respuesta con Gemini
        prompt_respuesta = f"""Eres Linceus, asistente de la ETSII. El usuario pregunto: "{pregunta}"

Datos encontrados:
{info_basica}
{rag_contexto}

Responde de forma natural y concisa a la pregunta del usuario usando los datos.
No saludes. Ve directo a la respuesta. Maximo 3-4 frases."""

        return llamar_gemini(prompt_respuesta, options={"num_predict": 300, "temperature": 0.3})

    except Exception as e:
        print(f"Error en consulta fallback asignatura: {e}")
        return None
    finally:
        conn.close()


def _ejecutar_consulta_horario(nombre_asignatura: str = None, curso: str = None,
                                grupo: str = None, pregunta: str = "",
                                tracker: Tracker = None) -> Optional[str]:
    """Busca horarios en BD y genera respuesta."""
    titulacion = BotConfig.get_titulacion_activa(tracker)

    conn = db_client.get_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()

        if nombre_asignatura:
            nombre_lower = nombre_asignatura.lower().strip()
            nombre_expandido = ALIAS_ASIGNATURAS.get(nombre_lower, nombre_asignatura)

            cur.execute(
                """SELECT a.nombre, h.dia_semana, h.hora_inicio, h.hora_fin,
                          h.aula_codigo, gc.codigo as grupo
                   FROM horarios h
                   JOIN grupos_clase gc ON h.grupo_clase_id = gc.id
                   JOIN asignaturas a ON gc.asignatura_id = a.id
                   JOIN titulaciones t ON a.titulacion_id = t.id
                   WHERE t.codigo = %s
                   AND (a.nombre_normalizado ILIKE %s OR a.nombre ILIKE %s)
                   ORDER BY h.dia_semana, h.hora_inicio
                   LIMIT 20""",
                (titulacion, f"%{nombre_expandido}%", f"%{nombre_expandido}%")
            )
        elif curso:
            cur.execute(
                """SELECT a.nombre, h.dia_semana, h.hora_inicio, h.hora_fin,
                          h.aula_codigo, gc.codigo as grupo
                   FROM horarios h
                   JOIN grupos_clase gc ON h.grupo_clase_id = gc.id
                   JOIN asignaturas a ON gc.asignatura_id = a.id
                   JOIN titulaciones t ON a.titulacion_id = t.id
                   WHERE t.codigo = %s AND a.curso = %s
                   ORDER BY h.dia_semana, h.hora_inicio
                   LIMIT 30""",
                (titulacion, int(curso))
            )
        else:
            return None

        rows = cur.fetchall()
        if not rows:
            return None

        datos = "\n".join(
            f"- {r[0]}: {r[1]} de {r[2]} a {r[3]} en aula {r[4]} (grupo {r[5]})"
            for r in rows
        )

        prompt_respuesta = f"""Eres Linceus, asistente de la ETSII. El usuario pregunto: "{pregunta}"

Horarios encontrados:
{datos}

Responde de forma natural y concisa. No saludes. Maximo 3-4 frases."""

        return llamar_gemini(prompt_respuesta, options={"num_predict": 300, "temperature": 0.3})

    except Exception as e:
        print(f"Error en consulta fallback horario: {e}")
        return None
    finally:
        conn.close()


def _ejecutar_consulta_profesor(nombre_profesor: str, pregunta: str) -> Optional[str]:
    """Busca info de un profesor en BD y genera respuesta."""
    conn = db_client.get_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT nombre, apellidos, email, despacho, telefono,
                      categoria_academica, enlace_perfil, d.nombre as departamento
               FROM profesores p
               LEFT JOIN departamentos d ON p.departamento_id = d.id
               WHERE p.nombre_normalizado ILIKE %s
               OR p.nombre ILIKE %s
               OR p.apellidos ILIKE %s
               LIMIT 3""",
            (f"%{nombre_profesor}%", f"%{nombre_profesor}%", f"%{nombre_profesor}%")
        )
        rows = cur.fetchall()
        if not rows:
            return None

        datos = "\n".join(
            f"- {r[0]} {r[1] or ''}: email={r[2]}, despacho={r[3]}, "
            f"tel={r[4]}, categoria={r[5]}, depto={r[7]}"
            for r in rows
        )

        prompt_respuesta = f"""Eres Linceus, asistente de la ETSII. El usuario pregunto: "{pregunta}"

Profesores encontrados:
{datos}

Responde de forma natural y concisa. No saludes. Maximo 3-4 frases."""

        return llamar_gemini(prompt_respuesta, options={"num_predict": 300, "temperature": 0.3})

    except Exception as e:
        print(f"Error en consulta fallback profesor: {e}")
        return None
    finally:
        conn.close()


class ActionSmartFallback(Action):
    def name(self) -> Text:
        return "action_smart_fallback"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        pregunta = tracker.latest_message.get("text", "")
        if not pregunta.strip():
            dispatcher.utter_message(text="No he entendido tu mensaje. Puedes reformularlo?")
            return []

        titulacion = BotConfig.get_titulacion_activa(tracker)
        ultima_asignatura = tracker.get_slot("ultimo_nombre_asignatura") or "ninguna"

        print(f"🧠 Smart Fallback: analizando '{pregunta}'")

        # Paso 1: Clasificar con Gemini
        prompt = PROMPT_CLASIFICAR.format(
            pregunta=pregunta,
            titulacion=titulacion or "no definida",
            ultima_asignatura=ultima_asignatura,
            actions=ACTIONS_DISPONIBLES,
        )

        respuesta_json = llamar_gemini(prompt, options={"num_predict": 200, "temperature": 0.0})

        if not respuesta_json:
            dispatcher.utter_message(
                text="No he podido procesar tu pregunta. Prueba a reformularla o escribe 'ayuda'."
            )
            return []

        # Parsear JSON
        try:
            # Limpiar posibles artefactos
            clean = respuesta_json.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            decision = json.loads(clean.strip())
        except (json.JSONDecodeError, Exception) as e:
            print(f"  Error parseando JSON del fallback: {e}\n  Respuesta: {respuesta_json}")
            dispatcher.utter_message(
                text="No he podido procesar tu pregunta. Prueba a reformularla o escribe 'ayuda'."
            )
            return []

        action = decision.get("action", "NINGUNO")
        params = decision.get("parametros", {})
        respuesta_directa = decision.get("respuesta_directa", "")

        print(f"  Clasificado como: {action}, params: {params}")

        # Paso 2: Ejecutar segun la decision
        respuesta = None

        if action == "BUSCAR_ASIGNATURA" and params.get("nombre_asignatura"):
            respuesta = _ejecutar_consulta_asignatura(
                params["nombre_asignatura"], pregunta, tracker
            )

        elif action == "BUSCAR_HORARIO":
            respuesta = _ejecutar_consulta_horario(
                nombre_asignatura=params.get("nombre_asignatura"),
                curso=params.get("curso"),
                grupo=params.get("grupo"),
                pregunta=pregunta,
                tracker=tracker,
            )

        elif action == "BUSCAR_PROFESOR" and params.get("nombre_profesor"):
            respuesta = _ejecutar_consulta_profesor(
                params["nombre_profesor"], pregunta
            )

        elif action == "NINGUNO" and respuesta_directa:
            respuesta = respuesta_directa

        # Paso 3: Responder
        if respuesta:
            dispatcher.utter_message(text=respuesta)
        else:
            dispatcher.utter_message(
                text="No he encontrado informacion sobre eso. Puedo ayudarte con "
                     "**asignaturas**, **horarios** y **profesores** de la ETSII. "
                     "Escribe 'ayuda' para ver ejemplos."
            )

        return []
