# Diseño Completo: Intents y Actions - Dominio Asignaturas
## Sistema Multi-Titulación

**Fecha:** 2025-02-15
**Contexto:** 4 titulaciones del Grado en Ingeniería Informática (ETSII, Universidad de Sevilla)
- GII-IS: Ingeniería del Software
- GII-TI: Tecnologías Informáticas
- GII-IC: Ingeniería de Computadores
- GII-SI: Sistemas de Información

**Estimado:** ~200 asignaturas totales (50 por titulación aprox)

---

## 1. ARQUITECTURA DE INTENTS

### 1.1 Intent Principal: `consultar_asignatura_db`

**Propósito:** Intent único que maneja TODAS las consultas sobre asignaturas

**Tipos de consulta que cubre:**

#### A. Consultas específicas (sobre UNA asignatura)
```
"¿Qué es Fundamentos de Programación?"
"¿Cuántos créditos tiene Redes?"
"IS2 de qué curso es?"
"Dime sobre Criptografía"
```

#### B. Consultas de listado (con filtros)
```
"Dame las asignaturas de primero"
"¿Qué optativas hay en cuarto?"
"Asignaturas del segundo cuatrimestre"
"Obligatorias de 6 créditos"
```

#### C. Consultas de conteo
```
"¿Cuántas asignaturas hay en segundo?"
"¿Cuántas optativas de 6 créditos?"
```

#### D. Consultas cross-titulación
```
"¿Redes es igual en todas las carreras?"
"¿Qué asignaturas de TI no están en IS?"
"Comparar optativas de cuarto entre IS y TI"
"Asignaturas comunes entre IS e IC"
```

#### E. Consultas de contexto (seguimiento)
```
"Y esa cuántos créditos tiene?"
"Y en tercero?"
"Y las optativas?"
```

**Razón para UN SOLO intent:**
- Evitar confusión en clasificación (DIET tendría problemas diferenciando "cuántas hay" vs "cuáles hay")
- La action puede clasificar el tipo de consulta internamente con Ollama
- Simplifica el training data
- Mejor manejo de consultas ambiguas

---

### 1.2 Intent Secundario: `pedir_mas_resultados`

**Propósito:** Mostrar resultados paginados o la lista completa

**Ejemplos:**
```
"Ver todas"
"Mostrar el resto"
"Muéstrame todas las asignaturas"
"Sí, quiero ver la lista completa"
```

**Nota:** Este intent se solapa con `affirm`, pero está especializado en contexto de paginación.

---

### 1.3 Intents de Contexto Académico

#### `cambiar_contexto_academico`
**Propósito:** Cambiar la titulación activa del bot

**Ejemplos:**
```
"Cambiar a Tecnologías Informáticas"
"Ver asignaturas de TI"
"Ahora quiero consultar la carrera de Computadores"
"Cambiar a Ingeniería del Software"
"Quiero ver las de Sistemas de Información"
```

**Entidades extraídas:** `nombre_titulacion`

#### `consultar_contexto_academico`
**Propósito:** Preguntar qué titulación está consultando actualmente

**Ejemplos:**
```
"¿Qué carrera estoy consultando?"
"¿De qué titulación son estas asignaturas?"
"¿En qué contexto estoy?"
"Recuérdame qué carrera estoy viendo"
```

---

### 1.4 Intent de Comparación (NUEVO): `comparar_asignaturas_titulaciones`

**Propósito:** Comparar asignaturas entre titulaciones

**Ejemplos:**
```
"Comparar IS y TI"
"¿Qué diferencias hay entre las optativas de IS y las de IC?"
"Asignaturas comunes entre todas las carreras"
"¿Qué asignaturas tiene TI que no tenga IS?"
"Ver el plan de estudios de IS comparado con TI"
```

**Entidades extraídas:**
- `nombre_titulacion` (múltiples instancias)
- `filtro_curso`, `filtro_tipologia`

**Acción:** `action_comparar_titulaciones`

---

## 2. ENTIDADES (Entities)

### 2.1 Entidades Principales

#### `nombre_asignatura`
**Tipo:** Texto libre
**Extracción:** DIET + fuzzy matching en action
**Ejemplos:**
- Nombres completos: "Fundamentos de Programación", "Redes de Computadores"
- Nombres cortos: "Redes", "Cálculo", "IS2"
- Códigos: "2050001", "2050023"
- Variaciones: "Programación", "FP", "FOPro"

#### `nombre_titulacion`
**Tipo:** Catálogo cerrado
**Valores válidos:** GII-IS, GII-TI, GII-IC, GII-SI
**Sinónimos:**
```yaml
- Ingeniería del Software → GII-IS
- Software → GII-IS
- IS → GII-IS
- Tecnologías Informáticas → GII-TI
- Tecnologías → GII-TI
- TI → GII-TI
- Ingeniería de Computadores → GII-IC
- Computadores → GII-IC
- IC → GII-IC
- Sistemas de Información → GII-SI
- Sistemas → GII-SI
- SI → GII-SI
```

**IMPORTANTE:** Crear sinónimos en `domain.yml` para normalización automática

---

### 2.2 Entidades de Filtro

#### `filtro_curso`
**Tipo:** Entero
**Valores:** 1, 2, 3, 4
**Sinónimos:**
```yaml
- primero → 1
- primer curso → 1
- 1º → 1
- segundo → 2
- segundo curso → 2
- 2º → 2
- tercero → 3
- tercer curso → 3
- 3º → 3
- cuarto → 4
- cuarto curso → 4
- 4º → 4
```

#### `filtro_tipologia`
**Tipo:** Catálogo
**Valores:** TRONCAL, OBLIGATORIA, OPTATIVA, FORMACION_BASICA
**Sinónimos:**
```yaml
- obligatoria → OBLIGATORIA
- obligatorias → OBLIGATORIA
- troncal → TRONCAL
- troncales → TRONCAL
- optativa → OPTATIVA
- optativas → OPTATIVA
- formación básica → FORMACION_BASICA
- básicas → FORMACION_BASICA
- basica → FORMACION_BASICA
```

#### `filtro_duracion`
**Tipo:** Catálogo
**Valores:** A (Anual), C1 (Cuatrimestre 1), C2 (Cuatrimestre 2)
**Sinónimos:**
```yaml
- anual → A
- anuales → A
- primer cuatrimestre → C1
- primer cuatri → C1
- cuatrimestre 1 → C1
- C1 → C1
- segundo cuatrimestre → C2
- segundo cuatri → C2
- cuatrimestre 2 → C2
- C2 → C2
```

