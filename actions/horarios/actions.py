"""
Actions de Rasa para consultas de horarios personales (curso + grupo).
Consulta la BD (tablas horarios, grupos_clase, asignaturas, aulas) y responde
preguntas como:
  - "¿Qué horario tiene 2º de Computadores grupo 1?"
  - "¿Qué clases hay los lunes en primero grupo 2?"

Requiere curso y grupo. Si el usuario no los da, se le piden.
Las consultas de horario de asignaturas concretas ("¿cuándo tengo FP?",
"¿en qué aula es ADDA?") se gestionan desde ActionConsultaEspecifica.
"""

import re
import unicodedata
from typing import Any, Text, Dict, List, Optional

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from ..shared.config import BotConfig, ALIAS_ASIGNATURAS
from ..shared.db import db_client
from ..shared.gemini_client import llamar_gemini as llamar_llm
from ..asignaturas.actions import comprobar_titulacion, _contar_turnos_desde_slot

# ─── Constantes ──────────────────────────────────────────────────────────────

PDF_HORARIOS_URL = "https://www.informatica.us.es/docs/orgdocente/horarios-grados-2025-26.pdf"

NOMBRES_TITULACION = {
    "GII-IC": "Ingeniería de Computadores",
    "GII-IS": "Ingeniería del Software",
    "GII-TI": "Tecnologías Informáticas",
}

DIAS_NOMBRE = {1: "Lunes", 2: "Martes", 3: "Miércoles", 4: "Jueves", 5: "Viernes"}

DIAS_SEMANA = {
    "lunes": 1, "martes": 2, "miercoles": 3, "miércoles": 3,
    "jueves": 4, "viernes": 5,
}


# ─── Utilidades de detección ─────────────────────────────────────────────────

def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower().strip()


def _detectar_curso(texto: str) -> Optional[int]:
    texto_lower = texto.lower()
    patrones = [
        (r"\b(\d)[ºª°]\b", lambda m: int(m.group(1))),
        (r"\bcurso\s+(\d)\b", lambda m: int(m.group(1))),
        (r"\bprimero\b", lambda m: 1),
        (r"\bsegundo\b", lambda m: 2),
        (r"\btercero\b", lambda m: 3),
        (r"\bcuarto\b", lambda m: 4),
        (r"\b1er\b", lambda m: 1),
        (r"\b2do\b", lambda m: 2),
        (r"\b3er\b", lambda m: 3),
        (r"\b4to\b", lambda m: 4),
    ]
    for patron, extractor in patrones:
        m = re.search(patron, texto_lower)
        if m:
            val = extractor(m)
            if 1 <= val <= 4:
                return val
    return None


def _detectar_grupo(texto: str) -> Optional[int]:
    texto_lower = texto.lower()
    m = re.search(r"\bgrupo\s+(\d+)\b", texto_lower)
    if m:
        return int(m.group(1))
    m = re.search(r"\bg(\d+)\b", texto_lower)
    if m:
        return int(m.group(1))
    return None


# Patron "letra X del DNI" / "inicial de apellido": el usuario no sabe su
# numero de grupo y pregunta por la letra. Detectamos la presencia para no
# interpretar la letra como alias de asignatura (ej. T = Teledeteccion).
_RE_LETRA_DNI = re.compile(
    r"letra\s+([a-zñ])(?:\s+(?:de|del)\s+(?:mi\s+)?dni|\s+de\s+apellido|\s+inicial)?",
    re.IGNORECASE,
)


def _tiene_referencia_letra_dni(texto: str) -> bool:
    """True si el usuario se refiere a grupos por letra del DNI/apellido."""
    return bool(_RE_LETRA_DNI.search(texto or ""))


def _detectar_dia(texto: str) -> Optional[int]:
    texto_norm = _normalizar(texto)
    for dia_txt, dia_num in DIAS_SEMANA.items():
        if dia_txt in texto_norm:
            return dia_num
    return None


def _detectar_cuatrimestre(texto: str) -> Optional[int]:
    texto_lower = texto.lower()
    patrones = [
        (r"\bc(?:uatrimestre)?\s*1\b", 1),
        (r"\bc(?:uatrimestre)?\s*2\b", 2),
        (r"\bprimer\s+cuatrimestre\b", 1),
        (r"\bsegundo\s+cuatrimestre\b", 2),
    ]
    for patron, val in patrones:
        if re.search(patron, texto_lower):
            return val
    return None


