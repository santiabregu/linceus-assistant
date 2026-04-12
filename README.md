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

## Panel de administración

El panel admin permite gestionar centros, titulaciones, asignaturas (sincronizando con Sevius), profesores, horarios, conversaciones y feedback.

### Arrancar en desarrollo (local)

Requiere dos terminales:

**Terminal 1 — API admin (puerto 5050):**
```bash
python -m admin.app
```

**Terminal 2 — Frontend estático (puerto 8080):**
```bash
cd frontend
python -m http.server 8080
```

Luego abre en el navegador: **http://localhost:8080/admin.html**

> El frontend detecta automáticamente si está en `localhost` y apunta a `http://localhost:5050`. No hace falta configurar nada más.

### Estructura del admin

```
admin/
├── app.py               ← punto de entrada Flask
├── db.py                ← helpers de BD (query, execute, normalizar)
├── sevius_scraper.py    ← scraper de Sevius (centros, titulaciones, asignaturas)
└── routes/
    ├── centros.py       ← GET + POST /centros
    ├── titulaciones.py  ← GET + POST /titulaciones
    ├── asignaturas.py   ← GET + POST /sync
    ├── sevius.py        ← GET /sevius/centros|titulaciones|asignaturas (preview)
    ├── planes_docentes.py
    ├── profesores.py
    ├── horarios.py
    ├── conversaciones.py
    └── stats.py
```

### Flujo para añadir un nuevo centro/titulación

1. **Solo centro**: panel → "Nuevo centro" → selecciona de Sevius → crear
2. **Centro + titulación**: crear centro → entrar en él → "Nueva titulacion" → seleccionar en Sevius → crear
3. **Con asignaturas**: tras crear titulación → entrar en ella → "Sincronizar desde Sevius" → selecciona centro y titulación en Sevius → crea automáticamente todas las asignaturas que no existan

### En Docker (con el resto de servicios)

El admin se incluye como servicio adicional en `docker/docker-compose.yml`:

```bash
docker compose -f docker/docker-compose.yml up --build admin
```

---

## Docker

El proyecto se puede levantar con Docker Compose. Incluye cuatro servicios:

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| `actions` | 5055 | Action server (rasa-sdk + RAG) |
| `rasa` | 5005 | Servidor Rasa (NLU + diálogo) |
| `admin` | 5050 | Panel de administración (Flask) |
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
