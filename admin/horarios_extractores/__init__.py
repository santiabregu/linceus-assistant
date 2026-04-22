"""
Registry de extractores de horarios por centro.

Cada extractor es responsable de parsear el PDF/fuente oficial del centro y
producir la estructura comun definida en `base.ExtraccionHorarios`. Desde ahi,
`base.insertar_en_bd()` y `base.escribir_markdown()` se ocupan del resto.

Para anyadir un centro nuevo:
  1. Crear `admin/horarios_extractores/<slug_centro>.py` que exponga
     `ejecutar_pipeline(curso_academico, limpiar) -> dict`.
  2. Registrar aqui en `EXTRACTORES` con el codigo de centro que uses en BD.
"""

from . import etsii


EXTRACTORES = {
    "ETSII": {
        "funcion": etsii.ejecutar_pipeline,
        "descripcion": "PDF oficial de ETSII (informatica.us.es)",
        "pdf_url": etsii.PDF_URL,
    },
}


def obtener_extractor(centro_codigo: str):
    return EXTRACTORES.get(centro_codigo)


def codigos_soportados() -> list[str]:
    return list(EXTRACTORES.keys())
