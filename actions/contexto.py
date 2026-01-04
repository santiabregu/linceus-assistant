# Actions relacionadas con el contexto académico (centro/titulación)
# v1.4.0 - Soporte para múltiples carreras con defaults

from typing import Any, Text, Dict, List
from rapidfuzz import fuzz, process

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from .config import BotConfig


class ActionCambiarContexto(Action):
    """
    Permite cambiar el centro o titulación del contexto académico.
    Por ahora solo soporta cambio de titulación dentro de ETSII.
    """
    
    # Mapeo de texto a códigos de titulación (fuzzy matching)
    TITULACION_MAP = {
        'ingenieria del software': 'GII-IS',
        'software': 'GII-IS',
        'is': 'GII-IS',
        'gii-is': 'GII-IS',
        'tecnologias informaticas': 'GII-TI',
        'tecnologias': 'GII-TI',
        'ti': 'GII-TI',
        'gii-ti': 'GII-TI',
        'ingenieria de computadores': 'GII-IC',
        'computadores': 'GII-IC',
        'ic': 'GII-IC',
        'gii-ic': 'GII-IC',
        'sistemas de informacion': 'GII-SI',
        'sistemas': 'GII-SI',
        'si': 'GII-SI',
        'gii-si': 'GII-SI',
    }
    
    def name(self) -> Text:
        return "action_cambiar_contexto"
    
    def _normalizar_titulacion(self, texto: str) -> str:
        """Intenta encontrar el código de titulación a partir del texto"""
        if not texto:
            return None
        
        texto_lower = texto.lower().strip()
        
        # Match exacto
        if texto_lower in self.TITULACION_MAP:
            return self.TITULACION_MAP[texto_lower]
        
        # Fuzzy matching
        resultado = process.extractOne(
            texto_lower,
            list(self.TITULACION_MAP.keys()),
            scorer=fuzz.WRatio,
            score_cutoff=70
        )
        
        if resultado:
            return self.TITULACION_MAP[resultado[0]]
        
        return None
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Obtener entidad de titulación del mensaje
        nombre_titulacion = next(tracker.get_latest_entity_values("nombre_titulacion"), None)
        
        if not nombre_titulacion:
            # Intentar extraer del mensaje
            mensaje = tracker.latest_message.get('text', '')
            codigo = self._normalizar_titulacion(mensaje)
        else:
            codigo = self._normalizar_titulacion(nombre_titulacion)
        
        if codigo:
            nombre_completo = BotConfig.get_nombre_titulacion(codigo)
            dispatcher.utter_message(
                text=f"✅ Cambiado a: {nombre_completo}\n\n"
                     "Ahora las consultas de asignaturas serán de esta titulación."
            )
            return [SlotSet("contexto_titulacion", codigo)]
        else:
            # Mostrar opciones disponibles
            opciones = "\n".join([
                f"• Ingeniería del Software (IS)",
                f"• Tecnologías Informáticas (TI)", 
                f"• Ingeniería de Computadores (IC)",
                f"• Sistemas de Información (SI)",
            ])
            dispatcher.utter_message(
                text=f"No reconocí la titulación. Las opciones disponibles son:\n\n{opciones}\n\n"
                     "Dime cuál quieres consultar."
            )
            return []


class ActionConsultarContexto(Action):
    """Muestra el contexto académico actual (centro y titulación)"""
    
    def name(self) -> Text:
        return "action_consultar_contexto"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Leer slots o usar defaults
        centro = tracker.get_slot("contexto_centro")
        titulacion = tracker.get_slot("contexto_titulacion")
        
        contexto = BotConfig.get_contexto_actual(centro, titulacion)
        
        dispatcher.utter_message(
            text=f"📍 **Contexto actual:**\n"
                 f"• Centro: {contexto['centro_nombre']}\n"
                 f"• Titulación: {contexto['titulacion_nombre']}\n\n"
                 "Si quieres cambiar de carrera, dime cuál te interesa."
        )
        
        return []
