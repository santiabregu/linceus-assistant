"""
Test del sistema de contexto con Ollama.
Ejecutar: python test_contexto.py
"""

import requests
import json
import re

OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"


def verificar_ollama():
    """Verifica que Ollama este corriendo."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False


def llamar_ollama(prompt):
    """Llama a Ollama con un prompt."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 150,
        }
    }

    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data.get("response", "")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def detectar_especifica_obvia(pregunta):
    """Detecta consultas obviamente especificas (heuristica rapida)."""
    pregunta_lower = pregunta.lower()

    patrones = [
        (r'(?:cuantos|cuanto)\s+(?:creditos)\s+tiene\s+(.+?)(?:\?|$)', "creditos"),
        (r'^(.+?)\s+tiene\s+(?:cuantos|cuanto)\s+(?:creditos)', "creditos"),
        (r'(?:creditos)\s+(?:de|tiene)\s+(.+?)(?:\?|$)', "creditos"),
        (r'^(.+?)\s+es\s+(?:obligatoria|optativa)', "tipo"),
        (r'(?:en\s+)?(?:que)\s+curso\s+(?:esta)\s+(.+?)(?:\?|$)', "curso"),
        (r'(?:que|qué)\s+es\s+(.+?)(?:\?|$)', "general"),
        (r'(?:informacion|info)\s+(?:de|sobre)\s+(.+?)(?:\?|$)', "general"),
    ]

    for patron, atributo in patrones:
        match = re.search(patron, pregunta_lower, re.IGNORECASE)
        if match:
            nombre = match.group(1).strip()
            nombre = re.sub(r'^(la\s+asignatura\s+de|la\s+asignatura|asignatura)\s+', '', nombre)
            nombre = nombre.strip('?.,! ')
            if len(nombre) > 1:
                return {
                    "tipo": "especifica",
                    "es_seguimiento": False,
                    "nombre_asignatura": nombre,
                    "atributo": atributo,
                    "metodo": "heuristica"
                }
    return None


def detectar_seguimiento_obvio(pregunta, tiene_contexto):
    """Detecta seguimientos obvios."""
    if not tiene_contexto:
        return None

    pregunta_lower = pregunta.lower().strip()

    patrones = [
        (r'^(?:y\s+)?(?:los\s+)?creditos\??$', "creditos"),
        (r'^(?:y\s+)?(?:cuantos|cuanto)\s+creditos\s+tiene\??$', "creditos"),
        (r'^(?:y\s+)?es\s+(?:obligatoria|optativa)\??$', "tipo"),
        (r'^(?:y\s+)?(?:de\s+)?(?:que\s+)?curso\s+es\??$', "curso"),
        (r'^(?:y\s+)?(?:la\s+)?duracion\??$', "duracion"),
    ]

    for patron, atributo in patrones:
        if re.match(patron, pregunta_lower):
            return {
                "tipo": "especifica",
                "es_seguimiento": True,
                "nombre_asignatura": None,
                "atributo": atributo,
                "metodo": "heuristica_seguimiento"
            }
    return None


def es_general_obvia(pregunta):
    """Detecta consultas obviamente generales."""
    pregunta_lower = pregunta.lower()
    patrones = [
        r'(?:asignaturas|materias)\s+(?:de|del|en)\s+(?:primero|segundo|tercero|cuarto)',
        r'(?:cuantas)\s+(?:asignaturas|optativas|obligatorias)',
        r'(?:optativas|obligatorias)\s+(?:de|del|en)',
    ]
    return any(re.search(p, pregunta_lower) for p in patrones)


def analizar_con_contexto(pregunta, contexto_asignatura=None):
    """Analiza una pregunta con contexto (sistema hibrido)."""

    # 1. HEURISTICAS: Especifica obvia
    resultado = detectar_especifica_obvia(pregunta)
    if resultado:
        resultado["metodo"] = "HEURISTICA (especifica)"
        return resultado

    # 2. HEURISTICAS: Seguimiento obvio
    tiene_contexto = contexto_asignatura is not None
    resultado = detectar_seguimiento_obvio(pregunta, tiene_contexto)
    if resultado:
        resultado["metodo"] = "HEURISTICA (seguimiento)"
        return resultado

    # 3. HEURISTICAS: General obvia
    if es_general_obvia(pregunta):
        return {
            "tipo": "general",
            "es_seguimiento": False,
            "nombre_asignatura": None,
            "atributo": None,
            "metodo": "HEURISTICA (general)"
        }

    # 4. LLM: Solo casos ambiguos
    if contexto_asignatura:
        contexto_str = f'CONTEXTO: La ultima asignatura consultada fue "{contexto_asignatura}".\n'
    else:
        contexto_str = "CONTEXTO: No hay asignatura previa en la conversacion.\n"

    prompt = f"""{contexto_str}PREGUNTA DEL USUARIO: "{pregunta}"

Analiza la consulta y responde SOLO con JSON valido:

{{
  "tipo": "especifica" o "general",
  "es_seguimiento": true/false,
  "nombre_asignatura": "nombre" o null,
  "atributo": "creditos"|"tipo"|"curso"|"duracion"|"general"
}}

REGLAS:
- tipo="especifica": pregunta sobre UNA asignatura concreta
- tipo="general": pregunta sobre VARIAS asignaturas (ej: "optativas de cuarto")
- es_seguimiento=true: si usa pronombres (esa, la, tiene) o continua tema anterior SIN nombrar asignatura nueva
- es_seguimiento=false: si menciona una asignatura nueva o no hay contexto
- nombre_asignatura: solo si menciona una asignatura NUEVA, null si es seguimiento
- atributo: que informacion pide (creditos, tipo, curso, duracion, o general si pide todo)

EJEMPLOS:
- "cuantos creditos tiene Redes" -> {{"tipo":"especifica","es_seguimiento":false,"nombre_asignatura":"Redes","atributo":"creditos"}}
- "y cuantos creditos tiene?" (con contexto) -> {{"tipo":"especifica","es_seguimiento":true,"nombre_asignatura":null,"atributo":"creditos"}}
- "es obligatoria?" (con contexto) -> {{"tipo":"especifica","es_seguimiento":true,"nombre_asignatura":null,"atributo":"tipo"}}
- "y Programacion?" (con contexto) -> {{"tipo":"especifica","es_seguimiento":false,"nombre_asignatura":"Programacion","atributo":"general"}}
- "asignaturas de primero" -> {{"tipo":"general","es_seguimiento":false,"nombre_asignatura":null,"atributo":null}}

JSON:"""

    salida = llamar_ollama(prompt)

    if salida:
        # Extraer JSON
        match = re.search(r'\{[^{}]*\}', salida)
        if match:
            try:
                data = json.loads(match.group(0))
                data["metodo"] = "LLM (caso ambiguo)"
                return data
            except:
                pass

    return {
        "tipo": "general",
        "es_seguimiento": False,
        "nombre_asignatura": None,
        "atributo": None,
        "metodo": "FALLBACK (error)"
    }


