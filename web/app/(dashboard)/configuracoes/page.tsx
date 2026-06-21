import { redirect } from 'next/navigation';
import { revalidatePath } from 'next/cache';
import { createClient } from '@/lib/supabase/server';
import { query } from '@/lib/db';

export const dynamic = 'force-dynamic';

// ---------------------------------------------------------------------------
// Dados de domínio
// ---------------------------------------------------------------------------

const CATEGORIAS = [
  { value: 'trator', label: 'Tratores' },
  { value: 'retroescavadeira', label: 'Retroescavadeiras' },
  { value: 'motoniveladora', label: 'Motoniveladoras' },
  { value: 'motor_diesel', label: 'Motores diesel industriais' },
  { value: 'peca_manutencao', label: 'Peças e manutenção de frota' },
  { value: 'locacao_maquinario', label: 'Locação de maquinário agrícola' },
];

const UFS = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO',
  'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI',
  'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
];

// ---------------------------------------------------------------------------
// Tipos
// ---------------------------------------------------------------------------

interface Filtros {
  telegram_chat_id?: string;
  telegram_token?: string;
  categorias?: string[];
  ufs?: string[];
}

interface ClienteRow {
  filtros: Filtros;
}

// ---------------------------------------------------------------------------
// Server Actions
// ---------------------------------------------------------------------------

async function salvarFiltros(formData: FormData) {
  'use server';
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect('/login');

  const categorias = formData.getAll('categorias') as string[];
  const ufs = formData.getAll('ufs') as string[];

  await query(
    `UPDATE clientes
     SET filtros = filtros || $1::jsonb
     WHERE auth_user_id = $2`,
    [JSON.stringify({ categorias, ufs }), user.id],
  );

  redirect('/configuracoes?saved=1');
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function ConfiguracoesPage({
  searchParams,
}: {
  searchParams: Promise<{ saved?: string }>;
}) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect('/login');

  const { saved } = await searchParams;

  // Busca filtros atuais do cliente
  const rows = await query<ClienteRow>(
    `SELECT filtros FROM clientes WHERE auth_user_id = $1 LIMIT 1`,
    [user.id],
  );

  let filtros: Filtros = rows[0]?.filtros ?? {};

  // Gera token Telegram na primeira visita se ainda não existir
  if (!filtros.telegram_token) {
    const token = crypto.randomUUID().replace(/-/g, '').substring(0, 8).toUpperCase();
    await query(
      `UPDATE clientes SET filtros = filtros || $1::jsonb WHERE auth_user_id = $2`,
      [JSON.stringify({ telegram_token: token }), user.id],
    );
    filtros = { ...filtros, telegram_token: token };
  }

  const categoriasAtivas = new Set(filtros.categorias ?? []);
  const ufsAtivas = new Set(filtros.ufs ?? []);

  return (
    <div className="space-y-8 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Configurações</h1>
        <p className="mt-1 text-sm text-gray-400">
          Defina o que você quer monitorar e como receber alertas.
        </p>
      </div>

      {saved && (
        <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm px-4 py-3 rounded-xl">
          <span className="text-base">✓</span>
          Configurações salvas com sucesso.
        </div>
      )}

      <form action={salvarFiltros} className="space-y-6">
        {/* Categorias */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 space-y-4">
          <div>
            <h2 className="text-base font-semibold text-gray-900">Categorias de interesse</h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Você receberá alertas apenas para as categorias selecionadas.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {CATEGORIAS.map(({ value, label }) => (
              <label
                key={value}
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg border border-gray-100 hover:border-indigo-200 hover:bg-indigo-50/40 cursor-pointer transition-colors group"
              >
                <input
                  type="checkbox"
                  name="categorias"
                  value={value}
                  defaultChecked={categoriasAtivas.has(value)}
                  className="w-4 h-4 rounded text-indigo-600 border-gray-300 focus:ring-indigo-500"
                />
                <span className="text-sm text-gray-700 group-hover:text-indigo-700 transition-colors">
                  {label}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Regiões */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 space-y-4">
          <div>
            <h2 className="text-base font-semibold text-gray-900">Regiões de interesse</h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Selecione os estados que deseja monitorar. Deixe vazio para receber de todo o Brasil.
            </p>
          </div>
          <div className="grid grid-cols-4 sm:grid-cols-6 gap-2">
            {UFS.map((uf) => (
              <label
                key={uf}
                className="flex items-center justify-center gap-1.5 px-2 py-2 rounded-lg border border-gray-100 hover:border-indigo-200 hover:bg-indigo-50/40 cursor-pointer transition-colors text-sm font-medium text-gray-600 hover:text-indigo-700 group"
              >
                <input
                  type="checkbox"
                  name="ufs"
                  value={uf}
                  defaultChecked={ufsAtivas.has(uf)}
                  className="w-3.5 h-3.5 rounded text-indigo-600 border-gray-300 focus:ring-indigo-500"
                />
                {uf}
              </label>
            ))}
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            className="px-6 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 transition-colors shadow-sm"
          >
            Salvar configurações
          </button>
        </div>
      </form>

      {/* Telegram */}
      <div className="bg-white border border-gray-200 rounded-2xl p-6 space-y-4">
        <div>
          <h2 className="text-base font-semibold text-gray-900">Conectar Telegram</h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Vincule sua conta para receber os alertas diretamente no Telegram.
          </p>
        </div>

        {filtros.telegram_chat_id ? (
          <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm px-4 py-3 rounded-xl">
            <span className="text-base">✓</span>
            Telegram conectado. Você receberá alertas nesta conta.
          </div>
        ) : (
          <div className="space-y-3">
            <div className="bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 space-y-2">
              <p className="text-xs text-slate-500 font-medium uppercase tracking-wide">Seu código de vinculação</p>
              <p className="text-2xl font-mono font-bold text-slate-900 tracking-widest">
                {filtros.telegram_token}
              </p>
            </div>
            <ol className="text-sm text-gray-600 space-y-1.5 list-decimal list-inside">
              <li>Abra o Telegram e procure por <strong>@licitacoesia_bot</strong></li>
              <li>
                Envie o comando: <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs font-mono">/start {filtros.telegram_token}</code>
              </li>
              <li>Pronto — seus alertas serão entregues nesta conta.</li>
            </ol>
          </div>
        )}
      </div>
    </div>
  );
}
