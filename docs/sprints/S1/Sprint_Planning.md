# Sprint Planning — TFG Chatbot Universidad de Sevilla

## Resumen del Enfoque

- **Sep–Dic (baja carga):** Finalizar **Asignaturas v1 (DB estructurada)** + **primera versión básica del frontend**.  
- **Ene–Mar:** Profesores (DB) + RAG Asignaturas v2.  
- **Mar–Abr:** QA RAG Asignaturas + Horarios (DB).  
- **May:** RAG Trámites + entrega memoria y defensa.  
- **Entrega final:** 20 mayo 2026 → memoria, slides y defensa.  
- **Cadencia:** Sprints fijos de **3 semanas** (lunes–domingo).  
- **Horas totales estimadas:** ~395 h (dentro del rango 300–400 h).

---

## Plan de Sprints (desde Sprint 1)

> Todos los sprints inician en **lunes** y finalizan en **domingo** (zona horaria Europa/Madrid — Sevilla).  
> El **Sprint 1** se redefine para cerrar el 22 septiembre.

### Otoño 2025 — Baja carga, Asignaturas v1 (DB) + Frontend inicial

- **Sprint 1 (02 Sep – 22 Sep, ~15 h)**  
  - Objetivo: Arranque real del proyecto.  
  - Entregables:  
    - **Esquema inicial de la base de datos en Supabase** (tablas de asignaturas con campos básicos).  
    - **Arreglos del anteproyecto** (casos de uso y comparativas).  

- **Sprint 2 (23 Sep – 13 Oct, ~18 h)**  
  - Objetivo: Herramienta de carga de datos de Asignaturas.  
  - Entregables:  
    - Script de carga CSV en Python/SQL para asignaturas (código, nombre, curso, créditos, calificación, etc.).  
    - Validaciones mínimas: obligatorios, normalización de tildes, duplicados.  

- **Sprint 3 (14 Oct – 03 Nov, ~18 h)**  
  - Objetivo: Ingesta inicial + primeras consultas desde Rasa.  
  - Entregables: 6–8 asignaturas cargadas + acción Rasa que consulta 1 campo.

- **Sprint 4 (04 Nov – 24 Nov, ~18 h)**  
  - Objetivo: Completar curso objetivo (~9 asignaturas).  
  - Entregables: intents/entidades + respuestas formateadas.

- **Sprint 5 (25 Nov – 15 Dic, ~18 h)**  
  - Objetivo: Pulido Asignaturas v1 + **Primera versión del frontend**.  
  - Entregables:  
    - Normalización de nombres, fallback, mensajes de error.  
    - **Frontend React inicial**: interfaz mínima de chat conectada a Rasa (básico, sin diseño final).  

- **Sprint 6 (16 Dic – 05 Ene, ~15 h)**  
  - Objetivo: Testing de Asignaturas v1.  
  - Entregables: golden set ≥30 preguntas, unit tests, e2e.  

**Resultado enero:** Épica Asignaturas v1 cerrada, con frontend inicial ya funcional. RAG aún sin empezar, pero inventario de fuentes preparado.

---

### Invierno 2026 — Profesores + inicio RAG Asignaturas

- **Sprint 7 (06 Ene – 26 Ene, ~18 h)**  
  - Objetivo: Profesores (esquema y carga inicial).  
  - Entregables: consultas básicas “correo de…” / “despacho de…”.

- **Sprint 8 (27 Ene – 16 Feb, ~20 h)**  
  - Objetivo: Tutorías + búsqueda por asignatura.  
  - Entregables: tabla tutorías, normalización nombres, mini golden set.

- **Sprint 9 (17 Feb – 09 Mar, ~22 h)**  
  - Objetivo: RAG Asignaturas v2 — descubrimiento + extracción.  
  - Entregables: mapa de URLs, extractor PDF/HTML, chunking.

- **Sprint 10 (10 Mar – 30 Mar, ~23 h)**  
  - Objetivo: Embeddings + acción Rasa RAG con cita (doc+sección).

---

### Primavera 2026 — QA + Horarios + RAG Trámites + Cierre

- **Sprint 11 (31 Mar – 20 Abr, ~23 h)**  
  - Objetivo: QA RAG Asignaturas.  
  - Entregables: golden set ≥40, pruebas anti-alucinación.  

- **Sprint 12 (21 Abr – 11 May, ~23 h)**  
  - Objetivo: Horarios DB + Testing.  
  - Entregables: esquema, carga curso, golden set horarios, latencia p95 ≤1s.  

- **Sprint 13 (12 May – 19 May, ~25 h)**  
  - Objetivo: RAG Trámites + Frontend final + Memoria y defensa.  
  - Entregables:  
    - Extracción y embeddings de trámites, consultas con cita.  
    - **Frontend refinado**: mejoras de UX y pruebas piloto con estudiantes.  
    - Documento final, slides, checklist criterios de evaluación, ensayo.  

---

## Definición: Script de carga CSV

Un script pequeño (Python recomendado) que:  
1. Lee un CSV con columnas acordadas (`codigo_asignatura`, `nombre`, `curso`, `calificacion`, etc.).  
2. Valida (no nulos, tipos, normaliza tildes).  
3. Hace **upsert** en Supabase (insertar o actualizar).  
4. Devuelve log de filas cargadas/errores.  

> Alternativa rápida: importar CSV desde el panel de Supabase o `COPY SQL`, aunque el script permite versionar y repetir cargas.
