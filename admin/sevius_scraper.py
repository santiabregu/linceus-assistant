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
