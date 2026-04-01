"""
scraper_lsi.py
--------------
Scraper para el departamento LSI (Lenguajes y Sistemas Informáticos).
Web WordPress + Elementor.

Fuente listado: https://departamento.us.es/lsi/profesorado/

Estructura HTML: cada profesor es un contenedor Elementor (8 niveles
arriba del botón "Más información") con:
  - .elementor-heading-title  → "Apellidos, Nombre"
  - .elementor-widget-text-editor → Categoría académica
  - .elementor-icon-list-text (×3) → despacho, email, teléfono
  - botón <a href="/profesor/{slug}/">

Campos extraídos:
  - nombre, apellidos, categoria_academica, email, telefono, despacho,
    enlace_perfil
"""

import json
import os
import re
import unicodedata

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://departamento.us.es/lsi/profesorado/"
TIMEOUT = 15
OUTPUT = "profesores/datos/lsi.json"


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower().strip()


def limpiar_texto(texto):
    if not texto:
        return None
    return " ".join(texto.split()).strip() or None


def extraer_listado():
    """Extrae el listado de profesores del LSI."""
    resp = requests.get(BASE_URL, timeout=TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    profesores = []

    # Cada botón "Más información" enlaza a /profesor/{slug}/
    links = soup.find_all("a", href=lambda h: h and "/profesor/" in h)

    for link in links:
        prof = {}

        # Subir 8 niveles hasta el contenedor de la tarjeta completa
        card = link
        for _ in range(8):
            card = card.parent

        # Nombre (formato "Apellidos, Nombre")
        heading = card.select_one(".elementor-heading-title")
        if not heading:
            continue

        nombre_completo = limpiar_texto(heading.get_text())
        if not nombre_completo:
            continue

        if "," in nombre_completo:
            partes = nombre_completo.split(",", 1)
            prof["apellidos"] = limpiar_texto(partes[0])
            prof["nombre"] = limpiar_texto(partes[1])
        else:
            prof["nombre"] = nombre_completo
            prof["apellidos"] = ""

        # Enlace al perfil
        prof["enlace_perfil"] = link["href"]

        # Categoría académica
        text_ed = card.select_one(".elementor-widget-text-editor")
        if text_ed:
            prof["categoria_academica"] = limpiar_texto(text_ed.get_text())

        # Despacho, email, teléfono (3 icon-list-items en orden)
        icons = card.select(".elementor-icon-list-text")
        for icon in icons:
            texto = limpiar_texto(icon.get_text())
            if not texto:
                continue
            if "@" in texto:
                prof["email"] = texto
            elif re.match(r"[A-Z]\d+\.\d+", texto):
                prof["despacho"] = texto
            elif re.search(r"\d{9}", texto):
                prof["telefono"] = re.search(r"\d{9}", texto).group()

        prof["nombre_normalizado"] = normalizar(
            f"{prof.get('apellidos', '')} {prof.get('nombre', '')}"
        )
        prof["departamento"] = "LSI"
        profesores.append(prof)

    return profesores


def main():
    print("=== Scraping LSI ===")
    print(f"Fuente: {BASE_URL}")

    profesores = extraer_listado()
    print(f"Profesores encontrados: {len(profesores)}")

    for prof in profesores:
        nombre = f"{prof.get('apellidos', '')}, {prof.get('nombre', '')}"
        email = prof.get("email", "sin email")
        print(f"  - {nombre} ({email})")

    # Guardar
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(profesores, f, ensure_ascii=False, indent=2)

    print(f"\nGuardados {len(profesores)} profesores en {OUTPUT}")
    return profesores


if __name__ == "__main__":
    main()
