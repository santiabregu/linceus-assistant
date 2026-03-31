"""
scraper_ma1.py
--------------
Scraper para el departamento MA1 (Matemática Aplicada I).
Web propia caída; datos de SISIUS + Directorio US.

Fuentes:
  - SISIUS listado:  https://investigacion.us.es/sisius/sis_dep.php?id_dpto=92
  - SISIUS perfil:   https://investigacion.us.es/sisius/sis_showpub.php?idpers={id}
  - Directorio US:   https://www.us.es/trabaja-en-la-us/directorio/{slug}

Campos extraídos:
  - nombre, apellidos, categoria_academica, email, telefono,
    web_personal, orcid, enlace_perfil
"""

import json
import re
import time
import unicodedata

import requests
from bs4 import BeautifulSoup

SISIUS_LISTADO = "https://investigacion.us.es/sisius/sis_dep.php?id_dpto=92"
SISIUS_PERFIL_BASE = "https://investigacion.us.es/sisius/sis_showpub.php?idpers="
DIRECTORIO_US_BASE = "https://www.us.es/trabaja-en-la-us/directorio/"
PAUSA = 0.5
TIMEOUT = 15
OUTPUT = "profesores/datos/ma1.json"


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower().strip()


def limpiar_texto(texto):
    if not texto:
        return None
    return " ".join(texto.split()).strip() or None


