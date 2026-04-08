"""
Script para crear subcarpetas de grupos (curso 2025-26) dentro de cada carpeta
de asignatura que ya existe en proyectos_docentes/ing_software/.

Flujo:
  1. Lee todas las carpetas existentes en BASE_DIR (formato "Nombre (codigo)").
  2. Para cada una, hace scraping en sevius4.us.es y detecta los grupos 2025-26.
  3. Crea una subcarpeta por cada grupo encontrado (puede ser 1, 2, 3, 4, 5…).

Estructura resultante:
    proyectos_docentes/ing_software/
        Nombre asignatura (codigo)/
            Grupo 1/
            Grupo 2/
            ...
"""

import os
import re
import time
import requests
from bs4 import BeautifulSoup

# ── Configuración ──────────────────────────────────────────────────────────────
BASE_DIR               = os.path.join(os.path.dirname(__file__), "..", "proyectos_docentes", "ing_software")
CURSO_OBJETIVO         = "2025-26"
SEVIUS_BASE            = "https://sevius4.us.es/index.php?PyP=LISTA&codcentro=3&titulacion=205&asignatura={codigo}"
PAUSA_ENTRE_PETICIONES = 0.5   # segundos entre requests


# ── Utilidades ─────────────────────────────────────────────────────────────────

def sanitizar(nombre: str) -> str:
    """Elimina caracteres prohibidos en nombres de carpeta (Windows/Linux)."""
    return re.sub(r'[\\/:*?"<>|]', '_', nombre).strip()


# ── Leer carpetas existentes ───────────────────────────────────────────────────

def leer_asignaturas_desde_carpetas() -> list[dict]:
    """
    Recorre BASE_DIR y extrae nombre + codigo de cada carpeta con formato
    'Nombre asignatura (codigo)'. Ignora subcarpetas (p.ej. 'Grupo 1').
    """
    asignaturas = []
    patron = re.compile(r'^(.+)\((\d+)\)\s*$')

    if not os.path.isdir(BASE_DIR):
        raise FileNotFoundError(f"No existe el directorio base: {BASE_DIR}")

    for entrada in sorted(os.scandir(BASE_DIR), key=lambda e: e.name):
        if not entrada.is_dir():
            continue
        m = patron.match(entrada.name)
        if m:
            asignaturas.append({
                "nombre":  m.group(1).strip(),
                "codigo":  m.group(2).strip(),
                "ruta":    entrada.path,
                "carpeta": entrada.name,
            })
        else:
            print(f"  [ignorada] '{entrada.name}' (no coincide con patrón 'Nombre (codigo)')")

    return asignaturas


# ── Web scraping ───────────────────────────────────────────────────────────────

def obtener_grupos_25_26(codigo_asignatura: str) -> list[dict]:
    """
    Accede a la página de sevius4 para la asignatura y devuelve la lista
    de grupos disponibles para CURSO_OBJETIVO.

    Cada elemento es un dict:
        { 'nombre': 'Grupo 1', 'proyecto': '2050006/2025-26/1099319/1' }

    Devuelve lista vacía si no hay datos o hay error de red.
    """
    url = SEVIUS_BASE.format(codigo=codigo_asignatura)
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"    ⚠ Error de red para {codigo_asignatura}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    grupos = []

    for th_curso in soup.find_all("th", string=lambda t: t and CURSO_OBJETIVO in t):
        tabla = th_curso.find_parent("table")
        if not tabla:
            continue

        recolectando = False
        for tr in tabla.find_all("tr"):
            ths = tr.find_all("th")
            textos = [th.get_text(strip=True) for th in ths]

            if CURSO_OBJETIVO in " ".join(textos):
                recolectando = True
                continue

            if not recolectando:
                continue

            # Nueva cabecera de otro curso detiene la recolección
            if any(re.search(r'Curso \d{4}-\d{2}', t) for t in textos):
                break

            for th in ths:
                texto = th.get_text(strip=True)
                m = re.search(r'Proyecto del grupo\s+(.+)', texto, re.IGNORECASE)
                if m:
                    etiqueta = m.group(1).strip()
                    nombre_grupo = f"Grupo {etiqueta}"
                    # Buscar el input 'proyecto' dentro de este <th>
                    inp = th.find("input", {"name": "proyecto"})
                    valor_proyecto = inp["value"] if inp else None
                    if nombre_grupo not in [g["nombre"] for g in grupos]:
                        grupos.append({"nombre": nombre_grupo, "proyecto": valor_proyecto})

    return grupos


