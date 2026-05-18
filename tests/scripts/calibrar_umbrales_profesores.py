"""Mini-experimento de calibracion de umbrales del fuzzy matching de profesores.

Reproduce el procedimiento que cita la memoria: ejecutar un corpus de consultas
de prueba sobre el directorio real de profesores y medir precision/recall del
matching para tres ajustes de umbral.

Uso:
    python tests/scripts/calibrar_umbrales_profesores.py

No modifica nada en la base de datos.
"""

import os
import sys
from typing import List, Tuple

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from actions.shared.matching import score_por_normalizado  # noqa: E402

load_dotenv()


# ─── Conjunto de casos de prueba ──────────────────────────────────────────────
#
# Cada caso es (consulta, lista de nombres normalizados esperados).
# Cubrimos cinco categorias representativas: nombre completo exacto,
# apellido solo, typo moderado (1-2 caracteres distintos), typo severo
# (3+ caracteres distintos o letras invertidas), y nombres cortos
# ambiguos (deberian quedar como descartados o sugerencia, no firmes).
#
# La verdad sobre cada caso se ha fijado manualmente a partir del directorio
# real de profesores activos (tabla profesores).

CASOS = [
    # --- nombre completo exacto (15) ---
    ("Capitán Agudo, Carlos", ["capitan agudo carlos"]),
    ("Gómez López, María Teresa", ["gomez lopez maria teresa"]),
    ("Olivero González, Miguel Ángel", ["olivero gonzalez miguel angel"]),
    ("Fernández-Montes González, Alejandro", ["fernandez-montes gonzalez alejandro"]),
    ("Gutiérrez Fernández, Antonio Manuel", ["gutierrez fernandez antonio manuel"]),
    ("Ruiz Cortés, Antonio", ["ruiz cortes antonio"]),
    ("Benavides Cuevas, David", ["benavides cuevas david"]),
    ("Segura Rueda, Sergio", ["segura rueda sergio"]),
    ("Galindo Duarte, José Antonio", ["galindo duarte jose antonio"]),
    ("Ramos Gutiérrez, Belén", ["ramos gutierrez belen"]),

    # --- apellido o nombre solo (8) ---
    ("Benavides", ["benavides cuevas david"]),
    ("Galindo", ["galindo duarte jose antonio"]),
    ("Sergio Segura", ["segura rueda sergio"]),
    ("Ruiz Cortés", ["ruiz cortes antonio"]),
    ("Olivero", ["olivero gonzalez miguel angel"]),
    ("Ramos", ["ramos gutierrez belen"]),
    ("Reina", ["reina jimenez juan antonio"]),
    ("Vega", ["vega marquez maria de los angeles"]),

    # --- typos moderados (7): 1-2 caracteres mal, deberia matchear ---
    ("Benavies", ["benavides cuevas david"]),       # falta 'd'
    ("Galindro", ["galindo duarte jose antonio"]),  # 'r' de mas
    ("Olivro", ["olivero gonzalez miguel angel"]),  # falta 'e'
    ("Segrua", ["segura rueda sergio"]),            # letras invertidas
    ("Cpitn Agudo", ["capitan agudo carlos"]),      # 2 letras faltan
    ("Gmez Lopez", ["gomez lopez maria teresa"]),   # falta acento + 'o'
    ("Parejjo", []),                                # typo, profesor no en BD

    # --- typos severos (5): no deberia matchear como firme ni sugerencia ---
    ("Bnavds", []),                          # demasiado corto/destruido
    ("Galnzdoo", []),                        # destrucion fonetica
    ("Caputin", []),                         # transformacion severa
    ("Goz", []),                             # demasiado generico
    ("Olv", []),                             # demasiado corto

    # --- nombres cortos / muy genericos / ambiguos (10) ---
    # Estos deberian (a) NO ser firmes (porque matchean demasiados profesores),
    # o (b) ser descartados si el umbral es razonable.
    ("García", []),  # multiples Garcia en BD → ambiguo, no debe ser firme unico
    ("López", []),
    ("Martín", []),
    ("Pérez", []),
    ("González", []),
    ("Fernández", []),
    ("Rodríguez", []),
    ("Sánchez", []),
    ("Antonio", []),
    ("Juan", []),
]


def cargar_profesores_db() -> List[dict]:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
        database=os.getenv("DB_DATABASE"),
        user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    )
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, nombre_completo, nombre_normalizado "
                "FROM profesores WHERE activo = TRUE;"
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def evaluar(
    casos: List[Tuple[str, List[str]]],
    profesores: List[dict],
    umbral_firme: float,
    umbral_descarte: float,
) -> Tuple[int, int, int, int]:
    """Devuelve (TP, FP, FN, TN) sumados sobre todos los casos.

    Para cada caso:
      - Se calcula score contra cada profesor.
      - Se consideran 'firmes' los que superan umbral_firme.
      - Si la consulta tiene profesor esperado, los firmes que coinciden
        con el esperado son TP; los firmes restantes son FP; los esperados
        no recuperados son FN.
      - Si la consulta no tiene profesor esperado (ambigua, severa),
        cualquier firme es FP; ningun firme es TN.
    """
    TP = FP = FN = TN = 0
    for consulta, esperados_norm in casos:
        scores = [
            (p, score_por_normalizado(consulta, p["nombre_normalizado"] or ""))
            for p in profesores
        ]
        firmes = [p for p, s in scores if s >= umbral_firme]

        if esperados_norm:
            firmes_norm = {f["nombre_normalizado"] for f in firmes}
            tps = firmes_norm & set(esperados_norm)
            TP += len(tps)
            FP += len(firmes_norm - set(esperados_norm))
            FN += len(set(esperados_norm) - firmes_norm)
        else:
            if firmes:
                FP += len(firmes)
            else:
                TN += 1
    return TP, FP, FN, TN


def metricas(TP: int, FP: int, FN: int) -> Tuple[float, float]:
    prec = TP / (TP + FP) if (TP + FP) else 1.0
    recall = TP / (TP + FN) if (TP + FN) else 1.0
    return prec, recall


def main() -> None:
    profesores = cargar_profesores_db()
    print(f"Profesores cargados: {len(profesores)}")
    print(f"Casos de prueba:     {len(CASOS)}")
    print()

    configuraciones = [
        ("Umbral firme 0,80", 0.80, 0.30),
        ("Umbral firme 0,40", 0.40, 0.30),
        ("Umbral firme 0,60 + sugerencias 0,30", 0.60, 0.30),
    ]

    print(f"{'Configuracion':<42} {'TP':>4} {'FP':>4} {'FN':>4} {'TN':>4} {'Prec':>6} {'Recall':>7}")
    print("-" * 80)
    for nombre, uf, ud in configuraciones:
        TP, FP, FN, TN = evaluar(CASOS, profesores, uf, ud)
        prec, rec = metricas(TP, FP, FN)
        print(f"{nombre:<42} {TP:>4} {FP:>4} {FN:>4} {TN:>4} {prec*100:>5.1f}% {rec*100:>6.1f}%")


if __name__ == "__main__":
    main()
