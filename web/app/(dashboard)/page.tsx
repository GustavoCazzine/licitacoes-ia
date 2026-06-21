import { getStats, getRecentRelevantes } from '@/lib/queries';
import { StatsGrid } from '@/components/StatsGrid';
import { EditaisTable } from '@/components/EditaisTable';
import Link from 'next/link';

export const dynamic = 'force-dynamic';

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Bom dia';
  if (h < 18) return 'Boa tarde';
  return 'Boa noite';
}

function todayLabel(): string {
  return new Date().toLocaleDateString('pt-BR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

export default async function DashboardPage() {
  const [stats, recentEditais] = await Promise.all([
    getStats(),
    getRecentRelevantes(),
  ]);

  return (
    <div className="space-y-10">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{greeting()} 👋</h1>
          <p className="mt-1 text-sm text-gray-400 capitalize">{todayLabel()}</p>
        </div>
        <Link
          href="/editais"
          className="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
        >
          Ver todos os editais →
        </Link>
      </div>

      {/* Stats */}
      <StatsGrid stats={stats} />

      {/* Recent relevant */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-gray-800">
            Últimas licitações relevantes
          </h2>
          {recentEditais.length > 0 && (
            <Link
              href="/editais?filter=relevante"
              className="text-xs text-indigo-500 hover:text-indigo-700 font-medium"
            >
              Ver todos relevantes →
            </Link>
          )}
        </div>
        <EditaisTable editais={recentEditais} />
      </section>

      {/* Empty state */}
      {stats.total === 0 && (
        <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-10 text-center">
          <p className="text-5xl mb-4">🚀</p>
          <h3 className="font-semibold text-gray-700 mb-2">Banco ainda vazio</h3>
          <p className="text-sm text-gray-400 max-w-md mx-auto">
            Execute o pipeline para importar os primeiros editais:
          </p>
          <pre className="mt-4 bg-gray-900 text-green-400 text-xs rounded-xl px-6 py-4 inline-block text-left">
            {`python pipeline.py --uf SP --paginas 3
python -m notifier.telegram`}
          </pre>
        </div>
      )}
    </div>
  );
}
