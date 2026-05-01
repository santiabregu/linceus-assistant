"""
Pipeline de vectorización de proyectos docentes.

Orquesta el proceso completo:
  1. Descubre PDFs en proyectos_docentes/ing_software/
  2. Extrae texto con pdfplumber
  3. Segmenta por secciones del proyecto docente
  4. Genera embeddings con Gemini text-embedding-004
  5. Inserta chunks + vectores en Supabase (planes_docentes_chunks)

Gestión de actualizaciones:
  - Compara hash SHA256 del PDF con el almacenado en planes_docentes
  - Si el hash cambia → borra chunks antiguos → re-procesa
  - Si el hash coincide → skip (ya vectorizado)

Uso:
    python -m rag.pipeline                   # Procesar todos los PDFs
    python -m rag.pipeline --dry-run         # Solo mostrar qué se haría
    python -m rag.pipeline --asignatura 2050001   # Solo una asignatura
    python -m rag.pipeline --stats           # Mostrar estadísticas
"""

import re
import sys
import time
import argparse
from pathlib import Path
from typing import List, Dict, Optional

# Forzar UTF-8 en consola Windows (evita UnicodeEncodeError con emojis)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Asegurar que el directorio raíz del proyecto está en el path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag.extraer_pdf import extraer_texto_completo, extraer_metadata_basica  # noqa: E402
from rag.chunking import procesar_documento  # noqa: E402
from rag.embeddings import generar_embeddings_batch, verificar_embeddings  # noqa: E402
from rag.db_vectores import (  # noqa: E402
    calcular_hash_pdf,
    obtener_asignatura_id,
    obtener_plan_existente,
    crear_plan_docente,
    borrar_chunks_plan,
    insertar_chunks,
    actualizar_estado_plan,
    actualizar_hash_plan,
    obtener_estadisticas,
    obtener_codigos_con_error,
)

# ── Configuración ──────────────────────────────────────────────────────────────
PROYECTOS_DIR = PROJECT_ROOT / "knowledge_base" / "proyectos_docentes" / "ing_software"
CURSO_ACADEMICO = "2025-26"

# Patrón para extraer nombre y código de las carpetas de asignatura
PATRON_CARPETA = re.compile(r"^(.+)\((\d+)\)\s*$")
# Patrón para extraer número de grupo
PATRON_GRUPO = re.compile(r"^Grupo\s+(.+)$")


def descubrir_pdfs() -> List[Dict]:
    """
    Escanea la estructura de carpetas y devuelve todos los PDFs encontrados.

    Returns:
        Lista de dicts con:
            - ruta_pdf (Path): Ruta al PDF.
            - codigo_asignatura (str): Código extraído de la carpeta.
            - nombre_asignatura (str): Nombre extraído de la carpeta.
            - grupo (str): Nombre del grupo (ej: "Grupo 1").
    """
    pdfs = []

    if not PROYECTOS_DIR.exists():
        print(f"❌ Directorio no encontrado: {PROYECTOS_DIR}")
        return pdfs

    for carpeta_asig in sorted(PROYECTOS_DIR.iterdir()):
        if not carpeta_asig.is_dir():
            continue

        match = PATRON_CARPETA.match(carpeta_asig.name)
        if not match:
            continue

        nombre_asig = match.group(1).strip()
        codigo_asig = match.group(2).strip()

        for carpeta_grupo in sorted(carpeta_asig.iterdir()):
            if not carpeta_grupo.is_dir():
                continue

            grupo_match = PATRON_GRUPO.match(carpeta_grupo.name)
            if not grupo_match:
                continue

            grupo_nombre = carpeta_grupo.name

            # Buscar PDF dentro del grupo
            pdf_files = list(carpeta_grupo.glob("*.pdf"))
            if len(pdf_files) == 1:
                pdfs.append({
                    "ruta_pdf": pdf_files[0],
                    "codigo_asignatura": codigo_asig,
                    "nombre_asignatura": nombre_asig,
                    "grupo": grupo_nombre,
                })
            elif len(pdf_files) > 1:
                print(f"  ⚠ Múltiples PDFs en {carpeta_grupo.name}, "
                      f"usando el primero")
                pdfs.append({
                    "ruta_pdf": pdf_files[0],
                    "codigo_asignatura": codigo_asig,
                    "nombre_asignatura": nombre_asig,
                    "grupo": grupo_nombre,
                })

    return pdfs


