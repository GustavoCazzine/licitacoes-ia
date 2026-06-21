-- Migration 002: integração com Supabase Auth

ALTER TABLE clientes ADD COLUMN IF NOT EXISTS auth_user_id UUID UNIQUE;

CREATE INDEX IF NOT EXISTS idx_clientes_auth_user_id ON clientes(auth_user_id);
