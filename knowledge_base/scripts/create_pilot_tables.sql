-- Tablas para el piloto con usuarios de prueba
-- Ejecutar en Supabase SQL Editor

-- 1. Log de conversaciones (todas las preguntas al chatbot)
CREATE TABLE IF NOT EXISTS conversation_log (
    id SERIAL PRIMARY KEY,
    session_id TEXT,
    user_message TEXT NOT NULL,
    bot_response TEXT,
    intent TEXT,
    confidence REAL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Feedback de usuarios
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    session_id TEXT,
    rating INTEGER CHECK (rating IN (1, -1)),  -- 1 = positivo, -1 = negativo
    comment TEXT,
    last_user_message TEXT,
    last_bot_response TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indices para consultas rapidas
CREATE INDEX IF NOT EXISTS idx_conversation_log_created ON conversation_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at DESC);
