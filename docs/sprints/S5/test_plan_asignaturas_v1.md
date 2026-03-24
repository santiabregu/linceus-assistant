# Plan de Testing — Épica Asignaturas v1 (sin RAG)

## 1. Alcance

Se testean las consultas sobre atributos de la tabla `asignaturas` **sin** el módulo de vectorización/RAG.
Los 4 actions bajo prueba son:

| Action | Intent asociado | Descripción |
|--------|----------------|-------------|
| `action_consulta_especifica` | `consulta_asignatura_especifica` | Info de UNA asignatura concreta |
| `action_consulta_listado` | `consulta_asignaturas_listado` | Listar asignaturas con filtros |
| `action_consulta_conteo` | `consulta_asignaturas_conteo` | Contar asignaturas con filtros |
| `action_mostrar_todas_asignaturas` | `pedir_mas_resultados` | Paginación de resultados previos |

---

## 2. Esquema de la tabla `asignaturas`

```sql
CREATE TABLE asignaturas (
    id UUID PRIMARY KEY,
    titulacion_id UUID,            -- FK a titulaciones
    departamento_id UUID,          -- FK a departamentos
    codigo VARCHAR(20),            -- Ej: "2050001"
    nombre VARCHAR(200),           -- Ej: "Fundamentos de Programación"
    curso INTEGER,                 -- 1, 2, 3 o 4
    creditos DECIMAL(4,1),         -- 6.0 o 12.0
    duracion VARCHAR(10),          -- 'A' (anual), 'C1' (1er cuatri), 'C2' (2º cuatri)
    tipologia VARCHAR(50),         -- 'TRONCAL', 'OBLIGATORIA', 'OPTATIVA', 'FORMACION_BASICA'
    es_formacion_basica BOOLEAN,
    es_optativa BOOLEAN,
    nombre_normalizado VARCHAR(200),
    activa BOOLEAN DEFAULT true
);
```

**Valores posibles:**
- `curso`: 1, 2, 3, 4
- `creditos`: 6, 12
- `duracion`: `A` (anual), `C1` (1er cuatrimestre), `C2` (2º cuatrimestre)
- `tipologia`: `TRONCAL`, `OBLIGATORIA`, `OPTATIVA`, `FORMACION_BASICA`

---

## 3. Datos existentes en la BD

| Titulación | Código | Asignaturas | Total ECTS |
|-----------|--------|-------------|------------|
| Grado en Ing. Informática - Ingeniería del Software | GII-IS | 42 | 240 |
| Grado en Ing. Informática - Ingeniería de Computadores | GII-IC | 44 | 240 |
| Grado en Ing. Informática - Tecnologías Informáticas | GII-TI | 52 | 240 |
| **Total** | | **138** | |

### Asignaturas de referencia para pruebas (GII-IS)

| Código | Nombre | Curso | ECTS | Duración | Tipología |
|--------|--------|-------|------|----------|-----------|
| 2050001 | Fundamentos de Programación | 1 | 12 | A | FORMACION_BASICA |
| 2050002 | Cálculo Infinitesimal y Numérico | 1 | 6 | C1 | FORMACION_BASICA |
| 2050008 | Estadística | 1 | 6 | C2 | FORMACION_BASICA |
| 2050010 | Análisis y Diseño de Datos y Algoritmos | 2 | 6 | C1 | OBLIGATORIA |
| 2050013 | Redes de Computadores | 2 | 6 | C1 | OBLIGATORIA |
| 2050014 | Sistemas Operativos | 2 | 6 | C1 | OBLIGATORIA |
| 2050024 | Inteligencia Artificial | 3 | 6 | C2 | OBLIGATORIA |
| 2050048 | Diseño y Pruebas I | 3 | 6 | C1 | OBLIGATORIA |
| 2050030 | Criptografía | 4 | 6 | C1 | OPTATIVA |
| 2050045 | Trabajo Fin de Grado | 4 | 12 | C2 | TRONCAL |
| 2050035 | Planificación y Gestión de Proy. Informáticos | 4 | 6 | C1 | OBLIGATORIA |

### Asignaturas de referencia para pruebas (GII-IC)

