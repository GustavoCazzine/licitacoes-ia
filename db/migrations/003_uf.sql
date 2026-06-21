-- Migration 003: coluna uf em editais (necessária para filtros por região)

ALTER TABLE editais ADD COLUMN IF NOT EXISTS uf CHAR(2);

CREATE INDEX IF NOT EXISTS idx_editais_uf ON editais(uf);
