"""
Scraper del directorio de Personal Docente e Investigador (PDI) de la US.
Fuentes:
  - https://www.us.es/centros/<centro-slug>        -> lista de departamentos del centro
  - https://www.us.es/centros/departamentos/<depto-slug>  -> info del depto
  - https://www.us.es/trabaja-en-la-us/directorio/personal-docente-e-investigador
      ?title=<nombre>&title_1=<departamento>&title_2=<centro>&page=N
    Busqueda del directorio PDI con filtros.
  - https://www.us.es/trabaja-en-la-us/directorio/<slug>   -> perfil de un profesor
"""

import re
import time
import requests
from bs4 import BeautifulSoup

BASE = "https://www.us.es"
DIRECTORIO_URL = BASE + "/trabaja-en-la-us/directorio/personal-docente-e-investigador"
TIMEOUT = 20
PAUSA = 0.3


def _get_soup(url: str, params: dict | None = None) -> BeautifulSoup:
    resp = requests.get(url, params=params, timeout=TIMEOUT, verify=False)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def _abs(href: str) -> str:
    if not href:
        return href
    return href if href.startswith("http") else BASE + href


def obtener_departamentos_de_centro(centro_slug: str) -> list[dict]:
    """
    Scrapea /centros/<centro-slug> y devuelve la lista de departamentos
    ubicados en ese centro.
    Returns: [{"nombre": "CIENCIAS...", "slug": "ciencias-de-la-computacion..."}, ...]
    """
    soup = _get_soup(f"{BASE}/centros/{centro_slug}")
    deptos: list[dict] = []
    vistos: set[str] = set()
    for a in soup.find_all("a", href=re.compile(r"/centros/departamentos/[^/\"#?]+/?$")):
        href = a.get("href", "")
        slug = href.rstrip("/").rsplit("/", 1)[-1]
        nombre = " ".join(a.get_text(strip=True).split())
        if not nombre or slug in vistos:
            continue
        vistos.add(slug)
        deptos.append({"nombre": nombre, "slug": slug})
    return deptos


def buscar_profesores(
    centro_nombre: str | None = None,
    departamento_nombre: str | None = None,
    nombre: str | None = None,
    max_paginas: int = 50,
) -> list[dict]:
    """
    Itera la busqueda del directorio PDI aplicando filtros y devuelve
    los profesores encontrados con el enlace a su perfil.

    Returns: [{"nombre": "...", "slug": "...", "url": "..."}, ...]
    """
    resultados: list[dict] = []
    vistos: set[str] = set()

    for page in range(max_paginas):
        params = {
            "title": nombre or "",
            "title_1": departamento_nombre or "",
            "title_2": centro_nombre or "",
            "page": page,
        }
        soup = _get_soup(DIRECTORIO_URL, params=params)

        # Cada profe es un <a href="/trabaja-en-la-us/directorio/<slug>">
        nuevos = 0
        for a in soup.find_all("a", href=re.compile(r"^/trabaja-en-la-us/directorio/[^/\"#?]+$")):
            href = a.get("href", "")
            # Ignorar el propio enlace al listado
            if href.endswith("/personal-docente-e-investigador"):
                continue
            slug = href.rsplit("/", 1)[-1]
            if slug in vistos:
                continue
            vistos.add(slug)
            texto = " ".join(a.get_text(strip=True).split())
            if not texto:
                continue
            resultados.append({
                "nombre": texto,
                "slug": slug,
                "url": _abs(href),
            })
            nuevos += 1

        # Si no hay enlace a siguiente pagina, terminamos.
        tiene_siguiente = bool(
            soup.find("a", string=re.compile(r"Siguiente", re.IGNORECASE)) or
            soup.find("a", href=re.compile(rf"[?&]page={page + 1}\b"))
        )
        if nuevos == 0 or not tiene_siguiente:
            break
        time.sleep(PAUSA)

    return resultados


def _split_nombre_apellidos(nombre_completo: str) -> tuple[str, str]:
    """
    us.es muestra el nombre como "NOMBRE APELLIDO1 APELLIDO2" (todo mayusculas).
    Sin coma no se puede separar fiablemente. Heuristica simple: la primera
    palabra es el nombre, el resto apellidos. Si hay 4+ palabras, 2 primeras
    suelen ser nombre compuesto.
    """
    if not nombre_completo:
        return "", ""
    palabras = nombre_completo.strip().split()
    if len(palabras) <= 1:
        return palabras[0] if palabras else "", ""
    if len(palabras) == 2:
        return palabras[0], palabras[1]
    if len(palabras) == 3:
        return palabras[0], " ".join(palabras[1:])
    # 4+ palabras: 2 primeras = nombre compuesto
    return " ".join(palabras[:2]), " ".join(palabras[2:])


