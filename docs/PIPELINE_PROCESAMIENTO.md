# Pipeline de Procesamiento de Mensajes - Sistema Linceus v2.0

Este documento explica el flujo completo de procesamiento de un mensaje desde que el usuario lo escribe hasta que recibe una respuesta.

---

## 🔄 Flujo General del Sistema

```mermaid
flowchart TD
    A[👤 Usuario escribe mensaje] --> B[📨 Rasa recibe mensaje]
    B --> C{🧠 NLU Pipeline<br/>Clasifica Intent}

    C -->|Intent: consultar_asignatura_db| D[🤖 Action: ActionConsultarAsignaturaDB]
    C -->|Intent: greet| E[💬 Response: utter_greet]
    C -->|Intent: pregunta_seguimiento| F[🤖 Action: ActionPreguntaSeguimiento]
    C -->|Otros intents| G[📋 Otras Actions/Responses]

    D --> H[🔍 Sistema Text-to-SQL con Ollama]
    H --> I[💬 Respuesta Natural al Usuario]

    F --> J[🔍 Usa contexto previo]
    J --> I

    E --> I
    G --> I

    style H fill:#ff9999
    style D fill:#99ccff
    style C fill:#ffcc99
```

---

## 📊 Pipeline NLU de Rasa (Clasificación de Intent)

Este proceso ocurre **ANTES** de llamar a las actions, y determina qué intent tiene el mensaje.

```mermaid
flowchart LR
    A[📝 Mensaje del usuario] --> B[Tokenizer<br/>WhitespaceTokenizer]
    B --> C[Featurizer<br/>RegexFeaturizer]
    C --> D[Featurizer<br/>LexicalSyntacticFeaturizer]
    D --> E[Featurizer<br/>CountVectorsFeaturizer]
    E --> F[Classifier<br/>DIETClassifier]
    F --> G[Intent + Confianza<br/>consultar_asignatura_db: 0.98]
    G --> H[Entity Extractor<br/>EntitySynonymMapper]
    H --> I{Intent clasificado<br/>+ Entidades extraídas}

    style F fill:#ff9999
    style I fill:#99ff99
```

**Ejemplo:**
```
Input: "cuántos créditos tiene Redes"
  ↓ Tokenizer: ["cuántos", "créditos", "tiene", "Redes"]
  ↓ Featurizers: [vectores numéricos]
  ↓ DIET Classifier: intent="consultar_asignatura_db" (conf: 0.98)
  ↓ Entity Extractor: (ninguna entidad detectada en este caso)
Output: Intent="consultar_asignatura_db"
```

---

## 🤖 Sistema Text-to-SQL con Ollama (ActionConsultarAsignaturaDB)

Una vez que Rasa clasifica el intent como `consultar_asignatura_db`, se ejecuta la action principal que usa Ollama.

```mermaid
flowchart TD
    A[🎯 Action recibe mensaje<br/>consultar_asignatura_db] --> B[📦 Cargar asignaturas en memoria<br/>cargar_asignaturas_titulacion]

    B --> C[🔍 Paso 1: Clasificar tipo de consulta<br/>clasificar_tipo_consulta_asignatura]

    C --> D{🤖 LLM Ollama:<br/>Llama3.2:3b}
    D -->|Prompt: Clasificar tipo| E[⏱️ 2-3 segundos]
    E --> F{Tipo de consulta?}

    F -->|ESPECÍFICA<br/>Ej: créditos de Redes| G[📝 Paso 2a: Extraer datos<br/>extraer_datos_consulta_especifica]
    F -->|GENERAL<br/>Ej: asignaturas de primero| H[📝 Paso 2b: Generar SQL<br/>generar_sql_consulta_general]

    G --> I[🤖 LLM Ollama:<br/>Extraer nombre + atributo]
    I --> J[⏱️ 2-3 segundos]
    J --> K[Resultado:<br/>nombre=Redes<br/>atributo=creditos]

    K --> L[🔎 Paso 3a: Búsqueda Fuzzy<br/>_buscar_asignatura]

    L --> M[Buscar en memoria<br/>buscar_en_memoria]
    M --> N{¿Coincidencias?}

    N -->|Exacta por código| O[✅ Asignatura encontrada]
    N -->|Exacta por nombre| O
    N -->|Fuzzy match 1 resultado| O
    N -->|Fuzzy match múltiples| P[🤖 LLM Ollama:<br/>Desambiguar]

    P --> Q[⏱️ 2-3 segundos]
    Q --> O

    O --> R[📊 Paso 4a: Formatear respuesta<br/>_formatear_respuesta_especifica]

    H --> S[🤖 LLM Ollama:<br/>Generar SQL WHERE]
    S --> T[⏱️ 3-5 segundos]
    T --> U[SQL generado:<br/>WHERE curso=1 AND activa=true]

    U --> V[💾 Ejecutar query en BD]
    V --> W[Resultados obtenidos]

    W --> X[📊 Paso 4b: Formatear respuesta<br/>_formatear_respuesta_general]

    R --> Y[🤖 LLM Ollama:<br/>Generar respuesta natural<br/>generar_respuesta_natural]
    X --> Y

    Y --> Z[⏱️ 3-5 segundos]
    Z --> AA[💬 Respuesta natural lista]
    AA --> AB[👤 Usuario recibe respuesta]

    style D fill:#ff9999
    style I fill:#ff9999
    style P fill:#ff9999
    style S fill:#ff9999
    style Y fill:#ff9999
    style AB fill:#99ff99
```

