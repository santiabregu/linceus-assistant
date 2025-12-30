# Resumen de Datos Iniciales - TFG Chatbot

## 📍 Ubicación de los archivos

| Archivo | Descripción |
|---------|-------------|
| `tfg_chatbot_schema.sql` | Esquema completo de tablas (ejecutar primero) |
| `tfg_chatbot_datos_iniciales.sql` | Datos iniciales (ejecutar después del esquema) |

---

## 🏛️ Datos añadidos

### 1. Universidad

| Campo | Valor |
|-------|-------|
| **Tabla** | `universidades` |
| **Código** | `US` |
| **Nombre** | Universidad de Sevilla |
| **Dominio** | us.es |
| **Ciudad** | Sevilla |

---

### 2. Centro

| Campo | Valor |
|-------|-------|
| **Tabla** | `centros` |
| **Código** | `ETSII` |
| **Nombre** | Escuela Técnica Superior de Ingeniería Informática |
| **Dirección** | Avda. Reina Mercedes s/n, 41012 Sevilla |
| **Teléfono** | 954556817 |
| **Web** | https://www.informatica.us.es |

---

### 3. Titulación

| Campo | Valor |
|-------|-------|
| **Tabla** | `titulaciones` |
| **Código** | `GII-IS` |
| **Nombre** | Grado en Ingeniería Informática - Ingeniería del Software |
| **Plan de estudios** | 2010 |
| **Créditos totales** | 240 ECTS |
| **Duración** | 4 años |
| **Requisito idioma** | B1 |

---

### 4. Asignaturas (42 total)

| Curso | Formación Básica | Obligatorias | Optativas | TFG | Total |
|-------|------------------|--------------|-----------|-----|-------|
| 1º | 9 (60 ECTS) | - | - | - | 9 |
| 2º | - | 9 (54 ECTS) | - | - | 9 |
| 3º | - | 10 (60 ECTS) | - | - | 10 |
| 4º | - | 3 (18 ECTS) | 15 (90 ECTS) | 1 (12 ECTS) | 19 |

**Nota:** El alumno debe elegir 30 ECTS de optativas (5 asignaturas de 6 ECTS)

---

## 📋 Lista completa de asignaturas

### Curso 1 (60 ECTS)

| Código | Nombre | ECTS | Periodo | Tipo |
|--------|--------|------|---------|------|
| 2050001 | Fundamentos de Programación | 12 | Anual | FB |
| 2050002 | Cálculo Infinitesimal y Numérico | 6 | C1 | FB |
| 2050003 | Circuitos Electrónicos Digitales | 6 | C1 | FB |
| 2050004 | Fundamentos Físicos de la Informática | 6 | C1 | FB |
| 2050005 | Introducción a la Matemática Discreta | 6 | C1 | FB |
| 2050006 | Administración de Empresas | 6 | C2 | FB |
| 2050007 | Álgebra Lineal y Numérica | 6 | C2 | FB |
| 2050008 | Estadística | 6 | C2 | FB |
| 2050009 | Estructura de Computadores | 6 | C2 | FB |

### Curso 2 (54 ECTS)

| Código | Nombre | ECTS | Periodo | Tipo |
|--------|--------|------|---------|------|
| 2050010 | Análisis y Diseño de Datos y Algoritmos | 6 | C1 | OB |
| 2050046 | Introducción a la Ingeniería del Software y SI I | 6 | C1 | OB |
| 2050012 | Lógica Informática | 6 | C1 | OB |
| 2050013 | Redes de Computadores | 6 | C1 | OB |
| 2050014 | Sistemas Operativos | 6 | C1 | OB |
| 2050015 | Arquitectura de Computadores | 6 | C2 | OB |
| 2050016 | Arquitectura e Integración de Sistemas Software | 6 | C2 | OB |
| 2050047 | Introducción a la Ingeniería del Software y SI II | 6 | C2 | OB |
| 2050017 | Matemática Discreta | 6 | C2 | OB |

### Curso 3 (60 ECTS)

