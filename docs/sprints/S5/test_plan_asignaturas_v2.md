# Plan de pruebas - Asignaturas v2 (RAG / Proyecto Docente)

**Fecha:** 2026-03-20
**Versión:** v2 — Pruebas manuales sobre datos del proyecto docente (RAG)
**Alcance:** Verificar que el bot responde correctamente a preguntas que requieren consultar el proyecto docente vectorizado (RAG), no solo la tabla SQL de asignaturas.

---

## 1. Objetivo

Validar que el sistema RAG devuelve información correcta y coherente extraída de los proyectos docentes reales de las asignaturas del GII-IS (Ingeniería del Software), curso 2025-26.

Las pruebas anteriores (v1) cubrían consultas SQL (créditos, curso, tipología, duración, listados, conteo). Esta batería v2 se centra en la información que **solo existe en el proyecto docente**: profesorado, temario, evaluación, metodología, objetivos, bibliografía, actividades formativas, idioma, etc.

---

## 2. Metodología

- **Ejecución manual:** El tester envía la pregunta al bot y anota la respuesta obtenida.
- **Cobertura:** Se seleccionan **23 asignaturas** (~50% del catálogo), cubriendo los 4 cursos y todas las tipologías (Formación Básica, Obligatoria, Optativa). Se prueban **todos los grupos** de cada asignatura seleccionada.
- **Titulación por defecto:** GII-IS (slot `titulacion = GII-IS`), salvo que se indique otra.
- **Validación:** Se compara la respuesta del bot con los datos reales del PDF del proyecto docente.

---

## 3. Categorías de preguntas RAG

| Cat. | Tipo de pregunta | Palabras clave RAG | Ejemplo |
|------|------------------|--------------------|---------|
| P | **Profesorado** | profesor, profesora, profesorado, imparte, coordinador | "¿Quién da clase en FP grupo 1?" |
| T | **Temario / Contenidos** | temario, tema, contenido, programa | "¿Qué temas se dan en IA?" |
| E | **Evaluación** | evaluación, examen, nota, calificación, aprobar | "¿Cómo se evalúa Redes?" |
| M | **Metodología** | metodología, método, clase | "¿Qué metodología usa PGPI?" |
| O | **Objetivos / Competencias** | objetivo, competencia | "¿Cuáles son los objetivos de Estadística?" |
| A | **Actividades formativas** | actividad, práctica, laboratorio, horas | "¿Cuántas horas de laboratorio tiene Criptografía?" |
| I | **Idioma** | idioma, lengua, inglés | "¿En qué idioma se imparte ADDA grupo 5?" |

---

## 4. Asignaturas seleccionadas (23 de 47)

### Curso 1 — Formación Básica / Troncal
| Asignatura | Código | Grupos | Créditos | Duración |
|-----------|--------|--------|----------|----------|
| Fundamentos de Programación | 2050001 | 1-5 | 12 | Anual |
| Cálculo Infinitesimal y Numérico | 2050002 | 1-5 | 12 | Anual |
| Circuitos Electrónicos Digitales | 2050003 | 1-5 | 6 | C1 |
| Introducción a la Matemática Discreta | 2050005 | 1-4, 5(EN) | 6 | C1 |
| Estadística | 2050008 | 1-5 | 6 | C2 |

### Curso 2 — Obligatoria
| Asignatura | Código | Grupos | Créditos | Duración |
|-----------|--------|--------|----------|----------|
| Análisis y Diseño de Datos y Algoritmos | 2050010 | 1-4, 5(EN) | 12 | Anual |
| Lógica Informática | 2050012 | 1-4, 5(EN) | 6 | C1 |
| Redes de Computadores | 2050013 | 1-5 | 6 | C1 |
| Sistemas Operativos | 2050014 | 1-5 | 6 | C1 |
| Arquitectura de Computadores | 2050015 | 1-4, 5(EN) | 6 | C2 |

### Curso 3 — Obligatoria
| Asignatura | Código | Grupos | Créditos | Duración |
|-----------|--------|--------|----------|----------|
| Ingeniería de Requisitos | 2050020 | 1-3, 4(EN) | 6 | C1 |
| Modelado y Simulación Numérica | 2050021 | 1-3, 4(EN) | 6 | C1 |
| Inteligencia Artificial | 2050024 | 1-4 | 6 | C2 |
| Diseño y Pruebas I | 2050048 | 1-4 | 6 | C1 |
| Proceso Software y Gestión I | 2050050 | 1-4 | 6 | C1 |

### Curso 4 — Obligatoria
| Asignatura | Código | Grupos | Créditos | Duración |
|-----------|--------|--------|----------|----------|
| Evolución y Gestión de la Configuración | 2050032 | 1-3 | 6 | C1 |
| Planificación y Gestión de Proyectos Inf. | 2050035 | 1-3 | 6 | C1 |
| Diseño y Pruebas II | 2050049 | 1-4 | 6 | C2 |

### Curso 4 — Optativa
| Asignatura | Código | Grupos | Créditos | Duración |
|-----------|--------|--------|----------|----------|
| Acceso Inteligente a la Información | 2050027 | 1-2 | 6 | C1 |
| Criptografía | 2050030 | 1-2 | 6 | C1 |
| Derecho en la Informática | 2050031 | 1 | 6 | C1 |
| Computación en la Nube y Big Data | 2050037 | 1-2 | 6 | C2 |
| Seguridad de Sist. de Información | 2050043 | 1 | 6 | C2 |

---

## 5. Procedimiento de ejecución

1. Arrancar Rasa (`rasa run --enable-api`) y el Action Server (`rasa run actions`).
2. Establecer el slot de titulación: enviar un mensaje que fije `titulacion = GII-IS`.
3. Para cada fila de la tabla de testing:
   - Enviar la pregunta al bot.
   - Anotar la respuesta obtenida en la columna correspondiente.
   - Comparar con la respuesta esperada (extraída del PDF del proyecto docente).
   - Marcar resultado: OK / KO / PARCIAL.
4. Anotar observaciones si la respuesta es incorrecta o incompleta.

---

## 6. Tabla de pruebas

La tabla con todos los casos de prueba está en:
**[testing/test_rag_asignaturas_v2.md](../../../testing/test_rag_asignaturas_v2.md)**

---

## 7. Criterios de aceptación

| Métrica | Umbral mínimo |
|---------|---------------|
| % de respuestas correctas (OK) | >= 70% |
| % de respuestas parciales aceptables (OK + PARCIAL) | >= 85% |
| Ninguna respuesta con datos inventados (alucinación) | 0 |
| Respuestas RAG que devuelven fallback SQL en vez de plan docente | <= 10% |