def generar_slug_directorio(nombre_completo):
    """Genera el slug para el directorio US: nombre-apellido1-apellido2."""
    slug = normalizar(nombre_completo)
    slug = re.sub(r"[^a-z\s]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    return slug


def extraer_listado_sisius():
    """Extrae el listado de profesores de MA1 desde SISIUS."""
    resp = requests.get(SISIUS_LISTADO, timeout=TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    profesores = []

    # Los profesores son enlaces con href que contiene sis_showpub.php
    links = soup.find_all("a", href=re.compile(r"sis_showpub\.php\?idpers="))

    for link in links:
        prof = {}
        nombre_completo = limpiar_texto(link.get_text())
        if not nombre_completo:
            continue

        # Extraer ID de SISIUS para enlace y enriquecimiento posterior
        id_match = re.search(r"idpers=(\d+)", link["href"])
        sisius_id = id_match.group(1) if id_match else None
        if sisius_id:
            prof["_sisius_id"] = sisius_id  # interno, no va a BD
            prof["enlace_perfil"] = SISIUS_PERFIL_BASE + sisius_id

        # No se puede separar nombre/apellidos fiablemente sin coma
        prof["nombre"] = nombre_completo
        prof["apellidos"] = ""

        # La categoría puede estar en el texto adyacente (agrupados por categoría)
        # Buscamos el encabezado de categoría más cercano anterior
        parent = link.parent
        if parent:
            prev_header = parent.find_previous(["h2", "h3", "h4", "strong", "b"])
            if prev_header:
                cat = limpiar_texto(prev_header.get_text())
                if cat and re.search(
                    r"(Catedr|Titular|Contratado|Asociado|Ayudante|Profesor|Sustituto|Investigador)",
                    cat, re.IGNORECASE
                ):
                    prof["categoria_academica"] = cat

        prof["nombre_normalizado"] = normalizar(nombre_completo)
        prof["departamento"] = "MA1"
        profesores.append(prof)

    return profesores


def enriquecer_con_sisius(prof):
    """Visita el perfil SISIUS para extraer ORCID, web, teléfono."""
    sisius_id = prof.get("_sisius_id")
    if not sisius_id:
        return prof

    url = SISIUS_PERFIL_BASE + sisius_id
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  Error SISIUS {url}: {e}")
        return prof

    soup = BeautifulSoup(resp.text, "html.parser")
    texto = soup.get_text()

    # Teléfono
    tel_match = re.search(r"(\d{2}\.\d{3}\.\d{2}\.\d{2})", texto)
    if tel_match:
        prof["telefono"] = tel_match.group().replace(".", "")
    else:
        tel_match2 = re.search(r"(?:954|955)\d{6}", texto)
        if tel_match2:
            prof["telefono"] = tel_match2.group()

    # ORCID
    orcid_link = soup.find("a", href=re.compile(r"orcid\.org"))
    if orcid_link:
        orcid_match = re.search(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", orcid_link["href"])
        if orcid_match:
            prof["orcid"] = orcid_match.group()

    # Web personal
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "personal.us.es" in href or ("http" in href and "us.es/sisius" not in href
                                         and "orcid.org" not in href
                                         and "scopus.com" not in href
                                         and "webofscience" not in href
                                         and "dialnet" not in href):
            txt = limpiar_texto(a.get_text()) or ""
            if "personal" in txt.lower() or "web" in txt.lower() or "personal.us.es" in href:
                prof["web_personal"] = href
                break

    # Categoría (si no se obtuvo del listado)
    if not prof.get("categoria_academica"):
        cat_match = re.search(
            r"(Catedr[áa]tic[oa]\s+de\s+Universidad|Profesor[a]?\s+Titular[a]?\s+de\s+Universidad|"
            r"Contratado\s+Doctor|Profesor[a]?\s+Ayudante|Asociad[oa])",
            texto, re.IGNORECASE
        )
        if cat_match:
            prof["categoria_academica"] = cat_match.group()

    return prof


def enriquecer_con_directorio_us(prof):
    """Visita el directorio US para obtener email y teléfono."""
    nombre = prof.get("nombre", "")
    if not nombre:
        return prof

    slug = generar_slug_directorio(nombre)
    url = DIRECTORIO_US_BASE + slug

    try:
        resp = requests.get(url, timeout=TIMEOUT)
        if resp.status_code == 404:
            return prof
        resp.raise_for_status()
    except requests.RequestException:
        return prof

    soup = BeautifulSoup(resp.text, "html.parser")

    # Email
    email_link = soup.find("a", href=re.compile(r"mailto:"))
    if email_link:
        prof["email"] = email_link["href"].replace("mailto:", "").strip()

    # Teléfono (si no se obtuvo de SISIUS)
    if not prof.get("telefono"):
        tel_link = soup.find("a", href=re.compile(r"tel:"))
        if tel_link:
            prof["telefono"] = re.sub(r"\D", "", tel_link["href"].replace("tel:", ""))

    # Categoría (si no se obtuvo de SISIUS)
    if not prof.get("categoria_academica"):
        texto = soup.get_text()
        cat_match = re.search(
            r"(Catedr[áa]tic[oa]\s+de\s+Universidad|Profesor[a]?\s+Titular\s+de\s+Universidad|"
            r"Contratado\s+Doctor|Ayudante|Asociad[oa])",
            texto, re.IGNORECASE
        )
        if cat_match:
            prof["categoria_academica"] = cat_match.group()

    return prof


def main():
    print("=== Scraping MA1 ===")

    # 1. Listado SISIUS
    print(f"Fuente SISIUS: {SISIUS_LISTADO}")
    profesores = extraer_listado_sisius()
    print(f"Profesores encontrados en SISIUS: {len(profesores)}")

    # 2. Enriquecer con perfil SISIUS (ORCID, web, teléfono)
    print("\nEnriqueciendo con perfiles SISIUS...")
    for i, prof in enumerate(profesores):
        nombre = prof.get("nombre", "?")
        print(f"  [{i+1}/{len(profesores)}] {nombre}")
        enriquecer_con_sisius(prof)
        time.sleep(PAUSA)

    # 3. Enriquecer con directorio US (email, teléfono)
    print("\nEnriqueciendo con directorio US...")
    for i, prof in enumerate(profesores):
        if not prof.get("email"):
            nombre = prof.get("nombre", "?")
            print(f"  [{i+1}/{len(profesores)}] {nombre}")
            enriquecer_con_directorio_us(prof)
            time.sleep(PAUSA)

    # Guardar
    import os
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(profesores, f, ensure_ascii=False, indent=2)

    print(f"\nGuardados {len(profesores)} profesores en {OUTPUT}")
    return profesores


if __name__ == "__main__":
    main()