| Código | Nombre | Curso | ECTS | Duración | Tipología |
|--------|--------|-------|------|----------|-----------|
| 2040001 | Fundamentos de Programación | 1 | 12 | A | FORMACION_BASICA |
| 2040017 | Redes de Computadores | 2 | 6 | C2 | OBLIGATORIA |

### Asignaturas de referencia para pruebas (GII-TI)

| Código | Nombre | Curso | ECTS | Duración | Tipología |
|--------|--------|-------|------|----------|-----------|
| 2060001 | Fundamentos de Programación | 1 | 12 | A | FORMACION_BASICA |
| 2060021 | Inteligencia Artificial | 3 | 6 | C1 | OBLIGATORIA |

---

## 4. Enfoques de testing aplicables desde Rasa

Tras investigar las capacidades de testing de Rasa, se seleccionan las siguientes técnicas para este proyecto:

### 4.1. Test de NLU (`rasa test nlu`)
**Aplicable: SÍ**
- Evalúa la clasificación de intents y la extracción de entidades (`nombre_asignatura`).
- Se ejecuta con `rasa test nlu --nlu data/nlu/asignaturas.yml` o cross-validation con `-f 5`.
- Genera confusion matrix, F1 por intent, y reportes de errores.
- **Relevante porque**: nuestros actions dependen del intent correcto Y de la entidad `nombre_asignatura` extraída. Si el NLU falla, el action correcto ni se ejecuta.

### 4.2. Test de stories / diálogo (`rasa test core`)
**Aplicable: SÍ**
- Verifica que ante un intent determinado, se ejecuta el action correcto.
- Archivos en `tests/` con prefijo `test_`.
- Se ejecuta con `rasa test --stories tests/ --fail-on-prediction-errors`.
- **Relevante porque**: valida que `consulta_asignatura_especifica` → `action_consulta_especifica`, etc.

### 4.3. Unit tests de custom actions (pytest)
**Aplicable: SÍ — principal enfoque para v1**
- Tests Python con pytest que instancian los actions, crean Trackers mock con intents y entidades predefinidos, y validan los resultados.
- Se usan `CollectingDispatcher` (real), `Tracker.from_dict()` o `MagicMock`, y un `domain` vacío.
- **Relevante porque**: los actions contienen lógica interna compleja (detección de titulación con LLM, generación Text-to-SQL, fuzzy matching, detección de seguimiento). El unit test permite aislar cada pieza.
- **Particularidad de este proyecto**: los actions internamente revisan el intent (`tracker.latest_message["intent"]`) para decidir flujos, así que los mocks deben incluir `latest_message.intent.name` y `latest_message.intent.confidence`.

### 4.4. Test E2E (`rasa test e2e`)
**Aplicable: PARCIAL**
- Solo disponible en Rasa Pro / CALM. Si usamos Rasa OSS, el equivalente son test stories con texto completo del usuario.
- **Limitación**: no ejecuta el action server real, así que no valida la respuesta SQL. Se complementa con los unit tests.

### 4.5. Validación de datos (`rasa data validate`)
**Aplicable: SÍ**
- Detecta stories conflictivas donde la misma secuencia de intents lleva a actions distintos.
- Ejecutar: `rasa data validate stories --max-history 5`.

### Enfoque combinado elegido

| Nivel | Herramienta | Qué valida |
|-------|-------------|------------|
| **NLU** | `rasa test nlu` | Intent correcto + entidad `nombre_asignatura` extraída |
| **Diálogo** | `rasa test core` | Intent → action mapping correcto |
| **Action (lógica)** | pytest + mocks | SQL generada, datos devueltos, respuesta del dispatcher |
| **Integración** | Test manual / script | Pregunta real → respuesta final (con BD y LLM reales) |

---

## 5. Metodología de las pruebas de integración

Cada caso de prueba se ejecuta **2 veces** (3 en casos de complejidad extra) para validar consistencia del LLM.

**Entrada:**
1. Pregunta del usuario (texto libre)
2. Contexto previo (titulación en slot, asignatura previa si aplica)

**Resultados esperados (se validan ANTES del procesamiento LLM de la respuesta):**
- Intent clasificado
- Action ejecutado
- Entidades extraídas
- JSON de la asignatura devuelto por la query SQL (atributos crudos)

**Resultados obtenidos:**
- Se capturan los mismos campos desde los logs del action server (los `print()` ya existentes en el código).

