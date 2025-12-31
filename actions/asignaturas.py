# Actions relacionadas con la épica de Asignaturas
# v1.2.1 - Rapidfuzz, mejor contexto, respuestas naturales

from typing import Any, Text, Dict, List, Optional
from rapidfuzz import fuzz, process
import unicodedata

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from .db import db_client


# =============================================================================
# UTILIDADES COMPARTIDAS PARA ASIGNATURAS
# =============================================================================

def normalizar_texto(texto: str) -> str:
    """
    Normaliza texto: quita acentos y convierte a minúsculas.
    Útil para búsquedas tolerantes a errores.
    """
    if not texto:
        return ""
    # Descomponer caracteres unicode (é -> e + ́)
    texto_normalizado = unicodedata.normalize('NFD', texto)
    # Eliminar marcas diacríticas (acentos)
    texto_sin_acentos = ''.join(
        char for char in texto_normalizado 
        if unicodedata.category(char) != 'Mn'
    )
    return texto_sin_acentos.lower().strip()

# Mapeo de lenguaje natural a campos de BD
ATRIBUTO_MAP = {
    # Créditos
    'creditos': 'creditos',
    'créditos': 'creditos',
    'credito': 'creditos',
    'crédito': 'creditos',
    # Curso
    'curso': 'curso',
    'año': 'curso',
    'cursos': 'curso',
    # Duración
    'dura': 'duracion',
    'duración': 'duracion',
    'duracion': 'duracion',
    'anual': 'duracion',
    'cuatrimestre': 'duracion',
    'semestre': 'duracion',
    # Tipología
    'tipo': 'tipologia',
    'tipología': 'tipologia',
    'tipologia': 'tipologia',
    'obligatoria': 'tipologia',
    'obligatorio': 'tipologia',
    'optativa': 'es_optativa',
    'optativo': 'es_optativa',
    'formación básica': 'es_formacion_basica',
    'formacion basica': 'es_formacion_basica',
    'basica': 'es_formacion_basica',
    'básica': 'es_formacion_basica',
    # Departamento
    'departamento': 'departamento',
    'depto': 'departamento',
    'quien la da': 'departamento',
    'quien la imparte': 'departamento',
    'imparte': 'departamento',
    # Titulación
    'titulación': 'titulacion',
    'titulacion': 'titulacion',
    'carrera': 'titulacion',
    'grado': 'titulacion',
    # Nombre
    'nombre': 'nombre',
    'llama': 'nombre',
    'llamar': 'nombre',
}

# Lista de palabras clave para fuzzy matching
ATRIBUTO_KEYWORDS = list(ATRIBUTO_MAP.keys())

# Query base para obtener datos de asignatura
QUERY_ASIGNATURA_BASE = """
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
"""


def normalizar_atributo(atributo: str) -> Optional[str]:
    """
    Normaliza el atributo extraído al campo de BD correspondiente.
    Usa rapidfuzz para tolerar errores ortográficos.
    """
    if not atributo:
        return None
    
    atributo_lower = atributo.lower().strip()
    
    # Primero intenta match exacto
    if atributo_lower in ATRIBUTO_MAP:
        return ATRIBUTO_MAP[atributo_lower]
    
    # Si no hay match exacto, intenta fuzzy matching con rapidfuzz
    resultado = process.extractOne(
        atributo_lower, 
        ATRIBUTO_KEYWORDS, 
        scorer=fuzz.WRatio,
        score_cutoff=70  # Mínimo 70% de similitud
    )
    
    if resultado:
        mejor_match, score, _ = resultado
        return ATRIBUTO_MAP[mejor_match]
    
    return None


def formatear_duracion(duracion: str) -> str:
    """Formatea el código de duración a texto legible"""
    return {
        'A': 'Anual',
        'C1': 'Primer Cuatrimestre',
        'C2': 'Segundo Cuatrimestre'
    }.get(duracion, duracion)


def formatear_tipologia(tipologia: str) -> str:
    """Formatea la tipología a texto legible"""
    return tipologia.replace('_', ' ').title() if tipologia else ''


