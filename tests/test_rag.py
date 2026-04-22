"""
Script de diagnóstico para el pipeline RAG.
Ejecutar desde la raíz del proyecto:
    python test_rag.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def test_embedding(texto="¿Cuáles son los objetivos de la asignatura?"):
    print("\n" + "=" * 60)
    print("1. TEST EMBEDDING")
    print("=" * 60)

    from rag.embeddings import generar_embedding, EMBEDDING_DIMS
    print(f"   Texto: '{texto}'")
    embedding = generar_embedding(texto)

    if embedding is None:
        print("   ❌ Embedding devolvió None — cuota agotada o error de API")
        return None
    if len(embedding) != EMBEDDING_DIMS:
        print(f"   ❌ Dimensión incorrecta: {len(embedding)} (esperado {EMBEDDING_DIMS})")
        return None

    print(f"   ✅ Embedding OK — {len(embedding)} dims, primeros valores: {embedding[:5]}")
    return embedding


def test_chunks_en_bd():
    print("\n" + "=" * 60)
    print("2. TEST CHUNKS EN BD")
    print("=" * 60)

    from actions.shared.db import db_client
    conn = db_client.get_connection()
    if not conn:
        print("   ❌ No se pudo conectar a la BD")
        return

    try:
        cur = conn.cursor()

        # Total de chunks
        cur.execute("SELECT COUNT(*) FROM planes_docentes_chunks")
        total = cur.fetchone()[0]
        print(f"   Total chunks: {total}")

        # Planes por estado
        cur.execute("""
            SELECT estado_rag, COUNT(*)
            FROM planes_docentes
            GROUP BY estado_rag
        """)
        print("   Planes por estado:")
        for estado, count in cur.fetchall():
            print(f"     - {estado}: {count}")

        # Ver si hay chunks con embedding distinto de NULL
        cur.execute("""
            SELECT COUNT(*) FROM planes_docentes_chunks
            WHERE embedding IS NOT NULL
        """)
        con_embedding = cur.fetchone()[0]
        print(f"   Chunks con embedding: {con_embedding}")

        # Muestra de chunks
        cur.execute("""
            SELECT c.seccion, LEFT(c.contenido, 80), a.nombre, pd.grupo
            FROM planes_docentes_chunks c
            JOIN planes_docentes pd ON pd.id = c.plan_docente_id
            JOIN asignaturas a ON a.id = pd.asignatura_id
            LIMIT 3
        """)
        rows = cur.fetchall()
        if rows:
            print("   Muestra de chunks:")
            for seccion, contenido, nombre, grupo in rows:
                print(f"     [{nombre} - {grupo}] {seccion}: {contenido}...")
        else:
            print("   ⚠ No hay chunks en la BD")

    finally:
        conn.close()


def test_busqueda_vectorial(pregunta="objetivos de la asignatura", codigo=None, grupo=None):
    print("\n" + "=" * 60)
    print("3. TEST BÚSQUEDA VECTORIAL DIRECTA")
    print("=" * 60)
    print(f"   Pregunta: '{pregunta}'")
    print(f"   Código asignatura: {codigo or '(todas)'}")
    print(f"   Grupo: {grupo or '(todos)'}")

    from rag.embeddings import generar_embedding
    embedding = generar_embedding(pregunta)
    if not embedding:
        print("   ❌ Sin embedding, no se puede probar búsqueda vectorial")
        return

    from actions.shared.db import db_client
    conn = db_client.get_connection()
    if not conn:
        print("   ❌ Sin conexión BD")
        return

    try:
        cur = conn.cursor()
        embedding_str = str(embedding)

        # Probar con umbral 0 para ver TODAS las similitudes (sin filtrar)
        if codigo:
            cur.execute(
                """SELECT chunk_id, seccion, similitud, asignatura_nombre, grupo
                   FROM buscar_plan_docente(
                       %s::vector(2000), %s, NULL::uuid, %s, %s, NULL, %s, %s
                   )""",
                (embedding_str, codigo, "2025-26", grupo, 5, 0.0),
            )
        else:
            cur.execute(
                """SELECT chunk_id, seccion, similitud, asignatura_nombre, grupo
                   FROM buscar_plan_docente_global(
                       %s::vector(2000), %s, %s, %s
                   )""",
                (embedding_str, "2025-26", 5, 0.0),
            )

        rows = cur.fetchall()
        if rows:
            print("   Resultados (umbral=0, mostrando las mejores similitudes):")
            for row in rows:
                print(f"     similitud={row[2]:.4f} | {row[3]} - {row[4]} | {row[1]}")
        else:
            print("   ❌ Sin resultados incluso con umbral=0 — revisar función SQL o datos")

    except Exception as e:
        print(f"   ❌ Error SQL: {e}")
    finally:
        conn.close()


def test_busqueda_completa(pregunta="¿Cuáles son los objetivos?", codigo=None):
    print("\n" + "=" * 60)
    print("4. TEST BÚSQUEDA COMPLETA (buscar_en_plan_docente)")
    print("=" * 60)

    from rag.buscar import buscar_en_plan_docente
    resultados = buscar_en_plan_docente(
        pregunta=pregunta,
        codigo_asignatura=codigo,
        umbral=0.1,
    )
    if resultados:
        print(f"   ✅ {len(resultados)} resultados encontrados:")
        for r in resultados:
            sim = r.get("similitud")
            sim_str = f"{sim:.3f}" if sim is not None else "keyword"
            print(f"     [{sim_str}] {r.get('asignatura_nombre')} | {r.get('seccion')}")
            print(f"            {r.get('contenido', '')[:100]}...")
    else:
        print("   ❌ Sin resultados")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Diagnóstico del pipeline RAG")
    parser.add_argument("--pregunta", default="¿Cuáles son los objetivos de la asignatura?")
    parser.add_argument("--codigo", default=None, help="Código de asignatura (ej: 2050001)")
    parser.add_argument("--grupo", default=None, help="Grupo (ej: 'Grupo 1')")
    args = parser.parse_args()

    test_embedding(args.pregunta)
    test_chunks_en_bd()
    test_busqueda_vectorial(args.pregunta, args.codigo, args.grupo)
    test_busqueda_completa(args.pregunta, args.codigo)

    print("\n" + "=" * 60)
    print("Diagnóstico completado")
    print("=" * 60)