#### `filtro_creditos`
**Tipo:** Entero
**Valores:** 6, 12
**Extracción:** Regex pattern `(\d+)\s*créditos?`

---

### 2.3 Entidad de Atributo

#### `atributo_asignatura`
**Propósito:** Qué aspecto de la asignatura se pregunta
**Valores:** creditos, curso, duracion, tipologia, departamento, codigo
**Ejemplos:**
```
"¿Cuántos CRÉDITOS tiene Redes?"
"¿De qué CURSO es Cálculo?"
"¿Cuál es la DURACIÓN de IS2?"
"¿Qué TIPO es Programación?"
```

**Uso:** Permite al LLM generar respuestas más precisas

---

## 3. SLOTS (Conversational Memory)

### 3.1 Slots de Contexto Académico

```yaml
contexto_centro:
  type: text
  influence_conversation: false
  mappings:
    - type: custom
  initial_value: "ETSII"

contexto_titulacion:
  type: text
  influence_conversation: false
  mappings:
    - type: custom
  initial_value: "GII-IS"
```

### 3.2 Slots de Memoria de Consulta

```yaml
ultimo_codigo_consultado:
  type: text
  influence_conversation: false
  mappings:
    - type: custom

ultimo_nombre_asignatura:
  type: text
  influence_conversation: false
  mappings:
    - type: custom

ultimos_filtros_aplicados:
  type: any
  influence_conversation: false
  mappings:
    - type: custom
```

**Propósito:** Mantener contexto para consultas de seguimiento como "y esa?" o "y en cuarto?"

### 3.3 Slots de Resultados

```yaml
ultimos_resultados_asignaturas:
  type: any
  influence_conversation: false
  mappings:
    - type: custom

total_resultados_encontrados:
  type: any
  influence_conversation: false
  mappings:
    - type: custom
```

**Propósito:** Paginación de resultados

### 3.4 Slot de Caché (NUEVO)

```yaml
asignaturas_memoria:
  type: any
  influence_conversation: false
  mappings:
    - type: custom
```

**Propósito:** Mantener todas las asignaturas de la titulación actual en memoria para búsqueda rápida

---

## 4. ACTIONS - ESPECIFICACIÓN DETALLADA

### 4.1 `ActionConsultarAsignaturaDB`

**Nombre:** `action_consultar_asignatura_db`

#### Flujo de Ejecución

```python
def run(self, dispatcher, tracker, domain):
    # 1. Obtener contexto académico
    titulacion = tracker.get_slot("contexto_titulacion") or "GII-IS"

    # 2. Cargar asignaturas en memoria (con caché)
    asignaturas = self._cargar_o_cachear(titulacion)

    # 3. Extraer entidades de Rasa
    entities = self._extraer_entidades(tracker)

    # 4. Obtener contexto conversacional
    ultimo_codigo = tracker.get_slot("ultimo_codigo_consultado")
    ultimo_nombre = tracker.get_slot("ultimo_nombre_asignatura")
    ultimos_filtros = tracker.get_slot("ultimos_filtros_aplicados")

    # 5. Analizar consulta con LLM (tipo + intención)
    pregunta = tracker.latest_message.get('text')
    analisis = analizar_consulta_unificado(
        pregunta=pregunta,
        entities=entities,
        ultimo_codigo=ultimo_codigo,
        ultimo_nombre=ultimo_nombre,
        ultimos_filtros=ultimos_filtros
    )

    # 6. Procesar según tipo de consulta
    if analisis['tipo'] == 'especifica':
        return self._procesar_especifica(analisis, asignaturas, ...)
    elif analisis['tipo'] == 'general':
        return self._procesar_general(analisis, asignaturas, ...)
    elif analisis['tipo'] == 'conteo':
        return self._procesar_conteo(analisis, asignaturas, ...)
    else:
        return self._fallback()
```

#### Método: `_procesar_especifica()`

**Casos:**
1. Pregunta sobre UNA asignatura específica
2. Pregunta de seguimiento ("y esa?")

```python
def _procesar_especifica(self, analisis, asignaturas, dispatcher, tracker):
    # 1. Buscar asignatura
    nombre_o_codigo = analisis['asignatura_objetivo']
    asignatura = buscar_en_memoria(nombre_o_codigo, asignaturas)

    if not asignatura:
        # Buscar en TODAS las titulaciones (cross-search)
        resultado_cross = self._buscar_en_otras_titulaciones(nombre_o_codigo)
        if resultado_cross:
            dispatcher.utter_message(
                text=f"⚠️ '{nombre_o_codigo}' no está en {titulacion_actual}, "
                     f"pero sí en {resultado_cross['titulacion']}.\n\n"
                     "¿Quieres cambiar a esa carrera?"
            )
            return [SlotSet("asignatura_encontrada_otra_titulacion", resultado_cross)]
        else:
            dispatcher.utter_message(text=respuesta_no_encontrada(nombre_o_codigo))
            return []

    # 2. Generar respuesta con LLM
    atributo = analisis.get('atributo')  # creditos, curso, etc.
    respuesta = respuesta_template(
        asignatura=asignatura,
        atributo=atributo,
        pregunta=tracker.latest_message['text']
    )

    dispatcher.utter_message(text=respuesta)

    # 3. Actualizar slots de memoria
    return [
        SlotSet("ultimo_codigo_consultado", asignatura['codigo']),
        SlotSet("ultimo_nombre_asignatura", asignatura['nombre']),
    ]
```

#### Método: `_procesar_general()`

**Casos:**
1. Listado con filtros
2. Búsqueda explorativa

```python
def _procesar_general(self, analisis, asignaturas, dispatcher, tracker):
    # 1. Extraer filtros (heurísticas + LLM)
    filtros = extraer_filtros_combinados(
        pregunta=tracker.latest_message['text'],
        analisis_llm=analisis,
        entities_rasa=self._extraer_entidades(tracker)
    )

    # 2. Aplicar filtros
    resultados = filtrar_en_memoria(asignaturas, **filtros)

    # 3. Decidir formato de respuesta
    total = len(resultados)
    MAX_INLINE = 8  # Mostrar directamente hasta 8

    if total == 0:
        respuesta = respuesta_sin_resultados(filtros)
    elif total <= MAX_INLINE:
        # Mostrar todas inline
        respuesta = respuesta_template_lista(
            resultados=resultados,
            filtros=filtros,
            mostrar_todas=True
        )
        return [
            SlotSet("ultimos_resultados_asignaturas", None),  # No hace falta paginar
            SlotSet("ultimos_filtros_aplicados", filtros),
        ]
    else:
        # Mostrar primeras N + ofrecer ver todas
        respuesta = respuesta_template_lista(
            resultados=resultados[:MAX_INLINE],
            filtros=filtros,
            total=total,
            mostrar_todas=False
        )
        respuesta += f"\n\n📋 Mostrando {MAX_INLINE} de {total}. ¿Quieres ver todas?"

        return [
            SlotSet("ultimos_resultados_asignaturas", resultados),
            SlotSet("total_resultados_encontrados", total),
            SlotSet("ultimos_filtros_aplicados", filtros),
        ]

    dispatcher.utter_message(text=respuesta)
    return []
```

