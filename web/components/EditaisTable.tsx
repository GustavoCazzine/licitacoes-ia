import Link from 'next/link';
import type { Edital } from '@/lib/queries';
import { StatusBadge } from './StatusBadge';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function currency(value: number | null): string {
  if (value === null) return '—';
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    notation: value >= 1_000_000 ? 'compact' : 'standard',
    maximumFractionDigits: value >= 1_000_000 ? 1 : 0,
  }).format(value);
}

function fmtDate(s: string | null): string {
  if (!s) return '—';
  const d = new Date(s);
  return isNaN(d.getTime())
    ? '—'
    : d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' });
}

function truncate(text: string | null, n = 90): string {
  if (!text) return '—';
  return text.length > n ? text.slice(0, n) + '…' : text;
}

// ---------------------------------------------------------------------------
// Confidence bar
// ---------------------------------------------------------------------------

function ConfiancaBar({ value }: { value: number | null }) {
  if (value === null) return <span className="text-gray-300 text-xs">—</span>;
  const pct = Math.round(value * 100);
  const bar =
    pct >= 80 ? 'bg-emerald-500' : pct >= 60 ? 'bg-amber-400' : 'bg-rose-400';
  const text =
    pct >= 80 ? 'text-emerald-700' : pct >= 60 ? 'text-amber-700' : 'text-rose-600';
  return (
    <div className="flex items-center gap-2 min-w-[80px]">
      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full ${bar} rounded-full transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`text-xs font-medium tabular-nums ${text}`}>{pct}%</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Table
// ---------------------------------------------------------------------------

const TH = 'px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider whitespace-nowrap';
const TD = 'px-4 py-3 text-sm';

export function EditaisTable({ editais }: { editais: Edital[] }) {
  if (editais.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-gray-200 py-16 text-center shadow-sm">
        <p className="text-4xl mb-3">📭</p>
        <p className="text-gray-400 text-sm">Nenhum edital encontrado para este filtro.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-100">
          <thead className="bg-gray-50/80">
            <tr>
              <th className={TH}>Objeto</th>
              <th className={TH}>Categoria</th>
              <th className={TH}>Confiança</th>
              <th className={TH}>Valor Est.</th>
              <th className={TH}>Abertura</th>
              <th className={TH}>Status</th>
              <th className={TH + ' text-right'}>Link</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {editais.map((e) => (
              <tr key={e.id} className="hover:bg-indigo-50/30 transition-colors group">
                {/* Objeto */}
                <td className={`${TD} max-w-sm`}>
                  <span
                    className="text-gray-800 leading-snug block"
                    title={e.objeto_raw ?? undefined}
                  >
                    {truncate(e.objeto_resumo ?? e.objeto_raw)}
                  </span>
                  {e.numero_processo && (
                    <span className="text-gray-400 text-xs mt-0.5 block font-mono">
                      {e.numero_processo.slice(0, 30)}
                    </span>
                  )}
                </td>

                {/* Categoria */}
                <td className={`${TD} text-gray-500 whitespace-nowrap`}>
                  {e.classificacao ?? '—'}
                </td>

                {/* Confiança */}
                <td className={TD}>
                  <ConfiancaBar value={e.confianca} />
                </td>

                {/* Valor */}
                <td className={`${TD} text-gray-700 whitespace-nowrap tabular-nums`}>
                  {currency(e.valor_estimado)}
                </td>

                {/* Abertura */}
                <td className={`${TD} text-gray-500 whitespace-nowrap`}>
                  {fmtDate(e.data_abertura)}
                </td>

                {/* Status */}
                <td className={`${TD} whitespace-nowrap`}>
                  <StatusBadge
                    status={e.status}
                    classificacao={e.classificacao}
                    confianca={e.confianca}
                  />
                </td>

                {/* Link */}
                <td className={`${TD} text-right whitespace-nowrap`}>
                  {e.link_original ? (
                    <Link
                      href={e.link_original}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-indigo-500 hover:text-indigo-700 text-xs font-medium opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      Abrir ↗
                    </Link>
                  ) : (
                    <span className="text-gray-300 text-xs">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="px-4 py-3 border-t border-gray-100 bg-gray-50/50">
        <p className="text-xs text-gray-400">
          {editais.length} edital{editais.length !== 1 ? 'is' : ''} exibido{editais.length !== 1 ? 's' : ''}
        </p>
      </div>
    </div>
  );
}
