"""Resolución genérica de afirmaciones / negaciones / "hay más".

Cualquier action que haga una pregunta al usuario deja un dict en el
slot `ultima_sugerencia` con la forma:

    {
        "action": <nombre_action_a_re_ejecutar>,
        "campo": <nombre_entidad_inyectada> (opcional),
        "valor": <valor_sugerido>,
        "pregunta_original": <texto> (opcional),
    }

Cuando el usuario dice "si"/"sí"/"ok" → ActionResolverAfirmacion lee ese slot
y re-ejecuta la action con el valor sugerido inyectado como entidad del
último mensaje (monkey-patch del tracker). Si no hay sugerencia, delega en
`action_mostrar_todas_asignaturas` cuando hay resultados paginados, o pide
aclaración.

"Hay más / no hay más" (ActionPreguntarHayMas / ActionResolverNoHayMas)
leen `ultima_action_ejecutada` para saber de qué dominio se habla (grupos
de una asignatura, más asignaturas, más profesores, etc.) y responden
acordemente.
"""

from typing import Any, Dict, List, Text
from copy import deepcopy

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet


def _inyectar_entidad(tracker: Tracker, campo: str, valor: str) -> Tracker:
    """Devuelve un tracker con una entidad sintética inyectada en el último
    mensaje. Así las actions existentes reciben el valor sugerido sin
    cambiar su código.
    """
    latest = deepcopy(tracker.latest_message or {})
    entities = list(latest.get("entities", []) or [])
    entities.append({
        "entity": campo,
        "value": valor,
        "start": 0,
        "end": len(valor),
        "extractor": "sugerencia",
    })
    latest["entities"] = entities
    # El texto también se sustituye para que resolver_asignatura y otros
    # pipelines que trabajan sobre el texto tengan material con el que
    # hacer fuzzy match.
    if valor:
        latest["text"] = valor

    # Shallow clone del tracker: rasa_sdk.Tracker no es mutable directamente,
    # pero sí podemos construir uno nuevo a partir del estado.
    nuevo = Tracker(
        sender_id=tracker.sender_id,
        slots=tracker.current_slot_values(),
        latest_message=latest,
        events=tracker.events,
        paused=tracker.is_paused(),
        followup_action=tracker.followup_action,
        active_loop=tracker.active_loop,
        latest_action_name=tracker.latest_action_name,
    )
    return nuevo


class ActionResolverAfirmacion(Action):
    """Maneja un 'si' del usuario en función del contexto previo."""

    def name(self) -> Text:
        return "action_resolver_afirmacion"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        sugerencia = tracker.get_slot("ultima_sugerencia")
        ultima_action = tracker.get_slot("ultima_action_ejecutada")
        resultados_pag = tracker.get_slot("ultimos_resultados_asignaturas")

        print(f"[resolver_afirmacion] sugerencia={sugerencia}, ultima_action={ultima_action}")

        # 1) Hay una sugerencia pendiente → reejecutar la action con el valor
        if sugerencia and isinstance(sugerencia, dict) and sugerencia.get("valor"):
            action_name = sugerencia.get("action")
            campo = sugerencia.get("campo") or "nombre_asignatura"
            valor = sugerencia["valor"]

            from ..actions import __all__ as _  # lazy: garantiza registro
            from .. import actions as acciones_pkg

            # Import mapeo: nombre Action → clase
            mapping = {
                "action_consulta_profesor": "ActionConsultaProfesor",
                "action_consulta_especifica": "ActionConsultaEspecifica",
                "action_consulta_listado": "ActionConsultaListado",
                "action_consulta_conteo": "ActionConsultaConteo",
                "action_consulta_horario": "ActionConsultaHorario",
            }
            clase_name = mapping.get(action_name)
            if not clase_name:
                dispatcher.utter_message(
                    text="Vale. ¿Puedes reformular la pregunta?"
                )
                return [SlotSet("ultima_sugerencia", None)]

            clase = getattr(acciones_pkg, clase_name, None)
            if clase is None:
                dispatcher.utter_message(text="Vale. ¿Puedes reformular la pregunta?")
                return [SlotSet("ultima_sugerencia", None)]

            tracker_inyectado = _inyectar_entidad(tracker, campo, valor)
            eventos = clase().run(dispatcher, tracker_inyectado, domain) or []
            # Limpiamos la sugerencia para que no se aplique dos veces
            eventos = list(eventos) + [SlotSet("ultima_sugerencia", None)]
            return eventos

        # 2) Hay lista paginada pendiente → mostrar todas
        if resultados_pag:
            from ..asignaturas.actions import ActionMostrarTodasAsignaturas
            return ActionMostrarTodasAsignaturas().run(dispatcher, tracker, domain)

        # 3) Sin contexto → mensaje neutro
        dispatcher.utter_message(
            text="¿Qué quieres que haga? Puedes preguntarme por asignaturas, "
                 "horarios o profesores."
        )
        return []


