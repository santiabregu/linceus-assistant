"""
Actions de Rasa para consultas de horarios personales (curso + grupo).
Consulta la BD (tablas horarios, grupos_clase, asignaturas, aulas) y responde
preguntas como:
  - "¿Qué horario tiene 2º de Computadores grupo 1?"
  - "¿Qué clases hay los lunes en primero grupo 2?"

Requiere curso y grupo. Si el usuario no los da, se le piden.
Las consultas de horario de asignaturas concretas ("¿cuándo tengo FP?",
"¿en qué aula es ADDA?") se gestionan desde
`ActionConsultaHorarioAsignatura` (módulo asignaturas, intent
`consulta_horario_asignatura`).
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

DIAS_NOMBRE = {1: "Lunes", 2: "Martes", 3: "Miércoles", 4: "Jueves", 5: "Viernes",
               6: "Sábado", 7: "Domingo"}

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
        # Ordinales tipográficos: 2º, 2ª, 2°
        (r"\b(\d)[ºª°]\b", lambda m: int(m.group(1))),
        # Aproximaciones sin tecla de ordinal: 2o, 2a (en teclados sin "º")
        (r"\b(\d)[oa]\b", lambda m: int(m.group(1))),
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


# Convención ETSII: aulas con código que empieza por 'A' son teoría;
# las demás (F, B, G, H, I, ...) son laboratorio.
def _es_aula_teoria(codigo: str) -> bool:
    return bool(codigo) and codigo.startswith("A")


def _detectar_filtro_aula(texto: str) -> Optional[str]:
    """Detecta si la pregunta pide solo lab o solo teoría.

    Devuelve 'lab', 'teoria' o None (sin filtro). No se usa "prácticas"
    porque colisiona con la asignatura "Prácticas Externas" y con la
    expresión genérica "clases teórico-prácticas" del plan docente.
    """
    if not texto:
        return None
    t = unicodedata.normalize("NFKD", texto.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    if re.search(r"\blab(oratorio)?s?\b", t):
        return "lab"
    if re.search(r"\bteori[ck]?as?\b", t):
        return "teoria"
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


def _cuatrimestre_actual_por_fecha() -> Optional[int]:
    """Mapeo del calendario académico US Sevilla:
       - septiembre..enero → C1
       - febrero..julio    → C2
       - agosto            → None (sin docencia, mostrar todo)

    Cuando el usuario no especifica cuatrimestre, el bot asume el activo
    según `now()`. Ver D-066 / D-067.
    """
    from datetime import datetime
    mes = datetime.now().month
    if mes in (9, 10, 11, 12, 1):
        return 1
    if mes in (2, 3, 4, 5, 6, 7):
        return 2
    return None  # agosto


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
                a.duracion,
                h.cuatrimestre
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
            # Filtro directo por cuatrimestre del horario (D-066). Antes se
            # filtraba por `a.duracion`, lo que rompía con anuales (siempre
            # pasaban) y con horarios donde la asignatura cambiaba de
            # día/hora entre C1 y C2.
            sql += " AND h.cuatrimestre = %s"
            params.append(str(cuatrimestre))

        # Incluimos h.cuatrimestre en el GROUP BY: sin él, anuales como FP
        # con la misma franja en C1 y C2 (mié 10:40) se colapsarían en una
        # fila aunque sean dos sesiones distintas.
        sql += (" GROUP BY h.dia_semana, h.hora_inicio, h.hora_fin, "
                "a.nombre, au.codigo, a.duracion, h.cuatrimestre")
        sql += " ORDER BY h.cuatrimestre, h.dia_semana, h.hora_inicio, a.nombre"

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
                      grupo: Optional[int] = None,
                      cuatrimestre: Optional[int] = None) -> list:
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
                a.curso,
                h.cuatrimestre
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

        if cuatrimestre:
            sql += " AND h.cuatrimestre = %s"
            params.append(str(cuatrimestre))

        # h.cuatrimestre en GROUP BY para no colapsar anuales que se imparten
        # en la misma franja en C1 y C2 (D-066).
        sql += (" GROUP BY h.dia_semana, h.hora_inicio, h.hora_fin, "
                "a.nombre, au.codigo, gc.codigo, a.curso, h.cuatrimestre")
        sql += " ORDER BY gc.codigo, h.cuatrimestre, h.dia_semana, h.hora_inicio"

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
                            dia_filtro: Optional[int] = None,
                            cuatrimestre: Optional[int] = None,
                            cuatri_explicito: bool = True,
                            filtro_aula: Optional[str] = None) -> str:
    """Convierte resultados de query de horario en texto plano para el LLM.

    Si `cuatrimestre` está fijado y `cuatri_explicito=False`, añade un aviso
    al header indicando que se asumió por la fecha actual (D-067).
    """
    nombre = NOMBRES_TITULACION.get(titulacion, titulacion)
    header = f"Horario de {curso}º de {nombre}, Grupo {grupo}"
    if cuatrimestre:
        header += f" — Cuatrimestre {cuatrimestre}"
        if not cuatri_explicito:
            header += " (cuatrimestre activo según fecha actual)"
    header += ":"
    lineas = [header]

    if not resultados:
        return "No hay horarios registrados para esta combinación."

    # Agrupamos por slot (dia, hora, asig, cuatri) porque tras D-068 cada
    # aula del slot es una fila distinta en `horarios` (teoría + labs).
    slots = {}  # (dia, h_ini, h_fin, asig, h_cuatri) -> {aulas_teoria, aulas_lab}
    for dia, h_ini, h_fin, asig, aula, duracion, h_cuatri in resultados:
        key = (dia, h_ini, h_fin, asig, h_cuatri)
        if key not in slots:
            slots[key] = {"teoria": [], "lab": []}
        if aula:
            categoria = "teoria" if _es_aula_teoria(aula) else "lab"
            if aula not in slots[key][categoria]:
                slots[key][categoria].append(aula)

    por_dia = {}
    for (dia, h_ini, h_fin, asig, h_cuatri), aulas in slots.items():
        # Si el usuario pidió solo lab/teoría y este slot no tiene ese tipo,
        # lo omitimos del resultado.
        if filtro_aula == "lab" and not aulas["lab"]:
            continue
        if filtro_aula == "teoria" and not aulas["teoria"]:
            continue
        if dia not in por_dia:
            por_dia[dia] = []
        partes_aula = []
        if filtro_aula in (None, "teoria") and aulas["teoria"]:
            partes_aula.append("teoría: " + ", ".join(sorted(aulas["teoria"])))
        if filtro_aula in (None, "lab") and aulas["lab"]:
            partes_aula.append("lab: " + ", ".join(sorted(aulas["lab"])))
        aula_txt = f" ({'; '.join(partes_aula)})" if partes_aula else ""
        cuatri_txt = f" [C{h_cuatri}]" if (not cuatrimestre and h_cuatri) else ""
        por_dia[dia].append(
            (h_ini, f"{str(h_ini)[:5]}-{str(h_fin)[:5]}: {asig}{aula_txt}{cuatri_txt}")
        )

    dias_mostrar = [dia_filtro] if dia_filtro else sorted(por_dia.keys())
    for dia in dias_mostrar:
        if dia not in por_dia:
            continue
        lineas.append(f"\n{DIAS_NOMBRE.get(dia, dia)}:")
        for _, entrada in sorted(por_dia[dia], key=lambda x: x[0]):
            lineas.append(f"  - {entrada}")

    if len(lineas) == 1:  # solo header, todos los slots filtrados
        if filtro_aula == "lab":
            return "No hay sesiones de laboratorio registradas para esta combinación."
        if filtro_aula == "teoria":
            return "No hay sesiones de teoría registradas para esta combinación."

    return "\n".join(lineas)


def _datos_asignatura_a_texto(resultados: list, alias: str,
                               titulacion: str,
                               filtro_aula: Optional[str] = None) -> str:
    """Convierte resultados de búsqueda por asignatura en texto plano para el LLM.

    Tras D-068 cada aula del slot es una fila distinta en `horarios`. Aquí
    agrupamos por (curso, grupo, día, hora, cuatri) y unimos las aulas
    separando teoría (códigos que empiezan por 'A') de lab (resto). Si
    `filtro_aula` viene informado, omite los slots que no tienen ese tipo
    y oculta las aulas del tipo opuesto.
    """
    nombre_tit = NOMBRES_TITULACION.get(titulacion, titulacion)

    if not resultados:
        return f"No se encontró {alias.upper()} en los horarios de {nombre_tit}."

    nombre_asig = resultados[0][3]

    # Agrupar por (curso, grupo, día, h_ini, h_fin, cuatri) → aulas
    slots = {}
    for dia, h_ini, h_fin, asig, aula, grupo_cod, curso, h_cuatri in resultados:
        key = (curso, grupo_cod, dia, h_ini, h_fin, h_cuatri)
        if key not in slots:
            slots[key] = {"teoria": [], "lab": []}
        if aula:
            categoria = "teoria" if _es_aula_teoria(aula) else "lab"
            if aula not in slots[key][categoria]:
                slots[key][categoria].append(aula)

    encabezado = f"Horarios de {nombre_asig} en {nombre_tit}"
    if filtro_aula == "lab":
        encabezado += " (solo laboratorio)"
    elif filtro_aula == "teoria":
        encabezado += " (solo teoría)"
    lineas = [encabezado + ":"]

    # Orden estable: curso, grupo, cuatri, día, hora.
    for key in sorted(slots.keys(),
                      key=lambda k: (k[0], k[1], k[5] or "", k[2], k[3])):
        curso, grupo_cod, dia, h_ini, h_fin, h_cuatri = key
        aulas = slots[key]
        if filtro_aula == "lab" and not aulas["lab"]:
            continue
        if filtro_aula == "teoria" and not aulas["teoria"]:
            continue
        partes_aula = []
        if filtro_aula in (None, "teoria") and aulas["teoria"]:
            partes_aula.append("teoría: " + ", ".join(sorted(aulas["teoria"])))
        if filtro_aula in (None, "lab") and aulas["lab"]:
            partes_aula.append("lab: " + ", ".join(sorted(aulas["lab"])))
        aula_txt = f" ({'; '.join(partes_aula)})" if partes_aula else ""
        cuatri_txt = f" [C{h_cuatri}]" if h_cuatri else ""
        dia_txt = DIAS_NOMBRE.get(dia, str(dia))
        lineas.append(
            f"  - Curso {curso} Grupo {grupo_cod}{cuatri_txt}: "
            f"{dia_txt} {str(h_ini)[:5]}-{str(h_fin)[:5]}{aula_txt}"
        )

    if len(lineas) == 1:  # solo header
        if filtro_aula == "lab":
            return f"No hay sesiones de laboratorio de {nombre_asig} registradas."
        if filtro_aula == "teoria":
            return f"No hay sesiones de teoría de {nombre_asig} registradas."

    return "\n".join(lineas)


# ─── Generación de respuesta con LLM ────────────────────────────────────────

def _generar_respuesta_horario(pregunta: str, datos_texto: str) -> str:
    """
    Usa el LLM para generar una respuesta natural a partir de los datos de horario.
    Mismo patrón que generar_respuesta_natural en asignaturas.
    """
    from datetime import datetime
    ahora = datetime.now()
    dia_actual = DIAS_NOMBRE.get(ahora.isoweekday(), "?")
    fecha_actual = ahora.strftime("%Y-%m-%d")

    prompt = f"""Eres Linceus, un asistente universitario de la ETSII (Universidad de Sevilla).
