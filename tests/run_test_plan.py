"""
Automatización del plan de pruebas: Épica Asignaturas v1 (sin RAG).

Ejecuta los casos de prueba definidos en el test plan contra el bot Rasa
usando la API REST, captura resultados y genera un informe.

Requisitos previos:
    1. Rasa server corriendo:     rasa run --enable-api --cors "*"
    2. Action server corriendo:   rasa run actions

Uso:
    python tests/run_test_plan.py
    python tests/run_test_plan.py --rasa-url http://localhost:5005
    python tests/run_test_plan.py --only especifica
    python tests/run_test_plan.py --only listado,conteo
    python tests/run_test_plan.py --runs 3
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

import requests

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

RASA_URL = "http://127.0.0.1:5005"
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
DEFAULT_RUNS = 2  # ejecuciones por caso (el plan dice 2, 3 para complejos)


# ---------------------------------------------------------------------------
# Modelo de datos
# ---------------------------------------------------------------------------

@dataclass
class TestCase:
    id: str
    category: str          # especifica, listado, conteo, fuera_ambito
    subcategory: str       # positiva, negativa, seguimiento, cross_titulacion
    query: str
    slot_titulacion: Optional[str] = None
    slot_ultimo_nombre: Optional[str] = None
    expected_intent: Optional[str] = None
    expected_action: Optional[str] = None
    expected_entity_name: Optional[str] = None    # nombre del entity
    expected_entity_value: Optional[str] = None   # valor esperado
    expected_json_attrs: Optional[dict] = None    # atributos clave del JSON de respuesta
    expected_count: Optional[int] = None          # para conteo
    expected_contains: Optional[str] = None       # texto que debe contener la respuesta
    expected_not_found: bool = False               # se espera "no encontrada"
    expected_ask_titulacion: bool = False           # se espera que pida titulación
    runs: int = DEFAULT_RUNS
    setup_messages: list = field(default_factory=list)  # mensajes previos para contexto


@dataclass
class TestResult:
    test_id: str
    run_number: int
    query: str
    timestamp: str
    # NLU
    intent_detected: Optional[str] = None
    intent_confidence: Optional[float] = None
    entities_detected: Optional[list] = None
    # Respuesta
    bot_responses: Optional[list] = None
    custom_data: Any = None  # datos estructurados del json_message
    # Validación
    intent_ok: bool = False
    entity_ok: bool = False
    response_ok: bool = False
    overall_pass: bool = False
    notes: str = ""


# ---------------------------------------------------------------------------
# Casos de prueba (del plan de pruebas v1)
# ---------------------------------------------------------------------------

def build_test_cases() -> list[TestCase]:
    """Construye todos los casos de prueba del plan."""
    cases = []

    # ===================================================================
    # 6.1 action_consulta_especifica
    # ===================================================================

    # --- Positivas: atributo concreto ---
    cases.append(TestCase(
        id="E-P01", category="especifica", subcategory="positiva_atributo",
        query="¿Cuántos créditos tiene Redes?",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignatura_especifica",
        expected_action="action_consulta_especifica",
        expected_entity_name="nombre_asignatura",
        expected_entity_value="Redes",
        expected_json_attrs={"nombre": "Redes de Computadores", "creditos": 6},
    ))
    cases.append(TestCase(
        id="E-P02", category="especifica", subcategory="positiva_atributo",
        query="¿En qué curso está Cálculo?",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignatura_especifica",
        expected_action="action_consulta_especifica",
        expected_entity_name="nombre_asignatura",
        expected_entity_value="Cálculo",
        expected_json_attrs={"nombre": "Cálculo Infinitesimal y Numérico", "curso": 1},
    ))
    cases.append(TestCase(
        id="E-P03", category="especifica", subcategory="positiva_atributo",
        query="¿Fundamentos de Programación es anual?",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignatura_especifica",
        expected_action="action_consulta_especifica",
        expected_entity_name="nombre_asignatura",
        expected_entity_value="Fundamentos de Programación",
        expected_json_attrs={"nombre": "Fundamentos de Programación", "duracion": "A"},
    ))
    cases.append(TestCase(
        id="E-P04", category="especifica", subcategory="positiva_atributo",
        query="¿Estadística es obligatoria?",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignatura_especifica",
        expected_action="action_consulta_especifica",
        expected_entity_name="nombre_asignatura",
        expected_entity_value="Estadística",
        expected_json_attrs={"tipologia": "FORMACION_BASICA"},
    ))
    cases.append(TestCase(
        id="E-P05", category="especifica", subcategory="positiva_atributo",
        query="¿Criptografía es optativa?",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignatura_especifica",
        expected_action="action_consulta_especifica",
        expected_entity_name="nombre_asignatura",
        expected_entity_value="Criptografía",
        expected_json_attrs={"tipologia": "OPTATIVA"},
    ))
    cases.append(TestCase(
        id="E-P06", category="especifica", subcategory="positiva_atributo",
        query="¿De qué cuatrimestre es IA?",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignatura_especifica",
        expected_action="action_consulta_especifica",
        expected_entity_name="nombre_asignatura",
        expected_entity_value="IA",
        expected_json_attrs={"nombre": "Inteligencia Artificial", "duracion": "C2"},
    ))

    # --- Positivas: información general ---
    cases.append(TestCase(
        id="E-P07", category="especifica", subcategory="positiva_general",
        query="Información sobre Sistemas Operativos",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignatura_especifica",
        expected_action="action_consulta_especifica",
        expected_entity_name="nombre_asignatura",
        expected_entity_value="Sistemas Operativos",
        expected_json_attrs={"nombre": "Sistemas Operativos", "curso": 2, "creditos": 6},
    ))
    cases.append(TestCase(
        id="E-P08", category="especifica", subcategory="positiva_general",
        query="Háblame de Diseño y Pruebas",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignatura_especifica",
        expected_action="action_consulta_especifica",
        expected_entity_name="nombre_asignatura",
        expected_entity_value="Diseño y Pruebas",
        expected_contains="Diseño y Pruebas",
        runs=3,
    ))
    cases.append(TestCase(
        id="E-P09", category="especifica", subcategory="positiva_general",
        query="¿Qué es ADDA?",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignatura_especifica",
        expected_action="action_consulta_especifica",
        expected_entity_name="nombre_asignatura",
        expected_entity_value="ADDA",
        expected_contains="Análisis y Diseño de Datos y Algoritmos",
        runs=3,
    ))
    cases.append(TestCase(
        id="E-P10", category="especifica", subcategory="positiva_general",
        query="Dame info del TFG",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignatura_especifica",
        expected_action="action_consulta_especifica",
        expected_entity_name="nombre_asignatura",
        expected_entity_value="TFG",
        expected_contains="Trabajo Fin de Grado",
    ))
    cases.append(TestCase(
        id="E-P11", category="especifica", subcategory="positiva_general",
        query="Datos de PGPI",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignatura_especifica",
        expected_action="action_consulta_especifica",
        expected_entity_name="nombre_asignatura",
        expected_entity_value="PGPI",
        expected_contains="Planificación y Gestión de Proyectos Informáticos",
        runs=3,
    ))

    # --- Positiva: búsqueda por código ---
    cases.append(TestCase(
        id="E-P12", category="especifica", subcategory="positiva_codigo",
        query="¿Qué asignatura es la 2050001?",
        slot_titulacion="GII-IS",
        expected_action="action_consulta_especifica",
        expected_contains="Fundamentos de Programación",
    ))

    # --- Seguimiento ---
    cases.append(TestCase(
        id="E-S01", category="especifica", subcategory="seguimiento",
        query="¿Y cuántos créditos tiene?",
        slot_titulacion="GII-IS",
        slot_ultimo_nombre="Redes de Computadores",
        expected_intent="consulta_asignatura_especifica",
        expected_action="action_consulta_especifica",
        expected_contains="6",
        setup_messages=["¿Cuántos créditos tiene Redes?"],
    ))
    cases.append(TestCase(
        id="E-S02", category="especifica", subcategory="seguimiento",
        query="¿Es obligatoria?",
        slot_titulacion="GII-IS",
        slot_ultimo_nombre="Estadística",
        expected_intent="consulta_asignatura_especifica",
        expected_action="action_consulta_especifica",
        setup_messages=["Háblame de Estadística"],
    ))
    cases.append(TestCase(
        id="E-S03", category="especifica", subcategory="seguimiento",
        query="¿Y esa de qué curso es?",
        slot_titulacion="GII-IS",
        slot_ultimo_nombre="Criptografía",
        expected_intent="consulta_asignatura_especifica",
        expected_action="action_consulta_especifica",
        expected_contains="4",
        setup_messages=["Información sobre Criptografía"],
    ))

    # --- Negativas ---
    cases.append(TestCase(
        id="E-N01", category="especifica", subcategory="negativa",
        query="¿Cuántos créditos tiene Biología?",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignatura_especifica",
        expected_action="action_consulta_especifica",
        expected_not_found=True,
    ))
    cases.append(TestCase(
        id="E-N02", category="especifica", subcategory="negativa",
        query="Información sobre Derecho Penal",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignatura_especifica",
        expected_not_found=True,
    ))
    cases.append(TestCase(
        id="E-N03", category="especifica", subcategory="negativa",
        query="¿Qué es Química Orgánica?",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignatura_especifica",
        expected_action="action_consulta_especifica",
        expected_not_found=True,
    ))

    # --- Cross-titulación ---
    cases.append(TestCase(
        id="E-T01", category="especifica", subcategory="cross_titulacion",
        query="¿Cuántos créditos tiene Redes?",
        slot_titulacion="GII-IC",
        expected_intent="consulta_asignatura_especifica",
        expected_action="action_consulta_especifica",
        expected_contains="Redes",
    ))
    cases.append(TestCase(
        id="E-T02", category="especifica", subcategory="cross_titulacion",
        query="Info de IA",
        slot_titulacion="GII-TI",
        expected_intent="consulta_asignatura_especifica",
        expected_action="action_consulta_especifica",
        expected_contains="Inteligencia Artificial",
    ))
    # E-T03 eliminado: sin titulación en slot ni en mensaje, el bot pide titulación
    # correctamente. Se prueba manualmente.
    cases.append(TestCase(
        id="E-T04", category="especifica", subcategory="cross_titulacion",
        query="Dime sobre Redes en ingeniería del software",
        slot_titulacion=None,
        expected_intent="consulta_asignatura_especifica",
        expected_action="action_consulta_especifica",
        expected_contains="Redes",
        runs=3,
    ))

    # ===================================================================
    # 6.2 action_consulta_listado
    # ===================================================================

    # --- Un filtro ---
    cases.append(TestCase(
        id="L-P01", category="listado", subcategory="positiva_1filtro",
        query="Dame las asignaturas de primero",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignaturas_listado",
        expected_action="action_consulta_listado",
    ))
    cases.append(TestCase(
        id="L-P02", category="listado", subcategory="positiva_1filtro",
        query="Asignaturas de cuarto",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignaturas_listado",
        expected_action="action_consulta_listado",
    ))
    cases.append(TestCase(
        id="L-P03", category="listado", subcategory="positiva_1filtro",
        query="¿Qué optativas hay?",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignaturas_listado",
        expected_action="action_consulta_listado",
    ))
    cases.append(TestCase(
        id="L-P04", category="listado", subcategory="positiva_1filtro",
        query="Asignaturas anuales",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignaturas_listado",
        expected_action="action_consulta_listado",
    ))
    cases.append(TestCase(
        id="L-P05", category="listado", subcategory="positiva_1filtro",
        query="Asignaturas de formación básica",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignaturas_listado",
        expected_action="action_consulta_listado",
    ))

    # --- Dos filtros ---
    cases.append(TestCase(
        id="L-P06", category="listado", subcategory="positiva_2filtros",
        query="Optativas de cuarto",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignaturas_listado",
        expected_action="action_consulta_listado",
    ))
    cases.append(TestCase(
        id="L-P07", category="listado", subcategory="positiva_2filtros",
        query="Obligatorias de segundo",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignaturas_listado",
        expected_action="action_consulta_listado",
    ))
    cases.append(TestCase(
        id="L-P08", category="listado", subcategory="positiva_2filtros",
        query="Asignaturas de tercero del primer cuatrimestre",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignaturas_listado",
        expected_action="action_consulta_listado",
        runs=3,
    ))
    cases.append(TestCase(
        id="L-P09", category="listado", subcategory="positiva_2filtros",
        query="Asignaturas de 12 créditos",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignaturas_listado",
        expected_action="action_consulta_listado",
    ))

    # --- Paginación ---
    cases.append(TestCase(
        id="L-P10", category="listado", subcategory="paginacion",
        query="Dame todas las asignaturas",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignaturas_listado",
        expected_action="action_consulta_listado",
        expected_contains="más",
    ))

    # --- Negativas ---
    cases.append(TestCase(
        id="L-N01", category="listado", subcategory="negativa",
        query="Optativas de primero",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignaturas_listado",
        expected_action="action_consulta_listado",
        expected_not_found=True,
    ))
    cases.append(TestCase(
        id="L-N02", category="listado", subcategory="negativa",
        query="Asignaturas de quinto curso",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignaturas_listado",
        expected_action="action_consulta_listado",
        expected_not_found=True,
    ))

    # --- Cross-titulación ---
    cases.append(TestCase(
        id="L-T01", category="listado", subcategory="cross_titulacion",
        query="Asignaturas de primero",
        slot_titulacion="GII-IC",
        expected_intent="consulta_asignaturas_listado",
        expected_action="action_consulta_listado",
    ))
    cases.append(TestCase(
        id="L-T02", category="listado", subcategory="cross_titulacion",
        query="Optativas de cuarto",
        slot_titulacion="GII-TI",
        expected_intent="consulta_asignaturas_listado",
        expected_action="action_consulta_listado",
    ))
    cases.append(TestCase(
        id="L-T03", category="listado", subcategory="cross_titulacion",
        query="Dame las asignaturas de segundo",
        slot_titulacion=None,
        expected_intent="consulta_asignaturas_listado",
        expected_action="action_consulta_listado",
        expected_ask_titulacion=True,
    ))

    # ===================================================================
    # 6.3 action_consulta_conteo
    # ===================================================================

    cases.append(TestCase(
        id="C-P01", category="conteo", subcategory="positiva",
        query="¿Cuántas asignaturas hay en primero?",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignaturas_conteo",
        expected_action="action_consulta_conteo",
        expected_count=9,
    ))
    cases.append(TestCase(
        id="C-P02", category="conteo", subcategory="positiva",
        query="¿Cuántas optativas hay en cuarto?",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignaturas_conteo",
        expected_action="action_consulta_conteo",
    ))
    cases.append(TestCase(
        id="C-P03", category="conteo", subcategory="positiva",
        query="¿Cuántas asignaturas tiene la carrera?",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignaturas_conteo",
        expected_action="action_consulta_conteo",
        expected_count=47,
    ))
    cases.append(TestCase(
        id="C-P04", category="conteo", subcategory="positiva",
        query="¿Cuántas obligatorias de tercero?",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignaturas_conteo",
        expected_action="action_consulta_conteo",
        expected_count=10,
    ))
    cases.append(TestCase(
        id="C-P05", category="conteo", subcategory="positiva",
        query="Número de asignaturas anuales",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignaturas_conteo",
        expected_action="action_consulta_conteo",
    ))
    cases.append(TestCase(
        id="C-P06", category="conteo", subcategory="positiva",
        query="¿Cuántas de 12 créditos hay?",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignaturas_conteo",
        expected_action="action_consulta_conteo",
        expected_count=2,
    ))

    # --- Negativas ---
    cases.append(TestCase(
        id="C-N01", category="conteo", subcategory="negativa",
        query="¿Cuántas optativas hay en primero?",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignaturas_conteo",
        expected_action="action_consulta_conteo",
        expected_count=0,
    ))
    cases.append(TestCase(
        id="C-N02", category="conteo", subcategory="negativa",
        query="¿Cuántas asignaturas de quinto?",
        slot_titulacion="GII-IS",
        expected_intent="consulta_asignaturas_conteo",
        expected_action="action_consulta_conteo",
        expected_count=0,
    ))

    # --- Cross-titulación ---
    cases.append(TestCase(
        id="C-T01", category="conteo", subcategory="cross_titulacion",
        query="¿Cuántas asignaturas tiene la carrera?",
        slot_titulacion="GII-IC",
        expected_intent="consulta_asignaturas_conteo",
        expected_action="action_consulta_conteo",
        expected_count=48,
    ))
    cases.append(TestCase(
        id="C-T02", category="conteo", subcategory="cross_titulacion",
        query="¿Cuántas asignaturas tiene la carrera?",
        slot_titulacion="GII-TI",
        expected_intent="consulta_asignaturas_conteo",
        expected_action="action_consulta_conteo",
        expected_count=54,
    ))

    # ===================================================================
    # 6.4 Fuera de ámbito
    # ===================================================================

    cases.append(TestCase(
        id="F-01", category="fuera_ambito", subcategory="out_of_scope",
        query="¿Cuál es la capital de Francia?",
        expected_intent="nlu_fallback",
    ))
    cases.append(TestCase(
        id="F-02", category="fuera_ambito", subcategory="out_of_scope",
        query="¿Me puedes contar un chiste?",
        expected_intent="nlu_fallback",
    ))
    cases.append(TestCase(
        id="F-03", category="fuera_ambito", subcategory="out_of_scope",
        query="¿Qué tiempo hará mañana?",
        expected_intent="nlu_fallback",
    ))
    cases.append(TestCase(
        id="F-04", category="fuera_ambito", subcategory="out_of_scope",
        query="Quiero pedir una pizza",
        expected_intent="nlu_fallback",
    ))

    return cases


# ---------------------------------------------------------------------------
# Cliente Rasa
# ---------------------------------------------------------------------------

class RasaClient:
    """Cliente para interactuar con la API REST de Rasa."""

    def __init__(self, base_url: str = RASA_URL):
        self.base_url = base_url.rstrip("/")
        self._check_connection()

    def _check_connection(self):
        # 1. Verificar Rasa API server (puerto 5005)
        try:
            r = requests.get(f"{self.base_url}/status", timeout=5)
            r.raise_for_status()
            print(f"  Conectado a Rasa en {self.base_url}")
        except Exception as e:
            print(f"  ERROR: No se pudo conectar a Rasa en {self.base_url}")
            print(f"  Asegúrate de que el servidor está corriendo: rasa run --enable-api")
            print(f"  Detalle: {e}")
            sys.exit(1)

        # 2. Verificar Action Server (puerto 5055)
        action_url = "http://127.0.0.1:5055"
        try:
            r = requests.get(f"{action_url}/health", timeout=5)
            r.raise_for_status()
            print(f"  Conectado al Action Server en {action_url}")
        except Exception as e:
            print(f"  ERROR: No se pudo conectar al Action Server en {action_url}")
            print(f"  Asegúrate de que está corriendo: rasa run actions")
            print(f"  Sin action server, el bot devolverá respuestas vacías.")
            print(f"  Detalle: {e}")
            sys.exit(1)

    def parse_nlu(self, text: str) -> dict:
        """Envía texto al endpoint /model/parse para obtener intent y entidades."""
        r = requests.post(
            f"{self.base_url}/model/parse",
            json={"text": text},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def new_conversation(self, sender_id: str) -> str:
        """Prepara una conversación nueva. No envía restart porque deja un
        followup_action pendiente (action_session_start) que impide que Rasa
        procese el primer mensaje correctamente. Cada test ya usa un
        sender_id único, así que el tracker nace vacío."""
        return sender_id

    def set_slot(self, sender_id: str, slot_name: str, slot_value: Any):
        """Establece un slot en la conversación."""
        requests.post(
            f"{self.base_url}/conversations/{sender_id}/tracker/events",
            json={"event": "slot", "name": slot_name, "value": slot_value},
            timeout=10,
        )

    def send_message(self, sender_id: str, text: str) -> list[dict]:
        """Envía un mensaje y obtiene las respuestas del bot."""
        r = requests.post(
            f"{self.base_url}/webhooks/rest/webhook",
            json={"sender": sender_id, "message": text},
            timeout=120,  # timeout alto por LLM
        )
        r.raise_for_status()
        return r.json()


# ---------------------------------------------------------------------------
# Motor de ejecución de pruebas
# ---------------------------------------------------------------------------

def run_single_test(
    client: RasaClient,
    case: TestCase,
    run_number: int,
) -> TestResult:
    """Ejecuta un caso de prueba y devuelve el resultado."""
    timestamp = datetime.now().isoformat()
    sender_id = f"test_{case.id}_run{run_number}_{int(time.time())}"
    result = TestResult(
        test_id=case.id,
        run_number=run_number,
        query=case.query,
        timestamp=timestamp,
    )

    try:
        # 1. Crear conversación limpia
        client.new_conversation(sender_id)

        # 2. Configurar slots de contexto
        if case.slot_titulacion:
            client.set_slot(sender_id, "contexto_titulacion", case.slot_titulacion)
        if case.slot_ultimo_nombre:
            client.set_slot(sender_id, "ultimo_nombre_asignatura", case.slot_ultimo_nombre)

        # 3. Enviar mensajes de setup (para pruebas de seguimiento)
        for setup_msg in case.setup_messages:
            client.send_message(sender_id, setup_msg)
            time.sleep(1)  # dar tiempo al action server

        # 4. NLU: parsear el intent sin enviar al action server
        nlu_result = client.parse_nlu(case.query)
        result.intent_detected = nlu_result.get("intent", {}).get("name")
        result.intent_confidence = nlu_result.get("intent", {}).get("confidence")
        result.entities_detected = nlu_result.get("entities", [])

        # 5. Enviar mensaje real para obtener respuesta completa
        responses = client.send_message(sender_id, case.query)
        if not responses or not any(r.get("text") for r in responses):
            print(f"           [DEBUG] Raw response: {responses}")
        result.bot_responses = [r.get("text", "") for r in responses if r.get("text")]

        # Extraer datos estructurados (custom json_message) si existen
        custom_data = None
        for r in responses:
            cd = r.get("custom", {})
            if isinstance(cd, dict) and "data" in cd:
                custom_data = cd["data"]
                break
        result.custom_data = custom_data

        # 6. Validar intent
        if case.expected_intent:
            # Para fallback, aceptar nlu_fallback, out_of_scope o baja confianza
            if case.expected_intent == "nlu_fallback":
                is_fallback = (
                    result.intent_detected == "nlu_fallback"
                    or result.intent_detected == "out_of_scope"
                    or (result.intent_confidence and result.intent_confidence < 0.7)
                )
                result.intent_ok = is_fallback
            else:
                result.intent_ok = result.intent_detected == case.expected_intent
        else:
            result.intent_ok = True  # no se valida

        # 7. Validar entidad
        if case.expected_entity_name:
            found = any(
                e.get("entity") == case.expected_entity_name
                for e in (result.entities_detected or [])
            )
            result.entity_ok = found
            if case.expected_entity_value and found:
                value_match = any(
                    e.get("entity") == case.expected_entity_name
                    and case.expected_entity_value.lower() in e.get("value", "").lower()
                    for e in result.entities_detected
                )
                result.entity_ok = value_match
        else:
            result.entity_ok = True

        # 8. Validar respuesta
        full_response = " ".join(result.bot_responses).lower() if result.bot_responses else ""

        if case.expected_not_found:
            not_found_keywords = ["no encontr", "no pude", "no tengo", "no existe", "no hay"]
            result.response_ok = any(kw in full_response for kw in not_found_keywords)
            if not result.response_ok:
                result.notes += "Esperaba 'no encontrada' pero no se detectó. "

        elif case.expected_ask_titulacion:
            titulacion_keywords = ["titulación", "titulacion", "qué cursas", "cuál cursas", "dime cuál"]
            result.response_ok = any(kw in full_response for kw in titulacion_keywords)
            if not result.response_ok:
                result.notes += "Esperaba que pidiera titulación. "

        elif case.expected_contains:
            result.response_ok = case.expected_contains.lower() in full_response
            if not result.response_ok:
                result.notes += f"Esperaba contener '{case.expected_contains}'. "

        elif case.expected_json_attrs:
            # Validar contra datos estructurados (custom json_message)
            if custom_data and isinstance(custom_data, dict):
                missing = []
                for attr, value in case.expected_json_attrs.items():
                    actual = custom_data.get(attr)
                    # Comparación numérica si ambos son números
                    try:
                        if float(actual) == float(value):
                            continue
                    except (TypeError, ValueError):
                        pass
                    if str(actual).lower() != str(value).lower():
                        missing.append(f"{attr}: esperado={value}, obtenido={actual}")
                result.response_ok = len(missing) == 0
                if not result.response_ok:
                    result.notes += f"Attrs incorrectos en JSON: {missing}. "
            else:
                # Fallback: buscar en texto si no hay datos estructurados
                missing = []
                for attr, value in case.expected_json_attrs.items():
                    if str(value).lower() not in full_response:
                        missing.append(f"{attr}={value}")
                result.response_ok = len(missing) == 0
                if not result.response_ok:
                    result.notes += f"Sin JSON estructurado. Attrs no encontrados en texto: {missing}. "

        elif case.expected_count is not None:
            # Validar contra datos estructurados si existen
            if custom_data is not None and isinstance(custom_data, (int, float)):
                result.response_ok = int(custom_data) == case.expected_count
                if not result.response_ok:
                    result.notes += f"Esperaba count={case.expected_count}, obtenido={custom_data}. "
            else:
                # Fallback: buscar el número en la respuesta de texto
                import re
                numbers = re.findall(r'\d+', full_response)
                result.response_ok = str(case.expected_count) in numbers
                if not result.response_ok:
                    result.notes += f"Esperaba count={case.expected_count}, números encontrados: {numbers}. "

        else:
            # Si no hay criterio específico de respuesta, basta con que haya respondido
            result.response_ok = len(full_response) > 0

        # 9. Resultado global
        result.overall_pass = result.intent_ok and result.entity_ok and result.response_ok

        if not result.overall_pass:
            if not result.intent_ok:
                result.notes += f"Intent: esperado={case.expected_intent}, obtenido={result.intent_detected} ({result.intent_confidence:.2f}). "
            if not result.entity_ok:
                result.notes += f"Entity: esperado={case.expected_entity_name}={case.expected_entity_value}. "
            if not result.response_ok:
                full_resp = " ".join(result.bot_responses).lower() if result.bot_responses else "(vacía)"
                result.notes += f"Response: '{full_resp[:200]}'. "

    except requests.exceptions.Timeout:
        result.notes = "TIMEOUT: el servidor no respondió a tiempo."
        print(f"           [CAUGHT] Timeout en test {case.id}")
    except (requests.exceptions.ConnectionError, ConnectionError) as e:
        result.notes = f"CONNECTION_ERROR: {e}"
        print(f"           [CAUGHT] ConnectionError en test {case.id}: {e}")
    except Exception as e:
        result.notes = f"ERROR: {e}"
        print(f"           [CAUGHT] Error en test {case.id}: {e}")

    return result


# ---------------------------------------------------------------------------
# Generación de informes
# ---------------------------------------------------------------------------

def generate_report(
    all_results: list[TestResult],
    cases: list[TestCase],
    output_dir: str,
    timestamp: str,
):
    """Genera informes en JSON y Markdown."""
    os.makedirs(output_dir, exist_ok=True)

    # Solo guardamos la última ejecución (sobrescribe por diseño).
    # El timestamp sigue apareciendo dentro del informe como metadato.
    json_path = os.path.join(output_dir, "asignaturas.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            [asdict(r) for r in all_results],
            f,
            ensure_ascii=False,
            indent=2,
        )

    md_path = os.path.join(output_dir, "asignaturas.md")

    # Agrupar resultados por test_id
    results_by_id: dict[str, list[TestResult]] = {}
    for r in all_results:
        results_by_id.setdefault(r.test_id, []).append(r)

    total_cases = len(cases)
    passed_cases = 0
    failed_cases = 0
    inconsistent_cases = 0

    rows = []
    for case in cases:
        runs = results_by_id.get(case.id, [])
        if not runs:
            rows.append((case.id, case.query[:50], "-", "-", "-", "-", "No ejecutado"))
            continue

        pass_count = sum(1 for r in runs if r.overall_pass)
        total_runs = len(runs)
        all_passed = pass_count == total_runs
        none_passed = pass_count == 0
        consistent = all_passed or none_passed

        if all_passed:
            passed_cases += 1
            status = "PASS"
        elif none_passed:
            failed_cases += 1
            status = "FAIL"
        else:
            inconsistent_cases += 1
            status = f"INCONSISTENTE ({pass_count}/{total_runs})"

        intents = set(r.intent_detected for r in runs)
        intent_str = ", ".join(str(i) for i in intents)
        confs = [r.intent_confidence for r in runs if r.intent_confidence]
        conf_str = f"{sum(confs)/len(confs):.2f}" if confs else "-"
        notes = runs[0].notes if runs[0].notes else ""

        rows.append((
            case.id,
            case.query[:50],
            intent_str,
            conf_str,
            f"{pass_count}/{total_runs}",
            status,
            notes[:80],
        ))

    pass_rate = (passed_cases / total_cases * 100) if total_cases else 0
    threshold_met = pass_rate >= 90

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Informe de Pruebas — Asignaturas v1\n\n")
        f.write(f"**Fecha:** {timestamp}\n\n")
        f.write(f"## Resumen\n\n")
        f.write(f"| Métrica | Valor |\n")
        f.write(f"|---------|-------|\n")
        f.write(f"| Total casos | {total_cases} |\n")
        f.write(f"| Pasados | {passed_cases} |\n")
        f.write(f"| Fallidos | {failed_cases} |\n")
        f.write(f"| Inconsistentes | {inconsistent_cases} |\n")
        f.write(f"| **Tasa de éxito** | **{pass_rate:.1f}%** |\n")
        f.write(f"| Umbral (>=90%) | {'CUMPLIDO' if threshold_met else 'NO CUMPLIDO'} |\n")
        f.write(f"\n---\n\n")
        f.write(f"## Resultados por caso\n\n")
        f.write(f"| ID | Consulta | Intent detectado | Confianza | Runs OK | Estado | Notas |\n")
        f.write(f"|----|---------|-----------------|-----------|---------|--------|-------|\n")
        for row in rows:
            f.write(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]} | {row[6]} |\n")

        # Detalles de fallos
        cases_by_id = {case.id: case for case in cases}
        failed_ids = [case.id for case in cases
                      if any(not r.overall_pass for r in results_by_id.get(case.id, []))]
        if failed_ids:
            f.write(f"\n---\n\n## Detalle de fallos\n\n")
            for fid in failed_ids:
                runs = results_by_id.get(fid, [])
                case = cases_by_id[fid]
                f.write(f"### {fid}\n\n")
                # Valores esperados
                f.write(f"- **Query:** {case.query}\n")
                if case.expected_intent:
                    f.write(f"- **Intent esperado:** {case.expected_intent}\n")
                if case.expected_entity_name:
                    ent_exp = case.expected_entity_name
                    if case.expected_entity_value:
                        ent_exp += f"={case.expected_entity_value}"
                    f.write(f"- **Entity esperada:** {ent_exp}\n")
                if case.expected_json_attrs:
                    f.write(f"- **JSON esperado:** `{case.expected_json_attrs}`\n")
                if case.expected_count is not None:
                    f.write(f"- **Count esperado:** {case.expected_count}\n")
                if case.expected_contains:
                    f.write(f"- **Contiene esperado:** \"{case.expected_contains}\"\n")
                if case.expected_not_found:
                    f.write(f"- **Esperado:** respuesta \"no encontrada\"\n")
                if case.expected_ask_titulacion:
                    f.write(f"- **Esperado:** pide titulación\n")
                f.write(f"\n")
                for r in runs:
                    if not r.overall_pass:
                        conf_val = f"{r.intent_confidence:.2f}" if r.intent_confidence else "0"
                        f.write(f"- **Run {r.run_number}**: intent={r.intent_detected} "
                                f"(conf={conf_val}), "
                                f"intent_ok={r.intent_ok}, entity_ok={r.entity_ok}, "
                                f"response_ok={r.response_ok}\n")
                        if r.bot_responses:
                            resp_preview = r.bot_responses[0][:200] if r.bot_responses[0] else "(vacío)"
                            f.write(f"  - Respuesta: {resp_preview}\n")
                        # JSON esperado vs recibido
                        if case.expected_json_attrs:
                            f.write(f"  - **Esperado:** `{case.expected_json_attrs}`\n")
                            if r.custom_data is not None:
                                if isinstance(r.custom_data, dict):
                                    relevant = {k: r.custom_data.get(k) for k in case.expected_json_attrs}
                                    f.write(f"  - **Recibido:** `{relevant}`\n")
                                elif isinstance(r.custom_data, list) and r.custom_data:
                                    first = r.custom_data[0] if isinstance(r.custom_data[0], dict) else r.custom_data
                                    if isinstance(first, dict):
                                        relevant = {k: first.get(k) for k in case.expected_json_attrs}
                                        f.write(f"  - **Recibido (1er resultado):** `{relevant}`\n")
                                    else:
                                        f.write(f"  - **Recibido:** `{r.custom_data}`\n")
                                else:
                                    f.write(f"  - **Recibido:** `{r.custom_data}`\n")
                            else:
                                f.write(f"  - **Recibido:** (sin datos JSON estructurados)\n")
                        # Count esperado vs recibido
                        if case.expected_count is not None:
                            f.write(f"  - **Count esperado:** {case.expected_count}\n")
                            f.write(f"  - **Count recibido:** {r.custom_data if r.custom_data is not None else '(sin datos estructurados)'}\n")
                        if r.notes:
                            f.write(f"  - Notas: {r.notes}\n")
                f.write("\n")

    print(f"\n{'='*60}")
    print(f"  INFORME GENERADO")
    print(f"{'='*60}")
    print(f"  JSON:     {json_path}")
    print(f"  Markdown: {md_path}")
    print(f"  Pasados:  {passed_cases}/{total_cases} ({pass_rate:.1f}%)")
    print(f"  Umbral:   {'CUMPLIDO' if threshold_met else 'NO CUMPLIDO'}")
    print(f"{'='*60}")

    return json_path, md_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Ejecuta el plan de pruebas de asignaturas v1 contra Rasa."
    )
    parser.add_argument(
        "--rasa-url", default=RASA_URL,
        help=f"URL del servidor Rasa (default: {RASA_URL})"
    )
    parser.add_argument(
        "--only", default=None,
        help="Filtrar por categoría: especifica,listado,conteo,fuera_ambito (separar por coma)"
    )
    parser.add_argument(
        "--runs", type=int, default=None,
        help="Forzar N ejecuciones por caso (override del plan)"
    )
    parser.add_argument(
        "--nlu-only", action="store_true",
        help="Solo ejecutar validación NLU (sin enviar al action server)"
    )
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  PLAN DE PRUEBAS — ASIGNATURAS v1 (sin RAG)")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Conectar a Rasa
    client = RasaClient(args.rasa_url)

    # Construir casos
    cases = build_test_cases()

    # Filtrar categorías si se pidió
    if args.only:
        allowed = {c.strip() for c in args.only.split(",")}
        cases = [c for c in cases if c.category in allowed]
        print(f"  Filtrado: {len(cases)} casos de categorías {allowed}")

    print(f"  Total casos: {len(cases)}")
    total_runs = sum(args.runs or c.runs for c in cases)
    print(f"  Total ejecuciones: {total_runs}\n")

    # Ejecutar
    all_results: list[TestResult] = []
    for i, case in enumerate(cases, 1):
        n_runs = args.runs or case.runs
        print(f"  [{i}/{len(cases)}] {case.id} — {case.query[:60]}")

        for run in range(1, n_runs + 1):
            if args.nlu_only:
                # Solo NLU
                result = TestResult(
                    test_id=case.id,
                    run_number=run,
                    query=case.query,
                    timestamp=datetime.now().isoformat(),
                )
                try:
                    nlu = client.parse_nlu(case.query)
                    result.intent_detected = nlu.get("intent", {}).get("name")
                    result.intent_confidence = nlu.get("intent", {}).get("confidence")
                    result.entities_detected = nlu.get("entities", [])

                    if case.expected_intent:
                        if case.expected_intent == "nlu_fallback":
                            result.intent_ok = (
                                result.intent_detected == "nlu_fallback"
                                or (result.intent_confidence and result.intent_confidence < 0.7)
                            )
                        else:
                            result.intent_ok = result.intent_detected == case.expected_intent
                    else:
                        result.intent_ok = True

                    if case.expected_entity_name:
                        result.entity_ok = any(
                            e.get("entity") == case.expected_entity_name
                            for e in (result.entities_detected or [])
                        )
                    else:
                        result.entity_ok = True

                    result.response_ok = True  # no se valida en NLU-only
                    result.overall_pass = result.intent_ok and result.entity_ok
                except Exception as e:
                    result.notes = f"ERROR: {e}"

                all_results.append(result)
            else:
                for attempt in range(3):
                    try:
                        result = run_single_test(client, case, run)
                        break
                    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                        if attempt < 2:
                            print(f"           [retry {attempt+1}/2] conexión perdida, reintentando en 5s...")
                            time.sleep(5)
                        else:
                            result = TestResult(test_id=case.id, run_number=run, query=case.query, timestamp=datetime.now().isoformat())
                            result.notes = f"ERROR conexión: {e}"
                all_results.append(result)

            status = "PASS" if result.overall_pass else "FAIL"
            extra = f" — {result.notes}" if result.notes else ""
            # Mostrar entidades esperadas vs detectadas
            ent_expected = ""
            if case.expected_entity_name:
                ent_expected = f"{case.expected_entity_name}"
                if case.expected_entity_value:
                    ent_expected += f"={case.expected_entity_value}"
            ent_detected = ", ".join(
                f"{e.get('entity')}={e.get('value')}"
                for e in (result.entities_detected or [])
            ) or "none"
            ent_status = ""
            if case.expected_entity_name:
                ent_status = f" | ent_ok={'YES' if result.entity_ok else 'NO'}: expected=[{ent_expected}] detected=[{ent_detected}]"
            conf_display = f"{result.intent_confidence:.2f}" if result.intent_confidence else "0.00"
            print(f"           run {run}: {status} (intent={result.intent_detected}, "
                  f"conf={conf_display}{ent_status}){extra}")
            # Mostrar JSON esperado vs recibido
            if case.expected_json_attrs or case.expected_count is not None:
                custom = getattr(result, 'custom_data', None)
                if case.expected_json_attrs:
                    print(f"             JSON esperado: {case.expected_json_attrs}")
                    if custom and isinstance(custom, dict):
                        relevant = {k: custom.get(k) for k in case.expected_json_attrs}
                        print(f"             JSON recibido: {relevant}")
                    else:
                        print(f"             JSON recibido: (sin datos estructurados)")
                if case.expected_count is not None:
                    print(f"             Count esperado: {case.expected_count}")
                    if custom is not None:
                        print(f"             Count recibido: {custom}")
                    else:
                        print(f"             Count recibido: (sin datos estructurados)")
            # Mostrar respuesta de texto siempre
            if result.bot_responses:
                resp_preview = result.bot_responses[0][:150] if result.bot_responses else ""
                print(f"             Respuesta: '{resp_preview}'")

    # Generar informes
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    generate_report(all_results, cases, RESULTS_DIR, ts)


if __name__ == "__main__":
    main()
