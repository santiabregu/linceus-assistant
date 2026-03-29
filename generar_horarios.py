"""
generar_horarios.py
-------------------
Extrae los horarios del PDF oficial de la ETSII (curso 2025-26) para las 3 titulaciones
activas en Supabase (GII-IC, GII-IS, GII-TI) y genera archivos Markdown organizados
en horarios_aulas/{computadores,software,tecnologias_informaticas}/cursoX_grupoY.md

Cada archivo contiene las tablas de ambos cuatrimestres (C1 y C2).

Uso:
    python generar_horarios.py [ruta_pdf]

    Si no se pasa ruta, descarga el PDF de la web de la ETSII.

Requisitos:
    pip install pdfplumber
"""

import os
import re
import sys
import pdfplumber
from collections import defaultdict

# ─── Configuración ──────────────────────────────────────────────────────────

PDF_URL = "https://www.informatica.us.es/docs/orgdocente/horarios-grados-2025-26.pdf"
PDF_LOCAL = "horarios-grados-2025-26.pdf"

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "horarios_aulas")

# Mapeo código grado → carpeta
GRADO_CARPETA = {
    "C": "computadores",
    "S": "software",
    "T": "tecnologias_informaticas",
}

# Solo procesamos estos códigos de grado
GRADOS_VALIDOS = set(GRADO_CARPETA.keys())

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
DIAS_HEADER = ["L.", "Ma.", "Mi.", "J.", "V."]

# Patrón para identificar el código de tabla: xGy-Cz
# x = curso (1-4), G = letra grado (C/S/T), y = grupo (1-9), z = cuatrimestre (1/2)
RE_CODIGO = re.compile(r"^(\d)([A-Z])(\d)-C([12])$")

# Patrón para identificar aulas (empieza con letra + número + punto + números)
RE_AULA = re.compile(r"^[A-Z]\d+\.\d+[a-z]?$")

# Patrón para identificar labs (códigos como G1.32, F1.30, B1.31, I2.33, etc.)
RE_LAB = re.compile(r"^[A-Z]\d+\.\d+")


# ─── Funciones de extracción ────────────────────────────────────────────────

def descargar_pdf(url, destino):
    """Descarga el PDF si no existe localmente."""
    if os.path.exists(destino):
        print(f"  PDF ya existe: {destino}")
        return destino
    print(f"  Descargando PDF desde {url}...")
    import urllib.request
    urllib.request.urlretrieve(url, destino)
    print(f"  Descargado: {destino}")
    return destino


def filtrar_watermark(page):
    """Filtra el watermark 'BORRADOR DE HORARIOS' (size=59) de la página."""
    return page.filter(
        lambda obj: obj.get("size", 0) < 50
        if obj["object_type"] == "char"
        else True
    )


def es_fila_vacia(row):
    """Comprueba si una fila está vacía o solo tiene strings vacíos/None."""
    return all(c is None or c.strip() == "" for c in row)


def es_fila_continuacion(row):
    """
    Una fila de continuación tiene None o '' en la primera columna
    (no tiene hora) pero tiene contenido en otras columnas.
    """
    if not row:
        return False
    primera = row[0]
    if primera is not None and primera.strip() != "":
        return False
    return any(c is not None and c.strip() != "" for c in row[1:])


def parsear_codigo(codigo):
    """
    Parsea un código como '1C1-C1' y retorna (curso, grado, grupo, cuatrimestre)
    o None si no coincide con el patrón de grados válidos.
    """
    m = RE_CODIGO.match(codigo.strip())
    if not m:
        return None
    curso, grado, grupo, cuatri = m.groups()
    if grado not in GRADOS_VALIDOS:
        return None
    return int(curso), grado, int(grupo), int(cuatri)