| Código | Nombre | ECTS | Periodo | Tipo |
|--------|--------|------|---------|------|
| 2050048 | Diseño y Pruebas I | 6 | C1 | OB |
| 2050020 | Ingeniería de Requisitos | 6 | C1 | OB |
| 2050021 | Modelado y Simulación Numérica | 6 | C1 | OB |
| 2050022 | Procesamiento de Señales Multimedia | 6 | C1 | OB |
| 2050050 | Proceso Software y Gestión I | 6 | C1 | OB |
| 2050023 | Arquitectura y Servicios de Redes | 6 | C2 | OB |
| 2050049 | Diseño y Pruebas II | 6 | C2 | OB |
| 2050024 | Inteligencia Artificial | 6 | C2 | OB |
| 2050025 | Modelado y Visualización Gráfica | 6 | C2 | OB |
| 2050051 | Proceso Software y Gestión II | 6 | C2 | OB |

### Curso 4 - Obligatorias (18 ECTS)

| Código | Nombre | ECTS | Periodo | Tipo |
|--------|--------|------|---------|------|
| 2050032 | Evolución y Gestión de la Configuración | 6 | C1 | OB |
| 2050035 | Planificación y Gestión de Proyectos Informáticos | 6 | C1 | OB |
| 2050039 | Ingeniería del Software y Práctica Profesional | 6 | C2 | OB |

### Curso 4 - TFG (12 ECTS)

| Código | Nombre | ECTS | Periodo | Tipo |
|--------|--------|------|---------|------|
| 2050045 | Trabajo Fin de Grado | 12 | C2 | TFG |

### Curso 4 - Optativas C1 (elegir hasta completar 30 ECTS)

| Código | Nombre | ECTS | Periodo | Tipo |
|--------|--------|------|---------|------|
| 2050027 | Acceso Inteligente a la Información | 6 | C1 | OPT |
| 2050028 | Ampliación de Administración de Empresas | 6 | C1 | OPT |
| 2050029 | Aplicaciones de Soft Computing | 6 | C1 | OPT |
| 2050030 | Criptografía | 6 | C1 | OPT |
| 2050031 | Derecho en la Informática | 6 | C1 | OPT |
| 2050033 | Gestión de la Información Empresarial | 6 | C1 | OPT |
| 2050034 | Modelos de Computación y Complejidad | 6 | C1 | OPT |
| 2050036 | Técnicas e Infraestructura Software | 6 | C1 | OPT |

### Curso 4 - Optativas C2

| Código | Nombre | ECTS | Periodo | Tipo |
|--------|--------|------|---------|------|
| 2050037 | Computación en la Nube y Big Data | 6 | C2 | OPT |
| 2050038 | Emprendimiento Corporativo | 6 | C2 | OPT |
| 2050041 | Operaciones y Servicios | 6 | C2 | OPT |
| 2050042 | Procesamiento de Información Digital | 6 | C2 | OPT |
| 2050043 | Seguridad de Sistemas de Información | 6 | C2 | OPT |
| 2050044 | Telemática | 6 | C2 | OPT |

### Prácticas Externas (optativa especial)

| Código | Nombre | ECTS | Periodo | Tipo |
|--------|--------|------|---------|------|
| 2050040 | Prácticas Externas | 6 | Anual | OPT |

---

## 🔢 Resumen de créditos

| Tipo | ECTS |
|------|------|
| Formación Básica (FB) | 60 |
| Obligatorias (OB) | 132 |
| Optativas (elegir) | 30 de 90 disponibles |
| TFG | 12 |
| **Total carrera** | **240** |

---

## ⚙️ Cómo ejecutar en Supabase

1. **Primero** ejecutar el esquema:
   ```sql
   -- Ejecutar tfg_chatbot_schema.sql completo
   ```

2. **Después** ejecutar los datos iniciales:
   ```sql
   -- Ejecutar tfg_chatbot_datos_iniciales.sql
   ```

3. **Verificar** que los datos se insertaron:
   ```sql
   SELECT COUNT(*) FROM universidades;  -- Debe dar 1
   SELECT COUNT(*) FROM centros;        -- Debe dar 1
   SELECT COUNT(*) FROM titulaciones;   -- Debe dar 1
   SELECT COUNT(*) FROM asignaturas;    -- Debe dar 42
   ```

---

## 📌 Próximos pasos (según Sprint Planning)

- **Sprint 2:** Script de carga CSV para futuras asignaturas
- **Sprint 3:** Conectar Rasa con consultas a esta base de datos
- **Sprint 7:** Añadir profesores y tutorías
- **Sprint 9:** RAG de planes docentes (tabla `planes_docentes_chunks`)

---

## 📝 Fuente de datos

Plan de estudios oficial:  
https://www.informatica.us.es/index.php/grados/ingenieria-del-software/plan-de-estudios