def procesar_pdf(
    pdf_info: Dict,
    dry_run: bool = False,
    forzar: bool = False,
) -> Dict:
    """
    Procesa un solo PDF: extrae, chunka, embeddiza e inserta.

    Args:
        pdf_info: Dict con ruta_pdf, codigo_asignatura, nombre_asignatura, grupo.
        dry_run: Si True, solo muestra qué haría sin ejecutar.
        forzar: Si True, re-procesa aunque el hash no haya cambiado.

    Returns:
        Dict con resultado del procesamiento.
    """
    ruta_pdf = pdf_info["ruta_pdf"]
    codigo = pdf_info["codigo_asignatura"]
    nombre = pdf_info["nombre_asignatura"]
    grupo = pdf_info["grupo"]

    resultado = {
        "asignatura": f"{nombre} ({codigo})",
        "grupo": grupo,
        "estado": "pendiente",
        "chunks": 0,
        "accion": "",
    }

    # 1. Obtener asignatura_id
    asignatura_id = obtener_asignatura_id(codigo)
    if not asignatura_id:
        resultado["estado"] = "error"
        resultado["accion"] = f"Asignatura {codigo} no encontrada en BD"
        print(f"  ⚠ {nombre} ({codigo}) - {grupo}: "
              f"asignatura no encontrada en BD, saltando")
        return resultado

    # 2. Calcular hash del PDF
    hash_actual = calcular_hash_pdf(ruta_pdf)

    # 3. Buscar plan existente
    plan_existente = obtener_plan_existente(asignatura_id, CURSO_ACADEMICO, grupo)

    if plan_existente:
        if plan_existente["hash_documento"] == hash_actual and not forzar and plan_existente["estado_rag"] != "error":
            resultado["estado"] = "sin_cambios"
            resultado["accion"] = "Hash coincide, ya vectorizado"
            return resultado
        else:
            # El PDF cambió → re-procesar
            resultado["accion"] = "Actualización: borrando chunks anteriores"
            if not dry_run:
                borrados = borrar_chunks_plan(plan_existente["id"])
                print(f"  🗑️ Borrados {borrados} chunks antiguos")
                actualizar_hash_plan(plan_existente["id"], hash_actual)
                actualizar_estado_plan(plan_existente["id"], "procesando")
            plan_docente_id = plan_existente["id"]
    else:
        resultado["accion"] = "Nuevo plan docente"

    if dry_run:
        resultado["estado"] = "dry_run"
        return resultado

    # 4. Extraer texto del PDF
    try:
        texto_completo = extraer_texto_completo(ruta_pdf)
        metadata_pdf = extraer_metadata_basica(ruta_pdf)
    except Exception as e:
        resultado["estado"] = "error"
        resultado["accion"] = f"Error extrayendo PDF: {e}"
        return resultado

    # 5. Crear plan docente si no existe
    if not plan_existente:
        plan_docente_id = crear_plan_docente(
            asignatura_id=asignatura_id,
            curso_academico=CURSO_ACADEMICO,
            grupo=grupo,
            hash_documento=hash_actual,
            coordinador_nombre=metadata_pdf.get("coordinador"),
        )
        if not plan_docente_id:
            resultado["estado"] = "error"
            resultado["accion"] = "Error creando plan docente en BD"
            return resultado

    # 6. Chunking
    chunks = procesar_documento(texto_completo)
    if not chunks:
        actualizar_estado_plan(plan_docente_id, "error", "No se generaron chunks")
        resultado["estado"] = "error"
        resultado["accion"] = "No se generaron chunks del texto"
        return resultado

    # 7. Generar embeddings
    textos_chunks = [c["contenido"] for c in chunks]
    try:
        embeddings = generar_embeddings_batch(textos_chunks)
    except Exception as e:
        actualizar_estado_plan(plan_docente_id, "error", str(e))
        resultado["estado"] = "error"
        resultado["accion"] = f"Error generando embeddings: {e}"
        return resultado

    # Verificar que todos los embeddings se generaron
    embeddings_validos = sum(1 for e in embeddings if e is not None)
    if embeddings_validos == 0:
        actualizar_estado_plan(plan_docente_id, "error", "Ningún embedding generado")
        resultado["estado"] = "error"
        resultado["accion"] = "Ningún embedding generado"
        return resultado

    # 8. Insertar chunks en BD
    metadata_extra = {
        "asignatura_codigo": codigo,
        "asignatura_nombre": nombre,
        "curso_academico": CURSO_ACADEMICO,
        "grupo": grupo,
        "titulacion": "GII-IS",
    }

    insertados = insertar_chunks(plan_docente_id, chunks, embeddings, metadata_extra)

    # 9. Actualizar estado
    if insertados > 0:
        actualizar_estado_plan(plan_docente_id, "completado")
        resultado["estado"] = "completado"
        resultado["chunks"] = insertados
        resultado["accion"] = f"{insertados} chunks insertados"
    else:
        actualizar_estado_plan(plan_docente_id, "error", "0 chunks insertados")
        resultado["estado"] = "error"
        resultado["accion"] = "0 chunks insertados"

    return resultado