def parsear_celda(texto):
    """
    Parsea el contenido de una celda del horario.
    Retorna un string formateado: 'ASIGNATURA (aula, labs)' o '' si vacío.

    Estructura típica de celda:
    - Línea 1: Aula principal (ej: H0.11) - puede estar o no
    - Línea 2: Asignatura(s) (ej: ALN, EdC / FFI)
    - Líneas 3+: Labs (ej: G1.32,G1.35)
    """
    if not texto or texto.strip() == "":
        return ""

    lineas = [l.strip() for l in texto.strip().split("\n") if l.strip()]
    if not lineas:
        return ""

    aula = ""
    asignatura = ""
    labs = []

    i = 0
    # Intentar detectar aula principal en la primera línea
    if i < len(lineas) and RE_AULA.match(lineas[i].split(",")[0].strip()):
        aula = lineas[i]
        i += 1

    # La siguiente línea es la asignatura
    if i < len(lineas):
        # Verificar que no es solo una lista de labs
        candidato = lineas[i]
        partes = [p.strip() for p in candidato.replace("/", ",").split(",") if p.strip()]
        es_solo_labs = all(RE_LAB.match(p.rstrip("*")) for p in partes if p)
        if not es_solo_labs:
            asignatura = lineas[i]
            i += 1

    # El resto son labs
    while i < len(lineas):
        labs.append(lineas[i])
        i += 1

    # Si no encontramos asignatura pero sí labs, la primera parte puede ser la asignatura
    if not asignatura and labs:
        asignatura = labs.pop(0)

    if not asignatura and aula:
        # Solo teníamos aula, sin asignatura clara
        return ""

    if not asignatura:
        return ""

    # Limpiar asteriscos
    labs_str = ", ".join(labs).replace("**", "").replace("*", "").strip().rstrip(",")
    asignatura = asignatura.replace("**", "").replace("*", "").strip()

    # Construir resultado
    partes_info = []
    if aula:
        partes_info.append(aula)
    if labs_str:
        partes_info.append(labs_str)

    resultado = ""
    if partes_info:
        resultado = f"{asignatura} ({', '.join(partes_info)})"
    else:
        resultado = asignatura

    # Limpiar comas dobles y espacios extra
    resultado = re.sub(r",\s*,", ",", resultado)
    resultado = re.sub(r"\s{2,}", " ", resultado)
    return resultado


def extraer_tabla(raw_table):
    """
    Extrae datos de una tabla pdfplumber.
    Retorna (codigo_info, filas_horario) o (None, None) si no es válida.

    filas_horario = [(hora, [contenido_lunes, ..., contenido_viernes]), ...]
    """
    if not raw_table or len(raw_table) < 2:
        return None, None

    # Primera fila = header
    header = raw_table[0]
    if not header or not header[0]:
        return None, None

    codigo_info = parsear_codigo(header[0])
    if not codigo_info:
        return None, None

    # Procesar filas de datos: agrupar por franja horaria
    franjas = []
    current_hora = None
    current_celdas = [None] * 5  # 5 días

    for row in raw_table[1:]:
        if len(row) < 6:
            continue

        if es_fila_vacia(row):
            # Guardar franja actual si existe
            if current_hora:
                franjas.append((current_hora, current_celdas))
                current_hora = None
                current_celdas = [None] * 5
            continue

        primera = row[0]
        if primera is not None and primera.strip() != "" and "a " in primera:
            # Nueva franja horaria
            if current_hora:
                franjas.append((current_hora, current_celdas))

            current_hora = primera.strip().replace("\n", " ")
            current_celdas = [""] * 5
            for d in range(5):
                val = row[d + 1]
                current_celdas[d] = val.strip() if val else ""
        elif es_fila_continuacion(row):
            # Continuación de la franja actual
            if current_hora:
                for d in range(5):
                    val = row[d + 1]
                    if val and val.strip():
                        if current_celdas[d]:
                            current_celdas[d] += "\n" + val.strip()
                        else:
                            current_celdas[d] = val.strip()

    # Guardar última franja
    if current_hora:
        franjas.append((current_hora, current_celdas))

    return codigo_info, franjas


