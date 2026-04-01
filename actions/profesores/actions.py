"""
Actions de Rasa para consultas sobre profesores.
Usa Text-to-SQL (LLM genera queries) para responder:
  - "Tutorías del profesor Parejo"
  - "Correo de la profesora Diana que da FP"
  - "Profesores del departamento LSI"
  - "Despacho de Ruiz Cortés"

La asignatura se usa como contexto para identificar al profesor cuando el
usuario no sabe el apellido completo (ej: "correo de Belén que da FP").

Flujo:
  1. Extraer entidades (nombre_profesor, nombre_asignatura, nombre_departamento)
  2. Follow-up si no hay entidades (slot recency ≤3 turnos)
  3. LLM clasifica si necesita RAG (asignatura como contexto para resolver profesor)
  4. Si RAG → plan docente → extraer nombres → match en BD profesores → info contacto
  5. Si no RAG → LLM genera query SQL → ejecutar → enriquecer con tutorías
  6. LLM genera respuesta natural
"""

import unicodedata
from typing import Any, Text, Dict, List, Optional

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from ..shared.config import ALIAS_ASIGNATURAS, ALIAS_POR_TITULACION
from ..shared.db import db_client
from ..shared.gemini_client import llamar_gemini as llamar_llm

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from profesores_data.text_to_sql import (
    generar_sql_profesor,
    ejecutar_query,
    formatear_datos_para_prompt,
    generar_respuesta_natural,
)


# ─── Utilidades ──────────────────────────────────────────────────────────────

def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower().strip()


def _contar_turnos_desde_slot(tracker, slot_name: str) -> int:
    turnos = 0
    for event in reversed(tracker.events):
        if event.get("event") == "user":
            turnos += 1
        if event.get("event") == "slot" and event.get("name") == slot_name:
            return turnos
    return 999


def _expandir_alias_asignatura(nombre: str, titulacion: str = None) -> str:
    """Expande alias de asignatura (fp → fundamentos de programacion)."""
    if not nombre:
        return nombre
    nombre_lower = nombre.lower().strip()
    if titulacion and titulacion in ALIAS_POR_TITULACION:
        if nombre_lower in ALIAS_POR_TITULACION[titulacion]:
            return ALIAS_POR_TITULACION[titulacion][nombre_lower]
    if nombre_lower in ALIAS_ASIGNATURAS:
        return ALIAS_ASIGNATURAS[nombre_lower]
    return nombre


def _extraer_nombre_profesor_con_llm(pregunta: str, nombre_asignatura: str) -> Optional[str]:
    """Pide al LLM que extraiga el nombre del profesor de la pregunta.
    Útil cuando el NLU no detectó la entidad nombre_profesor pero
    hay un nombre de persona en el texto (ej: 'correo de belen de dp1')."""
    prompt = f"""Extrae SOLO el nombre de la persona (profesor/a) de la siguiente pregunta.
La asignatura mencionada es "{nombre_asignatura}", NO la incluyas.

PREGUNTA: "{pregunta}"

Si hay un nombre de persona, devuelve SOLO ese nombre (sin comillas, sin explicaciones).
Si NO hay nombre de persona, devuelve: NONE

Nombre:"""

    respuesta = llamar_llm(
        prompt, timeout=10,
        options={"temperature": 0.0, "num_predict": 20}
    )
    if respuesta:
        nombre = respuesta.strip().strip('"').strip("'")
        if nombre and nombre.upper() != "NONE" and len(nombre) > 1:
            return nombre
    return None


def _resolver_asignatura_contexto(
    pregunta: str, tracker: Tracker, titulacion: str
) -> Optional[Dict]:
    """Reutiliza el pipeline completo de resolución de asignaturas
    (NLU entity → alias → fuzzy BD → fallbacks) para identificar
    la asignatura mencionada como contexto.
    Returns: dict con codigo, nombre, etc. o None."""
    try:
        from ..asignaturas.actions import resolver_asignatura
        asignatura, nombre_usado = resolver_asignatura(
            pregunta, tracker, titulacion or "", usar_seguimiento=False
        )
        if asignatura:
            print(f"  → Asignatura resuelta: {asignatura.get('nombre')} (via pipeline asignaturas)")
        return asignatura
    except Exception as e:
        print(f"  ⚠ Error resolviendo asignatura: {e}")
        return None