def obtener_perfil_profesor(slug: str) -> dict:
    """
    Scrapea /trabaja-en-la-us/directorio/<slug> y devuelve los campos visibles.
    Cualquier campo ausente queda como None (salvo centros/listas, que van vacias).
    """
    url = f"{BASE}/trabaja-en-la-us/directorio/{slug}"
    soup = _get_soup(url)

    perfil: dict = {
        "slug": slug,
        "enlace_perfil": url,
        "nombre_completo": None,
        "nombre": None,
        "apellidos": None,
        "categoria": None,
        "email": None,
        "departamento_nombre": None,
        "departamento_slug": None,
        "area": None,
        "centros": [],
        "grupo_investigacion": None,
        "prisma_url": None,
    }

    # Nombre: primer h2 no vacio
    for h in soup.find_all("h2"):
        txt = " ".join(h.get_text(strip=True).split())
        if txt:
            perfil["nombre_completo"] = txt
            perfil["nombre"], perfil["apellidos"] = _split_nombre_apellidos(txt)
            break

    # Departamento: link a /centros/departamentos/<slug>
    d_link = soup.find("a", href=re.compile(r"/centros/departamentos/[^/\"#?]+/?$"))
    if d_link:
        perfil["departamento_nombre"] = " ".join(d_link.get_text(strip=True).split())
        perfil["departamento_slug"] = d_link["href"].rstrip("/").rsplit("/", 1)[-1]

    # Centros: TODOS los links a /centros/<slug>  (excluyendo /centros/departamentos/...)
    centros_vistos: set[str] = set()
    for a in soup.find_all("a", href=re.compile(r"^/centros/[^/\"#?]+/?$")):
        href = a.get("href", "")
        if "/departamentos/" in href:
            continue
        slug_c = href.rstrip("/").rsplit("/", 1)[-1]
        if slug_c in centros_vistos:
            continue
        centros_vistos.add(slug_c)
        perfil["centros"].append({
            "nombre": " ".join(a.get_text(strip=True).split()),
            "slug": slug_c,
        })

    # Email
    mail_link = soup.find("a", href=re.compile(r"^mailto:"))
    if mail_link:
        perfil["email"] = mail_link["href"].replace("mailto:", "").strip() or None

    # PRISMA
    prisma = soup.find("a", href=re.compile(r"bibliometria\.us\.es/prisma"))
    if prisma:
        perfil["prisma_url"] = prisma["href"]

    # Categoria, Area, Grupo de investigacion: texto plano tras la etiqueta
    texto = soup.get_text("\n")
    perfil["categoria"] = _extraer_tras_etiqueta(texto, "Categoría")
    perfil["area"] = _extraer_tras_etiqueta(texto, "Área")
    perfil["grupo_investigacion"] = _extraer_tras_etiqueta(texto, "Grupo de investigación")

    return perfil


def obtener_docencia(slug: str) -> list[dict]:
    """
    Scrapea la sección "Docencia > Asignaturas que imparte" del perfil us.es.

    Estructura HTML esperada:
      <h3 class="field-group-toggler">Asignaturas que imparte</h3>
      <div class="field-group-wrapper">
        <ul class="links field__items">
          <li><a href="/estudiar/.../grado-en-xxx-YYYY/CODIGO">Nombre</a></li>
          ...
        </ul>
      </div>

    Returns: [{"codigo": "2050001", "nombre": "...", "titulacion_slug": "grado-en-..."}, ...]
    Devuelve lista vacía si el perfil no tiene sección Docencia.
    """
    url = f"{BASE}/trabaja-en-la-us/directorio/{slug}"
    soup = _get_soup(url)

    h3 = soup.find(
        "h3",
        class_="field-group-toggler",
        string=lambda s: s and "Asignaturas que imparte" in s,
    )
    if not h3:
        return []

    container = h3.find_parent("div", class_="panel-title")
    if not container:
        return []

    resultados: list[dict] = []
    vistos: set[str] = set()

    for a in container.find_all("a", href=True):
        href = a["href"]
        # Formato esperado:
        # /estudiar/que-estudiar/oferta-de-grados/<slug-titulacion>/<codigo>
        m = re.match(
            r"^/estudiar/que-estudiar/oferta-de-grados/([^/]+)/(\d{6,8})/?$",
            href,
        )
        if not m:
            continue
        titulacion_slug = m.group(1)
        codigo = m.group(2)
        # Evita duplicados exactos (mismo código listado dos veces en la ficha).
        clave = f"{codigo}|{titulacion_slug}"
        if clave in vistos:
            continue
        vistos.add(clave)

        nombre = " ".join(a.get_text(strip=True).split())
        resultados.append({
            "codigo": codigo,
            "nombre": nombre,
            "titulacion_slug": titulacion_slug,
        })

    return resultados


def _extraer_tras_etiqueta(texto: str, etiqueta: str) -> str | None:
    """
    Busca 'Etiqueta\\n<valor>' en el texto y devuelve el valor (primera linea no vacia).
    """
    patron = re.compile(rf"{re.escape(etiqueta)}\s*\n+(.+?)(?:\n|$)", re.IGNORECASE)
    m = patron.search(texto)
    if not m:
        return None
    val = " ".join(m.group(1).split())
    return val or None