class ActionResolverNegacion(Action):
    """Maneja un 'no' del usuario limpiando sugerencias pendientes."""

    def name(self) -> Text:
        return "action_resolver_negacion"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        sugerencia = tracker.get_slot("ultima_sugerencia")
        resultados_pag = tracker.get_slot("ultimos_resultados_asignaturas")

        if sugerencia:
            dispatcher.utter_message(
                text="Vale. ¿Puedes darme más detalles (nombre completo, apellido, "
                     "código de asignatura…)?"
            )
            return [SlotSet("ultima_sugerencia", None)]

        if resultados_pag:
            dispatcher.utter_message(text="De acuerdo, no muestro el resto.")
            return [SlotSet("ultimos_resultados_asignaturas", None)]

        dispatcher.utter_message(
            text="Vale. Dime en qué puedo ayudarte."
        )
        return []


class ActionPreguntarHayMas(Action):
    """Responde a preguntas del tipo '¿hay más grupos?', '¿hay más asignaturas?'
    usando el contexto de la última action ejecutada.
    """

    def name(self) -> Text:
        return "action_preguntar_hay_mas"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        ultima = tracker.get_slot("ultima_action_ejecutada") or ""
        titulacion = tracker.get_slot("contexto_titulacion")

        # Contexto: última consulta fue de horario de asignatura concreta
        if ultima in ("consulta_especifica", "action_consulta_horario"):
            ultima_asig = tracker.get_slot("ultimo_nombre_asignatura")
            if ultima_asig and titulacion:
                from ..horarios.actions import _query_asignatura, _query_grupos_de_asignatura
                from ..shared.config import ALIAS_ASIGNATURAS
                from ..asignaturas.actions import normalizar_texto as _norm

                # Buscar alias correspondiente
                nombre_norm = _norm(ultima_asig)
                alias = None
                for a, n in ALIAS_ASIGNATURAS.items():
                    if n in nombre_norm or nombre_norm in n:
                        alias = a
                        break
                if alias:
                    nombre_real, grupos = _query_grupos_de_asignatura(titulacion, alias)
                    if grupos:
                        if len(grupos) <= 1:
                            dispatcher.utter_message(
                                text=f"**{nombre_real or ultima_asig}** solo tiene un grupo "
                                     f"({grupos[0]})."
                            )
                        else:
                            dispatcher.utter_message(
                                text=f"**{nombre_real or ultima_asig}** tiene estos grupos: "
                                     f"{', '.join(grupos)}."
                            )
                        return []
            dispatcher.utter_message(
                text="No tengo constancia de más grupos para esa asignatura."
            )
            return []

        # Contexto: listado paginado de asignaturas
        resultados_pag = tracker.get_slot("ultimos_resultados_asignaturas")
        if resultados_pag:
            dispatcher.utter_message(
                text=f"Sí, hay {len(resultados_pag)} resultados en total. "
                     f"Di **'ver todas'** para mostrarlos."
            )
            return []

        dispatcher.utter_message(
            text="¿Más de qué exactamente? Dime si hablamos de grupos, asignaturas o profesores."
        )
        return []
