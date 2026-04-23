"""
Chunking de documentos de proyectos docentes.

Estrategia: **chunking por secciones**. Primero se parte el texto por los
títulos de sección conocidos del proyecto docente de la ETSII (usando una
tabla de cabeceras), luego dentro de cada sección se chunka por tamaño con
overlap. Un chunk NUNCA cruza la frontera de una sección.

Razonamiento (raíz de un bug del piloto):
  Antes se chunkaba por párrafos y se asignaba sección "best-effort"
  buscando la ÚLTIMA etiqueta dentro del chunk. Esto hacía que un chunk
  con los nombres de profesorado seguido de "Bibliografía recomendada"
  acabara etiquetado como `bibliografia` — rompiendo los filtros por
  sección del retrieval RAG.

  Al partir PRIMERO por sección, el etiquetado es determinista y el
  retrieval `seccion=profesorado` devuelve solo contenido de ese bloque.
"""

import re
from typing import List, Dict, Tuple


# ── Configuración de chunking ─────────────────────────────────────────────────

MAX_CHUNK_SIZE = 800
OVERLAP_SIZE = 100
MIN_CHUNK_SIZE = 50


# ── Cabeceras de sección del proyecto docente ─────────────────────────────────
# Tuplas (regex, nombre_normalizado). El regex detecta la cabecera en el
# texto extraído; el nombre se usa como valor de la columna `seccion`.
# El ORDEN de la lista NO importa para la detección: se localizan todas las
# ocurrencias y se ordenan por posición en el texto.

_SECTION_HEADERS: List[Tuple[str, str]] = [
    (r"Datos b[áa]sicos de la asignatura", "datos_basicos"),
    (r"Coordinador de la asignatura", "coordinador"),
    (r"Profesorado(?:\s+del\s+grupo)?", "profesorado"),
    (r"Objetivos y resultados del aprendizaje", "objetivos"),
    (r"Contenidos o bloques tem[áa]ticos", "contenidos"),
    (r"Relaci[óo]n detallada y ordenaci[óo]n temporal", "contenidos_detallados"),
    (r"Actividades formativas", "actividades_formativas"),
    (r"Metodolog[íi]a de ense[ñn]anza[\s\S-]{0,30}aprendizaje", "metodologia"),
    (r"Idioma de impartici[óo]n(?:\s+del\s+grupo)?", "idioma"),
    (r"Sistemas y criterios de evaluaci[óo]n y calificaci[óo]n del grupo",
     "evaluacion_grupo"),
    (r"Sistemas y criterios de evaluaci[óo]n y calificaci[óo]n", "evaluacion_general"),
    (r"Horarios del grupo(?:\s+del\s+proyecto\s+docente)?", "horarios"),
    (r"Calendario de ex[áa]menes", "calendario_examenes"),
    (r"Tribunales espec[íi]ficos(?:\s+de\s+evaluaci[óo]n)?", "tribunales"),
    (r"Bibliograf[íi]a recomendada", "bibliografia"),
    (r"Informaci[óo]n Adicional", "informacion_adicional"),
]

_HEADERS_COMPILED = [(re.compile(p, re.IGNORECASE), name) for p, name in _SECTION_HEADERS]


def procesar_documento(
    texto_completo: str,
    max_size: int = MAX_CHUNK_SIZE,
    overlap: int = OVERLAP_SIZE,
    min_size: int = MIN_CHUNK_SIZE,
) -> List[Dict]:
    """
    Divide un proyecto docente en chunks, partiendo PRIMERO por secciones
    detectadas y chunkando DESPUÉS por tamaño dentro de cada sección.

    Returns:
        Lista de dicts con: contenido, seccion, orden_chunk, subseccion.
    """
    if not texto_completo or not texto_completo.strip():
        return []

    bloques = _partir_por_secciones(texto_completo)

    chunks: List[Dict] = []
    orden = 1
    for seccion, texto_seccion in bloques:
        if not texto_seccion.strip():
            continue
        fragmentos = _chunkar_texto(texto_seccion, max_size, overlap, min_size)
        for fragmento in fragmentos:
            chunks.append({
                "contenido": fragmento,
                "seccion": seccion,
                "orden_chunk": orden,
                "subseccion": None,
            })
            orden += 1

    return chunks


