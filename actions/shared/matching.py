"""Funciones de matching de nombres compartidas entre dominios
(profesores, asignaturas). Puntúa siempre contra el campo
`nombre_normalizado` (nombre + apellidos / nombre completo sin tildes)
sin penalizaciones especiales: si los tokens de la consulta aparecen
en el normalizado, es match firme.
"""

import unicodedata
from typing import List, Tuple, Dict


_UMBRAL_DESCARTE = 0.30
_UMBRAL_MATCH_FIRME = 0.60


def normalizar(texto: str) -> str:
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower().strip()


def score_por_normalizado(consulta: str, normalizado: str) -> float:
    """Puntúa [0, 1] la coincidencia de `consulta` contra `normalizado`.

    - Si todos los tokens de la consulta están como substring en el
      normalizado → 1.0 (match firme).
    - Si parte de los tokens coinciden → proporción.
    - No hay penalizaciones por "solo nombre" o "solo apellido": basta
      con que los fragmentos pedidos estén en el nombre completo.
    """
    if not consulta:
        return 1.0
    consulta_norm = normalizar(consulta)
    tokens = [t for t in consulta_norm.split() if len(t) >= 2]
    if not tokens:
        return 1.0
    norm = normalizar(normalizado)
    if not norm:
        return 0.0

    if all(t in norm for t in tokens):
        return 1.0

    aciertos = sum(1 for t in tokens if t in norm)
    return round(aciertos / len(tokens), 3)


def clasificar_por_normalizado(
    consulta: str, resultados: List[Dict], campo: str = "nombre_normalizado",
    umbral_firme: float = _UMBRAL_MATCH_FIRME,
    umbral_descarte: float = _UMBRAL_DESCARTE,
) -> Tuple[List[Dict], List[Dict]]:
    """Separa resultados en (firmes, sugerencias) por score contra `campo`.
    Los resultados con score < umbral_descarte se eliminan.
    """
    if not consulta or not resultados:
        return resultados, []

    # Fallback al campo nombre_completo / (nombre + apellidos) si el registro
    # no trae nombre_normalizado
    def _valor_normalizado(r: Dict) -> str:
        v = r.get(campo)
        if v:
            return v
        nombre = r.get("nombre") or ""
        apellidos = r.get("apellidos") or ""
        return f"{nombre} {apellidos}".strip()

    scored = [(r, score_por_normalizado(consulta, _valor_normalizado(r))) for r in resultados]
    firmes = [r for r, s in scored if s >= umbral_firme]
    sugerencias = [r for r, s in scored if umbral_descarte <= s < umbral_firme]

    for r, s in scored:
        marca = "✅" if s >= umbral_firme else ("❓" if s >= umbral_descarte else "❌")
        print(f"     {marca} {s:.2f}  {_valor_normalizado(r)}")

    return firmes, sugerencias
