# Sistema Text-to-SQL para Asignaturas

Sistema de consultas dinámicas usando Llama 3 (Ollama) que convierte lenguaje natural a SQL.

## Características Principales

### ✅ 1. Búsqueda Fuzzy con Desambiguación LLM

El usuario **NO necesita escribir el nombre exacto** de la asignatura:

- **Búsqueda por código**: `"2050016"`, `"IS2"`, `"IA"`
- **Búsqueda por nombre parcial**: `"Redes"` → "Redes de Computadores"
- **Búsqueda con errores**: `"Calculo"` → "Cálculo I"
- **Desambiguación automática**: Si hay múltiples coincidencias, el LLM elige la correcta

**Proceso de búsqueda:**
1. Búsqueda exacta por código
2. Búsqueda con LIKE
3. Fuzzy matching con `rapidfuzz` (similitud > 60%)
4. Si hay múltiples candidatos: LLM desambigua

### ✅ 2. Clasificación Automática de Consultas

El sistema distingue automáticamente entre:

#### **Consultas ESPECÍFICAS** (sobre UNA asignatura)
- "cuántos créditos tiene Redes"
- "qué es IS2"
- "Redes es obligatoria?"
- "en qué curso está Cálculo"

→ **Acción**: Busca la asignatura y devuelve el atributo solicitado

#### **Consultas GENERALES** (con filtros, múltiples resultados)
- "asignaturas de primero"
- "cuántas optativas hay en cuarto"
- "asignaturas del segundo cuatrimestre"
- "dame las obligatorias de tercero"

→ **Acción**: Genera SQL dinámico con filtros

### ✅ 3. Respuestas Naturales con LLM

Todas las respuestas se procesan con el LLM para **eliminar la roboticidad**:

**Antes (robótico):**
```
Redes de Computadores (2050016)
• Curso: 3º
• Créditos: 6 ECTS
• Tipo: Obligatoria
• Duración: Cuatrimestral
```

**Ahora (natural):**
```
Redes de Computadores es una asignatura obligatoria de 6 créditos
que se imparte en tercero durante el primer cuatrimestre.
```

---

## Ejemplos de Uso

### 📚 Consultas Específicas

| Usuario | Sistema |
|---------|---------|
| "cuántos créditos tiene Redes" | "Redes de Computadores tiene 6 créditos ECTS" |
| "qué es IS2" | "Ingeniería del Software II es una asignatura obligatoria de 6 créditos que se imparte en segundo curso..." |
| "Redes es obligatoria?" | "Sí, Redes de Computadores es una asignatura obligatoria" |
| "en qué cuatrimestre está IA" | "Inteligencia Artificial se imparte en el segundo cuatrimestre" |

### 📊 Consultas Generales

| Usuario | Sistema |
|---------|---------|
| "asignaturas de primero" | "Aquí tienes las asignaturas de primer curso: 1. Cálculo I (6 ECTS), 2. Álgebra (6 ECTS)..." |
| "cuántas optativas hay en cuarto" | "Hay 12 asignaturas optativas en cuarto curso" |
| "asignaturas del segundo cuatrimestre" | "En el segundo cuatrimestre tienes 8 asignaturas: 1. Física II, 2. Estructuras de Datos..." |
| "dame las obligatorias de tercero con más de 6 créditos" | SQL dinámico generado |

### 🔍 Búsqueda Fuzzy

| Usuario escribe | Sistema encuentra |
|----------------|-------------------|
| "Redes" | "Redes de Computadores" |
| "IS2" | "Ingeniería del Software II" |
| "Calculo" | "Cálculo I" (fuzzy match) |
| "2050016" | "Redes de Computadores" (por código) |
| "Bases datos" | "Bases de Datos" (fuzzy match) |

---

## Arquitectura Técnica

### Flujo de Ejecución

```
Usuario: "cuántos créditos tiene Redes"
    ↓
1. ActionConsultarAsignaturaDB recibe la pregunta
    ↓
2. clasificar_tipo_consulta_asignatura()
    → Resultado: "específica"
    ↓
3. extraer_datos_consulta_especifica()
    → nombre_asignatura: "Redes"
    → atributo_solicitado: "creditos"
    ↓
4. _buscar_asignatura("Redes")
    a. Búsqueda exacta: ❌
    b. Búsqueda LIKE: ❌
    c. Fuzzy matching: ✅ "Redes de Computadores" (score: 85)
    d. Devuelve asignatura
    ↓
5. _formatear_respuesta_especifica()
    → Datos: {nombre: "Redes de Computadores", creditos: 6}
    → generar_respuesta_natural()
    ↓
6. LLM genera: "Redes de Computadores tiene 6 créditos ECTS"
    ↓
7. Usuario recibe respuesta natural
```

### Componentes

#### 1. **Clasificación de Tipo de Consulta**
```python
clasificar_tipo_consulta_asignatura(pregunta)
# → {"tipo": "especifica|general", "confianza": 0-1}
```

#### 2. **Extracción de Datos (Consultas Específicas)**
```python
extraer_datos_consulta_especifica(pregunta)
# → {"nombre_asignatura": "...", "atributo_solicitado": "creditos|tipo|..."}
```