# ─── Queries a la BD ─────────────────────────────────────────────────────────

def _query_horario(titulacion: str, curso: int, grupo: int,
                   dia: Optional[int] = None,
                   cuatrimestre: Optional[int] = None) -> list:
    """
    Consulta horarios de un curso/grupo de una titulación.
    Retorna [(dia_semana, hora_inicio, hora_fin, asignatura, aula_codigo, duracion)]
    """
    conn = db_client.get_connection()
    if not conn:
        return []

    try:
        cur = conn.cursor()
        sql = """
            SELECT
                h.dia_semana,
                h.hora_inicio,
                h.hora_fin,
                a.nombre AS asignatura,
                COALESCE(au.codigo, '') AS aula,
                a.duracion
            FROM horarios h
            JOIN grupos_clase gc ON h.grupo_id = gc.id
            JOIN asignaturas a ON gc.asignatura_id = a.id
            JOIN titulaciones t ON a.titulacion_id = t.id
            LEFT JOIN aulas au ON h.aula_id = au.id
            WHERE t.codigo = %s
              AND a.curso = %s
              AND gc.codigo = %s
              AND h.activo = true
        """
        params = [titulacion, curso, str(grupo)]

        if dia:
            sql += " AND h.dia_semana = %s"
            params.append(dia)

        if cuatrimestre:
            sql += " AND a.duracion IN (%s, 'A')"
            params.append(f"C{cuatrimestre}")

        sql += " GROUP BY h.dia_semana, h.hora_inicio, h.hora_fin, a.nombre, au.codigo, a.duracion"
        sql += " ORDER BY h.dia_semana, h.hora_inicio, a.nombre"

        cur.execute(sql, params)
        resultados = cur.fetchall()
        cur.close()
        conn.close()
        return resultados
    except Exception as e:
        print(f"Error consultando horarios: {e}")
        if conn:
            conn.close()
        return []


def _query_asignatura(titulacion: str, alias_asig: str,
                      grupo: Optional[int] = None) -> list:
    """
    Busca horarios de una asignatura específica por su alias.
    Retorna [(dia_semana, hora_inicio, hora_fin, asignatura, aula, grupo_codigo, curso)]
    """
    nombre_norm = ALIAS_ASIGNATURAS.get(alias_asig.lower())
    if not nombre_norm:
        return []

    conn = db_client.get_connection()
    if not conn:
        return []

    try:
        cur = conn.cursor()
        sql = """
            SELECT
                h.dia_semana,
                h.hora_inicio,
                h.hora_fin,
                a.nombre AS asignatura,
                COALESCE(au.codigo, '') AS aula,
                gc.codigo AS grupo,
                a.curso
            FROM horarios h
            JOIN grupos_clase gc ON h.grupo_id = gc.id
            JOIN asignaturas a ON gc.asignatura_id = a.id
            JOIN titulaciones t ON a.titulacion_id = t.id
            LEFT JOIN aulas au ON h.aula_id = au.id
            WHERE t.codigo = %s
              AND a.nombre_normalizado LIKE %s
              AND h.activo = true
        """
        params = [titulacion, f"%{nombre_norm}%"]

        if grupo:
            sql += " AND gc.codigo = %s"
            params.append(str(grupo))

        sql += " GROUP BY h.dia_semana, h.hora_inicio, h.hora_fin, a.nombre, au.codigo, gc.codigo, a.curso"
        sql += " ORDER BY gc.codigo, h.dia_semana, h.hora_inicio"

        cur.execute(sql, params)
        resultados = cur.fetchall()
        cur.close()
        conn.close()
        return resultados
    except Exception as e:
        print(f"Error buscando asignatura en horarios: {e}")
        if conn:
            conn.close()
        return []


