"""
Cliente para Ollama usando API HTTP en vez de subprocess.
Mucho más rápido porque el modelo se mantiene cargado en memoria.
"""

import requests
import json
import re
from typing import Dict, Any, Optional


# Configuración de Ollama
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"  # Más rápido en CPU
DEFAULT_TIMEOUT = 120  # segundos (Ollama en CPU es lento)


def limpiar_ansi(texto: str) -> str:
    """Elimina códigos de escape ANSI del texto."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\[\?[0-9;]*[a-zA-Z]|\[K|\[G)')
    return ansi_escape.sub('', texto)


def llamar_ollama(
    prompt: str,
    modelo: str = OLLAMA_MODEL,
    timeout: int = DEFAULT_TIMEOUT,
    stream: bool = False,
    options: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Llama a Ollama usando la API HTTP.

    Ventajas vs subprocess:
    - Modelo se mantiene cargado en memoria
    - 10-20x más rápido (1-3s vs 20-30s)
    - No overhead de proceso

    Args:
        prompt: Prompt para el modelo
        modelo: Nombre del modelo (default: llama3)
        timeout: Timeout en segundos
        stream: Si hacer streaming o no
        options: Opciones personalizadas (sobreescribe defaults)

    Returns:
        Respuesta del modelo o None si hay error
    """

    # Defaults optimizados para generación SQL (JSON corto)
    default_options = {
        "temperature": 0.1,
        "num_predict": 150,
        "num_ctx": 512,
        "top_k": 10,
        "top_p": 0.9
    }

    # Permitir sobreescribir opciones por llamada
    if options:
        default_options.update(options)

    payload = {
        "model": modelo,
        "prompt": prompt,
        "stream": stream,
        "keep_alive": "2h",
        "options": default_options
    }

    try:
        print(f"🤖 Llamando a Ollama API (modelo: {modelo})...")

        response = requests.post(
            OLLAMA_API_URL,
            json=payload,
            timeout=timeout
        )

        if response.status_code != 200:
            print(f"❌ Error HTTP {response.status_code}: {response.text}")
            return None

        # Ollama devuelve NDJSON (múltiples objetos JSON separados por líneas)
        respuesta_completa = ""

        for linea in response.text.strip().split('\n'):
            if linea:
                try:
                    data = json.loads(linea)
                    respuesta_completa += data.get("response", "")

                    # Si es la última línea
                    if data.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue

        respuesta_limpia = limpiar_ansi(respuesta_completa.strip())

        print(f"✅ Respuesta recibida ({len(respuesta_limpia)} chars)")

        return respuesta_limpia

    except requests.exceptions.Timeout:
        print(f"❌ Timeout de Ollama ({timeout}s)")
        return None

    except requests.exceptions.ConnectionError:
        print(f"❌ No se pudo conectar a Ollama. ¿Está corriendo? Ejecuta: ollama serve")
        return None

    except Exception as e:
        print(f"❌ Error llamando a Ollama: {e}")
        return None


def verificar_ollama_activo() -> bool:
    """
    Verifica si Ollama está corriendo y el modelo está disponible.

    Returns:
        True si Ollama está activo y responde
    """
    try:
        # Endpoint de health check
        response = requests.get("http://localhost:11434/api/tags", timeout=5)

        if response.status_code == 200:
            modelos = response.json().get("models", [])
            modelo_disponible = any(m.get("name", "").startswith(OLLAMA_MODEL) for m in modelos)

            if modelo_disponible:
                print(f"✅ Ollama activo con modelo {OLLAMA_MODEL}")
                return True
            else:
                print(f"⚠️ Ollama activo pero modelo {OLLAMA_MODEL} no encontrado")
                print(f"   Modelos disponibles: {[m.get('name') for m in modelos]}")
                return False

        return False

    except:
        print("❌ Ollama no está corriendo. Ejecuta: ollama serve")
        return False


def precargar_modelo(modelo: str = OLLAMA_MODEL):
    """
    Pre-carga el modelo en memoria para acelerar futuras llamadas.

    Args:
        modelo: Nombre del modelo a pre-cargar
    """
    print(f"🔄 Pre-cargando modelo {modelo}...")

    # Hacer una llamada simple para forzar la carga del modelo
    respuesta = llamar_ollama(
        prompt="Hola",
        modelo=modelo,
        timeout=60  # Primera carga puede tardar más
    )

    if respuesta:
        print(f"✅ Modelo {modelo} pre-cargado y listo")
    else:
        print(f"⚠️ No se pudo pre-cargar el modelo")


# Test del módulo
if __name__ == "__main__":
    print("🧪 Testing Ollama Client\n")

    # 1. Verificar que Ollama está activo
    if not verificar_ollama_activo():
        print("\n💡 Para iniciar Ollama, ejecuta en otra terminal:")
        print("   ollama serve")
        exit(1)

    # 2. Pre-cargar modelo
    precargar_modelo()

    # 3. Test simple
    print("\n📝 Test 1: Clasificación simple")
    respuesta = llamar_ollama(
        prompt='Clasifica: "cuántos créditos tiene Redes". Responde: {"tipo": "especifica"}',
        timeout=10
    )
    print(f"Respuesta: {respuesta}")

    # 4. Test de velocidad
    print("\n⚡ Test 2: Velocidad (debería ser <3s)")
    import time
    inicio = time.time()
    respuesta = llamar_ollama(
        prompt="Di 'OK'",
        timeout=5
    )
    duracion = time.time() - inicio
    print(f"Respuesta: {respuesta}")
    print(f"Duración: {duracion:.2f}s")

    if duracion < 3:
        print("✅ Velocidad óptima!")
    else:
        print("⚠️ Más lento de lo esperado")