def _extraer_entidades(tracker: Tracker) -> Dict[str, Optional[str]]:
    """Extrae nombre_profesor, nombre_asignatura y nombre_departamento."""
    entities = tracker.latest_message.get("entities", [])

    nombre_profesor = None
    nombre_asignatura = None
    nombre_departamento = None

    for ent in entities:
        if ent["entity"] == "nombre_profesor" and not nombre_profesor:
            nombre_profesor = ent["value"]
        elif ent["entity"] == "nombre_asignatura" and not nombre_asignatura:
            nombre_asignatura = ent["value"]
        elif ent["entity"] == "nombre_departamento" and not nombre_departamento:
            nombre_departamento = ent["value"]

    return {
        "nombre_profesor": nombre_profesor,
        "nombre_asignatura": nombre_asignatura,
        "nombre_departamento": nombre_departamento,
    }


def _construir_historial(tracker: Tracker, max_turnos: int = 4) -> str:
    """Construye historial conversacional reciente para contexto del LLM."""
    lineas = []
    turnos = 0
    for event in reversed(tracker.events):
        if event.get("event") == "user":
            lineas.insert(0, f"Usuario: {event.get('text', '')}")
            turnos += 1
            if turnos >= max_turnos:
                break
        elif event.get("event") == "bot":
            text = event.get("text", "")
            if text:
                lineas.insert(0, f"Bot: {text[:150]}...")
    return "\n".join(lineas)


# ─── Clasificador RAG ───────────────────────────────────────────────────────

def _clasificar_necesita_rag(
    pregunta: str, nombre_profesor: str, nombre_asignatura: str
) -> bool:
    """
    Decide si necesitamos RAG para resolver la consulta.
    Caso típico: el usuario menciona un nombre parcial + asignatura,
    y necesitamos el plan docente para saber qué profesores dan esa asignatura
    y así poder hacer match con el nombre parcial.

    Solo aplica cuando hay asignatura — si solo hay nombre de profesor,
    basta con buscar directamente en la tabla profesores.
    """
    # Sin asignatura → no necesita RAG, SQL directo
    if not nombre_asignatura:
        return False

    # Si no hay nombre de profesor → no necesita RAG tampoco,
    # el text-to-SQL puede buscar por profesor_asignatura directamente
    if not nombre_profesor:
        return False

    # Hay profesor + asignatura → la IA decide si el nombre es suficientemente
    # ambiguo como para necesitar el plan docente para desambiguar
    prompt = f"""Eres un clasificador. Decide si necesitamos consultar el plan docente de una asignatura para identificar a un profesor.

CONTEXTO: El usuario pregunta por un profesor dando su nombre (posiblemente parcial) y una asignatura.
Tenemos una tabla de profesores con nombre_normalizado que permite búsqueda fuzzy.

Si el nombre del profesor es un apellido completo o nombre+apellido (ej: "Parejo", "Ruiz Cortés", "José Antonio Parejo") → NO necesita plan docente, podemos buscar directamente.

Si el nombre es solo un nombre de pila común/corto (ej: "Belén", "Diana", "Antonio", "Juan") y hay una asignatura que ayudaría a desambiguar → SÍ necesita plan docente para saber cuál de los posibles "Belén" o "Diana" es.

NOMBRE DEL PROFESOR: "{nombre_profesor}"
ASIGNATURA: "{nombre_asignatura}"
PREGUNTA: "{pregunta}"

Responde SOLO con: true o false"""

    try:
        respuesta = llamar_llm(
            prompt, timeout=15,
            options={"temperature": 0.0, "num_predict": 5}
        )
        if respuesta:
            resp_lower = respuesta.strip().lower()
            if 'true' in resp_lower:
                print(f"   → Clasificador RAG profesor: true (LLM)")
                return True
            if 'false' in resp_lower:
                print(f"   → Clasificador RAG profesor: false (LLM)")
                return False
    except Exception as e:
        print(f"   Error clasificando RAG profesor: {e}")

    # Heurística fallback: si el nombre tiene solo 1 palabra y ≤8 chars, probablemente
    # es un nombre de pila y necesita RAG
    partes = nombre_profesor.strip().split()
    if len(partes) == 1 and len(partes[0]) <= 8:
        print(f"   → Clasificador RAG profesor: true (heurística: nombre corto)")
        return True

    print(f"   → Clasificador RAG profesor: false (heurística: nombre largo)")
    return False


