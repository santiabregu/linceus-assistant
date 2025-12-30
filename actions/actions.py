# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action: 
# https://rasa.com/docs/rasa/custom-actions

import os
import psycopg2
from typing import Any, Text, Dict, List
from dotenv import load_dotenv

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

# Cargar variables de entorno
load_dotenv()

# Configuración de base de datos
class DatabaseConnection:
    def __init__(self):
        self.host = os.getenv("DB_HOST")
        self.port = os.getenv("DB_PORT")
        self.database = os.getenv("DB_DATABASE")
        self.user = os.getenv("DB_USER")
        self.password = os.getenv("DB_PASSWORD")
        
        if not all([self.host, self.port, self.database, self.user, self.password]):
            raise ValueError("Todas las variables de BD deben estar configuradas en .env")
    
    def get_connection(self):
        """Obtiene una conexión a la base de datos"""
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            return conn
        except Exception as e:
            print(f"Error conectando con la base de datos: {e}")
            return None
    
    def test_connection(self):
        """Prueba la conexión con la base de datos"""
        conn = self.get_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                conn.close()
                return True
            except Exception as e:
                print(f"Error en test de conexión: {e}")
                if conn:
                    conn.close()
                return False
        return False

# Instancia global de conexión
try:
    db_client = DatabaseConnection()
    print("Configuración de base de datos cargada correctamente")
except Exception as e:
    print(f"Error configurando base de datos: {e}")
    db_client = None


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


