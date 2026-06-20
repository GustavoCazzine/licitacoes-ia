-- Migration 001: schema inicial

CREATE TABLE IF NOT EXISTS municipios (
  id          SERIAL PRIMARY KEY,
  nome        VARCHAR(255) NOT NULL,
  uf          CHAR(2)      NOT NULL,
  portal_url  TEXT,
  ativo       BOOLEAN      NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS editais (
  id               SERIAL PRIMARY KEY,
  municipio_id     INTEGER REFERENCES municipios(id),
  fonte            VARCHAR(100) NOT NULL,
  numero_processo  VARCHAR(255),
  objeto_raw       TEXT,
  objeto_resumo    TEXT,
  valor_estimado   NUMERIC(15, 2),
  data_abertura    TIMESTAMP,
  link_original    TEXT,
  pdf_hash         VARCHAR(64) UNIQUE,
  classificacao    VARCHAR(100),
  confianca        NUMERIC(4, 3),
  status           VARCHAR(50) NOT NULL DEFAULT 'pendente',
  created_at       TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS clientes (
  id        SERIAL PRIMARY KEY,
  nome      VARCHAR(255) NOT NULL,
  whatsapp  VARCHAR(20),
  email     VARCHAR(255),
  filtros   JSONB NOT NULL DEFAULT '{}',
  ativo     BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS alertas_enviados (
  id         SERIAL PRIMARY KEY,
  edital_id  INTEGER NOT NULL REFERENCES editais(id),
  cliente_id INTEGER NOT NULL REFERENCES clientes(id),
  canal      VARCHAR(50) NOT NULL,
  enviado_em TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Índices úteis para consultas frequentes
CREATE INDEX IF NOT EXISTS idx_editais_status       ON editais(status);
CREATE INDEX IF NOT EXISTS idx_editais_created_at   ON editais(created_at);
CREATE INDEX IF NOT EXISTS idx_editais_municipio_id ON editais(municipio_id);
CREATE INDEX IF NOT EXISTS idx_alertas_edital_id    ON alertas_enviados(edital_id);
CREATE INDEX IF NOT EXISTS idx_alertas_cliente_id   ON alertas_enviados(cliente_id);