def extraer_horarios_pdf(pdf_path):
    """
    Extrae todos los horarios del PDF para los grados válidos.
    Retorna un dict: {(grado, curso, grupo): {cuatrimestre: [(hora, [celdas])]}}
    """
    horarios = defaultdict(lambda: {})

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            filtered = filtrar_watermark(page)
            tables = filtered.extract_tables()

            for raw_table in tables:
                codigo_info, franjas = extraer_tabla(raw_table)
                if not codigo_info or not franjas:
                    continue

                curso, grado, grupo, cuatri = codigo_info
                key = (grado, curso, grupo)
                horarios[key][cuatri] = franjas
                print(f"  Extraído: {curso}{grado}{grupo}-C{cuatri} ({len(franjas)} franjas)")

    return horarios


# ─── Generación de Markdown ─────────────────────────────────────────────────

def formatear_hora(hora_raw):
    """Formatea '8:30 a 10:20' → '8:30 - 10:20'."""
    return hora_raw.replace(" a ", " - ").replace("a ", "- ")


def generar_tabla_md(franjas):
    """Genera una tabla Markdown a partir de las franjas horarias."""
    lineas = []
    lineas.append(f"| Hora | {' | '.join(DIAS)} |")
    lineas.append(f"|------|{'|'.join(['------'] * 5)}|")

    for hora_raw, celdas in franjas:
        hora = formatear_hora(hora_raw)
        contenidos = []
        for c in celdas:
            parsed = parsear_celda(c)
            contenidos.append(parsed if parsed else "-")
        lineas.append(f"| {hora} | {' | '.join(contenidos)} |")

    return "\n".join(lineas)


NOMBRES_GRADO = {
    "C": "Ingeniería de Computadores",
    "S": "Ingeniería del Software",
    "T": "Tecnologías Informáticas",
}


def generar_markdown(grado, curso, grupo, cuatrimestres):
    """Genera el contenido Markdown completo para un archivo de horario."""
    nombre_grado = NOMBRES_GRADO[grado]
    lineas = [
        f"# Horario - {nombre_grado}",
        f"## Curso {curso} - Grupo {grupo}",
        "",
    ]

    for cuatri in sorted(cuatrimestres.keys()):
        franjas = cuatrimestres[cuatri]
        lineas.append(f"### Cuatrimestre {cuatri}")
        lineas.append("")
        lineas.append(generar_tabla_md(franjas))
        lineas.append("")

    return "\n".join(lineas)


def guardar_horarios(horarios):
    """Guarda los horarios en archivos Markdown organizados por titulación."""
    archivos_creados = []

    for (grado, curso, grupo), cuatrimestres in sorted(horarios.items()):
        carpeta = GRADO_CARPETA[grado]
        dir_path = os.path.join(BASE_DIR, carpeta)
        os.makedirs(dir_path, exist_ok=True)

        filename = f"curso{curso}_grupo{grupo}.md"
        filepath = os.path.join(dir_path, filename)

        contenido = generar_markdown(grado, curso, grupo, cuatrimestres)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(contenido)

        archivos_creados.append(filepath)
        print(f"  Creado: {os.path.relpath(filepath)}")

    return archivos_creados


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    print("=== Generador de Horarios ETSII ===\n")

    # Determinar ruta del PDF
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), PDF_LOCAL
        )
        if not os.path.exists(pdf_path):
            descargar_pdf(PDF_URL, pdf_path)

    if not os.path.exists(pdf_path):
        print(f"Error: No se encuentra el PDF: {pdf_path}")
        sys.exit(1)

    print(f"PDF: {pdf_path}\n")

    # 1. Extraer horarios
    print("1. Extrayendo horarios del PDF...")
    horarios = extraer_horarios_pdf(pdf_path)
    print(f"\n  Total: {len(horarios)} combinaciones curso/grupo extraídas\n")

    # 2. Generar archivos Markdown
    print("2. Generando archivos Markdown...")
    archivos = guardar_horarios(horarios)
    print(f"\n  Total: {len(archivos)} archivos creados\n")

    # 3. Resumen
    print("=== Resumen ===")
    for grado_code, carpeta in GRADO_CARPETA.items():
        nombre = NOMBRES_GRADO[grado_code]
        n = sum(1 for k in horarios if k[0] == grado_code)
        print(f"  {nombre}: {n} archivos")

    print(f"\nArchivos en: {BASE_DIR}/")
    print("¡Listo!")


if __name__ == "__main__":
    main()
