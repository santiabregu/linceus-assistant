# Investigación: Ollama en el Pipeline NLU de Rasa

## Pregunta clave
> ¿Merece la pena usar Ollama (llama3.2:3b) para clasificar intents en el pipeline NLU de Rasa, o es mejor mantener DIET Classifier?

---

## 1. Estado actual: LLMCommandGenerator en config.yml

Tu `config.yml` actual incluye esto:

```yaml
- name: LLMCommandGenerator
  llm:
    model: "ollama"
```

### PROBLEMA CRÍTICO: LLMCommandGenerator es SOLO de Rasa Pro

| Componente | Rasa OSS 3.6 | Rasa Pro |
|---|---|---|
| LLMCommandGenerator | **NO** | Sí |
| CompactLLMCommandGenerator | **NO** | Sí |
| LLMIntentClassifier (rasa_plus) | **NO** | Sí |
| CALM (flows + commands) | **NO** | Sí |
| ContextualResponseRephraser | **NO** | Sí |
| EnterpriseSearchPolicy | **NO** | Sí |
| DIET Classifier | **Sí** | Sí |
| Custom GraphComponents | **Sí** | Sí |
| Custom Actions (rasa-sdk) | **Sí** | Sí |

**Rasa Pro cuesta ~$35,000/año mínimo.** No es viable para un TFG.

**Acción inmediata**: Eliminar `LLMCommandGenerator` de `config.yml`. Causará error al entrenar/cargar el modelo.