---

## 🎯 Ejemplo Completo: "cuántos créditos tiene Redes"

```mermaid
sequenceDiagram
    participant U as 👤 Usuario
    participant R as 🎯 Rasa NLU
    participant A as 🤖 Action
    participant O as 🦙 Ollama<br/>Llama3.2:3b
    participant M as 💾 Memoria<br/>Cache asignaturas
    participant D as 🗄️ Base de Datos

    U->>R: "cuántos créditos tiene Redes"

    Note over R: Pipeline NLU
    R->>R: Tokenize + Featurize
    R->>R: DIET Classifier
    R->>R: Intent: consultar_asignatura_db<br/>Confidence: 0.98

    R->>A: Ejecutar ActionConsultarAsignaturaDB

    Note over A,M: Cargar asignaturas si no están en cache
    A->>D: SELECT * FROM asignaturas<br/>WHERE titulacion_id = 'GII-IS'
    D-->>A: 50 asignaturas
    A->>M: Guardar en memoria

    Note over A,O: PASO 1: Clasificar tipo de consulta
    A->>O: Prompt: "Clasifica este tipo de consulta:<br/>cuántos créditos tiene Redes"
    Note over O: Procesamiento LLM<br/>⏱️ 2-3s
    O-->>A: {"tipo": "especifica",<br/>"confianza": 0.95}

    Note over A,O: PASO 2: Extraer datos
    A->>O: Prompt: "Extrae nombre de asignatura<br/>y atributo solicitado"
    Note over O: Procesamiento LLM<br/>⏱️ 2-3s
    O-->>A: {"nombre_asignatura": "Redes",<br/>"atributo_solicitado": "creditos"}

    Note over A,M: PASO 3: Búsqueda Fuzzy
    A->>M: Buscar "Redes" en memoria
    M-->>A: Candidatos:<br/>1. Redes de Computadores (score: 85)<br/>2. Redes Neuronales (score: 72)

    Note over A,O: Múltiples coincidencias, desambiguar
    A->>O: Prompt: "Usuario pregunta por 'Redes'.<br/>¿Se refiere a 'Redes de Computadores'<br/>o 'Redes Neuronales'?"
    Note over O: Procesamiento LLM<br/>⏱️ 2-3s
    O-->>A: "Redes de Computadores"

    A->>M: Obtener datos de<br/>"Redes de Computadores"
    M-->>A: {codigo: "2050016",<br/>nombre: "Redes de Computadores",<br/>creditos: 6, curso: 3,<br/>tipologia: "Obligatoria"}

    Note over A,O: PASO 4: Generar respuesta natural
    A->>O: Prompt: "Genera respuesta natural:<br/>Pregunta: cuántos créditos tiene Redes<br/>Datos: creditos=6,<br/>nombre=Redes de Computadores"
    Note over O: Procesamiento LLM<br/>⏱️ 3-5s
    O-->>A: "Redes de Computadores tiene<br/>6 créditos ECTS"

    A->>R: Respuesta + Slots actualizados
    R->>U: "Redes de Computadores tiene<br/>6 créditos ECTS"

    Note over U: ⏱️ Tiempo total: ~10-15 segundos
```

---

## 🔍 Detalle: Clasificación de Tipo de Consulta

