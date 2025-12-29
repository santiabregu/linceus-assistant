# Diccionario del Sistema Conversacional

Este documento define los principales conceptos, componentes y elementos técnicos utilizados en el desarrollo del sistema conversacional. Las definiciones se basan en la documentación oficial de Rasa y en las decisiones de diseño adoptadas durante el proyecto. Su finalidad es servir como referencia común durante todo el ciclo de desarrollo.

---

# PARTE 1: ESTRUCTURA DE ARCHIVOS DE RASA

Esta sección explica los archivos principales del proyecto y su función dentro del sistema.

---

## 📁 Estructura de carpetas típica

```
mi_chatbot/
├── data/
│   ├── nlu.yml          # Ejemplos de frases del usuario
│   ├── stories.yml      # Flujos de conversación para entrenamiento
│   └── rules.yml        # Comportamientos fijos/deterministas
├── actions/
│   └── actions.py       # Código Python para lógica personalizada
├── domain.yml           # Definición central del asistente
├── config.yml           # Configuración del pipeline NLU y políticas
├── endpoints.yml        # Conexiones externas (action server, tracker store)
└── credentials.yml      # Credenciales de canales (web, telegram, etc.)
```

---

## domain.yml
**Qué es:** El archivo de configuración central que define TODO lo que el asistente "conoce".

**Contiene:**
- Lista de `intents` que el bot puede reconocer
- Lista de `entities` que puede extraer
- Definición de `slots` para almacenar información
- `responses` (respuestas predefinidas con `utter_`)
- Lista de `actions` disponibles (incluyendo custom actions)

**Analogía:** Es como el "vocabulario" y "capacidades" del asistente. Si algo no está en el domain, el bot no lo conoce.

**Ejemplo:**
```yaml
intents:
  - greet
  - consultar_asignatura

entities:
  - nombre_asignatura

slots:
  nombre_asignatura:
    type: text
    mappings:
      - type: from_entity
        entity: nombre_asignatura

responses:
  utter_greet:
    - text: "¡Hola! ¿En qué puedo ayudarte?"

actions:
  - action_consultar_asignatura
```

---

## data/nlu.yml
**Qué es:** Archivo con ejemplos de frases que los usuarios pueden decir, etiquetadas por intención.

**Propósito:** Entrenar al modelo NLU para que clasifique correctamente las frases del usuario.

**Regla clave:** Cuantos más ejemplos variados, mejor clasificará el modelo.

**Ejemplo:**
```yaml
nlu:
- intent: consultar_asignatura
  examples: |
    - información de [Fundamentos de Programación](nombre_asignatura)
    - qué es [Estadística](nombre_asignatura)
    - cuéntame sobre la asignatura [Redes](nombre_asignatura)
    - datos de [ADDA](nombre_asignatura)
    - quiero saber de una asignatura

- intent: greet
  examples: |
    - hola
    - buenos días
    - qué tal
```

**Nota:** Los corchetes `[texto](entidad)` marcan las entidades dentro del ejemplo.

---

## data/stories.yml
**Qué es:** Archivo que define flujos de conversación completos como ejemplos de entrenamiento.

**Propósito:** Enseñar al modelo de diálogo cómo debe progresar una conversación típica.

**Cuándo usarlo:**
- Conversaciones de varios turnos
- Flujos donde el contexto importa (lo que pasó antes afecta lo que pasa después)
- Situaciones donde el bot debe recordar información previa

**Ejemplo:**
```yaml
stories:
- story: usuario pregunta por asignatura después de saludar
  steps:
  - intent: greet
  - action: utter_greet
  - intent: consultar_asignatura
    entities:
    - nombre_asignatura: "Fundamentos de Programación"
  - action: action_consultar_asignatura
  - intent: goodbye
  - action: utter_goodbye
```

**Analogía:** Son como "guiones de ejemplo" que muestran conversaciones ideales.

---

## data/rules.yml
**Qué es:** Archivo que define comportamientos FIJOS que siempre deben ocurrir.

**Propósito:** Garantizar respuestas deterministas en situaciones específicas.

**Diferencia clave con stories:**
| Stories | Rules |
|---------|-------|
| Son ejemplos para entrenar | Son leyes que siempre se cumplen |
| El modelo puede generalizar | No hay generalización, es exacto |
| Para flujos complejos | Para respuestas simples y directas |
| "Aprende de esto" | "Haz siempre esto" |

**Cuándo usar rules:**
- Saludos y despedidas
- Preguntas frecuentes con respuesta única
- Fallbacks
- Cualquier caso donde SIEMPRE quieres la misma respuesta

**Ejemplo:**
```yaml
rules:
- rule: Siempre responder al saludo
  steps:
  - intent: greet
  - action: utter_greet

- rule: Consultar asignatura cuando el usuario lo pide
  steps:
  - intent: consultar_asignatura
  - action: action_consultar_asignatura
```

---

## actions/actions.py
**Qué es:** Archivo Python donde se programa la lógica personalizada del asistente.

**Propósito:** Ejecutar código que no puede hacerse con respuestas simples (consultar BD, llamar APIs, procesar datos).