def test_conversacion():
    """Simula una conversacion completa."""
    print("\n" + "=" * 70)
    print("   SIMULACION DE CONVERSACION CON CONTEXTO")
    print("=" * 70)

    conversacion = [
        ("cuantos creditos tiene redes", None),
        ("y es obligatoria?", "Redes de Computadores"),
        ("de que curso es?", "Redes de Computadores"),
        ("y programacion cuantos creditos tiene?", "Redes de Computadores"),
        ("es anual?", "Fundamentos de Programacion"),
    ]

    for i, (pregunta, contexto) in enumerate(conversacion, 1):
        print(f"\n{'─' * 70}")
        print(f"TURNO {i}")
        print(f"{'─' * 70}")
        print(f"Usuario: \"{pregunta}\"")
        if contexto:
            print(f"Contexto actual: {contexto}")
        else:
            print(f"Contexto actual: (ninguno)")

        print("\nAnalizando...")
        resultado = analizar_con_contexto(pregunta, contexto)

        if resultado:
            print(f"\nResultado del analisis:")
            print(f"  tipo: {resultado.get('tipo')}")
            print(f"  es_seguimiento: {resultado.get('es_seguimiento')}")
            print(f"  nombre_asignatura: {resultado.get('nombre_asignatura')}")
            print(f"  atributo: {resultado.get('atributo')}")
            print(f"  metodo: {resultado.get('metodo')}")

            # Interpretacion
            if resultado.get('es_seguimiento'):
                print(f"\n  ✓ SEGUIMIENTO detectado - usara contexto previo")
            elif resultado.get('nombre_asignatura'):
                print(f"\n  ✓ NUEVA asignatura detectada - actualizara contexto")
            else:
                print(f"\n  ✓ Consulta GENERAL - no necesita contexto")
        else:
            print("\n  ✗ Error en analisis")

        input("\nPresiona Enter para continuar...")


def test_individual():
    """Test interactivo."""
    print("\n" + "=" * 70)
    print("   TEST INTERACTIVO")
    print("=" * 70)
    print("\nEscribe 'salir' para terminar\n")

    contexto = None

    while True:
        pregunta = input("\nPregunta: ").strip()

        if pregunta.lower() in ('salir', 'exit', 'quit'):
            break

        if not pregunta:
            continue

        print(f"Contexto actual: {contexto or '(ninguno)'}")
        print("Analizando...")

        resultado = analizar_con_contexto(pregunta, contexto)

        if resultado:
            print(f"\nResultado:")
            print(f"  tipo: {resultado.get('tipo')}")
            print(f"  es_seguimiento: {resultado.get('es_seguimiento')}")
            print(f"  nombre_asignatura: {resultado.get('nombre_asignatura')}")
            print(f"  atributo: {resultado.get('atributo')}")
            print(f"  metodo: {resultado.get('metodo')}")

            # Simular actualizacion de contexto
            if resultado.get('nombre_asignatura'):
                contexto = resultado.get('nombre_asignatura')
                print(f"\n  -> Contexto actualizado a: {contexto}")
            elif resultado.get('es_seguimiento'):
                print(f"  -> Usando contexto: {contexto}")
        else:
            print("Error en analisis")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   TEST DE CONTEXTO CON OLLAMA")
    print("=" * 70 + "\n")

    print("Verificando Ollama...")
    if not verificar_ollama():
        print("ERROR: Ollama no esta corriendo")
        print("Ejecuta: ollama serve")
        print("Luego ejecuta: ollama run llama3.2:3b")
        exit(1)

    print("OK: Ollama activo\n")

    print("Selecciona modo:")
    print("1. Conversacion simulada (recomendado)")
    print("2. Test interactivo")

    opcion = input("\nOpcion (1/2): ").strip()

    if opcion == "1":
        test_conversacion()
    elif opcion == "2":
        test_individual()
    else:
        print("Opcion invalida")

    print("\n" + "=" * 70)
    print("Test completado!")
    print("=" * 70)
