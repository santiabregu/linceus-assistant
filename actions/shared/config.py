# Configuración centralizada del chatbot Linceus
# Define los valores por defecto para el contexto académico

import os
from typing import Optional
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
    def get_titulacion_activa(cls, tracker) -> Optional[str]:
        """
        Obtiene la titulación activa para la conversación.
        Devuelve None si el usuario no ha elegido titulación.
        """
        return tracker.get_slot("contexto_titulacion") or None
    
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
        titulacion = titulacion_override
        
        return {
            'universidad': cls.get_default_universidad(),
            'centro_codigo': centro,
            'centro_nombre': cls.get_nombre_centro(centro),
            'titulacion_codigo': titulacion,
            'titulacion_nombre': cls.get_nombre_titulacion(titulacion),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Diccionario unificado de alias/abreviaturas → nombre normalizado
# Fuente única para: text_to_sql, action de horarios, inserción en BD
# Claves en minúsculas, valores sin tildes y en minúsculas
# ─────────────────────────────────────────────────────────────────────────────

ALIAS_ASIGNATURAS = {
    # ── Curso 1 (comunes a IC/IS/TI) ──
    'aln': 'algebra lineal y numerica',
    'ced': 'circuitos electronicos digitales',
    'imd': 'introduccion a la matematica discreta',
    'fp': 'fundamentos de programacion',
    'ae': 'administracion de empresas',
    'ffi': 'fundamentos fisicos de la informatica',
    'cin': 'calculo infinitesimal y numerico',
    'e': 'estadistica',
    'edc': 'estructura de computadores',

    # ── Curso 2 (comunes / IC) ──
    'adda': 'analisis y diseno de datos y algoritmos',
    'so': 'sistemas operativos',
    'tc': 'tecnologia de computadores',
    'dsd': 'diseno de sistemas digitales',
    'iissi1': 'introduccion a la ingenieria del software y los sistemas de informacion i',
    'iissi2': 'introduccion a la ingenieria del software y los sistemas de informacion ii',
    'iissi': 'introduccion a la ingenieria del software y los si',
    'ac': 'arquitectura de computadores',
    'md': 'matematica discreta',
    'rc': 'redes de computadores',

    # ── Curso 2 (IS) ──
    'li': 'logica informatica',
    'aiss': 'arquitectura e integracion de sistemas software',

    # ── Curso 2 (TI) ──
    'ar': 'arquitectura de redes',

    # ── Curso 3 (IC) ──
    'ss': 'software de sistemas',
    'spd': 'sistemas paralelos y distribuidos',
    'tg': 'teoria de grafos',
    'ia': 'inteligencia artificial',
    'atr1': 'arquitectura y tecnologias de redes i',
    'atr2': 'arquitectura y tecnologias de redes ii',
    'pi': 'perifericos e interfaces',
    'setr1': 'sistemas empotrados y de tiempo real i',
    'gc': 'geometria computacional',
    'dad': 'desarrollo de aplicaciones distribuidas',

    # ── Curso 3 (IS) ──
    'dp1': 'diseno y pruebas i',
    'dp2': 'diseno y pruebas ii',
    'is1': 'introduccion a la ingenieria del software',
    'is2': 'diseno y pruebas',
    'iso': 'introduccion a la ingenieria del software y los sistemas de informacion',
    'psm': 'procesamiento de senales multimedia',
    'msn': 'modelado y simulacion numerica',
    'ir': 'ingenieria de requisitos',
    'psg1': 'proceso software y gestion i',
    'psg2': 'proceso software y gestion ii',
    'psg': 'proceso software y gestion i',
    'asr': 'arquitectura y servicios de redes',
    'mvg': 'modelado y visualizacion grafica',

    # ── Curso 3 (TI) ──
    'cimsi': 'configuracion, implementacion y mantenimiento de sistemas informaticos',
    'gsi': 'gestion de sistemas de informacion',
    'pl': 'procesadores de lenguajes',
    'pd': 'programacion declarativa',
    'tai': 'tecnologias avanzadas de la informacion',
    'gee': 'gestion y estrategia empresarial',
    'asd': 'arquitectura de sistemas distribuidos',
    'sos': 'sistemas orientados a servicios',
    'sie': 'sistemas inteligentes',
    'si': 'sistemas de informacion empresariales',
    'masi': 'matematica aplicada a sistemas de informacion',
    'aia': 'ampliacion de inteligencia artificial',

    # ── Curso 4 (IC) ──
    'pgpi': 'planificacion y gestion de proyectos informaticos',
    'ssii': 'seguridad en sistemas informaticos y en internet',
    'gp': 'gestion de la produccion',
    'setr2': 'sistemas empotrados y de tiempo real ii',
    'ldh': 'laboratorio de desarrollo de hardware',
    'tis': 'tecnologia, informatica y sociedad',
    'asc': 'aplicaciones de soft computing',
    'phae': 'plataformas hardware de aplicacion especifica',
    'pid': 'procesamiento de imagenes digitales',
    'ra': 'robotica y automatizacion',
    'sac': 'sistemas de adquisicion y control',
    'aii': 'acceso inteligente a la informacion',
    'ec': 'estadistica computacional',
    't': 'teledeteccion',

    # ── Curso 4 (IS) ──
    'mc': 'modelos de computacion y complejidad',
    'mcc': 'modelos de computacion y complejidad',
    'ispp': 'ingenieria del software y practica profesional',
    'cbd': 'complementos de base de datos',
    'mati': 'matematica aplicada a tecnologias de la informacion',
    'ipo': 'interaccion persona-ordenador',
    'marsi': 'modelado y analisis de requisitos en sistemas de informacion',
    'isi': 'infraestructura de sistemas de informacion',
    'gps': 'gestion de procesos y servicios',
    'cm': 'computacion movil',
    'asi': 'administracion de sistemas de informacion',
    'os': 'operaciones y servicios',
    'egc': 'evolucion y gestion de la configuracion',
    'ssi': 'seguridad de sistemas de informacion',
    'cripto': 'criptografia',

    # ── Curso 4 (TI) ──
    'mcg': 'matematicas para la computacion',
    'di': 'derecho en la informatica',
    'c': 'criptografia',
    'aae': 'ampliacion de administracion de empresas',
    'gie': 'gestion de la informacion empresarial',
    'ie': 'inteligencia empresarial',

    # ── Alias coloquiales / variantes ──
    'tfg': 'trabajo fin de grado',
}

# Alias que cambian de significado según la titulación
ALIAS_POR_TITULACION = {
    'GII-IS': {
        'ssii': 'seguridad de sistemas de informacion',
    },
}


# Instancia global para imports fáciles
config = BotConfig()
