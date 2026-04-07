"""
scraper_dte.py
--------------
Scraper para el departamento DTE (Tecnología Electrónica).
Web en Plone CMS, scrapeabilidad media. Email ofuscado con imagen arroba.

Fuente listado: https://www.dte.us.es/dte_users_group

Estructura HTML real:
  <div class="dtepersonal">
    <h2 class="dte-personal-name"><a href="...">Apellidos, Nombre</a></h2>
    <div class="dte-personal-categoria">Categoría</div>
    <div class="dtepersonalcab">
      <span>usuario</span><img alt="Arroba"/><span>dominio</span>
    </div>
    <div>Teléfono: +34 ...</div>
    <div class="dte-personal-ubicacion">Despacho: G1.67 (ETSII)</div>
    <div class="dte-personal-tutorias">...</div>
  </div>

Campos extraídos:
  - nombre, apellidos, categoria_academica, email, telefono, despacho,
    enlace_perfil, tutorias
"""

import json
import re
import unicodedata

import requests
from bs4 import BeautifulSoup

LISTADO_URL = "https://www.dte.us.es/dte_users_group"
TIMEOUT = 15
OUTPUT = "profesores/datos/dte.json"

DIAS_MAP = {
    "lunes": 1, "martes": 2, "miércoles": 3, "miercoles": 3,
    "jueves": 4, "viernes": 5,
}


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower().strip()


def limpiar_texto(texto):
    if not texto:
        return None
    return " ".join(texto.split()).strip() or None


def extraer_email(bloque):
    """Reconstruye el email desde spans separados por img arroba."""
    cab = bloque.find("div", class_="dtepersonalcab")
    if not cab:
        return None

    # Buscar spans hijos directos
    spans = cab.find_all("span")
    # Filtrar el span de label
    partes_email = []
    for span in spans:
        cls = span.get("class", [])
        if "dtepersonalcab" in cls:
            continue  # es el label "Correo electrónico:"
        texto = span.get_text(strip=True)
        if texto:
            partes_email.append(texto)

    if len(partes_email) >= 2:
        return f"{partes_email[0]}@{partes_email[1]}"
    return None


def extraer_telefono(bloque):
    """Extrae el teléfono del bloque."""
    for div in bloque.find_all("div"):
        texto = div.get_text()
        if "teléfono" in texto.lower() or "telefono" in texto.lower():
            # Extraer números de 9 dígitos (con posibles espacios)
            match = re.search(r"(\d[\d\s]{8,})", texto)
            if match:
                tel = re.sub(r"\s", "", match.group(1))
                # Quitar prefijo 34 si tiene 11+ dígitos
                if len(tel) >= 11 and tel.startswith("34"):
                    tel = tel[2:]
                if len(tel) >= 9:
                    return tel[:9]
    return None


def extraer_despacho(bloque):
    """Extrae el despacho del bloque."""
    ubic = bloque.find("div", class_="dte-personal-ubicacion")
    if not ubic:
        return None
    texto = ubic.get_text()
    # Buscar patrón de despacho como G1.67, F0.45, etc.
    match = re.search(r"([A-Z]\d+\.\d+)", texto)
    if match:
        return match.group(1)
    return None


def extraer_tutorias(bloque):
    """Extrae las tutorías del bloque."""
    tut_div = bloque.find("div", class_="dte-personal-tutorias")
    if not tut_div:
        return None

    texto = tut_div.get_text()
    bloques_tut = []

    for linea in texto.split("\n"):
        linea_limpia = linea.strip()
        # Buscar patrón: "Día: HH:MM a HH:MM" o "- Día de HH:MM a HH:MM"
        match = re.search(
            r"(lunes|martes|mi[eé]rcoles|jueves|viernes)[:\s]+(?:de\s+)?(\d{1,2}[:.]\d{2})\s+a\s+(\d{1,2}[:.]\d{2})",
            linea_limpia, re.IGNORECASE
        )
        if match:
            dia_str = normalizar(match.group(1))
            hora_inicio = match.group(2).replace(".", ":")
            hora_fin = match.group(3).replace(".", ":")
            bloques_tut.append({
                "dia_semana": DIAS_MAP.get(dia_str, 0),
                "hora_inicio": hora_inicio,
                "hora_fin": hora_fin,
            })

    return {"bloques": bloques_tut} if bloques_tut else None


def extraer_listado():
    """Extrae el listado de profesores del DTE."""
    resp = requests.get(LISTADO_URL, timeout=TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    profesores = []

    bloques = soup.find_all("div", class_="dtepersonal")
    print(f"Bloques dtepersonal encontrados: {len(bloques)}")

    for bloque in bloques:
        prof = {}

        # Nombre
        h2 = bloque.find("h2", class_="dte-personal-name")
        if not h2:
            continue

        link = h2.find("a")
        if link:
            nombre_completo = limpiar_texto(link.get_text())
            href = link.get("href", "")
            if href:
                prof["enlace_perfil"] = href
        else:
            nombre_completo = limpiar_texto(h2.get_text())

        if not nombre_completo:
            continue

        # Formato "Apellidos, Nombre"
        if "," in nombre_completo:
            partes = nombre_completo.split(",", 1)
            prof["apellidos"] = limpiar_texto(partes[0])
            prof["nombre"] = limpiar_texto(partes[1])
        else:
            prof["nombre"] = nombre_completo
            prof["apellidos"] = ""

        # Categoría
        cat_div = bloque.find("div", class_="dte-personal-categoria")
        if cat_div:
            prof["categoria_academica"] = limpiar_texto(cat_div.get_text())

        # Email (ofuscado)
        prof["email"] = extraer_email(bloque)

        # Teléfono
        prof["telefono"] = extraer_telefono(bloque)

        # Despacho
        prof["despacho"] = extraer_despacho(bloque)

        # Tutorías
        tutorias = extraer_tutorias(bloque)
        if tutorias:
            prof["tutorias"] = tutorias

        prof["nombre_normalizado"] = normalizar(
            f"{prof.get('apellidos', '')} {prof.get('nombre', '')}"
        )
        prof["departamento"] = "DTE"
        profesores.append(prof)

    return profesores


def main():
    print("=== Scraping DTE ===")
    print(f"Fuente: {LISTADO_URL}")

    profesores = extraer_listado()
    print(f"Profesores extraídos: {len(profesores)}")

    for prof in profesores:
        nombre = f"{prof.get('apellidos', '')}, {prof.get('nombre', '')}"
        email = prof.get("email", "sin email")
        print(f"  - {nombre} ({email})")

    # Guardar
    import os
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(profesores, f, ensure_ascii=False, indent=2)

    print(f"\nGuardados {len(profesores)} profesores en {OUTPUT}")
    return profesores


if __name__ == "__main__":
    main()
