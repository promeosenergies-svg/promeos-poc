/**
 * EvenementsRecents — 4 derniers événements/notifications pour le cockpit exécutif.
 *
 * RÈGLE : display-only. Source : GET /api/notifications/list.
 */
import { useState, useEffect } from 'react';
import { getNotificationsList } from '../../services/api';
import { Skeleton } from '../../ui';

const SEVERITY_DOTS = {
  critical: 'bg-red-500',
  high: 'bg-amber-500',
  medium: 'bg-blue-400',
  info: 'bg-green-400',
};

const SOURCE_LABELS = {
  compliance: 'DT',
  billing: 'Billing',
  consumption: 'Alerte',
  purchase: 'Achat',
  monitoring: 'Monitoring',
  insight: 'Insight',
  manual: 'Manuel',
  action_hub: 'Actions',
};

function relativeDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const now = new Date();
  const diffMs = now - d;
  const diffH = Math.floor(diffMs / (1000 * 60 * 60));
  if (diffH < 1) return "À l'instant";
  if (diffH < 24) return `${diffH}h`;
  const diffD = Math.floor(diffH / 24);
  if (diffD === 0) return "Aujourd'hui";
  if (diffD === 1) return 'Hier';
  return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
}

export default function EvenementsRecents() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getNotificationsList({ limit: 4 })
      .then((data) => {
        const items = data?.notifications ?? data?.items ?? data ?? [];
        setEvents(Array.isArray(items) ? items.slice(0, 4) : []);
      })
      .catch(() => setEvents([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div
      className="bg-white border border-gray-200 rounded-xl p-4"
      data-testid="evenements-recents"
    >
      <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
        Événements récents
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-10 rounded" />
          ))}
        </div>
      ) : events.length === 0 ? (
        <p className="text-xs text-gray-400 text-center py-4">Aucun événement récent.</p>
      ) : (
        <div className="space-y-2.5">
          {events.map((evt, i) => {
            const dotCls = SEVERITY_DOTS[evt.severity] ?? 'bg-gray-400';
            const srcLabel = SOURCE_LABELS[evt.source_type] ?? evt.source_type ?? '';

            return (
              <div key={evt.id ?? i} className="flex items-start gap-2.5">
                <span className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${dotCls}`} />
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-gray-800 leading-snug">
                    {srcLabel && <span className="font-semibold text-gray-600">{srcLabel}</span>}{' '}
                    {evt.title ?? evt.message ?? '—'}
                  </div>
                  <div className="text-[10px] text-gray-400 mt-0.5">
                    {relativeDate(evt.created_at)}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
