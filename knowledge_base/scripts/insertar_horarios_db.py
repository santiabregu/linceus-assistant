"""
insertar_horarios_db.py
-----------------------
Lee los archivos Markdown generados por generar_horarios.py y los inserta en
las tablas de Supabase: aulas, grupos_clase y horarios.

Uso:
    python insertar_horarios_db.py          # Insertar todo
    python insertar_horarios_db.py --clean  # Limpiar tablas antes de insertar

Requisitos:
    - .env con las credenciales de la BD
    - Archivos Markdown en horarios_aulas/
    - Asignaturas ya insertadas en la BD
"""

import os
import re
import sys
import uuid
import unicodedata
from collections import defaultdict
from dotenv import load_dotenv
import psycopg2

load_dotenv()

# ─── Configuración ──────────────────────────────────────────────────────────

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "horarios_aulas")

TITULACION_CARPETA = {
    "GII-IC": "computadores",
    "GII-IS": "software",
    "GII-TI": "tecnologias_informaticas",
}

CARPETA_TITULACION = {v: k for k, v in TITULACION_CARPETA.items()}

TITULACION_IDS = {
    "GII-IS": "c0000000-0000-0000-0000-000000000001",
    "GII-IC": "c0000000-0000-0000-0000-000000000002",
    "GII-TI": "c0000000-0000-0000-0000-000000000003",
}

CENTRO_ID = "b0000000-0000-0000-0000-000000000001"  # ETSII

# Importar diccionario unificado de alias desde config central
# (las claves están en minúsculas; resolver_abreviatura hace .lower())
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "actions"))
from actions.shared.config import ALIAS_ASIGNATURAS as _ALIAS_CENTRAL, ALIAS_POR_TITULACION

# Convertir a claves UPPER para compatibilidad con el código existente
ABREVIATURA_NOMBRE = {k.upper(): v for k, v in _ALIAS_CENTRAL.items()}

# Convertir alias por titulación a UPPER
ABREVIATURA_POR_TITULACION = {
    tit: {k.upper(): v for k, v in aliases.items()}
    for tit, aliases in ALIAS_POR_TITULACION.items()
}


# ─── Utilidades ─────────────────────────────────────────────────────────────

def normalizar(texto):
    """Quita tildes, minúsculas, limpia."""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower().strip()


