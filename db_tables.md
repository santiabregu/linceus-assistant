erDiagram
    UNIVERSIDADES ||--o{ CENTROS : tiene
    UNIVERSIDADES ||--o{ DEPARTAMENTOS : tiene
    CENTROS ||--o{ TITULACIONES : ofrece
    CENTROS ||--o{ AULAS : tiene
    
    TITULACIONES ||--o{ ASIGNATURAS : contiene
    DEPARTAMENTOS ||--o{ ASIGNATURAS : imparte
    DEPARTAMENTOS ||--o{ PROFESORES : pertenece
    
    ASIGNATURAS ||--o{ PLANES_DOCENTES : tiene
    ASIGNATURAS ||--o{ GRUPOS_CLASE : tiene
    ASIGNATURAS ||--o{ PROFESOR_ASIGNATURA : asignada
    
    PLANES_DOCENTES ||--o{ PLANES_DOCENTES_CHUNKS : vectorizado
    
    PROFESORES ||--o{ TUTORIAS : ofrece
    PROFESORES ||--o{ PROFESOR_ASIGNATURA : imparte
    PROFESORES ||--o{ HORARIOS : da_clase
    
    GRUPOS_CLASE ||--o{ HORARIOS : tiene
    AULAS ||--o{ HORARIOS : usa
    
    CATEGORIAS_TRAMITES ||--o{ TRAMITES : agrupa
    UNIVERSIDADES ||--o{ TRAMITES : tiene
    TRAMITES ||--o{ TRAMITES_CHUNKS : vectorizado

    UNIVERSIDADES {
        uuid id PK
        varchar codigo UK "US"
        varchar nombre "Universidad de Sevilla"
        varchar nombre_corto
        varchar dominio_web
        varchar ciudad
        boolean activa
        timestamptz created_at
        timestamptz updated_at
    }
    
    CENTROS {
        uuid id PK
        uuid universidad_id FK
        varchar codigo UK "ETSII"
        varchar nombre "E.T.S. Ingenieria Informatica"
        varchar nombre_corto
        varchar direccion
        varchar telefono
        varchar email
        varchar web
        boolean activo
    }
    
    DEPARTAMENTOS {
        uuid id PK
        uuid universidad_id FK
        varchar codigo
        varchar nombre "Lenguajes y Sistemas Informaticos"
        varchar siglas "LSI"
        varchar email
        varchar web
        boolean activo
    }
    
    TITULACIONES {
        uuid id PK
        uuid centro_id FK
        varchar codigo "GII-IS"
        varchar codigo_oficial
        varchar nombre "Grado en Ing Informatica-Ing del Software"
        varchar nombre_corto
        varchar tipo "GRADO MASTER DOCTORADO"
        int plan_estudios_anio "2010"
        int creditos_totales "240"
        int duracion_anios "4"
        varchar requisito_idioma "B1"
        boolean activa
    }
    
    ASIGNATURAS {
        uuid id PK
        uuid titulacion_id FK
        uuid departamento_id FK
        varchar codigo "2050001"
        varchar nombre "Fundamentos de Programacion"
        int curso "1 2 3 4"
        decimal creditos "12 6"
        varchar duracion "A C1 C2"
        varchar tipologia "TRONCAL OBLIGATORIA OPTATIVA"
        boolean es_formacion_basica
        boolean es_optativa
        varchar nombre_normalizado "fundamentos de programacion"
        text[] palabras_clave
        boolean activa
    }
    
    PLANES_DOCENTES {
        uuid id PK
        uuid asignatura_id FK
        varchar curso_academico "2025-26"
        varchar grupo "Grupo 1"
        varchar url_documento
        varchar hash_documento "SHA256"
        date fecha_documento
        varchar coordinador_nombre
        varchar estado_rag "pendiente procesando completado error"
        timestamptz fecha_procesamiento
        text error_procesamiento
        timestamptz updated_at
    }
    
    PLANES_DOCENTES_CHUNKS {
        uuid id PK
        uuid plan_docente_id FK
        text contenido
        vector embedding "768 dims"
        varchar seccion "Evaluacion Contenidos Metodologia"
        varchar subseccion
        int numero_pagina
        int orden_chunk
        jsonb metadata
        timestamptz updated_at
    }
    
    PROFESORES {
        uuid id PK
        uuid departamento_id FK
        varchar nombre
        varchar apellidos
        varchar nombre_completo "GENERATED"
        varchar nombre_normalizado
        varchar email
        varchar telefono
        varchar despacho "F1.45"
        varchar edificio
        varchar planta
        varchar web_personal
        varchar orcid
        boolean activo
    }
    
    TUTORIAS {
        uuid id PK
        uuid profesor_id FK
        int dia_semana "1-5"
        time hora_inicio
        time hora_fin
        varchar ubicacion
        varchar modalidad "presencial online mixta"
        varchar enlace_online
        varchar curso_academico
        varchar cuatrimestre
        text notas
        boolean activa
    }
    
    PROFESOR_ASIGNATURA {
        uuid id PK
        uuid profesor_id FK
        uuid asignatura_id FK
        varchar curso_academico
        varchar grupo
        boolean es_coordinador
        varchar tipo_docencia "teoria practicas laboratorio"
    }
    
    AULAS {
        uuid id PK
        uuid centro_id FK
        varchar codigo "A1.01"
        varchar nombre
        varchar edificio
        varchar planta
        int capacidad
        varchar tipo "teoria laboratorio seminario"
        boolean tiene_proyector
        boolean tiene_ordenadores
        boolean activa
    }
    
    GRUPOS_CLASE {
        uuid id PK
        uuid asignatura_id FK
        varchar codigo "1 A"
        varchar nombre "Grupo 1"
        varchar tipo "teoria practicas laboratorio"
        varchar curso_academico
        varchar cuatrimestre
        int capacidad_maxima
        varchar idioma "ES EN"
        boolean activo
    }
    
    HORARIOS {
        uuid id PK
        uuid grupo_id FK
        uuid aula_id FK
        uuid profesor_id FK
        int dia_semana "1-5"
        time hora_inicio
        time hora_fin
        date fecha_inicio
        date fecha_fin
        text notas
        boolean activo
    }
    
    CATEGORIAS_TRAMITES {
        uuid id PK
        varchar codigo UK "matricula becas"
        varchar nombre
        text descripcion
        varchar icono
        int orden
        boolean activa
    }
    
    TRAMITES {
        uuid id PK
        uuid categoria_id FK
        uuid universidad_id FK
        varchar codigo
        varchar nombre
        text descripcion
        varchar url_oficial
        varchar url_formulario
        text[] palabras_clave
        varchar estado_rag
        timestamptz fecha_procesamiento
        boolean activo
    }
    
    TRAMITES_CHUNKS {
        uuid id PK
        uuid tramite_id FK
        text contenido
        vector embedding "768 dims"
        varchar seccion
        varchar fuente
        jsonb metadata
    }
    
    ENLACES_UTILES {
        uuid id PK
        varchar tema "horarios matricula"
        varchar titulo
        text descripcion
        varchar url
        uuid universidad_id FK
        uuid centro_id FK
        int prioridad
        boolean activo
    }
    
    INTENTS_FALLBACK {
        uuid id PK
        varchar intent "ask_horario"
        text respuesta_texto
        uuid[] enlaces_ids
        boolean activo
    }
