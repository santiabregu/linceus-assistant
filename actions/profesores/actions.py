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

import difflib
import re
import unicodedata
from typing import Any, Text, Dict, List, Optional

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from ..shared.config import ALIAS_ASIGNATURAS, ALIAS_POR_TITULACION
from ..shared.db import db_client
from ..shared.gemini_client import llamar_gemini as llamar_llm
from ..shared.matching import clasificar_por_normalizado

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from knowledge_base.profesores_data.text_to_sql import (
    generar_sql_profesor,
    ejecutar_query,
    formatear_datos_para_prompt,
    generar_respuesta_natural,
    _fallback_sql,
)


# ─── Utilidades ──────────────────────────────────────────────────────────────

def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower().strip()


# Objetivo para fuzzy match: los tokens normalizados de "tutoría(s)".
_TUTORIA_VARIANTES = ("tutoria", "tutorias")


def _pregunta_sobre_tutorias(pregunta: str) -> bool:
    """True si la pregunta menciona tutorías (tolerando typos).

    Tokeniza la pregunta y compara cada token (≥5 chars, empieza por 't')
    contra {"tutoria","tutorias"} con SequenceMatcher. Umbral 0.8 acierta
    'tutuoria', 'tutoriaa', 'tuturia' y descarta 'turista'/'historia'.
    """
    for token in re.findall(r"[a-záéíóúñ]+", pregunta.lower()):
        tok = _normalizar(token)
        if len(tok) < 5 or not tok.startswith("t"):
            continue
        for ref in _TUTORIA_VARIANTES:
            if difflib.SequenceMatcher(None, tok, ref).ratio() >= 0.8:
                return True
    return False


def _clasificar_resultados_por_similitud(
    nombre_consulta: str, resultados: list
) -> tuple[list, list]:
    """Wrapper que delega en el matcher compartido (nombre_normalizado)."""
    print(f"  🎯 Scoring '{nombre_consulta}':")
    return clasificar_por_normalizado(nombre_consulta, resultados)


def _detectar_grupo(texto: str) -> Optional[str]:
    """Detecta 'grupo X' o 'gX' en la pregunta y lo devuelve como 'Grupo X'.

    Mismo patrón que `_detectar_grupo` en actions/asignaturas/actions.py;
    se duplica aquí para evitar importes cruzados entre módulos de actions.
    """
    if not texto:
        return None
    texto_lower = texto.lower()
    match = re.search(r'\bgrupo\s+(\d+)\b', texto_lower)
    if match:
        return f"Grupo {match.group(1)}"
    match = re.search(r'\bg(\d+)\b', texto_lower)
    if match:
        return f"Grupo {match.group(1)}"
    return None


def _formatear_sugerencia(nombre_consulta: str, sugerencias: list) -> str:
    """
    Construye el mensaje 'no encontre X, ¿quizas Y?' cuando no hay match firme.
    """
    if not sugerencias:
        return (f"No encontré ningún profesor llamado \"{nombre_consulta}\". "
                f"Prueba con el apellido completo.")

    nombres_sug = []
    for s in sugerencias[:3]:
        n = s.get("nombre") or ""
        a = s.get("apellidos") or ""
        nombres_sug.append(f"**{(a + ', ' + n).strip(', ')}**".strip())

    if len(nombres_sug) == 1:
        return (f"No encontré ningún profesor llamado \"{nombre_consulta}\". "
                f"¿Quizás te refieres a {nombres_sug[0]}?")
    lista = ", ".join(nombres_sug[:-1]) + f" o {nombres_sug[-1]}"
    return (f"No encontré ningún profesor llamado \"{nombre_consulta}\". "
            f"¿Quizás te refieres a {lista}?")


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
    # R2: ignorar aliases de 1 letra (demasiado ambiguos).
    if len(nombre_lower) == 1:
        return nombre
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

# Roles no modelados en `profesor_asignatura`: cuando el usuario los menciona
# explícitamente, RAG vectorial es la única fuente de verdad.
_PALABRAS_SOLO_RAG = (
    'coordinador', 'coordinadora', 'coordina', 'coordinan',
    'suplente', 'suplentes',
)