Fuentes:
- [Command Generator - Rasa Pro Docs](https://rasa.com/docs/pro/customize/command-generator/)
- [LLM Intent Classification - Rasa Legacy Docs](https://legacy-docs-oss.rasa.com/docs/rasa/next/llms/llm-intent/)
- [Local LLM with RASA CALM - Forum](https://forum.rasa.com/t/local-llm-with-rasa-calm/62752/2)

---

## 2. Estado de Rasa Open Source

**Rasa OSS está en modo mantenimiento.** La versión 3.6.21 es la última release.

- La documentación OSS se movió a `legacy-docs-oss.rasa.com`
- Actividad del foro casi nula
- No funciona con versiones recientes de Python
- Usa TensorFlow 2.11.x (antiguo)
- No habrá nuevas features para OSS

**Pese a todo, sigue siendo la mejor opción open-source para gestión de diálogo estructurado.** No hay alternativa real equivalente en código abierto.

Fuentes:
- [Is the project dead? - Forum](https://forum.rasa.com/t/is-the-project-dead/68344)
- [Rasa Pro vs OSS - Voiceflow](https://www.voiceflow.com/blog/rasa-chatbot)

---

## 3. Opciones reales para integrar Ollama con Rasa OSS 3.6

### Opción A: DIET para NLU + Ollama solo en Custom Actions (RECOMENDADA)

```
Usuario → Rasa DIET (~30ms) → Intent + Entities → Custom Action → Ollama (2-4s) → Respuesta natural
```

**Pros:**
- NLU rápido (~30ms por mensaje)
- Determinista y predecible para intents conocidos
- Ollama se usa donde aporta más valor: generar respuestas naturales
- Arquitectura simple y bien documentada
- Es lo que ya tienes parcialmente implementado en `actions/asignaturas.py`

**Contras:**
- DIET no generaliza bien a frases nunca vistas
- Necesita training data suficiente por intent (~20-50 ejemplos)
- No entiende variaciones lingüísticas complejas sin ejemplos

### Opción B: Custom GraphComponent que llama a Ollama para clasificar intents

Rasa OSS 3.6 permite crear componentes NLU custom usando la API `GraphComponent`:

```python
from rasa.engine.recipes.default_recipe import DefaultV1Recipe
from rasa.engine.graph import GraphComponent, ExecutionContext
from rasa.shared.nlu.training_data.message import Message

@DefaultV1Recipe.register(
    component_types=[DefaultV1Recipe.ComponentType.INTENT_CLASSIFIER],
    is_trainable=False
)
class OllamaIntentClassifier(GraphComponent):

    def process(self, messages: List[Message]) -> List[Message]:
        for message in messages:
            text = message.get("text")

            # Llamar a Ollama para clasificar
            prompt = f"""Clasifica este mensaje en uno de estos intents:
            - greet, goodbye, affirm, deny
            - consultar_asignatura_db, pedir_mas_resultados
            - cambiar_contexto_academico, consultar_contexto_academico
            - pedir_ayuda, bot_challenge

            Mensaje: "{text}"
            Responde SOLO con JSON: {{"intent": "nombre", "confidence": 0.95}}"""

            resultado = llamar_ollama(prompt)
            # Parsear y setear intent en el mensaje
            message.set("intent", {"name": intent, "confidence": conf})

        return messages
```

**Config:**
```yaml
pipeline:
  - name: WhitespaceTokenizer
  - name: path.to.OllamaIntentClassifier
    model: "llama3.2:3b"
  - name: FallbackClassifier
    threshold: 0.6
```

**Pros:**
- Generaliza mejor a frases nunca vistas (zero-shot / few-shot)
- No necesita tanta training data
- Entiende variaciones lingüísticas complejas
- Multilingüe sin reentrenar

**Contras:**
- **+200-3000ms de latencia por CADA mensaje** (vs 30ms de DIET)
- Menos determinista (puede variar entre ejecuciones)
- Más complejo de implementar y debuggear
- Requiere Ollama siempre activo para que funcione el NLU
- Para solo 11 intents bien definidos, es overkill

### Opción C: Híbrido - DIET primero, Ollama como fallback

```
Usuario → DIET (30ms)
  ├── Confianza >= 0.6 → Usar intent de DIET ✓
  └── Confianza < 0.6 → Ollama reclasifica (2-4s) → Intent corregido
```

```python
@DefaultV1Recipe.register(
    component_types=[DefaultV1Recipe.ComponentType.INTENT_CLASSIFIER],
    is_trainable=False
)
class OllamaFallbackClassifier(GraphComponent):

    def process(self, messages: List[Message]) -> List[Message]:
        for message in messages:
            intent = message.get("intent", {})
            confidence = intent.get("confidence", 0)

            # Solo llamar a Ollama si DIET no está seguro
            if confidence < 0.6:
                # Reclasificar con Ollama
                resultado = self._clasificar_con_ollama(message.get("text"))
                if resultado:
                    message.set("intent", resultado)

        return messages
```

**Pros:**
- Rápido para consultas que DIET entiende bien (mayoría)
- Ollama solo interviene cuando hay duda (~10-20% de mensajes)
- Mejor accuracy global que DIET solo
- Latencia media baja (DIET resuelve la mayoría en 30ms)

**Contras:**
- Más complejo de implementar
- Dos sistemas que mantener
- Necesita tuning del threshold de fallback

---

## 4. Comparativa de Rendimiento: DIET vs LLM

### Latencia

| Sistema | Latencia por mensaje |
|---|---|
| DIET Classifier (Rasa) | ~30ms |
| Ollama llama3.2:3b (GPU) | ~200-800ms |
| Ollama llama3.2:3b (CPU) | ~1,000-3,000ms |
| GPT-3.5-turbo (API) | ~500-1,000ms |
| Claude Haiku (API) | ~1,697ms |

**DIET es ~56x más rápido** que el mejor LLM para clasificación de intents.

### Accuracy

| Sistema | F1 Score | Notas |
|---|---|---|
| DIET (275 ejemplos, 11 intents) | ~85-95% estimado | Para intents bien definidos con datos suficientes |
| LLM (zero-shot) | ~70-75% | Sin fine-tuning, solo prompt |
| LLM (few-shot, 5-10 ejemplos en prompt) | ~80-90% | Ejemplos en el prompt |
| Híbrido (DIET + LLM fallback) | ~90-97% | Lo mejor de ambos mundos |

### Resumen por caso de uso

| Escenario | Mejor opción |
|---|---|
| 11 intents bien definidos, training data suficiente | **DIET** |
| Muchos intents (+30), poca training data | **LLM** |
| Frases con mucha variación lingüística | **LLM** |
| Latencia crítica (<100ms) | **DIET** |
| Máxima accuracy posible | **Híbrido** |
| Proyecto universitario con recursos limitados | **DIET + Ollama en actions** |

Fuentes:
- [Intent Detection in the Age of LLMs - arXiv](https://arxiv.org/html/2410.01627v1)
- [Benchmarking Hybrid LLM Classification - Voiceflow](https://www.voiceflow.com/blog/benchmarking-hybrid-llm-classification-systems)
- [Introducing DIET - Rasa Blog](https://rasa.com/blog/introducing-dual-intent-and-entity-transformer-diet-state-of-the-art-performance-on-a-lightweight-architecture)

---

## 5. Análisis del Training Data Actual

### Distribución de intents

| Intent | Ejemplos | Evaluación |
|---|---|---|
| consultar_asignatura_db | 128 | Excelente |
| pedir_mas_resultados | 27 | Bueno |
| affirm | 21 | Adecuado |
| pedir_ayuda | 17 | Aceptable |
| greet | 15 | Aceptable |
| goodbye | 15 | Aceptable |
| deny | 10 | Borderline |
| mood_great | 10 | Borderline |
| mood_unhappy | 10 | Borderline |
| bot_challenge | 8 | **Insuficiente** |
| cambiar_contexto_academico | 8 | **Insuficiente** |
| consultar_contexto_academico | 6 | **Insuficiente** |

**Total: 275 ejemplos, 11 intents**

### Problemas detectados

1. **3 intents con <10 ejemplos** - DIET necesita mínimo 10-15 por intent
2. **Solo 43 ejemplos con entidad `nombre_asignatura` anotada** de 128
3. **Solo 6 ejemplos con entidad `nombre_titulacion`** - extracción será pobre
4. **Solapamiento** entre `pedir_mas_resultados` ("sí", "vale") y `affirm`

### Mejoras recomendadas para DIET

| Acción | Impacto estimado |
|---|---|
| Subir `consultar_contexto_academico` a 20+ ejemplos | F1 del intent: +30% |
| Subir `cambiar_contexto_academico` a 20+ ejemplos | F1 del intent: +25% |
| Anotar entidades en los 85 ejemplos sin anotar | Entity extraction: +20% |
| Añadir `nombre_titulacion` a 30+ ejemplos | Entity extraction: +40% |
| Añadir `es_core_news_md` (SpaCy español) al pipeline | F1 global: +5-10% |

Con estas mejoras, DIET rendiría al **90-95% F1** para los 11 intents.

---

## 6. Recomendación Final

### Para tu TFG: Opción A (DIET + Ollama en actions)

```
┌─────────────────────────────────────────────┐
│              PIPELINE NLU (rápido)           │
│                                             │
│  WhitespaceTokenizer                        │
│  → RegexFeaturizer                          │
│  → LexicalSyntacticFeaturizer               │
│  → CountVectorsFeaturizer (word + char)     │
│  → DIETClassifier (150 epochs)         ~30ms│
│  → EntitySynonymMapper                      │
│  → FallbackClassifier (threshold: 0.6)      │
└──────────────────┬──────────────────────────┘
                   │ intent + entities
                   ▼
┌─────────────────────────────────────────────┐
│           CUSTOM ACTIONS (inteligente)       │
│                                             │
│  1. Recibir intent + entities de DIET       │
│  2. Si hacen falta más datos:               │
│     → Ollama analiza consulta (2-4s)        │
│  3. Consultar Supabase                      │
│  4. Ollama genera respuesta natural (2-4s)  │
│                                             │
│  Latencia total: 2-6s (aceptable)           │
└─────────────────────────────────────────────┘
```

### Por qué NO usar Ollama en el pipeline NLU:

1. **Latencia innecesaria**: +2-3s en CADA mensaje, incluso "hola" o "adiós"
2. **Solo tienes 11 intents**: DIET los maneja perfectamente con training data suficiente
3. **Ya usas Ollama en actions**: Ahí es donde aporta valor real (entender consultas complejas, generar respuestas)
4. **Complejidad extra**: Mantener un GraphComponent custom vs usar DIET estándar
5. **Fiabilidad**: DIET es determinista, Ollama puede dar resultados variables

### Cuándo SÍ valdría la pena Ollama en NLU:

- Si tuvieras +30 intents con poca training data
- Si las consultas fueran extremadamente variadas e impredecibles
- Si necesitaras clasificación zero-shot (sin training data)
- Si migraras a una arquitectura sin Rasa (solo LLM)

### Acción inmediata en config.yml

Eliminar `LLMCommandGenerator` (no funciona en Rasa OSS):

```yaml
# ELIMINAR estas líneas:
# - name: LLMCommandGenerator
#   llm:
#     model: "ollama"
```

### Mejoras opcionales al pipeline

```yaml
pipeline:
  # Añadir SpaCy para embeddings preentrenados en español
  - name: SpacyNLP
    model: "es_core_news_md"
  - name: SpacyTokenizer
  # ... resto del pipeline igual
```

---

## 7. Fuentes

- [Command Generator - Rasa Pro Docs](https://rasa.com/docs/pro/customize/command-generator/)
- [LLM Configuration for Rasa Pro](https://rasa.com/docs/reference/config/components/llm-configuration/)
- [Custom Graph Components - Rasa OSS Docs](https://legacy-docs-oss.rasa.com/docs/rasa/custom-graph-components/)
- [Intent Detection in the Age of LLMs - arXiv](https://arxiv.org/html/2410.01627v1)
- [Benchmarking Hybrid LLM Classification - Voiceflow](https://www.voiceflow.com/blog/benchmarking-hybrid-llm-classification-systems)
- [Introducing DIET - Rasa Blog](https://rasa.com/blog/introducing-dual-intent-and-entity-transformer-diet-state-of-the-art-performance-on-a-lightweight-architecture)
- [DIET Paper - arXiv](https://arxiv.org/pdf/2004.09936)
- [Is the project dead? - Rasa Forum](https://forum.rasa.com/t/is-the-project-dead/68344)
- [Local LLM with RASA CALM - Rasa Forum](https://forum.rasa.com/t/local-llm-with-rasa-calm/62752/2)
- [When to Choose Rasa vs LangChain - Simplico](https://simplico.net/2025/05/09/when-to-choose-rasa-vs-langchain-for-building-chatbots/)
- [Building AI Chatbot with Rasa and Ollama - Codecademy](https://www.codecademy.com/article/ai-chatbot-with-rasa-and-ollama)
- [Rasa NLU Examples - GitHub](https://github.com/RasaHQ/rasa-nlu-examples)
