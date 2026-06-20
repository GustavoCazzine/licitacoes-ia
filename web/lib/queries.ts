import { query } from './db';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Edital {
  id: number;
  fonte: string;
  numero_processo: string | null;
  objeto_raw: string | null;
  objeto_resumo: string | null;
  valor_estimado: number | null;
  data_abertura: string | null;
  link_original: string | null;
  classificacao: string | null;
  confianca: number | null;
  status: string;
  created_at: string;
}

export interface Stats {
  total: number;
  relevantes: number;
  revisao_manual: number;
  pendentes: number;
}

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

const EDITAL_COLS = `
  id, fonte, numero_processo,
  objeto_raw, objeto_resumo,
  valor_estimado::float,
  data_abertura, link_original,
  classificacao, confianca::float,
  status, created_at
`;

export async function getStats(): Promise<Stats> {
  const [row] = await query<Record<string, string>>(`
    SELECT
      COUNT(*)::int                                                   AS total,
      COUNT(*) FILTER (
        WHERE status = 'classificado'
          AND classificacao NOT IN ('irrelevante', 'indefinido')
          AND confianca >= 0.6
      )::int                                                          AS relevantes,
      COUNT(*) FILTER (WHERE status = 'revisao_manual')::int         AS revisao_manual,
      COUNT(*) FILTER (WHERE status = 'pendente')::int               AS pendentes
    FROM editais
  `);
  return {
    total: Number(row.total),
    relevantes: Number(row.relevantes),
    revisao_manual: Number(row.revisao_manual),
    pendentes: Number(row.pendentes),
  };
}

export async function getRecentRelevantes(): Promise<Edital[]> {
  return query<Edital>(`
    SELECT ${EDITAL_COLS}
    FROM editais
    WHERE status = 'classificado'
      AND classificacao NOT IN ('irrelevante', 'indefinido')
      AND confianca >= 0.6
    ORDER BY created_at DESC
    LIMIT 10
  `);
}

export type FilterKey = 'relevante' | 'revisao_manual' | 'pendente' | 'descartado' | undefined;

export async function getEditais(
  filter?: FilterKey,
  search?: string
): Promise<Edital[]> {
  const conditions: string[] = [];
  const params: unknown[] = [];
  let p = 1;

  switch (filter) {
    case 'relevante':
      conditions.push(
        `status = 'classificado'`,
        `classificacao NOT IN ('irrelevante', 'indefinido')`,
        `confianca >= 0.6`
      );
      break;
    case 'revisao_manual':
      conditions.push(`status = 'revisao_manual'`);
      break;
    case 'pendente':
      conditions.push(`status = 'pendente'`);
      break;
    case 'descartado':
      conditions.push(
        `status = 'classificado'`,
        `(classificacao IN ('irrelevante', 'indefinido') OR confianca < 0.6 OR confianca IS NULL)`
      );
      break;
  }

  if (search?.trim()) {
    conditions.push(`objeto_raw ILIKE $${p}`);
    params.push(`%${search.trim()}%`);
    p++;
  }

  const where = conditions.length ? `WHERE ${conditions.join(' AND ')}` : '';

  return query<Edital>(
    `SELECT ${EDITAL_COLS} FROM editais ${where} ORDER BY created_at DESC LIMIT 200`,
    params
  );
}

export async function countByFilter(): Promise<Record<FilterKey | 'todos', number>> {
  const [row] = await query<Record<string, string>>(`
    SELECT
      COUNT(*)::int AS todos,
      COUNT(*) FILTER (
        WHERE status = 'classificado'
          AND classificacao NOT IN ('irrelevante', 'indefinido')
          AND confianca >= 0.6
      )::int AS relevante,
      COUNT(*) FILTER (WHERE status = 'revisao_manual')::int AS revisao_manual,
      COUNT(*) FILTER (WHERE status = 'pendente')::int AS pendente,
      COUNT(*) FILTER (
        WHERE status = 'classificado'
          AND (classificacao IN ('irrelevante', 'indefinido') OR confianca < 0.6 OR confianca IS NULL)
      )::int AS descartado
    FROM editais
  `);
  return {
    todos: Number(row.todos),
    relevante: Number(row.relevante),
    revisao_manual: Number(row.revisao_manual),
    pendente: Number(row.pendente),
    descartado: Number(row.descartado),
    undefined: Number(row.todos),
  };
}
