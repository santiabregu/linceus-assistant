"""
Scraper para Sevius (Secretaria Virtual de la Universidad de Sevilla).

Extrae centros, titulaciones y asignaturas del sistema de programas
y proyectos docentes: https://sevius4.us.es/index.php?PyP=LISTA

Cada funcion devuelve listas de dicts con codigo/nombre listos para
insertar en la BD.
"""

import re
import requests
from bs4 import BeautifulSoup

SEVIUS_URL = "https://sevius4.us.es/index.php?PyP=LISTA"
SEVIUS_ASIG_URL = "https://sevius4.us.es/index.php?PyP=LISTA&codcentro={codcentro}&titulacion={titulacion}&asignatura={asignatura}"
TIMEOUT = 15


def _get_soup(params: dict | None = None) -> BeautifulSoup:
    """Hace GET a Sevius y devuelve un objeto BeautifulSoup."""
    resp = requests.get(SEVIUS_URL, params=params, timeout=TIMEOUT, verify=False)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def obtener_centros() -> list[dict]:
    """
    Devuelve todos los centros disponibles en Sevius.
    [{"codigo": "3", "nombre": "E.T.S. Ingenieria Informatica"}, ...]
    """
    soup = _get_soup()
    select = soup.find("select", {"name": "codcentro"})
    if not select:
        return []

    centros = []
    for opt in select.find_all("option"):
        val = opt.get("value", "")
        if val and val != "-1":
            centros.append({"codigo_sevius": val, "nombre": opt.get_text(strip=True)})
    return centros


def obtener_titulaciones(codcentro: str) -> list[dict]:
    """
    Devuelve las titulaciones de un centro.
    [{"codigo": "205", "nombre": "Grado en Ingenieria Informatica-Ingenieria del Software"}, ...]
    """
    soup = _get_soup({"codcentro": codcentro})
    select = soup.find("select", {"name": "titulacion"})
    if not select:
        return []

    titulaciones = []
    for opt in select.find_all("option"):
        val = opt.get("value", "")
        if val and val != "":
            texto = opt.get_text(strip=True)
            # Quitar el codigo entre parentesis del final: "Nombre (205)" -> "Nombre"
            nombre = re.sub(r"\s*\(\w+\)\s*$", "", texto)
            titulaciones.append({"codigo": val, "nombre": nombre})
    return titulaciones


def obtener_asignaturas(codcentro: str, titulacion: str) -> list[dict]:
    """
    Devuelve las asignaturas de una titulacion.
    [{"codigo": "2050001", "nombre": "Fundamentos de Programacion"}, ...]
    """
    soup = _get_soup({"codcentro": codcentro, "titulacion": titulacion})
    select = soup.find("select", {"name": "asignatura"})
    if not select:
        return []

    asignaturas = []
    vistos = set()
    for opt in select.find_all("option"):
        val = opt.get("value", "")
        if val and val != "-1" and val not in vistos:
            vistos.add(val)
            texto = opt.get_text(strip=True)
            nombre = re.sub(r"\s*\(\d+\)\s*$", "", texto)
            asignaturas.append({"codigo": val, "nombre": nombre})
    return asignaturas


def obtener_grupos_asignatura(
    codcentro: str,
    titulacion: str,
    codigo_asignatura: str,
    curso: str = "2025-26",
) -> list[dict]:
    """
    Obtiene los grupos y el valor 'proyecto' (para descargar el PDF) de una
    asignatura para un curso academico.

    Returns:
        [{"nombre": "Grupo 1", "proyecto": "2050006/2025-26/1099319/1"}, ...]
    """
    url = SEVIUS_ASIG_URL.format(
        codcentro=codcentro, titulacion=titulacion, asignatura=codigo_asignatura
    )
    resp = requests.get(url, timeout=TIMEOUT, verify=False)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    grupos: list[dict] = []
    for th_curso in soup.find_all("th", string=lambda t: t and curso in t):
        tabla = th_curso.find_parent("table")
        if not tabla:
            continue
        recolectando = False
        for tr in tabla.find_all("tr"):
            ths = tr.find_all("th")
            textos = [th.get_text(strip=True) for th in ths]
            if curso in " ".join(textos):
                recolectando = True
                continue
            if not recolectando:
                continue
            if any(re.search(r"Curso \d{4}-\d{2}", t) for t in textos):
                break
            for th in ths:
                texto = th.get_text(strip=True)
                m = re.search(r"Proyecto del grupo\s+(.+)", texto, re.IGNORECASE)
                if m:
                    etiqueta = m.group(1).strip()
                    nombre_grupo = f"Grupo {etiqueta}"
                    inp = th.find("input", {"name": "proyecto"})
                    valor = inp["value"] if inp else None
                    if nombre_grupo not in [g["nombre"] for g in grupos]:
                        grupos.append({"nombre": nombre_grupo, "proyecto": valor})
    return grupos


def descargar_proyecto_pdf(valor_proyecto: str, ruta_destino) -> bool:
    """
    Descarga el PDF del proyecto docente a ruta_destino via POST. True si ok.
    """
    try:
        resp = requests.post(
            SEVIUS_URL,
            data={"proyecto": valor_proyecto},
            timeout=30,
            stream=True,
            verify=False,
        )
        resp.raise_for_status()
        if "application/pdf" not in resp.headers.get("Content-Type", ""):
            return False
        with open(ruta_destino, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except requests.RequestException:
        return False
