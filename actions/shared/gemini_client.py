"""
Cliente para Google Gemini API.
Alternativa rápida a Ollama cuando se necesita velocidad (demo, producción).
"""

import os
from google import genai
from google.genai import types
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# Configuración de Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemma-3-27b-it"  # 15K req/día gratis, muy capaz para SQL/JSON
DEFAULT_TIMEOUT = 30  # segundos


def llamar_gemini(
    prompt: str,
    modelo: str = GEMINI_MODEL,
    timeout: int = DEFAULT_TIMEOUT,
    options: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Llama a Gemini API.

    Ventajas vs Ollama local:
    - Mucho más rápido (1-3s vs 30-60s en CPU)
    - No consume recursos locales
    - Modelos más potentes

    Args:
        prompt: Prompt para el modelo
        modelo: Nombre del modelo
        timeout: Timeout en segundos
        options: Opciones de generación

    Returns:
        Respuesta del modelo o None si hay error
    """

    # Defaults optimizados para generación SQL (JSON corto)
    temperature = 0.0
    max_tokens = 150
    top_p = 0.9
    top_k = 10

    # Permitir sobreescribir opciones
    if options:
        if "temperature" in options:
            temperature = options["temperature"]
        if "num_predict" in options:
            max_tokens = options["num_predict"]
        if "top_p" in options:
            top_p = options["top_p"]
        if "top_k" in options:
            top_k = options["top_k"]

    try:
        print(f"🤖 Llamando a Gemini API (modelo: {modelo})...")

        # Crear cliente con API key
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Generar contenido
        response = client.models.generate_content(
            model=modelo,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                top_p=top_p,
                top_k=top_k
            )
        )

        respuesta = response.text.strip()
        print(f"✅ Respuesta recibida ({len(respuesta)} chars)")

        return respuesta

    except Exception as e:
        print(f"❌ Error llamando a Gemini: {e}")
        return None


def verificar_gemini_activo() -> bool:
    """
    Verifica si Gemini está configurado correctamente.

    Returns:
        True si la API key está configurada y es válida
    """
    try:
        if not GEMINI_API_KEY:
            print("❌ GEMINI_API_KEY no encontrada en .env")
            return False

        # Test simple
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents="Di 'OK'",
            config=types.GenerateContentConfig(
                max_output_tokens=10,
                temperature=0.0
            )
        )
        
        if response.text:
            print(f"✅ Gemini activo y respondiendo (modelo: {GEMINI_MODEL})")
            return True
        
        return False

    except Exception as e:
        print(f"❌ Error verificando Gemini: {e}")
        return False


# Test del módulo
if __name__ == "__main__":
    print("🧪 Testing Gemini Client\n")

    # 1. Verificar que Gemini está activo
    if not verificar_gemini_activo():
        print("\n💡 Para usar Gemini:")
        print("   1. Obtén una API key en: https://makersuite.google.com/app/apikey")
        print("   2. Agrégala al archivo .env: GEMINI_API_KEY=tu_key_aqui")
        exit(1)

    # 2. Test simple
    print("\n📝 Test 1: Clasificación simple")
    respuesta = llamar_gemini(
        prompt='Clasifica: "cuántos créditos tiene Redes". Responde: {"tipo": "especifica"}',
        timeout=10
    )
    print(f"Respuesta: {respuesta}")

    # 3. Test de velocidad
    print("\n⚡ Test 2: Velocidad (debería ser <3s)")
    import time
    inicio = time.time()
    respuesta = llamar_gemini(
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