# ─── Flujo RAG: plan docente → match profesor → info contacto ────────────────

def _resolver_profesor_via_rag(
    pregunta: str,
    nombre_profesor: str,
    codigo_asignatura: str,
    nombre_asignatura: str,
) -> Optional[List[Dict]]:
    """
    Flujo RAG simple:
      1. Buscar chunks con el nombre del profesor en plan docente de la asignatura
      2. Buscar candidatos con ese nombre en tabla profesores
      3. Si hay varios, filtrar por los que aparecen en el texto de los chunks

    Returns: lista de dicts con datos del profesor, o None si falla.
    """
    try:
        from rag.buscar import _buscar_por_keywords
    except ImportError as e:
        print(f"   ⚠ RAG no disponible: {e}")
        return None

    nombre_prof_norm = _normalizar(nombre_profesor)
    print(f"   📚 RAG: buscando '{nombre_prof_norm}' en plan docente de {nombre_asignatura} ({codigo_asignatura})")

    # Paso 1: buscar por keyword el nombre del profesor directamente
    chunks = _buscar_por_keywords(
        nombre_profesor, codigo_asignatura=codigo_asignatura, grupo=None, limite=6
    )

    # Paso 2: si no hay resultados, buscar "profesorado coordinador" en todos los grupos
    if not chunks:
        print(f"   ⚠ Keyword '{nombre_prof_norm}' sin resultados, buscando sección profesorado...")
        chunks = _buscar_por_keywords(
            "profesorado coordinador", codigo_asignatura=codigo_asignatura, grupo=None, limite=10
        )

    if not chunks:
        print(f"   ⚠ RAG: sin chunks para {nombre_asignatura}")
        return None

    print(f"   📊 Chunks encontrados: {len(chunks)}")

    # Paso 3: juntar texto, normalizar, verificar que el nombre aparece
    texto_completo = _normalizar(" ".join(c['contenido'] for c in chunks))

    if nombre_prof_norm not in texto_completo:
        print(f"   ⚠ RAG: '{nombre_prof_norm}' no aparece en los chunks del plan docente")
        return None

    print(f"   ✅ '{nombre_prof_norm}' encontrado en plan docente")

    # Paso 4: buscar candidatos en tabla profesores por nombre_normalizado
    conn = db_client.get_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.id, p.nombre, p.apellidos, p.nombre_normalizado,
                   p.email, p.telefono, p.despacho, p.edificio, p.planta,
                   p.web_personal, p.orcid, p.categoria_academica,
                   p.enlace_perfil, d.siglas AS departamento
            FROM profesores p
            LEFT JOIN departamentos d ON p.departamento_id = d.id
            WHERE p.activo = true AND p.nombre_normalizado ILIKE %s
        """, (f"%{nombre_prof_norm}%",))
        columnas = [desc[0] for desc in cur.description]
        candidatos = [dict(zip(columnas, row)) for row in cur.fetchall()]
        cur.close()
        conn.close()
    except Exception as e:
        print(f"   ⚠ RAG: error buscando en BD: {e}")
        if conn:
            conn.close()
        return None

    if not candidatos:
        print(f"   ⚠ RAG: '{nombre_prof_norm}' no encontrado en tabla profesores")
        return None

    # Paso 5: si hay varios candidatos, filtrar por nombre_normalizado completo en el texto
    if len(candidatos) > 1:
        filtrados = [
            c for c in candidatos
            if c.get('nombre_normalizado', '') in texto_completo
        ]
        if filtrados:
            for f in filtrados:
                print(f"   ✅ Match: '{f['nombre_normalizado']}' en plan docente")
            candidatos = filtrados

    for c in candidatos:
        print(f"   ✅ Resultado: {c.get('nombre')} {c.get('apellidos')} ({c.get('email')})")

    return candidatos


# ─── Consulta de tutorías por ID ─────────────────────────────────────────────

def _enriquecer_con_tutorias(resultados: List[Dict]) -> List[Dict]:
    """Si los resultados no incluyen tutorías, las busca aparte."""
    if not resultados:
        return resultados
    if any(r.get('dia_semana') for r in resultados):
        return resultados

    prof_ids = list({str(r['id']) for r in resultados if r.get('id')})
    if not prof_ids or len(prof_ids) > 5:
        return resultados

    conn = db_client.get_connection()
    if not conn:
        return resultados

    try:
        cur = conn.cursor()
        placeholders = ','.join(['%s'] * len(prof_ids))
        cur.execute(f"""
            SELECT profesor_id, dia_semana, hora_inicio, hora_fin,
                   ubicacion, modalidad
            FROM tutorias
            WHERE profesor_id IN ({placeholders}) AND activa = true
            ORDER BY profesor_id, dia_semana, hora_inicio
        """, prof_ids)

        tutorias_map = {}
        for row in cur.fetchall():
            pid = str(row[0])
            if pid not in tutorias_map:
                tutorias_map[pid] = []
            tutorias_map[pid].append({
                'dia_semana': row[1],
                'hora_inicio': row[2],
                'hora_fin': row[3],
                'ubicacion': row[4],
                'modalidad': row[5],
            })
        cur.close()
        conn.close()

        resultados_expandidos = []
        for r in resultados:
            pid = str(r.get('id', ''))
            tuts = tutorias_map.get(pid, [])
            if tuts:
                for t in tuts:
                    r_copy = r.copy()
                    r_copy.update(t)
                    resultados_expandidos.append(r_copy)
            else:
                resultados_expandidos.append(r)

        return resultados_expandidos
    except Exception as e:
        print(f"Error buscando tutorías: {e}")
        if conn:
            conn.close()
        return resultados


# ─── Action principal ────────────────────────────────────────────────────────

class ActionConsultaProfesor(Action):
    def name(self) -> Text:
        return "action_consulta_profesor"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        pregunta = tracker.latest_message.get("text", "")
        titulacion = tracker.get_slot("contexto_titulacion")
        entidades = _extraer_entidades(tracker)

        nombre_profesor = entidades["nombre_profesor"]
        nombre_asignatura = entidades["nombre_asignatura"]
        nombre_departamento = entidades["nombre_departamento"]

        print(f"\n{'='*60}")
        print(f"[consulta_profesor] pregunta='{pregunta}'")
        print(f"  profesor={nombre_profesor}, asignatura={nombre_asignatura}, "
              f"departamento={nombre_departamento}")
        print(f"  titulación={titulacion}")
        print(f"{'='*60}")

        # ── Follow-up: si no hay entidades, usar contexto previo ──
        if not nombre_profesor and not nombre_asignatura and not nombre_departamento:
            ultimo_prof = tracker.get_slot("ultimo_profesor_consultado")
            if ultimo_prof:
                turnos = _contar_turnos_desde_slot(tracker, "ultimo_profesor_consultado")
                if turnos <= 3:
                    nombre_profesor = ultimo_prof
                    print(f"  → Seguimiento profesor: '{ultimo_prof}' ({turnos} turnos)")

            if not nombre_profesor:
                ultimo_asig = tracker.get_slot("ultimo_nombre_asignatura")
                if ultimo_asig:
                    turnos = _contar_turnos_desde_slot(tracker, "ultimo_nombre_asignatura")
                    if turnos <= 3:
                        nombre_asignatura = ultimo_asig
                        print(f"  → Seguimiento asignatura: '{ultimo_asig}' ({turnos} turnos)")

        slots = [SlotSet("ultima_action_ejecutada", "action_consulta_profesor")]

        # ── Resolver asignatura con pipeline completo (alias, fuzzy, etc.) ──
        asignatura_resuelta = _resolver_asignatura_contexto(pregunta, tracker, titulacion)
        codigo_asignatura = None
        if asignatura_resuelta:
            nombre_asignatura = asignatura_resuelta.get("nombre")
            codigo_asignatura = asignatura_resuelta.get("codigo")
        elif nombre_asignatura:
            nombre_asignatura = _expandir_alias_asignatura(nombre_asignatura, titulacion)
            print(f"  Asignatura expandida: {nombre_asignatura}")

        # ── Si tenemos asignatura pero no profesor, pedir al LLM que lo extraiga ──
        if nombre_asignatura and not nombre_profesor:
            nombre_profesor = _extraer_nombre_profesor_con_llm(pregunta, nombre_asignatura)
            if nombre_profesor:
                print(f"  → Profesor extraído por LLM: '{nombre_profesor}'")

        # ── Clasificar si necesita RAG (IA decide) ──
        necesita_rag = _clasificar_necesita_rag(pregunta, nombre_profesor, nombre_asignatura)

        if necesita_rag:
            print(f"  → Flujo RAG: plan docente de '{nombre_asignatura}' para resolver '{nombre_profesor}'")
            resultados_rag = _resolver_profesor_via_rag(
                pregunta, nombre_profesor, codigo_asignatura, nombre_asignatura
            )
            if resultados_rag:
                resultados_rag = _enriquecer_con_tutorias(resultados_rag)
                datos_texto = formatear_datos_para_prompt(resultados_rag)
                respuesta = generar_respuesta_natural(pregunta, resultados_rag)
                dispatcher.utter_message(text=respuesta)

                primer = resultados_rag[0]
                apellidos = primer.get('apellidos', '')
                nombre = primer.get('nombre', '')
                prof_display = f"{apellidos}, {nombre}" if apellidos else nombre
                slots.append(SlotSet("ultimo_profesor_consultado", prof_display))
                return slots
            else:
                print(f"  ⚠ RAG no dio resultados, cayendo a text-to-SQL")

        # ── Text-to-SQL: generar query con LLM ──
        # Si RAG se intentó (había profesor + asignatura), no pasar la asignatura
        # al text-to-SQL porque profesor_asignatura está vacía y generaría JOINs inútiles
        asignatura_para_sql = None if necesita_rag else nombre_asignatura

        historial = _construir_historial(tracker)

        resultado_sql = generar_sql_profesor(
            pregunta=pregunta,
            nombre_profesor=nombre_profesor,
            nombre_asignatura=asignatura_para_sql,
            nombre_departamento=nombre_departamento,
            historial=historial,
        )

        if not resultado_sql.get('valido'):
            dispatcher.utter_message(
                text="Ha habido un problema generando la consulta. ¿Puedes reformular tu pregunta?"
            )
            return slots

        sql = resultado_sql['sql']
        parametros = resultado_sql.get('parametros', [])
        print(f"  SQL: {sql[:120]}...")
        print(f"  Params: {parametros}")

        # ── Ejecutar query ──
        exito, resultados = ejecutar_query(sql, parametros)

        if not exito:
            print(f"  ❌ Error SQL: {resultados}")
            dispatcher.utter_message(
                text="No pude consultar la base de datos. ¿Puedes intentar de otra forma?"
            )
            return slots

        if not resultados:
            msg = "No encontré resultados para tu consulta."
            if nombre_profesor:
                msg = (f"No encontré ningún profesor con el nombre \"{nombre_profesor}\". "
                       f"Prueba con el apellido completo.")
            elif nombre_asignatura:
                msg = (f"No encontré profesores asignados a \"{nombre_asignatura}\". "
                       f"Es posible que aún no se hayan cargado las asignaciones.")
            dispatcher.utter_message(text=msg)
            return slots

        print(f"  ✅ Resultados: {len(resultados)} filas")

        # ── Enriquecer con tutorías si no vinieron en el JOIN ──
        resultados = _enriquecer_con_tutorias(resultados)

        # ── Generar respuesta natural con LLM ──
        respuesta = generar_respuesta_natural(pregunta, resultados)
        dispatcher.utter_message(text=respuesta)

        # ── Guardar contexto en slots ──
        if resultados and len(resultados) <= 5:
            primer = resultados[0]
            apellidos = primer.get('apellidos', '')
            nombre = primer.get('nombre', '')
            if apellidos:
                prof_display = f"{apellidos}, {nombre}"
            else:
                prof_display = nombre
            slots.append(SlotSet("ultimo_profesor_consultado", prof_display))

        return slots
