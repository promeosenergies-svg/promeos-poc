/**
 * PROMEOS — ContextBanner (Consumption Explorer)
 * Info banner: one row per selected site — name, readings count, energy types, date range.
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

export default function ContextBanner({ availabilityBySite = {}, siteIds = [] }) {
  const rows = siteIds
    .map((sid) => availabilityBySite[sid])
    .filter((a) => a?.has_data);

  if (!rows.length) return null;

  return (
    <div className="space-y-1.5">
      {rows.map((a) => (
        <div
          key={a.site_nom}
          className="flex items-center gap-4 bg-blue-50 border border-blue-200 rounded-lg px-4 py-2.5 text-sm"
        >
          <CheckCircle size={16} className="text-blue-600 shrink-0" />
          <span className="text-blue-800">
            <strong>{a.site_nom || 'Site'}</strong> — {(a.readings_count || 0).toLocaleString()} releves
            {a.energy_types?.length > 0 && ` (${a.energy_types.join(', ')})`}
          </span>
          {a.first_ts && a.last_ts && (
            <span className="text-xs text-blue-500 ml-auto whitespace-nowrap">
              {fmtDate(a.first_ts)} → {fmtDate(a.last_ts)}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
