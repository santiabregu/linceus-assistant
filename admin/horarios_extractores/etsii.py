"""
Extractor de horarios de la ETSII (Ing. Informatica US).

Fuente: PDF oficial publicado en
    https://www.informatica.us.es/docs/orgdocente/horarios-grados-<curso>.pdf

Formato: codigos de tabla "xGy-Cz" donde:
  x = curso (1..4)
  G = grado: C=Computadores, S=Software, T=Tecnologias (las 3 titulaciones ETSII)
  y = grupo (1..9)
  z = cuatrimestre (1|2)

Salida: `base.ExtraccionHorarios` con 3 titulaciones y los grupos detectados.
El marcado temporal (watermark "BORRADOR DE HORARIOS" en tamanyo 59) se filtra
descartando chars con `size >= 50`.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Optional

import pdfplumber

from .base import (
    ExtraccionHorarios,
    TitulacionExtraida,
    GrupoExtraido,
    EntradaHorario,
    descargar_pdf,
    escribir_markdown,
    insertar_en_bd,
    es_aula_valida,
)


# ── Configuracion ─────────────────────────────────────────────────────────────

PDF_URL = "https://www.informatica.us.es/docs/orgdocente/horarios-grados-2025-26.pdf"
PDF_FILENAME = "horarios-grados-2025-26.pdf"
CURSO_ACADEMICO_DEFAULT = "2025-26"
CENTRO_CODIGO = "ETSII"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = PROJECT_ROOT / "knowledge_base" / "horarios_aulas"
MD_DIR = PROJECT_ROOT / "knowledge_base" / "horarios_aulas"

# grado -> (codigo_titulacion_bd, carpeta_md, nombre_legible)
GRADOS = {
    "C": ("GII-IC", "computadores", "Ingeniería de Computadores"),
    "S": ("GII-IS", "software", "Ingeniería del Software"),
    "T": ("GII-TI", "tecnologias_informaticas", "Tecnologías Informáticas"),
}

RE_CODIGO = re.compile(r"^(\d)([A-Z])(\d)-C([12])$")
RE_AULA = re.compile(r"^[A-Z]\d+\.\d+[a-z]?$")
RE_AULA_PREFIJO = re.compile(r"^[A-Z]\d+\.\d+")
RE_HORA_FRANJA = re.compile(r"(\d{1,2}[:.]\d{2})\s*a\s*(\d{1,2}[:.]\d{2})")


# ── Parseo del PDF ────────────────────────────────────────────────────────────

def _filtrar_watermark(page):
    return page.filter(
        lambda obj: obj.get("size", 0) < 50
        if obj["object_type"] == "char" else True
    )


def _fila_vacia(row) -> bool:
    return all(c is None or c.strip() == "" for c in row)


def _fila_continuacion(row) -> bool:
    if not row:
        return False
    primera = row[0]
    if primera and primera.strip():
        return False
    return any(c and c.strip() for c in row[1:])


def _parsear_codigo(texto: str):
    m = RE_CODIGO.match(texto.strip())
    if not m:
        return None
    curso, grado, grupo, cuatri = m.groups()
    if grado not in GRADOS:
        return None
    return int(curso), grado, int(grupo), int(cuatri)


def _normalizar_hora(h: str) -> str:
    return h.replace(".", ":").strip()


def _parsear_celda(texto: str) -> list[tuple[str, Optional[str], list[str]]]:
    """
    Estructura tipica por celda (multilinea):
        [aula_principal]     (opcional)
        asignatura(s)        (ej: "EdC / FFI")
        lab_1, lab_2         (opcional)

    Devuelve lista de tuplas (asignatura_alias, aula_principal, labs).
    """
    if not texto or not texto.strip():
        return []

    lineas = [linea.strip() for linea in texto.strip().split("\n") if linea.strip()]
    if not lineas:
        return []

    aula = None
    asignaturas_linea: Optional[str] = None
    labs: list[str] = []
    i = 0

    if RE_AULA.match(lineas[i].split(",")[0].strip()):
        aula = lineas[i].split(",")[0].strip()
        i += 1

    if i < len(lineas):
        candidato = lineas[i]
        partes = [p.strip() for p in candidato.replace("/", ",").split(",") if p.strip()]
        es_solo_labs = partes and all(RE_AULA_PREFIJO.match(p.rstrip("*")) for p in partes)
        if not es_solo_labs:
            asignaturas_linea = lineas[i]
            i += 1

    while i < len(lineas):
        for parte in lineas[i].split(","):
            parte = parte.strip().rstrip("*").replace("**", "").replace("*", "")
            if parte and RE_AULA_PREFIJO.match(parte):
                labs.append(parte)
        i += 1

    if not asignaturas_linea:
        return []

    asignaturas = [a.strip().rstrip("*").replace("**", "").replace("*", "")
                   for a in asignaturas_linea.split("/") if a.strip()]

    resultados = []
    for idx, asig in enumerate(asignaturas):
        if not asig or RE_AULA.match(asig):
            continue
        if re.match(r"^\d+\)", asig) or asig.startswith("("):
            continue
        resultados.append((asig, aula if idx == 0 else None, list(labs)))
    return resultados


def _extraer_franjas(raw_table):
    """
    Dada una tabla cruda de pdfplumber, devuelve codigo_info + lista de
    (hora_inicio, hora_fin, [celda_lunes, ..., celda_viernes]).
    """
    if not raw_table or len(raw_table) < 2:
        return None, None
    header = raw_table[0]
    if not header or not header[0]:
        return None, None
    codigo_info = _parsear_codigo(header[0])
    if not codigo_info:
        return None, None

    franjas = []
    cur_hora = None
    cur_celdas = [""] * 5

    for row in raw_table[1:]:
        if len(row) < 6:
            continue
        if _fila_vacia(row):
            if cur_hora:
                franjas.append((cur_hora, cur_celdas))
                cur_hora = None
                cur_celdas = [""] * 5
            continue

        primera = row[0]
        if primera and primera.strip() and "a " in primera:
            if cur_hora:
                franjas.append((cur_hora, cur_celdas))
            cur_hora = primera.strip().replace("\n", " ")
            cur_celdas = [""] * 5
            for d in range(5):
                val = row[d + 1]
                cur_celdas[d] = val.strip() if val else ""
        elif _fila_continuacion(row):
            if cur_hora:
                for d in range(5):
                    val = row[d + 1]
                    if val and val.strip():
                        cur_celdas[d] = (cur_celdas[d] + "\n" + val.strip()).strip() \
                            if cur_celdas[d] else val.strip()

    if cur_hora:
        franjas.append((cur_hora, cur_celdas))
    return codigo_info, franjas


def _franja_a_horas(franja_texto: str) -> Optional[tuple[str, str]]:
    m = RE_HORA_FRANJA.search(franja_texto)
    if not m:
        return None
    return _normalizar_hora(m.group(1)), _normalizar_hora(m.group(2))


def parsear_pdf(pdf_path: Path, curso_academico: str) -> ExtraccionHorarios:
    """
    PDF ETSII -> ExtraccionHorarios.
    """
    # Buckets temporales por (grado, curso, grupo) -> list[EntradaHorario]
    por_grupo: dict[tuple[str, int, int], list[EntradaHorario]] = defaultdict(list)

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            tablas = _filtrar_watermark(page).extract_tables()
            for raw_table in tablas:
                codigo_info, franjas = _extraer_franjas(raw_table)
                if not codigo_info or not franjas:
                    continue
                curso, grado, grupo, cuatri = codigo_info

                for hora_texto, celdas in franjas:
                    horas = _franja_a_horas(hora_texto)
                    if not horas:
                        continue
                    hora_ini, hora_fin = horas
                    for dia_idx, celda_texto in enumerate(celdas):
                        for asig, aula, labs in _parsear_celda(celda_texto):
                            por_grupo[(grado, curso, grupo)].append(EntradaHorario(
                                cuatrimestre=cuatri,
                                dia_semana=dia_idx + 1,
                                hora_inicio=hora_ini,
                                hora_fin=hora_fin,
                                asignatura_alias=asig,
                                aula_codigo=aula if aula and es_aula_valida(aula) else None,
                                labs=[lab for lab in labs if es_aula_valida(lab)],
                            ))

    extraccion = ExtraccionHorarios(
        centro_codigo=CENTRO_CODIGO,
        curso_academico=curso_academico,
    )

    for grado, (tit_codigo, carpeta, nombre_grado) in GRADOS.items():
        tit = TitulacionExtraida(codigo=tit_codigo, carpeta_md=carpeta, nombre_grado=nombre_grado)
        grupos_grado = sorted((k for k in por_grupo if k[0] == grado), key=lambda x: (x[1], x[2]))
        for _, curso, grupo in grupos_grado:
            tit.grupos.append(GrupoExtraido(
                curso=curso, grupo=grupo, entradas=por_grupo[(grado, curso, grupo)],
            ))
        if tit.grupos:
            extraccion.titulaciones.append(tit)

    return extraccion


# ── Pipeline completo ─────────────────────────────────────────────────────────

def ejecutar_pipeline(
    curso_academico: str = CURSO_ACADEMICO_DEFAULT,
    limpiar: bool = False,
    centro_id: str | None = None,
) -> dict:
    """
    Entry point llamado desde el admin.
    Descarga PDF (si falta) -> parsea -> escribe MD -> inserta en BD.
    """
    # Importacion perezosa para no crear ciclo en el registry
    from admin.db import query_one
    from actions.shared.config import ALIAS_ASIGNATURAS, ALIAS_POR_TITULACION

    # Resolver centro_id si no se proporciona
    if not centro_id:
        row = query_one("SELECT id FROM centros WHERE codigo = %s", (CENTRO_CODIGO,))
        if not row:
            raise RuntimeError(f"Centro {CENTRO_CODIGO} no encontrado en BD")
        centro_id = row["id"]

    # 1) descargar PDF
    pdf_path = descargar_pdf(PDF_URL, PDF_DIR / PDF_FILENAME)

    # 2) parsear
    extraccion = parsear_pdf(pdf_path, curso_academico)

    # 3) escribir MD
    archivos_md = escribir_markdown(extraccion, MD_DIR)

    # 4) preparar alias (ALIAS_ASIGNATURAS tiene claves en lowercase)
    alias_generico = {k.upper(): v for k, v in ALIAS_ASIGNATURAS.items()}
    alias_por_tit = {
        tit: {k.upper(): v for k, v in aliases.items()}
        for tit, aliases in ALIAS_POR_TITULACION.items()
    }

    # 5) insertar en BD
    res = insertar_en_bd(
        extraccion, centro_id,
        alias_generico=alias_generico,
        alias_por_titulacion=alias_por_tit,
        limpiar=limpiar,
    )

    return {
        "centro": CENTRO_CODIGO,
        "curso_academico": curso_academico,
        "titulaciones_procesadas": [t.codigo for t in extraccion.titulaciones],
        "grupos_extraidos": sum(len(t.grupos) for t in extraccion.titulaciones),
        "archivos_md_generados": len(archivos_md),
        "pdf_local": str(pdf_path),
        **res,
    }


if __name__ == "__main__":
    import json
    resultado = ejecutar_pipeline(limpiar="--clean" in __import__("sys").argv)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