#### Método: `_procesar_conteo()`

**Casos:**
1. "¿Cuántas asignaturas hay en X?"

```python
def _procesar_conteo(self, analisis, asignaturas, dispatcher):
    # 1. Extraer filtros
    filtros = extraer_filtros_combinados(...)

    # 2. Contar
    resultados = filtrar_en_memoria(asignaturas, **filtros)
    count = len(resultados)

    # 3. Generar respuesta
    respuesta = respuesta_template_count(count, filtros)

    dispatcher.utter_message(text=respuesta)
    return [SlotSet("ultimos_filtros_aplicados", filtros)]
```

---

### 4.2 `ActionMostrarTodasAsignaturas` (NUEVA IMPLEMENTACIÓN)

**Nombre:** `action_mostrar_todas_asignaturas`

**Propósito:** Mostrar todos los resultados guardados en `ultimos_resultados_asignaturas`

```python
class ActionMostrarTodasAsignaturas(Action):
    def name(self):
        return "action_mostrar_todas_asignaturas"

    def run(self, dispatcher, tracker, domain):
        resultados = tracker.get_slot("ultimos_resultados_asignaturas")
        filtros = tracker.get_slot("ultimos_filtros_aplicados")

        if not resultados:
            dispatcher.utter_message(
                text="No tengo resultados guardados. Haz una consulta primero."
            )
            return []

        # Generar lista completa
        respuesta = respuesta_template_lista_completa(
            resultados=resultados,
            filtros=filtros
        )

        dispatcher.utter_message(text=respuesta)

        # Limpiar slots
        return [
            SlotSet("ultimos_resultados_asignaturas", None),
            SlotSet("total_resultados_encontrados", None),
        ]
```

---

### 4.3 `ActionCompararTitulaciones` (NUEVA)

**Nombre:** `action_comparar_titulaciones`

**Propósito:** Comparar asignaturas entre titulaciones

```python
class ActionCompararTitulaciones(Action):
    def name(self):
        return "action_comparar_titulaciones"

    def run(self, dispatcher, tracker, domain):
        # 1. Extraer titulaciones a comparar
        titulaciones = self._extraer_titulaciones(tracker)

        if len(titulaciones) < 2:
            # Comparar con la titulación actual
            titulacion_actual = tracker.get_slot("contexto_titulacion")
            titulaciones = [titulacion_actual, "GII-TI"]  # Default: comparar con TI

        # 2. Cargar asignaturas de cada titulación
        asigs_por_titulacion = {}
        for tit in titulaciones:
            asigs_por_titulacion[tit] = cargar_asignaturas_titulacion(tit)

        # 3. Extraer filtros (opcional)
        filtros = extraer_filtros_heuristicas(tracker.latest_message['text'])

        # 4. Análisis comparativo
        comparacion = analizar_comparacion(
            asigs_por_titulacion=asigs_por_titulacion,
            filtros=filtros
        )

        # 5. Generar respuesta con LLM
        respuesta = generar_respuesta_comparacion(
            comparacion=comparacion,
            titulaciones=titulaciones,
            pregunta=tracker.latest_message['text']
        )

        dispatcher.utter_message(text=respuesta)
        return []
```

**Función auxiliar: `analizar_comparacion()`**

```python
def analizar_comparacion(asigs_por_titulacion, filtros):
    # Aplicar filtros si existen
    if filtros:
        for tit in asigs_por_titulacion:
            asigs_por_titulacion[tit] = filtrar_en_memoria(
                asigs_por_titulacion[tit], **filtros
            )

    # Encontrar asignaturas comunes (por nombre normalizado)
    nombres_por_tit = {
        tit: {a['nombre_normalizado'] for a in asigs}
        for tit, asigs in asigs_por_titulacion.items()
    }

    comunes = set.intersection(*nombres_por_tit.values())

    # Encontrar únicas por titulación
    unicas = {}
    for tit, nombres in nombres_por_tit.items():
        otras_titulaciones = [n for t, n in nombres_por_tit.items() if t != tit]
        unicas[tit] = nombres - set.union(*otras_titulaciones)

    return {
        'comunes': list(comunes),
        'unicas': unicas,
        'totales': {tit: len(asigs) for tit, asigs in asigs_por_titulacion.items()},
    }
```

---

## 5. FUNCIONES AUXILIARES CRÍTICAS

### 5.1 `analizar_consulta_unificado()`

**Firma:**
```python
def analizar_consulta_unificado(
    pregunta: str,
    entities: dict,
    ultimo_codigo: str = None,
    ultimo_nombre: str = None,
    ultimos_filtros: dict = None
) -> dict:
```

**Retorna:**
```python
{
    'tipo': 'especifica' | 'general' | 'conteo',
    'asignatura_objetivo': str | None,  # Para consultas específicas
    'atributo': str | None,  # creditos, curso, tipologia, etc.
    'filtros': dict,  # Para consultas generales
    'es_seguimiento': bool,  # True si usa contexto previo
}
```

**Implementación con Ollama:**