class ActionConsultarAsignatura(Action):
    """Action para consultar información de una asignatura por código y atributo específico"""
    
    # Mapeo de lenguaje natural a campos de BD
    ATRIBUTO_MAP = {
        'creditos': 'creditos',
        'créditos': 'creditos',
        'curso': 'curso',
        'año': 'curso',
        'dura': 'duracion',
        'duración': 'duracion',
        'duracion': 'duracion',
        'anual': 'duracion',
        'cuatrimestre': 'duracion',
        'tipo': 'tipologia',
        'tipología': 'tipologia',
        'obligatoria': 'tipologia',
        'optativa': 'es_optativa',
        'formación básica': 'es_formacion_basica',
        'formacion basica': 'es_formacion_basica',
        'departamento': 'departamento',
        'titulación': 'titulacion',
        'titulacion': 'titulacion',
        'carrera': 'titulacion',
        'grado': 'titulacion',
        'nombre': 'nombre',
        'llama': 'nombre',
    }
    
    def name(self) -> Text:
        return "action_consultar_asignatura"
    
    def _normalizar_atributo(self, atributo: str) -> str:
        """Normaliza el atributo extraído al campo de BD correspondiente"""
        if not atributo:
            return None
        atributo_lower = atributo.lower().strip()
        return self.ATRIBUTO_MAP.get(atributo_lower)
    
    def _formatear_duracion(self, duracion: str) -> str:
        """Formatea el código de duración a texto legible"""
        return {
            'A': 'Anual',
            'C1': 'Primer Cuatrimestre',
            'C2': 'Segundo Cuatrimestre'
        }.get(duracion, duracion)
    
    def _formatear_tipologia(self, tipologia: str) -> str:
        """Formatea la tipología a texto legible"""
        return tipologia.replace('_', ' ').title() if tipologia else ''
    
    def _generar_respuesta_atributo(self, atributo: str, datos: dict) -> str:
        """Genera respuesta específica según el atributo solicitado"""
        nombre = datos['nombre']
        
        respuestas = {
            'nombre': f"La asignatura se llama {nombre}.",
            'creditos': f"{nombre} tiene {datos['creditos']} créditos ECTS.",
            'curso': f"{nombre} se imparte en {datos['curso']}º curso.",
            'duracion': f"{nombre} tiene una duración {self._formatear_duracion(datos['duracion']).lower()}.",
            'tipologia': f"{nombre} es de tipo {self._formatear_tipologia(datos['tipologia'])}.",
            'es_optativa': f"{'Sí' if datos['es_optativa'] else 'No'}, {nombre} {'es' if datos['es_optativa'] else 'no es'} optativa.",
            'es_formacion_basica': f"{'Sí' if datos['es_formacion_basica'] else 'No'}, {nombre} {'es' if datos['es_formacion_basica'] else 'no es'} formación básica.",
            'departamento': f"{nombre} es impartida por el departamento de {datos['departamento']}."
                            if datos['departamento'] else f"No tengo información del departamento que imparte {nombre}.",
            'titulacion': f"{nombre} pertenece a {datos['titulacion']}."
                          if datos['titulacion'] else f"No tengo información de la titulación de {nombre}.",
        }
        
        return respuestas.get(atributo, self._generar_respuesta_general(datos))
    
    def _generar_respuesta_general(self, datos: dict) -> str:
        """Genera respuesta con resumen básico de la asignatura"""
        duracion_texto = self._formatear_duracion(datos['duracion'])
        tipo_texto = self._formatear_tipologia(datos['tipologia'])
        
        respuesta = f"""{datos['nombre']} ({datos['codigo']}):
        • Curso: {datos['curso']}º
        • Créditos: {datos['creditos']} ECTS
        • Duración: {duracion_texto}
        • Tipo: {tipo_texto}"""
        
        if datos['departamento']:
            respuesta += f"\n• Departamento: {datos['departamento']}"
        
        return respuesta
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        if db_client is None:
            dispatcher.utter_message(text="Error: No se pudo conectar con la base de datos")
            return []
        
        # Obtener entidades extraídas
        codigo_asignatura = next(tracker.get_latest_entity_values("codigo_asignatura"), None)
        atributo_raw = next(tracker.get_latest_entity_values("atributo_asignatura"), None)
        
        if not codigo_asignatura:
            dispatcher.utter_message(text="Por favor, especifica el código de la asignatura que quieres consultar.")
            return []
        
        codigo_asignatura = codigo_asignatura.upper()
        atributo = self._normalizar_atributo(atributo_raw)
        
        # Realizar consulta a la base de datos
        conn = db_client.get_connection()
        if not conn:
            dispatcher.utter_message(text="Error al conectar con la base de datos")
            return []
        
        try:
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    a.codigo,
                    a.nombre,
                    a.curso,
                    a.creditos,
                    a.duracion,
                    a.tipologia,
                    a.es_formacion_basica,
                    a.es_optativa,
                    t.nombre as titulacion_nombre,
                    d.nombre as departamento_nombre
                FROM asignaturas a
                LEFT JOIN titulaciones t ON a.titulacion_id = t.id
                LEFT JOIN departamentos d ON a.departamento_id = d.id
                WHERE a.codigo = %s AND a.activa = true
            """
            
            cursor.execute(query, (codigo_asignatura,))
            result = cursor.fetchone()
            
            if result:
                datos = {
                    'codigo': result[0],
                    'nombre': result[1],
                    'curso': result[2],
                    'creditos': result[3],
                    'duracion': result[4],
                    'tipologia': result[5],
                    'es_formacion_basica': result[6],
                    'es_optativa': result[7],
                    'titulacion': result[8],
                    'departamento': result[9],
                }
                
                # Generar respuesta según si hay atributo específico o no
                if atributo:
                    respuesta = self._generar_respuesta_atributo(atributo, datos)
                else:
                    respuesta = self._generar_respuesta_general(datos)
                
                dispatcher.utter_message(text=respuesta)
                
                # Guardar contexto para preguntas de seguimiento
                return [
                    SlotSet("ultimo_codigo_consultado", datos['codigo']),
                    SlotSet("ultimo_nombre_asignatura", datos['nombre'])
                ]
            else:
                dispatcher.utter_message(
                    text=f"No encontré información para la asignatura con código '{codigo_asignatura}'. "
                         "Verifica que el código sea correcto."
                )
            
            cursor.close()
            
        except Exception as e:
            print(f"Error en consulta de asignatura: {e}")
            dispatcher.utter_message(text="Error al consultar la información de la asignatura.")
        finally:
            conn.close()
        
        return []


class ActionPreguntaSeguimiento(Action):
    """Action para responder preguntas de seguimiento sobre la última asignatura consultada"""
    
    # Reutilizar el mismo mapeo de atributos
    ATRIBUTO_MAP = ActionConsultarAsignatura.ATRIBUTO_MAP
    
    def name(self) -> Text:
        return "action_pregunta_seguimiento"
    
    def _normalizar_atributo(self, atributo: str) -> str:
        if not atributo:
            return None
        atributo_lower = atributo.lower().strip()
        return self.ATRIBUTO_MAP.get(atributo_lower)
    
    def _formatear_duracion(self, duracion: str) -> str:
        return {
            'A': 'Anual',
            'C1': 'Primer Cuatrimestre',
            'C2': 'Segundo Cuatrimestre'
        }.get(duracion, duracion)
    
    def _formatear_tipologia(self, tipologia: str) -> str:
        return tipologia.replace('_', ' ').title() if tipologia else ''
    
    def _generar_respuesta_atributo(self, atributo: str, datos: dict) -> str:
        nombre = datos['nombre']
        
        respuestas = {
            'nombre': f"La asignatura se llama {nombre}.",
            'creditos': f"{nombre} tiene {datos['creditos']} créditos ECTS.",
            'curso': f"{nombre} se imparte en {datos['curso']}º curso.",
            'duracion': f"{nombre} tiene una duración {self._formatear_duracion(datos['duracion']).lower()}.",
            'tipologia': f"{nombre} es de tipo {self._formatear_tipologia(datos['tipologia'])}.",
            'es_optativa': f"{'Sí' if datos['es_optativa'] else 'No'}, {nombre} {'es' if datos['es_optativa'] else 'no es'} optativa.",
            'es_formacion_basica': f"{'Sí' if datos['es_formacion_basica'] else 'No'}, {nombre} {'es' if datos['es_formacion_basica'] else 'no es'} formación básica.",
            'departamento': f"{nombre} es impartida por el departamento de {datos['departamento']}."
                            if datos['departamento'] else f"No tengo información del departamento que imparte {nombre}.",
            'titulacion': f"{nombre} pertenece a {datos['titulacion']}."
                          if datos['titulacion'] else f"No tengo información de la titulación de {nombre}.",
        }
        
        return respuestas.get(atributo)
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Obtener contexto de la última consulta
        ultimo_codigo = tracker.get_slot("ultimo_codigo_consultado")
        
        if not ultimo_codigo:
            dispatcher.utter_message(text="No tengo contexto de una asignatura anterior. Por favor, indica el código de la asignatura.")
            return []
        
        # Obtener atributo solicitado
        atributo_raw = next(tracker.get_latest_entity_values("atributo_asignatura"), None)
        atributo = self._normalizar_atributo(atributo_raw)
        
        if not atributo:
            dispatcher.utter_message(text="No entendí qué información quieres. ¿Créditos, curso, duración, departamento...?")
            return []
        
        if db_client is None:
            dispatcher.utter_message(text="Error: No se pudo conectar con la base de datos")
            return []
        
        conn = db_client.get_connection()
        if not conn:
            dispatcher.utter_message(text="Error al conectar con la base de datos")
            return []
        
        try:
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    a.codigo,
                    a.nombre,
                    a.curso,
                    a.creditos,
                    a.duracion,
                    a.tipologia,
                    a.es_formacion_basica,
                    a.es_optativa,
                    t.nombre as titulacion_nombre,
                    d.nombre as departamento_nombre
                FROM asignaturas a
                LEFT JOIN titulaciones t ON a.titulacion_id = t.id
                LEFT JOIN departamentos d ON a.departamento_id = d.id
                WHERE a.codigo = %s AND a.activa = true
            """
            
            cursor.execute(query, (ultimo_codigo,))
            result = cursor.fetchone()
            
            if result:
                datos = {
                    'codigo': result[0],
                    'nombre': result[1],
                    'curso': result[2],
                    'creditos': result[3],
                    'duracion': result[4],
                    'tipologia': result[5],
                    'es_formacion_basica': result[6],
                    'es_optativa': result[7],
                    'titulacion': result[8],
                    'departamento': result[9],
                }
                
                respuesta = self._generar_respuesta_atributo(atributo, datos)
                if respuesta:
                    dispatcher.utter_message(text=respuesta)
                else:
                    dispatcher.utter_message(text="No pude obtener esa información.")
            else:
                dispatcher.utter_message(text="No encontré la asignatura en la base de datos.")
            
            cursor.close()
            
        except Exception as e:
            print(f"Error en pregunta de seguimiento: {e}")
            dispatcher.utter_message(text="Error al consultar la información.")
        finally:
            conn.close()
        
        return []