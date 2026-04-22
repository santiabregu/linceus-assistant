"""
Smart Fallback: cuando Rasa no clasifica un intent, Gemini analiza la pregunta
y decide si puede resolverla con los actions disponibles o responde directamente.
"""

import json
import re
from typing import Any, Text, Dict, List, Optional
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from ..shared.gemini_client import llamar_gemini
from ..shared.db import db_client
from ..shared.config import BotConfig, ALIAS_ASIGNATURAS
from ..asignaturas.actions import comprobar_titulacion


# ─── Heuristicas de continuacion / memoria ───────────────────────────────────

# Maximo numero de turnos de usuario tras los que un slot se considera "stale".
_TURNOS_SLOT_RECIENTE = 3

# Frases de continuacion sin mencionar el sujeto: "dime la de todos los grupos",
# "y los otros grupos?", "y del grupo 3?", "dame la de los demas".
# Si hay slot reciente de asignatura -> heredar y quitar filtro de grupo.
_RE_CONTINUACION_TODOS_GRUPOS = re.compile(
    r"\b(todos\s+los\s+grupos|los\s+dem[aá]s\s+grupos|los\s+otros\s+grupos|"
    r"de\s+los\s+dem[aá]s|otros\s+grupos|el\s+resto\s+de\s+grupos)\b",
    re.IGNORECASE,
)


def _contar_turnos_desde_slot(tracker, slot_name: str) -> int:
    """
    Cuenta turnos de usuario desde la ultima vez que se seteo el slot.
    Devuelve 999 si no hay registro del slot.
    """
    turnos = 0
    for event in reversed(tracker.events):
        if event.get("event") == "user":
            turnos += 1
        if event.get("event") == "slot" and event.get("name") == slot_name:
            return turnos
    return 999


def _ultimos_intercambios(tracker, n: int = 3) -> list:
    """
    Devuelve los ultimos N intercambios (user, bot) en orden cronologico.
    Cada elemento: {"user": "...", "bot": "..."}.
    """
    pares = []
    user_msg = None
    for event in tracker.events:
        if event.get("event") == "user":
            user_msg = event.get("text") or ""
        elif event.get("event") == "bot" and user_msg is not None:
            pares.append({"user": user_msg, "bot": event.get("text") or ""})
            user_msg = None
    return pares[-n:] if n else pares




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

Intercambios recientes (mas antiguo primero):
{historial}

Actions disponibles:
{actions}

REGLAS DE CONTINUACION (IMPORTANTE):
- Si la pregunta del usuario es corta, pronominal o referencial (ej: "y del otro grupo?",
  "dime la de los demas", "dame ese", "mas info", "y de tercero?"), esta hablando de la
  **ultima asignatura consultada**. Usa ese nombre como "nombre_asignatura".
- Si pide informacion que ya hemos dado pero con variantes ("todos los grupos",
  "otro dia", "otro cuatrimestre"), mantener "nombre_asignatura" del contexto y
  ajustar curso/grupo segun pida.
- Si no hay "ultima asignatura consultada" (valor "ninguna") no asumas nada.

METAPREGUNTAS SOBRE LA CONVERSACION:
- Si el usuario pregunta por lo que ya ha dicho o se le ha respondido
  (ej: "que te dije antes", "recuerdas lo que pregunte", "de que hemos hablado",
  "mi pregunta anterior"), action = "NINGUNO" y en "respuesta_directa" resume
  de forma natural el bloque "Intercambios recientes". No inventes preguntas
  que no esten ahi. Si no hay intercambios previos, dilo.

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
    titulacion = tracker.get_slot("contexto_titulacion")

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
    titulacion = tracker.get_slot("contexto_titulacion")

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
                          COALESCE(au.codigo, '') AS aula, gc.codigo as grupo
                   FROM horarios h
                   JOIN grupos_clase gc ON h.grupo_id = gc.id
                   JOIN asignaturas a ON gc.asignatura_id = a.id
                   JOIN titulaciones t ON a.titulacion_id = t.id
                   LEFT JOIN aulas au ON au.id = h.aula_id
                   WHERE t.codigo = %s
                   AND (a.nombre_normalizado ILIKE %s OR a.nombre ILIKE %s)
                   AND h.activo = true
                   ORDER BY gc.codigo, h.dia_semana, h.hora_inicio
                   LIMIT 40""",
                (titulacion, f"%{nombre_expandido}%", f"%{nombre_expandido}%")
            )
        elif curso:
            cur.execute(
                """SELECT a.nombre, h.dia_semana, h.hora_inicio, h.hora_fin,
                          COALESCE(au.codigo, '') AS aula, gc.codigo as grupo
                   FROM horarios h
                   JOIN grupos_clase gc ON h.grupo_id = gc.id
                   JOIN asignaturas a ON gc.asignatura_id = a.id
                   JOIN titulaciones t ON a.titulacion_id = t.id
                   LEFT JOIN aulas au ON au.id = h.aula_id
                   WHERE t.codigo = %s AND a.curso = %s AND h.activo = true
                   ORDER BY gc.codigo, h.dia_semana, h.hora_inicio
                   LIMIT 40""",
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

        titulacion = tracker.get_slot("contexto_titulacion") or "no definida"
        ultima_asignatura = tracker.get_slot("ultimo_nombre_asignatura") or "ninguna"

        print(f"🧠 Smart Fallback: analizando '{pregunta}'")

        # ── 1. Continuacion "todos los grupos" + slot reciente de asignatura ─
        slot_asig = tracker.get_slot("ultimo_nombre_asignatura")
        turnos_asig = _contar_turnos_desde_slot(tracker, "ultimo_nombre_asignatura")
        if (slot_asig and turnos_asig <= _TURNOS_SLOT_RECIENTE
                and _RE_CONTINUACION_TODOS_GRUPOS.search(pregunta)):
            print(f"   → Continuacion detectada: heredando asignatura '{slot_asig}' "
                  f"({turnos_asig} turnos), sin filtro de grupo")
            titulacion_ok, _ev = comprobar_titulacion(tracker, dispatcher)
            if not titulacion_ok:
                return []
            respuesta_cont = _ejecutar_consulta_horario(
                nombre_asignatura=slot_asig,
                curso=None, grupo=None,
                pregunta=pregunta, tracker=tracker,
            )
            if respuesta_cont:
                dispatcher.utter_message(text=respuesta_cont)
                return [SlotSet("ultimo_nombre_asignatura", slot_asig)]
            # si falla, seguimos al flujo normal para que el LLM intente

        # Paso 1: Clasificar con Gemini
        pares_recientes = _ultimos_intercambios(tracker, n=3)
        # Excluimos el turno actual (la propia pregunta); nos quedamos con los anteriores
        pares_previos = pares_recientes[:-1] if pares_recientes else pares_recientes
        if pares_previos:
            historial_txt = "\n".join(
                f"  Usuario: {p['user'][:200]}\n  Bot: {(p['bot'] or '')[:200]}"
                for p in pares_previos
            )
        else:
            historial_txt = "  (sin intercambios previos en esta sesion)"

        prompt = PROMPT_CLASIFICAR.format(
            pregunta=pregunta,
            titulacion=titulacion,
            ultima_asignatura=ultima_asignatura,
            historial=historial_txt,
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

        # Acciones que requieren titulación
        if action in ("BUSCAR_ASIGNATURA", "BUSCAR_HORARIO"):
            titulacion, _ = comprobar_titulacion(tracker, dispatcher)
            if not titulacion:
                return []

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