```python
def analizar_consulta_unificado(pregunta, entities, ultimo_codigo=None,
                                 ultimo_nombre=None, ultimos_filtros=None):

    # Construir prompt con contexto
    contexto_previo = ""
    if ultimo_nombre:
        contexto_previo = f"Última asignatura consultada: {ultimo_nombre} (código: {ultimo_codigo})"
    if ultimos_filtros:
        contexto_previo += f"\nÚltimos filtros aplicados: {ultimos_filtros}"

    prompt = f"""Analiza esta consulta sobre asignaturas universitarias.

CONSULTA: "{pregunta}"

ENTIDADES DETECTADAS: {json.dumps(entities, ensure_ascii=False)}

CONTEXTO PREVIO:
{contexto_previo}

Clasifica la consulta en:
- "especifica": pregunta sobre UNA asignatura concreta (ej: "qué es Redes", "IS2 cuántos créditos tiene")
- "general": listado de asignaturas con filtros (ej: "optativas de cuarto", "asignaturas de segundo")
- "conteo": cuántas asignaturas hay (ej: "cuántas asignaturas hay en primero")

Si es "especifica", indica:
- asignatura_objetivo: nombre o código de la asignatura
- atributo: qué se pregunta (creditos, curso, duracion, tipologia, departamento, descripcion)
- es_seguimiento: true si usa pronombres como "esa", "y esa", "y cuántos"

Si es "general" o "conteo", extrae los filtros:
- filtro_curso: 1, 2, 3, 4
- filtro_tipologia: OBLIGATORIA, OPTATIVA, TRONCAL, FORMACION_BASICA
- filtro_duracion: A, C1, C2
- filtro_creditos: 6, 12

Responde SOLO con JSON válido:
{{
  "tipo": "especifica|general|conteo",
  "asignatura_objetivo": "nombre o codigo",
  "atributo": "creditos|curso|etc",
  "es_seguimiento": true|false,
  "filtros": {{"filtro_curso": 1, "filtro_tipologia": "OPTATIVA"}},
  "confianza": 0.95
}}"""

    respuesta = llamar_ollama(prompt, modelo="llama3.2:3b", temperatura=0.1)

    try:
        return json.loads(respuesta)
    except json.JSONDecodeError:
        # Fallback: usar solo entidades de Rasa
        return construir_analisis_fallback(entities)
```

---

### 5.2 `extraer_filtros_combinados()`

**Propósito:** Combinar filtros de Rasa entities + heurísticas regex + LLM

```python
def extraer_filtros_combinados(pregunta, analisis_llm, entities_rasa):
    filtros = {}

    # 1. Prioridad a entidades de Rasa (más precisas)
    if 'filtro_curso' in entities_rasa:
        filtros['curso'] = entities_rasa['filtro_curso']
    if 'filtro_tipologia' in entities_rasa:
        filtros['tipologia'] = entities_rasa['filtro_tipologia']
    if 'filtro_duracion' in entities_rasa:
        filtros['duracion'] = entities_rasa['filtro_duracion']
    if 'filtro_creditos' in entities_rasa:
        filtros['creditos'] = entities_rasa['filtro_creditos']

    # 2. Complementar con análisis LLM
    if analisis_llm.get('filtros'):
        for key, value in analisis_llm['filtros'].items():
            if key not in filtros and value is not None:
                filtros[key.replace('filtro_', '')] = value

    # 3. Heurísticas regex como último recurso
    if 'curso' not in filtros:
        match = re.search(r'\b(primer|1º|primero|segundo|2º|tercero|3º|cuarto|4º)\s*(curso|año)?\b', pregunta, re.IGNORECASE)
        if match:
            curso_map = {'primer': 1, 'primero': 1, '1º': 1,
                         'segundo': 2, '2º': 2,
                         'tercero': 3, 'tercer': 3, '3º': 3,
                         'cuarto': 4, '4º': 4}
            filtros['curso'] = curso_map.get(match.group(1).lower())

    return filtros
```

---

### 5.3 `respuesta_template()`

**Propósito:** Generar respuesta natural sobre UNA asignatura usando Ollama

```python
def respuesta_template(asignatura: dict, atributo: str = None, pregunta: str = "") -> str:
    """
    Genera respuesta natural sobre una asignatura específica.

    Args:
        asignatura: dict con datos de la asignatura (codigo, nombre, curso, creditos, etc.)
        atributo: atributo específico preguntado (creditos, curso, tipologia, etc.)
        pregunta: pregunta original del usuario (para contextualizar)

    Returns:
        str: Respuesta en lenguaje natural
    """

    # Construir datos estructurados
    datos = f"""
Código: {asignatura['codigo']}
Nombre: {asignatura['nombre']}
Curso: {asignatura['curso']}º
Créditos: {asignatura['creditos']} ECTS
Duración: {DURACION_NOMBRES[asignatura['duracion']]}
Tipología: {asignatura['tipologia']}
Departamento: {asignatura.get('departamento_nombre', 'N/A')}
"""

    # Prompt para Ollama
    prompt = f"""Eres un asistente universitario. Responde esta pregunta sobre una asignatura.

PREGUNTA: "{pregunta}"

DATOS DE LA ASIGNATURA:
{datos}

{"ATRIBUTO ESPECÍFICO PREGUNTADO: " + atributo if atributo else ""}

Genera una respuesta natural, concisa (2-3 frases máximo) y amigable.
- Si preguntan por un atributo específico, céntrate en eso
- Usa formato markdown para énfasis (**)
- No añadas información no pedida
- Sé directo y claro

Respuesta:"""

    respuesta = llamar_ollama(prompt, modelo="llama3.2:3b", max_tokens=100, temperatura=0.2)

    # Post-procesamiento
    respuesta = respuesta.strip()

    # Añadir emoji según tipología
    emoji_map = {
        'OBLIGATORIA': '📗',
        'OPTATIVA': '📘',
        'TRONCAL': '📙',
        'FORMACION_BASICA': '📕'
    }
    emoji = emoji_map.get(asignatura['tipologia'], '📚')

    return f"{emoji} {respuesta}"
```

---

### 5.4 `respuesta_template_lista()`

**Propósito:** Formatear lista de asignaturas de forma legible

