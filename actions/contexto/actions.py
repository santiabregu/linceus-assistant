# Actions relacionadas con el contexto académico (centro/titulación)
# v2.1.0 - Soporte para múltiples carreras con consulta de titulaciones

from typing import Any, Text, Dict, List
from rapidfuzz import fuzz, process

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from ..shared.config import BotConfig
from ..shared.db import db_client


class ActionCambiarContexto(Action):
    """
    Permite cambiar el centro o titulación del contexto académico.
    Por ahora solo soporta cambio de titulación dentro de ETSII.
    """
    
    # Mapeo de texto a códigos de titulación (fuzzy matching) segun db
    TITULACION_MAP = {
        'ingenieria del software': 'GII-IS',
        'ingeniería del software': 'GII-IS',
        'ing del software': 'GII-IS',
        'ing software': 'GII-IS',
        'software': 'GII-IS',
        'is': 'GII-IS',
        'gii-is': 'GII-IS',
        'tecnologias informaticas': 'GII-TI',
        'tecnologías informáticas': 'GII-TI',
        'tecnologias': 'GII-TI',
        'tecnologías': 'GII-TI',
        'ti': 'GII-TI',
        'gii-ti': 'GII-TI',
        'ingenieria de computadores': 'GII-IC',
        'ingeniería de computadores': 'GII-IC',
        'ing de computadores': 'GII-IC',
        'ing computadores': 'GII-IC',
        'computadores': 'GII-IC',
        'ic': 'GII-IC',
        'gii-ic': 'GII-IC',
    }
    
    def name(self) -> Text:
        return "action_cambiar_contexto"
    
    # Tokens discriminantes: el input debe compartir al menos uno para
    # considerarse una titulación. Evita que "Ingeniería de la Salud" haga
    # match con "Ingeniería del Software" solo por "ingeniería".
    _TOKENS_TITULACION = {
        'software', 'computadores', 'tecnologias', 'tecnologías',
        'informaticas', 'informáticas',
        'is', 'ti', 'ic', 'gii-is', 'gii-ti', 'gii-ic',
    }

    def _normalizar_titulacion(self, texto: str) -> str:
        """Intenta encontrar el código de titulación a partir del texto.

        R3: cutoff endurecido a 85 + filtro por token discriminante. "Ingeniería
        de la Salud" ya no hace match con GII-IS."""
        if not texto:
            return None

        texto_lower = texto.lower().strip()

        # Match exacto
        if texto_lower in self.TITULACION_MAP:
            return self.TITULACION_MAP[texto_lower]

        # Guard: el texto debe contener al menos un token discriminante
        # (software, computadores, tecnologias, is/ti/ic…). Si no, no es
        # una titulación conocida.
        tokens_input = set(texto_lower.split())
        if not (tokens_input & self._TOKENS_TITULACION):
            return None

        # Fuzzy matching (cutoff 85 — antes era 70, demasiado permisivo)
        resultado = process.extractOne(
            texto_lower,
            list(self.TITULACION_MAP.keys()),
            scorer=fuzz.WRatio,
            score_cutoff=85
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


class ActionResetContexto(Action):
    """
    Reset suave del contexto: limpia slots de seguimiento y vuelve a mostrar
    los botones de elección de titulación. Disparado por `reset_contexto`
    ("reset", "cambiar titulación", "empezar de cero", etc.).

    Mantiene la sesión de Rasa pero deja el bot como recién iniciado: el
    siguiente click selecciona la titulación nueva sin ningún slot de la
    conversación previa interfiriendo.
    """

    SLOTS_A_LIMPIAR = (
        "contexto_titulacion",
        "ultimo_codigo_consultado",
        "ultimo_nombre_asignatura",
        "ultimos_resultados_asignaturas",
        "asignaturas_memoria",
        "ultima_action_ejecutada",
        "ultimo_curso_consultado",
        "ultimo_grupo_consultado",
        "ultimo_profesor_consultado",
        "ultima_sugerencia",
    )

    def name(self) -> Text:
        return "action_reset_contexto"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # Importación local para evitar el ciclo asignaturas↔contexto.
        from ..asignaturas.actions import _construir_botones_titulaciones

        botones = _construir_botones_titulaciones()
        dispatcher.utter_message(
            text=("Empezamos de cero. Elige la titulación que quieres "
                  "consultar:"),
            buttons=botones,
        )
        return [SlotSet(slot, None) for slot in self.SLOTS_A_LIMPIAR]


class ActionConsultaTitulaciones(Action):
    """
    Consulta las titulaciones disponibles en la base de datos.
    Permite al usuario preguntar qué carreras hay en el centro.
    """
    
    def name(self) -> Text:
        return "action_consulta_titulaciones"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Consultar titulaciones de la base de datos
        sql = """
            SELECT t.codigo, t.nombre, c.nombre as centro_nombre,
                   (SELECT COUNT(*) FROM asignaturas WHERE titulacion_id = t.id AND activa = true) as num_asignaturas
            FROM titulaciones t
            JOIN centros c ON t.centro_id = c.id
            WHERE t.activa = true
            ORDER BY t.nombre
        """
        
        try:
            conn = db_client.get_connection()
            if not conn:
                dispatcher.utter_message(
                    text="No pude conectar con la base de datos. Inténtalo de nuevo."
                )
                return []
            
            cursor = conn.cursor()
            cursor.execute(sql)
            columnas = [desc[0] for desc in cursor.description]
            filas = cursor.fetchall()
            cursor.close()
            conn.close()
            
            if not filas:
                dispatcher.utter_message(
                    text="No encontré titulaciones activas en la base de datos."
                )
                return []
            
            # Formatear respuesta
            titulaciones = [dict(zip(columnas, fila)) for fila in filas]
            
            # Agrupar por centro
            centros = {}
            for t in titulaciones:
                centro = t['centro_nombre']
                if centro not in centros:
                    centros[centro] = []
                centros[centro].append(t)
            
            # Construir mensaje
            mensaje = "📚 **Titulaciones disponibles:**\n\n"
            
            for centro, tits in centros.items():
                mensaje += f"**{centro}:**\n"
                for t in tits:
                    mensaje += f"• **{t['nombre']}** ({t['codigo']}) - {t['num_asignaturas']} asignaturas\n"
                mensaje += "\n"
            
            mensaje += "Dime cuál te interesa para consultar sus asignaturas."
            
            dispatcher.utter_message(text=mensaje)
            
        except Exception as e:
            print(f"Error consultando titulaciones: {e}")
            dispatcher.utter_message(
                text="Hubo un problema al consultar las titulaciones. Inténtalo de nuevo."
            )
        
        return []
