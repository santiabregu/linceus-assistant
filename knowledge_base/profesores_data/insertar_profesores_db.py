"""
insertar_profesores_db.py
-------------------------
Lee los JSON generados por los scrapers de cada departamento e inserta
los profesores en la tabla `profesores` de Supabase.

Uso:
    python profesores/insertar_profesores_db.py          # Insertar todo
    python profesores/insertar_profesores_db.py --clean   # Limpiar tabla antes

Requisitos:
    - .env con credenciales de BD
    - JSONs en profesores/datos/ (ejecutar scrapers primero)
    - Departamentos ya insertados en la BD
"""

import json
import os
import re
import sys
import unicodedata
import uuid

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos")

DEPARTAMENTO_SIGLAS = ["LSI", "CCIA", "DTE", "MA1"]

EDIFICIO_PLANTA = {
    "A": ("A", None), "B": ("B", None), "E": ("E", None),
    "F": ("F", None), "G": ("G", None), "H": ("H", None),
    "I": ("I", None),
}


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower().strip()


def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_DATABASE"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def cargar_departamentos(conn):
    """Retorna {siglas: id}"""
    cur = conn.cursor()
    cur.execute("SELECT id, siglas FROM departamentos WHERE activo = true")
    mapa = {row[1]: str(row[0]) for row in cur.fetchall()}
    cur.close()
    return mapa


def cargar_profesores_existentes(conn):
    """Retorna {nombre_normalizado: id} para evitar duplicados."""
    cur = conn.cursor()
    cur.execute("SELECT id, nombre_normalizado FROM profesores")
    mapa = {row[1]: str(row[0]) for row in cur.fetchall()}
    cur.close()
    return mapa


def extraer_edificio_planta(despacho):
    """Dado un despacho como 'F1.45', extrae edificio y planta."""
    if not despacho:
        return None, None
    match = re.match(r"([A-Z])(\d+)\.\d+", despacho)
    if match:
        return match.group(1), match.group(2)
    return None, None


def leer_json_departamento(siglas):
    """Lee el JSON de un departamento."""
    archivo = os.path.join(DATOS_DIR, f"{siglas.lower()}.json")
    if not os.path.exists(archivo):
        print(f"  Archivo no encontrado: {archivo}")
        return []
    with open(archivo, "r", encoding="utf-8") as f:
        return json.load(f)


def insertar_profesores(conn, profesores_json, departamento_id, existentes):
    """Inserta profesores nuevos en la BD. Retorna contadores."""
    cur = conn.cursor()
    insertados = 0
    omitidos = 0

    for prof in profesores_json:
        nombre = prof.get("nombre", "")
        apellidos = prof.get("apellidos", "")

        # Calcular nombre_normalizado para detección de duplicados
        nombre_norm = normalizar(f"{apellidos} {nombre}" if apellidos else nombre)

        # Evitar duplicados
        if nombre_norm in existentes:
            omitidos += 1
            continue

        edificio, planta = extraer_edificio_planta(prof.get("despacho"))

        profesor_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO profesores (
                id, departamento_id, nombre, apellidos,
                email, telefono,
                despacho, edificio, planta,
                web_personal, orcid,
                categoria_academica, enlace_perfil,
                activo
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s,
                true
            )
        """, (
            profesor_id,
            departamento_id,
            nombre,
            apellidos,
            prof.get("email"),
            prof.get("telefono"),
            prof.get("despacho"),
            edificio,
            planta,
            prof.get("web_personal"),
            prof.get("orcid"),
            prof.get("categoria_academica"),
            prof.get("enlace_perfil"),
        ))

        existentes[nombre_norm] = profesor_id
        insertados += 1

    conn.commit()
    cur.close()
    return insertados, omitidos


def limpiar_tabla(conn):
    """Elimina todos los profesores."""
    cur = conn.cursor()
    cur.execute("DELETE FROM profesores")
    eliminados = cur.rowcount
    conn.commit()
    cur.close()
    return eliminados


def main():
    clean = "--clean" in sys.argv

    print("=== Insertar profesores en BD ===\n")
    conn = get_connection()

    if clean:
        eliminados = limpiar_tabla(conn)
        print(f"Tabla limpiada: {eliminados} registros eliminados\n")

    # Cargar mapas
    deptos = cargar_departamentos(conn)
    print(f"Departamentos en BD: {deptos}\n")

    existentes = cargar_profesores_existentes(conn)
    print(f"Profesores existentes en BD: {len(existentes)}\n")

    total_insertados = 0
    total_omitidos = 0

    for siglas in DEPARTAMENTO_SIGLAS:
        print(f"--- {siglas} ---")

        if siglas not in deptos:
            print(f"  Departamento {siglas} no encontrado en BD, omitiendo.")
            continue

        profesores_json = leer_json_departamento(siglas)
        if not profesores_json:
            print(f"  Sin datos para {siglas}.")
            continue

        print(f"  Profesores en JSON: {len(profesores_json)}")

        insertados, omitidos = insertar_profesores(
            conn, profesores_json, deptos[siglas], existentes
        )

        print(f"  Insertados: {insertados}, Omitidos (duplicados): {omitidos}")
        total_insertados += insertados
        total_omitidos += omitidos

    conn.close()
    print(f"\n=== Resumen ===")
    print(f"Total insertados: {total_insertados}")
    print(f"Total omitidos:   {total_omitidos}")


if __name__ == "__main__":
    main()