```python
def respuesta_template_lista(resultados: list, filtros: dict,
                              total: int = None, mostrar_todas: bool = True) -> str:
    """
    Formatea una lista de asignaturas.

    Args:
        resultados: lista de asignaturas a mostrar
        filtros: filtros aplicados (para intro contextual)
        total: total de resultados (si se está paginando)
        mostrar_todas: si True, muestra todas; si False, indica que hay más

    Returns:
        str: Lista formateada en markdown
    """

    if not resultados:
        return respuesta_sin_resultados(filtros)

    # Intro contextual
    intro = generar_intro_lista(filtros, len(resultados), total)

    # Formatear lista
    lineas = [intro, ""]

    # Agrupar por curso si no hay filtro de curso
    if 'curso' not in filtros and len(resultados) > 5:
        por_curso = {}
        for asig in resultados:
            curso = asig['curso']
            if curso not in por_curso:
                por_curso[curso] = []
            por_curso[curso].append(asig)

        for curso in sorted(por_curso.keys()):
            lineas.append(f"### {curso}º Curso")
            for asig in por_curso[curso]:
                lineas.append(formatear_asignatura_inline(asig))
            lineas.append("")
    else:
        # Lista simple
        for asig in resultados:
            lineas.append(formatear_asignatura_inline(asig))

    return "\n".join(lineas)


def formatear_asignatura_inline(asig: dict) -> str:
    """Formatea una asignatura en una línea"""
    emoji_map = {
        'OBLIGATORIA': '📗',
        'OPTATIVA': '📘',
        'TRONCAL': '📙',
        'FORMACION_BASICA': '📕'
    }
    emoji = emoji_map.get(asig['tipologia'], '📚')

    return (f"{emoji} **{asig['nombre']}** "
            f"({asig['codigo']}) · "
            f"{asig['creditos']} ECTS · "
            f"{asig['curso']}º · "
            f"{DURACION_ABREV[asig['duracion']]}")


def generar_intro_lista(filtros: dict, n_mostrados: int, total: int = None) -> str:
    """Genera introducción contextual para la lista"""

    partes = []

    if 'curso' in filtros:
        partes.append(f"{filtros['curso']}º curso")

    if 'tipologia' in filtros:
        tipo_nombre = {
            'OBLIGATORIA': 'obligatorias',
            'OPTATIVA': 'optativas',
            'FORMACION_BASICA': 'de formación básica',
            'TRONCAL': 'troncales'
        }
        partes.append(tipo_nombre.get(filtros['tipologia'], filtros['tipologia'].lower()))

    if 'duracion' in filtros:
        dur_nombre = {
            'A': 'anuales',
            'C1': 'del primer cuatrimestre',
            'C2': 'del segundo cuatrimestre'
        }
        partes.append(dur_nombre[filtros['duracion']])

    if 'creditos' in filtros:
        partes.append(f"de {filtros['creditos']} créditos")

    if partes:
        descripcion = "Asignaturas " + " ".join(partes)
    else:
        descripcion = "Asignaturas"

    if total and total > n_mostrados:
        return f"**{descripcion}** (mostrando {n_mostrados} de {total}):"
    else:
        return f"**{descripcion}** ({n_mostrados} encontradas):"
```

---

### 5.5 `respuesta_template_count()`

**Propósito:** Responder a consultas de conteo

```python
def respuesta_template_count(count: int, filtros: dict) -> str:
    """
    Genera respuesta para consultas de conteo.

    Ejemplos:
      - "Hay 15 asignaturas optativas en cuarto"
      - "En segundo curso hay 9 asignaturas obligatorias"
    """

    # Construir descripción de filtros
    descripcion_partes = []

    if 'tipologia' in filtros:
        tipo_map = {
            'OBLIGATORIA': 'obligatorias',
            'OPTATIVA': 'optativas',
            'TRONCAL': 'troncales',
            'FORMACION_BASICA': 'de formación básica'
        }
        descripcion_partes.append(tipo_map[filtros['tipologia']])
    else:
        descripcion_partes.append("asignaturas")

    if 'curso' in filtros:
        descripcion_partes.append(f"en {filtros['curso']}º curso")

    if 'duracion' in filtros:
        dur_map = {'A': 'anuales', 'C1': 'del primer cuatrimestre', 'C2': 'del segundo cuatrimestre'}
        descripcion_partes.append(dur_map[filtros['duracion']])

    if 'creditos' in filtros:
        descripcion_partes.append(f"de {filtros['creditos']} créditos")

    descripcion = " ".join(descripcion_partes)

    # Generar respuesta
    if count == 0:
        return f"❌ No hay {descripcion}."
    elif count == 1:
        return f"✅ Hay **1 asignatura** {descripcion}."
    else:
        return f"✅ Hay **{count} asignaturas** {descripcion}."
```

---

### 5.6 `normalizar_texto()`

**Propósito:** Normalizar texto para búsqueda fuzzy

```python
import unicodedata
import re

def normalizar_texto(texto: str) -> str:
    """
    Normaliza texto para búsqueda:
    - Lowercase
    - Quita acentos
    - Quita caracteres especiales (excepto espacios)

    Ejemplos:
      "Ingeniería del Software" → "ingenieria del software"
      "Análisis y Diseño" → "analisis y diseno"
    """
    if not texto:
        return ""

    # Lowercase
    texto = texto.lower()

    # Quitar acentos (NFD = descomponer, luego quitar combining marks)
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(char for char in texto if unicodedata.category(char) != 'Mn')

    # Quitar caracteres especiales (mantener letras, números, espacios)
    texto = re.sub(r'[^a-z0-9\s]', '', texto)

    # Normalizar espacios múltiples
    texto = re.sub(r'\s+', ' ', texto).strip()

    return texto
```

---

## 6. TRAINING DATA - DISEÑO COMPLETO

### 6.1 Estrategia de Training Data

**Objetivo:** 500+ ejemplos totales para cobertura robusta

**Distribución:**
- `consultar_asignatura_db`: 350 ejemplos
  - Consultas específicas (nombre de asignatura): 150
  - Consultas de listado (con filtros): 120
  - Consultas de conteo: 40
  - Consultas de seguimiento: 40
- `pedir_mas_resultados`: 30 ejemplos
- `cambiar_contexto_academico`: 30 ejemplos (↑ desde 8)
- `consultar_contexto_academico`: 20 ejemplos (↑ desde 6)
- `comparar_asignaturas_titulaciones`: 40 ejemplos (NUEVO)

**Total asignaturas:** ~470 ejemplos solo para el dominio de asiganturas

---

### 6.2 Ejemplos con Entidades Anotadas - `consultar_asignatura_db`

#### A. Consultas Específicas (150 ejemplos)

**Nombres completos:**
```yaml
- cuantos creditos tiene [Fundamentos de Programación](nombre_asignatura)
- que es [Redes de Computadores](nombre_asignatura)
- en que curso esta [Análisis y Diseño de Datos y Algoritmos](nombre_asignatura)
- [Ingeniería de Requisitos](nombre_asignatura) es obligatoria?
- dime sobre [Sistemas Operativos](nombre_asignatura)
- informacion de [Bases de Datos](nombre_asignatura)
- [Inteligencia Artificial](nombre_asignatura) cuanto dura
```

**Nombres cortos:**
```yaml
- [Redes](nombre_asignatura) cuantos creditos tiene
- que es [IA](nombre_asignatura)
- [Cálculo](nombre_asignatura) de que curso es
- [Álgebra](nombre_asignatura) es anual
- [IS2](nombre_asignatura) es optativa?
- [ADDA](nombre_asignatura) cuantos creditos
- dime de [Criptografía](nombre_asignatura)
```

