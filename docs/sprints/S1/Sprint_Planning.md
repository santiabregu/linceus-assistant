# Sprint Planning — TFG Chatbot Universidad de Sevilla

## Resumen del Enfoque

- **Sep–Dic (baja carga):** Finalizar **Asignaturas v1 (DB estructurada)** → rellenar tabla de asignaturas (campos clave) + consultas básicas desde Rasa.  
- **RAG de asignaturas (v2):** Inicia en febrero, con tiempo suficiente para extracción, embeddings y QA.  
- **Ene–Mar:** Profesores (DB) + RAG Asignaturas v2.  
- **Mar–May:** Horarios (DB) + RAG Trámites.  
- **Jun:** Frontend + piloto + memoria y defensa.  
- **Cadencia:** Sprints fijos de 2 semanas (lunes–domingo). Carga baja en otoño, media/alta en primavera.  
- **Horas totales estimadas:** ~395 h (dentro del rango 300–400 h).

---

## Plan de Sprints (desde Sprint 2)

> Todos los sprints inician en **lunes** y finalizan en **domingo** (zona horaria Europa/Tirane).  
> El **Sprint 1** ya se realizó: *Sprint Planning + mejora del anteproyecto + comparación tecnológica*.

### Otoño 2025 — Baja carga, cierre de Asignaturas v1 (DB)

- **Sprint 2 (15 Sep – 28 Sep, ~12 h)**  
  - Objetivo: Herramienta de carga de datos de **Asignaturas**.  
  - Entregables:  
    - Script de carga CSV en Python/SQL que suba asignaturas desde un archivo con columnas básicas (código, nombre, curso, créditos, calificación, etc.).  
    - Validaciones mínimas: campos obligatorios, normalización de tildes, duplicados.  
    - Alternativa si no hay tiempo: carga manual inicial desde el panel de Supabase (2–3 asignaturas de prueba).  

- **Sprint 3 (29 Sep – 12 Oct, ~15 h)**  
  - Objetivo: Ingesta mínima + primera consulta desde Rasa.  
  - Entregables: 6–8 asignaturas cargadas + acción Rasa que consulta 1 campo.

- **Sprint 4 (13 Oct – 26 Oct, ~18 h)**  
  - Objetivo: Completar curso objetivo (≈9 asignaturas).  
  - Entregables: intents/entidades + respuestas formateadas.

- **Sprint 5 (27 Oct – 09 Nov, ~18 h)**  
  - Objetivo: Pulido y consistencia “Asignaturas v1 (DB)”.  
  - Entregables: normalización nombres, mensajes de error claros, fallback.

- **Sprint 6 (10 Nov – 23 Nov, ~18 h)**  
  - Objetivo: Testing de la épica Asignaturas v1.  
  - Entregables: golden set ≥ 30 preguntas, unit tests, e2e con historias.  

- **Sprint 7 (24 Nov – 07 Dic, ~12 h)**  
  - Objetivo: Buffer y documentación breve.  
  - Entregables: diagramas de casos de uso + mini guía de datos.

- **Sprint 8 (08 Dic – 21 Dic, ~15 h)**  
  - Objetivo: Remates de Asignaturas v1 y preparación RAG.  
  - Entregables: lista de fuentes RAG + estrategia extracción (scraping/manual).

**Resultado diciembre:** Épica Asignaturas v1 (DB) cerrada y testeada. RAG aún sin empezar, pero con inventario de fuentes listo.

---

### Segundo Cuatrimestre 2026 — Más tiempo y carga uniforme

- **Sprint 9 (22 Dic – 04 Ene, ~8 h)**  
  - Objetivo: Housekeeping + preparación entorno RAG.

- **Sprint 10 (05 Ene – 18 Ene, ~18 h)**  
  - Objetivo: Esquema y carga Profesores.  
  - Entregables: consultas básicas “correo de…” / “despacho de…”.

- **Sprint 11 (19 Ene – 01 Feb, ~20 h)**  
  - Objetivo: Tutorías + búsqueda por asignatura.  
  - Entregables: tabla tutorías, normalización nombres, mini golden set.

- **Sprint 12 (02 Feb – 15 Feb, ~22 h)**  
  - Objetivo: RAG Asignaturas v2 — descubrimiento + extracción.  
  - Entregables: mapa de URLs, extractor PDF/HTML, chunking.

- **Sprint 13 (16 Feb – 01 Mar, ~23 h)**  
  - Objetivo: Embeddings + consulta RAG (pgvector Supabase).  
  - Entregables: acción Rasa RAG con cita (doc+sección).

- **Sprint 14 (02 Mar – 15 Mar, ~22 h)**  
  - Objetivo: QA RAG Asignaturas.  
  - Entregables: golden set ≥ 40, pruebas anti-alucinación.  

- **Sprint 15 (16 Mar – 29 Mar, ~22 h)**  
  - Objetivo: Horarios (DB) — esquema + carga 1 curso.  
  - Entregables: consultas por asignatura/grupo/curso.

- **Sprint 16 (30 Mar – 12 Abr, ~22 h)**  
  - Objetivo: Testing de la épica Horarios.  
  - Entregables: golden set horarios, latencia p95 ≤1s, salida tabla/markdown.

- **Sprint 17 (13 Abr – 26 Abr, ~24 h)**  
  - Objetivo: RAG Trámites — descubrimiento + extracción.  
  - Entregables: scraping/curación + chunking con fechas y enlaces.

- **Sprint 18 (27 Abr – 10 May, ~24 h)**  
  - Objetivo: Embeddings + consultas RAG Trámites.  
  - Entregables: acciones RAG con fuente y fecha.

- **Sprint 19 (11 May – 24 May, ~22 h)**  
  - Objetivo: Testing épica RAG Trámites.  
  - Entregables: golden set ≥ 40, verificación vigencia, no-regresión.

- **Sprint 20 (25 May – 07 Jun, ~24 h)**  
  - Objetivo: Frontend React + piloto.  
  - Entregables: chat mínimo, prueba con 5–10 estudiantes, feedback.

- **Sprint 21 (08 Jun – 21 Jun, ~24 h)**  
  - Objetivo: Memoria y defensa.  
  - Entregables: documento final, slides, checklist criterios de evaluación, ensayo.

---

## Definición: Script de carga CSV

Un script pequeño (Python recomendado) que:  
1. Lee un CSV con columnas acordadas (`codigo_asignatura`, `nombre`, `curso`, `calificacion`, etc.).  
2. Valida (no nulos, tipos, normaliza tildes).  
3. Hace **upsert** en Supabase (insertar o actualizar).  
4. Devuelve log de filas cargadas/errores.  

> Alternativa rápida: importar CSV desde el panel de Supabase o `COPY SQL`, aunque el script permite versionar y repetir cargas.
