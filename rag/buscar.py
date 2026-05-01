"""
Búsqueda en planes docentes para consultas en runtime.

Estrategia con fallback automático:
  1. Búsqueda vectorial (semántica) con gemini-embedding-001 — mejor calidad.
  2. Si el embedding falla (ej. cuota agotada), búsqueda por palabras clave
     usando ILIKE sobre el contenido de los chunks — funcional para testing.

Incluye reranking por relevancia de sección (metadata-aware).
"""

import re
import sys
import unicodedata
from pathlib import Path
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.embeddings import generar_embedding  # noqa: E402
from actions.shared.db import db_client  # noqa: E402

CURSO_ACADEMICO = "2025-26"
GRUPO_DEFAULT = "Grupo 1"

# ── Pesos de reranking por sección ──────────────────────────────────────────
# Mapea (tipo_consulta, seccion_chunk) → bonus de score.
# El bonus se SUMA a la similitud coseno (0-1) para reordenar.
RERANK_WEIGHTS = {
    # El chunker etiqueta la sección best-effort y a veces se equivoca (p.ej.
    # nombres de profesorado acaban en chunks etiquetados como 'bibliografia'
    # o 'evaluacion_grupo' cuando la cabecera de la siguiente sección cae
    # dentro del chunk). Por eso NO filtramos por sección en la query —
    # dejamos que la similitud vectorial decida — y usamos estos pesos solo
    # como empujón suave cuando la sección acierta. Bonus positivos
    # pequeños, sin penalizaciones negativas (antes -0.30 para bibliografia
    # enmascaraba chunks con nombres de profes mal etiquetados).
    "profesorado": {
        "profesorado": 0.15,
        "coordinador": 0.12,
        "datos_basicos": 0.03,
    },
    "evaluacion": {
        "evaluacion_general": 0.15,
        "evaluacion_grupo": 0.15,
        "metodologia": 0.03,
    },
    "contenidos": {
        "contenidos": 0.15,
        "contenidos_detallados": 0.15,
        "objetivos": 0.05,
    },
    "horarios": {
        "horarios": 0.15,
        "calendario_examenes": 0.05,
    },
    "bibliografia": {
        "bibliografia": 0.15,
        "informacion_adicional": 0.03,
    },
}

# Palabras clave para detectar el tipo de consulta (para reranking)
_TIPO_CONSULTA_KEYWORDS = {
    "profesorado": [
        "profesor", "profesora", "profesores", "profesorado", "docente",
        "imparte", "quien da", "quién da", "quien enseña", "da clase",
        "coordinador", "coordinadora", "responsable",
    ],
    "evaluacion": [
        "evalua", "evaluacion", "evaluación", "califica", "nota", "notas",
        "examen", "examenes", "parcial", "aprueba", "aprobar", "convocatoria",
        "porcentaje", "puntua", "suspender",
    ],
    "contenidos": [
        "temario", "tema", "temas", "contenido", "contenidos", "programa",
        "objetivo", "competencia",
    ],
    "horarios": [
        "horario", "clase", "aula", "calendario", "examen",
    ],
    "bibliografia": [
        "bibliografia", "bibliografía", "libro", "libros", "material",
    ],
}


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower().strip()


def _detectar_tipo_consulta(pregunta: str) -> Optional[str]:
    """Detecta el tipo de consulta para aplicar reranking por sección."""
    pregunta_lower = pregunta.lower()
    for tipo, keywords in _TIPO_CONSULTA_KEYWORDS.items():
        if any(kw in pregunta_lower for kw in keywords):
            return tipo
    return None


def _rerank(chunks: List[Dict], tipo_consulta: Optional[str]) -> List[Dict]:
    """
    Reordena chunks aplicando bonificaciones por sección según el tipo de consulta.
    Los chunks con secciones más relevantes suben, los irrelevantes bajan.
    """
    if not tipo_consulta or tipo_consulta not in RERANK_WEIGHTS:
        return chunks

    weights = RERANK_WEIGHTS[tipo_consulta]

    def score(chunk):
        similitud = chunk.get("similitud") or 0.0
        seccion = chunk.get("seccion", "general")
        bonus = weights.get(seccion, 0.0)
        return similitud + bonus

    reranked = sorted(chunks, key=score, reverse=True)

    print(f"  🔄 Rerank ({tipo_consulta}):")
    for i, c in enumerate(reranked[:5]):
        sim = c.get('similitud') or 0.0
        sec = c.get('seccion', '?')
        bonus = weights.get(sec, 0.0)
        print(f"     [{i+1}] sim={sim:.3f} +bonus={bonus:+.2f} = {sim+bonus:.3f} | {sec}")

    return reranked