**Códigos de asignatura:**
```yaml
- que es la [2050001](nombre_asignatura)
- [2050023](nombre_asignatura) cuantos creditos tiene
- informacion sobre la [2050012](nombre_asignatura)
```

**Consultas de atributos específicos:**
```yaml
- cuantos creditos tiene [Redes](nombre_asignatura)
- en que curso esta [Cálculo](nombre_asignatura)
- de que cuatrimestre es [IS2](nombre_asignatura)
- [Programación](nombre_asignatura) es anual o cuatrimestral
- que tipo de asignatura es [ADDA](nombre_asignatura)
- quien imparte [Fundamentos de Programación](nombre_asignatura)
- que departamento da [Redes](nombre_asignatura)
```

**Consultas de seguimiento (contextuales):**
```yaml
- y cuántos créditos tiene?
- y esa de qué curso es?
- es obligatoria?
- y en qué cuatrimestre está?
- y esa?
- y [Redes](nombre_asignatura)?
- qué hay de [Bases de Datos](nombre_asignatura)?
```

---

#### B. Consultas de Listado (120 ejemplos)

**Por curso:**
```yaml
- asignaturas de primero
- asignaturas de [primer](filtro_curso) curso
- dame las asignaturas de [segundo](filtro_curso)
- que asignaturas hay en [tercero](filtro_curso)
- asignaturas de [cuarto](filtro_curso)
- lista de asignaturas de [1º](filtro_curso)
- cuales son las asignaturas de [2º](filtro_curso)
```

**Por tipología:**
```yaml
- dame las [optativas](filtro_tipologia)
- asignaturas [obligatorias](filtro_tipologia)
- cuales son las [optativas](filtro_tipologia)
- lista de [obligatorias](filtro_tipologia)
- asignaturas de [formación básica](filtro_tipologia)
- las [troncales](filtro_tipologia)
```

**Por duración:**
```yaml
- asignaturas [anuales](filtro_duracion)
- asignaturas del [primer cuatrimestre](filtro_duracion)
- del [segundo cuatrimestre](filtro_duracion)
- dame las [anuales](filtro_duracion)
- asignaturas del [primer cuatri](filtro_duracion)
- las del [C2](filtro_duracion)
```

**Por créditos:**
```yaml
- asignaturas de [6](filtro_creditos) creditos
- asignaturas de [12](filtro_creditos) creditos
- las de [6](filtro_creditos) ECTS
```

**Filtros combinados:**
```yaml
- [optativas](filtro_tipologia) de [cuarto](filtro_curso)
- [obligatorias](filtro_tipologia) de [primero](filtro_curso)
- asignaturas [anuales](filtro_duracion) de [segundo](filtro_curso)
- [optativas](filtro_tipologia) del [segundo cuatrimestre](filtro_duracion)
- [obligatorias](filtro_tipologia) de [6](filtro_creditos) creditos en [tercero](filtro_curso)
- dame las [optativas](filtro_tipologia) de [cuarto](filtro_curso) del [primer cuatrimestre](filtro_duracion)
```

**Consultas abiertas (sin filtros explícitos):**
```yaml
- que asignaturas hay
- lista de asignaturas
- muestrame las asignaturas
- todas las asignaturas
- dame la lista de asignaturas
```

---

#### C. Consultas de Conteo (40 ejemplos)

```yaml
- cuantas asignaturas hay en [primero](filtro_curso)
- cuantas [optativas](filtro_tipologia) hay
- cuantas [obligatorias](filtro_tipologia) en [segundo](filtro_curso)
- cuantas asignaturas del [primer cuatrimestre](filtro_duracion)
- cuantas hay en [cuarto](filtro_curso)
- numero de asignaturas en [tercero](filtro_curso)
- cuantas [anuales](filtro_duracion)
- cuantas asignaturas de [6](filtro_creditos) creditos
- total de [optativas](filtro_tipologia) en [cuarto](filtro_curso)
```

---

### 6.3 Ejemplos - `cambiar_contexto_academico` (30 ejemplos)

```yaml
- cambiar a [Tecnologías Informáticas](nombre_titulacion)
- cambiar a [TI](nombre_titulacion)
- ver asignaturas de [Computadores](nombre_titulacion)
- quiero consultar [Sistemas de Información](nombre_titulacion)
- cambiar de carrera a [IS](nombre_titulacion)
- ahora quiero ver [Ingeniería de Computadores](nombre_titulacion)
- cambiar contexto a [Software](nombre_titulacion)
- ver la carrera de [TI](nombre_titulacion)
- consultar [IC](nombre_titulacion)
- asignaturas de [SI](nombre_titulacion)
- [GII-TI](nombre_titulacion)
- [GII-IC](nombre_titulacion)
- pasar a [Tecnologías](nombre_titulacion)
- ver las de [Computadores](nombre_titulacion)
- cambiar a la carrera de [Sistemas](nombre_titulacion)
```

---

### 6.4 Ejemplos - `comparar_asignaturas_titulaciones` (40 ejemplos)

```yaml
- comparar [IS](nombre_titulacion) y [TI](nombre_titulacion)
- diferencias entre [Software](nombre_titulacion) y [Computadores](nombre_titulacion)
- que asignaturas comunes hay entre [IS](nombre_titulacion) e [IC](nombre_titulacion)
- comparar optativas de [IS](nombre_titulacion) y [TI](nombre_titulacion)
- que tiene [TI](nombre_titulacion) que no tenga [IS](nombre_titulacion)
- asignaturas unicas de [Computadores](nombre_titulacion)
- plan de estudios de [IS](nombre_titulacion) versus [SI](nombre_titulacion)
- comparar las 4 carreras
- diferencias entre todas las titulaciones
- que carreras comparten mas asignaturas
- asignaturas comunes entre [IS](nombre_titulacion) [TI](nombre_titulacion) y [IC](nombre_titulacion)
```

---

## 7. DOMAIN.YML - CONFIGURACIÓN ACTUALIZADA

### 7.1 Intents

```yaml
intents:
  # Conversacionales básicos
  - greet
  - goodbye
  - affirm
  - deny
  - pedir_ayuda
  - bot_challenge

  # NLU fallback
  - nlu_fallback

  # Contexto académico
  - cambiar_contexto_academico
  - consultar_contexto_academico

  # Asignaturas
  - consultar_asignatura_db
  - pedir_mas_resultados
  - comparar_asignaturas_titulaciones  # NUEVO
```

---