### Tipos de prueba

| Tipo | Descripción |
|------|-------------|
| **P** (Positiva) | Asignatura existe en la BD. Se espera respuesta correcta con datos reales. |
| **N** (Negativa) | Asignatura NO existe en la BD. Se espera mensaje de "no encontrada" o fallback. |
| **F** (Fuera de ámbito) | Pregunta no relacionada con universidad. Se espera rechazo amable. |
| **S** (Seguimiento) | Pregunta sin nombre de asignatura, usando contexto de la anterior. |
| **T** (Cross-titulación) | Pregunta sobre asignatura de otra titulación o sin titulación definida. |

---

## 6. Casos de prueba

### 6.1. `action_consulta_especifica` — Consultas de una asignatura

#### Positivas — Atributo concreto

| ID | Consulta | Contexto (slot titulación) | Intent esperado | Action esperado | Entidad esperada | Atributos esperados del JSON | Ejecuciones |
|----|---------|---------------------------|----------------|----------------|-----------------|------------------------------|-------------|
| E-P01 | "¿Cuántos créditos tiene Redes?" | GII-IS | consulta_asignatura_especifica | action_consulta_especifica | nombre_asignatura: "Redes" | `{nombre: "Redes de Computadores", creditos: 6, codigo: "2050013"}` | 2 |
| E-P02 | "¿En qué curso está Cálculo?" | GII-IS | consulta_asignatura_especifica | action_consulta_especifica | nombre_asignatura: "Cálculo" | `{nombre: "Cálculo Infinitesimal y Numérico", curso: 1}` | 2 |
| E-P03 | "¿Fundamentos de Programación es anual?" | GII-IS | consulta_asignatura_especifica | action_consulta_especifica | nombre_asignatura: "Fundamentos de Programación" | `{nombre: "Fundamentos de Programación", duracion: "A"}` | 2 |
| E-P04 | "¿Estadística es obligatoria?" | GII-IS | consulta_asignatura_especifica | action_consulta_especifica | nombre_asignatura: "Estadística" | `{nombre: "Estadística", tipologia: "FORMACION_BASICA"}` | 2 |
| E-P05 | "¿Criptografía es optativa?" | GII-IS | consulta_asignatura_especifica | action_consulta_especifica | nombre_asignatura: "Criptografía" | `{nombre: "Criptografía", tipologia: "OPTATIVA", es_optativa: true}` | 2 |
| E-P06 | "¿De qué cuatrimestre es IA?" | GII-IS | consulta_asignatura_especifica | action_consulta_especifica | nombre_asignatura: "IA" | `{nombre: "Inteligencia Artificial", duracion: "C2"}` | 2 |

#### Positivas — Información general

| ID | Consulta | Contexto | Intent esperado | Action esperado | Entidad esperada | Atributos esperados del JSON | Ejecuciones |
|----|---------|---------|----------------|----------------|-----------------|------------------------------|-------------|
| E-P07 | "Información sobre Sistemas Operativos" | GII-IS | consulta_asignatura_especifica | action_consulta_especifica | nombre_asignatura: "Sistemas Operativos" | `{nombre: "Sistemas Operativos", curso: 2, creditos: 6, duracion: "C1", tipologia: "OBLIGATORIA"}` | 2 |
| E-P08 | "Háblame de Diseño y Pruebas" | GII-IS | consulta_asignatura_especifica | action_consulta_especifica | nombre_asignatura: "Diseño y Pruebas" | `{nombre: "Diseño y Pruebas I", curso: 3}` (fuzzy match) | 3 |
| E-P09 | "¿Qué es ADDA?" | GII-IS | consulta_asignatura_especifica | action_consulta_especifica | nombre_asignatura: "ADDA" | `{nombre: "Análisis y Diseño de Datos y Algoritmos"}` (alias) | 3 |
| E-P10 | "Dame info del TFG" | GII-IS | consulta_asignatura_especifica | action_consulta_especifica | nombre_asignatura: "TFG" | `{nombre: "Trabajo Fin de Grado", creditos: 12, curso: 4}` (alias) | 2 |
| E-P11 | "Datos de PGPI" | GII-IS | consulta_asignatura_especifica | action_consulta_especifica | nombre_asignatura: "PGPI" | `{nombre: "Planificación y Gestión de Proyectos Informáticos"}` (alias) | 3 |

