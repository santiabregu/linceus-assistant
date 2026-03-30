# LinceUS Assistant

**LinceUS** es un asistente virtual inteligente para la **Universidad de Sevilla**, diseñado para responder preguntas y guiar a los estudiantes en trámites, servicios y vida académica.

## Propósito
El objetivo de LinceUS es simplificar el acceso a la información universitaria, reduciendo el tiempo y esfuerzo que los estudiantes dedican a buscar en múltiples sitios web, documentos y correos electrónicos.

## Funcionalidades principales
- **Sistema de preguntas y respuestas** sobre consultas frecuentes de los estudiantes  
- Guía en **procedimientos administrativos** (matrícula, pagos, Erasmus, TFG, etc.)  
- Acceso a **información de facultades y departamentos**  
- Apoyo a **estudiantes de nuevo ingreso** (nacionales e internacionales)  

## Tecnologías
- **Rasa (Python)** – Motor conversacional principal  
- **Acciones personalizadas (Python)** – Conexión a bases de datos, scraping y pipelines RAG  
- **Node.js** – Integración opcional con frontend  
- **Base de datos vectorial** – Para búsqueda semántica en documentos universitarios  

## Docker

El proyecto se puede levantar con Docker Compose. Incluye tres servicios:

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| `actions` | 5055 | Action server (rasa-sdk + RAG) |
| `rasa` | 5005 | Servidor Rasa (NLU + diálogo) |
| `frontend` | 80 | Widget de chat (nginx) |

### Requisitos previos

- [Docker](https://docs.docker.com/get-docker/) y [Docker Compose](https://docs.docker.com/compose/install/)
- Un archivo `.env` en la raíz con las variables de entorno necesarias (Supabase, Google AI, etc.)
- Un modelo entrenado en `models/` (ver sección de entrenamiento)

### Levantar el entorno

```bash
# Construir imágenes y arrancar todos los servicios
docker compose up --build

# En segundo plano
docker compose up --build -d
```

### Comandos útiles

```bash
# Ver logs de un servicio
docker compose logs -f actions
docker compose logs -f rasa

# Reiniciar solo un servicio
docker compose restart actions

# Parar todo
docker compose down

# Reconstruir solo el action server (tras cambiar dependencias)
docker compose build actions && docker compose up -d actions
```

### Desarrollo con hot-reload

En modo desarrollo, los volúmenes montan el código local directamente en los contenedores:

- `./actions` → `/app/actions`
- `./rag` → `/app/rag`
- `./models` → `/app/models`

El action server usa `--auto-reload`, así que los cambios en `actions/` o `rag/` se aplican automáticamente sin reiniciar el contenedor.

> Si cambias dependencias en `requirements-actions.txt`, sí necesitas reconstruir: `docker compose build actions`

### Entrenar un modelo

```bash
# Desde tu entorno local con Rasa instalado
rasa train

# El modelo se guarda en models/ y se monta automáticamente en el contenedor
```

## Estado
Actualmente en desarrollo como parte de un Trabajo Fin de Grado.