### 7.2 Entities con Synonyms

```yaml
entities:
  - nombre_centro
  - nombre_titulacion
  - nombre_asignatura
  - atributo_asignatura
  - filtro_curso
  - filtro_tipologia
  - filtro_duracion
  - filtro_creditos

# Sinónimos para normalización automática
entity_synonyms:
  # Titulaciones
  GII-IS:
    - Ingeniería del Software
    - Software
    - IS
    - ingenieria del software

  GII-TI:
    - Tecnologías Informáticas
    - Tecnologías
    - TI
    - tecnologias informaticas
    - tecnologias

  GII-IC:
    - Ingeniería de Computadores
    - Computadores
    - IC
    - ingenieria de computadores

  GII-SI:
    - Sistemas de Información
    - Sistemas
    - SI
    - sistemas de informacion

  # Cursos
  "1":
    - primero
    - primer curso
    - 1º
    - primer año

  "2":
    - segundo
    - segundo curso
    - 2º
    - segundo año

  "3":
    - tercero
    - tercer curso
    - 3º
    - tercer año

  "4":
    - cuarto
    - cuarto curso
    - 4º
    - cuarto año

  # Tipologías
  OBLIGATORIA:
    - obligatoria
    - obligatorias
    - obli

  OPTATIVA:
    - optativa
    - optativas
    - opta

  FORMACION_BASICA:
    - formación básica
    - formacion basica
    - básica
    - basica
    - básicas
    - basicas
    - FB

  TRONCAL:
    - troncal
    - troncales

  # Duraciones
  A:
    - anual
    - anuales
    - todo el año

  C1:
    - primer cuatrimestre
    - primer cuatri
    - cuatrimestre 1
    - 1er cuatrimestre

  C2:
    - segundo cuatrimestre
    - segundo cuatri
    - cuatrimestre 2
    - 2º cuatrimestre
```

---

### 7.3 Slots Actualizados

```yaml
slots:
  # Contexto académico
  contexto_centro:
    type: text
    influence_conversation: false
    mappings:
      - type: custom
    initial_value: "ETSII"

  contexto_titulacion:
    type: text
    influence_conversation: false
    mappings:
      - type: custom
    initial_value: "GII-IS"

  # Memoria de consulta (seguimiento)
  ultimo_codigo_consultado:
    type: text
    influence_conversation: false
    mappings:
      - type: custom

  ultimo_nombre_asignatura:
    type: text
    influence_conversation: false
    mappings:
      - type: custom

  ultimos_filtros_aplicados:
    type: any
    influence_conversation: false
    mappings:
      - type: custom

  # Resultados y paginación
  ultimos_resultados_asignaturas:
    type: any
    influence_conversation: false
    mappings:
      - type: custom

  total_resultados_encontrados:
    type: any
    influence_conversation: false
    mappings:
      - type: custom

  # Caché de asignaturas de la titulación actual
  asignaturas_memoria:
    type: any
    influence_conversation: false
    mappings:
      - type: custom

  # Cross-titulación search (NUEVO)
  asignatura_encontrada_otra_titulacion:
    type: any
    influence_conversation: false
    mappings:
      - type: custom
```

---

### 7.4 Actions

```yaml
actions:
  # Contexto académico
  - action_cambiar_contexto
  - action_consultar_contexto

  # Asignaturas
  - action_consultar_asignatura_db
  - action_mostrar_todas_asignaturas
  - action_comparar_titulaciones  # NUEVO
```

---

## 8. REGLAS Y STORIES RECOMENDADAS

### 8.1 Rules Actualizadas

```yaml
rules:
  - rule: Consultar asignatura
    steps:
      - intent: consultar_asignatura_db
      - action: action_consultar_asignatura_db

  - rule: Mostrar todas las asignaturas (intent directo)
    steps:
      - intent: pedir_mas_resultados
      - action: action_mostrar_todas_asignaturas

  - rule: Mostrar todas con afirmación (si hay resultados guardados)
    steps:
      - intent: affirm
      - action: action_mostrar_todas_asignaturas
    condition:
      - slot_was_set:
          - ultimos_resultados_asignaturas

  - rule: Cambiar contexto académico
    steps:
      - intent: cambiar_contexto_academico
      - action: action_cambiar_contexto

  - rule: Consultar contexto académico
    steps:
      - intent: consultar_contexto_academico
      - action: action_consultar_contexto

  - rule: Comparar titulaciones
    steps:
      - intent: comparar_asignaturas_titulaciones
      - action: action_comparar_titulaciones
```

---

### 8.2 Stories Recomendadas

```yaml
stories:
  - story: Consulta con seguimiento
    steps:
      - intent: greet
      - action: utter_greet
      - intent: consultar_asignatura_db
        entities:
          - nombre_asignatura: "Redes"
      - action: action_consultar_asignatura_db
      - intent: consultar_asignatura_db  # "y cuántos créditos tiene?"
      - action: action_consultar_asignatura_db

  - story: Cambiar titulación y consultar
    steps:
      - intent: cambiar_contexto_academico
        entities:
          - nombre_titulacion: "TI"
      - action: action_cambiar_contexto
      - intent: consultar_asignatura_db  # "optativas de cuarto"
      - action: action_consultar_asignatura_db

  - story: Consulta con paginación
    steps:
      - intent: consultar_asignatura_db  # "asignaturas de primero"
      - action: action_consultar_asignatura_db
      - slot_was_set:
          - ultimos_resultados_asignaturas
      - intent: affirm  # "sí, quiero ver todas"
      - action: action_mostrar_todas_asignaturas

  - story: Comparar y cambiar de carrera
    steps:
      - intent: comparar_asignaturas_titulaciones
        entities:
          - nombre_titulacion: "IS"
          - nombre_titulacion: "TI"
      - action: action_comparar_titulaciones
      - intent: cambiar_contexto_academico  # "cambiar a TI"
        entities:
          - nombre_titulacion: "TI"
      - action: action_cambiar_contexto
```

---

## 9. CONFIG.YML - AJUSTES RECOMENDADOS

### 9.1 Pipeline NLU

**CRÍTICO:** Eliminar `LLMCommandGenerator` (Rasa Pro only)

