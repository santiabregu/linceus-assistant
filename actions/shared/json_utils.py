"""Utilidades de extraccion de JSON robustas frente a salidas verbosas del LLM.

Gemma 4 (sustituto de Gemma 3 27B desde mayo 2026) razona antes de responder
y suele envolver el JSON final en bloques markdown precedidos de texto. Las
funciones de este modulo extraen el dict JSON correcto independientemente
del envoltorio.
"""

import json
import re
from typing import Any, Dict, Iterable, Optional


def _iter_bloques_balanceados(texto: str) -> Iterable[str]:
    """Genera cada subcadena {...} con llaves balanceadas dentro de `texto`."""
    for inicio in (i for i, c in enumerate(texto) if c == "{"):
        nivel = 0
        for j in range(inicio, len(texto)):
            if texto[j] == "{":
                nivel += 1
            elif texto[j] == "}":
                nivel -= 1
                if nivel == 0:
                    yield texto[inicio:j + 1]
                    break


def extraer_json_dict(
    texto: str,
    requiere_clave: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Devuelve el primer dict JSON valido encontrado en `texto`, recorriendo
    los candidatos del ultimo al primero. Tolerante a:
      * bloques markdown ```json ... ``` o ``` ... ```
      * texto narrativo / razonamiento antes y/o despues del JSON
      * objetos JSON anidados

    Si se pasa `requiere_clave`, solo se aceptan candidatos cuyo dict
    contenga esa clave en el nivel superior (util para distinguir el JSON
    objetivo de objetos auxiliares que el razonamiento del LLM pueda incluir).
    """
    if not texto:
        return None

    def _valido(data: Any) -> bool:
        if not isinstance(data, dict):
            return False
        if requiere_clave is not None and requiere_clave not in data:
            return False
        return True

    # 1. Bloques markdown explicitos. Se prueban del ultimo al primero.
    bloques = re.findall(
        r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", texto, re.IGNORECASE
    )
    for bloque in reversed(bloques):
        try:
            data = json.loads(bloque)
            if _valido(data):
                return data
        except json.JSONDecodeError:
            continue

    # 2. Cualquier {...} balanceado, recorriendo del ultimo al primero.
    candidatos = list(_iter_bloques_balanceados(texto))
    for cand in reversed(candidatos):
        try:
            data = json.loads(cand)
            if _valido(data):
                return data
        except json.JSONDecodeError:
            continue

    return None