def _partir_por_secciones(texto: str) -> List[Tuple[str, str]]:
    """
    Parte el texto por las cabeceras conocidas. Devuelve lista de
    `(seccion, contenido)` en orden de aparición.

    El contenido anterior a la primera cabecera detectada se etiqueta como
    'general' (suele contener la portada / título del proyecto docente).

    Si una misma cabecera aparece varias veces (por repetirse en cada página
    del PDF), cada ocurrencia delimita un bloque nuevo: **se desduplica
    posteriormente** conservando el bloque más largo por sección, para
    evitar los duplicados que se observaron en BD.
    """
    matches: List[Tuple[int, int, str]] = []
    for regex, nombre in _HEADERS_COMPILED:
        for m in regex.finditer(texto):
            matches.append((m.start(), m.end(), nombre))

    if not matches:
        return [("general", texto)]

    matches.sort(key=lambda t: t[0])

    bloques_raw: List[Tuple[str, str]] = []

    # Contenido antes del primer header -> "general"
    primer_inicio = matches[0][0]
    pre = texto[:primer_inicio].strip()
    if pre:
        bloques_raw.append(("general", pre))

    # Recorre headers y toma el rango hasta el siguiente header
    for i, (ini, fin, nombre) in enumerate(matches):
        siguiente = matches[i + 1][0] if i + 1 < len(matches) else len(texto)
        contenido = texto[fin:siguiente].strip()
        if contenido:
            bloques_raw.append((nombre, contenido))

    return _deduplicar_bloques(bloques_raw)


def _deduplicar_bloques(bloques: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """
    Si una sección aparece varias veces (cabeceras repetidas por página),
    conserva solo la de mayor longitud. Evita la duplicación observada en
    `planes_docentes_chunks` donde cada sección tenía 2-4 copias.
    """
    mejor: Dict[str, Tuple[int, str]] = {}
    orden_primera_aparicion: Dict[str, int] = {}
    for idx, (seccion, contenido) in enumerate(bloques):
        orden_primera_aparicion.setdefault(seccion, idx)
        if seccion not in mejor or len(contenido) > mejor[seccion][0]:
            mejor[seccion] = (len(contenido), contenido)

    return [
        (seccion, mejor[seccion][1])
        for seccion in sorted(mejor.keys(), key=lambda s: orden_primera_aparicion[s])
    ]


def _chunkar_texto(
    texto: str,
    max_size: int,
    overlap: int,
    min_size: int,
) -> List[str]:
    """
    Chunking por tamaño dentro de una sección. Respeta párrafos y añade
    overlap entre chunks consecutivos — pero nunca cruza la frontera de
    la sección (la función opera sobre texto ya segmentado por sección).
    """
    parrafos = re.split(r"\n\s*\n", texto)
    parrafos = [p.strip() for p in parrafos if p.strip()]

    if not parrafos:
        return []

    fragmentos: List[str] = []
    buffer = ""

    for parrafo in parrafos:
        if buffer and len(buffer) + len(parrafo) + 2 > max_size:
            if len(buffer) >= min_size:
                fragmentos.append(buffer.strip())
            if overlap > 0 and buffer:
                buffer = buffer[-overlap:] + "\n\n" + parrafo
            else:
                buffer = parrafo
        else:
            buffer = buffer + "\n\n" + parrafo if buffer else parrafo

    if buffer.strip() and len(buffer.strip()) >= min_size:
        fragmentos.append(buffer.strip())

    # Si un solo párrafo supera max_size y no se ha emitido nada,
    # devolver el texto entero para no perderlo.
    if not fragmentos and texto.strip():
        fragmentos = [texto.strip()]

    return fragmentos