```yaml
language: es

pipeline:
  # Tokenización
  - name: WhitespaceTokenizer

  # Feature Extraction
  - name: RegexFeaturizer
  - name: LexicalSyntacticFeaturizer
  - name: CountVectorsFeaturizer
    analyzer: word
    min_ngram: 1
    max_ngram: 2
  - name: CountVectorsFeaturizer
    analyzer: char_wb
    min_ngram: 1
    max_ngram: 4

  # Intent Classification + Entity Extraction
  - name: DIETClassifier
    epochs: 200            # ↑ Aumentar de 150 a 200 con más ejemplos
    batch_size: [64, 256]
    dropout: 0.2
    embedding_dimension: 30
    number_of_transformer_layers: 2
    weight_sparsity: 0.7
    constrain_similarities: true

  # Entity Processing
  - name: EntitySynonymMapper

  # Response Selection (para chitchat)
  - name: ResponseSelector
    epochs: 150

  # Fallback
  - name: FallbackClassifier
    threshold: 0.6
    ambiguity_threshold: 0.15
```

### 9.2 Policies

```yaml
policies:
  - name: MemoizationPolicy
    max_history: 5

  - name: RulePolicy
    core_fallback_threshold: 0.4
    core_fallback_action_name: "utter_default"
    enable_fallback_prediction: true

  - name: UnexpecTEDIntentPolicy
    max_history: 5
    epochs: 100

  - name: TEDPolicy
    max_history: 5
    epochs: 100
    constrain_similarities: true
```

---

## 10. MÉTRICAS DE ÉXITO

### 10.1 KPIs de NLU

| Métrica | Objetivo | Estado Actual Estimado |
|---------|----------|------------------------|
| Intent Accuracy (DIET) | ≥ 92% | ~85% (training data insuficiente) |
| Entity Extraction F1 (nombre_asignatura) | ≥ 85% | ~60% (pocas anotaciones) |
| Entity Extraction F1 (nombre_titulacion) | ≥ 90% | ~40% (solo 6 ejemplos) |
| Fallback Rate | < 10% | ~15% estimado |

**Con las mejoras propuestas (500+ ejemplos, entity synonyms):**
- Intent Accuracy: **95%+**
- Entity F1 (nombre_asignatura): **85%+**
- Entity F1 (nombre_titulacion): **92%+**
- Fallback Rate: **< 7%**

---

### 10.2 KPIs de Actions

| Métrica | Objetivo |
|---------|----------|
| Latencia total (consulta específica) | < 3s (NLU 30ms + Action 2-4s) |
| Latencia total (consulta general) | < 2s (sin LLM, solo filtros) |
| Accuracy de búsqueda fuzzy | ≥ 95% (top-1 correcto) |
| Recall de filtros | ≥ 90% (extraer filtros correctamente) |
| Satisfacción de usuario | ≥ 4.0/5 (encuestas) |

---

## 11. PLAN DE IMPLEMENTACIÓN

### Fase 1: Funciones Base (CRÍTICO)
**Estimado:** 2-3 horas

1. Implementar 6 funciones faltantes en `asignaturas.py`:
   - `normalizar_texto()`
   - `analizar_consulta_unificado()`
   - `extraer_filtros_combinados()`
   - `respuesta_template()`
   - `respuesta_template_lista()`
   - `respuesta_template_count()`

2. Implementar `ActionMostrarTodasAsignaturas`

3. Eliminar `LLMCommandGenerator` de `config.yml`

### Fase 2: Training Data Expandido
**Estimado:** 3-4 horas

1. Expandir `data/nlu/asignaturas.yml` a 350 ejemplos
2. Expandir `data/nlu/contexto.yml` a 50 ejemplos
3. Crear `data/nlu/comparacion.yml` con 40 ejemplos
4. Anotar entidades en todos los ejemplos

### Fase 3: Domain y Config
**Estimado:** 1 hora

1. Actualizar `domain.yml`:
   - Añadir entity_synonyms
   - Añadir nuevos slots
   - Añadir nuevas acciones

2. Actualizar `config.yml`:
   - Ajustar epochs de DIETClassifier a 200

3. Actualizar rules y stories

### Fase 4: Comparación de Titulaciones
**Estimado:** 2-3 horas

1. Implementar `ActionCompararTitulaciones`
2. Implementar funciones auxiliares de comparación
3. Cargar datos de las 4 titulaciones en DB

### Fase 5: Testing
**Estimado:** 2 horas

1. Entrenar modelo: `rasa train`
2. Probar flujos end-to-end en `rasa shell`
3. Validar cross-titulación search
4. Validar consultas de seguimiento

---

## 12. PRÓXIMOS PASOS INMEDIATOS

### ✅ ACCIÓN 1: Eliminar LLMCommandGenerator

```bash
# Editar config.yml y eliminar estas líneas:
# - name: LLMCommandGenerator
#   llm:
#     model: "ollama"
```

### ✅ ACCIÓN 2: Implementar funciones críticas

Orden recomendado:
1. `normalizar_texto()` (más simple)
2. `extraer_filtros_heuristicas()` → renombrar a `extraer_filtros_combinados()`
3. `respuesta_template_count()`
4. `respuesta_template_lista()`
5. `respuesta_template()`
6. `analizar_consulta_unificado()`

### ✅ ACCIÓN 3: Expandir training data

Prioridad:
1. `cambiar_contexto_academico`: subir de 8 a 30 ejemplos
2. `consultar_contexto_academico`: subir de 6 a 20 ejemplos
3. `consultar_asignatura_db`: añadir 100+ ejemplos con variaciones y anotaciones

---

## 13. NOTAS FINALES

### Ventajas del Diseño Propuesto

1. **Escalable**: Añadir nuevas titulaciones solo requiere poblar la DB
2. **Flexible**: Un solo intent principal simplifica NLU
3. **Inteligente**: LLM maneja casos edge y variaciones lingüísticas
4. **Rápido**: Caché en memoria para consultas frecuentes
5. **Robusto**: Fallback a cross-titulación search si no encuentra en actual
6. **Contextual**: Mantiene memoria de última consulta para follow-ups

### Limitaciones Conocidas

1. **Latencia LLM**: 2-4s por consulta que requiere Ollama
2. **Sin RAG aún**: No responde preguntas sobre contenido de planes docentes
3. **Una sola universidad**: Por ahora solo Universidad de Sevilla
4. **Sin horarios**: No integrado con épica de Horarios

### Siguientes Épicas

1. **Profesores** (deps: Asignaturas completo)
2. **Horarios** (deps: Asignaturas + Profesores)
3. **RAG Planes Docentes** (deps: Asignaturas completo)
4. **RAG Trámites** (deps: RAG Planes Docentes)

---

**Documento generado el:** 2025-02-15
**Versión:** 1.0
**Autor:** Claude (LinceUS Assistant Architecture)