#### Positivas — Búsqueda por código

| ID | Consulta | Contexto | Intent esperado | Action esperado | Entidad esperada | Atributos esperados del JSON | Ejecuciones |
|----|---------|---------|----------------|----------------|-----------------|------------------------------|-------------|
| E-P12 | "¿Qué asignatura es la 2050001?" | GII-IS | consulta_asignatura_especifica | action_consulta_especifica | nombre_asignatura: "2050001" | `{nombre: "Fundamentos de Programación", codigo: "2050001"}` | 2 |

#### Seguimiento (sin nombre explícito)

| ID | Consulta | Contexto (slots) | Intent esperado | Action esperado | Entidad esperada | Atributos esperados del JSON | Ejecuciones |
|----|---------|------------------|----------------|----------------|-----------------|------------------------------|-------------|
| E-S01 | "¿Y cuántos créditos tiene?" | GII-IS, ultimo_nombre: "Redes de Computadores" | consulta_asignatura_especifica | action_consulta_especifica | (ninguna) | `{nombre: "Redes de Computadores", creditos: 6}` | 2 |
| E-S02 | "¿Es obligatoria?" | GII-IS, ultimo_nombre: "Estadística" | consulta_asignatura_especifica | action_consulta_especifica | (ninguna) | `{nombre: "Estadística", tipologia: "FORMACION_BASICA"}` | 2 |
| E-S03 | "¿Y esa de qué curso es?" | GII-IS, ultimo_nombre: "Criptografía" | consulta_asignatura_especifica | action_consulta_especifica | (ninguna) | `{nombre: "Criptografía", curso: 4}` | 2 |

#### Negativas — Asignatura no existe

| ID | Consulta | Contexto | Intent esperado | Action esperado | Respuesta esperada | Ejecuciones |
|----|---------|---------|----------------|----------------|-------------------|-------------|
| E-N01 | "¿Cuántos créditos tiene Biología?" | GII-IS | consulta_asignatura_especifica | action_consulta_especifica | Mensaje indicando que no se encontró la asignatura | 2 |
| E-N02 | "Información sobre Derecho Penal" | GII-IS | consulta_asignatura_especifica | action_consulta_especifica | Mensaje indicando que no se encontró la asignatura | 2 |
| E-N03 | "¿Qué es Química Orgánica?" | GII-IS | consulta_asignatura_especifica | action_consulta_especifica | Mensaje indicando que no se encontró la asignatura | 2 |

#### Cross-titulación

| ID | Consulta | Contexto | Intent esperado | Action esperado | Resultado esperado | Ejecuciones |
|----|---------|---------|----------------|----------------|-------------------|-------------|
| E-T01 | "¿Cuántos créditos tiene Redes?" | GII-IC | consulta_asignatura_especifica | action_consulta_especifica | `{nombre: "Redes de Computadores", codigo: "2040017"}` (de GII-IC) | 2 |
| E-T02 | "Info de IA" | GII-TI | consulta_asignatura_especifica | action_consulta_especifica | `{nombre: "Inteligencia Artificial", codigo: "2060021"}` (de GII-TI) | 2 |
| E-T03 | "¿Cuántos créditos tiene Redes?" | (sin slot) | consulta_asignatura_especifica | action_consulta_especifica | Mensaje pidiendo que indique la titulación | 2 |
| E-T04 | "Dime sobre Redes en ingeniería del software" | (sin slot) | consulta_asignatura_especifica | action_consulta_especifica | Detecta GII-IS vía LLM + devuelve datos de Redes en GII-IS | 3 |

---

### 6.2. `action_consulta_listado` — Listados con filtros

#### Positivas — Un filtro

