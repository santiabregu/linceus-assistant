# Gestión de Proyectos – LinceUS Assistant

Este documento describe la metodología de organización de tareas para el desarrollo de **LinceUS Assistant**, utilizando la pestaña **GitHub Projects** como herramienta principal de planificación y seguimiento.

---

## 1. Estructura de los proyectos

- Se usará un **tablero Kanban** en GitHub Projects.  
- Cada sprint tendrá un **milestone** (2 semanas de duración).  
- Las tarjetas del tablero se crean a partir de **Issues**.  

### Columnas recomendadas en el tablero
- **Backlog** → Ideas o tareas pendientes aún no planificadas.  
- **To Do (Sprint N)** → Tareas asignadas al sprint actual.  
- **In Progress** → Tareas en desarrollo.  
- **Review** → Tareas finalizadas pendientes de validación/pruebas.  
- **Done** → Tareas completadas y cerradas.  

---

## 2. Organización de los sprints

- Cada sprint dura **14 días** (lunes–domingo).  
- Al inicio del sprint, se seleccionan tareas del **Backlog** y se mueven a **To Do**.  
- Al finalizar el sprint:  
  - Se cierran las Issues completadas.  
  - Se genera un breve informe en el tablero con las tareas realizadas.  
  - Las tareas no completadas regresan al Backlog o se replanifican para el siguiente sprint.  

---

## 3. Reglas de las tareas (Issues)

- Cada tarea debe estar asociada a un **Issue** con:  
  - **Título claro y conciso**.  
  - **Descripción detallada** (objetivo, entregables esperados).  
  - **Etiqueta** correspondiente (`feature`, `bug`, `documentation`, `maintenance`).  
  - **Milestone** = sprint al que pertenece.  

- Cerrar las tareas usando referencias en commits o PRs:  
