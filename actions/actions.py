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
    print("✅ Configuración de base de datos cargada correctamente")
except Exception as e:
    print(f"❌ Error configurando base de datos: {e}")
    db_client = None


class ActionTestSupabase(Action):
    """Action de prueba para verificar conexión con la base de datos"""
    
    def name(self) -> Text:
        return "action_test_supabase"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        if db_client is None:
            dispatcher.utter_message(text="❌ Error: No se pudo configurar la conexión a la base de datos")
            return []
        
        if db_client.test_connection():
            dispatcher.utter_message(text="✅ Conexión con la base de datos exitosa!")
        else:
            dispatcher.utter_message(text="❌ Error al conectar con la base de datos")
        
        return []


class ActionConsultarAsignatura(Action):
    """Action para consultar información de una asignatura"""
    
    def name(self) -> Text:
        return "action_consultar_asignatura"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        if db_client is None:
            dispatcher.utter_message(text="❌ Error: No se pudo conectar con la base de datos")
            return []
        
        # Obtener el código de asignatura de la entidad extraída
        codigo_asignatura = next(tracker.get_latest_entity_values("codigo_asignatura"), None)
        
        if not codigo_asignatura:
            dispatcher.utter_message(text="Por favor, especifica el código de la asignatura que quieres consultar (por ejemplo: IS2)")
            return []
        
        # Convertir a mayúsculas para mayor robustez
        codigo_asignatura = codigo_asignatura.upper()
        
        # Realizar consulta a la base de datos
        conn = db_client.get_connection()
        if not conn:
            dispatcher.utter_message(text="❌ Error al conectar con la base de datos")
            return []
        
        try:
            cursor = conn.cursor()
            query = """
                SELECT codigo, nombre, curso, creditos, calificacion, evaluacion, metodologia, bibliografia
                FROM public.asignaturas 
                WHERE codigo = %s
            """
            cursor.execute(query, (codigo_asignatura,))
            result = cursor.fetchone()
            
            if result:
                codigo, nombre, curso, creditos, calificacion, evaluacion, metodologia, bibliografia = result
                
                # Formatear la respuesta
                respuesta = f"""
📚 **{nombre}** ({codigo})

🎓 **Curso:** {curso}º año
📖 **Créditos:** {creditos} ECTS

📊 **Calificación:**
{calificacion}

📝 **Evaluación:**
{evaluacion}

🔬 **Metodología:**
{metodologia}

📚 **Bibliografía:**
{bibliografia}
                """.strip()
                
                dispatcher.utter_message(text=respuesta)
            else:
                dispatcher.utter_message(text=f"❌ No se encontró información para la asignatura '{codigo_asignatura}'. Verifica que el código sea correcto.")
            
            cursor.close()
            
        except Exception as e:
            print(f"Error en consulta de asignatura: {e}")
            dispatcher.utter_message(text="❌ Error al consultar la información de la asignatura")
        finally:
            conn.close()
        
        return []