def _resolver_grupo(codigo_asignatura: str, grupo: str) -> str:
    """
    Resuelve el nombre exacto del grupo en la BD.
    Maneja variantes como 'Grupo 5INGLES' cuando el detector devuelve 'Grupo 5'.
    """
    conn = db_client.get_connection()
    if not conn:
        return grupo
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT pd.grupo
            FROM planes_docentes pd
            JOIN asignaturas a ON a.id = pd.asignatura_id
            WHERE a.codigo = %s AND pd.grupo LIKE %s
            ORDER BY pd.grupo
            LIMIT 1
            """,
            (codigo_asignatura, f"{grupo}%"),
        )
        row = cur.fetchone()
        return row[0] if row else grupo
    except Exception:
        return grupo
    finally:
        conn.close()


def buscar_en_plan_docente(
    pregunta: str,
    codigo_asignatura: str = None,
    grupo: Optional[str] = None,
    limite: int = 10,
    umbral: float = 0.5,
    seccion_filtro: Optional[str] = None,
) -> List[Dict]:
    """
    Busca chunks relevantes en los planes docentes.

    Intenta búsqueda vectorial primero. Si el embedding no está disponible
    (cuota agotada, error de red), cae automáticamente a búsqueda por
    palabras clave sobre el contenido de los chunks.

    Si se proporciona seccion_filtro, busca primero con ese filtro.
    Si no hay resultados suficientes, repite sin filtro como fallback.

    Aplica reranking según el tipo de consulta detectado.
    """
    # Resolver nombre exacto del grupo
    if grupo and codigo_asignatura:
        grupo = _resolver_grupo(codigo_asignatura, grupo)

    # Detectar tipo de consulta para reranking
    tipo_consulta = _detectar_tipo_consulta(pregunta)

    # Nota: ya NO filtramos por sección en la query. El chunker etiqueta
    # best-effort y la clasificación puede fallar (p.ej. nombres de profes
    # en chunks marcados como 'bibliografia'). Traemos los N más similares
    # y la sección se usa únicamente como empujón en el reranking.
    if seccion_filtro:
        print(f"  🔎 Filtro por sección (explícito): {seccion_filtro}")

    # --- Intento 1: búsqueda vectorial ---
    embedding = generar_embedding(pregunta, task_type="SEMANTIC_SIMILARITY")
    if embedding:
        resultados = _buscar_vectorial(
            embedding, codigo_asignatura, grupo, limite, umbral,
            seccion=seccion_filtro,
        )
        if resultados:
            return _rerank(resultados, tipo_consulta)
        print("  ⚠ Búsqueda vectorial sin resultados, probando keyword fallback")

    # --- Fallback: búsqueda por palabras clave ---
    print("  🔍 Usando búsqueda por palabras clave (sin embedding)")
    resultados = _buscar_por_keywords(
        pregunta, codigo_asignatura, grupo, limite,
        seccion=seccion_filtro,
    )
    return _rerank(resultados, tipo_consulta)


def _buscar_vectorial(
    embedding: List[float],
    codigo_asignatura: Optional[str],
    grupo: Optional[str],
    limite: int,
    umbral: float,
    seccion: Optional[str] = None,
) -> List[Dict]:
    conn = db_client.get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        embedding_str = str(embedding)

        if codigo_asignatura:
            cur.execute(
                """SELECT chunk_id, contenido, seccion, subseccion, similitud,
                          asignatura_nombre, asignatura_codigo, grupo, metadata
                   FROM buscar_plan_docente(
                       %s::vector(2000), %s, NULL::uuid, %s, %s, %s, %s, %s
                   )""",
                (embedding_str, codigo_asignatura, CURSO_ACADEMICO,
                 grupo, seccion, limite, umbral),
            )
        else:
            cur.execute(
                """SELECT chunk_id, contenido, seccion, similitud,
                          asignatura_nombre, asignatura_codigo, grupo, metadata
                   FROM buscar_plan_docente_global(
                       %s::vector(2000), %s, %s, %s
                   )""",
                (embedding_str, CURSO_ACADEMICO, limite, umbral),
            )

        columnas = [desc[0] for desc in cur.description]
        resultados = [dict(zip(columnas, row)) for row in cur.fetchall()]

        for r in resultados:
            print(f"  📎 [{r.get('similitud', 0):.3f}] "
                  f"{r.get('seccion', '?')} — "
                  f"{r.get('contenido', '')[:80]}...")
        return resultados

    except Exception as e:
        print(f"  ❌ Error en búsqueda vectorial: {e}")
        return []
    finally:
        conn.close()


def _buscar_por_keywords(
    pregunta: str,
    codigo_asignatura: Optional[str],
    grupo: Optional[str],
    limite: int,
    seccion: Optional[str] = None,
) -> List[Dict]:
    """
    Fallback: busca chunks cuyo contenido coincida con palabras clave
    extraídas de la pregunta. Sin embedding, sin cuota de API.
    """
    # Extraer palabras significativas (>3 chars, sin stopwords)
    stopwords = {
        "como", "cual", "que", "quien", "donde", "cuando", "cuanto",
        "tiene", "hay", "esta", "este", "para", "con", "los", "las",
        "del", "una", "son", "por", "mas", "sobre", "sus", "hay",
        "puedes", "dime", "cuales", "quiero", "saber", "asignatura",
    }
    palabras = re.findall(r"\b\w{4,}\b", _normalizar(pregunta))
    keywords = [p for p in palabras if p not in stopwords][:4]

    if not keywords:
        keywords = []

    conn = db_client.get_connection()
    if not conn:
        return []

    try:
        cur = conn.cursor()

        # Construir condición ILIKE para cada keyword (OR entre ellas)
        if keywords:
            ilike_parts = " OR ".join(
                "c.contenido ILIKE %s" for _ in keywords
            )
            keyword_params = [f"%{kw}%" for kw in keywords]
            where_keywords = f"AND ({ilike_parts})"
        else:
            where_keywords = ""
            keyword_params = []

        # Filtro por asignatura
        if codigo_asignatura:
            where_asig = "AND a.codigo = %s"
            asig_params = [codigo_asignatura]
        else:
            where_asig = ""
            asig_params = []

        if grupo:
            where_grupo = "AND pd.grupo = %s"
            grupo_params = [grupo]
        else:
            where_grupo = ""
            grupo_params = []

        # Filtro por sección
        if seccion:
            where_seccion = "AND c.seccion = %s"
            seccion_params = [seccion]
        else:
            where_seccion = ""
            seccion_params = []

        sql = f"""
            SELECT
                c.id        AS chunk_id,
                c.contenido,
                c.seccion,
                c.subseccion,
                NULL::float AS similitud,
                a.nombre    AS asignatura_nombre,
                a.codigo    AS asignatura_codigo,
                pd.grupo,
                c.metadata
            FROM planes_docentes_chunks c
            JOIN planes_docentes pd ON pd.id = c.plan_docente_id
            JOIN asignaturas a      ON a.id  = pd.asignatura_id
            WHERE pd.estado_rag = 'completado'
              AND pd.curso_academico = %s
              {where_grupo}
              {where_asig}
              {where_seccion}
              {where_keywords}
            ORDER BY c.orden_chunk
            LIMIT %s
        """

        params = (
            [CURSO_ACADEMICO]
            + grupo_params
            + asig_params
            + seccion_params
            + keyword_params
            + [limite]
        )
        cur.execute(sql, params)

        columnas = [desc[0] for desc in cur.description]
        resultados = [dict(zip(columnas, row)) for row in cur.fetchall()]

        for r in resultados:
            print(f"  📎 [keyword] "
                  f"{r.get('seccion', '?')} — "
                  f"{r.get('contenido', '')[:80]}...")
        return resultados

    except Exception as e:
        print(f"  ❌ Error en búsqueda por keywords: {e}")
        return []
    finally:
        conn.close()