Responde a la pregunta del usuario usando SOLO los datos proporcionados.

FECHA ACTUAL: {dia_actual}, {fecha_actual}.

PREGUNTA DEL USUARIO: "{pregunta}"

DATOS DE HORARIOS:
{datos_texto}

REGLAS:
- Responde de forma natural, cercana y concisa
- Presenta los horarios de forma organizada y legible, agrupados por día
- Incluye siempre el aula cuando esté disponible
- Usa markdown para formatear (negritas, listas)
- **PROHIBIDO INVENTAR DATOS.** Si los datos no contienen aulas, asignaturas o
  franjas horarias para lo que el usuario pide, NO las completes con valores
  plausibles. Di que no hay horarios registrados para esa combinación.
- Si la pregunta usa referencias temporales relativas ("hoy", "mañana", "esta
  tarde", "ahora"), interprétalas SIEMPRE respecto a la FECHA ACTUAL indicada
  arriba. No inventes ni asumas otro día. Si la fecha actual cae en sábado o
  domingo, no hay clases.
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

        # Si el usuario no especifica cuatrimestre, asumimos el activo según
        # `now()` (D-066, D-067). Si ambos cuatrimestres son interesantes
        # (agosto, sin docencia), `cuatri_actual` queda en None y la query
        # devuelve todo.
        cuatri_explicito = cuatrimestre is not None
        if not cuatri_explicito:
            cuatrimestre = _cuatrimestre_actual_por_fecha()

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
        cuatri_origen = "explícito" if cuatri_explicito else ("auto" if cuatrimestre else "ninguno")
        print(f"   Titulación: {titulacion} | Curso: {curso} | Grupo: {grupo} | "
              f"Día: {dia} | Cuatri: {cuatrimestre} ({cuatri_origen})")
        print(f"{'='*60}")

        # Nota: las preguntas "horario de ASIGNATURA" las clasifica el NLU
        # como `consulta_horario_asignatura` y las gestiona
        # `ActionConsultaHorarioAsignatura` (módulo asignaturas). Aquí solo
        # procesamos horario por curso+grupo.

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

        # ── Seguimiento cross-intent (H-S01): turno elíptico tipo
        # "y qué horario tiene" tras una asignatura. Solo delegamos cuando el
        # mensaje NO aporta ninguna pista de horario por curso+grupo (ni
        # curso, ni grupo, ni día, ni cuatrimestre). Si el usuario dice
        # "grupo 1" o "los lunes", la pregunta es genérica y solo le falta el
        # curso: ahí pedimos curso, no heredamos asignatura.
        sin_pistas_horario = not (curso or grupo or dia or cuatri_explicito)
        if sin_pistas_horario:
            ultima_asig = tracker.get_slot("ultimo_nombre_asignatura")
            if ultima_asig and _contar_turnos_desde_slot(
                tracker, "ultimo_nombre_asignatura") <= 3:
                from ..asignaturas.actions import ActionConsultaHorarioAsignatura
                print(f"   → H-S01: delegando a horario_asignatura "
                      f"(asignatura heredada: '{ultima_asig}')")
                return ActionConsultaHorarioAsignatura().run(
                    dispatcher, tracker, domain
                )

        # ── Se requiere curso y grupo ──
        if not curso or not grupo:
            dispatcher.utter_message(
                text=_respuesta_faltan_datos(titulacion, curso, grupo)
            )
            return []

        resultados = _query_horario(titulacion, curso, grupo, dia, cuatrimestre)
        filtro_aula = _detectar_filtro_aula(mensaje)
        datos_texto = _datos_horario_a_texto(
            resultados, titulacion, curso, grupo, dia,
            cuatrimestre=cuatrimestre, cuatri_explicito=cuatri_explicito,
            filtro_aula=filtro_aula,
        )
        respuesta = _generar_respuesta_horario(mensaje, datos_texto)
        dispatcher.utter_message(text=respuesta)
        # Persistir curso/grupo consultados para follow-ups posteriores
        return [
            SlotSet("ultimo_curso_consultado", curso),
            SlotSet("ultimo_grupo_consultado", grupo),
            SlotSet("ultima_action_ejecutada", "action_consulta_horario"),
        ]
