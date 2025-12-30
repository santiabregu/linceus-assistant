# Estrategia de versionado del sistema

El desarrollo del chatbot se ha organizado siguiendo una **estrategia de versionado semántico**, adaptada a un enfoque incremental basado en **épicas funcionales**. Esta estrategia permite identificar de forma clara la evolución del sistema, las funcionalidades incorporadas en cada versión y el alcance de los cambios realizados.

El formato de versionado adoptado es el siguiente:

```
vMAJOR.MINOR.PATCH
```

donde cada componente tiene un significado específico dentro del contexto del proyecto.

---

## Versiones MAJOR (épicas funcionales)

El incremento del número **MAJOR** indica la incorporación de una **nueva épica funcional** al chatbot, es decir, una nueva capacidad principal del sistema. Cada épica agrupa un conjunto coherente de casos de uso relacionados.

Ejemplos de épicas funcionales del sistema son:
- Consulta de asignaturas
- Consulta de horarios
- Consulta de documentación administrativa
- Información sobre profesorado
- Localización de espacios universitarios

Cada vez que el sistema incorpora una nueva épica, se incrementa el valor MAJOR de la versión.

---

## Versiones MINOR (ampliaciones dentro de una épica)

El incremento del número **MINOR** representa la incorporación de **nuevas funcionalidades** dentro de una misma épica ya existente. Estas versiones suponen una ampliación del comportamiento del sistema, pero no introducen una nueva capacidad principal.

Algunos ejemplos de cambios que justifican un incremento MINOR son:
- Nuevos intents o variaciones de preguntas soportadas
- Nuevos filtros de búsqueda
- Inclusión de nuevos atributos en las respuestas
- Mejora de la lógica de recuperación de información

---

## Versiones PATCH (correcciones y ajustes)

El incremento del número **PATCH** se reserva para **correcciones de errores**, ajustes internos o mejoras que no alteran el comportamiento funcional esperado del sistema.

Este tipo de versiones incluye, entre otros:
- Corrección de errores en la detección de intención
- Ajustes en la formulación de las respuestas
- Resolución de casos ambiguos
- Pequeñas optimizaciones internas

---

## Ejemplo de evolución de versiones

A modo ilustrativo, la evolución del sistema podría seguir el siguiente esquema:

```
v1.0.0  → Implementación inicial de la épica “Asignaturas”
v1.1.0  → Añadido filtro por curso académico
v1.2.0  → Inclusión de información sobre créditos y tipología
v1.2.1  → Corrección de respuestas ambiguas

v2.0.0  → Implementación de la épica “Horarios”
v2.1.0  → Consulta de horarios por grupo
v2.1.1  → Corrección de solapamientos detectados
```

---

## Beneficios de la estrategia adoptada

Esta estrategia de versionado aporta las siguientes ventajas:
- Facilita el seguimiento de la evolución del sistema
- Permite relacionar cada versión con funcionalidades concretas
- Mejora la trazabilidad entre requisitos, versiones y pruebas
- Proporciona una estructura clara y comprensible para la evaluación académica