| ID | Consulta | Contexto | Intent esperado | Action esperado | Filtros SQL esperados | Resultado esperado | Ejecuciones |
|----|---------|---------|----------------|----------------|----------------------|-------------------|-------------|
| L-P01 | "Dame las asignaturas de primero" | GII-IS | consulta_asignaturas_listado | action_consulta_listado | `curso = 1` | 9 asignaturas de formación básica | 2 |
| L-P02 | "Asignaturas de cuarto" | GII-IS | consulta_asignaturas_listado | action_consulta_listado | `curso = 4` | Obligatorias + optativas + TFG de 4º | 2 |
| L-P03 | "¿Qué optativas hay?" | GII-IS | consulta_asignaturas_listado | action_consulta_listado | `tipologia = 'OPTATIVA'` | Todas las optativas de GII-IS (~14) | 2 |
| L-P04 | "Asignaturas anuales" | GII-IS | consulta_asignaturas_listado | action_consulta_listado | `duracion = 'A'` | Ej: FP (12 ECTS) y Prácticas Externas | 2 |
| L-P05 | "Asignaturas de formación básica" | GII-IS | consulta_asignaturas_listado | action_consulta_listado | `tipologia = 'FORMACION_BASICA'` | 9 asignaturas de 1er curso | 2 |

#### Positivas — Dos filtros combinados

| ID | Consulta | Contexto | Intent esperado | Action esperado | Filtros SQL esperados | Resultado esperado | Ejecuciones |
|----|---------|---------|----------------|----------------|----------------------|-------------------|-------------|
| L-P06 | "Optativas de cuarto" | GII-IS | consulta_asignaturas_listado | action_consulta_listado | `curso = 4, tipologia = 'OPTATIVA'` | ~14 optativas de 4º | 2 |
| L-P07 | "Obligatorias de segundo" | GII-IS | consulta_asignaturas_listado | action_consulta_listado | `curso = 2, tipologia = 'OBLIGATORIA'` | 9 obligatorias de 2º | 2 |
| L-P08 | "Asignaturas de tercero del primer cuatrimestre" | GII-IS | consulta_asignaturas_listado | action_consulta_listado | `curso = 3, duracion = 'C1'` | 5 asignaturas de 3º C1 | 3 |
| L-P09 | "Asignaturas de 12 créditos" | GII-IS | consulta_asignaturas_listado | action_consulta_listado | `creditos = 12` | FP (1º) + TFG (4º) | 2 |

#### Positivas — Paginación

| ID | Consulta | Contexto | Intent esperado | Action esperado | Resultado esperado | Ejecuciones |
|----|---------|---------|----------------|----------------|-------------------|-------------|
| L-P10 | "Dame todas las asignaturas" | GII-IS | consulta_asignaturas_listado | action_consulta_listado | Primeras 8 + mensaje "hay X más, ¿quieres ver todas?" | 2 |
| L-P11 | "Sí, muéstrame todas" | GII-IS (slot ultimos_resultados relleno) | pedir_mas_resultados | action_mostrar_todas_asignaturas | Lista completa de 42 asignaturas | 2 |

#### Negativas — Sin resultados

| ID | Consulta | Contexto | Intent esperado | Action esperado | Resultado esperado | Ejecuciones |
|----|---------|---------|----------------|----------------|-------------------|-------------|
| L-N01 | "Optativas de primero" | GII-IS | consulta_asignaturas_listado | action_consulta_listado | 0 resultados (1º solo tiene formación básica) | 2 |
| L-N02 | "Asignaturas de quinto curso" | GII-IS | consulta_asignaturas_listado | action_consulta_listado | 0 resultados (no existe 5º curso) | 2 |

#### Cross-titulación

| ID | Consulta | Contexto | Intent esperado | Action esperado | Resultado esperado | Ejecuciones |
|----|---------|---------|----------------|----------------|-------------------|-------------|
| L-T01 | "Asignaturas de primero" | GII-IC | consulta_asignaturas_listado | action_consulta_listado | 9 asignaturas de 1º de GII-IC | 2 |
| L-T02 | "Optativas de cuarto" | GII-TI | consulta_asignaturas_listado | action_consulta_listado | Optativas de 4º de GII-TI (≠ GII-IS) | 2 |
| L-T03 | "Dame las asignaturas de segundo" | (sin slot) | consulta_asignaturas_listado | action_consulta_listado | Mensaje pidiendo que indique la titulación | 2 |

---

### 6.3. `action_consulta_conteo` — Contar asignaturas

#### Positivas