**Cuándo usarlo:**
- Consultas a bases de datos
- Cálculos o procesamiento de datos
- Integración con servicios externos
- Respuestas dinámicas basadas en datos

**Estructura básica de una action:**
```python
class ActionConsultarAsignatura(Action):
    
    def name(self) -> Text:
        """Nombre que usas en domain.yml y rules/stories"""
        return "action_consultar_asignatura"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        dispatcher: para enviar mensajes al usuario
        tracker: para leer el estado de la conversación (slots, entidades, historial)
        domain: para acceder a la configuración del domain.yml
        """
        
        # 1. Obtener datos del usuario
        nombre = tracker.get_slot("nombre_asignatura")
        
        # 2. Hacer algo (consultar BD, procesar, etc.)
        resultado = consultar_base_datos(nombre)
        
        # 3. Responder al usuario
        dispatcher.utter_message(text=f"La asignatura {nombre} tiene...")
        
        # 4. Opcionalmente, modificar slots
        return [SlotSet("nombre_asignatura", nombre)]
```

---

## config.yml
**Qué es:** Configuración del pipeline de NLU y las políticas de diálogo.

**Propósito:** Definir qué componentes procesan el texto y cómo se toman las decisiones.

**Secciones principales:**
- `pipeline`: componentes que procesan el texto del usuario (tokenización, clasificación, extracción de entidades)
- `policies`: mecanismos que deciden la siguiente acción

**Ejemplo simplificado:**
```yaml
pipeline:
  - name: WhitespaceTokenizer      # Divide el texto en palabras
  - name: CountVectorsFeaturizer   # Convierte palabras en vectores
  - name: DIETClassifier           # Clasifica intents y extrae entidades

policies:
  - name: RulePolicy               # Aplica las rules.yml
  - name: TEDPolicy                # Aprende de las stories.yml
  - name: MemoizationPolicy        # Memoriza stories exactas
```

---

## endpoints.yml
**Qué es:** Configuración de conexiones a servicios externos.

**Contiene típicamente:**
- URL del action server (donde corren las custom actions)
- Configuración del tracker store (donde se guarda el estado)

**Ejemplo:**
```yaml
action_endpoint:
  url: "http://localhost:5055/webhook"
```

---

# PARTE 2: CONCEPTOS FUNDAMENTALES

---

## Sistema conversacional
Aplicación software diseñada para interactuar con usuarios mediante lenguaje natural. El sistema interpreta las entradas del usuario, mantiene el estado del diálogo y genera respuestas coherentes en función del contexto y de los objetivos definidos.

---

## Rasa
Framework open-source orientado al desarrollo de asistentes conversacionales que permite construir sistemas basados en clasificación explícita de intenciones, extracción de entidades y gestión estructurada del diálogo.

---

## NLU (Natural Language Understanding)
Componente encargado de procesar los mensajes del usuario para identificar la intención principal y extraer entidades relevantes. El NLU constituye la primera etapa del procesamiento de cada entrada textual.

**Flujo:**
```
"Info de Fundamentos de Programación"
         ↓ NLU
Intent: consultar_asignatura (confianza: 0.95)
Entity: nombre_asignatura = "Fundamentos de Programación"
```

---

## Intent
Representa el propósito o objetivo del mensaje del usuario. Cada mensaje se clasifica en una única intención que determina el tipo de acción que debe realizar el asistente.

**Ejemplos de intents típicos:**
| Intent | Frases ejemplo |
|--------|----------------|
| `greet` | "hola", "buenos días" |
| `consultar_asignatura` | "info de FP", "qué es Estadística" |
| `consultar_horario` | "cuándo tengo clase", "horario de mañana" |
| `goodbye` | "adiós", "hasta luego" |

---

## Entity
Elemento de información concreta extraído del mensaje del usuario que aporta detalles adicionales a la intención detectada.

**Ejemplo:**
```
Frase: "¿Cuál es el horario de Fundamentos de Programación del grupo 1?"

Intent: consultar_horario
Entities:
  - nombre_asignatura: "Fundamentos de Programación"
  - grupo: "1"
```

---

## Slot
Variable de memoria utilizada para almacenar información relevante durante una conversación. Los slots permiten mantener el estado del diálogo entre turnos.

**Tipos de slots:**
| Tipo | Uso |
|------|-----|
| `text` | Almacena cualquier texto |
| `bool` | Verdadero/Falso |
| `categorical` | Valor de una lista predefinida |
| `float` | Números decimales |
| `list` | Lista de valores |
| `any` | Cualquier tipo |

**Diferencia Entity vs Slot:**
- **Entity**: Se extrae del mensaje actual
- **Slot**: Persiste durante toda la conversación

---

## Tracker
Estructura interna que almacena el estado completo de la conversación. Es como la "memoria" del bot.

**Contiene:**
- Historial de mensajes del usuario
- Intents detectados
- Entidades extraídas
- Valores actuales de los slots
- Acciones ejecutadas