def _query_grupos_de_asignatura(titulacion: str, alias_asig: str) -> tuple[Optional[str], list]:
    """
    Dada una asignatura, devuelve (nombre_real, [grupos_codigo]) en esa titulacion.
    Sirve para dar un mensaje claro cuando el usuario pide un grupo que no existe.
    """
    nombre_norm = ALIAS_ASIGNATURAS.get(alias_asig.lower())
    if not nombre_norm:
        return None, []
    conn = db_client.get_connection()
    if not conn:
        return None, []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT a.nombre, gc.codigo
            FROM grupos_clase gc
            JOIN asignaturas a ON gc.asignatura_id = a.id
            JOIN titulaciones t ON a.titulacion_id = t.id
            WHERE t.codigo = %s
              AND a.nombre_normalizado LIKE %s
              AND gc.activo = true
            GROUP BY a.nombre, gc.codigo
            ORDER BY gc.codigo
        """, (titulacion, f"%{nombre_norm}%"))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        if not rows:
            return None, []
        nombre_real = rows[0][0]
        grupos = [r[1] for r in rows]
        return nombre_real, grupos
    except Exception as e:
        print(f"Error consultando grupos de asignatura: {e}")
        if conn:
            conn.close()
        return None, []


def _query_grupos_disponibles(titulacion: str, curso: int) -> list:
    """Retorna los grupos disponibles para un curso/titulación."""
    conn = db_client.get_connection()
    if not conn:
        return []

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT gc.codigo
            FROM grupos_clase gc
            JOIN asignaturas a ON gc.asignatura_id = a.id
            JOIN titulaciones t ON a.titulacion_id = t.id
            WHERE t.codigo = %s AND a.curso = %s AND gc.activo = true
            ORDER BY gc.codigo
        """, (titulacion, curso))
        grupos = [int(row[0]) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return grupos
    except Exception as e:
        print(f"Error consultando grupos: {e}")
        if conn:
            conn.close()
        return []


# ─── Formateo de datos para el LLM ───────────────────────────────────────────

def _respuesta_faltan_datos(titulacion: str, curso: Optional[int] = None,
                            grupo: Optional[int] = None) -> str:
    """Respuesta cuando falta curso y/o grupo."""
    nombre = NOMBRES_TITULACION.get(titulacion, titulacion)

    faltan = []
    if not curso:
        faltan.append("**curso** (1º, 2º, 3º o 4º)")
    if not grupo:
        faltan.append("**grupo**")

    msg = f"Para consultar el horario necesito que me digas: {' y '.join(faltan)}."

    if curso and not grupo:
        grupos = _query_grupos_disponibles(titulacion, curso)
        if grupos:
            lista = ", ".join(str(g) for g in grupos)
            msg += f"\n\nEn {curso}º de {nombre} hay grupos: {lista}."

    ejemplo_curso = curso or 2
    ejemplo_grupo = grupo or 1
    msg += f"\n\nDime por ejemplo: *horario de {ejemplo_curso}º grupo {ejemplo_grupo}*"
    msg += (
        f"\n\nO consulta el PDF completo:"
        f"\n[Horarios ETSII 2025-26]({PDF_HORARIOS_URL})"
    )
    return msg


def _datos_horario_a_texto(resultados: list, titulacion: str,
                            curso: int, grupo: int,
                            dia_filtro: Optional[int] = None) -> str:
    """Convierte resultados de query de horario en texto plano para el LLM."""
    nombre = NOMBRES_TITULACION.get(titulacion, titulacion)
    lineas = [f"Horario de {curso}º de {nombre}, Grupo {grupo}:"]

    if not resultados:
        return "No hay horarios registrados para esta combinación."

    por_dia = {}
    for dia, h_ini, h_fin, asig, aula, duracion in resultados:
        if dia not in por_dia:
            por_dia[dia] = []
        aula_txt = f" en aula {aula}" if aula else ""
        por_dia[dia].append(f"{str(h_ini)[:5]}-{str(h_fin)[:5]}: {asig}{aula_txt}")

    dias_mostrar = [dia_filtro] if dia_filtro else sorted(por_dia.keys())
    for dia in dias_mostrar:
        if dia not in por_dia:
            continue
        lineas.append(f"\n{DIAS_NOMBRE.get(dia, dia)}:")
        for entrada in por_dia[dia]:
            lineas.append(f"  - {entrada}")

    return "\n".join(lineas)


def _datos_asignatura_a_texto(resultados: list, alias: str,
                               titulacion: str) -> str:
    """Convierte resultados de búsqueda por asignatura en texto plano para el LLM."""
    nombre_tit = NOMBRES_TITULACION.get(titulacion, titulacion)

    if not resultados:
        return f"No se encontró {alias.upper()} en los horarios de {nombre_tit}."

    nombre_asig = resultados[0][3]
    lineas = [f"Horarios de {nombre_asig} en {nombre_tit}:"]

    for dia, h_ini, h_fin, asig, aula, grupo_cod, curso in resultados:
        dia_txt = DIAS_NOMBRE.get(dia, str(dia))
        aula_txt = f", aula {aula}" if aula else ""
        lineas.append(f"  - Curso {curso} Grupo {grupo_cod}: {dia_txt} {str(h_ini)[:5]}-{str(h_fin)[:5]}{aula_txt}")

    return "\n".join(lineas)


# ─── Generación de respuesta con LLM ────────────────────────────────────────

def _generar_respuesta_horario(pregunta: str, datos_texto: str) -> str:
    """
    Usa el LLM para generar una respuesta natural a partir de los datos de horario.
    Mismo patrón que generar_respuesta_natural en asignaturas.
    """
    prompt = f"""Eres Linceus, un asistente universitario de la ETSII (Universidad de Sevilla).
Responde a la pregunta del usuario usando SOLO los datos proporcionados.

PREGUNTA DEL USUARIO: "{pregunta}"

DATOS DE HORARIOS:
{datos_texto}

REGLAS:
- Responde de forma natural, cercana y concisa
- Presenta los horarios de forma organizada y legible, agrupados por día
- Incluye siempre el aula cuando esté disponible
- Usa markdown para formatear (negritas, listas)
- No inventes datos que no estén proporcionados
- Si no hay resultados, dilo amablemente
- No repitas la pregunta del usuario
- No digas "según los datos" ni menciones la base de datos
- No saludes (nada de "¡Hola!", "Hola!", "Buenos días", etc.) — ve directo a la respuesta
- Si hay muchas entradas, organízalas bien para que sea fácil de leer
- IMPORTANTE: Tu respuesta debe tener como MÁXIMO 1500 caracteres. Si los datos son muy extensos, resume agrupando de forma compacta

Respuesta:"""

    try:
        respuesta = llamar_llm(
            prompt,
            timeout=120,
            options={
                "temperature": 0.3,
                "num_predict": 800,
                "num_ctx": 4096,
            }
        )
        if respuesta:
            return respuesta.strip()
    except Exception as e:
        print(f"Error generando respuesta de horarios con LLM: {e}")

    # Fallback: devolver los datos en texto plano
    return datos_texto


# ─── Action de Rasa ──────────────────────────────────────────────────────────

class ActionConsultaHorario(Action):
    """
    Maneja consultas de horario personal: requiere curso y grupo.
    Si faltan, pide al usuario que los especifique.
    """

    def name(self) -> Text:
        return "action_consulta_horario"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        mensaje = tracker.latest_message.get("text", "")

        titulacion, eventos_tit = comprobar_titulacion(tracker, dispatcher)
        if not titulacion:
            return eventos_tit

        curso = _detectar_curso(mensaje)
        grupo = _detectar_grupo(mensaje)
        dia = _detectar_dia(mensaje)
        cuatrimestre = _detectar_cuatrimestre(mensaje)

        # Si el usuario se refiere a grupos por letra del DNI (ej. "letra T"),
        # no podemos mapearlo automaticamente: los grupos por letra cambian por
        # titulacion y curso. Mejor pedir el numero de grupo directamente.
        if _tiene_referencia_letra_dni(mensaje) and not grupo:
            dispatcher.utter_message(
                text=("La asignación de grupos por letra del DNI varía cada curso "
                      "y titulación, así que no puedo deducir tu grupo con certeza. "
                      "¿Puedes decirme directamente el **número de grupo** (1, 2, 3…)? "
                      "Lo encontrarás en SEVIUS o en el tablón de la ETSII.")
            )
            return []

        print(f"\n{'='*60}")
        print(f"📅 CONSULTA HORARIO PERSONAL: {mensaje}")
        print(f"   Titulación: {titulacion} | Curso: {curso} | Grupo: {grupo} | Día: {dia} | Cuatri: {cuatrimestre}")
        print(f"{'='*60}")

        # ── Si el NLU detectó una asignatura, redirigir a ActionConsultaEspecifica ──
        tiene_asignatura = any(
            e.get("entity") == "nombre_asignatura"
            for e in tracker.latest_message.get("entities", [])
        )
        if not tiene_asignatura:
            # Fallback: buscar alias en el texto por si el NLU no lo extrajo como entidad
            texto_lower = mensaje.lower()
            aliases_ordenados = sorted(ALIAS_ASIGNATURAS.keys(), key=len, reverse=True)
            # Excluir alias cortos que son palabras comunes del español
            # SALVO cuando el contexto lo convierte claramente en asignatura
            # (precedido por "asignatura", "de la", "horario de", etc.).
            STOP_WORDS = {'e', 'c', 't', 'y', 'o', 'a'}
            CONTEXTO_ASIGNATURA = (
                r'(?:asignatura\s+(?:de\s+)?|horario\s+de\s+(?:la\s+)?|'
                r'aula\s+de\s+|clase\s+de\s+|materia\s+(?:de\s+)?)'
            )
            for alias in aliases_ordenados:
                # Alias corto (≤2) y en stop list: exigir contexto explícito
                if len(alias) <= 2 and alias in STOP_WORDS:
                    pat_contexto = CONTEXTO_ASIGNATURA + re.escape(alias) + r'\b'
                    if re.search(pat_contexto, texto_lower):
                        tiene_asignatura = True
                        print(f"   → Alias corto con contexto: '{alias}'")
                        break
                    continue
                # 'si' no está en STOP_WORDS: es alias real de Sistemas de
                # Información. Lo aceptamos si aparece como palabra completa.
                if re.search(r'\b' + re.escape(alias) + r'\b', texto_lower):
                    tiene_asignatura = True
                    print(f"   → Alias detectado en texto: '{alias}'")
                    break

        if tiene_asignatura:
            print(f"   → Redirigiendo a ActionConsultaEspecifica (detectada asignatura)")
            from ..asignaturas.actions import ActionConsultaEspecifica
            action_especifica = ActionConsultaEspecifica()
            return action_especifica.run(dispatcher, tracker, domain)

        # ── Follow-up: sin asignatura ni curso/grupo, pero con slot reciente ──
        # Ej: tras "hablame de DP1" -> "que horario tiene?". Heredamos la
        # asignatura del slot y redirigimos a ActionConsultaEspecifica para
        # que use el flujo de horario por asignatura.
        if not curso and not grupo:
            ultimo_asig = tracker.get_slot("ultimo_nombre_asignatura")
            if ultimo_asig:
                turnos = _contar_turnos_desde_slot(tracker, "ultimo_nombre_asignatura")
                if turnos <= 3:
                    print(f"   → Seguimiento horario: heredando asignatura "
                          f"'{ultimo_asig}' del slot ({turnos} turnos)")
                    from ..asignaturas.actions import ActionConsultaEspecifica
                    action_especifica = ActionConsultaEspecifica()
                    return action_especifica.run(dispatcher, tracker, domain)

        # ── Follow-up: rellena curso/grupo parciales con slots recientes ──
        # Ej: tras "horario de 2 grupo 1" -> "y del grupo 2?".
        if not curso:
            ultimo_curso = tracker.get_slot("ultimo_curso_consultado")
            if ultimo_curso and _contar_turnos_desde_slot(
                tracker, "ultimo_curso_consultado") <= 3:
                try:
                    curso = int(ultimo_curso)
                    print(f"   → Seguimiento horario: heredando curso {curso}")
                except (TypeError, ValueError):
                    pass
        if not grupo:
            ultimo_grupo = tracker.get_slot("ultimo_grupo_consultado")
            if ultimo_grupo and _contar_turnos_desde_slot(
                tracker, "ultimo_grupo_consultado") <= 3:
                try:
                    grupo = int(ultimo_grupo)
                    print(f"   → Seguimiento horario: heredando grupo {grupo}")
                except (TypeError, ValueError):
                    pass

        # ── Se requiere curso y grupo ──
        if not curso or not grupo:
            dispatcher.utter_message(
                text=_respuesta_faltan_datos(titulacion, curso, grupo)
            )
            return []

        resultados = _query_horario(titulacion, curso, grupo, dia, cuatrimestre)
        datos_texto = _datos_horario_a_texto(
            resultados, titulacion, curso, grupo, dia
        )
        respuesta = _generar_respuesta_horario(mensaje, datos_texto)
        dispatcher.utter_message(text=respuesta)
        # Persistir curso/grupo consultados para follow-ups posteriores
        return [
            SlotSet("ultimo_curso_consultado", curso),
            SlotSet("ultimo_grupo_consultado", grupo),
            SlotSet("ultima_action_ejecutada", "action_consulta_horario"),
        ]
