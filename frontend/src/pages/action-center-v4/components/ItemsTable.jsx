import { fmtEurShort } from '../../../utils/format';
import { A11Y_COPY, COPY, PRIORITY_SOL_BG, SOL_COPY } from '../constants';
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

// M2-5.10.A.bis — focus ring sur token Sol (le bleu Tailwind ring-blue-500
// initial cassait la palette journal, anti-pattern doctrine §6.1 — audit
// UI Sol). Strip vertical 3px = PRIORITY_SOL_BG (SoT unique constants.js).
const ROW_CLASS =
  'transition cursor-pointer relative ' +
  'hover:bg-[color:var(--sol-bg-panel)] ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--sol-ink-900)]';

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
              {COPY.columnDomain}
            </th>
            {/* M2-5.11.D — colonne € (à risque 12m) — alignée droite, MONO
                pour scan colonne CFO. La doctrine v0.3 §6.6 prescrit un
                alignement à droite des montants pour lecture vertical. */}
            <th
              className={`${TH_CLASS} text-right`}
              style={{
                background: 'var(--sol-bg-panel)',
                borderColor: 'var(--sol-rule)',
                color: 'var(--sol-ink-500)',
              }}
            >
              {COPY.columnAmount}
            </th>
            {/* M2-5.11.E — colonne Pilote (owner_display_name) avant Priorité. */}
            <th
              className={TH_CLASS}
              style={{
                background: 'var(--sol-bg-panel)',
                borderColor: 'var(--sol-rule)',
                color: 'var(--sol-ink-500)',
              }}
            >
              {COPY.columnOwner}
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
            const strip = PRIORITY_SOL_BG[item.priority_bracket] || 'var(--sol-ink-300)';
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
                    site/PRM/source). M2-5.11.F : abaissé le minWidth de 320 →
                    240 (les 7 colonnes M2-5.11.D/E saturent le viewport < 1400px
                    sinon) + ajout `truncate` + tooltip natif sur dépassement. */}
                <td className={TD_CLASS} style={{ minWidth: 240, maxWidth: 480 }}>
                  <div
                    className="truncate text-[14px] font-medium leading-tight tracking-[-0.005em]"
                    style={{
                      fontFamily: 'var(--sol-font-display)',
                      color: 'var(--sol-ink-900)',
                    }}
                    title={item.title}
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
                {/* M2-5.11.D — montant à risque 12m. `fmtEurShort` rend
                    « 7,5 k€ » / « 1,2 M€ » / « — » si null. Couleur refuse
                    (dérive émotionnelle) car c'est ce qui peut être perdu. */}
                <td
                  className={`${TD_CLASS} text-right whitespace-nowrap`}
                  title={
                    item.impact_at_risk_eur != null ? COPY.amountTooltip : COPY.amountTooltipMissing
                  }
                >
                  <span
                    className="font-mono text-[12.5px] font-medium"
                    style={{
                      color:
                        item.impact_at_risk_eur != null
                          ? 'var(--sol-refuse-fg)'
                          : 'var(--sol-ink-400)',
                    }}
                  >
                    {fmtEurShort(item.impact_at_risk_eur)}
                  </span>
                </td>
                {/* M2-5.11.E — Pilote (snapshot display_name). Si pas
                    assigné : libellé « Non assigné » ink-400 italique. Le
                    bouton Assigner vit dans le drawer (ouvrable via clic
                    sur la ligne) — pas d'action inline pour ne pas
                    encombrer la colonne. */}
                <td className={TD_CLASS}>
                  {item.owner_display_name ? (
                    <span className="text-[12.5px]" style={{ color: 'var(--sol-ink-900)' }}>
                      {item.owner_display_name}
                    </span>
                  ) : (
                    <span
                      className="text-[12px] italic"
                      style={{
                        color: 'var(--sol-ink-400)',
                        fontFamily: 'var(--sol-font-display)',
                      }}
                      title={COPY.ownerUnassignedTooltip}
                    >
                      {COPY.ownerUnassignedLabel}
                    </span>
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
