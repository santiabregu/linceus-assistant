"""
Operaciones de base de datos para el pipeline RAG.
Inserta/borra planes docentes y sus chunks vectorizados en Supabase.
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Reutilizar la conexión del proyecto
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from actions.db import db_client


def calcular_hash_pdf(ruta_pdf: Path) -> str:
    """Calcula SHA256 de un archivo PDF para detectar cambios."""
    sha256 = hashlib.sha256()
    with open(ruta_pdf, "rb") as f:
        for bloque in iter(lambda: f.read(8192), b""):
            sha256.update(bloque)
    return sha256.hexdigest()


def obtener_asignatura_id(codigo_asignatura: str) -> Optional[str]:
    """
    Busca el UUID de una asignatura por su código.

    Args:
        codigo_asignatura: Código de la asignatura (ej: "2050001").

    Returns:
        UUID como string o None si no existe.
    """
    conn = db_client.get_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM asignaturas WHERE codigo = %s AND activa = true LIMIT 1",
            (codigo_asignatura,)
        )
        row = cur.fetchone()
        return str(row[0]) if row else None
    finally:
        conn.close()


def obtener_plan_existente(
    asignatura_id: str,
    curso_academico: str,
    grupo: str,
) -> Optional[Dict]:
    """
    Busca un plan docente existente para una asignatura/curso/grupo.

    Returns:
        Dict con id, hash_documento, estado_rag o None si no existe.
    """
    conn = db_client.get_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, hash_documento, estado_rag 
               FROM planes_docentes 
               WHERE asignatura_id = %s 
                 AND curso_academico = %s 
                 AND grupo = %s""",
            (asignatura_id, curso_academico, grupo)
        )
        row = cur.fetchone()
        if row:
            return {
                "id": str(row[0]),
                "hash_documento": row[1],
                "estado_rag": row[2],
            }
        return None
    finally:
        conn.close()


def crear_plan_docente(
    asignatura_id: str,
    curso_academico: str,
    grupo: str,
    hash_documento: str,
    coordinador_nombre: Optional[str] = None,
    url_documento: Optional[str] = None,
) -> Optional[str]:
    """
    Inserta un nuevo plan docente en la tabla planes_docentes.

    Returns:
        UUID del plan docente creado, o None si hay error.
    """
    conn = db_client.get_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO planes_docentes 
               (asignatura_id, curso_academico, grupo, hash_documento,
                coordinador_nombre, url_documento, estado_rag)
               VALUES (%s, %s, %s, %s, %s, %s, 'procesando')
               RETURNING id""",
            (asignatura_id, curso_academico, grupo, hash_documento,
             coordinador_nombre, url_documento)
        )
        plan_id = str(cur.fetchone()[0])
        conn.commit()
        return plan_id
    except Exception as e:
        conn.rollback()
        print(f"  ❌ Error creando plan docente: {e}")
        return None
    finally:
        conn.close()


def borrar_chunks_plan(plan_docente_id: str) -> int:
    """
    Borra todos los chunks vectorizados de un plan docente.
    Se usa antes de re-procesar un documento actualizado.

    Returns:
        Número de chunks borrados.
    """
    conn = db_client.get_connection()
    if not conn:
        return 0
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM planes_docentes_chunks WHERE plan_docente_id = %s",
            (plan_docente_id,)
        )
        borrados = cur.rowcount
        conn.commit()
        return borrados
    finally:
        conn.close()


def insertar_chunks(
    plan_docente_id: str,
    chunks: List[Dict],
    embeddings: List[List[float]],
    metadata_extra: Dict,
) -> int:
    """
    Inserta chunks vectorizados en planes_docentes_chunks.

    Args:
        plan_docente_id: UUID del plan docente padre.
        chunks: Lista de chunks (output de chunking.crear_chunks).
        embeddings: Lista de embeddings (mismo orden que chunks).
        metadata_extra: Metadata adicional para JSONB (codigo, nombre, etc.).

    Returns:
        Número de chunks insertados.
    """
    if len(chunks) != len(embeddings):
        raise ValueError(
            f"Mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings"
        )

    conn = db_client.get_connection()
    if not conn:
        return 0

    insertados = 0
    try:
        cur = conn.cursor()
        for chunk, embedding in zip(chunks, embeddings):
            if embedding is None:
                print(f"  ⚠ Saltando chunk {chunk['orden_chunk']}: embedding es None")
                continue

            # Combinar metadata del chunk con la metadata extra
            metadata_completa = {
                **metadata_extra,
                "seccion": chunk["seccion"],
            }
            if chunk.get("subseccion"):
                metadata_completa["subseccion"] = chunk["subseccion"]

            cur.execute(
                """INSERT INTO planes_docentes_chunks 
                   (plan_docente_id, contenido, embedding, seccion, subseccion,
                    orden_chunk, metadata)
                   VALUES (%s, %s, %s::vector, %s, %s, %s, %s)""",
                (
                    plan_docente_id,
                    chunk["contenido"],
                    str(embedding),  # pgvector acepta formato string '[0.1, 0.2, ...]'
                    chunk["seccion"],
                    chunk.get("subseccion"),
                    chunk["orden_chunk"],
                    json.dumps(metadata_completa, ensure_ascii=False),
                )
            )
            insertados += 1

        conn.commit()
        return insertados

    except Exception as e:
        conn.rollback()
        print(f"  ❌ Error insertando chunks: {e}")
        return 0
    finally:
        conn.close()


def actualizar_estado_plan(
    plan_docente_id: str,
    estado: str,
    error: Optional[str] = None,
) -> None:
    """
    Actualiza el estado_rag de un plan docente.

    Args:
        plan_docente_id: UUID del plan docente.
        estado: Nuevo estado ('pendiente', 'procesando', 'completado', 'error').
        error: Mensaje de error (solo si estado = 'error').
    """
    conn = db_client.get_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE planes_docentes 
               SET estado_rag = %s,
                   error_procesamiento = %s,
                   fecha_procesamiento = NOW(),
                   updated_at = NOW()
               WHERE id = %s""",
            (estado, error, plan_docente_id)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"  ❌ Error actualizando estado: {e}")
    finally:
        conn.close()


def actualizar_hash_plan(plan_docente_id: str, nuevo_hash: str) -> None:
    """Actualiza el hash del documento tras re-procesar."""
    conn = db_client.get_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE planes_docentes 
               SET hash_documento = %s, updated_at = NOW()
               WHERE id = %s""",
            (nuevo_hash, plan_docente_id)
        )
        conn.commit()
    finally:
        conn.close()


def obtener_estadisticas() -> Dict:
    """
    Devuelve estadísticas del estado actual de la vectorización.

    Returns:
        Dict con conteo de planes por estado y total de chunks.
    """
    conn = db_client.get_connection()
    if not conn:
        return {}
    try:
        cur = conn.cursor()

        # Conteo por estado
        cur.execute("""
            SELECT estado_rag, COUNT(*) 
            FROM planes_docentes 
            GROUP BY estado_rag
        """)
        estados = {row[0]: row[1] for row in cur.fetchall()}

        # Total de chunks
        cur.execute("SELECT COUNT(*) FROM planes_docentes_chunks")
        total_chunks = cur.fetchone()[0]

        # Total de planes
        cur.execute("SELECT COUNT(*) FROM planes_docentes")
        total_planes = cur.fetchone()[0]

        return {
            "total_planes": total_planes,
            "total_chunks": total_chunks,
            "por_estado": estados,
        }
    finally:
        conn.close()
