# Actions relacionadas con la épica de Asignaturas
# v1.3.1 - Lógica singular/plural + filtro créditos + fallbacks

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
    La búsqueda por nombre usa múltiples estrategias:
    1. LIKE exacto en BD
    2. Coincidencia de palabras clave
    3. Fuzzy matching como fallback
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
            # ESTRATEGIA 1: Búsqueda exacta con LIKE
            query = QUERY_ASIGNATURA_BASE + "WHERE LOWER(a.nombre) LIKE LOWER(%s) AND a.activa = true"
            cursor.execute(query, (f"%{nombre}%",))
            result = cursor.fetchone()
            
            if not result:
                nombre_normalizado = normalizar_texto(nombre)
                cursor.execute(QUERY_ASIGNATURA_BASE + "WHERE a.activa = true")
                todas = cursor.fetchall()
                
                # ESTRATEGIA 2: Coincidencia de palabras clave
                # Extraer palabras significativas del input (>3 caracteres)
                palabras_busqueda = [
                    p for p in nombre_normalizado.split() 
                    if len(p) > 3 and p not in {'sobre', 'info', 'dame', 'quiero', 'asignatura', 'mas', 'informacion'}
                ]
                
                if palabras_busqueda:
                    mejor_score = 0
                    mejor_resultado = None
                    
                    for row in todas:
                        nombre_asig_norm = normalizar_texto(row[1])
                        palabras_asig = nombre_asig_norm.split()
                        
                        # Contar cuántas palabras del input están en el nombre
                        coincidencias = sum(
                            1 for palabra in palabras_busqueda 
                            if any(palabra in asig_palabra or asig_palabra in palabra 
                                   for asig_palabra in palabras_asig)
                        )
                        
                        # Score basado en porcentaje de palabras que coinciden
                        if coincidencias > 0:
                            score = coincidencias / len(palabras_busqueda)
                            # Bonus si todas las palabras coinciden
                            if coincidencias == len(palabras_busqueda):
                                score += 0.5
                            
                            if score > mejor_score:
                                mejor_score = score
                                mejor_resultado = row
                    
                    if mejor_resultado and mejor_score >= 0.5:
                        result = mejor_resultado
                
                # ESTRATEGIA 3: Fuzzy matching como fallback
                if not result:
                    nombres_normalizados = {
                        normalizar_texto(row[1]): row for row in todas
                    }
                    
                    mejor_match = process.extractOne(
                        nombre_normalizado,
                        list(nombres_normalizados.keys()),
                        scorer=fuzz.WRatio,
                        score_cutoff=70  # Aumentado a 70% para evitar falsos positivos
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

def extraer_posible_nombre_del_mensaje(mensaje: str) -> Optional[str]:
    """
    Intenta extraer un posible nombre de asignatura del mensaje.
    Busca palabras capitalizadas o patrones comunes.
    """
    import re
    
    # Eliminar palabras comunes de preguntas
    palabras_ignorar = {
        'la', 'el', 'es', 'de', 'del', 'que', 'qué', 'como', 'cómo',
        'asignatura', 'asignaturas', 'obligatoria', 'optativa', 'básica',
        'formación', 'cuántos', 'cuantos', 'créditos', 'creditos', 'curso',
        'duración', 'duracion', 'tiene', 'son', 'hay', 'dame', 'dime',
        'información', 'informacion', 'info', 'sobre', 'cuál', 'cual',
        'anual', 'cuatrimestre', 'primero', 'segundo', 'tercero', 'cuarto',
        'y', 'o', 'a', 'en', 'por', 'para', 'con', 'sin', 'esta', 'esa',
        'tipo', 'departamento', 'titulación', 'titulacion', 'carrera',
    }
    
    # Buscar palabras que empiezan con mayúscula (posibles nombres)
    palabras = mensaje.split()
    candidatos = []
    
    for palabra in palabras:
        palabra_limpia = re.sub(r'[¿?!¡,.]', '', palabra)
        if palabra_limpia and palabra_limpia.lower() not in palabras_ignorar:
            if palabra_limpia[0].isupper() or len(palabra_limpia) > 3:
                candidatos.append(palabra_limpia)
    
    if candidatos:
        return ' '.join(candidatos)
    return None


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
        
        # FALLBACK: Si no hay código ni nombre, intentar extraer del mensaje
        if not codigo and not nombre:
            mensaje = tracker.latest_message.get('text', '')
            nombre_candidato = extraer_posible_nombre_del_mensaje(mensaje)
            if nombre_candidato:
                nombre = nombre_candidato
        
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
    """
    Action para responder preguntas de seguimiento sobre la última asignatura consultada.
    
    IMPORTANTE: Si detecta un nombre de asignatura en el mensaje, usa ESE nombre
    en lugar del contexto. Esto maneja casos como "Redes es obligatoria?" que 
    podrían clasificarse erróneamente como seguimiento.
    """
    
    def name(self) -> Text:
        return "action_pregunta_seguimiento"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Primero: verificar si hay un nombre mencionado en el mensaje
        nombre_mencionado = next(tracker.get_latest_entity_values("nombre_asignatura"), None)
        
        # Si hay nombre, buscar ESA asignatura (no usar contexto)
        if nombre_mencionado:
            datos = buscar_asignatura(nombre=nombre_mencionado)
            if datos:
                atributo_raw = next(tracker.get_latest_entity_values("atributo_asignatura"), None)
                atributo = normalizar_atributo(atributo_raw)
                
                if atributo:
                    respuesta = generar_respuesta_atributo(atributo, datos)
                else:
                    respuesta = generar_respuesta_general(datos)
                
                dispatcher.utter_message(text=respuesta)
                # Actualizar contexto con esta nueva asignatura
                return [
                    SlotSet("ultimo_codigo_consultado", datos['codigo']),
                    SlotSet("ultimo_nombre_asignatura", datos['nombre'])
                ]
            else:
                dispatcher.utter_message(
                    text=f"No encontré ninguna asignatura llamada '{nombre_mencionado}'."
                )
                return []
        
        # Si no hay nombre, usar contexto de última consulta
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


class ActionConsultarAsignaturasFiltradas(Action):
    """
    Action para consultas con múltiples filtros usando NLU puro.
    Extrae entidades: filtro_curso, filtro_tipologia, filtro_duracion, filtro_titulacion
    Ejemplos:
    - "¿Cuáles son las asignaturas obligatorias de primero?"
    - "Dame las optativas de cuarto curso"
    - "¿Qué asignaturas anuales hay?"
    """
    
    # Mapeo de texto a valores de curso
    CURSO_MAP = {
        'primero': 1, 'primer': 1, '1': 1, '1º': 1, '1°': 1,
        'segundo': 2, '2': 2, '2º': 2, '2°': 2,
        'tercero': 3, 'tercer': 3, '3': 3, '3º': 3, '3°': 3,
        'cuarto': 4, '4': 4, '4º': 4, '4°': 4,
    }
    
    # Mapeo de texto a valores de tipología (claves sin acentos para normalizar)
    TIPOLOGIA_MAP = {
        'obligatoria': 'Obligatoria',
        'obligatorias': 'Obligatoria',
        'obligatorio': 'Obligatoria',
        'optativa': 'Optativa',
        'optativas': 'Optativa',
        'optativo': 'Optativa',
        'formacion basica': 'Formacion_Basica',
        'basica': 'Formacion_Basica',
        'basicas': 'Formacion_Basica',
    }
    
    # Mapeo de texto a valores de duración
    DURACION_MAP = {
        'anual': 'A',
        'anuales': 'A',
        'primer cuatrimestre': 'C1',
        'cuatrimestre 1': 'C1',
        'c1': 'C1',
        'segundo cuatrimestre': 'C2',
        'cuatrimestre 2': 'C2',
        'c2': 'C2',
    }
    
    def name(self) -> Text:
        return "action_consultar_asignaturas_filtradas"
    
    def _normalizar_curso(self, valor: str) -> Optional[int]:
        """Convierte texto de curso a número"""
        if not valor:
            return None
        valor_lower = normalizar_texto(valor)
        return self.CURSO_MAP.get(valor_lower)
    
    def _normalizar_tipologia(self, valor: str) -> Optional[str]:
        """Convierte texto de tipología al valor de BD"""
        if not valor:
            return None
        valor_lower = normalizar_texto(valor)
        return self.TIPOLOGIA_MAP.get(valor_lower)
    
    def _extraer_filtros_del_texto(self, texto: str) -> Dict[str, Any]:
        """
        Fallback: extrae filtros directamente del texto si NLU no los detectó.
        Esto maneja casos como 'asignaturas obligatorias' sin entidades.
        """
        filtros = {}
        texto_norm = normalizar_texto(texto)
        
        # Buscar tipología en el texto
        for key, value in self.TIPOLOGIA_MAP.items():
            if key in texto_norm:
                filtros['tipologia'] = value
                break
        
        # Buscar curso en el texto
        for key, value in self.CURSO_MAP.items():
            if key in texto_norm:
                filtros['curso'] = value
                break
        
        # Buscar duración en el texto
        for key, value in self.DURACION_MAP.items():
            if key in texto_norm:
                filtros['duracion'] = value
                break
        
        return filtros
    
    def _normalizar_duracion(self, valor: str) -> Optional[str]:
        """Convierte texto de duración al valor de BD"""
        if not valor:
            return None
        valor_lower = normalizar_texto(valor)
        return self.DURACION_MAP.get(valor_lower)
    
    def _construir_query(self, filtros: Dict[str, Any]) -> tuple:
        """
        Construye la query SQL de forma segura a partir de los filtros.
        Retorna (query_string, params_list)
        """
        query = QUERY_ASIGNATURA_BASE + " WHERE a.activa = true"
        params = []
        
        if filtros.get('curso'):
            query += " AND a.curso = %s"
            params.append(filtros['curso'])
        
        if filtros.get('tipologia'):
            query += " AND a.tipologia = %s"
            params.append(filtros['tipologia'])
        
        if filtros.get('duracion'):
            query += " AND a.duracion = %s"
            params.append(filtros['duracion'])
        
        if filtros.get('titulacion'):
            query += " AND LOWER(t.nombre) LIKE LOWER(%s)"
            params.append(f"%{filtros['titulacion']}%")
        
        if filtros.get('creditos'):
            query += " AND a.creditos = %s"
            params.append(filtros['creditos'])
        
        # Ordenar por curso y nombre
        query += " ORDER BY a.curso, a.nombre"
        
        # El límite se aplica dinámicamente, no aquí
        
        return query, params
    
    def _formatear_resultados(self, resultados: List[dict], filtros: Dict[str, Any], mostrar_todas: bool = False) -> str:
        """Formatea resultados de forma legible"""
        if len(resultados) == 0:
            return "No encontré asignaturas que cumplan esos criterios."
        
        if len(resultados) == 1:
            return generar_respuesta_general(resultados[0])
        
        # Construir descripción del filtro aplicado
        desc_filtro = []
        if filtros.get('tipologia'):
            desc_filtro.append(formatear_tipologia(filtros['tipologia']).lower())
        if filtros.get('curso'):
            desc_filtro.append(f"de {filtros['curso']}º curso")
        if filtros.get('duracion'):
            desc_filtro.append(formatear_duracion(filtros['duracion']).lower())
        if filtros.get('titulacion'):
            desc_filtro.append(f"de {filtros['titulacion']}")
        if filtros.get('creditos'):
            desc_filtro.append(f"de {filtros['creditos']} créditos")
        
        filtro_texto = " ".join(desc_filtro) if desc_filtro else ""
        
        # Determinar cuántas mostrar
        limite_mostrar = len(resultados) if mostrar_todas else 10
        
        # Múltiples resultados
        respuesta = f"Encontré {len(resultados)} asignaturas {filtro_texto}:\n\n"
        for i, datos in enumerate(resultados[:limite_mostrar], 1):
            tipo = formatear_tipologia(datos['tipologia'])
            duracion = formatear_duracion(datos['duracion'])
            respuesta += f"{i}. {datos['nombre']} ({datos['creditos']} ECTS, {duracion})\n"
        
        if not mostrar_todas and len(resultados) > limite_mostrar:
            respuesta += f"\n... y {len(resultados) - limite_mostrar} más. Di 'todas' para ver la lista completa."
        
        return respuesta
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Detectar si el usuario quiere ver TODAS las asignaturas
        mensaje = tracker.latest_message.get('text', '')
        mensaje_lower = mensaje.lower()
        mostrar_todas = any(palabra in mensaje_lower for palabra in ['todas', 'todos', 'completa', 'completo', 'listado completo'])
        
        # Extraer entidades de filtro
        filtro_curso_raw = next(tracker.get_latest_entity_values("filtro_curso"), None)
        filtro_tipologia_raw = next(tracker.get_latest_entity_values("filtro_tipologia"), None)
        filtro_duracion_raw = next(tracker.get_latest_entity_values("filtro_duracion"), None)
        filtro_titulacion = next(tracker.get_latest_entity_values("filtro_titulacion"), None)
        filtro_creditos_raw = next(tracker.get_latest_entity_values("filtro_creditos"), None)
        
        # Normalizar valores
        filtros = {}
        
        curso = self._normalizar_curso(filtro_curso_raw)
        if curso:
            filtros['curso'] = curso
        
        tipologia = self._normalizar_tipologia(filtro_tipologia_raw)
        if tipologia:
            filtros['tipologia'] = tipologia
        
        duracion = self._normalizar_duracion(filtro_duracion_raw)
        if duracion:
            filtros['duracion'] = duracion
        
        if filtro_titulacion:
            filtros['titulacion'] = filtro_titulacion
        
        # Convertir créditos a número
        if filtro_creditos_raw:
            try:
                filtros['creditos'] = float(filtro_creditos_raw)
            except ValueError:
                pass
        
        # FALLBACK: Si NLU no extrajo entidades, buscar en el texto directamente
        if not filtros:
            mensaje = tracker.latest_message.get('text', '')
            filtros = self._extraer_filtros_del_texto(mensaje)
        
        # Verificar que hay al menos un filtro
        if not filtros:
            dispatcher.utter_message(
                text="No detecté ningún filtro en tu consulta. "
                     "Puedo buscar por curso (primero, segundo...), "
                     "tipo (obligatorias, optativas, básicas), "
                     "duración (anuales, primer/segundo cuatrimestre) "
                     "o titulación."
            )
            return []
        
        # Ejecutar query
        if db_client is None:
            dispatcher.utter_message(text="Error de conexión a la base de datos.")
            return []
        
        conn = db_client.get_connection()
        if not conn:
            dispatcher.utter_message(text="No pude conectar con la base de datos.")
            return []
        
        try:
            query, params = self._construir_query(filtros)
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            
            resultados = [parsear_resultado_asignatura(row) for row in rows]
            respuesta = self._formatear_resultados(resultados, filtros, mostrar_todas)
            dispatcher.utter_message(text=respuesta)
            
            # Si hay un solo resultado, guardar contexto
            if len(resultados) == 1:
                return [
                    SlotSet("ultimo_codigo_consultado", resultados[0]['codigo']),
                    SlotSet("ultimo_nombre_asignatura", resultados[0]['nombre'])
                ]
            
            # Limpiar slots de filtro para próximas consultas
            return [
                SlotSet("filtro_curso", None),
                SlotSet("filtro_tipologia", None),
                SlotSet("filtro_duracion", None),
                SlotSet("filtro_titulacion", None),
                SlotSet("filtro_creditos", None),
            ]
            
        except Exception as e:
            print(f"Error en consulta filtrada: {e}")
            dispatcher.utter_message(text="Ocurrió un error al buscar las asignaturas.")
            return []
        finally:
            conn.close()