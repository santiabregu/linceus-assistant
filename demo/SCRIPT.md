# Guion de voz en off — Demo Linceus Assistant

> Vídeo de **3:00** (180 s). Los timestamps son acumulativos desde el segundo 0 y reflejan los tiempos del timeline alineados con la grabación real.
> Tono recomendado: claro, calmado, natural. Pausas breves entre escenas.

---

## 00:00 – 00:10 · Apertura (10 s)

> "Linceus Assistant es el asistente virtual de la ETSII de la Universidad de Sevilla. Permite a los estudiantes consultar asignaturas, horarios y profesores en lenguaje natural, directamente desde la web de la escuela."

*(El widget se abre al final de la frase.)*


---

## 00:10 – 00:23 · Onboarding · Selección de titulación (13 s)

> "Al abrirlo por primera vez, el asistente pregunta por la titulación del estudiante. A partir de esa elección, todas las respuestas se ajustan automáticamente a su plan de estudios. En este caso seleccionamos Ingeniería del Software."

*(El cursor pulsa el botón "Ingeniería del Software".)*

---

## 00:23 – 00:34 · Caso 1 · Información sobre una asignatura (11 s)

> "Empezamos con una consulta básica sobre Sistemas Operativos. El estudiante escribe como lo haría a una persona, y el asistente responde con curso, tipo, cuatrimestre, créditos y departamento en una sola respuesta clara."

---

## 00:34 – 00:45 · Caso 2 · Seguimiento elíptico (11 s)

> "Ahora el estudiante hace una pregunta de seguimiento: simplemente pregunta cuántos créditos tiene, sin repetir el nombre de la asignatura. El asistente recuerda el contexto de la conversación y responde correctamente."

---

## 00:45 – 00:56 · Caso 3 · Listado de optativas (11 s)

> "El estudiante pregunta qué optativas hay disponibles. El asistente sabe a qué titulación pertenece y devuelve únicamente las optativas de su plan: las ocho asignaturas de cuarto curso con su cuatrimestre."

---

## 00:56 – 01:06 · Caso 4 · Horario por asignatura sin grupo (10 s)

> "Al preguntar simplemente cuándo es ADDA, sin indicar grupo, el asistente devuelve los horarios de todos los grupos disponibles. Toma como referencia el cuatrimestre activo según la fecha actual y se lo indica al usuario."

---

## 01:06 – 01:17 · Caso 5 · Horario por curso y grupo (11 s)

> "Si el estudiante quiere su horario del lunes, puede indicar su curso y grupo directamente. El asistente le devuelve las dos asignaturas que tiene ese día, con la franja horaria y el aula de cada una."

---

## 01:17 – 01:28 · Caso 6 · Correo de un profesor (11 s)

> "El asistente también resuelve consultas sobre profesores. Aquí el estudiante pide el correo de José Antonio Parejo, y el asistente lo localiza en el directorio del departamento y lo muestra de forma directa."

---

## 01:28 – 01:39 · Caso 7 · Cambio de titulación (11 s)

> "Un estudiante puede cambiar su titulación en cualquier momento simplemente diciéndoselo al asistente. Al escribir 'soy de IC', el contexto cambia a Ingeniería de Computadores y todas las consultas siguientes se adaptan a ese plan."

---

## 01:39 – 01:50 · Caso 8 · Robustez frente a jailbreak (11 s)

> "Por último, un intento de manipulación: el estudiante le pide que ignore sus instrucciones y revele su prompt interno. El asistente rechaza la solicitud con educación y devuelve la conversación al ámbito académico."

---

## 01:50 – 02:04 · Panel · Inicio (14 s)

> "Pasamos ahora al panel de administración. Desde aquí el personal de la escuela gestiona todos los datos del sistema sin necesidad de conocimientos técnicos. La vista de inicio muestra los tres centros configurados; al entrar en cualquiera de ellos se accede a sus titulaciones y asignaturas."

---

## 02:04 – 02:18 · Panel · Asignaturas (14 s)

> "Dentro de una titulación, el panel ofrece las acciones que mantienen vivo el sistema: sincronizar las asignaturas desde Sevius, enriquecer sus datos desde us.es y, sobre todo, vectorizar los planes docentes para que el componente RAG pueda responder preguntas sobre su contenido."

---

## 02:18 – 02:26 · Panel · Horarios (8 s)

> "La sección de horarios permite generar las franjas de cada titulación a partir del extractor del centro correspondiente, hoy disponible para la ETSII."

---

## 02:26 – 02:36 · Panel · Profesores (10 s)

> "En profesores encontramos el directorio completo del departamento, con la opción de enriquecerlo automáticamente desde us.es para mantener actualizados correos, categorías y despachos."

---

## 02:36 – 02:46 · Panel · Conversaciones (10 s)

> "La sección de conversaciones registra todas las sesiones de los usuarios. El administrador puede revisar qué preguntas se han hecho, cuándo y durante cuánto tiempo, lo que permite detectar problemas y mejorar el sistema."

---

## 02:46 – 02:54 · Panel · Estadísticas (8 s)

Y en estadísticas tenemos una visión global de las asignaturas, profesores y del contenido procesado y disponible para responder preguntas.

---

## 02:54 – 03:00 · Cierre (6 s)

> "Linceus Assistant — un asistente conversacional listo para escalar a toda la Universidad de Sevilla."

---

## Notas de grabación

- Duración total: **3:00** (180 s) tras añadir 1 segundo de holgura a 9 escenas sobre los tiempos reales grabados (171 s).
- Escenas con el segundo extra: Onboarding, Casos 2, 3, 4, 5, 6, Panel · Horarios, Panel · Estadísticas y Cierre.
- Las más holgadas son Panel · Inicio y Panel · Asignaturas (14 s cada una).
- Las más ajustadas tras la holgura: Cierre (6 s), Panel · Horarios (8 s), Panel · Estadísticas (8 s) y Caso 4 (10 s).
- Los bloques del panel replican exactamente los botones del frontend real: "Vectorizar planes docentes", "Enriquecer datos (us.es)", "Cargar docencia", "Sincronizar desde Sevius" y "Generar horarios".
