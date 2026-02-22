"""
Búsqueda en planes docentes para consultas en runtime.

Estrategia con fallback automático:
  1. Búsqueda vectorial (semántica) con gemini-embedding-001 — mejor calidad.
  2. Si el embedding falla (ej. cuota agotada), búsqueda por palabras clave
     usando ILIKE sobre el contenido de los chunks — funcional para testing.
"""

import re
import sys
import unicodedata
from pathlib import Path
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.embeddings import generar_embedding
from actions.db import db_client

CURSO_ACADEMICO = "2025-26"
GRUPO_DEFAULT = "Grupo 1"


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower().strip()


def buscar_en_plan_docente(
    pregunta: str,
    codigo_asignatura: str = None,
    grupo: str = GRUPO_DEFAULT,
    limite: int = 3,
    umbral: float = 0.3,
) -> List[Dict]:
    """
    Busca chunks relevantes en los planes docentes.

    Intenta búsqueda vectorial primero. Si el embedding no está disponible
    (cuota agotada, error de red), cae automáticamente a búsqueda por
    palabras clave sobre el contenido de los chunks.

    Args:
        pregunta: Texto de la consulta del usuario.
        codigo_asignatura: Código de la asignatura (ej. "2050001").
        grupo: Grupo a consultar (default "Grupo 1").
        limite: Número máximo de chunks a devolver.
        umbral: Umbral mínimo de similitud (solo para búsqueda vectorial).

    Returns:
        Lista de dicts con contenido, seccion, similitud (o None), etc.
    """
    # --- Intento 1: búsqueda vectorial ---
    embedding = generar_embedding(pregunta)
    if embedding:
        resultados = _buscar_vectorial(
            embedding, codigo_asignatura, grupo, limite, umbral
        )
        if resultados:
            return resultados
        print("  ⚠ Búsqueda vectorial sin resultados, probando keyword fallback")

    # --- Fallback: búsqueda por palabras clave ---
    print("  🔍 Usando búsqueda por palabras clave (sin embedding)")
    return _buscar_por_keywords(pregunta, codigo_asignatura, grupo, limite)


def _buscar_vectorial(
    embedding: List[float],
    codigo_asignatura: Optional[str],
    grupo: str,
    limite: int,
    umbral: float,
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
                       %s::vector(2000), %s, NULL::uuid, %s, %s, NULL, %s, %s
                   )""",
                (embedding_str, codigo_asignatura, CURSO_ACADEMICO,
                 grupo, limite, umbral),
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
    grupo: str,
    limite: int,
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
        # Sin keywords útiles: devolver los primeros chunks de la asignatura
        keywords = []

    conn = db_client.get_connection()
    if not conn:
        return []

    try:
        cur = conn.cursor()

        # Construir condición ILIKE para cada keyword (OR entre ellas)
        if keywords:
            ilike_parts = " OR ".join(
                f"c.contenido ILIKE %s" for _ in keywords
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
              AND pd.grupo = %s
              {where_asig}
              {where_keywords}
            ORDER BY c.orden_chunk
            LIMIT %s
        """

        params = (
            [CURSO_ACADEMICO, grupo]
            + asig_params
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
