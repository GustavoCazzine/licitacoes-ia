import { Pool } from 'pg';

declare global {
  // eslint-disable-next-line no-var
  var _pgPool: Pool | undefined;
}

const isProd = process.env.NODE_ENV === 'production';

function createPool(): Pool {
  if (!process.env.DATABASE_URL) {
    throw new Error(
      'DATABASE_URL não está definida. ' +
      'Adicione-a nas variáveis de ambiente da Vercel (Project Settings → Environment Variables).'
    );
  }
  return new Pool({
    connectionString: process.env.DATABASE_URL,
    max: isProd ? 3 : 5,
    idleTimeoutMillis: 30_000,
    connectionTimeoutMillis: 10_000,
    // Supabase e a maioria dos Postgres na nuvem requerem SSL
    ssl: isProd ? { rejectUnauthorized: false } : false,
  });
}

// Reutiliza o pool entre hot-reloads no dev
const pool = globalThis._pgPool ?? createPool();
if (!isProd) globalThis._pgPool = pool;

export async function query<T = Record<string, unknown>>(
  sql: string,
  params?: unknown[]
): Promise<T[]> {
  const { rows } = await pool.query(sql, params ?? []);
  return rows as T[];
}
