"""
Paquete RAG para vectorización de proyectos docentes.

Módulos:
    - extraer_pdf: Extracción de texto de PDFs con pdfplumber.
    - chunking: Segmentación inteligente por secciones del proyecto docente.
    - embeddings: Generación de embeddings con Gemini text-embedding-004.
    - db_vectores: Inserción/borrado de vectores en Supabase (planes_docentes_chunks).
    - pipeline: Orquestador principal que conecta todos los módulos.
"""
