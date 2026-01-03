# Actions principales del chatbot Linceus
# Este archivo importa y expone todas las actions de los diferentes módulos

from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

# Importar conexión a BD
from .db import db_client

# Importar actions de asignaturas
from .asignaturas import (
    ActionConsultarAsignatura,
    ActionPreguntaSeguimiento,
    ActionConsultarAsignaturasFiltradas,
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


# =============================================================================
# EXPORTAR TODAS LAS ACTIONS
# =============================================================================
# Rasa detecta automáticamente las clases que heredan de Action,
# pero las importamos explícitamente para claridad

__all__ = [
    'ActionTestSupabase',
    'ActionConsultarAsignatura', 
    'ActionPreguntaSeguimiento',
    'ActionPedirInfoAsignatura',
]
