"""
Chunking de documentos con solapamiento (overlap).

Enfoque genérico: divide cualquier texto en chunks de tamaño fijo con overlap,
sin depender de la estructura del documento. La búsqueda vectorial se encarga
de encontrar los fragmentos relevantes.

Opcionalmente, intenta etiquetar cada chunk con la sección del proyecto docente
a la que pertenece (best-effort: si no la detecta, el chunk se marca como
'general' y funciona igual).
"""

import re
from typing import List, Dict, Optional, Tuple


# ── Configuración de chunking ─────────────────────────────────────────────────

# Tamaño máximo de chunk en caracteres.
# ~800 chars ≈ ~150-200 tokens → buen balance entre especificidad y contexto.
MAX_CHUNK_SIZE = 800
# Solapamiento entre chunks consecutivos para no perder contexto en los bordes.
OVERLAP_SIZE = 100
# Tamaño mínimo para que un chunk valga la pena vectorizarlo.
MIN_CHUNK_SIZE = 50


# ── Etiquetas de sección (best-effort, opcional) ──────────────────────────────
# Si un chunk contiene uno de estos patrones, se etiqueta con la sección.
# No afecta al chunking en sí, solo enriquece metadata.

ETIQUETAS_SECCION: List[Tuple[str, str]] = [
    (r"Datos b[áa]sicos de la asignatura", "datos_basicos"),
    (r"Coordinador de la asignatura", "coordinador"),
    (r"Profesorado", "profesorado"),
    (r"Objetivos y resultados del aprendizaje", "objetivos"),
    (r"Contenidos o bloques tem[áa]ticos", "contenidos"),
    (r"Relaci[óo]n detallada y ordenaci[óo]n temporal", "contenidos_detallados"),
    (r"Actividades formativas", "actividades_formativas"),
    (r"Idioma de impartici[óo]n", "idioma"),
    (r"criterios de evaluaci[óo]n y calificaci[óo]n del grupo", "evaluacion_grupo"),
    (r"criterios de evaluaci[óo]n y calificaci[óo]n", "evaluacion_general"),
    (r"Metodolog[íi]a de ense[ñn]anza", "metodologia"),
    (r"Horarios del grupo", "horarios"),
    (r"Calendario de ex[áa]menes", "calendario_examenes"),
    (r"Tribunales espec[íi]ficos", "tribunales"),
    (r"Bibliograf[íi]a recomendada", "bibliografia"),
    (r"Informaci[óo]n Adicional", "informacion_adicional"),
    (r"(?:PRIMERA|SEGUNDA|TERCERA) CONVOCATORIA", "evaluacion_grupo"),
    (r"[Ee]valuaci[óo]n continua", "evaluacion_grupo"),
]


def procesar_documento(
    texto_completo: str,
    max_size: int = MAX_CHUNK_SIZE,
    overlap: int = OVERLAP_SIZE,
    min_size: int = MIN_CHUNK_SIZE,
) -> List[Dict]:
    """
    Divide un texto en chunks con solapamiento.

    Estrategia: corte por párrafos respetando tamaño máximo.
    Cada chunk recibe una etiqueta de sección best-effort.

    Args:
        texto_completo: Texto limpio del documento.
        max_size: Tamaño máximo de chunk en caracteres.
        overlap: Caracteres de solapamiento entre chunks.
        min_size: Tamaño mínimo para crear un chunk.

    Returns:
        Lista de dicts con:
            - contenido (str): Texto del chunk.
            - seccion (str): Etiqueta de sección (best-effort, 'general' si no detectada).
            - orden_chunk (int): Número de orden (1-indexed).
            - subseccion (str | None): Siempre None (compatibilidad con BD).
    """
    if not texto_completo or not texto_completo.strip():
        return []

    # 1. Dividir en párrafos (doble salto de línea)
    parrafos = re.split(r"\n\s*\n", texto_completo)
    parrafos = [p.strip() for p in parrafos if p.strip()]

    if not parrafos:
        return []

    # 2. Agrupar párrafos en chunks con overlap
    fragmentos = _agrupar_con_overlap(parrafos, max_size, overlap, min_size)

    # 3. Crear chunks con metadata
    chunks = []
    for i, fragmento in enumerate(fragmentos, start=1):
        seccion = _detectar_seccion(fragmento)
        chunks.append({
            "contenido": fragmento,
            "seccion": seccion,
            "orden_chunk": i,
            "subseccion": None,
        })

    return chunks


def _detectar_seccion(texto: str) -> str:
    """
    Intenta detectar a qué sección pertenece un chunk (best-effort).
    Busca la ÚLTIMA etiqueta que aparezca, ya que es la más relevante
    para el contenido del chunk.

    Returns:
        Nombre normalizado de la sección, o 'general' si no se detecta.
    """
    ultima_seccion = "general"
    ultima_pos = -1

    for patron, nombre in ETIQUETAS_SECCION:
        match = None
        for m in re.finditer(patron, texto, re.IGNORECASE):
            match = m
        if match and match.start() >= ultima_pos:
            # Si hay empate de posición, preferir el nombre más específico
            if match.start() > ultima_pos or len(nombre) > len(ultima_seccion):
                ultima_seccion = nombre
                ultima_pos = match.start()

    return ultima_seccion


def _agrupar_con_overlap(
    parrafos: List[str],
    max_size: int,
    overlap: int,
    min_size: int,
) -> List[str]:
    """
    Agrupa párrafos en fragmentos de tamaño <= max_size con solapamiento.
    """
    fragmentos = []
    buffer = ""

    for parrafo in parrafos:
        if not parrafo:
            continue

        # Si añadir este párrafo supera el máximo, guardar el buffer actual
        if buffer and len(buffer) + len(parrafo) + 2 > max_size:
            if len(buffer) >= min_size:
                fragmentos.append(buffer.strip())
            # Solapamiento: mantener el final del buffer anterior
            if overlap > 0 and buffer:
                buffer = buffer[-overlap:] + "\n\n" + parrafo
            else:
                buffer = parrafo
        else:
            buffer = buffer + "\n\n" + parrafo if buffer else parrafo

    # Último fragmento
    if buffer.strip() and len(buffer.strip()) >= min_size:
        fragmentos.append(buffer.strip())

    return fragmentos if fragmentos else [
        "\n\n".join(p for p in parrafos if p.strip())
    ]
