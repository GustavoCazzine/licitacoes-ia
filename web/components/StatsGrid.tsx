import type { Stats } from '@/lib/queries';

interface Card {
  key: keyof Stats;
  label: string;
  sublabel: string;
  icon: string;
  value_class: string;
  border: string;
}

const CARDS: Card[] = [
  {
    key: 'total',
    label: 'Total de Editais',
    sublabel: 'Todos processados',
    icon: '📋',
    value_class: 'text-gray-900',
    border: 'border-gray-200',
  },
  {
    key: 'relevantes',
    label: 'Relevantes',
    sublabel: 'Confiança ≥ 60%',
    icon: '✅',
    value_class: 'text-emerald-700',
    border: 'border-emerald-200',
  },
  {
    key: 'revisao_manual',
    label: 'Em Revisão',
    sublabel: 'Aguardando triagem',
    icon: '🔍',
    value_class: 'text-amber-700',
    border: 'border-amber-200',
  },
  {
    key: 'pendentes',
    label: 'Pendentes',
    sublabel: 'Sem classificação',
    icon: '⏳',
    value_class: 'text-sky-700',
    border: 'border-sky-200',
  },
];

export function StatsGrid({ stats }: { stats: Stats }) {
  return (
    <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
      {CARDS.map(({ key, label, sublabel, icon, value_class, border }) => (
        <div
          key={key}
          className={`bg-white rounded-2xl border ${border} p-6 flex flex-col gap-3 shadow-sm`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
              {label}
            </span>
            <span className="text-xl">{icon}</span>
          </div>
          <p className={`text-4xl font-bold tabular-nums ${value_class}`}>
            {stats[key].toLocaleString('pt-BR')}
          </p>
          <p className="text-xs text-gray-400">{sublabel}</p>
        </div>
      ))}
    </div>
  );
}
