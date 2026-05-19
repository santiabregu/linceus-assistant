"""
Cliente para Google Gemini API vía REST directo con `requests`.

No usamos ningún SDK oficial porque tanto `google-generativeai` (deprecado, sin
`thinking_config`) como `google-genai` (sucesor, con `thinking_config`) chocan
con dependencias del proyecto: `google-genai` exige `httpx>=0.28` y
`websockets>=13`, mientras que `supabase 2.3.0` exige `httpx<0.25` y
`rasa-sdk 3.6.2` exige `websockets<11`. Pegar a REST evita esos conflictos y
nos permite pasar `thinkingConfig.thinkingBudget=0` para que Gemini 2.5 Flash
no consuma `maxOutputTokens` en su razonamiento interno (lo que truncaba las
respuestas RAG).
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Modelo principal: familia Gemini 3.5, sin CoT leak con thinking_budget=0.
# Calidad superior a 2.5 Flash Lite en respuestas RAG; mismo precio o cercano.
GEMINI_MODEL = "gemini-3.5-flash"
# Fallback automático ante errores transitorios del principal (5xx, timeout,
# rate limit). Mismo proveedor, sin CoT, estable, barato. Se descarta usar
# Gemma 4 como fallback porque su CoT es estructural y no se suprime de forma
# fiable (Google admite que estos modelos emiten thinking incluso con flags
# de desactivación).
GEMINI_FALLBACK_MODEL = "gemini-2.5-flash-lite"
DEFAULT_TIMEOUT = 30
_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

_BENCH_METRICS_PATH = os.getenv("LINCEUS_BENCH_METRICS")


def _log_bench_metric(record: dict) -> None:
    if not _BENCH_METRICS_PATH:
        return
    try:
        with open(_BENCH_METRICS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _invocar_modelo(
    prompt: str,
    modelo: str,
    timeout: int,
    temperature: float,
    max_tokens: int,
    top_p: float,
    top_k: int,
    context: str,
) -> Optional[str]:
    """Una llamada HTTP a un modelo concreto. Devuelve texto o None si falla."""
    url = f"{_API_BASE}/{modelo}:generateContent"
    generation_config = {
        "temperature": temperature,
        "maxOutputTokens": max_tokens,
        "topP": top_p,
        "topK": top_k,
    }
    # thinkingConfig sólo lo aceptan los modelos Gemini 2.5+; Gemma 4 y anteriores
    # responden HTTP 400 si se lo pasamos, así que lo condicionamos por familia.
    if modelo.startswith("gemini-2.5") or modelo.startswith("gemini-3"):
        generation_config["thinkingConfig"] = {"thinkingBudget": 0}

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": generation_config,
    }

    try:
        print(f"🤖 Llamando a Gemini API (modelo: {modelo})...")
        t_start = time.perf_counter()
        resp = requests.post(
            url,
            params={"key": GEMINI_API_KEY},
            json=body,
            timeout=timeout,
        )
        latencia_ms = int((time.perf_counter() - t_start) * 1000)

        if resp.status_code != 200:
            print(f"❌ Error llamando a Gemini: HTTP {resp.status_code} {resp.text[:300]}")
            if _BENCH_METRICS_PATH:
                _log_bench_metric({
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "modelo": modelo,
                    "context": context,
                    "ok": False,
                    "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                })
            return None

        data = resp.json()
        candidates = data.get("candidates") or []
        if not candidates:
            print(f"❌ Gemini devolvió sin candidates: {data.get('promptFeedback')}")
            return None

        parts = (candidates[0].get("content") or {}).get("parts") or []
        respuesta = "".join(p.get("text", "") for p in parts).strip()
        print(f"✅ Respuesta recibida ({len(respuesta)} chars)")

        if _BENCH_METRICS_PATH:
            usage = data.get("usageMetadata") or {}
            _log_bench_metric({
                "ts": datetime.now(timezone.utc).isoformat(),
                "modelo": modelo,
                "context": context,
                "input_tokens": usage.get("promptTokenCount"),
                "output_tokens": usage.get("candidatesTokenCount"),
                "total_tokens": usage.get("totalTokenCount"),
                "latencia_ms": latencia_ms,
                "prompt_chars": len(prompt),
                "respuesta_chars": len(respuesta),
                "ok": True,
            })

        return respuesta or None

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


def llamar_gemini(
    prompt: str,
    modelo: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
    options: Optional[Dict[str, Any]] = None,
    context: str = "unknown",
) -> Optional[str]:
    """
    Llama a Gemini API vía REST. Si el modelo principal falla (HTTP 5xx,
    timeout, rate limit, respuesta vacía), reintenta una sola vez con
    GEMINI_FALLBACK_MODEL para no devolver None al usuario por un fallo
    transitorio del proveedor.

    Args:
        prompt: Prompt para el modelo
        modelo: Nombre del modelo (si se pasa explícito, NO se usa fallback)
        timeout: Timeout en segundos
        options: Opciones de generación (temperature, num_predict, top_p, top_k)
        context: etiqueta libre que identifica el call site (sólo se usa cuando
            `LINCEUS_BENCH_METRICS` está activa)

    Returns:
        Texto generado por el modelo, o None si ambos (principal y fallback) fallan.
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

    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY no encontrada en .env")
        return None

    caller_pidio_modelo = modelo is not None
    modelo_efectivo = modelo or GEMINI_MODEL

    respuesta = _invocar_modelo(
        prompt, modelo_efectivo, timeout, temperature, max_tokens, top_p, top_k, context,
    )
    if respuesta is not None:
        return respuesta

    # Fallback automático SOLO si el caller no pidió un modelo concreto
    # (si lo pidió, respetamos su decisión y no le sustituimos sin avisar).
    if not caller_pidio_modelo and GEMINI_FALLBACK_MODEL != modelo_efectivo:
        print(f"↩  Reintentando con modelo de fallback: {GEMINI_FALLBACK_MODEL}")
        return _invocar_modelo(
            prompt, GEMINI_FALLBACK_MODEL, timeout, temperature,
            max_tokens, top_p, top_k, f"{context}__fallback",
        )

    return None


def verificar_gemini_activo() -> bool:
    """Verifica si Gemini está configurado correctamente."""
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY no encontrada en .env")
        return False
    respuesta = llamar_gemini("Di 'OK'", timeout=10, options={"num_predict": 10})
    if respuesta:
        print(f"✅ Gemini activo y respondiendo (modelo: {GEMINI_MODEL})")
        return True
    return False


# Test del módulo
if __name__ == "__main__":
    print("🧪 Testing Gemini Client (REST directo)\n")

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
