"""
Helpers transversales de seguimiento conversacional y contexto.

Antes vivían duplicados en `asignaturas/actions.py`, `profesores/actions.py` y
`fallback/actions.py`. Se centralizan aquí para evitar drift entre copias y
para reducir el tamaño del archivo `asignaturas/actions.py`, que se había
convertido de facto en una librería compartida.

Mantenemos sus firmas exactas para no romper a los importadores existentes.
"""

from typing import List, Optional, Tuple


def _contar_turnos_desde_slot(tracker, slot_name: str) -> int:
    """
    Cuenta turnos de usuario desde la última vez que se seteó el slot.
    Usado para determinar si el slot es reciente (seguimiento) o stale.
    Devuelve 999 si no hay registro del slot.
    """
    turnos = 0
    for event in reversed(tracker.events):
        if event.get("event") == "user":
            turnos += 1
        if event.get("event") == "slot" and event.get("name") == slot_name:
            return turnos
    return 999


def comprobar_titulacion(
    tracker, dispatcher
) -> Tuple[Optional[str], List]:
    """
    Comprueba si el usuario ya eligió titulación.
    Si no, pide que la elija con botones.

    Devuelve (codigo_titulacion, eventos_rasa).
    """
    # Import lazy para evitar el ciclo asignaturas ↔ shared.
    from ..asignaturas.actions import _construir_botones_titulaciones

    titulacion = tracker.get_slot("contexto_titulacion")

    if not titulacion:
        botones = _construir_botones_titulaciones()
        dispatcher.utter_message(
            text="Antes de consultar asignaturas, necesito saber tu titulación:",
            buttons=botones
        )
        return None, []

    return titulacion, []