| ID | Consulta | Contexto | Intent esperado | Action esperado | COUNT esperado | Ejecuciones |
|----|---------|---------|----------------|----------------|----------------|-------------|
| C-P01 | "¿Cuántas asignaturas hay en primero?" | GII-IS | consulta_asignaturas_conteo | action_consulta_conteo | 9 | 2 |
| C-P02 | "¿Cuántas optativas hay en cuarto?" | GII-IS | consulta_asignaturas_conteo | action_consulta_conteo | ~14 | 2 |
| C-P03 | "¿Cuántas asignaturas tiene la carrera?" | GII-IS | consulta_asignaturas_conteo | action_consulta_conteo | 42 | 2 |
| C-P04 | "¿Cuántas obligatorias de tercero?" | GII-IS | consulta_asignaturas_conteo | action_consulta_conteo | 10 | 2 |
| C-P05 | "Número de asignaturas anuales" | GII-IS | consulta_asignaturas_conteo | action_consulta_conteo | ~2 (FP + Prácticas) | 2 |
| C-P06 | "¿Cuántas de 12 créditos hay?" | GII-IS | consulta_asignaturas_conteo | action_consulta_conteo | 2 (FP + TFG) | 2 |

#### Negativas / Borde

| ID | Consulta | Contexto | Intent esperado | Action esperado | COUNT esperado | Ejecuciones |
|----|---------|---------|----------------|----------------|----------------|-------------|
| C-N01 | "¿Cuántas optativas hay en primero?" | GII-IS | consulta_asignaturas_conteo | action_consulta_conteo | 0 | 2 |
| C-N02 | "¿Cuántas asignaturas de quinto?" | GII-IS | consulta_asignaturas_conteo | action_consulta_conteo | 0 | 2 |

#### Cross-titulación

| ID | Consulta | Contexto | Intent esperado | Action esperado | COUNT esperado | Ejecuciones |
|----|---------|---------|----------------|----------------|----------------|-------------|
| C-T01 | "¿Cuántas asignaturas tiene la carrera?" | GII-IC | consulta_asignaturas_conteo | action_consulta_conteo | 44 | 2 |
| C-T02 | "¿Cuántas asignaturas tiene la carrera?" | GII-TI | consulta_asignaturas_conteo | action_consulta_conteo | 52 | 2 |

---

### 6.4. Pruebas fuera de ámbito (intent `out_of_scope` o similar)

| ID | Consulta | Intent esperado | Respuesta esperada | Ejecuciones |
|----|---------|----------------|-------------------|-------------|
| F-01 | "¿Cuál es la capital de Francia?" | out_of_scope / nlu_fallback | Mensaje tipo "por favor pregúntame sobre la universidad" | 2 |
| F-02 | "¿Me puedes contar un chiste?" | out_of_scope / nlu_fallback | Mensaje redirigiendo al ámbito universitario | 2 |
| F-03 | "¿Qué tiempo hará mañana?" | out_of_scope / nlu_fallback | Mensaje redirigiendo al ámbito universitario | 2 |
| F-04 | "Quiero pedir una pizza" | out_of_scope / nlu_fallback | Mensaje redirigiendo al ámbito universitario | 2 |

---

## 7. Tabla resumen de ejecución

| Categoría | Nº casos | Ejecuciones/caso | Total ejecuciones |
|-----------|----------|-------------------|-------------------|
| Específica — Positiva atributo | 6 | 2 | 12 |
| Específica — Positiva general | 5 | 2-3 | 12 |
| Específica — Por código | 1 | 2 | 2 |
| Específica — Seguimiento | 3 | 2 | 6 |
| Específica — Negativa | 3 | 2 | 6 |
| Específica — Cross-titulación | 4 | 2-3 | 9 |
| Listado — Un filtro | 5 | 2 | 10 |
| Listado — Dos filtros | 4 | 2-3 | 9 |
| Listado — Paginación | 2 | 2 | 4 |
| Listado — Negativa | 2 | 2 | 4 |
| Listado — Cross-titulación | 3 | 2 | 6 |
| Conteo — Positiva | 6 | 2 | 12 |
| Conteo — Negativa | 2 | 2 | 4 |
| Conteo — Cross-titulación | 2 | 2 | 4 |
| Fuera de ámbito | 4 | 2 | 8 |
| **TOTAL** | **52** | | **108** |

---

## 8. Criterios de aceptación

