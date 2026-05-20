import { EVENT_TYPE_LABELS, TIMELINE_ACTOR_COPY } from '../constants';
import { formatDateTimeFR } from '../utils/date';

/**
 * M2-5.3.A / M2-5.10.B — Entrée audit-list dans la timeline (maquette §8.4
 * lignes 614-637).
 *
 * Layout : dot coloré à gauche (system = calme, user = ink-400) + audit-time
 * (mono · jour gras + heure) + audit-content (actor pill + event FR + detail
 * italique Fraunces).
 *
 * Mapping acteur : `actor_role === 'system'` → pill calme ; sinon pill panel.
 * Le fallback (acteur absent) affiche « Système » en pill calme aussi.
 */
export function EventItem({ event, isFirst = false }) {
  const label = EVENT_TYPE_LABELS[event.event_type] || event.event_type;
  // `system` strict (côté backend, `actor_role` est l'enum). Un utilisateur
  // avec un actor_role custom (« admin », « manager »...) reste rendu en pill
  // panel normale ; le fallback ultime (rien) → « Système ».
  const isSystem = event.actor_role === 'system';
  const actorLabel = isSystem
    ? TIMELINE_ACTOR_COPY.systemLabel
    : event.actor_name || event.actor_role || TIMELINE_ACTOR_COPY.fallbackActor;

  // Date découpée : jour gras + heure mono (signature audit-time maquette).
  const dt = event.occurred_at ? new Date(event.occurred_at) : null;
  const dayStr = dt ? dt.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' }) : '—';
  const timeStr = dt ? dt.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : '';

  // Dot coloré aligné avec la ligne verticale du parent EventTimelineList.
  const dotColor = isFirst
    ? 'var(--sol-ink-900)'
    : isSystem
      ? 'var(--sol-calme-fg)'
      : 'var(--sol-ink-400)';

  return (
    <article
      className="relative grid items-start gap-3 py-1.5 pl-3.5 text-[12px]"
      style={{ gridTemplateColumns: '70px 1fr' }}
      title={formatDateTimeFR(event.occurred_at)}
    >
      {/* Dot — position absolute alignée avec la ligne verticale du parent. */}
      <span
        aria-hidden="true"
        className="absolute h-[11px] w-[11px] rounded-full border-2"
        style={{
          left: '-5px',
          top: '10px',
          background: isFirst ? dotColor : 'var(--sol-bg-paper)',
          borderColor: dotColor,
        }}
      />

      <span
        className="font-mono text-[10.5px] text-right tracking-[0.02em]"
        style={{ color: 'var(--sol-ink-500)' }}
      >
        <span className="font-semibold" style={{ color: 'var(--sol-ink-900)' }}>
          {dayStr}
        </span>{' '}
        {timeStr}
      </span>

      <div className="leading-[1.45]">
        <div style={{ color: 'var(--sol-ink-900)' }}>
          <span
            className="mr-1.5 inline-block rounded-[2px] px-1.5 py-px font-mono text-[10px] tracking-[0.04em]"
            style={{
              background: isSystem ? 'var(--sol-calme-bg)' : 'var(--sol-bg-panel)',
              color: isSystem ? 'var(--sol-calme-fg)' : 'var(--sol-ink-700)',
            }}
          >
            {actorLabel}
          </span>
          <span
            className="font-medium"
            style={{ fontFamily: 'var(--sol-font-body)', color: 'var(--sol-ink-900)' }}
          >
            {label}
          </span>
        </div>
        {event.summary && (
          <p
            className="mt-0.5 text-[11.5px] italic leading-[1.4]"
            style={{
              fontFamily: 'var(--sol-font-display)',
              color: 'var(--sol-ink-500)',
            }}
          >
            {event.summary}
          </p>
        )}
      </div>
    </article>
  );
}
