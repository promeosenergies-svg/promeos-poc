import { A11Y_COPY, COPY, SOL_COPY } from '../constants';
import { DomainChip } from './DomainChip';
import { KindCell } from './KindCell';
import { LifecycleBadge } from './LifecycleBadge';
import { PriorityBadge } from './PriorityBadge';

/**
 * M2-5.10.A — Tableau du référentiel (maquette §8.3 pixel-perfect).
 *
 * Colonnes (ordre maquette) : Classement · Item · État · Domaine · Priorité.
 * « Mis à jour » (colonne actuelle) retiré : absent de la maquette ; la date
 * de mise à jour reste consultable dans le drawer détail. Colonnes
 * Responsable / Échéance / Impact / bulk = dette M3+ (BACKLOG_M3).
 *
 * Signature cardinale : strip vertical 3px à gauche de chaque ligne, couleur
 * dérivée du `priority_bracket` (P0 rouge → P3 gris). Pas un badge — un
 * marqueur typographique inspiré du « pull-quote » Sol.
 *
 * Accessibilité clavier (P0-4 audit M2-5, WCAG 2.1.1) : chaque ligne est
 * `tabIndex=0` + `role="button"` + `aria-label` explicite, activable par
 * Entrée ou Espace, avec un anneau de focus visible.
 *
 * Doctrine §13.5 : on ne touche pas le composant `src/ui/Table.jsx` — on
 * stylise localement la `<table>` avec les tokens Sol via inline `style` +
 * Tailwind arbitrary values.
 */

const PRIORITY_STRIP = {
  P0: 'var(--sol-refuse-fg)',
  P1: 'var(--sol-attention-fg)',
  P2: 'var(--sol-calme-fg)',
  P3: 'var(--sol-ink-400)',
};

const ROW_CLASS =
  'transition cursor-pointer relative ' +
  'hover:bg-[color:var(--sol-bg-panel)] ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500';

const TH_CLASS =
  'border-b px-3 py-2.5 text-left font-mono text-[9.5px] font-semibold uppercase tracking-[0.14em] ' +
  'whitespace-nowrap';

const TD_CLASS = 'px-3 py-3 align-middle';

export function ItemsTable({ items, onOpenItem }) {
  return (
    <div
      className="overflow-hidden rounded-lg border"
      style={{
        background: 'var(--sol-bg-paper)',
        borderColor: 'var(--sol-rule)',
      }}
    >
      <table className="w-full border-collapse text-[13px]">
        <thead>
          <tr>
            <th
              className={TH_CLASS}
              style={{
                background: 'var(--sol-bg-panel)',
                borderColor: 'var(--sol-rule)',
                color: 'var(--sol-ink-500)',
              }}
            >
              {SOL_COPY.filterLabelClassement}
            </th>
            <th
              className={TH_CLASS}
              style={{
                background: 'var(--sol-bg-panel)',
                borderColor: 'var(--sol-rule)',
                color: 'var(--sol-ink-500)',
              }}
            >
              {COPY.columnTitle}
            </th>
            <th
              className={TH_CLASS}
              style={{
                background: 'var(--sol-bg-panel)',
                borderColor: 'var(--sol-rule)',
                color: 'var(--sol-ink-500)',
              }}
            >
              {COPY.columnState}
            </th>
            <th
              className={TH_CLASS}
              style={{
                background: 'var(--sol-bg-panel)',
                borderColor: 'var(--sol-rule)',
                color: 'var(--sol-ink-500)',
              }}
            >
              Domaine
            </th>
            <th
              className={`${TH_CLASS} text-center`}
              style={{
                background: 'var(--sol-bg-panel)',
                borderColor: 'var(--sol-rule)',
                color: 'var(--sol-ink-500)',
              }}
            >
              {COPY.columnPriority}
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const open = () => onOpenItem(item);
            const strip = PRIORITY_STRIP[item.priority_bracket] || 'var(--sol-ink-300)';
            return (
              <tr
                key={item.id}
                className={ROW_CLASS}
                onClick={open}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault(); // Espace : évite le scroll de page
                    open();
                  }
                }}
                tabIndex={0}
                role="button"
                aria-label={A11Y_COPY.rowAriaLabel(item.title)}
                data-priority={item.priority_bracket}
                style={{ borderBottom: '1px solid var(--sol-rule)' }}
              >
                {/* Classement — la première td contient le strip vertical 3px
                    en pseudo-élément via inline style (signature maquette). */}
                <td
                  className={TD_CLASS}
                  style={{
                    paddingLeft: 0,
                    position: 'relative',
                    boxShadow: `inset 3px 0 0 0 ${strip}`,
                  }}
                >
                  <KindCell kind={item.kind} />
                </td>
                {/* Item — titre Display Fraunces + meta optionnelle (M3+ pour
                    site/PRM/source). */}
                <td className={TD_CLASS} style={{ minWidth: 320, maxWidth: 480 }}>
                  <div
                    className="text-[14px] font-medium leading-tight tracking-[-0.005em]"
                    style={{
                      fontFamily: 'var(--sol-font-display)',
                      color: 'var(--sol-ink-900)',
                    }}
                  >
                    {item.title}
                  </div>
                </td>
                {/* État — pill lifecycle Sol. */}
                <td className={TD_CLASS}>
                  <LifecycleBadge state={item.lifecycle_state} />
                </td>
                {/* Domaine — chip MONO Sol, ou « — » si absent. */}
                <td className={TD_CLASS}>
                  {item.domain ? (
                    <DomainChip domain={item.domain} />
                  ) : (
                    <span style={{ color: 'var(--sol-ink-400)' }}>—</span>
                  )}
                </td>
                {/* Priorité — tag P0·92 centré. */}
                <td className={`${TD_CLASS} text-center whitespace-nowrap`}>
                  <PriorityBadge bracket={item.priority_bracket} score={item.priority_score} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
