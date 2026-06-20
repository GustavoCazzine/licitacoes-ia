import Link from 'next/link';
import { getEditais, countByFilter, type FilterKey } from '@/lib/queries';
import { EditaisTable } from '@/components/EditaisTable';

export const dynamic = 'force-dynamic';

// ---------------------------------------------------------------------------
// Filter tab config
// ---------------------------------------------------------------------------

const FILTERS: { label: string; value: FilterKey; color: string }[] = [
  { label: 'Todos', value: undefined, color: 'gray' },
  { label: 'Relevantes', value: 'relevante', color: 'emerald' },
  { label: 'Revisão', value: 'revisao_manual', color: 'amber' },
  { label: 'Pendentes', value: 'pendente', color: 'sky' },
  { label: 'Descartados', value: 'descartado', color: 'gray' },
];

function tabClasses(active: boolean, color: string): string {
  if (active) {
    const map: Record<string, string> = {
      emerald: 'bg-emerald-600 text-white shadow-sm',
      amber: 'bg-amber-500 text-white shadow-sm',
      sky: 'bg-sky-600 text-white shadow-sm',
      gray: 'bg-gray-800 text-white shadow-sm',
    };
    return map[color] ?? 'bg-indigo-600 text-white shadow-sm';
  }
  return 'bg-white text-gray-600 border border-gray-200 hover:border-gray-300 hover:bg-gray-50';
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

interface PageProps {
  searchParams: Promise<{ filter?: string; q?: string }>;
}

export default async function EditaisPage({ searchParams }: PageProps) {
  const { filter: rawFilter, q } = await searchParams;

  // Valida o filtro
  const validFilters: (FilterKey | string)[] = [
    'relevante', 'revisao_manual', 'pendente', 'descartado',
  ];
  const filter: FilterKey = validFilters.includes(rawFilter ?? '')
    ? (rawFilter as FilterKey)
    : undefined;

  const [editais, counts] = await Promise.all([
    getEditais(filter, q),
    countByFilter(),
  ]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Editais</h1>
        <p className="mt-1 text-sm text-gray-400">
          Licitações capturadas e classificadas pelo pipeline
        </p>
      </div>

      {/* Filter tabs + Search */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
        {/* Tabs */}
        <div className="flex flex-wrap gap-2">
          {FILTERS.map(({ label, value, color }) => {
            const active = filter === value || (!filter && !value);
            const count =
              value === undefined
                ? counts.todos
                : counts[value as keyof typeof counts] ?? 0;
            const href = value ? `/editais?filter=${value}` : '/editais';
            return (
              <Link
                key={label}
                href={href}
                className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all ${tabClasses(active, color)}`}
              >
                {label}
                <span
                  className={`text-xs rounded-full px-1.5 py-0.5 tabular-nums ${
                    active
                      ? 'bg-white/20 text-white'
                      : 'bg-gray-100 text-gray-500'
                  }`}
                >
                  {count}
                </span>
              </Link>
            );
          })}
        </div>

        {/* Search */}
        <form
          action="/editais"
          method="GET"
          className="flex gap-2 ml-auto"
        >
          {filter && <input type="hidden" name="filter" value={filter} />}
          <input
            type="search"
            name="q"
            defaultValue={q ?? ''}
            placeholder="Buscar no objeto…"
            className="w-56 px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
          <button
            type="submit"
            className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium"
          >
            Buscar
          </button>
        </form>
      </div>

      {/* Active search indicator */}
      {q && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">
            Buscando por: <strong className="text-gray-700">&ldquo;{q}&rdquo;</strong>
          </span>
          <Link
            href={filter ? `/editais?filter=${filter}` : '/editais'}
            className="text-xs text-gray-400 hover:text-gray-600 underline"
          >
            limpar
          </Link>
        </div>
      )}

      {/* Table */}
      <EditaisTable editais={editais} />
    </div>
  );
}