def parsear_resultado_asignatura(result: tuple) -> dict:
    """Convierte el resultado de la query a un diccionario"""
    return {
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


def generar_respuesta_atributo(atributo: str, datos: dict) -> Optional[str]:
    """Genera respuesta específica según el atributo solicitado"""
    nombre = datos['nombre']
    
    respuestas = {
        'nombre': f"La asignatura se llama {nombre}.",
        'creditos': f"{nombre} tiene {datos['creditos']} créditos ECTS.",
        'curso': f"{nombre} se imparte en {datos['curso']}º curso.",
        'duracion': f"{nombre} tiene una duración {formatear_duracion(datos['duracion']).lower()}.",
        'tipologia': f"{nombre} es de tipo {formatear_tipologia(datos['tipologia'])}.",
        'es_optativa': f"{'Sí' if datos['es_optativa'] else 'No'}, {nombre} {'es' if datos['es_optativa'] else 'no es'} optativa.",
        'es_formacion_basica': f"{'Sí' if datos['es_formacion_basica'] else 'No'}, {nombre} {'es' if datos['es_formacion_basica'] else 'no es'} formación básica.",
        'departamento': f"{nombre} es impartida por el departamento de {datos['departamento']}."
                        if datos['departamento'] else f"No tengo información del departamento que imparte {nombre}.",
        'titulacion': f"{nombre} pertenece a {datos['titulacion']}."
                      if datos['titulacion'] else f"No tengo información de la titulación de {nombre}.",
    }
    
    return respuestas.get(atributo)


def generar_respuesta_general(datos: dict) -> str:
    """Genera respuesta con resumen básico de la asignatura"""
    duracion_texto = formatear_duracion(datos['duracion'])
    tipo_texto = formatear_tipologia(datos['tipologia'])
    
    respuesta = f"""{datos['nombre']} ({datos['codigo']}):
• Curso: {datos['curso']}º
• Créditos: {datos['creditos']} ECTS
• Duración: {duracion_texto}
• Tipo: {tipo_texto}"""
    
    if datos['departamento']:
        respuesta += f"\n• Departamento: {datos['departamento']}"
    
    return respuesta


def buscar_asignatura(codigo: str = None, nombre: str = None) -> Optional[dict]:
    """
    Busca una asignatura por código o nombre.
    La búsqueda por nombre usa rapidfuzz para tolerar errores y acentos.
    Retorna el diccionario de datos o None si no encuentra.
    """
    if not codigo and not nombre:
        return None
    
    if db_client is None:
        return None
    
    conn = db_client.get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        
        if codigo:
            query = QUERY_ASIGNATURA_BASE + "WHERE a.codigo = %s AND a.activa = true"
            cursor.execute(query, (codigo.upper(),))
            result = cursor.fetchone()
        else:
            # Primero intentar búsqueda exacta con LIKE
            query = QUERY_ASIGNATURA_BASE + "WHERE LOWER(a.nombre) LIKE LOWER(%s) AND a.activa = true"
            cursor.execute(query, (f"%{nombre}%",))
            result = cursor.fetchone()
            
            # Si no encuentra, buscar con fuzzy matching usando rapidfuzz
            if not result:
                nombre_normalizado = normalizar_texto(nombre)
                cursor.execute(QUERY_ASIGNATURA_BASE + "WHERE a.activa = true")
                todas = cursor.fetchall()
                
                # Crear diccionario de nombres normalizados -> row
                nombres_normalizados = {
                    normalizar_texto(row[1]): row for row in todas
                }
                
                # Buscar mejor coincidencia con rapidfuzz
                mejor_match = process.extractOne(
                    nombre_normalizado,
                    list(nombres_normalizados.keys()),
                    scorer=fuzz.WRatio,
                    score_cutoff=60  # Mínimo 60% similitud para nombres
                )
                
                if mejor_match:
                    nombre_encontrado, score, _ = mejor_match
                    result = nombres_normalizados[nombre_encontrado]
        
        cursor.close()
        
        if result:
            return parsear_resultado_asignatura(result)
        return None
        
    except Exception as e:
        print(f"Error buscando asignatura: {e}")
        return None
    finally:
        conn.close()


# =============================================================================
# ACTIONS
# =============================================================================

class ActionConsultarAsignatura(Action):
    """Action para consultar información de una asignatura por código o nombre"""
    
    def name(self) -> Text:
        return "action_consultar_asignatura"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Obtener entidades extraídas
        codigo = next(tracker.get_latest_entity_values("codigo_asignatura"), None)
        nombre = next(tracker.get_latest_entity_values("nombre_asignatura"), None)
        atributo_raw = next(tracker.get_latest_entity_values("atributo_asignatura"), None)
        
        if not codigo and not nombre:
            dispatcher.utter_message(
                text="Por favor, especifica el código o nombre de la asignatura que quieres consultar."
            )
            return []
        
        # Buscar asignatura
        datos = buscar_asignatura(codigo=codigo, nombre=nombre)
        
        if not datos:
            if codigo:
                dispatcher.utter_message(
                    text=f"No encontré información para la asignatura con código '{codigo.upper()}'. "
                         "Verifica que el código sea correcto."
                )
            else:
                dispatcher.utter_message(
                    text=f"No encontré ninguna asignatura con el nombre '{nombre}'. "
                         "Intenta con otro nombre o usa el código de la asignatura."
                )
            return []
        
        # Generar respuesta
        atributo = normalizar_atributo(atributo_raw)
        if atributo:
            respuesta = generar_respuesta_atributo(atributo, datos)
            if not respuesta:
                respuesta = generar_respuesta_general(datos)
        else:
            respuesta = generar_respuesta_general(datos)
        
        dispatcher.utter_message(text=respuesta)
        
        # Guardar contexto para preguntas de seguimiento
        return [
            SlotSet("ultimo_codigo_consultado", datos['codigo']),
            SlotSet("ultimo_nombre_asignatura", datos['nombre'])
        ]


class ActionPreguntaSeguimiento(Action):
    """Action para responder preguntas de seguimiento sobre la última asignatura consultada"""
    
    def name(self) -> Text:
        return "action_pregunta_seguimiento"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Obtener contexto de la última consulta
        ultimo_codigo = tracker.get_slot("ultimo_codigo_consultado")
        
        if not ultimo_codigo:
            dispatcher.utter_message(
                text="No tengo contexto de una asignatura anterior. "
                     "Por favor, indica el código o nombre de la asignatura."
            )
            return []
        
        # Obtener atributo solicitado
        atributo_raw = next(tracker.get_latest_entity_values("atributo_asignatura"), None)
        atributo = normalizar_atributo(atributo_raw)
        
        if not atributo:
            dispatcher.utter_message(
                text="No entendí qué información quieres. ¿Créditos, curso, duración, departamento...?"
            )
            return []
        
        # Buscar asignatura con el código guardado
        datos = buscar_asignatura(codigo=ultimo_codigo)
        
        if not datos:
            dispatcher.utter_message(text="No encontré la asignatura en la base de datos.")
            return []
        
        # Generar respuesta
        respuesta = generar_respuesta_atributo(atributo, datos)
        if respuesta:
            dispatcher.utter_message(text=respuesta)
        else:
            dispatcher.utter_message(text="No pude obtener esa información.")
        
        return []

class ActionPedirInfoAsignatura(Action):
    """
    Action para cuando el usuario pide info genérica o quiere cambiar de asignatura.
    Detecta si quiere "otra asignatura" para limpiar contexto.
    """
    
    # Palabras clave que indican querer cambiar de asignatura
    PALABRAS_CAMBIO = ['otra', 'diferente', 'distinta', 'cambiar', 'nueva', 'otro']
    
    def name(self) -> Text:
        return "action_pedir_info_asignatura"
    
    def _quiere_cambiar_asignatura(self, tracker: Tracker) -> bool:
        """Detecta si el usuario quiere consultar otra asignatura diferente"""
        ultimo_mensaje = tracker.latest_message.get('text', '').lower()
        return any(palabra in ultimo_mensaje for palabra in self.PALABRAS_CAMBIO)
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Verificar si quiere cambiar de asignatura
        if self._quiere_cambiar_asignatura(tracker):
            dispatcher.utter_message(
                text="¡Claro! ¿Qué asignatura te interesa ahora? Dime el nombre o código."
            )
            # Limpiar contexto anterior
            return [
                SlotSet("ultimo_codigo_consultado", None),
                SlotSet("ultimo_nombre_asignatura", None)
            ]
        
        # Verificar si hay contexto previo
        ultimo_codigo = tracker.get_slot("ultimo_codigo_consultado")
        
        if ultimo_codigo:
            # Hay contexto, mostrar info de esa asignatura
            datos = buscar_asignatura(codigo=ultimo_codigo)
            if datos:
                respuesta = generar_respuesta_general(datos)
                dispatcher.utter_message(
                    text=f"Esta es la información de la última asignatura que consultaste:\n\n{respuesta}\n\n"
                         "¿Quieres saber algo más específico o consultar otra asignatura?"
                )
                return []
        
        # No hay contexto, pedir que especifique
        dispatcher.utter_message(
            text="¿Qué asignatura te interesa? Puedes decirme el nombre (ej: 'Fundamentos de Programación') "
                 "o el código (ej: '2050001')."
        )
        return []