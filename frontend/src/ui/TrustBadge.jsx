const CONFIDENCE = {
  high: { label: 'Confiance élevée', color: 'bg-green-50 text-green-700', dot: 'bg-green-500' },
  medium: { label: 'Confiance moyenne', color: 'bg-amber-50 text-amber-700', dot: 'bg-amber-500' },
  low: { label: 'Confiance basse', color: 'bg-gray-100 text-gray-600', dot: 'bg-gray-400' },
};

function fmtPeriod(period) {
  if (!period) return null;
  return period.replace(/(\d{4})-(\d{2})-(\d{2})/g, '$3/$2/$1');
}

export default function TrustBadge({ source, period, confidence = 'medium', className = '' }) {
  const cfg = CONFIDENCE[confidence] || CONFIDENCE.medium;
  const displayPeriod = fmtPeriod(period);
  return (
    <span
      className={`inline-flex items-center gap-1.5 text-xs ${cfg.color} px-2 py-0.5 rounded-full ${className}`}
      title={cfg.label}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {(source || cfg.label) && <span>{source || cfg.label}</span>}
      {displayPeriod && <span className="text-gray-400">|</span>}
      {displayPeriod && <span>{displayPeriod}</span>}
    </span>
  );
}
