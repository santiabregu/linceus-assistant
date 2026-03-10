-- ============================================================================
-- Función de búsqueda vectorial para proyectos docentes
-- Ejecutar en Supabase SQL Editor tras crear las tablas
-- ============================================================================

-- Índice HNSW para búsqueda rápida de similitud coseno
-- (Crear solo si no existe)
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
ON planes_docentes_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Índice para filtrar por plan_docente_id (FK)
CREATE INDEX IF NOT EXISTS idx_chunks_plan_docente
ON planes_docentes_chunks (plan_docente_id);

-- Índice para filtrar por sección
CREATE INDEX IF NOT EXISTS idx_chunks_seccion
ON planes_docentes_chunks (seccion);

-- Índice en planes_docentes para búsquedas por asignatura + curso
CREATE INDEX IF NOT EXISTS idx_planes_asignatura_curso
ON planes_docentes (asignatura_id, curso_academico);

-- ============================================================================
-- Función: buscar_plan_docente
-- Búsqueda vectorial filtrada por asignatura (y opcionalmente grupo/sección)
-- ============================================================================
CREATE OR REPLACE FUNCTION buscar_plan_docente(
    query_embedding vector(2000),
    p_asignatura_codigo VARCHAR DEFAULT NULL,
    p_asignatura_id UUID DEFAULT NULL,
    p_curso_academico VARCHAR DEFAULT '2025-26',
    p_grupo VARCHAR DEFAULT NULL,
    p_seccion VARCHAR DEFAULT NULL,
    p_limite INT DEFAULT 5,
    p_umbral_similitud FLOAT DEFAULT 0.5
)
RETURNS TABLE (
    chunk_id UUID,
    contenido TEXT,
    seccion VARCHAR,
    subseccion VARCHAR,
    similitud FLOAT,
    asignatura_nombre VARCHAR,
    asignatura_codigo VARCHAR,
    grupo VARCHAR,
    curso_academico VARCHAR,
    metadata JSONB
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_asignatura_id UUID;
BEGIN
    -- Resolver asignatura_id desde código si se proporcionó
    IF p_asignatura_id IS NOT NULL THEN
        v_asignatura_id := p_asignatura_id;
    ELSIF p_asignatura_codigo IS NOT NULL THEN
        SELECT a.id INTO v_asignatura_id
        FROM asignaturas a
        WHERE a.codigo = p_asignatura_codigo AND a.activa = true
        LIMIT 1;
        
        IF v_asignatura_id IS NULL THEN
            RAISE NOTICE 'Asignatura con código % no encontrada', p_asignatura_codigo;
            RETURN;
        END IF;
    END IF;

    RETURN QUERY
    SELECT 
        c.id AS chunk_id,
        c.contenido,
        c.seccion,
        c.subseccion,
        1 - (c.embedding <=> query_embedding) AS similitud,
        a.nombre AS asignatura_nombre,
        a.codigo AS asignatura_codigo,
        pd.grupo,
        pd.curso_academico,
        c.metadata
    FROM planes_docentes_chunks c
    JOIN planes_docentes pd ON pd.id = c.plan_docente_id
    JOIN asignaturas a ON a.id = pd.asignatura_id
    WHERE 
        pd.estado_rag = 'completado'
        AND pd.curso_academico = p_curso_academico
        -- Filtro por asignatura (si se proporcionó)
        AND (v_asignatura_id IS NULL OR pd.asignatura_id = v_asignatura_id)
        -- Filtro por grupo (si se proporcionó)
        AND (p_grupo IS NULL OR pd.grupo = p_grupo)
        -- Filtro por sección (si se proporcionó)
        AND (p_seccion IS NULL OR c.seccion = p_seccion)
        -- Filtro por umbral de similitud
        AND 1 - (c.embedding <=> query_embedding) >= p_umbral_similitud
    ORDER BY c.embedding <=> query_embedding
    LIMIT p_limite;
END;
$$;

-- ============================================================================
-- Función: buscar_plan_docente_global
-- Búsqueda sin filtro de asignatura (para preguntas generales)
-- ============================================================================
CREATE OR REPLACE FUNCTION buscar_plan_docente_global(
    query_embedding vector(2000),
    p_curso_academico VARCHAR DEFAULT '2025-26',
    p_limite INT DEFAULT 5,
    p_umbral_similitud FLOAT DEFAULT 0.5
)
RETURNS TABLE (
    chunk_id UUID,
    contenido TEXT,
    seccion VARCHAR,
    similitud FLOAT,
    asignatura_nombre VARCHAR,
    asignatura_codigo VARCHAR,
    grupo VARCHAR,
    metadata JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id AS chunk_id,
        c.contenido,
        c.seccion,
        1 - (c.embedding <=> query_embedding) AS similitud,
        a.nombre AS asignatura_nombre,
        a.codigo AS asignatura_codigo,
        pd.grupo,
        c.metadata
    FROM planes_docentes_chunks c
    JOIN planes_docentes pd ON pd.id = c.plan_docente_id
    JOIN asignaturas a ON a.id = pd.asignatura_id
    WHERE 
        pd.estado_rag = 'completado'
        AND pd.curso_academico = p_curso_academico
        AND 1 - (c.embedding <=> query_embedding) >= p_umbral_similitud
    ORDER BY c.embedding <=> query_embedding
    LIMIT p_limite;
END;
$$;

-- ============================================================================
-- Comentarios para documentación
-- ============================================================================
COMMENT ON FUNCTION buscar_plan_docente IS 
'Búsqueda vectorial filtrada de chunks de proyectos docentes. 
Permite filtrar por asignatura (código o UUID), grupo y sección.
Devuelve chunks ordenados por similitud coseno descendente.';

COMMENT ON FUNCTION buscar_plan_docente_global IS 
'Búsqueda vectorial global sin filtro de asignatura.
Útil para preguntas generales que no mencionan una asignatura concreta.';