def _pregunta_menciona_rol_rag(pregunta: str) -> bool:
    """True si la pregunta menciona coordinador/suplente: fuerza RAG directo."""
    pregunta_lower = pregunta.lower()
    return any(p in pregunta_lower for p in _PALABRAS_SOLO_RAG)


# ─── Flujo RAG: búsqueda vectorial sobre el plan docente ─────────────────────

def _rag_chunks_plan_docente(
    pregunta: str, codigo_asignatura: str, nombre_asignatura: str,
    grupo: Optional[str] = None,
) -> List[Dict]:
    """Búsqueda vectorial (con reranking) sobre el plan docente de la asignatura.
    Mismo patrón que ActionConsultaEspecifica: la titulación ya quedó aplicada
    al resolver la asignatura aguas arriba.

    Si `grupo` viene informado (p.ej. "Grupo 2"), se filtra el RAG por ese grupo
    para responder a preguntas tipo "profesores del grupo 2 de Redes". La
    columna `profesor_asignatura.grupo` no está poblada por el scraping
    actual (decisión Cat 2), así que el grupo solo es fiable vía plan docente.
    """
    try:
        from rag.buscar import buscar_en_plan_docente
    except ImportError as e:
        print(f"   ⚠ RAG no disponible: {e}")
        return []

    print(f"   📚 RAG vectorial: plan docente de {nombre_asignatura} ({codigo_asignatura})"
          + (f" [grupo={grupo}]" if grupo else ""))
    chunks = buscar_en_plan_docente(
        pregunta,
        codigo_asignatura=codigo_asignatura,
        grupo=grupo,
        limite=10,
    )
    print(f"   📊 Chunks recuperados: {len(chunks) if chunks else 0}")
    return chunks or []