# ── Descarga de PDF ───────────────────────────────────────────────────────────

SEVIUS_POST_URL = "https://sevius4.us.es/index.php?PyP=LISTA"


def descargar_pdf(valor_proyecto: str, ruta_destino: str) -> bool:
    """
    Descarga el PDF del proyecto docente mediante POST y lo guarda en ruta_destino.
    Devuelve True si se descargó correctamente.
    """
    try:
        resp = requests.post(
            SEVIUS_POST_URL,
            data={"proyecto": valor_proyecto},
            timeout=30,
            stream=True,
        )
        resp.raise_for_status()
        if "application/pdf" not in resp.headers.get("Content-Type", ""):
            print(f"        ⚠ Respuesta inesperada (no es PDF): {resp.headers.get('Content-Type')}")
            return False
        with open(ruta_destino, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except requests.RequestException as e:
        print(f"        ⚠ Error descargando PDF: {e}")
        return False


# ── Creación de carpetas ───────────────────────────────────────────────────────

def crear_estructura(asignaturas: list[dict]) -> None:
    total_asig  = len(asignaturas)
    carpetas_ok = 0
    sin_datos   = []

    for i, a in enumerate(asignaturas, 1):
        ruta_asig = a["ruta"]   # ya existe
        print(f"[{i}/{total_asig}] {a['carpeta']}")

        grupos = obtener_grupos_25_26(a["codigo"])

        if not grupos:
            print(f"    → Sin grupos {CURSO_OBJETIVO} en sevius.")
            sin_datos.append(a["nombre"])
        else:
            nombres = [g["nombre"] for g in grupos]
            print(f"    → {len(grupos)} grupo(s): {', '.join(nombres)}")
            for grupo in grupos:
                ruta_grupo = os.path.join(ruta_asig, sanitizar(grupo["nombre"]))
                es_nueva = not os.path.exists(ruta_grupo)
                os.makedirs(ruta_grupo, exist_ok=True)
                if es_nueva:
                    carpetas_ok += 1
                    print(f"        [creada]    {grupo['nombre']}")
                else:
                    print(f"        [ya existe] {grupo['nombre']}")

                # Descargar PDF
                ruta_pdf = os.path.join(ruta_grupo, "proyecto_docente.pdf")
                if os.path.exists(ruta_pdf):
                    print(f"        [pdf ok]    ya descargado")
                elif grupo["proyecto"]:
                    ok = descargar_pdf(grupo["proyecto"], ruta_pdf)
                    if ok:
                        print(f"        [pdf ok]    descargado ({os.path.getsize(ruta_pdf) // 1024} KB)")
                    time.sleep(PAUSA_ENTRE_PETICIONES)
                else:
                    print(f"        [pdf ⚠]    sin valor 'proyecto' en el form")

        time.sleep(PAUSA_ENTRE_PETICIONES)

    print(f"\n{'='*55}")
    print(f"Subcarpetas de grupo creadas : {carpetas_ok}")
    if sin_datos:
        print(f"Sin datos {CURSO_OBJETIVO} ({len(sin_datos)}): {', '.join(sin_datos)}")
    print(f"{'='*55}")


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Leyendo carpetas existentes en:\n  {BASE_DIR}\n")
    try:
        asignaturas = leer_asignaturas_desde_carpetas()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        raise SystemExit(1)

    if not asignaturas:
        print("No se encontraron carpetas con formato 'Nombre (codigo)'.")
        raise SystemExit(1)

    print(f"  → {len(asignaturas)} asignaturas encontradas.")
    print(f"  → Scraping de grupos {CURSO_OBJETIVO} en sevius4.us.es...\n")

    crear_estructura(asignaturas)

