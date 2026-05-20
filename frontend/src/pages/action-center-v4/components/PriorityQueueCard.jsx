import { A11Y_COPY, PRIORITY_SOL_BG } from '../constants';
import { DomainChip } from './DomainChip';
import { KindCell } from './KindCell';
import { LifecycleBadge } from './LifecycleBadge';
import { PriorityBadge } from './PriorityBadge';

/**
 * M2-5.10.D — Card d'un item dans la file prioritaire Pilotage (maquette §8.1
 * lignes 878-1180 — `item-card`).
 *
 * Bloc papier + strip vertical 3px couleur priorité + status row Sol
 * (KindCell + PriorityBadge avec score + LifecycleBadge + DomainChip) +
 * titre Display Fraunces. Clic → ouvre le drawer détail via `onOpenItem`.
 *
 * Réutilise les chips Sol restylés M2-5.10.A/B (SoT unique constants.js).
 * Pas de SLA pair, owner avatar, flags récurrence — backend manquant
 * (BACKLOG_M3). La maquette les prévoit mais sans data ils sont mensongers.
 */
export function PriorityQueueCard({ item, onOpenItem }) {
  const strip = PRIORITY_SOL_BG[item.priority_bracket] || 'var(--sol-ink-300)';
  const open = () => onOpenItem(item);

  return (
    <article
      className="relative cursor-pointer rounded-[8px] border transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--sol-ink-900)]"
      style={{
        background: 'var(--sol-bg-paper)',
        borderColor: 'var(--sol-rule)',
        boxShadow: `inset 3px 0 0 0 ${strip}`,
      }}
      tabIndex={0}
      role="button"
      aria-label={A11Y_COPY.rowAriaLabel(item.title)}
      onClick={open}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          open();
        }
      }}
      data-priority={item.priority_bracket}
    >
      <div className="flex flex-wrap items-center gap-1.5 px-4 pt-3">
        <KindCell kind={item.kind} />
        <PriorityBadge bracket={item.priority_bracket} score={item.priority_score} />
        <LifecycleBadge state={item.lifecycle_state} />
        {item.domain && <DomainChip domain={item.domain} />}
      </div>

      <div className="px-4 pb-3 pt-2">
        <h3
          className="text-[15px] font-medium leading-[1.3] tracking-[-0.005em]"
          style={{
            fontFamily: 'var(--sol-font-display)',
            color: 'var(--sol-ink-900)',
          }}
        >
          {item.title}
        </h3>
        {item.description && (
          <p
            className="mt-1 text-[12.5px] leading-[1.4]"
            style={{
              fontFamily: 'var(--sol-font-body)',
              color: 'var(--sol-ink-500)',
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
            }}
          >
            {item.description}
          </p>
        )}
      </div>
    </article>
  );
}
