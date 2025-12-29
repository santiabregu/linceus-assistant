---
applyTo: '**'
---
## Contexto del proyecto TFG
Proyecto: Diseño y desarrollo de un chatbot inteligente  
Universidad de Sevilla – Ingeniería del Software  
Objetivo: Asistente conversacional que centralice la información académica/administrativa usando Rasa + Supabase (pgvector) + Gemini API + React.  

---

### Puntos clave para la asistencia de Cursor
1. No añadir código automáticamente salvo que lo pida explícitamente.  
2. Responder con explicaciones y sugerencias primero, antes de dar código.  
3. Stack principal:  
   - Rasa (framework conversacional en Python).  
   - Supabase (Postgres + pgvector para datos estructurados y embeddings).  
   - Gemini API (detección de intención y generación de respuestas).  
   - React (frontend del chatbot).  
4. El proyecto sigue un backlog dividido en épicas: Asignaturas, Profesores, Horarios, Trámites, RAG.  
5. Evitar alucinaciones y asegurar que siempre se citen fuentes cuando se use RAG.  
6. Pruebas obligatorias:  
   - Rendimiento (Locust).  
   - Testing conversacional en Rasa (.yml con historias).  
   - Validación de información (precisión, trazabilidad, evitar respuestas perezosas).  
   - Seguridad (RGPD, control de acceso, ataques comunes).  

---

### Guía para la interacción
- Si planteo una duda técnica, sugerir enfoques dentro del stack definido.  
- Si pregunto por alternativas, comparar pros/contras pero sin cambiar la arquitectura base.  
- Si pido código, darlo limpio, comentado y minimalista.  
- Si no pido código, no dar ejemplos de código.  
