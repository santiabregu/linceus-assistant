# Plan de optimización: Soporte para inglés

**Fecha:** 2026-03-22
**Sprint:** S5
**Estado:** Pendiente
**Prioridad:** Media

---

## Motivación

El sistema actual (NLU, prompts, stopwords, limpieza de entidades) está diseñado exclusivamente para español. Sin embargo, existen grupos de docencia en inglés (e.g. "Grupo 5 INGLÉS" en varias asignaturas) y algunos planes docentes podrían estar redactados en inglés. Soportar consultas en inglés amplía la accesibilidad del bot.

---

## Componentes afectados

| Componente | Archivo(s) | Estado actual |
|---|---|---|
| Palabras ruido NLU | `actions/asignaturas/actions.py` (PALABRAS_RUIDO, SUFIJOS_RUIDO) | Solo español |
| Stopwords búsqueda keyword | `rag/buscar.py` (stopwords en `_buscar_por_keywords`) | Solo español |
| Prompts LLM (respuesta RAG) | `actions/asignaturas/actions.py` (`_generar_respuesta_rag`) | Instrucciones en español |
| Prompts LLM (text-to-SQL) | `actions/asignaturas/text_to_sql.py` | Instrucciones en español |
| Datos de entrenamiento NLU | `data/nlu/asignaturas.yml`, `data/nlu/general.yml` | Ejemplos solo en español |
| Reglas y stories | `data/rules.yml`, `data/stories/` | Intents solo en español |
| Respuestas del dominio | `domain.yml` | Templates solo en español |

---

## Tareas

### Fase 1 — Detección de idioma

- [ ] Implementar detección de idioma del mensaje del usuario (regex simple o clasificador ligero)
- [ ] Añadir slot `idioma_usuario` (es/en) para mantener contexto de idioma en la conversación
- [ ] Considerar si el idioma se hereda de mensajes anteriores o se detecta por mensaje

### Fase 2 — NLU bilingüe

- [ ] Añadir ejemplos de intents en inglés a `data/nlu/asignaturas.yml` (e.g. "What are the credits for...", "Who teaches...")
- [ ] Añadir ejemplos de intents en inglés a `data/nlu/general.yml`
- [ ] Ampliar PALABRAS_RUIDO con equivalentes en inglés (the, of, from, about, tell, me, what, etc.)
- [ ] Ampliar SUFIJOS_RUIDO con equivalentes en inglés (the, of, and, or, etc.)
- [ ] Añadir stopwords en inglés a `rag/buscar.py`

### Fase 3 — Prompts bilingües

- [ ] Adaptar prompt de `_generar_respuesta_rag` para responder en el idioma del usuario
- [ ] Adaptar prompt de `generar_sql_especifica` para aceptar preguntas en inglés
- [ ] Adaptar prompt de `generar_respuesta_natural` para responder en el idioma detectado

### Fase 4 — Respuestas del dominio

- [ ] Añadir variantes en inglés de las respuestas en `domain.yml` (utter_*)
- [ ] Considerar si usar respuestas condicionales por slot `idioma_usuario` o duplicar intents

### Fase 5 — Testing

- [ ] Crear plan de pruebas con consultas en inglés (mismas asignaturas, preguntas traducidas)
- [ ] Validar que las consultas en español no se ven afectadas (regresión)
- [ ] Probar mezcla de idiomas (pregunta en inglés sobre asignatura con nombre en español)

---

## Notas

- Los nombres de las asignaturas en la BD están en español → las búsquedas ILIKE/fuzzy deben seguir funcionando con nombres en español aunque la pregunta sea en inglés
- Los planes docentes de grupos en inglés pueden tener contenido en inglés → los embeddings del modelo `gemini-embedding-001` son multilingües, por lo que la búsqueda vectorial debería funcionar sin cambios
- El LLM (gemma-3-27b-it) soporta inglés → los prompts solo necesitan indicar que responda en el idioma del usuario
- Priorizar fase 2 y 3 ya que dan el mayor impacto con menor esfuerzo
