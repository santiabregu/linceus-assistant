"""
Cliente para Google Gemini API.
Alternativa rápida a Ollama cuando se necesita velocidad (demo, producción).

Usa la SDK `google-genai` (sucesora de `google-generativeai`, que está deprecada).
La SDK nueva es la única que expone `ThinkingConfig`, necesario para desactivar
el "thinking" interno de Gemini 2.5 Flash; con thinking activado los tokens de
razonamiento consumen el presupuesto de `max_output_tokens` y la respuesta al
usuario llega truncada.
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"  # Variante completa: prefill suficiente para prompts grandes (chunks RAG) sin disparar 504 "cancelled before prefill" que veíamos con -lite. Thinking se desactiva explícitamente con thinking_budget=0.
DEFAULT_TIMEOUT = 30

_BENCH_METRICS_PATH = os.getenv("LINCEUS_BENCH_METRICS")


def _log_bench_metric(record: dict) -> None:
    if not _BENCH_METRICS_PATH:
        return
    try:
        with open(_BENCH_METRICS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def llamar_gemini(
    prompt: str,
    modelo: str = GEMINI_MODEL,
    timeout: int = DEFAULT_TIMEOUT,
    options: Optional[Dict[str, Any]] = None,
    context: str = "unknown",
) -> Optional[str]:
    """
    Llama a Gemini API.

    Args:
        prompt: Prompt para el modelo
        modelo: Nombre del modelo
        timeout: Timeout en segundos
        options: Opciones de generación (temperature, num_predict, top_p, top_k)
        context: etiqueta libre que identifica el call site (se usa solo
            cuando `LINCEUS_BENCH_METRICS` está activa)

    Returns:
        Respuesta del modelo o None si hay error
    """

    # Defaults optimizados para generación SQL (JSON corto)
    temperature = 0.0
    max_tokens = 150
    top_p = 0.9
    top_k = 10

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

        client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=timeout * 1000),  # SDK espera ms
        )

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            top_p=top_p,
            top_k=top_k,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )

        t_start = time.perf_counter()
        response = client.models.generate_content(
            model=modelo,
            contents=prompt,
            config=config,
        )
        latencia_ms = int((time.perf_counter() - t_start) * 1000)

        respuesta = (response.text or "").strip()
        print(f"✅ Respuesta recibida ({len(respuesta)} chars)")

        if _BENCH_METRICS_PATH:
            usage = getattr(response, "usage_metadata", None)
            input_tokens = getattr(usage, "prompt_token_count", None) if usage else None
            output_tokens = getattr(usage, "candidates_token_count", None) if usage else None
            total_tokens = getattr(usage, "total_token_count", None) if usage else None
            _log_bench_metric({
                "ts": datetime.now(timezone.utc).isoformat(),
                "modelo": modelo,
                "context": context,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "latencia_ms": latencia_ms,
                "prompt_chars": len(prompt),
                "respuesta_chars": len(respuesta),
                "ok": True,
            })

        return respuesta

    except Exception as e:
        print(f"❌ Error llamando a Gemini: {e}")
        if _BENCH_METRICS_PATH:
            _log_bench_metric({
                "ts": datetime.now(timezone.utc).isoformat(),
                "modelo": modelo,
                "context": context,
                "ok": False,
                "error": str(e)[:200],
            })
        return None


def verificar_gemini_activo() -> bool:
    """Verifica si Gemini está configurado correctamente."""
    try:
        if not GEMINI_API_KEY:
            print("❌ GEMINI_API_KEY no encontrada en .env")
            return False

        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents="Di 'OK'",
            config=types.GenerateContentConfig(
                max_output_tokens=10,
                temperature=0.0,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
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

    if not verificar_gemini_activo():
        print("\n💡 Para usar Gemini:")
        print("   1. Obtén una API key en: https://makersuite.google.com/app/apikey")
        print("   2. Agrégala al archivo .env: GEMINI_API_KEY=tu_key_aqui")
        exit(1)

    print("\n📝 Test 1: Clasificación simple")
    respuesta = llamar_gemini(
        prompt='Clasifica: "cuántos créditos tiene Redes". Responde: {"tipo": "especifica"}',
        timeout=10
    )
    print(f"Respuesta: {respuesta}")

    print("\n⚡ Test 2: Velocidad (debería ser <3s)")
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
