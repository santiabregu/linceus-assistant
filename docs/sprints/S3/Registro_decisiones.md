# Registro de Decisiones - Sprint 3

## Decisiones Técnicas

1) **Migración completa de Gemini a Ollama**: Se eliminó por completo la dependencia de Gemini API y se migró a Ollama con Llama 3, permitiendo ejecución local sin costos de API y mayor control sobre el procesamiento.

2) **Cliente HTTP para Ollama en vez de subprocess**: Se implementó `ollama_client.py` que usa la API HTTP de Ollama (`http://localhost:11434/api/generate`) en lugar de subprocess. Esto mantiene el modelo cargado en memoria entre consultas, mejorando la velocidad de 20-30s a 2-4s por consulta (5-15x más rápido).

3) **Modelo optimizado llama3.2:3b**: Se eligió el modelo `llama3.2:3b` en vez de `llama3` completo porque ofrece tiempos de respuesta 2-3x más rápidos manteniendo calidad suficiente para las tareas de clasificación, extracción y generación de respuestas naturales.

4) **Sistema Text-to-SQL con clasificación automática**: Se implementó un sistema que clasifica automáticamente las consultas en "específicas" (sobre una asignatura concreta) vs "generales" (listados con filtros), permitiendo generar SQL dinámico o búsquedas fuzzy según el tipo de consulta.

5) **Cache de asignaturas en memoria por sesión**: Las asignaturas de la titulación activa se cargan una sola vez por sesión con `cargar_asignaturas_titulacion()` y se mantienen en memoria, eliminando múltiples queries a BD y mejorando el rendimiento de búsquedas fuzzy.

6) **Búsqueda fuzzy mejorada con desambiguación LLM**: El sistema ahora hace búsqueda exacta por código, búsqueda LIKE, y fuzzy matching con rapidfuzz. Cuando encuentra múltiples coincidencias, usa el LLM para desambiguar automáticamente cuál asignatura es más probable según el contexto.

7) **Respuestas naturales generadas con LLM**: Todas las respuestas del bot (tanto específicas como generales) pasan por `generar_respuesta_natural()` que usa el LLM para convertir datos estructurados en texto conversacional natural, eliminando respuestas robóticas.

8) **Separación de lógica de interpretación LLM**: Se creó `llm_interpreter.py` como módulo independiente para la interpretación inicial de mensajes, separando la lógica de preprocesamiento del sistema principal de consultas.

9) **Documentación técnica exhaustiva**: Se crearon documentos específicos (`TEXT_TO_SQL_ASIGNATURAS.md`, `SOLUCION_VELOCIDAD_OLLAMA.md`, `VERIFICACION_SISTEMA.md`) para facilitar el mantenimiento y onboarding de nuevos desarrolladores.

10) **Script de inicialización para Ollama**: Se creó `iniciar_ollama.bat` que automatiza el proceso de iniciar el servidor Ollama y pre-cargar el modelo, reduciendo friction en el setup del proyecto.

11) **Ignorar directorio `old/` en git**: Se agregó `old/` al `.gitignore` para mantener limpio el repositorio de archivos legacy y pruebas temporales durante la migración.

12) **Nuevos slots para cache de resultados**: Se implementó `ultimos_resultados_asignaturas` (tipo `any`) para guardar resultados de consultas generales, permitiendo que el usuario pueda pedir "ver todas" sin re-ejecutar la query SQL.

## Decisiones de Producto

13) **Priorizar velocidad sobre capacidad del modelo**: Se priorizó un modelo más pequeño (3b) pero más rápido sobre uno más capaz pero lento, ya que los tiempos de respuesta >15s degradan significativamente la experiencia de usuario en un chatbot.

14) **Mantener compatibilidad con sistema legacy**: Se mantuvieron los intents y actions antiguos (`consultar_asignatura`, `action_consultar_asignatura`) durante la transición para no romper flujos existentes mientras se estabiliza el nuevo sistema Text-to-SQL.
