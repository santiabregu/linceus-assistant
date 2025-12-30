# Módulo de conexión a base de datos
# Centraliza la configuración y conexión a PostgreSQL/Supabase

import os
import psycopg2
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


class DatabaseConnection:
    """Gestiona la conexión a la base de datos PostgreSQL"""
    
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