Una prueba se considera **PASADA** si:
1. El **intent** clasificado coincide con el esperado.
2. El **action** ejecutado coincide con el esperado.
3. La **entidad** `nombre_asignatura` se extrae correctamente (cuando aplica).
4. Los **atributos del JSON** devuelto por la query SQL coinciden con los valores reales de la BD.
5. En las pruebas negativas, el bot responde con un mensaje de "no encontrada" (no se cuelga ni devuelve datos incorrectos).
6. En las pruebas fuera de ámbito, el bot no intenta ejecutar un action de asignaturas.
7. El resultado es **consistente** entre las 2-3 ejecuciones del mismo caso.

**Umbral de aprobación**: ≥90% de los casos pasados (≥47 de 52).

---

## 9. Notas de implementación para la automatización

### Captura de resultados en los actions
Los actions ya tienen `print()` con los datos relevantes. Para automatizar:
- Redirigir stdout del action server a un log parseado.
- O interceptar `dispatcher.messages` y `SlotSet` events en los tests pytest.

### Estructura de los unit tests con pytest

```python
# tests/test_asignaturas_v1.py
import pytest
from unittest.mock import MagicMock, patch
from rasa_sdk import Tracker
from rasa_sdk.executor import CollectingDispatcher
from actions.asignaturas.actions import ActionConsultaEspecifica

@pytest.fixture
def dispatcher():
    return CollectingDispatcher()

def make_tracker(text, intent, entities=None, slots=None):
    """Crea un Tracker mock con los datos necesarios."""
    return Tracker(
        sender_id="test",
        slots=slots or {"contexto_titulacion": "GII-IS"},
        latest_message={
            "text": text,
            "intent": {"name": intent, "confidence": 0.95},
            "entities": entities or [],
        },
        events=[],
        paused=False,
        followup_action=None,
        active_loop={},
        latest_action_name="action_listen",
    )

@patch("actions.asignaturas.actions.generar_sql_especifica")
@patch("actions.asignaturas.actions.ejecutar_query")
@patch("actions.asignaturas.actions.generar_respuesta_natural")
def test_E_P01_creditos_redes(mock_resp, mock_query, mock_sql, dispatcher):
    mock_sql.return_value = {"sql": "...", "parametros": [], "necesita_rag": False}
    mock_query.return_value = (True, [{"nombre": "Redes de Computadores", "creditos": 6, "codigo": "2050013"}])
    mock_resp.return_value = "Redes de Computadores tiene 6 créditos."

    tracker = make_tracker(
        text="¿Cuántos créditos tiene Redes?",
        intent="consulta_asignatura_especifica",
        entities=[{"entity": "nombre_asignatura", "value": "Redes"}],
    )
    action = ActionConsultaEspecifica()
    events = action.run(dispatcher, tracker, {})

    assert len(dispatcher.messages) > 0
    # Validar que se establecen los slots de contexto
    slot_events = [e for e in events if isinstance(e, dict) and e.get("event") == "slot"]
    # ... más aserciones
```

### Ejecución del NLU test

```bash
# Cross-validation de 5 folds
rasa test nlu --cross-validation -f 5

# Test con split fijo
rasa data split nlu
rasa test nlu --nlu train_test_split/test_data.yml
```

### Test de stories

```yaml
# tests/test_asignaturas_stories.yml
stories:
- story: test consulta específica créditos
  steps:
  - user: "¿Cuántos créditos tiene Redes?"
    intent: consulta_asignatura_especifica
  - action: action_consulta_especifica

- story: test consulta listado primero
  steps:
  - user: "Dame las asignaturas de primero"
    intent: consulta_asignaturas_listado
  - action: action_consulta_listado

- story: test consulta conteo
  steps:
  - user: "¿Cuántas asignaturas hay en primero?"
    intent: consulta_asignaturas_conteo
  - action: action_consulta_conteo

- story: test paginación
  steps:
  - user: "Dame todas las asignaturas"
    intent: consulta_asignaturas_listado
  - action: action_consulta_listado
  - user: "Sí, muéstrame todas"
    intent: pedir_mas_resultados
  - action: action_mostrar_todas_asignaturas
```

```bash
rasa test --stories tests/test_asignaturas_stories.yml --fail-on-prediction-errors
```
