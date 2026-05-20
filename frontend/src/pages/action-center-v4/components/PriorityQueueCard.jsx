import { fmtEurShort } from '../../../utils/format';
import { A11Y_COPY, COPY, PRIORITY_SOL_BG } from '../constants';
import { DomainChip } from './DomainChip';
import { KindCell } from './KindCell';
import { LifecycleBadge } from './LifecycleBadge';
import { PriorityBadge } from './PriorityBadge';

/**
 * M2-5.10.D / .bis clôture — Card d'un item dans la file prioritaire Pilotage
 * (maquette §8.1 lignes 878-1180 — `item-card`).
 *
 * Bloc papier + strip vertical 3px couleur priorité + status row Sol
 * (KindCell + PriorityBadge avec score + LifecycleBadge + DomainChip) +
 * titre Display Fraunces. Clic → ouvre le drawer détail via `onOpenItem`.
 *
 * Réutilise les chips Sol restylés M2-5.10.A/B (SoT unique constants.js).
 * Pas de SLA pair, owner avatar, flags récurrence — backend manquant
 * (BACKLOG_M3). La maquette les prévoit mais sans data ils sont mensongers.
 *
 * M2-5.10.bis clôture (audit CS P1-3) : si l'item est `closed`, la card est
 * visuellement opacifiée (60 %) pour signaler que toute action est en
 * lecture seule — cohérent avec `ItemClosedBanner` posé à l'intérieur du
 * drawer détail. Évite que des items closed apparaissent comme actifs
 * dans la file prioritaire (transition asynchrone, refresh courte fenêtre).
 */
export function PriorityQueueCard({ item, onOpenItem }) {
  const strip = PRIORITY_SOL_BG[item.priority_bracket] || 'var(--sol-ink-300)';
  const open = () => onOpenItem(item);
  const isClosed = item.lifecycle_state === 'closed';

  return (
    <article
      className={
        // M2-5.11.F : `min-h-[110px]` harmonise les hauteurs entre les
        // cards avec / sans description / impact_at_risk_eur / pilote.
        // Sans ça, la file alterne entre 60px et 100px → rythme cassé
        // (audit polish M2-5.11.F).
        'relative min-h-[110px] cursor-pointer rounded-[8px] border transition ' +
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--sol-ink-900)]' +
        (isClosed ? ' opacity-60' : '')
      }
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
        {/* M2-5.11.D — montant à risque 12m posé sous le titre (maquette
            pilotage_decisions_v031.html ligne 917 `item-card-impact-value`).
            Affiché uniquement quand un montant existe — pas de tiret bruit
            quand l'impact n'est pas encore calculé (cohérent §6.6 doctrine
            « pas de chiffre menteur »). */}
        {/* M2-5.11.G : passé sur `--sol-ink-700` (au lieu de refuse-fg) —
            le strip vertical 3px porte déjà la signature « dérive » P0/P1,
            cumuler refuse-fg sur le montant créait une saturation rouge
            (audit visuel post-M2-5.11). */}
        {item.impact_at_risk_eur != null && (
          <div
            className="mt-1 font-mono text-[12.5px] font-medium"
            style={{ color: 'var(--sol-ink-700)' }}
            title={COPY.amountTooltip}
          >
            {fmtEurShort(item.impact_at_risk_eur)}
          </div>
        )}
        {/* M2-5.11.E / .G — pilote sous le titre (à côté du €). Si non assigné,
            on rend explicitement « Non assigné » italique — c'est une dette
            opérationnelle, pas un silence. M2-5.11.G : ink-400 (3.45:1) →
            ink-500 (5.2:1) WCAG AA. */}
        <div
          className="mt-1 text-[12px]"
          style={{
            color: item.owner_display_name ? 'var(--sol-ink-700)' : 'var(--sol-ink-500)',
            fontStyle: item.owner_display_name ? 'normal' : 'italic',
            fontFamily: item.owner_display_name
              ? 'var(--sol-font-body)'
              : 'var(--sol-font-display)',
          }}
          title={item.owner_display_name ? undefined : COPY.ownerUnassignedTooltip}
        >
          {item.owner_display_name || COPY.ownerUnassignedLabel}
        </div>
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
