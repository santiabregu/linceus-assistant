"""
Cliente para Google Gemini API.
Alternativa rápida a Ollama cuando se necesita velocidad (demo, producción).
"""

import json
import os
import time
from datetime import datetime, timezone
import google.generativeai as genai
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# Configuración de Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemma-3-27b-it"  # 15K req/día gratis, muy capaz para SQL/JSON
DEFAULT_TIMEOUT = 30  # segundos

# Path donde se vuelcan métricas en modo benchmark. Si la env var
# `LINCEUS_BENCH_METRICS` apunta a un fichero, cada llamada a Gemini añade
# una línea JSONL con tokens + latencia. Si no, no se mide.
_BENCH_METRICS_PATH = os.getenv("LINCEUS_BENCH_METRICS")

# Configurar API key globalmente
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def _log_bench_metric(record: dict) -> None:
    """Append-only log de métricas de Gemini cuando estamos en modo benchmark."""
    if not _BENCH_METRICS_PATH:
        return
    try:
        with open(_BENCH_METRICS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        # No queremos que un fallo de log rompa el bot.
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

    Ventajas vs Ollama local:
    - Mucho más rápido (1-3s vs 30-60s en CPU)
    - No consume recursos locales
    - Modelos más potentes

    Args:
        prompt: Prompt para el modelo
        modelo: Nombre del modelo
        timeout: Timeout en segundos
        options: Opciones de generación
        context: etiqueta libre que identifica el call site (p.ej.
            'profesores.text_to_sql', 'horarios.render'). Solo se usa
            cuando `LINCEUS_BENCH_METRICS` está activa, para agregar
            métricas por componente.

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

        model = genai.GenerativeModel(modelo)

        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            top_p=top_p,
            top_k=top_k,
        )

        t_start = time.perf_counter()
        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            request_options={"timeout": timeout},
        )
        latencia_ms = int((time.perf_counter() - t_start) * 1000)

        respuesta = response.text.strip()
        print(f"✅ Respuesta recibida ({len(respuesta)} chars)")

        # Métricas de benchmark (no-op si LINCEUS_BENCH_METRICS no está)
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
    """
    Verifica si Gemini está configurado correctamente.

    Returns:
        True si la API key está configurada y es válida
    """
    try:
        if not GEMINI_API_KEY:
            print("❌ GEMINI_API_KEY no encontrada en .env")
            return False

        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(
            "Di 'OK'",
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=10,
                temperature=0.0,
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
