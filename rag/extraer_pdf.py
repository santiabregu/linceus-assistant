"""
Extracción de texto de PDFs de proyectos docentes.
Usa pdfplumber para obtener texto limpio página a página.
"""

import re
import pdfplumber
from pathlib import Path
from typing import List, Dict, Optional


# Cabecera repetida en todas las páginas del proyecto docente (SEVIUS)
_PATRON_CABECERA = re.compile(
    r"^PROYECTO DOCENTE\n.+\n.+\nCURSO \d{4}-\d{2}\n?",
    re.MULTILINE,
)
# Pie de página: "Última modificación DD/MM/YYYY Página X de Y"
_PATRON_PIE = re.compile(
    r"Última modificación \d{2}/\d{2}/\d{4}\s+Página \d+ de \d+\s*$",
    re.MULTILINE,
)


def extraer_texto_pdf(ruta_pdf: Path) -> List[Dict]:
    """
    Extrae texto de un PDF de proyecto docente.

    Args:
        ruta_pdf: Ruta al archivo PDF.

    Returns:
        Lista de dicts con claves:
            - pagina (int): Número de página (1-indexed).
            - texto (str): Texto limpio de la página.
    """
    if not ruta_pdf.exists():
        raise FileNotFoundError(f"PDF no encontrado: {ruta_pdf}")

    paginas = []

    with pdfplumber.open(str(ruta_pdf)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            texto_raw = page.extract_text() or ""
            texto_limpio = _limpiar_texto_pagina(texto_raw)
            if texto_limpio.strip():
                paginas.append({
                    "pagina": i,
                    "texto": texto_limpio,
                })

    return paginas


def extraer_texto_completo(ruta_pdf: Path) -> str:
    """
    Extrae el texto completo del PDF como una sola cadena.

    Args:
        ruta_pdf: Ruta al archivo PDF.

    Returns:
        Texto completo limpio del documento.
    """
    paginas = extraer_texto_pdf(ruta_pdf)
    return "\n\n".join(p["texto"] for p in paginas)


def extraer_metadata_basica(ruta_pdf: Path) -> Dict:
    """
    Extrae metadata básica del encabezado del proyecto docente.
    (nombre asignatura, código, curso académico, grupo, coordinador)

    Args:
        ruta_pdf: Ruta al archivo PDF.

    Returns:
        Dict con los metadatos extraídos.
    """
    with pdfplumber.open(str(ruta_pdf)) as pdf:
        primera_pagina = pdf.pages[0].extract_text() or ""

    metadata = {}

    # Nombre de la asignatura (segunda línea del documento)
    lineas = primera_pagina.strip().split("\n")
    if len(lineas) >= 2:
        metadata["nombre_asignatura"] = lineas[1].strip()

    # Curso académico
    m = re.search(r"CURSO (\d{4}-\d{2})", primera_pagina)
    if m:
        metadata["curso_academico"] = m.group(1)

    # Código asignatura
    m = re.search(r"Código asignatura:\s*(\d+)", primera_pagina)
    if m:
        metadata["codigo_asignatura"] = m.group(1)

    # Coordinador
    m = re.search(r"Coordinador de la asignatura\n(.+)", primera_pagina)
    if m:
        metadata["coordinador"] = m.group(1).strip()

    # Grupo (de la línea 3 del encabezado)
    if len(lineas) >= 3:
        m_grupo = re.search(r"Grupo\s+(\S+)", lineas[2])
        if m_grupo:
            metadata["grupo"] = f"Grupo {m_grupo.group(1)}"

    return metadata


# ── Funciones internas ─────────────────────────────────────────────────────────

def _limpiar_texto_pagina(texto: str) -> str:
    """Elimina cabeceras y pies repetidos del texto de una página."""
    texto = _PATRON_CABECERA.sub("", texto)
    texto = _PATRON_PIE.sub("", texto)
    # Limpiar saltos de línea excesivos
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()