def get_connection():
    """Conecta a la BD."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_DATABASE"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def cargar_asignaturas(conn):
    """
    Carga todas las asignaturas de la BD.
    Retorna {(titulacion_codigo, nombre_normalizado): asignatura_id}
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT a.id, a.nombre, t.codigo
        FROM asignaturas a
        JOIN titulaciones t ON a.titulacion_id = t.id
        WHERE a.activa = true
    """)
    mapa = {}
    for row in cur.fetchall():
        asig_id, nombre, tit_codigo = row
        nombre_norm = normalizar(nombre)
        mapa[(tit_codigo, nombre_norm)] = str(asig_id)
    cur.close()
    return mapa


RE_CODIGO_AULA = re.compile(r"^[A-Z]\d+\.\d+")


def resolver_abreviatura(abreviatura, titulacion, mapa_asignaturas):
    """
    Resuelve una abreviatura del PDF al ID de asignatura en la BD.
    Retorna (asignatura_id, nombre_asignatura) o (None, None).
    """
    abr_upper = abreviatura.upper().strip()

    # Ignorar si parece un código de aula (ej: H0.11, A2.14)
    if RE_CODIGO_AULA.match(abr_upper):
        return None, abr_upper

    # Quitar sufijos de grupo como (1), (2), (3)
    abr_upper = re.sub(r"\(\d+\)$", "", abr_upper).strip()

    # Intentar mapeo específico por titulación primero
    nombre_norm = None
    if titulacion in ABREVIATURA_POR_TITULACION:
        nombre_norm = ABREVIATURA_POR_TITULACION[titulacion].get(abr_upper)

    # Luego mapeo general
    if not nombre_norm:
        nombre_norm = ABREVIATURA_NOMBRE.get(abr_upper)

    if not nombre_norm:
        return None, abr_upper

    asig_id = mapa_asignaturas.get((titulacion, nombre_norm))
    if asig_id:
        return asig_id, nombre_norm

    # Intentar búsqueda parcial (por si el nombre no coincide exactamente)
    for (tit, nombre), aid in mapa_asignaturas.items():
        if tit == titulacion and nombre_norm in nombre:
            return aid, nombre

    return None, nombre_norm


# ─── Parseo de Markdown ─────────────────────────────────────────────────────

# Patrón estricto para código de aula válido
RE_AULA_VALIDA = re.compile(r"^[A-Z]\d+\.\d+[a-z]?$")

DIAS_MAP = {
    "Lunes": 1, "Martes": 2, "Miércoles": 3, "Jueves": 4, "Viernes": 5,
}

RE_HORA = re.compile(r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})")


def parsear_celda_horario(texto):
    """
    Parsea 'FP (H0.11, F1.30, F1.31)' → (asignatura, aula_principal, labs).
    Puede haber múltiples asignaturas separadas por '/'.
    """
    if not texto or texto.strip() == "-":
        return []

    # Puede haber asignaturas compartidas: "EdC / FFI (G1.32 / G0.34)"
    # Tratamos cada '/' como posibles múltiples asignaturas
    # Pero primero separamos la parte principal del paréntesis
    m = re.match(r"^(.+?)\s*\((.+)\)\s*$", texto)
    if m:
        asig_parte = m.group(1).strip()
        aulas_parte = m.group(2).strip()
    else:
        asig_parte = texto.strip()
        aulas_parte = ""

    # Separar múltiples asignaturas por '/'
    asignaturas = [a.strip() for a in asig_parte.split("/") if a.strip()]
    aulas = [a.strip() for a in aulas_parte.split("/") if a.strip()] if aulas_parte else []

    resultados = []
    for i, asig in enumerate(asignaturas):
        # La primera aula del paréntesis suele ser la principal (de teoría)
        aula = ""
        if aulas:
            if i < len(aulas):
                aula = aulas[i].strip()
            else:
                aula = aulas[0].strip()

        # Extraer solo el primer código de aula (puede haber labs separados por coma)
        aula_principal = ""
        labs = []
        if aula:
            partes = [p.strip().rstrip("*") for p in aula.split(",") if p.strip()]
            if partes:
                aula_principal = partes[0]
                labs = partes[1:]

        resultados.append((asig, aula_principal, labs))

    return resultados


def parsear_archivo_md(filepath):
    """
    Parsea un archivo Markdown de horario.
    Retorna [(cuatrimestre, dia_num, hora_inicio, hora_fin, asignatura, aula_codigo)]
    """
    with open(filepath, "r", encoding="utf-8") as f:
        contenido = f.read()

    entradas = []
    cuatri_actual = None
    dias_header = []

    for linea in contenido.split("\n"):
        linea = linea.strip()

        m = re.match(r"###\s+Cuatrimestre\s+(\d)", linea)
        if m:
            cuatri_actual = int(m.group(1))
            continue

        if not cuatri_actual:
            continue

        if linea.startswith("| Hora"):
            dias_header = [
                c.strip()
                for c in linea.split("|")[1:]
                if c.strip() and c.strip() != "Hora"
            ]
            continue

        if linea.startswith("|---"):
            continue

        if linea.startswith("|") and cuatri_actual:
            celdas = [c.strip() for c in linea.split("|")]
            celdas = [c for c in celdas if c != ""]
            if not celdas:
                continue

            # Parsear hora
            hora_m = RE_HORA.match(celdas[0])
            if not hora_m:
                continue
            hora_inicio = hora_m.group(1)
            hora_fin = hora_m.group(2)

            # Parsear cada día
            for i, dia_nombre in enumerate(dias_header):
                dia_num = DIAS_MAP.get(dia_nombre)
                if not dia_num:
                    continue

                celda_texto = celdas[i + 1] if i + 1 < len(celdas) else "-"
                items = parsear_celda_horario(celda_texto)

                for asig, aula, labs in items:
                    if not asig or asig == "-":
                        continue
                    # Limpiar: ignorar si la "asignatura" parece un código de aula
                    if RE_AULA_VALIDA.match(asig.strip()):
                        continue
                    # Limpiar: ignorar fragmentos de parsing roto
                    if re.match(r"^\d+\)", asig) or asig.startswith("("):
                        continue
                    # Limpiar aula: tomar solo el primer código si hay varios pegados
                    if aula and " " in aula:
                        aula = aula.split()[0]
                    # Solo aulas con formato válido
                    if aula and not RE_AULA_VALIDA.match(aula):
                        aula = ""
                    entradas.append(
                        (cuatri_actual, dia_num, hora_inicio, hora_fin, asig, aula)
                    )

    return entradas


# ─── Inserción en BD ────────────────────────────────────────────────────────

def es_aula_valida(codigo):
    """Comprueba que un código tiene formato de aula real."""
    return bool(RE_AULA_VALIDA.match(codigo.strip()))


def insertar_aulas(conn, aulas_codigos):
    """Inserta aulas que no existan. Retorna {codigo: id}."""
    cur = conn.cursor()

    # Cargar existentes
    cur.execute("SELECT id, codigo FROM aulas")
    existentes = {row[1]: str(row[0]) for row in cur.fetchall()}

    # Filtrar solo códigos de aula válidos
    validas = {c for c in aulas_codigos if es_aula_valida(c)}
    descartadas = aulas_codigos - validas
    if descartadas:
        print(f"  Codigos descartados (no son aulas): {sorted(descartadas)}")

    nuevas = validas - set(existentes.keys())
    for codigo in sorted(nuevas):
        aula_id = str(uuid.uuid4())
        # Deducir edificio y planta del código (ej: H0.11 → edificio H, planta 0)
        m = re.match(r"([A-Z])(\d+)\.(\d+)", codigo)
        letra = m.group(1)
        piso = m.group(2)
        edificio = letra
        planta = piso
        # Labs suelen ser G, F, B, I
        tipo = "laboratorio" if letra in ("G", "F", "B", "I") else "teoria"

        cur.execute("""
            INSERT INTO aulas (id, centro_id, codigo, edificio, planta, tipo, activa)
            VALUES (%s, %s, %s, %s, %s, %s, true)
        """, (aula_id, CENTRO_ID, codigo, edificio, planta, tipo))
        existentes[codigo] = aula_id

    conn.commit()
    cur.close()
    print(f"  Aulas: {len(nuevas)} nuevas insertadas, {len(existentes)} total")
    return existentes


def insertar_grupos_clase(conn, grupos_necesarios, mapa_asignaturas, titulacion):
    """
    Inserta grupos_clase que no existan.
    grupos_necesarios: set de (asignatura_abr, grupo_num, cuatrimestre)
    Un grupo_clase es único por (asignatura, grupo, tipo, curso_academico),
    no por cuatrimestre. Ambos cuatrimestres comparten el mismo grupo_clase.
    Retorna {(asignatura_id, grupo_num): grupo_clase_id}
    """
    cur = conn.cursor()

    # Cargar existentes
    cur.execute("""
        SELECT gc.id, gc.asignatura_id, gc.codigo
        FROM grupos_clase gc
        JOIN asignaturas a ON gc.asignatura_id = a.id
        JOIN titulaciones t ON a.titulacion_id = t.id
        WHERE t.codigo = %s
    """, (titulacion,))
    existentes = {}
    for row in cur.fetchall():
        gc_id, asig_id, codigo = row
        existentes[(str(asig_id), codigo)] = str(gc_id)

    nuevos = 0
    resultado = {}
    no_encontrados = set()

    # Deduplicar: solo necesitamos (asig, grupo), no importa el cuatrimestre
    pares_unicos = set()
    for asig_abr, grupo_num, cuatri in grupos_necesarios:
        pares_unicos.add((asig_abr, grupo_num))

    for asig_abr, grupo_num in pares_unicos:
        asig_id, nombre = resolver_abreviatura(asig_abr, titulacion, mapa_asignaturas)
        if not asig_id:
            no_encontrados.add(asig_abr)
            continue

        grupo_codigo = str(grupo_num)
        grupo_nombre = f"Grupo {grupo_num}"
        key = (asig_id, grupo_codigo)

        if key in existentes:
            resultado[(asig_id, grupo_num)] = existentes[key]
            continue

        gc_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO grupos_clase
                (id, asignatura_id, codigo, nombre, tipo, curso_academico, activo)
            VALUES (%s, %s, %s, %s, 'teoria', '2025-26', true)
        """, (gc_id, asig_id, grupo_codigo, grupo_nombre))
        existentes[key] = gc_id
        resultado[(asig_id, grupo_num)] = gc_id
        nuevos += 1

    conn.commit()
    cur.close()

    if no_encontrados:
        print(f"  AVISO: Abreviaturas no mapeadas en {titulacion}: {sorted(no_encontrados)}")
    print(f"  Grupos_clase: {nuevos} nuevos insertados")
    return resultado


