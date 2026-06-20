interface Props {
  status: string;
  classificacao?: string | null;
  confianca?: number | null;
}

interface Meta {
  label: string;
  dot: string;
  pill: string;
}

export function resolveStatus(
  status: string,
  classificacao?: string | null,
  confianca?: number | null
): Meta {
  if (status === 'pendente') {
    return {
      label: 'Pendente',
      dot: 'bg-sky-400',
      pill: 'bg-sky-50 text-sky-700 ring-sky-600/20',
    };
  }
  if (status === 'revisao_manual') {
    return {
      label: 'Revisão',
      dot: 'bg-amber-400',
      pill: 'bg-amber-50 text-amber-700 ring-amber-600/20',
    };
  }
  // classificado
  const irrelevante =
    !classificacao || ['irrelevante', 'indefinido'].includes(classificacao);
  if (!irrelevante && (confianca ?? 0) >= 0.6) {
    return {
      label: 'Relevante',
      dot: 'bg-emerald-400',
      pill: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20',
    };
  }
  return {
    label: 'Descartado',
    dot: 'bg-gray-300',
    pill: 'bg-gray-50 text-gray-500 ring-gray-500/10',
  };
}

export function StatusBadge({ status, classificacao, confianca }: Props) {
  const { label, dot, pill } = resolveStatus(status, classificacao, confianca);
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${pill}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      {label}
    </span>
  );
}
