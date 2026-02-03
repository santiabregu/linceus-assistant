# Actions principales del chatbot Linceus
# Este archivo importa y expone todas las actions de los diferentes módulos

from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from .llm_interpreter import interpretar_con_llama


# Importar conexión a BD
from .db import db_client

# Importar actions de asignaturas
from .asignaturas import (
    ActionConsultarAsignatura,
    ActionPreguntaSeguimiento,
    ActionConsultarAsignaturasFiltradas,
    ActionMostrarTodas,
)

# Importar actions de contexto académico
from .contexto import (
    ActionCambiarContexto,
    ActionConsultarContexto,
)

# =============================================================================
# ACTIONS GENERALES
# =============================================================================

class ActionTestSupabase(Action):
    """Action de prueba para verificar conexión con la base de datos"""
    
    def name(self) -> Text:
        return "action_test_supabase"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        if db_client is None:
            dispatcher.utter_message(text="Error: No se pudo configurar la conexión a la base de datos")
            return []
        
        if db_client.test_connection():
            dispatcher.utter_message(text="Conexión con la base de datos exitosa")
        else:
            dispatcher.utter_message(text="Error al conectar con la base de datos")
        return []

class ActionLLMPreprocess(Action):

    def name(self) -> Text:
        return "action_llm_preprocess"

    def run(self, dispatcher, tracker, domain):
        try:
            mensaje = tracker.latest_message.get("text", "")

            llm_data = interpretar_con_llama(mensaje)

            eventos = []

            # Verificar que llm_data sea un diccionario válido
            if not isinstance(llm_data, dict):
                print(f"LLM devolvió tipo inválido: {type(llm_data)}")
                return []

            nombre = llm_data.get("nombre_asignatura")
            if nombre and isinstance(nombre, str):
                eventos.append(SlotSet("llm_nombre_asignatura", nombre))

            atributo = llm_data.get("atributo_asignatura")
            if atributo and isinstance(atributo, str):
                eventos.append(SlotSet("llm_atributo_asignatura", atributo))

            intent = llm_data.get("intent")
            if intent and isinstance(intent, str):
                eventos.append(SlotSet("llm_intent", intent))

            return eventos
        except Exception as e:
            print(f"Error en ActionLLMPreprocess: {e}")
            return []


# =============================================================================
# EXPORTAR TODAS LAS ACTIONS
# =============================================================================
# Rasa detecta automáticamente las clases que heredan de Action,
# pero las importamos explícitamente para claridad

__all__ = [
    'ActionTestSupabase',
    'ActionConsultarAsignatura', 
    'ActionPreguntaSeguimiento',
    'ActionConsultarAsignaturasFiltradas',
    'ActionCambiarContexto',
    'ActionConsultarContexto',
]