def insertar_horarios(conn, entradas_horario, mapa_aulas, mapa_grupos, mapa_asignaturas, titulacion):
    """Inserta los registros de horarios."""
    cur = conn.cursor()
    insertados = 0
    no_resueltos = set()

    for cuatri, dia, hora_inicio, hora_fin, asig_abr, aula_codigo in entradas_horario:
        # Resolver asignatura
        asig_id, _ = resolver_abreviatura(asig_abr, titulacion, mapa_asignaturas)
        if not asig_id:
            no_resueltos.add(asig_abr)
            continue

        # Resolver aula (puede estar vacía para slots de solo lab)
        aula_id = mapa_aulas.get(aula_codigo) if aula_codigo else None

        # Resolver grupo_clase (key es (asig_id, grupo_num) sin cuatrimestre)
        gc_key = (asig_id, entradas_horario._grupo_num)
        gc_id = mapa_grupos.get(gc_key)
        if not gc_id:
            continue

        horario_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO horarios
                (id, grupo_id, aula_id, dia_semana, hora_inicio, hora_fin, activo)
            VALUES (%s, %s, %s, %s, %s, %s, true)
        """, (horario_id, gc_id, aula_id, dia, hora_inicio, hora_fin))
        insertados += 1

    conn.commit()
    cur.close()
    return insertados, no_resueltos


# ─── Wrapper con grupo_num adjunto ──────────────────────────────────────────

class EntradasConGrupo(list):
    """Lista de entradas con un atributo grupo_num."""
    def __init__(self, items, grupo_num):
        super().__init__(items)
        self._grupo_num = grupo_num


# ─── Proceso principal ──────────────────────────────────────────────────────

def limpiar_tablas(conn):
    """Limpia horarios, grupos_clase y aulas (en orden por FK)."""
    cur = conn.cursor()
    cur.execute("DELETE FROM horarios")
    cur.execute("DELETE FROM grupos_clase")
    cur.execute("DELETE FROM aulas")
    conn.commit()
    cur.close()
    print("  Tablas horarios, grupos_clase y aulas limpiadas.")


def main():
    print("=== Inserción de horarios en Supabase ===\n")

    clean = "--clean" in sys.argv

    conn = get_connection()
    if not conn:
        print("Error: no se pudo conectar a la BD")
        sys.exit(1)

    if clean:
        print("1. Limpiando tablas...")
        limpiar_tablas(conn)
    else:
        print("1. Modo incremental (usa --clean para limpiar primero)")

    # Cargar mapa de asignaturas
    print("\n2. Cargando asignaturas de la BD...")
    mapa_asignaturas = cargar_asignaturas(conn)
    print(f"  {len(mapa_asignaturas)} asignaturas cargadas")

    # Recorrer todos los archivos Markdown
    print("\n3. Parseando archivos Markdown...")
    todas_aulas = set()
    todos_grupos = defaultdict(set)  # {titulacion: set((abr, grupo, cuatri))}
    todas_entradas = []  # [(titulacion, curso, grupo, entradas)]

    for carpeta_nombre in sorted(os.listdir(BASE_DIR)):
        carpeta_path = os.path.join(BASE_DIR, carpeta_nombre)
        if not os.path.isdir(carpeta_path):
            continue

        titulacion = CARPETA_TITULACION.get(carpeta_nombre)
        if not titulacion:
            continue

        for archivo in sorted(os.listdir(carpeta_path)):
            m = re.match(r"curso(\d+)_grupo(\d+)\.md", archivo)
            if not m:
                continue

            curso = int(m.group(1))
            grupo = int(m.group(2))
            filepath = os.path.join(carpeta_path, archivo)

            entradas = parsear_archivo_md(filepath)
            print(f"  {carpeta_nombre}/curso{curso}_grupo{grupo}: {len(entradas)} entradas")

            for cuatri, dia, h_ini, h_fin, asig, aula in entradas:
                if aula:
                    todas_aulas.add(aula)
                todos_grupos[titulacion].add((asig, grupo, cuatri))

            todas_entradas.append((titulacion, curso, grupo, entradas))

    # Insertar aulas
    print(f"\n4. Insertando aulas ({len(todas_aulas)} únicas)...")
    mapa_aulas = insertar_aulas(conn, todas_aulas)

    # Insertar grupos_clase por titulación
    print("\n5. Insertando grupos_clase...")
    mapa_grupos_global = {}
    for titulacion, grupos_set in todos_grupos.items():
        print(f"\n  [{titulacion}]")
        mapa_gc = insertar_grupos_clase(
            conn, grupos_set, mapa_asignaturas, titulacion
        )
        mapa_grupos_global[titulacion] = mapa_gc

    # Insertar horarios
    print("\n6. Insertando horarios...")
    total_insertados = 0
    todas_no_resueltas = set()

    for titulacion, curso, grupo, entradas in todas_entradas:
        mapa_gc = mapa_grupos_global.get(titulacion, {})
        entradas_wrapped = EntradasConGrupo(entradas, grupo)
        n, no_res = insertar_horarios(
            conn, entradas_wrapped, mapa_aulas, mapa_gc, mapa_asignaturas, titulacion
        )
        total_insertados += n
        todas_no_resueltas.update(no_res)

    print(f"\n  Total horarios insertados: {total_insertados}")
    if todas_no_resueltas:
        print(f"  AVISO: Abreviaturas no resueltas (ignoradas): {sorted(todas_no_resueltas)}")

    # Resumen
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM aulas")
    n_aulas = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM grupos_clase")
    n_gc = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM horarios")
    n_hor = cur.fetchone()[0]
    cur.close()

    print(f"\n=== Resumen BD ===")
    print(f"  Aulas: {n_aulas}")
    print(f"  Grupos clase: {n_gc}")
    print(f"  Horarios: {n_hor}")

    conn.close()
    print("\n¡Listo!")


if __name__ == "__main__":
    main()
