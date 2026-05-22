import { EVENT_TYPE_LABELS, TIMELINE_ACTOR_COPY } from '../constants';
import { formatDateTimeFR } from '../utils/date';

/**
 * M2-5.10.E — Ligne d'event dans la timeline Journal (maquette §8.2
 * lignes 642-708). Variante cross-item de `EventItem` :
 * - inclut le titre de l'item parent (action_item_title), cliquable pour
 *   ouvrir le drawer détail
 * - heure compacte HH:MM en mono (vs jour+heure pour la timeline item-scoped)
 * - actor pill comme EventItem (system = calme, user = panel)
 * - dot coloré système/utilisateur aligné avec la ligne verticale parent
 *
 * Doctrine : sélection visuelle pure ; le label `event_type` est mappé via
 * `EVENT_TYPE_LABELS` (FR) — fallback raw si type inconnu.
 */
export function JournalEventRow({ event, isFirst = false, onOpenItem }) {
  const label = EVENT_TYPE_LABELS[event.event_type] || event.event_type;
  // M2-6.C audit RGPD (CWE-359) — anti-déduction : `actor_role` (texte libre
  // technique : 'admin', 'energy_manager'…) ne doit plus servir de fallback
  // d'affichage. Cf. EventItem pour la justification doctrinale §6.3.
  const isSystem = event.actor_type === 'system';
  const actorLabel = isSystem
    ? TIMELINE_ACTOR_COPY.systemLabel
    : event.actor_name || TIMELINE_ACTOR_COPY.fallbackActor;

  const dt = event.occurred_at ? new Date(event.occurred_at) : null;
  const timeStr = dt ? dt.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : '—';

  const dotColor = isFirst
    ? 'var(--sol-ink-900)'
    : isSystem
      ? 'var(--sol-calme-fg)'
      : 'var(--sol-ink-400)';

  const handleOpen = () => {
    if (onOpenItem && event.action_item_id) onOpenItem(event.action_item_id);
  };

  return (
    <article
      className="relative grid items-start gap-3 py-2 pl-3.5 text-[12px]"
      style={{ gridTemplateColumns: '52px 1fr' }}
      title={formatDateTimeFR(event.occurred_at)}
    >
      {/* Dot — position absolute aligné avec la ligne verticale du parent. */}
      <span
        aria-hidden="true"
        className="absolute h-[11px] w-[11px] rounded-full border-2"
        style={{
          left: '-5px',
          top: '12px',
          background: isFirst ? dotColor : 'var(--sol-bg-paper)',
          borderColor: dotColor,
        }}
      />

      <span
        className="text-right font-mono text-[11px] font-semibold tracking-[0.02em]"
        style={{ color: 'var(--sol-ink-900)' }}
      >
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
          <span className="font-medium" style={{ fontFamily: 'var(--sol-font-body)' }}>
            {label}
          </span>{' '}
          <span style={{ color: 'var(--sol-ink-500)' }}>·</span>{' '}
          <button
            type="button"
            onClick={handleOpen}
            className="cursor-pointer border-0 bg-transparent p-0 text-left text-[12.5px] font-medium underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--sol-ink-900)]"
            style={{
              color: 'var(--sol-ink-900)',
              fontFamily: 'var(--sol-font-body)',
            }}
          >
            {event.action_item_title}
          </button>
        </div>
      </div>
    </article>
  );
}
