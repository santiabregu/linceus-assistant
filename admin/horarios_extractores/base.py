"""
Utilidades comunes a todos los extractores de horarios.

Cada extractor especifico de un centro produce una `ExtraccionHorarios`:
  - titulaciones: list[TitulacionExtraida]

Y estas funciones se encargan de:
  - escribir los markdowns (debug/backup humano)
  - insertar en BD (aulas, grupos_clase, horarios) de forma idempotente
"""

from __future__ import annotations

import re
import uuid
import urllib.request
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from admin.db import get_conn


# ── Modelos de datos ──────────────────────────────────────────────────────────


@dataclass
class EntradaHorario:
    cuatrimestre: int
    dia_semana: int          # 1=Lunes ... 5=Viernes
    hora_inicio: str         # "HH:MM"
    hora_fin: str
    asignatura_alias: str    # abreviatura tal cual sale del PDF
    aula_codigo: Optional[str] = None
    labs: list[str] = field(default_factory=list)


@dataclass
class GrupoExtraido:
    curso: int
    grupo: int
    entradas: list[EntradaHorario] = field(default_factory=list)


@dataclass
class TitulacionExtraida:
    codigo: str                            # "GII-IS"
    carpeta_md: str                        # "software"
    nombre_grado: str                      # "Ingenieria del Software"
    grupos: list[GrupoExtraido] = field(default_factory=list)


@dataclass
class ExtraccionHorarios:
    centro_codigo: str                     # "ETSII"
    curso_academico: str                   # "2025-26"
    titulaciones: list[TitulacionExtraida] = field(default_factory=list)


# ── Helpers ───────────────────────────────────────────────────────────────────

RE_AULA_VALIDA = re.compile(r"^[A-Z]\d+\.\d+[a-z]?$")
RE_CODIGO_AULA_PREFIJO = re.compile(r"^[A-Z]\d+\.\d+")


def es_aula_valida(codigo: str) -> bool:
    return bool(codigo and RE_AULA_VALIDA.match(codigo.strip()))