```mermaid
flowchart TD
    A[🤖 clasificar_tipo_consulta_asignatura] --> B[Construir prompt para LLM]

    B --> C["Prompt:<br/>Clasifica esta consulta:<br/>- específica: pregunta sobre UNA asignatura<br/>- general: listado/filtros/múltiples<br/><br/>Mensaje: {pregunta}<br/><br/>Responde JSON"]

    C --> D[🦙 LLM Ollama]
    D --> E[Respuesta JSON del LLM]

    E --> F{Parsear JSON}
    F -->|Success| G[Resultado válido]
    F -->|Error| H[Fallback: analizar keywords]

    H --> I{¿Contiene nombre<br/>de asignatura?}
    I -->|Sí| J[Tipo: específica]
    I -->|No| K[Tipo: general]

    G --> L{Tipo devuelto}
    L -->|específica| M[✅ Consulta sobre<br/>UNA asignatura]
    L -->|general| N[✅ Consulta con<br/>filtros/listado]

    J --> M
    K --> N

    style D fill:#ff9999
    style M fill:#99ff99
    style N fill:#99ccff
```

---

## 🔎 Detalle: Búsqueda Fuzzy con Desambiguación

```mermaid
flowchart TD
    A[🔍 _buscar_asignatura<br/>nombre_o_codigo] --> B[Obtener lista de asignaturas<br/>de memoria]

    B --> C{Búsqueda exacta<br/>por código?}
    C -->|Sí| D[✅ Retornar asignatura]
    C -->|No| E{Búsqueda exacta<br/>por nombre?}

    E -->|Sí| D
    E -->|No| F[Fuzzy matching con rapidfuzz<br/>WRatio scorer]

    F --> G[Obtener top 3 candidatos<br/>con score > 60%]

    G --> H{¿Cuántos candidatos?}
    H -->|0| I[❌ No encontrada]
    H -->|1| J[✅ Única coincidencia<br/>Retornar]
    H -->|2+| K[⚠️ Múltiples coincidencias<br/>Desambiguar]

    K --> L[Construir prompt LLM]
    L --> M["Prompt:<br/>Usuario pregunta: {pregunta}<br/>Candidatos:<br/>1. {nombre1}<br/>2. {nombre2}<br/><br/>¿Cuál es más probable?"]

    M --> N[🦙 LLM Ollama]
    N --> O[LLM elige el más probable]
    O --> P[Buscar en lista por nombre elegido]
    P --> D

    style N fill:#ff9999
    style D fill:#99ff99
    style I fill:#ff6666
```

**Ejemplo de desambiguación:**

```
Input: "Redes"

Candidatos encontrados:
1. Redes de Computadores (score: 85%)
2. Redes Neuronales (score: 72%)

Prompt a LLM:
"El usuario pregunta por 'Redes'. ¿Se refiere a:
1. Redes de Computadores (obligatoria, 3º curso)
2. Redes Neuronales (optativa, 4º curso)
Responde solo con el número."

LLM responde: "1"

Sistema retorna: "Redes de Computadores"
```

---

## 🎨 Detalle: Generación de Respuesta Natural

```mermaid
flowchart TD
    A[📊 Datos estructurados listos] --> B{Tipo de consulta?}

    B -->|Específica| C[Datos de UNA asignatura<br/>+ atributo solicitado]
    B -->|General| D[Lista de asignaturas<br/>o count]

    C --> E[Construir prompt específico]
    D --> F[Construir prompt general]

    E --> G["Prompt:<br/>Genera respuesta natural<br/><br/>Pregunta: {pregunta}<br/>Asignatura: {nombre}<br/>Atributo: {atributo}<br/>Valor: {valor}<br/><br/>Responde de forma conversacional"]

    F --> H["Prompt:<br/>Genera respuesta natural<br/><br/>Pregunta: {pregunta}<br/>Resultados:<br/>1. {asig1}<br/>2. {asig2}<br/>...<br/><br/>Responde en formato lista legible"]

    G --> I[🦙 LLM Ollama]
    H --> I

    I --> J[⏱️ 3-5 segundos]
    J --> K[Respuesta natural generada]

    K --> L[Limpiar formato<br/>eliminar ANSI codes]
    L --> M[💬 Respuesta lista<br/>para el usuario]

    style I fill:#ff9999
    style M fill:#99ff99
```

**Ejemplo:**

