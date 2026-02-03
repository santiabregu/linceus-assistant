import subprocess
import json
import re


def limpiar_ansi(texto: str) -> str:
    """Elimina códigos de escape ANSI del texto."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])|\[\?[0-9;]*[a-zA-Z]|\[K|\[G')
    return ansi_escape.sub('', texto)

PROMPT_TEMPLATE = """Clasifica este mensaje de un chatbot universitario.

Intents posibles: consultar_asignatura, saludo, despedida
Extrae: nombre_asignatura (si menciona alguna)

Mensaje: "{mensaje}"

Responde SOLO con JSON en UNA línea, ejemplo: {{"intent":"consultar_asignatura","nombre_asignatura":"Redes"}}
Si no hay asignatura, pon null: {{"intent":"saludo","nombre_asignatura":null}}"""


def interpretar_con_llama(mensaje: str) -> dict:
    prompt = PROMPT_TEMPLATE.format(mensaje=mensaje)

    try:
        result = subprocess.run(
            ["ollama", "run", "llama3"],
            input=prompt,
            text=True,
            capture_output=True,
            timeout=25,
            encoding='utf-8',
            errors='ignore'
        )
    except subprocess.TimeoutExpired:
        print("LLM timeout")
        return {}
    except Exception as e:
        print(f"Error ejecutando Ollama: {e}")
        return {}

    salida = result.stdout.strip()
    salida = limpiar_ansi(salida)

    if not salida:
        print("LLM devolvió respuesta vacía")
        return {}

    print(f"Salida LLM raw: {repr(salida)}")


    try:
        data = json.loads(salida)
        if isinstance(data, dict):
            print("LLM OK (directo):", data)
            return data
    except json.JSONDecodeError:
        pass


    match = re.search(r'\{[^{}]*"intent"[^{}]*\}', salida)
    if not match:
        match = re.search(r'\{.*?\}', salida)

    if not match:
        print("LLM no devolvió JSON válido:")
        print(salida)
        return {}

    json_text = match.group(0)
    print(f"JSON extraído: {repr(json_text)}")

    try:
        data = json.loads(json_text)
        print("LLM OK:", data)

        if not isinstance(data, dict):
            print("LLM devolvió tipo inesperado:", type(data))
            return {}

        return data
    except json.JSONDecodeError as e:
        print(f"Error parseando JSON del LLM: {e}")
        print(f"JSON text: {repr(json_text)}")
        return {}
    except Exception as e:
        print(f"Error inesperado procesando respuesta LLM: {e}")
        return {}
