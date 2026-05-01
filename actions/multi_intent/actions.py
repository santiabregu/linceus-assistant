"""
Action para multi-intent: ejecuta varias sub-acciones y genera
UNA sola respuesta unificada con el LLM.

Cuando Rasa clasifica un mensaje como "cambiar_contexto+consulta_horario",
esta action:
1. Descompone el intent por "+"
2. Ejecuta la lógica de cada sub-intent (sin enviar mensajes)
3. Recoge los datos crudos de cada uno
4. Pasa todo al LLM para generar una respuesta única
"""

from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from ..shared.config import BotConfig
from ..shared.gemini_client import llamar_gemini as llamar_llm

# Importar lógica de cada dominio (funciones, no actions)
from ..contexto.actions import ActionCambiarContexto
from ..asignaturas.actions import (
    comprobar_titulacion, resolver_asignatura,
)
from ..asignaturas.text_to_sql import (
    generar_sql_listado, generar_sql_conteo,
    ejecutar_query, ejecutar_count,
)
from ..horarios.actions import (
    _detectar_curso, _detectar_grupo, _detectar_dia, _detectar_cuatrimestre,
    _query_horario,
    _datos_horario_a_texto,
    _respuesta_faltan_datos,
)


# ─── Ejecutores de sub-intents (devuelven datos, no envían mensajes) ────────

def _ejecutar_cambiar_contexto(tracker) -> dict:
    """Resuelve el cambio de contexto. Devuelve {codigo, nombre, eventos} o {error}."""
    handler = ActionCambiarContexto()
    mensaje = tracker.latest_message.get("text", "")

    nombre_titulacion = next(tracker.get_latest_entity_values("nombre_titulacion"), None)
    if not nombre_titulacion:
        codigo = handler._normalizar_titulacion(mensaje)
    else:
        codigo = handler._normalizar_titulacion(nombre_titulacion)

    if codigo:
        nombre = BotConfig.get_nombre_titulacion(codigo)
        return {
            "tipo": "cambiar_contexto",
            "codigo": codigo,
            "nombre": nombre,
            "eventos": [SlotSet("contexto_titulacion", codigo)],
            "texto": f"Titulacion cambiada a {nombre} ({codigo})",
        }
    return {
        "tipo": "cambiar_contexto",
        "error": "No se reconocio la titulacion",
        "texto": "No reconoci la titulacion.",
    }


def _ejecutar_consulta_especifica(tracker, titulacion: str) -> dict:
    """Resuelve una consulta específica. Devuelve {asignatura_dict} o {error}."""
    pregunta = tracker.latest_message.get("text", "")

    asignatura, nombre_usado = resolver_asignatura(
        pregunta, tracker, titulacion, usar_seguimiento=False
    )

    if asignatura:
        return {
            "tipo": "consulta_especifica",
            "datos": asignatura,
            "texto": f"Asignatura: {asignatura.get('nombre')}, "
                     f"Curso: {asignatura.get('curso')}, "
                     f"Creditos: {asignatura.get('creditos')}, "
                     f"Duracion: {asignatura.get('duracion')}, "
                     f"Tipo: {asignatura.get('tipologia')}",
        }
    return {
        "tipo": "consulta_especifica",
        "error": f"No encontre la asignatura '{nombre_usado or '?'}'",
        "texto": f"No encontre la asignatura '{nombre_usado or '?'}' en la titulacion.",
    }


def _ejecutar_consulta_listado(tracker, titulacion: str) -> dict:
    """Ejecuta un listado de asignaturas."""
    pregunta = tracker.latest_message.get("text", "")

    exito, sql, params = generar_sql_listado(pregunta, titulacion)
    if not exito:
        return {"tipo": "consulta_listado", "error": "No pude generar la consulta",
                "texto": "No pude generar la consulta de listado."}

    exito, resultados = ejecutar_query(sql, params)
    if exito and resultados:
        return {
            "tipo": "consulta_listado",
            "datos": resultados,
            "texto": f"{len(resultados)} asignaturas encontradas: "
                     + ", ".join(r.get("nombre", "?") for r in resultados[:10]),
        }
    return {"tipo": "consulta_listado", "error": "Sin resultados",
            "texto": "No encontre asignaturas con esos filtros."}


def _ejecutar_consulta_conteo(tracker, titulacion: str) -> dict:
    """Ejecuta un conteo de asignaturas."""
    pregunta = tracker.latest_message.get("text", "")

    exito, sql, params = generar_sql_conteo(pregunta, titulacion)
    if not exito:
        return {"tipo": "consulta_conteo", "error": "No pude generar la consulta",
                "texto": "No pude generar la consulta de conteo."}

    exito, count = ejecutar_count(sql, params)
    if exito:
        return {
            "tipo": "consulta_conteo",
            "datos": count,
            "texto": f"Total: {count} asignaturas",
        }
    return {"tipo": "consulta_conteo", "error": "Error en conteo",
            "texto": "No pude realizar el conteo."}