**Uso en actions.py:**
```python
# Obtener valor de un slot
nombre = tracker.get_slot("nombre_asignatura")

# Obtener última entidad extraída
entidad = next(tracker.get_latest_entity_values("nombre_asignatura"), None)

# Obtener último mensaje del usuario
mensaje = tracker.latest_message.get("text")

# Obtener intent detectado
intent = tracker.latest_message.get("intent", {}).get("name")
```

---

## Action
Operación ejecutada por el asistente como respuesta. Hay dos tipos:

**1. Respuestas predefinidas (utter_):**
```yaml
# En domain.yml
responses:
  utter_greet:
    - text: "¡Hola! ¿En qué puedo ayudarte?"
```

**2. Custom Actions (action_):**
```python
# En actions.py
class ActionConsultarAsignatura(Action):
    def name(self):
        return "action_consultar_asignatura"
```

**Convención de nombres:**
- `utter_*` → Respuesta simple de texto (definida en domain.yml)
- `action_*` → Código Python personalizado (definido en actions.py)

---

## Form
Mecanismo para recopilar múltiples datos del usuario de forma estructurada.

**Ejemplo de uso:** Si necesitas código de asignatura + grupo + cuatrimestre para dar un horario, el form los pide uno a uno hasta tenerlos todos.

```yaml
# En domain.yml
forms:
  consulta_horario_form:
    required_slots:
      - nombre_asignatura
      - grupo
```

---

## Fallback
Comportamiento de recuperación cuando el bot no entiende al usuario.

**Se activa cuando:**
- Confianza del intent muy baja
- No hay acción definida para la situación
- Error en una custom action

**Configuración típica:**
```yaml
# En rules.yml
- rule: Fallback cuando no se entiende
  steps:
  - intent: nlu_fallback
  - action: utter_fallback
```

---

# PARTE 3: FLUJO DE PROCESAMIENTO

## ¿Cómo procesa Rasa un mensaje?

```
┌─────────────────────────────────────────────────────────────────┐
│  Usuario escribe: "Información de Fundamentos de Programación"  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. NLU (Natural Language Understanding)                        │
│     - Tokenización: divide en palabras                          │
│     - Clasifica intent: consultar_asignatura (0.95)             │
│     - Extrae entities: nombre_asignatura = "Fundamentos..."     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Dialogue Management (Políticas)                             │
│     - Consulta rules.yml → ¿hay regla para este intent?         │
│     - Si no, consulta stories.yml → ¿qué flujo se parece más?   │
│     - Decide acción: action_consultar_asignatura                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. Action Execution                                            │
│     - Si es utter_*: envía texto del domain.yml                 │
│     - Si es action_*: ejecuta código de actions.py              │
│       → Consulta base de datos                                  │
│       → Genera respuesta dinámica                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. Respuesta al usuario                                        │
│     "Fundamentos de Programación (2050001)                      │
│      Curso: 1º | Créditos: 12 ECTS | Duración: Anual"           │
└─────────────────────────────────────────────────────────────────┘
```

---

# PARTE 4: BACKEND Y DATOS

---

## Supabase
Plataforma backend basada en PostgreSQL utilizada en el proyecto para almacenar información estructurada y permitir su consulta desde las custom actions.

---

## pgvector
Extensión de PostgreSQL que permite almacenar y consultar vectores numéricos. Se utiliza para búsquedas semánticas (RAG) en la Épica 3 del proyecto.

---

## Conexión BD desde actions.py

```python
# Patrón típico
class ActionConsultarAsignatura(Action):
    def run(self, dispatcher, tracker, domain):
        # 1. Obtener entidad del usuario
        nombre = tracker.get_slot("nombre_asignatura")
        
        # 2. Conectar a BD
        conn = get_connection()
        cursor = conn.cursor()
        
        # 3. Ejecutar query
        cursor.execute("""
            SELECT codigo, nombre, creditos 
            FROM asignaturas 
            WHERE nombre_normalizado ILIKE %s
        """, (f"%{nombre}%",))
        
        # 4. Procesar resultado
        result = cursor.fetchone()
        
        # 5. Responder
        if result:
            dispatcher.utter_message(text=f"...")
        else:
            dispatcher.utter_message(text="No encontré esa asignatura")
        
        conn.close()
        return []
```

---

# PARTE 5: RESUMEN VISUAL

## ¿Dónde defino qué?

| Quiero... | Archivo |
|-----------|---------|
| Enseñar frases del usuario | `data/nlu.yml` |
| Definir un flujo de conversación | `data/stories.yml` |
| Crear una respuesta fija siempre igual | `data/rules.yml` |
| Declarar intents, entities, slots | `domain.yml` |
| Escribir respuestas de texto simples | `domain.yml` (responses) |
| Programar lógica con código | `actions/actions.py` |
| Configurar el modelo NLU | `config.yml` |

## Rules vs Stories: ¿Cuál uso?

```
¿La respuesta es SIEMPRE la misma sin importar el contexto?
    │
    ├── SÍ → Usa RULE
    │        Ejemplo: saludo, despedida, "soy un bot"
    │
    └── NO → Usa STORY
             Ejemplo: conversación de varios pasos donde
             la respuesta depende de lo anterior
```

---
