# Configuración centralizada del chatbot Linceus
# Define los valores por defecto para el contexto académico

import os
from dotenv import load_dotenv

load_dotenv()


class BotConfig:
    """
    Configuración del contexto académico del bot.
    Los valores por defecto se leen de variables de entorno.
    """
    
    # Valores por defecto (hardcoded como fallback)
    DEFAULTS = {
        'universidad': 'US',
        'centro': 'ETSII', 
        'titulacion': 'GII-IS',
    }
    
    # Nombres legibles para mostrar al usuario
    NOMBRES_CENTROS = {
        'ETSII': 'E.T.S. de Ingeniería Informática',
        # Añadir más centros según se necesiten
    }
    
    NOMBRES_TITULACIONES = {
        'GII-IS': 'Grado en Ingeniería Informática - Ingeniería del Software',
        'GII-TI': 'Grado en Ingeniería Informática - Tecnologías Informáticas',
        'GII-IC': 'Grado en Ingeniería Informática - Ingeniería de Computadores',
        'GII-SI': 'Grado en Ingeniería Informática - Sistemas de Información',
        # Añadir más titulaciones según se necesiten
    }
    
    @classmethod
    def get_default_universidad(cls) -> str:
        return os.getenv('DEFAULT_UNIVERSIDAD_CODIGO', cls.DEFAULTS['universidad'])
    
    @classmethod
    def get_default_centro(cls) -> str:
        return os.getenv('DEFAULT_CENTRO_CODIGO', cls.DEFAULTS['centro'])
    
    @classmethod
    def get_default_titulacion(cls) -> str:
        return os.getenv('DEFAULT_TITULACION_CODIGO', cls.DEFAULTS['titulacion'])
    
    @classmethod
    def get_nombre_centro(cls, codigo: str) -> str:
        return cls.NOMBRES_CENTROS.get(codigo, codigo)
    
    @classmethod
    def get_nombre_titulacion(cls, codigo: str) -> str:
        return cls.NOMBRES_TITULACIONES.get(codigo, codigo)
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Helpers para Actions (reciben el tracker de Rasa)
    # ─────────────────────────────────────────────────────────────────────────────
    
    @classmethod
    def get_titulacion_activa(cls, tracker) -> str:
        """
        Obtiene la titulación activa para la conversación.
        Lee del slot si el usuario la cambió, si no usa el default.
        Usar en las actions: titulacion = BotConfig.get_titulacion_activa(tracker)
        """
        return tracker.get_slot("contexto_titulacion") or cls.get_default_titulacion()
    
    @classmethod
    def get_centro_activo(cls, tracker) -> str:
        """
        Obtiene el centro activo para la conversación.
        Lee del slot si el usuario lo cambió, si no usa el default.
        """
        return tracker.get_slot("contexto_centro") or cls.get_default_centro()
    
    @classmethod
    def get_contexto_actual(cls, centro_override: str = None, titulacion_override: str = None) -> dict:
        """
        Retorna el contexto académico actual.
        Si se pasan overrides (de slots), los usa; si no, usa defaults.
        """
        centro = centro_override or cls.get_default_centro()
        titulacion = titulacion_override or cls.get_default_titulacion()
        
        return {
            'universidad': cls.get_default_universidad(),
            'centro_codigo': centro,
            'centro_nombre': cls.get_nombre_centro(centro),
            'titulacion_codigo': titulacion,
            'titulacion_nombre': cls.get_nombre_titulacion(titulacion),
        }


# Instancia global para imports fáciles
config = BotConfig()
