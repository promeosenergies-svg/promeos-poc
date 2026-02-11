import { Info } from 'lucide-react';

const CONFIDENCE = {
  high:   { label: 'Confiance elevee', color: 'bg-green-50 text-green-700', dot: 'bg-green-500' },
  medium: { label: 'Confiance moyenne', color: 'bg-amber-50 text-amber-700', dot: 'bg-amber-500' },
  low:    { label: 'Estimation', color: 'bg-gray-100 text-gray-600', dot: 'bg-gray-400' },
};

export default function TrustBadge({ source, period, confidence = 'medium', className = '' }) {
  const cfg = CONFIDENCE[confidence] || CONFIDENCE.medium;
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs ${cfg.color} px-2 py-0.5 rounded-full ${className}`} title={cfg.label}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {source && <span>{source}</span>}
      {period && <span className="text-gray-400">|</span>}
      {period && <span>{period}</span>}
    </span>
  );
}