```
Input estructurado:
{
  "pregunta": "cuántos créditos tiene Redes",
  "asignatura": "Redes de Computadores",
  "atributo": "creditos",
  "valor": 6
}

Prompt al LLM:
"Genera una respuesta natural y conversacional.
Pregunta: cuántos créditos tiene Redes
Asignatura: Redes de Computadores
Atributo: creditos
Valor: 6

Responde en una frase natural."

LLM genera:
"Redes de Computadores tiene 6 créditos ECTS."

Output al usuario:
"Redes de Computadores tiene 6 créditos ETS."
```

---

## ⏱️ Tiempos de Procesamiento

```mermaid
gantt
    title Desglose de Tiempos (Consulta Específica)
    dateFormat X
    axisFormat %S seg

    section Rasa
    NLU Classification           :0, 1

    section Cache
    Cargar asignaturas (1ª vez)  :1, 2

    section Ollama
    Clasificar tipo              :2, 4
    Extraer datos                :4, 6
    Desambiguar (si necesario)   :6, 8
    Respuesta natural            :8, 12

    section BD
    Query resultados             :12, 13

    section Total
    Tiempo total                 :0, 13
```

| Operación | Tiempo | Notas |
|-----------|--------|-------|
| Rasa NLU | ~0.5-1s | Clasificación de intent |
| Cargar asignaturas | ~1-2s | Solo primera vez |
| LLM: Clasificar | ~2-3s | Con cache de modelo |
| LLM: Extraer | ~2-3s | |
| Búsqueda fuzzy | ~0.05-0.1s | En memoria |
| LLM: Desambiguar | ~2-3s | Solo si múltiples matches |
| Query BD | ~0.1-0.2s | |
| LLM: Respuesta natural | ~3-5s | |
| **TOTAL (sin desambiguación)** | **~8-12s** | |
| **TOTAL (con desambiguación)** | **~10-15s** | |

---

## 🔄 Comparación: Sistema Anterior vs Nuevo

```mermaid
flowchart LR
    subgraph old[Sistema v1.x - Gemini API]
        A1[Usuario] --> B1[Rasa NLU]
        B1 --> C1[Action]
        C1 --> D1[Gemini API<br/>☁️ Cloud]
        D1 -.->|20-30s| E1[Respuesta]
        E1 --> F1[Usuario]
    end

    subgraph new[Sistema v2.0 - Ollama Local]
        A2[Usuario] --> B2[Rasa NLU]
        B2 --> C2[Action]
        C2 --> D2[Ollama HTTP API<br/>💻 Local]
        D2 -.->|2-4s| E2[Respuesta]
        C2 --> F2[Cache Memoria]
        F2 -.-> C2
        E2 --> G2[Usuario]
    end

    style D1 fill:#ffcccc
    style D2 fill:#ccffcc
```

| Aspecto | v1.x (Gemini) | v2.0 (Ollama) | Mejora |
|---------|---------------|---------------|--------|
| **Velocidad LLM** | 20-30s | 2-4s | **5-15x más rápido** |
| **Costo** | $0.10 por 1000 queries | Gratis | **100% ahorro** |
| **Dependencia** | Internet + API key | Local | **Mayor control** |
| **Privacy** | Datos en cloud | Datos locales | **Mayor privacidad** |
| **Cache** | No | Sí (memoria) | **Más eficiente** |

---

## 📚 Resumen para el Profesor

### Puntos Clave del Sistema:

1. **Rasa NLU Pipeline**: Clasifica el intent del usuario usando modelos de ML entrenados (DIET Classifier)

2. **Sistema Text-to-SQL**: Convierte lenguaje natural a consultas SQL estructuradas usando Llama 3

3. **Ollama Local**: LLM local que procesa 4 tipos de tareas:
   - Clasificar tipo de consulta
   - Extraer datos (nombre asignatura + atributo)
   - Desambiguar cuando hay múltiples coincidencias
   - Generar respuestas naturales

4. **Cache en Memoria**: Las asignaturas se cargan una vez por sesión, mejorando performance

5. **Búsqueda Fuzzy Inteligente**: Encuentra asignaturas incluso con errores ortográficos o nombres parciales

6. **Respuestas Naturales**: Elimina respuestas robóticas usando el LLM para generar texto conversacional

### Ventajas del Sistema v2.0:

- ⚡ **5-15x más rápido** que versión anterior
- 💰 **Sin costos de API** (100% local)
- 🔒 **Mayor privacidad** (datos no salen del servidor)
- 🎯 **Más preciso** (desambiguación inteligente)
- 💬 **Más natural** (respuestas conversacionales)