def _ejecutar_consulta_horario(tracker, titulacion: str) -> dict:
    """Ejecuta una consulta de horario personal (curso + grupo)."""
    mensaje = tracker.latest_message.get("text", "")

    curso = _detectar_curso(mensaje)
    grupo = _detectar_grupo(mensaje)
    dia = _detectar_dia(mensaje)
    cuatrimestre = _detectar_cuatrimestre(mensaje)

    if not curso or not grupo:
        return {
            "tipo": "consulta_horario",
            "datos": None,
            "texto": _respuesta_faltan_datos(titulacion, curso, grupo),
        }

    resultados = _query_horario(titulacion, curso, grupo, dia, cuatrimestre)
    datos_texto = _datos_horario_a_texto(resultados, titulacion, curso, grupo, dia)
    return {
        "tipo": "consulta_horario",
        "datos": datos_texto,
        "texto": datos_texto,
    }


# ─── Mapeo intent → ejecutor ────────────────────────────────────────────────

INTENT_EJECUTOR = {
    "cambiar_contexto_academico": _ejecutar_cambiar_contexto,
    "consulta_asignatura_especifica": _ejecutar_consulta_especifica,
    "consulta_asignaturas_listado": _ejecutar_consulta_listado,
    "consulta_asignaturas_conteo": _ejecutar_consulta_conteo,
    "consulta_horario": _ejecutar_consulta_horario,
}

# Intents que necesitan titulación como parámetro
NECESITA_TITULACION = {
    "consulta_asignatura_especifica",
    "consulta_asignaturas_listado",
    "consulta_asignaturas_conteo",
    "consulta_horario",
}


# ─── Generación de respuesta unificada ──────────────────────────────────────

def _generar_respuesta_unificada(pregunta: str, resultados: list) -> str:
    """Genera UNA respuesta natural combinando los resultados de todos los sub-intents."""
    datos_combinados = "\n\n".join(
        f"[{r['tipo']}]\n{r['texto']}" for r in resultados
    )

    prompt = f"""Eres Linceus, un asistente universitario de la ETSII (Universidad de Sevilla).
El usuario ha hecho una consulta que combina varias peticiones.
Responde con UN SOLO mensaje natural que integre toda la informacion.

PREGUNTA DEL USUARIO: "{pregunta}"

DATOS OBTENIDOS:
{datos_combinados}

REGLAS:
- Responde de forma natural, cercana y concisa en UN solo mensaje
- Integra toda la informacion de forma fluida, no la separes en bloques
- Si hubo un cambio de titulacion, mencionalo brevemente al principio
- Presenta los datos de forma organizada y legible
- Usa markdown para formatear (negritas, listas)
- No inventes datos que no esten proporcionados
- No menciones "base de datos" ni "datos obtenidos"
- No saludes (nada de "Hola!", "Buenos dias", etc.) — ve directo a la respuesta
- Si alguna sub-consulta fallo, mencionalo brevemente
- IMPORTANTE: Tu respuesta debe tener como MAXIMO 1500 caracteres. Si hay mucha informacion, resume lo mas relevante

Respuesta:"""

    try:
        respuesta = llamar_llm(
            prompt,
            timeout=120,
            options={"temperature": 0.3, "num_predict": 800, "num_ctx": 4096},
        )
        if respuesta:
            return respuesta.strip()
    except Exception as e:
        print(f"Error generando respuesta multi-intent: {e}")

    # Fallback: concatenar textos
    return "\n\n".join(r["texto"] for r in resultados)


# ─── Action principal ────────────────────────────────────────────────────────

class ActionMultiIntent(Action):
    def name(self) -> Text:
        return "action_multi_intent"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        intent_completo = tracker.latest_message.get("intent", {}).get("name", "")
        pregunta = tracker.latest_message.get("text", "")
        sub_intents = intent_completo.split("+")

        print(f"\n{'='*60}")
        print(f"MULTI-INTENT: {intent_completo}")
        print(f"  Sub-intents: {sub_intents}")
        print(f"  Pregunta: {pregunta}")
        print(f"{'='*60}")

        # Titulación actual (puede cambiar si el primer sub-intent es cambiar_contexto)
        titulacion = tracker.get_slot("contexto_titulacion")
        todos_eventos = []
        resultados = []

        for sub in sub_intents:
            sub = sub.strip()
            ejecutor = INTENT_EJECUTOR.get(sub)
            if not ejecutor:
                print(f"  Sub-intent desconocido: {sub}")
                continue

            # Ejecutar
            if sub == "cambiar_contexto_academico":
                resultado = ejecutor(tracker)
                if resultado.get("codigo"):
                    titulacion = resultado["codigo"]
                    todos_eventos.extend(resultado.get("eventos", []))
            elif sub in NECESITA_TITULACION:
                if not titulacion:
                    titulacion, _ = comprobar_titulacion(tracker, dispatcher)
                    if not titulacion:
                        return []
                resultado = ejecutor(tracker, titulacion)
            else:
                resultado = ejecutor(tracker)

            resultados.append(resultado)
            print(f"  [{sub}] → {resultado.get('tipo')}: "
                  f"{'OK' if not resultado.get('error') else resultado['error']}")

        # Generar respuesta unificada
        if resultados:
            respuesta = _generar_respuesta_unificada(pregunta, resultados)
            dispatcher.utter_message(text=respuesta)

        return todos_eventos