#### 3. **Generación SQL (Consultas Generales)**
```python
generar_sql_consulta_general(pregunta)
# → {"sql": "SELECT ...", "tipo_query": "count|list"}
```

#### 4. **Búsqueda Fuzzy + Desambiguación**
```python
_buscar_asignatura(nombre)
# 1. Búsqueda exacta
# 2. LIKE
# 3. Fuzzy (rapidfuzz)
# 4. Desambiguación LLM si múltiples candidatos
```

#### 5. **Generación de Respuestas Naturales**
```python
generar_respuesta_natural(pregunta, datos, tipo)
# → Respuesta conversacional generada por LLM
```

---

## Configuración

### Requisitos

- **Ollama** instalado con modelo `llama3`
- **PostgreSQL/Supabase** con tabla `asignaturas`
- **Python**: `rapidfuzz`, `rasa-sdk`

### Slots Necesarios (domain.yml)

```yaml
slots:
  contexto_centro:
    type: text
    initial_value: "ETSII"

  contexto_titulacion:
    type: text

  ultimos_resultados_asignaturas:
    type: any
    influence_conversation: false
```

### Intents

```yaml
intents:
  - consultar_asignatura_db  # Intent principal para Text-to-SQL
```

### Actions

```yaml
actions:
  - action_consultar_asignatura_db  # Action principal
  - action_mostrar_todas_asignaturas  # Mostrar todos los resultados
```

---

## Testing

### Comandos de Prueba

```bash
# Iniciar Rasa
rasa run actions

# En otra terminal
rasa shell

# Probar consultas
Usuario: cuántos créditos tiene Redes
Usuario: qué asignaturas hay en primero
Usuario: dame las optativas de cuarto
Usuario: IS2 es obligatoria?
Usuario: asignaturas del segundo cuatrimestre
```

### Ejemplos de Pruebas Completas

**1. Búsqueda Fuzzy**
```
Usuario: "cuántos créditos tiene Redes"
→ Busca "Redes" con fuzzy
→ Encuentra "Redes de Computadores" (score: 85)
→ Respuesta: "Redes de Computadores tiene 6 créditos ECTS"
```

**2. Consulta General**
```
Usuario: "asignaturas obligatorias de tercero"
→ Clasifica: GENERAL
→ Genera SQL: SELECT ... WHERE curso=3 AND tipologia='Obligatoria'
→ Ejecuta query
→ Respuesta natural: "Aquí tienes las asignaturas obligatorias de tercero: 1. Redes..."
```

**3. Desambiguación**
```
Usuario: "qué es Cálculo"
→ Fuzzy encuentra: ["Cálculo I", "Cálculo II"]
→ LLM desambigua: "Cálculo I" (más probable en contexto general)
→ Respuesta
```

---

## Troubleshooting

### Problema: LLM no responde
**Solución**: Verificar que Ollama esté corriendo:
```bash
ollama list
ollama run llama3
```

### Problema: No encuentra asignaturas
**Solución**:
1. Verificar que la tabla tiene datos con `activa = true`
2. Revisar el filtro de `centro` y `titulacion`
3. Comprobar logs de fuzzy matching

### Problema: Respuestas muy lentas
**Solución**:
1. Reducir timeout de LLM (actualmente 20-25s)
2. Usar modelo más rápido: `llama3:8b` en vez de `llama3`
3. Considerar caché de respuestas comunes

---

## Próximas Mejoras

- [ ] Caché de respuestas frecuentes
- [ ] Soporte para comparaciones ("cuál tiene más créditos: Redes o IS2")
- [ ] Filtros compuestos más complejos
- [ ] Integración con RAG para descripción de asignaturas
- [ ] Contexto de profesores y horarios
- [ ] Modo "debug" para ver SQL generado

---

## Métricas de Rendimiento

| Operación | Tiempo Promedio |
|-----------|----------------|
| Clasificación de consulta | ~3-5s |
| Búsqueda fuzzy | ~50-100ms |
| Generación SQL | ~5-8s |
| Ejecución BD | ~50-200ms |
| Respuesta natural | ~5-10s |
| **TOTAL** | **~15-25s** |

---

## Logs de Ejemplo

```
════════════════════════════════════════════════════════════════════════════
🎓 CONSULTA ASIGNATURA DB
   Pregunta: cuántos créditos tiene Redes
   Centro: ETSII
   Titulación: Todas
════════════════════════════════════════════════════════════════════════════

🔍 Clasificación: especifica (confianza: 0.95)
   Razón: Menciona asignatura específica 'Redes'

📝 Extracción específica:
   Asignatura: Redes
   Atributo: creditos

🔍 Búsqueda fuzzy...
   Candidatos:
   1. Redes de Computadores (score: 85)
   2. Redes Neuronales (score: 72)

🤔 Múltiples coincidencias encontradas, usando LLM para desambiguar...
✅ LLM eligió: Redes de Computadores

✅ Respuesta natural generada: Redes de Computadores tiene 6 créditos ECTS
```