def _generar_respuesta_rag(
    pregunta: str, chunks: List[Dict], nombre_asignatura: str,
) -> Optional[str]:
    """Convierte chunks del plan docente en una respuesta natural.
    Mismo prompt/estilo que ActionConsultaEspecifica en asignaturas."""
    if not chunks:
        return None

    def _chunk_header(c):
        label = c.get('_asignatura_label') or c.get('asignatura_nombre', '')
        seccion = c.get('seccion', 'general')
        return f"[{seccion}] ({label})" if label else f"[{seccion}]"

    contexto = "\n\n---\n\n".join(
        f"{_chunk_header(c)}\n{c.get('contenido', '')}\nMetadatos: {c.get('metadata', {})}"
        for c in chunks
    )

    prompt = f"""Eres Linceus, un asistente universitario de la ETSII (Universidad de Sevilla).
Responde a la pregunta del usuario usando SOLO la información del plan docente proporcionada.

PREGUNTA DEL USUARIO: "{pregunta}"
ASIGNATURA: {nombre_asignatura}

INFORMACIÓN DEL PLAN DOCENTE:
{contexto}

REGLAS:
- Responde de forma natural, cercana y concisa
- **PROHIBIDO INVENTAR DATOS.** Si la información proporcionada no contiene
  nombres, emails, grupos o cualquier dato concreto, NO los completes con
  datos plausibles. Di que esa información no consta y, si procede, sugiere
  consultar otra fuente.
- Puedes usar markdown para formatear (negritas, listas)
- No menciones que consultaste un "plan docente" ni "chunks"
- No saludes — ve directo a la respuesta
- Si la información no es suficiente para responder, dilo amablemente
- IMPORTANTE: Cada fragmento tiene una etiqueta de sección entre corchetes (ej. [profesorado], [bibliografia]).
  Los nombres en secciones [bibliografia] son AUTORES DE LIBROS, NO profesores de la asignatura.
  Solo menciona como profesores a personas de secciones [profesorado] o [coordinador].
- IMPORTANTE: Tu respuesta debe tener como MÁXIMO 1500 caracteres. Si hay mucha información, resume lo más relevante

Respuesta:"""

    respuesta = llamar_llm(
        prompt, timeout=30,
        options={"temperature": 0.3, "num_predict": 800},
    )
    return respuesta.strip() if respuesta else None


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

        # ── Detección de grupo en la pregunta ──
        # `profesor_asignatura.grupo` no está poblado por el scraping actual
        # (Cat 2), así que cuando el usuario menciona grupo el SQL no podrá
        # responder con fiabilidad. La única fuente con la asignación a grupo
        # es el plan docente (RAG). Si hay asignatura resuelta + grupo,
        # bypaseamos SQL y vamos directos al RAG con filtro por grupo.
        grupo_detectado = _detectar_grupo(pregunta)
        if grupo_detectado:
            print(f"  → Grupo detectado en pregunta: {grupo_detectado}")

        # ── Atajo: "coordinador"/"suplente" → RAG vectorial directo ──
        # Esos roles no viven en `profesor_asignatura`; el plan docente es la
        # única fuente. Si además tenemos la asignatura resuelta, saltamos SQL.
        if codigo_asignatura and _pregunta_menciona_rol_rag(pregunta):
            print(f"  → Atajo RAG: rol (coordinador/suplente) en pregunta")
            chunks = _rag_chunks_plan_docente(
                pregunta, codigo_asignatura, nombre_asignatura,
                grupo=grupo_detectado,
            )
            if chunks:
                respuesta_rag = _generar_respuesta_rag(pregunta, chunks, nombre_asignatura)
                if respuesta_rag:
                    dispatcher.utter_message(text=respuesta_rag)
                    slots.append(SlotSet("ultimo_nombre_asignatura", nombre_asignatura))
                    slots.append(SlotSet("ultimo_codigo_consultado", codigo_asignatura))
                    return slots
            # Si RAG no da resultados, caemos al flujo SQL normal como último recurso.
            print(f"  ⚠ RAG vectorial sin respuesta, cayendo a text-to-SQL")

        # ── Atajo: pregunta por grupo + asignatura resuelta → RAG directo ──
        # La columna `profesor_asignatura.grupo` no está poblada, así que SQL
        # no puede filtrar por grupo. Vamos directos al RAG con filtro de grupo.
        if codigo_asignatura and grupo_detectado and not _pregunta_menciona_rol_rag(pregunta):
            print(f"  → Atajo RAG: grupo {grupo_detectado} en pregunta (SQL no tiene grupo)")
            chunks = _rag_chunks_plan_docente(
                pregunta, codigo_asignatura, nombre_asignatura,
                grupo=grupo_detectado,
            )
            if chunks:
                respuesta_rag = _generar_respuesta_rag(pregunta, chunks, nombre_asignatura)
                if respuesta_rag:
                    dispatcher.utter_message(text=respuesta_rag)
                    slots.append(SlotSet("ultimo_nombre_asignatura", nombre_asignatura))
                    slots.append(SlotSet("ultimo_codigo_consultado", codigo_asignatura))
                    return slots
            print(f"  ⚠ RAG por grupo sin respuesta, cayendo a text-to-SQL")

        # ── Detección de consulta de tutorías (fuzzy, tolera typos) ──
        # Si el usuario pregunta por tutorías, tratamos la consulta como
        # "dame los profesores relevantes" + aviso de contactar por email
        # (la tabla `tutorias` está vacía — ver D-061). Usamos `_fallback_sql`
        # directo para evitar que el LLM genere un JOIN con `tutorias`.
        consulta_tutorias = _pregunta_sobre_tutorias(pregunta)
        if consulta_tutorias:
            print(f"  → Consulta de tutorías detectada: tratando como 'profesores de' + aviso")

        historial = _construir_historial(tracker)

        if consulta_tutorias and (nombre_profesor or nombre_asignatura):
            asig_norm = _normalizar(nombre_asignatura) if nombre_asignatura else None
            resultado_sql = _fallback_sql(
                nombre_profesor, asig_norm, nombre_departamento,
                contexto_titulacion=titulacion,
            )
        else:
            # ── Text-to-SQL: generar query con LLM ──
            resultado_sql = generar_sql_profesor(
                pregunta=pregunta,
                nombre_profesor=nombre_profesor,
                nombre_asignatura=nombre_asignatura,
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

        if not resultados and nombre_profesor:
            # Fallback: buscar por última palabra (probable apellido)
            partes = nombre_profesor.strip().split()
            if len(partes) > 1:
                ultimo_apellido = partes[-1]
                print(f"  → Retry con último apellido: '{ultimo_apellido}'")
                fallback_result = _fallback_sql(ultimo_apellido, None, None)
                exito2, resultados = ejecutar_query(
                    fallback_result['sql'], fallback_result['parametros']
                )
                if exito2 and resultados:
                    print(f"  ✅ Fallback apellido encontró: {len(resultados)} resultados")

        if not resultados:
            # Último recurso: RAG vectorial sobre el plan docente. Cubre los
            # casos en que `profesor_asignatura` está vacía o no cuadra con el
            # nombre parcial que dio el usuario.
            if codigo_asignatura:
                print(f"  → Fallback RAG vectorial: plan docente de '{nombre_asignatura}'")
                chunks = _rag_chunks_plan_docente(
                    pregunta, codigo_asignatura, nombre_asignatura,
                    grupo=grupo_detectado,
                )
                if chunks:
                    respuesta_rag = _generar_respuesta_rag(pregunta, chunks, nombre_asignatura)
                    if respuesta_rag:
                        dispatcher.utter_message(text=respuesta_rag)
                        slots.append(SlotSet("ultimo_nombre_asignatura", nombre_asignatura))
                        slots.append(SlotSet("ultimo_codigo_consultado", codigo_asignatura))
                        return slots

            msg = "No encontré resultados para tu consulta."
            if nombre_profesor:
                msg = (f"No encontré ningún profesor con el nombre \"{nombre_profesor}\". "
                       f"Prueba con el apellido completo.")
            elif nombre_asignatura:
                msg = (f"No encontré profesores asignados a \"{nombre_asignatura}\". "
                       f"Es posible que aún no se hayan cargado las asignaciones.")
            dispatcher.utter_message(text=msg)
            return slots

        # ── Filtrado por similitud de nombre ──────────────────────────────
        # Evita falsos positivos del tipo "Joaquín Peña" -> Joaquín Borrego.
        # Solo aplica cuando el usuario pidio un profesor concreto por nombre.
        if nombre_profesor:
            firmes, sugerencias = _clasificar_resultados_por_similitud(
                nombre_profesor, resultados,
            )
            if not firmes:
                dispatcher.utter_message(text=_formatear_sugerencia(nombre_profesor, sugerencias))
                # Guardar la mejor sugerencia para que un 'si' posterior
                # re-ejecute la consulta con ese nombre.
                if sugerencias:
                    mejor = sugerencias[0]
                    valor_sug = (mejor.get("nombre_normalizado")
                                 or f"{mejor.get('nombre','')} {mejor.get('apellidos','')}".strip())
                    slots.append(SlotSet("ultima_sugerencia", {
                        "action": "action_consulta_profesor",
                        "campo": "nombre_profesor",
                        "valor": valor_sug,
                        "pregunta_original": pregunta,
                    }))
                return slots
            resultados = firmes

        print(f"  ✅ Resultados: {len(resultados)} filas")

        # ── Enriquecer con tutorías si no vinieron en el JOIN ──
        resultados = _enriquecer_con_tutorias(resultados)

        # ── Generar respuesta natural con LLM ──
        # `tutorias_no_disponibles`: la tabla `tutorias` está vacía (D-061);
        # si el usuario preguntó por tutorías, instruimos al LLM a redirigir
        # al email en lugar de intentar responder con horarios.
        respuesta = generar_respuesta_natural(
            pregunta, resultados,
            tutorias_no_disponibles=consulta_tutorias,
            nombre_asignatura_resuelto=nombre_asignatura,
        )
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

        # Si la pregunta era por una asignatura (ej. "profesores de DP1"),
        # persistir tambien la asignatura para follow-ups cruzados.
        if nombre_asignatura:
            slots.append(SlotSet("ultimo_nombre_asignatura", nombre_asignatura))
            if codigo_asignatura:
                slots.append(SlotSet("ultimo_codigo_consultado", codigo_asignatura))

        return slots
