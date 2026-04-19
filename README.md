# LinceUS Assistant

**LinceUS** es un asistente virtual inteligente para la **Universidad de Sevilla**, diseñado para responder preguntas y guiar a los estudiantes en trámites, servicios y vida académica.

## Propósito
El objetivo de LinceUS es simplificar el acceso a la información universitaria, reduciendo el tiempo y esfuerzo que los estudiantes dedican a buscar en múltiples sitios web, documentos y correos electrónicos.

## Funcionalidades principales
- **Sistema de preguntas y respuestas** sobre consultas frecuentes de los estudiantes  
- Guía en **procedimientos administrativos** (matrícula, pagos, Erasmus, TFG, etc.)  
- Acceso a **información de facultades y departamentos**  
- Apoyo a **estudiantes de nuevo ingreso** (nacionales e internacionales)

## Stack tecnológico

| Capa | Tecnología | Puerto |
|------|-----------|--------|
| Frontend (chatbot + admin) | HTML/CSS/JS + Nginx | 80 / 8080 |
| Admin API | Flask (Python) | 5050 |
| NLU + diálogo | Rasa 3.6 (Python) | 5005 |
| Actions + RAG | Rasa SDK (Python) | 5055 |
| Base de datos | Supabase (PostgreSQL) + BD vectorial | — |
| IA | Google Gemini API, spaCy (español) | — |

---

## Inicio rápido — desarrollo local

> Necesitas Python 3.10+, un entorno virtual activo, y el archivo `.env` en la raíz del proyecto (pide una copia a un compañero o revisa `.env.example`).

### 1. Chatbot (página principal)

El frontend es HTML/JS estático. Sirve la carpeta con el servidor HTTP de Python:

```bash
cd frontend
python -m http.server 8080
```

Abre en el navegador: **http://localhost:8080/pagina-principal.html**

El widget de chat se conecta al servidor Rasa en `http://localhost:5005`. Para que el chatbot responda necesitas también levantar Rasa y el action server (ver sección Backend).

---

### 2. Panel de administración

El admin consta de dos piezas: una **API Flask** y el **frontend estático**. Necesitas dos terminales.

**Terminal 1 — API admin (puerto 5050):**
```bash
python -m admin.app
```

**Terminal 2 — Frontend estático (puerto 8080):**
```bash
cd frontend
python -m http.server 8080
```

Abre en el navegador: **http://localhost:8080/admin.html**

> El frontend detecta automáticamente si está en `localhost` y apunta a `http://localhost:5050`. No hace falta configurar nada más.

El panel permite gestionar:
- **Centros** y **titulaciones** (alta manual o importando desde Sevius)
- **Asignaturas** (sincronización automática con Sevius)
- **Profesores** y **horarios**
- **Conversaciones** y **feedback** de los usuarios

#### Flujo para añadir un centro/titulación/asignaturas

1. **Solo centro** → panel → "Nuevo centro" → selecciona de Sevius → crear
2. **Centro + titulación** → crear centro → entrar en él → "Nueva titulación" → seleccionar en Sevius → crear
3. **Con asignaturas** → tras crear titulación → entrar en ella → "Sincronizar desde Sevius" → selecciona centro y titulación en Sevius → se crean automáticamente todas las asignaturas que no existan

#### Estructura del admin

```
admin/
├── app.py               ← punto de entrada Flask (puerto 5050)
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

---

### 3. Backend Rasa (NLU + diálogo + actions)

Necesitas dos terminales adicionales (o usar Docker, que es más fácil).

**Terminal 1 — Action server (puerto 5055):**
```bash
python -m rasa_sdk --actions actions --port 5055 --auto-reload
```

**Terminal 2 — Servidor Rasa (puerto 5005):**
```bash
rasa run --enable-api --cors "*" --port 5005 --endpoints endpoints.yml
```

> El action server tiene `--auto-reload`: los cambios en `actions/` o `rag/` se aplican solos. Solo tienes que reiniciar si cambias dependencias.

#### Entrenar un modelo

Si no tienes un modelo en `models/` o quieres reentrenar:

```bash
rasa train
# El modelo se guarda en models/
```

---

## Docker (forma recomendada)

Con Docker levanta todos los servicios de una vez. No necesitas instalar Python, Rasa ni dependencias localmente.

### Requisitos previos

- [Docker](https://docs.docker.com/get-docker/) y [Docker Compose](https://docs.docker.com/compose/install/)
- Archivo `.env` en la raíz con las variables necesarias (Supabase, Gemini API, etc.)
- Un modelo entrenado en `models/` (ver sección de entrenamiento)

### Levantar todo el entorno

```bash
# Desde la raíz del proyecto
docker compose -f docker/docker-compose.yml up --build

# En segundo plano
docker compose -f docker/docker-compose.yml up --build -d
```

Una vez arrancado:

| URL | Qué es |
|-----|--------|
| http://localhost | Chatbot (página principal) |
| http://localhost/admin.html | Panel de administración |
| http://localhost:5050 | Admin API (Flask) |
| http://localhost:5005 | Rasa API |
| http://localhost:5055 | Action server |

### Levantar solo el admin (sin Rasa)

```bash
docker compose -f docker/docker-compose.yml up --build admin frontend
```

Útil cuando solo quieres trabajar en el panel sin necesitar el chatbot.

### Comandos útiles

```bash
# Ver logs de un servicio
docker compose -f docker/docker-compose.yml logs -f actions
docker compose -f docker/docker-compose.yml logs -f rasa
docker compose -f docker/docker-compose.yml logs -f admin

# Reiniciar solo un servicio
docker compose -f docker/docker-compose.yml restart actions

# Parar todo
docker compose -f docker/docker-compose.yml down

# Reconstruir solo el action server (tras cambiar requirements)
docker compose -f docker/docker-compose.yml build actions
docker compose -f docker/docker-compose.yml up -d actions
```

### Hot-reload en desarrollo

Los volúmenes del compose montan el código local en los contenedores:

- `./actions` → `/app/actions`
- `./rag` → `/app/rag`
- `./models` → `/app/models`

Los cambios en `actions/` y `rag/` se reflejan automáticamente (el action server usa `--auto-reload`).

> Si modificas `requirements-actions.txt` sí necesitas reconstruir: `docker compose -f docker/docker-compose.yml build actions`

---

## Resumen de puertos

| Servicio | Puerto local | Cómo arrancarlo (local) |
|----------|-------------|------------------------|
| Frontend (chatbot + admin UI) | 8080 | `cd frontend && python -m http.server 8080` |
| Admin API | 5050 | `python -m admin.app` |
| Rasa server | 5005 | `rasa run --enable-api --cors "*" --endpoints endpoints.yml` |
| Action server | 5055 | `python -m rasa_sdk --actions actions --port 5055` |
| Frontend (Docker/nginx) | 80 | `docker compose up frontend` |

---

## Estado
Actualmente en desarrollo como parte de un Trabajo Fin de Grado.
