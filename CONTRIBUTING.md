# Guía de Contribución – LinceUS Assistant

Este documento define la política de commits, branching y organización de tareas para el desarrollo de **LinceUS Assistant**. Aunque actualmente el desarrollo lo realiza una sola persona, seguir estas reglas garantiza un flujo de trabajo organizado y fácil de mantener.

**Nota:** La política de ramas y commits comienza a aplicarse a partir del segundo sprint. El primer sprint se dedica únicamente a la configuración inicial y desarrollo del MVP.

## 1. Nomenclatura de ramas

Se utilizará la siguiente convención para nombrar las ramas:

```
tipo/descripcion-breve
```

Tipos permitidos:
- `feature` → Para nuevas funcionalidades.
- `fix` → Para corregir errores.
- `docs` → Para cambios en la documentación.
- `chore` → Para tareas de mantenimiento que no afectan el código de producción.

Ejemplos:
```
feature/flujo-bienvenida
fix/error-configuracion-nlu
docs/actualizar-readme
chore/actualizar-dependencias
```

## 2. Convención de commits

Los mensajes de commit seguirán el estándar [Conventional Commits](https://www.conventionalcommits.org/):

```
tipo: descripcion breve en presente
```

Tipos recomendados:
- `feat` → Nueva funcionalidad.
- `fix` → Corrección de errores.
- `docs` → Documentación.
- `refactor` → Cambio en el código que no corrige errores ni añade funciones.
- `test` → Añadir o modificar pruebas.
- `chore` → Mantenimiento.

Ejemplos:
```
feat: añadir intent para matrícula Erasmus
fix: corregir extracción de entidades en intent de pagos
docs: actualizar guía de instalación
```

Reglas:
- Usar tiempo presente e imperativo.
- Mantener la descripción corta (máximo 72 caracteres).
- Si es necesario, añadir más detalles en un párrafo posterior.

## 3. Flujo de branching

Se trabajará con el siguiente flujo de ramas:

- `main` → Contiene la versión estable y lista para producción.
- `develop` → Rama de integración donde se prueban nuevas funcionalidades.
- `feature/...` → Ramas derivadas de `develop` para añadir nuevas funcionalidades.
- `fix/...` → Ramas derivadas de `develop` para corregir errores.

Proceso:
1. Crear rama a partir de `develop`.
2. Implementar cambios y hacer commits siguiendo la convención.
3. Realizar merge o rebase en `develop`.
4. Cuando se quiera liberar una versión estable, hacer merge de `develop` a `main`.

## 4. Organización de tareas

- Usar GitHub Projects o Issues para gestionar las tareas.
- Etiquetas recomendadas:
  - `feature`
  - `bug`
  - `documentation`
  - `maintenance`
- Definir siempre una descripción clara de la tarea antes de comenzarla.
- Cerrar las tareas vinculándolas a commits o Pull Requests (`close #ID` en el mensaje).

## 5. Pull Requests

Aunque el desarrollo sea individual, se recomienda usar Pull Requests para mantener un historial claro de cambios y permitir revisiones antes de fusionar en `develop` o `main`.

Reglas para las PR:
- Título descriptivo y breve.
- Descripción detallando los cambios realizados.
- Referencia a las tareas o issues que resuelve.
- Confirmar que las pruebas (si existen) pasan correctamente.

## 6. Versionado

Se seguirá [Semantic Versioning](https://semver.org/) (MAJOR.MINOR.PATCH):
- **MAJOR** → Cambios incompatibles con versiones anteriores.
- **MINOR** → Nuevas funcionalidades compatibles.
- **PATCH** → Correcciones de errores o mejoras menores.

## 7. Documentación

Mantener el `README.md` y cualquier otra documentación actualizados conforme se implementen nuevas funcionalidades o cambios importantes.
