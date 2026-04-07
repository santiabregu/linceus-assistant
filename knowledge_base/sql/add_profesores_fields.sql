-- =========================================
-- Migración: Añadir campos a profesores
-- Sprint 7 - Épica Profesores
-- =========================================

-- categoria_academica: Catedrático, Titular, Contratado Doctor, etc.
-- Disponible en todos los departamentos (DTE, LSI, MA1, CCIA)
ALTER TABLE public.profesores
  ADD COLUMN IF NOT EXISTS categoria_academica VARCHAR(100) NULL;

-- enlace_perfil: URL del perfil del profesor en la web del departamento
ALTER TABLE public.profesores
  ADD COLUMN IF NOT EXISTS enlace_perfil VARCHAR(500) NULL;
