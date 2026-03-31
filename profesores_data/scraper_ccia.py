"""
scraper_ccia.py
---------------
Scraper para el departamento CCIA (Ciencias de la Computación e IA).
HTML estático con alta scrapeabilidad.

Fuente directorio: https://www.cs.us.es/departamento/directorio
Perfiles:          https://www.cs.us.es/perfiles/{slug}
Tutorías:          https://www.cs.us.es/docencia/horarios-de-tutorias

Campos extraídos:
  - nombre, apellidos, categoria_academica, email, telefono, despacho,
    enlace_perfil, orcid, web_personal
"""

import json
import re
import time
import unicodedata

import requests
from bs4 import BeautifulSoup

DIRECTORIO_URL = "https://www.cs.us.es/departamento/directorio"
TUTORIAS_URL = "https://www.cs.us.es/docencia/horarios-de-tutorias"
PERFILES_BASE = "https://www.cs.us.es"
PAUSA = 0.5
TIMEOUT = 15
OUTPUT = "profesores/datos/ccia.json"


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower().strip()


def limpiar_texto(texto):
    if not texto:
        return None
    return " ".join(texto.split()).strip() or None


def extraer_directorio():
    """Extrae el listado del directorio de CCIA.

    Estructura HTML real:
      <div class="column">
        <div>
          Nombre Completo
          <a class="tooltip" href="/perfiles/slug">...</a>
        </div>
        <div class="text-small mx-2">Categoría Académica</div>
      </div>
    """
    resp = requests.get(DIRECTORIO_URL, timeout=TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    profesores = []

    # Cada profesor está en un div.column que contiene un enlace a /perfiles/
    columns = soup.find_all("div", class_="column")

    for col in columns:
        link = col.find("a", href=re.compile(r"/perfiles/"))
        if not link:
            continue

        prof = {}

        # El nombre está como texto directo en el div padre del enlace
        nombre_div = link.parent
        # Extraer solo el texto directo (no el del <a>)
        nombre_completo = ""
        for child in nombre_div.children:
            if isinstance(child, str):
                texto = child.strip()
                if texto:
                    nombre_completo = texto
                    break

        nombre_completo = limpiar_texto(nombre_completo)
        if not nombre_completo:
            continue

        # No se puede separar nombre/apellidos fiablemente sin coma
        # (ej: "José Luis Ruiz Reina" → ¿nombre compuesto o no?)
        # Guardamos nombre completo en "nombre" y apellidos vacío
        prof["nombre"] = nombre_completo
        prof["apellidos"] = ""

        prof["enlace_perfil"] = PERFILES_BASE + link["href"]

        # La categoría está en el div.text-small hermano
        cat_div = col.find("div", class_=re.compile(r"text-small"))
        if cat_div:
            prof["categoria_academica"] = limpiar_texto(cat_div.get_text())

        prof["nombre_normalizado"] = normalizar(nombre_completo)
        prof["departamento"] = "CCIA"
        profesores.append(prof)

    return profesores


def enriquecer_con_perfil(prof):
    """Visita el perfil individual para extraer campos de contacto."""
    url = prof.get("enlace_perfil")
    if not url:
        return prof

    try:
        resp = requests.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  Error accediendo perfil {url}: {e}")
        return prof

    soup = BeautifulSoup(resp.text, "html.parser")
    texto_completo = soup.get_text()

    # Categoría académica
    h5 = soup.find("h5")
    if h5:
        cat = limpiar_texto(h5.get_text())
        if cat and re.search(
            r"(Catedr|Titular|Contratado|Asociado|Ayudante|Profesor|Sustituto)",
            cat, re.IGNORECASE
        ):
            prof["categoria_academica"] = cat

    # Email
    email_link = soup.find("a", href=re.compile(r"mailto:"))
    if email_link:
        prof["email"] = email_link["href"].replace("mailto:", "").strip()

    # Teléfono
    tel_link = soup.find("a", href=re.compile(r"tel:"))
    if tel_link:
        prof["telefono"] = re.sub(r"\D", "", tel_link["href"].replace("tel:", ""))
    else:
        tel_match = re.search(r"(?:954|955)\s?\d{6}", texto_completo)
        if tel_match:
            prof["telefono"] = re.sub(r"\s", "", tel_match.group())

    # Despacho
    desp_match = re.search(r"[Dd]espacho\s*:?\s*([A-Z]\d+\.\d+)", texto_completo)
    if desp_match:
        prof["despacho"] = desp_match.group(1)
    else:
        desp_match = re.search(r"([EFGHABI]\d+\.\d+)", texto_completo)
        if desp_match:
            prof["despacho"] = desp_match.group(1)

    # ORCID
    orcid_link = soup.find("a", href=re.compile(r"orcid\.org"))
    if orcid_link:
        orcid_match = re.search(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", orcid_link["href"])
        if orcid_match:
            prof["orcid"] = orcid_match.group()

    # Web personal
    for a in soup.find_all("a", href=True):
        href = a["href"]
        txt = limpiar_texto(a.get_text()) or ""
        if "personal" in txt.lower() or "web" in txt.lower():
            if "cs.us.es" not in href:
                prof["web_personal"] = href
                break
        if "personal.us.es" in href:
            prof.setdefault("web_personal", href)

    return prof


def extraer_tutorias():
    """Extrae las tutorías de la página dedicada de CCIA."""
    resp = requests.get(TUTORIAS_URL, timeout=TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    tutorias = {}  # nombre_normalizado -> lista de bloques de tutoría

    # Cada profesor tiene un h4 con su nombre, seguido de texto con horarios
    headers = soup.find_all("h4")

    for h4 in headers:
        nombre = limpiar_texto(h4.get_text())
        if not nombre:
            continue

        nombre_norm = normalizar(nombre)
        bloques = []

        # Recorrer siblings hasta el siguiente h4
        sibling = h4.find_next_sibling()
        texto_acumulado = ""
        while sibling and sibling.name != "h4":
            texto_acumulado += sibling.get_text() + "\n"
            sibling = sibling.find_next_sibling()

        # Parsear líneas de tutoría: "Lunes de 10:00 a 12:00"
        dias_map = {
            "lunes": 1, "martes": 2, "miércoles": 3, "miercoles": 3,
            "jueves": 4, "viernes": 5
        }

        for linea in texto_acumulado.split("\n"):
            linea = linea.strip()
            match = re.search(
                r"(lunes|martes|mi[eé]rcoles|jueves|viernes)\s+de\s+(\d{1,2}[:.]\d{2})\s+a\s+(\d{1,2}[:.]\d{2})",
                linea, re.IGNORECASE
            )
            if match:
                dia_str = normalizar(match.group(1))
                hora_inicio = match.group(2).replace(".", ":")
                hora_fin = match.group(3).replace(".", ":")
                bloques.append({
                    "dia_semana": dias_map.get(dia_str, 0),
                    "hora_inicio": hora_inicio,
                    "hora_fin": hora_fin,
                })

        # Extraer despacho del texto
        desp_match = re.search(r"[Dd]espacho\s*:?\s*([A-Z]\d+\.\d+)", texto_acumulado)
        if not desp_match:
            desp_match = re.search(r"([EFGHABI]\d+\.\d+)", texto_acumulado)

        ubicacion = desp_match.group(1) if desp_match else None

        if bloques:
            tutorias[nombre_norm] = {
                "bloques": bloques,
                "ubicacion": ubicacion,
            }

    return tutorias


def main():
    print("=== Scraping CCIA ===")

    # 1. Directorio
    print(f"Fuente directorio: {DIRECTORIO_URL}")
    profesores = extraer_directorio()
    print(f"Profesores encontrados en directorio: {len(profesores)}")

    # 2. Enriquecer con perfiles individuales
    for i, prof in enumerate(profesores):
        nombre = prof.get("nombre", "?")
        print(f"  [{i+1}/{len(profesores)}] {nombre}")
        enriquecer_con_perfil(prof)
        time.sleep(PAUSA)

    # 3. Tutorías
    print(f"\nFuente tutorías: {TUTORIAS_URL}")
    tutorias = extraer_tutorias()
    print(f"Profesores con tutorías: {len(tutorias)}")

    # Asociar tutorías a profesores
    for prof in profesores:
        nombre_norm = prof.get("nombre_normalizado", "")
        if nombre_norm in tutorias:
            prof["tutorias"] = tutorias[nombre_norm]

    # Guardar
    import os
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(profesores, f, ensure_ascii=False, indent=2)

    print(f"\nGuardados {len(profesores)} profesores en {OUTPUT}")
    return profesores


if __name__ == "__main__":
    main()