def ejecutar_pipeline(
    dry_run: bool = False,
    filtro_asignatura: Optional[str] = None,
    forzar: bool = False,
    solo_errores: bool = False,
) -> None:
    """
    Ejecuta el pipeline completo de vectorización.

    Args:
        dry_run: Si True, solo muestra qué haría.
        filtro_asignatura: Si se indica, solo procesa esa asignatura (código).
        forzar: Si True, re-procesa todo aunque no haya cambios.
        solo_errores: Si True, solo procesa planes con estado_rag = 'error'.
    """
    print("=" * 70)
    print("🚀 PIPELINE DE VECTORIZACIÓN DE PROYECTOS DOCENTES")
    print(f"   Curso: {CURSO_ACADEMICO}")
    print(f"   Directorio: {PROYECTOS_DIR}")
    print(f"   Modo: {'DRY RUN (sin cambios)' if dry_run else 'EJECUCIÓN REAL'}")
    if filtro_asignatura:
        print(f"   Filtro: asignatura {filtro_asignatura}")
    if forzar:
        print("   ⚠ Forzando re-procesamiento")
    if solo_errores:
        print("   🔁 Solo re-procesando planes con errores")
    print("=" * 70)

    # 1. Verificar embeddings (solo si no es dry-run)
    if not dry_run:
        print("\n📡 Verificando conexión con Gemini Embeddings...")
        if not verificar_embeddings():
            print("❌ No se puede conectar con Gemini. Abortando.")
            return

    # 2. Descubrir PDFs
    print("\n📂 Descubriendo PDFs...")
    pdfs = descubrir_pdfs()

    if filtro_asignatura:
        pdfs = [p for p in pdfs if p["codigo_asignatura"] == filtro_asignatura]

    if solo_errores:
        codigos_error = obtener_codigos_con_error(CURSO_ACADEMICO)
        if not codigos_error:
            print("   ✅ No hay planes con errores. Nada que re-procesar.")
            return
        pdfs = [
            p for p in pdfs
            if (p["codigo_asignatura"], p["grupo"]) in codigos_error
        ]
        print(f"   Planes con error encontrados: {len(codigos_error)}")

    print(f"   Encontrados: {len(pdfs)} PDFs")

    if not pdfs:
        print("   No hay PDFs que procesar.")
        return

    # 3. Procesar cada PDF
    print(f"\n{'─' * 70}")
    resultados = {
        "completado": 0,
        "sin_cambios": 0,
        "error": 0,
        "dry_run": 0,
        "total_chunks": 0,
    }

    inicio_total = time.time()

    for i, pdf_info in enumerate(pdfs, start=1):
        nombre_corto = f"{pdf_info['nombre_asignatura']} - {pdf_info['grupo']}"
        print(f"\n[{i}/{len(pdfs)}] {nombre_corto}")

        inicio_pdf = time.time()
        resultado = procesar_pdf(pdf_info, dry_run=dry_run, forzar=forzar)
        duracion_pdf = time.time() - inicio_pdf

        estado = resultado["estado"]
        resultados[estado] = resultados.get(estado, 0) + 1
        resultados["total_chunks"] += resultado["chunks"]

        icono = {
            "completado": "✅",
            "sin_cambios": "⏭️",
            "error": "❌",
            "dry_run": "🔍",
        }.get(estado, "❓")

        print(f"   {icono} {resultado['accion']} ({duracion_pdf:.1f}s)")

    # 4. Resumen
    duracion_total = time.time() - inicio_total
    print(f"\n{'=' * 70}")
    print("📊 RESUMEN")
    print(f"   Tiempo total: {duracion_total:.1f}s")
    print(f"   Completados:  {resultados['completado']}")
    print(f"   Sin cambios:  {resultados['sin_cambios']}")
    print(f"   Errores:      {resultados['error']}")
    print(f"   Total chunks: {resultados['total_chunks']}")
    if dry_run:
        print(f"   Dry run:      {resultados['dry_run']}")
    print("=" * 70)


def mostrar_estadisticas() -> None:
    """Muestra estadísticas del estado actual de la vectorización."""
    stats = obtener_estadisticas()
    if not stats:
        print("❌ No se pudieron obtener estadísticas")
        return

    print("\n📊 ESTADÍSTICAS DE VECTORIZACIÓN")
    print(f"   Planes docentes: {stats['total_planes']}")
    print(f"   Chunks totales:  {stats['total_chunks']}")
    if stats["por_estado"]:
        print("   Por estado:")
        for estado, count in stats["por_estado"].items():
            print(f"     - {estado}: {count}")
    else:
        print("   No hay planes docentes registrados.")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Pipeline de vectorización de proyectos docentes"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo muestra qué se haría, sin ejecutar cambios",
    )
    parser.add_argument(
        "--asignatura",
        type=str,
        default=None,
        help="Código de asignatura para procesar solo esa (ej: 2050001)",
    )
    parser.add_argument(
        "--forzar",
        action="store_true",
        help="Re-procesar aunque el hash no haya cambiado",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Mostrar estadísticas actuales y salir",
    )
    parser.add_argument(
        "--solo-errores",
        action="store_true",
        help="Solo re-procesar planes con estado_rag = 'error'",
    )
    args = parser.parse_args()

    if args.stats:
        mostrar_estadisticas()
        return

    ejecutar_pipeline(
        dry_run=args.dry_run,
        filtro_asignatura=args.asignatura,
        forzar=args.forzar,
        solo_errores=args.solo_errores,
    )


if __name__ == "__main__":
    main()