def normalizar(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def descargar_pdf(url: str, destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        return destino
    urllib.request.urlretrieve(url, str(destino))
    return destino


# ── Escritura markdown (debug / backup humano) ────────────────────────────────

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]


def escribir_markdown(extraccion: ExtraccionHorarios, base_dir: Path) -> list[Path]:
    """
    Escribe un archivo por (titulacion, curso, grupo) en base_dir/<carpeta>/.
    """
    archivos: list[Path] = []
    for tit in extraccion.titulaciones:
        dir_tit = base_dir / tit.carpeta_md
        dir_tit.mkdir(parents=True, exist_ok=True)

        # Agrupar entradas por (curso, grupo, cuatrimestre, franja horaria)
        por_grupo: dict[tuple[int, int], dict[int, dict[tuple[str, str], list[str]]]] = {}
        for g in tit.grupos:
            key = (g.curso, g.grupo)
            por_grupo.setdefault(key, {})
            for e in g.entradas:
                por_cuatri = por_grupo[key].setdefault(e.cuatrimestre, {})
                franja = (e.hora_inicio, e.hora_fin)
                slot = por_cuatri.setdefault(franja, ["-"] * 5)
                slot_idx = e.dia_semana - 1
                if 0 <= slot_idx < 5:
                    celda = _formatear_celda_md(e)
                    if slot[slot_idx] == "-":
                        slot[slot_idx] = celda
                    else:
                        slot[slot_idx] += f" / {celda}"

        for (curso, grupo), cuatris in sorted(por_grupo.items()):
            path = dir_tit / f"curso{curso}_grupo{grupo}.md"
            lineas = [f"# Horario - {tit.nombre_grado}",
                      f"## Curso {curso} - Grupo {grupo}", ""]
            for cuatri in sorted(cuatris.keys()):
                lineas.append(f"### Cuatrimestre {cuatri}")
                lineas.append("")
                lineas.append(f"| Hora | {' | '.join(DIAS)} |")
                lineas.append(f"|------|{'|'.join(['------'] * 5)}|")
                for franja in sorted(cuatris[cuatri].keys()):
                    celdas = cuatris[cuatri][franja]
                    lineas.append(f"| {franja[0]} - {franja[1]} | {' | '.join(celdas)} |")
                lineas.append("")
            path.write_text("\n".join(lineas), encoding="utf-8")
            archivos.append(path)

    return archivos


def _formatear_celda_md(e: EntradaHorario) -> str:
    partes = []
    if e.aula_codigo:
        partes.append(e.aula_codigo)
    if e.labs:
        partes.append(", ".join(e.labs))
    if partes:
        return f"{e.asignatura_alias} ({', '.join(partes)})"
    return e.asignatura_alias


# ── Inserccion en BD ──────────────────────────────────────────────────────────

def limpiar_tablas_centro(conn, centro_id: str) -> None:
    """
    Borra horarios/grupos_clase/aulas relacionados con el centro.
    Relacion: aula.centro_id = centro; grupos_clase via asignatura.titulacion.centro.
    """
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM horarios h
        USING grupos_clase gc
        JOIN asignaturas a ON a.id = gc.asignatura_id
        JOIN titulaciones t ON t.id = a.titulacion_id
        WHERE h.grupo_id = gc.id AND t.centro_id = %s
    """, (centro_id,))
    cur.execute("""
        DELETE FROM grupos_clase gc
        USING asignaturas a, titulaciones t
        WHERE gc.asignatura_id = a.id AND a.titulacion_id = t.id AND t.centro_id = %s
    """, (centro_id,))
    cur.execute("DELETE FROM aulas WHERE centro_id = %s", (centro_id,))
    conn.commit()
    cur.close()


def _cargar_mapa_asignaturas(conn, centro_id: str) -> dict[tuple[str, str], str]:
    """Retorna {(titulacion_codigo, nombre_normalizado): asignatura_id}."""
    cur = conn.cursor()
    cur.execute("""
        SELECT a.id, a.nombre, t.codigo
        FROM asignaturas a
        JOIN titulaciones t ON a.titulacion_id = t.id
        WHERE a.activa = true AND t.centro_id = %s
    """, (centro_id,))
    mapa = {(tit, normalizar(nombre)): str(aid) for aid, nombre, tit in cur.fetchall()}
    cur.close()
    return mapa


def _resolver_alias(
    alias: str,
    titulacion: str,
    mapa_asignaturas: dict,
    alias_generico: dict,
    alias_por_tit: dict,
) -> Optional[str]:
    a = alias.upper().strip()
    if RE_CODIGO_AULA_PREFIJO.match(a):
        return None
    a = re.sub(r"\(\d+\)$", "", a).strip()

    nombre_norm = alias_por_tit.get(titulacion, {}).get(a) or alias_generico.get(a)
    if not nombre_norm:
        return None

    asig_id = mapa_asignaturas.get((titulacion, nombre_norm))
    if asig_id:
        return asig_id
    for (t, n), aid in mapa_asignaturas.items():
        if t == titulacion and nombre_norm in n:
            return aid
    return None


def insertar_en_bd(
    extraccion: ExtraccionHorarios,
    centro_id: str,
    alias_generico: dict,
    alias_por_titulacion: dict,
    limpiar: bool = False,
) -> dict:
    """
    Inserta una ExtraccionHorarios completa en aulas/grupos_clase/horarios.

    Args:
        alias_generico: dict {"ALIAS" -> "nombre normalizado de asignatura"}
        alias_por_titulacion: dict {"GII-IS": {"SSII": "nombre norm"}}
    Returns:
        dict con contadores y alias no resueltos.
    """
    conn = get_conn()
    try:
        if limpiar:
            limpiar_tablas_centro(conn, centro_id)

        mapa_asig = _cargar_mapa_asignaturas(conn, centro_id)

        # 1) aulas (dedup)
        aulas_validas: set[str] = set()
        for tit in extraccion.titulaciones:
            for g in tit.grupos:
                for e in g.entradas:
                    if e.aula_codigo and es_aula_valida(e.aula_codigo):
                        aulas_validas.add(e.aula_codigo)
                    for lab in e.labs:
                        if es_aula_valida(lab):
                            aulas_validas.add(lab)

        cur = conn.cursor()
        cur.execute("SELECT id, codigo FROM aulas WHERE centro_id = %s", (centro_id,))
        mapa_aulas = {codigo: str(aid) for aid, codigo in cur.fetchall()}
        nuevas_aulas = 0
        for codigo in sorted(aulas_validas - set(mapa_aulas.keys())):
            m = re.match(r"([A-Z])(\d+)\.\d+", codigo)
            edificio = m.group(1) if m else None
            planta = m.group(2) if m else None
            tipo = "laboratorio" if edificio in ("G", "F", "B", "I") else "teoria"
            aid = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO aulas (id, centro_id, codigo, edificio, planta, tipo, activa)
                VALUES (%s, %s, %s, %s, %s, %s, true)
            """, (aid, centro_id, codigo, edificio, planta, tipo))
            mapa_aulas[codigo] = aid
            nuevas_aulas += 1
        conn.commit()

        # 2) grupos_clase + 3) horarios
        # Modelo: un "Grupo 1" de teoría es UNA sola fila en grupos_clase
        # (existe la UNIQUE (asignatura_id, codigo, curso_academico, tipo)).
        # El cuatrimestre vive a nivel de `horarios`, porque lo que cambia
        # entre C1 y C2 es el horario semanal del alumno, no la entidad
        # "grupo de teoría". Asignaturas anuales (duracion='A') generan
        # filas en `horarios` con cuatri=1 y cuatri=2 colgando del mismo
        # `grupo_clase`. Ver D-066.
        cur.execute("""
            SELECT gc.id, gc.asignatura_id, gc.codigo
            FROM grupos_clase gc
            JOIN asignaturas a ON a.id = gc.asignatura_id
            JOIN titulaciones t ON t.id = a.titulacion_id
            WHERE t.centro_id = %s AND gc.curso_academico = %s
        """, (centro_id, extraccion.curso_academico))
        mapa_gc = {(str(asig_id), codigo): str(gc_id)
                   for gc_id, asig_id, codigo in cur.fetchall()}

        nuevos_grupos = 0
        nuevos_horarios = 0
        alias_no_resueltos: set[str] = set()

        for tit in extraccion.titulaciones:
            for g in tit.grupos:
                for e in g.entradas:
                    asig_id = _resolver_alias(
                        e.asignatura_alias, tit.codigo, mapa_asig,
                        alias_generico, alias_por_titulacion,
                    )
                    if not asig_id:
                        alias_no_resueltos.add(e.asignatura_alias)
                        continue

                    gc_codigo = str(g.grupo)
                    gc_key = (asig_id, gc_codigo)
                    if gc_key not in mapa_gc:
                        gc_id = str(uuid.uuid4())
                        cur.execute("""
                            INSERT INTO grupos_clase
                                (id, asignatura_id, codigo, nombre, tipo,
                                 curso_academico, activo)
                            VALUES (%s, %s, %s, %s, 'teoria', %s, true)
                        """, (gc_id, asig_id, gc_codigo, f"Grupo {g.grupo}",
                              extraccion.curso_academico))
                        mapa_gc[gc_key] = gc_id
                        nuevos_grupos += 1

                    # Una fila en `horarios` por cada aula del slot:
                    # la principal (`aula_codigo`) + cada lab/aula adicional
                    # (`labs`). El schema admite varias filas con mismo
                    # (grupo, día, hora, cuatri) y distinta aula.
                    codigos_aulas = []
                    if e.aula_codigo:
                        codigos_aulas.append(e.aula_codigo)
                    for lab in e.labs:
                        if lab and lab not in codigos_aulas:
                            codigos_aulas.append(lab)
                    if not codigos_aulas:
                        codigos_aulas = [None]  # slot sin aula registrada

                    for codigo_aula in codigos_aulas:
                        aula_id = mapa_aulas.get(codigo_aula) if codigo_aula else None
                        hid = str(uuid.uuid4())
                        cur.execute("""
                            INSERT INTO horarios
                                (id, grupo_id, aula_id, dia_semana,
                                 hora_inicio, hora_fin, cuatrimestre, activo)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, true)
                        """, (hid, mapa_gc[gc_key], aula_id,
                              e.dia_semana, e.hora_inicio, e.hora_fin,
                              str(e.cuatrimestre)))
                        nuevos_horarios += 1
        conn.commit()
        cur.close()

        return {
            "aulas_insertadas": nuevas_aulas,
            "grupos_clase_insertados": nuevos_grupos,
            "horarios_insertados": nuevos_horarios,
            "alias_no_resueltos": sorted(alias_no_resueltos),
        }
    finally:
        conn.close()
