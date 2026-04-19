"""
Scraper para la web de la Universidad de Sevilla (us.es).

Extrae la lista de grados disponibles y el plan de estudios de cada uno
(curso, creditos, tipologia) desde:
https://www.us.es/estudiar/que-estudiar/oferta-de-grados
"""

import re
import unicodedata
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.us.es"
GRADOS_URL = BASE_URL + "/estudiar/que-estudiar/oferta-de-grados"
TIMEOUT = 20


def _normalizar(texto: str) -> str:
    """Quita acentos y pasa a minusculas para comparaciones fuzzy."""
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def _get_soup(url: str) -> BeautifulSoup:
    resp = requests.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def obtener_grados() -> list[dict]:
    """
    Devuelve todos los grados listados en us.es.
    [{"nombre": "Grado en Estadística", "url": "https://www.us.es/..."}, ...]
    """
    soup = _get_soup(GRADOS_URL)
    grados = []
    for a in soup.select("a[href*='/oferta-de-grados/']"):
        href = a.get("href", "")
        nombre = a.get_text(strip=True)
        if not nombre or href == "/estudiar/que-estudiar/oferta-de-grados":
            continue
        url = href if href.startswith("http") else BASE_URL + href
        grados.append({"nombre": nombre, "url": url})
    return grados


def buscar_grado(nombre_titulacion: str) -> str | None:
    """
    Busca en us.es el grado que mejor coincida con el nombre dado.
    Devuelve la URL o None si no hay coincidencia.
    """
    grados = obtener_grados()
    nombre_norm = _normalizar(nombre_titulacion)

    # 1. Coincidencia exacta normalizada
    for g in grados:
        if _normalizar(g["nombre"]) == nombre_norm:
            return g["url"]

    # 2. Uno contiene al otro
    for g in grados:
        g_norm = _normalizar(g["nombre"])
        if nombre_norm in g_norm or g_norm in nombre_norm:
            return g["url"]

    # 3. Coincidencia por palabras clave (ignorando "grado", "en", "de", etc.)
    stopwords = {"grado", "en", "de", "del", "la", "las", "los", "y", "e", "por"}
    palabras_busqueda = set(_normalizar(nombre_titulacion).split()) - stopwords
    mejor, mejor_score = None, 0
    for g in grados:
        palabras_grado = set(_normalizar(g["nombre"]).split()) - stopwords
        comunes = palabras_busqueda & palabras_grado
        score = len(comunes) / max(len(palabras_busqueda), 1)
        if score > mejor_score:
            mejor_score = score
            mejor = g["url"]

    return mejor if mejor_score >= 0.5 else None


def obtener_plan_estudios(url_grado: str) -> list[dict]:
    """
    Extrae el plan de estudios de un grado desde su pagina en us.es.
    Devuelve:
    [{"codigo": "1960001", "nombre": "Algebra Lineal", "curso": 1,
      "creditos": 12.0, "tipologia": "Formación Básica"}, ...]
    """
    soup = _get_soup(url_grado)

    # Buscar tablas con columnas de asignaturas
    asignaturas = []
    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        # Identificar indices de columnas relevantes
        idx_codigo = idx_nombre = idx_curso = idx_creditos = idx_tipo = None
        for i, h in enumerate(headers):
            if "codigo" in h or "código" in h or "asig" in h.replace("asignatura", ""):
                if "asig" in h and idx_codigo is not None:
                    continue
                if idx_codigo is None:
                    idx_codigo = i
            if "asignatura" in h or h == "nombre":
                idx_nombre = i
            if "curso" in h:
                idx_curso = i
            if "credito" in h or "crédito" in h or "ects" in h:
                idx_creditos = i
            if "tipo" in h:
                idx_tipo = i

        if idx_nombre is None and idx_codigo is None:
            continue

        for tr in table.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue

            def cell(idx):
                if idx is not None and idx < len(tds):
                    return tds[idx].get_text(strip=True)
                return None

            codigo = cell(idx_codigo) or ""
            nombre = cell(idx_nombre) or ""
            curso_str = cell(idx_curso) or "0"
            creditos_str = cell(idx_creditos) or "0"
            tipologia = cell(idx_tipo) or ""

            if not nombre and not codigo:
                continue

            # Parsear curso (puede ser "1", "1º", etc.)
            curso_match = re.search(r"(\d+)", curso_str)
            curso = int(curso_match.group(1)) if curso_match else 0

            # Parsear creditos
            creditos_str = creditos_str.replace(",", ".")
            creditos_match = re.search(r"([\d.]+)", creditos_str)
            creditos = float(creditos_match.group(1)) if creditos_match else 0.0

            asignaturas.append({
                "codigo": codigo,
                "nombre": nombre,
                "curso": curso,
                "creditos": creditos,
                "tipologia": tipologia,
            })

    return asignaturas
