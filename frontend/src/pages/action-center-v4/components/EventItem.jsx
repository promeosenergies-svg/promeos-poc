import { EVENT_TYPE_LABELS } from '../constants';
import { formatDateTimeFR, formatRelativeDate } from '../utils/date';

/**
 * M2-5.3.A — Affichage d'un event dans la timeline.
 *
 * Label FR depuis EVENT_TYPE_LABELS (fallback : event_type brut si inconnu).
 * Acteur : actor_name → actor_role → « Système ».
 */
export function EventItem({ event }) {
  const label = EVENT_TYPE_LABELS[event.event_type] || event.event_type;
  const actor = event.actor_name || event.actor_role || 'Système';

  return (
    <article className="border-l-2 border-gray-200 py-1 pl-3">
      <div className="text-sm font-medium text-gray-900">{label}</div>
      {event.summary && <div className="mt-0.5 text-sm text-gray-600">{event.summary}</div>}
      <div className="mt-1 text-xs text-gray-500" title={formatDateTimeFR(event.occurred_at)}>
        Par <span className="text-gray-700">{actor}</span> · {formatRelativeDate(event.occurred_at)}
      </div>
    </article>
  );
}
