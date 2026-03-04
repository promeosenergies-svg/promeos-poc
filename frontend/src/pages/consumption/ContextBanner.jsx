/**
 * PROMEOS — ContextBanner (Consumption Explorer)
 * Info banner: site name, readings count, first/last date, energy types.
 */
import { CheckCircle } from 'lucide-react';

function fmtDate(ts) {
  if (!ts) return '—';
  return new Date(ts).toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

export default function ContextBanner({ availability }) {
  if (!availability?.has_data) return null;

  const { site_nom, readings_count, energy_types, first_ts, last_ts } = availability;

  return (
    <div className="flex items-center gap-4 bg-blue-50 border border-blue-200 rounded-lg px-4 py-2.5 text-sm">
      <CheckCircle size={16} className="text-blue-600 shrink-0" />
      <span className="text-blue-800">
        <strong>{site_nom || 'Site'}</strong> — {(readings_count || 0).toLocaleString()} releves
        {energy_types?.length > 0 && ` (${energy_types.join(', ')})`}
      </span>
      {first_ts && last_ts && (
        <span className="text-xs text-blue-500 ml-auto whitespace-nowrap">
          {fmtDate(first_ts)} → {fmtDate(last_ts)}
        </span>
      )}
    </div>
  );
}
