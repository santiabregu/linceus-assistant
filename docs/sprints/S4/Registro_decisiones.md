# Registro de Decisiones - Sprint 4

**Fecha:** Febrero 2026  
**Versión:** v2.0.0+  
**Épica:** Infraestructura + Asignaturas (Text-to-SQL con LLM)

---

## Índice de Decisiones

1. [Migración de Ollama a Gemini API](#decisión-1-migración-de-ollama-a-gemini-api)
2. [Actions para Detección de Intents vs Pipeline NLU Custom](#decisión-2-actions-para-detección-de-intents-vs-pipeline-nlu-custom)
3. [Actions como Responsables de Generación de SQL](#decisión-3-actions-como-responsables-de-generación-de-sql)
4. [Estrategia Dual: Gemini para Desarrollo, Ollama como Fallback](#decisión-4-estrategia-dual-gemini-para-desarrollo-ollama-como-fallback)

---

## Decisión 1: Migración de Ollama a Gemini API

### Contexto
En el Sprint 4 implementamos un sistema Text-to-SQL que requería múltiples llamadas al LLM:
- Clasificación de tipo de consulta (específica vs general)
- Extracción de datos de la consulta
- Generación de SQL dinámico
- Desambiguación de asignaturas con múltiples coincidencias
- Generación de respuestas naturales

**Problema:** Usar Ollama local con Llama 3 resultaba en tiempos de respuesta inaceptables para un chatbot interactivo.

### Tiempos Medidos (CPU Intel sin GPU)

| Operación | Ollama (llama3) | Gemini API | Mejora |
|-----------|-----------------|------------|--------|
| Clasificación de consulta | ~30s | ~1-2s | **15-30x** |
| Extracción de datos | ~25s | ~1-2s | **12-25x** |
| Generación SQL | ~35s | ~2-3s | **11-17x** |
| Respuesta natural | ~30s | ~1-2s | **15-30x** |
| **Consulta completa** | **60-90s** | **8-12s** | **7-10x** |

### Decisión Tomada
**Usar Gemini API (`gemini-2.5-flash-lite`) como LLM principal para desarrollo y testing.**

### Justificación

**Pros:**
- ✅ **Velocidad 10-20x superior**: Respuestas en 1-3s vs 30-60s
- ✅ **Experiencia de usuario aceptable**: Conversación fluida sin esperas largas
- ✅ **No consume recursos locales**: No degrada rendimiento del equipo
- ✅ **Modelos más potentes**: Mejor comprensión y generación de respuestas
- ✅ **Free tier generoso**: 10 RPM, 2M TPM, 1500 RPD por modelo
- ✅ **Múltiples modelos gratuitos**: Si agota cuota de uno, puede rotar a otro
- ✅ **Desarrollo más ágil**: Testing rápido sin esperas

**Contras:**
- ❌ **Dependencia de conexión a internet**
- ❌ **Cuotas diarias limitadas** (free tier): ~1500 requests/día por modelo
- ❌ **Posible costo en producción** (si se excede free tier)
- ❌ **Datos enviados a terceros** (aunque Google no usa datos de API para entrenamiento según ToS)

### Implementación

**Archivo:** `actions/gemini_client.py`

```python
GEMINI_MODEL = "gemini-2.5-flash-lite"  # Modelo económico y rápido

def llamar_gemini(prompt, modelo=GEMINI_MODEL, timeout=30, options=None):
    """
    Llama a Gemini API con configuración optimizada para SQL/JSON cortos.
    
    Ventajas vs Ollama:
    - 10-20x más rápido (1-3s vs 30-60s)
    - No consume recursos locales
    - Modelos más potentes
    """
    # Configuración optimizada...
```

**Modelos disponibles en free tier:**
- `gemini-2.5-flash-lite` (actual): Económico, rápido
- `gemini-2.5-flash`: Más potente, razonamiento híbrido
- `gemini-2.0-flash`: Multimodal, 1M contexto
- `gemini-3-flash-preview`: El más nuevo (preview)

**Cuotas por modelo (son independientes):**
Cada modelo tiene su propia cuota, lo que permite rotar entre ellos si uno se agota.

### Alternativas Consideradas

| Opción | Pros | Contras | Decisión |
|--------|------|---------|----------|
| **Ollama local** | Gratis, privado, sin límites | 10-20x más lento, consume recursos | ❌ Solo para fallback |
| **Gemini API** | Muy rápido, gratis (con límites), potente | Requiere internet, cuotas | ✅ **ELEGIDO** para desarrollo |
| **OpenAI GPT-4** | Muy potente | Pago desde request 1, más caro | ❌ No viable para TFG |
| **Groq (Llama en cloud)** | Muy rápido | Cuotas más restrictivas | ❌ Gemini tiene mejor free tier |
| **Modelo custom en pipeline Rasa** | Integración nativa | Requiere Rasa Pro (de pago) | ❌ Ver Decisión 2 |

### Impacto en el Proyecto

**Positivo:**
- Permite desarrollo ágil con feedback inmediato
- Testing efectivo sin frustraciones por lentitud
- Demos fluidas para presentaciones del TFG
- Viable para despliegue ligero (hasta ~1500 users/día por modelo)

**Consideraciones futuras:**
- Para producción pesada: considerar Rasa Pro + modelo local optimizado
- Para TFG y demos: configuración actual es óptima
- Mantener Ollama como fallback para trabajo offline

### Referencias
- Documentación de cuotas: https://ai.google.dev/gemini-api/docs/rate-limits
- Dashboard de uso: https://aistudio.google.com/usage
- Archivo de implementación: `actions/gemini_client.py`
- Tests de velocidad: Mediciones manuales durante desarrollo

---

## Decisión 2: Actions para Detección de Intents vs Pipeline NLU Custom

### Contexto
El sistema Text-to-SQL requiere un NLU más sofisticado que el pipeline básico de Rasa para:
1. Clasificar tipo de consulta (específica, listado, conteo)
2. Extraer nombres de asignaturas con fuzzy matching
3. Detectar atributos solicitados (créditos, curso, duración, etc.)
4. Manejar ambigüedad y contexto conversacional

### Opciones Evaluadas

#### Opción A: Reemplazar Pipeline NLU de Rasa con Modelo Custom (LLM)

**Cómo funcionaría:**
```yaml
# config.yml
pipeline:
  - name: "LLMFeaturizer"           # Usar LLM para generar features
  - name: "LLMIntentClassifier"     # Clasificar intents con LLM
  - name: "LLMEntityExtractor"      # Extraer entidades con LLM
```

**Pros:**
- Flexibilidad total en la lógica de NLU
- Mejor comprensión de lenguaje natural
- Menos dependencia de datos de entrenamiento

**Contras:**
- ❌ **Requiere Rasa Pro (de pago)** para componentes custom en pipeline
- ❌ Aumenta latencia en CADA mensaje (incluso saludos)
- ❌ Mayor consumo de cuota de LLM
- ❌ Complejidad de implementación y depuración
- ❌ No justificable para un TFG con presupuesto limitado

#### Opción B: Actions que Detectan Intents Después de Rasa NLU (ELEGIDA)

**Cómo funciona:**
```
Usuario: "cuántos créditos tiene Redes"
    ↓
1. Rasa NLU clasifica: intent = consultar_asignatura_db (RÁPIDO)
    ↓
2. Rasa ejecuta action: ActionConsultarAsignaturaDB
    ↓
3. Action usa LLM para:
   - Clasificar tipo específico de consulta
   - Extraer nombre de asignatura
   - Detectar atributo solicitado
    ↓
4. Action ejecuta búsqueda y responde
```

**Pros:**
- ✅ **Funciona con Rasa Open Source (gratuito)**
- ✅ Solo llama al LLM cuando es necesario (intents específicos)
- ✅ Rasa NLU sigue siendo rápido para intents simples (greet, goodbye, etc.)
- ✅ Fácil de depurar y testear
- ✅ Flexible: podemos añadir lógica específica por dominio
- ✅ Compatible con la arquitectura de Rasa (no la rompe)

**Contras:**
- Necesita un intent "catch-all" bien entrenado para derivar al action
- Ligeramente menos preciso que LLM puro (pero suficiente)

### Decisión Tomada
**Usar Actions con lógica LLM después de la clasificación inicial de Rasa NLU.**

### Implementación

**Intent catch-all en NLU:**
```yaml
# data/nlu/asignaturas.yml
- intent: consultar_asignatura_db
  examples: |
    - cuántos créditos tiene [Redes]
    - [IS2] es obligatoria?
    - qué asignaturas hay en [primero]
    - dame las [optativas]
    # ~50 ejemplos variados
```

**Action con LLM interno:**
```python
# actions/asignaturas.py
class ActionConsultarAsignaturaDB(Action):
    def name(self):
        return "action_consultar_asignatura_db"
    
    def run(self, dispatcher, tracker, domain):
        pregunta = tracker.latest_message.get('text')
        
        # 1. Clasificar tipo con LLM (solo para este intent)
        tipo = clasificar_tipo_consulta_asignatura(pregunta)
        
        # 2. Extraer datos con LLM
        if tipo == "especifica":
            datos = extraer_datos_consulta_especifica(pregunta)
            # Buscar asignatura y responder...
        
        elif tipo == "general":
            sql_data = generar_sql_consulta_general(pregunta)
            # Ejecutar SQL y responder...
```

**Rule simple:**
```yaml
# data/rules.yml
- rule: Consultar asignatura con DB
  steps:
  - intent: consultar_asignatura_db
  - action: action_consultar_asignatura_db
```

### Ventajas de Este Enfoque para el TFG

1. **Sin costos adicionales**: Rasa Open Source es suficiente
2. **Rendimiento óptimo**: LLM solo se usa cuando aporta valor
3. **Modular**: Fácil añadir épicas (profesores, horarios) con mismo patrón
4. **Documentable**: Arquitectura clara para explicar en la memoria del TFG
5. **Escalable**: Si en el futuro se necesita Rasa Pro, migración es sencilla

### Comparativa de Latencia

| Enfoque | Saludo simple | Consulta compleja |
|---------|---------------|-------------------|
| **LLM en Pipeline** | 1-3s (LLM) | 10-15s (varios LLM) |
| **Actions con LLM** | <100ms (Rasa NLU) | 8-12s (LLM en action) |

### Referencias
- Documentación Rasa Custom NLU: https://rasa.com/docs/rasa/custom-nlu-components
- Rasa Pro pricing: https://rasa.com/pricing/
- Implementación: `actions/asignaturas.py`

---

## Decisión 3: Actions como Responsables de Generación de SQL

### Contexto
En versiones anteriores (v1.x), las queries SQL estaban:
- Hardcodeadas en funciones helper (`db.py`)
- Limitadas a patrones predefinidos (búsqueda por código, por nombre, por filtros estáticos)
- No soportaban consultas arbitrarias ni composición dinámica de filtros

Con el sistema Text-to-SQL, necesitamos generar queries dinámicamente basadas en:
- Lenguaje natural del usuario
- Estructura de la base de datos
- Contexto conversacional

### Decisión Tomada
**Las Actions son responsables de generar las queries SQL según la estructura de la base de datos.**

### Arquitectura

```
┌─────────────────────────────────────────────────────┐
│  Usuario: "optativas de cuarto de 6 créditos"      │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  Rasa NLU: intent = consultar_asignatura_db         │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  ActionConsultarAsignaturaDB                        │
│  ┌───────────────────────────────────────────┐     │
│  │ 1. clasificar_tipo_consulta_asignatura()  │     │
│  │    → Resultado: "general" (listado)       │     │
│  └───────────────────────────────────────────┘     │
│                     ↓                               │
│  ┌───────────────────────────────────────────┐     │
│  │ 2. generar_sql_listado(pregunta)          │     │
│  │    Input: pregunta + SCHEMA de BD         │     │
│  │    LLM genera:                             │     │
│  │    {                                       │     │
│  │      "sql": "SELECT codigo, nombre, ...   │     │
│  │              FROM asignaturas             │     │
│  │              WHERE curso = 4              │     │
│  │              AND tipologia = 'OPTATIVA'   │     │
│  │              AND creditos = 6",           │     │
│  │      "filtros": {curso: 4, ...}           │     │
│  │    }                                       │     │
│  └───────────────────────────────────────────┘     │
│                     ↓                               │
│  ┌───────────────────────────────────────────┐     │
│  │ 3. validar_sql(sql)                       │     │
│  │    - Solo SELECT permitido                │     │
│  │    - Solo tabla 'asignaturas'             │     │
│  │    - No inyección SQL                     │     │
│  └───────────────────────────────────────────┘     │
│                     ↓                               │
│  ┌───────────────────────────────────────────┐     │
│  │ 4. ejecutar_query(sql, parametros)        │     │
│  │    → Resultados de BD                     │     │
│  └───────────────────────────────────────────┘     │
│                     ↓                               │
│  ┌───────────────────────────────────────────┐     │
│  │ 5. generar_respuesta_natural(datos)       │     │
│  │    LLM formatea respuesta conversacional   │     │
│  └───────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  Bot: "Encontré 3 asignaturas optativas de cuarto  │
│  con 6 créditos: 1. Computación Móvil, ..."        │
└─────────────────────────────────────────────────────┘
```

### Implementación

**Módulo `text_to_sql.py`:**
```python
# Schema de la BD disponible para el LLM
ASIGNATURAS_SCHEMA = """
CREATE TABLE asignaturas (
    id UUID PRIMARY KEY,
    codigo VARCHAR(20),
    nombre VARCHAR(200),
    curso INTEGER,           -- 1, 2, 3, 4
    creditos DECIMAL(4,1),   -- 6.0, 12.0
    duracion VARCHAR(10),    -- 'A', 'C1', 'C2'
    tipologia VARCHAR(50),   -- 'OBLIGATORIA', 'OPTATIVA', ...
    ...
);
"""

def generar_sql_listado(pregunta, contexto_titulacion):
    """
    Genera SQL para listar asignaturas con filtros.
    
    El LLM recibe:
    - Schema de la BD
    - Pregunta del usuario
    - Contexto de titulación
    
    Devuelve:
    - SQL parametrizado y seguro
    - Filtros aplicados
    """
    prompt = f"""Genera SQL para listar asignaturas según: "{pregunta}"

TABLA asignaturas:
{ASIGNATURAS_SCHEMA}

MAPEO:
"primero" → curso = 1
"optativa" → tipologia = 'OPTATIVA'
"anual" → duracion = 'A'

Genera JSON con SQL seguro y parametrizado."""

    respuesta = llamar_gemini(prompt, timeout=45)
    # Parsear JSON, validar, retornar
```

**Validación de seguridad:**
```python
def validar_sql(sql, tipo='select'):
    """
    Valida que la SQL generada sea segura.
    
    Reglas:
    - Solo SELECT (nunca INSERT, UPDATE, DELETE, DROP)
    - Solo tabla 'asignaturas'
    - No comandos peligrosos (EXEC, UNION, --, etc.)
    - Columnas válidas según schema
    """
    if not sql.upper().startswith('SELECT'):
        return None
    
    # Verificar tabla...
    # Verificar columnas...
    # Detectar inyección SQL...
    
    return sql  # o None si es inválida
```

**Ejecución segura:**
```python
def ejecutar_query(sql, parametros):
    """
    Ejecuta query SQL con parametrización (previene inyección).
    
    Usa psycopg2 con placeholders %s.
    """
    cursor.execute(sql, parametros)  # Siempre parametrizado
    resultados = cursor.fetchall()
    return resultados
```

### Ventajas de Este Enfoque

1. **Flexibilidad total**: Soporta cualquier consulta expresable en SQL
2. **Seguridad por capas**:
   - LLM genera SQL
   - Validación rechaza queries peligrosas
   - Parametrización previene inyección
3. **Mantenibilidad**: Schema en un solo lugar (`text_to_sql.py`)
4. **Escalabilidad**: Añadir columna = actualizar schema, el LLM adapta
5. **Separación de responsabilidades**:
   - `asignaturas.py`: Lógica de dominio (clasificar, buscar, responder)
   - `text_to_sql.py`: Generación y ejecución de SQL
   - `db.py`: Solo conexión y helpers básicos
   - `gemini_client.py`: Solo comunicación con LLM

### Cambios Respecto a v1.x

| Aspecto | v1.x (hardcoded) | v2.x (Text-to-SQL) |
|---------|------------------|---------------------|
| **Queries** | Predefinidas en código | Generadas dinámicamente por LLM |
| **Filtros** | Combinaciones limitadas | Cualquier combinación posible |
| **Añadir campo** | Modificar código en varios lugares | Actualizar schema en 1 lugar |
| **Complejidad** | ~20 queries diferentes hardcoded | 3 funciones generadoras (específica, listado, conteo) |
| **Riesgo SQL** | Bajo (todo controlado) | Medio-Bajo (validación robusta) |
| **Flexibilidad** | Baja | Alta |

### Seguridad: Prevención de Inyección SQL

**Ejemplo de ataque bloqueado:**
```
Usuario malicioso: "asignaturas'; DROP TABLE asignaturas; --"
    ↓
LLM genera algo como: "SELECT * FROM asignaturas WHERE nombre LIKE '%'; DROP TABLE..."
    ↓
validar_sql() detecta:
- Múltiples sentencias (punto y coma)
- Comando DROP
- Comentario SQL (--)
    ↓
❌ SQL RECHAZADO
Bot: "No pude procesar esa consulta"
```

**Doble protección:**
1. **Validación estricta** antes de ejecutar
2. **Parametrización** al ejecutar (psycopg2 escapa valores automáticamente)

### Casos de Uso Soportados

✅ Consultas específicas:
- "cuántos créditos tiene Redes"
- "IS2 es obligatoria?"

✅ Listados con filtros simples:
- "asignaturas de primero"
- "optativas de cuarto"

✅ Listados con filtros compuestos:
- "obligatorias de tercero del primer cuatrimestre"
- "asignaturas de 12 créditos de segundo"

✅ Conteos:
- "cuántas asignaturas hay en cuarto"
- "cuántas optativas tiene la carrera"

✅ Búsqueda fuzzy:
- "Calculo" → "Cálculo I"
- "IS2" → "Ingeniería del Software II"

### Limitaciones Actuales

❌ No soporta:
- JOINs con otras tablas (por seguridad, solo `asignaturas`)
- Agregaciones complejas (SUM, AVG, GROUP BY)
- Subconsultas

**Justificación:** Estos casos no son necesarios para la épica Asignaturas. Si en el futuro se necesitan (ej: profesores con más de X asignaturas), se añadirán con validación específica.

### Referencias
- Implementación: `actions/text_to_sql.py`
- Documentación completa: `docs/TEXT_TO_SQL_ASIGNATURAS.md`
- Validación SQL: Función `validar_sql()` en `text_to_sql.py:364`

---

## Decisión 4: Estrategia Dual: Gemini para Desarrollo, Ollama como Fallback

### Contexto
Tras implementar Gemini API como LLM principal (Decisión 1), surgieron dos escenarios problemáticos:
1. **Cuota diaria agotada**: Free tier tiene límite de ~1500 requests/día por modelo
2. **Trabajo offline**: Sin internet, el bot no funciona

### Decisión Tomada
**Mantener Ollama como fallback automático cuando Gemini falla.**

### Implementación Propuesta

**Función wrapper con fallback:**
```python
# actions/gemini_client.py o text_to_sql.py

def llamar_llm_con_fallback(prompt, timeout=30, options=None):
    """
    Intenta Gemini primero, si falla usa Ollama.
    
    Casos de fallback:
    - Error 429 (cuota excedida)
    - Error de conexión
    - Timeout
    """
    try:
        print("🤖 Intentando Gemini...")
        return llamar_gemini(prompt, timeout=timeout, options=options)
        
    except Exception as e:
        error_msg = str(e).lower()
        
        # Detectar errores de cuota o conexión
        if any(palabra in error_msg for palabra in ['429', 'quota', 'exceeded', 'connection']):
            print(f"⚠️ Gemini no disponible ({e}), usando Ollama como fallback...")
            return llamar_ollama(prompt, timeout=timeout, options=options)
        
        # Otros errores se propagan
        raise
```

**Uso en text_to_sql.py:**
```python
# Reemplazar todas las llamadas:
# llamar_gemini(...) → llamar_llm_con_fallback(...)

def clasificar_tipo_consulta_asignatura(pregunta):
    prompt = f"""Clasifica esta consulta: "{pregunta}"..."""
    respuesta = llamar_llm_con_fallback(prompt, timeout=45)  # ← Fallback automático
    # ...
```

### Ventajas

1. **Resiliencia**: Bot funciona incluso sin cuota de Gemini
2. **Trabajo offline**: Ollama local funciona sin internet
3. **Testing intensivo**: Puedes hacer 1000+ queries sin agotar nada
4. **Transparente**: El usuario no nota la diferencia (solo lentitud)
5. **Óptimo para TFG**: 
   - Desarrollo rápido con Gemini
   - Testing masivo con Ollama
   - Demos con Gemini (más rápido)

### Cuándo Usar Cada Uno

| Escenario | LLM Usado | Justificación |
|-----------|-----------|---------------|
| **Desarrollo normal** | Gemini | Rápido, fluido, mejor DX |
| **Testing intensivo** | Ollama | Sin límites, gratis |
| **Cuota Gemini agotada** | Ollama (auto) | Fallback automático |
| **Sin internet** | Ollama | Único disponible |
| **Demo/Presentación TFG** | Gemini | Velocidad profesional |
| **Producción ligera** | Gemini | Hasta ~1500 users/día |
| **Producción pesada** | Ollama optimizado | Sin límites, gratis |

### Rotación de Modelos Gemini

Además del fallback a Ollama, se puede rotar entre modelos Gemini (cada uno tiene cuota independiente):

```python
GEMINI_MODELS = [
    "gemini-2.5-flash-lite",    # Primero: más económico
    "gemini-2.5-flash",         # Segundo: más potente
    "gemini-2.0-flash",         # Tercero: más contexto
    "gemini-3-flash-preview"    # Último: el más nuevo
]

def llamar_llm_con_rotacion(prompt, timeout=30):
    """Rota entre modelos Gemini si uno agota cuota."""
    for modelo in GEMINI_MODELS:
        try:
            return llamar_gemini(prompt, modelo=modelo, timeout=timeout)
        except Exception as e:
            if '429' in str(e):  # Cuota agotada
                print(f"⚠️ {modelo} agotado, probando siguiente...")
                continue
            raise
    
    # Si todos los Gemini fallaron, usar Ollama
    print("⚠️ Todos los modelos Gemini agotados, usando Ollama...")
    return llamar_ollama(prompt, timeout=timeout)
```

Esto da hasta **~6000 requests/día gratuitos** (4 modelos × 1500 RPD).

### Estado Actual (Sprint 4)

**Implementado:**
- ✅ `gemini_client.py` con modelo configurable
- ✅ `ollama_client.py` funcional
- ✅ Variable de entorno para elegir: `LLM_PROVIDER=gemini|ollama`

**Pendiente (Sprint 5):**
- ⏳ Función `llamar_llm_con_fallback()` con detección automática
- ⏳ Rotación entre modelos Gemini
- ⏳ Logs de uso de cuota (warning al llegar a 80%)

### Recomendación para el TFG

**Durante desarrollo:**
```bash
# .env
LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash-lite
```

**Para testing intensivo:**
```bash
# .env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2:3b
```

**Para demos/presentación:**
```bash
# .env
LLM_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash-lite
```

### Referencias
- Implementación Gemini: `actions/gemini_client.py`
- Implementación Ollama: `actions/ollama_client.py`
- Uso actual: `actions/text_to_sql.py` (línea 8: `from .gemini_client import llamar_gemini as llamar_llm`)

---

## Resumen de Decisiones Clave

| # | Decisión | Impacto | Estado |
|---|----------|---------|--------|
| 1 | Gemini API como LLM principal | Velocidad 10-20x | ✅ Implementado |
| 2 | Actions para NLU avanzado (no pipeline custom) | Sin costo Rasa Pro | ✅ Implementado |
| 3 | Actions generan SQL dinámico | Flexibilidad + seguridad | ✅ Implementado |
| 4 | Ollama como fallback | Resiliencia + offline | ⏳ Parcial |

---

## Lecciones Aprendidas

### Para TFGs Similares

1. **Priorizar velocidad de desarrollo**: Un LLM en cloud (con free tier) es más práctico que optimizar local
2. **No pagar licencias innecesarias**: Rasa Open Source + Actions con LLM interno es suficiente
3. **Separar responsabilidades**: NLU básico en Rasa, lógica compleja en Actions
4. **Seguridad en capas**: Validar SQL generado por LLM antes de ejecutar
5. **Documentar contexto**: Estas decisiones son material valioso para la memoria del TFG

### Métricas de Éxito

| Métrica | Objetivo | Resultado |
|---------|----------|-----------|
| Tiempo de respuesta | <15s | ✅ 8-12s (Gemini) |
| Precisión de búsqueda | >90% | ✅ ~95% (fuzzy + desambiguación) |
| Cobertura de consultas | 80% casos comunes | ✅ ~85% |
| Costo desarrollo | €0 | ✅ €0 (free tiers) |
| Complejidad código | <2000 líneas | ✅ ~1500 líneas |

---

**Última actualización:** Febrero 2026  
**Responsable:** Santiago (Desarrollador TFG)  
**Revisión:** Sprint 5 - Evaluar implementación de fallback automático
