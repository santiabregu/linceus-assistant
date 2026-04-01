"""
Cliente de embeddings usando Gemini Embedding (gemini-embedding-001).

Límites tier gratuito (feb 2026):
    - 100 RPM (requests per minute)
    - 1.000 RPD (requests per day)
    - Dimensión nativa: 3072 (reducible con output_dimensionality)
    - Usamos 768 para compatibilidad con schema pgvector existente.

Para ~3.000 chunks con batch de 100 textos/request → ~30 requests → ~1 min.
"""

import os
import time
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMBEDDING_MODEL = "models/gemini-embedding-001"
EMBEDDING_DIMS = 2000  # nativo=3072, reducido a 2000 (máximo para índice HNSW en pgvector)

# Gemini permite hasta 100 textos por request de embedding batch
BATCH_SIZE = 100
# Pausa entre batches para respetar rate limits (100 RPM → 0.6s mínimo)
PAUSA_ENTRE_BATCHES = 1.0


def generar_embedding(
    texto: str,
    task_type: str = "SEMANTIC_SIMILARITY",
) -> Optional[List[float]]:
    """
    Genera un embedding para un solo texto.

    Args:
        texto: Texto a vectorizar.
        task_type: Tipo de tarea para Gemini. Usar "RETRIEVAL_QUERY" para
                   preguntas de búsqueda y "RETRIEVAL_DOCUMENT" para documentos.

    Returns:
        Lista de floats (EMBEDDING_DIMS dims) o None si hay error.
    """
    resultado = generar_embeddings_batch([texto], task_type=task_type)
    if resultado and resultado[0]:
        return resultado[0]
    return None


def generar_embeddings_batch(
    textos: List[str],
    task_type: str = "RETRIEVAL_DOCUMENT",
) -> List[Optional[List[float]]]:
    """
    Genera embeddings para una lista de textos usando batch API.

    Divide en sub-batches de BATCH_SIZE para respetar los límites de la API.
    Cada texto genera un vector de EMBEDDING_DIMS dimensiones.

    Args:
        textos: Lista de textos a vectorizar.
        task_type: Tipo de tarea para Gemini. Usar "RETRIEVAL_DOCUMENT" para
                   el pipeline de vectorización y "RETRIEVAL_QUERY" para búsquedas.

    Returns:
        Lista de embeddings (mismo orden que los textos de entrada).
        Cada elemento es una lista de floats o None si hubo error.
    """
    import google.generativeai as genai

    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY no configurada en .env")

    genai.configure(api_key=GEMINI_API_KEY)
    todos_embeddings: List[Optional[List[float]]] = []

    # Dividir en sub-batches
    for i in range(0, len(textos), BATCH_SIZE):
        batch = textos[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (len(textos) + BATCH_SIZE - 1) // BATCH_SIZE

        try:
            print(f"  📐 Embedding batch {batch_num}/{total_batches} "
                  f"({len(batch)} textos)...")

            response = genai.embed_content(
                model=EMBEDDING_MODEL,
                content=batch,
                task_type=task_type,
                output_dimensionality=EMBEDDING_DIMS,
            )

            # Extraer embeddings de la respuesta
            for embedding in response["embedding"]:
                todos_embeddings.append(list(embedding))

            print(f"  ✅ Batch {batch_num} completado")

        except Exception as e:
            print(f"  ❌ Error en batch {batch_num}: {e}")
            # Rellenar con None para mantener el orden
            todos_embeddings.extend([None] * len(batch))

            # Si es rate limit, esperar más
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print("  ⏳ Rate limit alcanzado, esperando 60s...")
                time.sleep(60)

        # Pausa entre batches para no saturar
        if i + BATCH_SIZE < len(textos):
            time.sleep(PAUSA_ENTRE_BATCHES)

    return todos_embeddings


def verificar_embeddings() -> bool:
    """
    Verifica que la API de embeddings funciona correctamente.

    Returns:
        True si el test fue exitoso.
    """
    try:
        embedding = generar_embedding("Test de verificación de embeddings")
        if embedding and len(embedding) == EMBEDDING_DIMS:
            print(f"✅ Embeddings OK: modelo={EMBEDDING_MODEL}, dims={len(embedding)}")
            return True
        else:
            print(f"❌ Embedding inválido: {len(embedding) if embedding else 'None'} dims")
            return False
    except Exception as e:
        print(f"❌ Error verificando embeddings: {e}")
        return False
