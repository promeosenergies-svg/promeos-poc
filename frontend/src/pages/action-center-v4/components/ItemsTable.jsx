import { formatEurosColumn } from '../../../utils/money';
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

// M2-5.11.G — style commun aux 7 `<th>` (audit code-reviewer P2 : 21 lignes
// `style={{...}}` dupliquées remplacées par 1 spread). Le `text-right` /
// `text-center` reste sur le `className` (alignement par colonne).
const TH_STYLE = {
  background: 'var(--sol-bg-panel)',
  borderColor: 'var(--sol-rule)',
  color: 'var(--sol-ink-500)',
};

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
            <th className={TH_CLASS} style={TH_STYLE}>
              {SOL_COPY.filterLabelClassement}
            </th>
            <th className={TH_CLASS} style={TH_STYLE}>
              {COPY.columnTitle}
            </th>
            {/* M2-5.11.K responsive — Domaine + État masqués < md (768px) :
                le titre + strip 3px + KindCell + Priorité suffisent en
                mobile pour scanner et ouvrir un item. Détails complets via
                le drawer (qui se posera en plein écran sur mobile en M3+). */}
            <th className={`hidden md:table-cell ${TH_CLASS}`} style={TH_STYLE}>
              {COPY.columnState}
            </th>
            <th className={`hidden lg:table-cell ${TH_CLASS}`} style={TH_STYLE}>
              {COPY.columnDomain}
            </th>
            {/* M2-5.11.D / .K — colonne € (à risque 12m) — alignée droite,
                MONO pour scan colonne CFO. Masquée < lg (1024px) pour ne
                pas saturer le scan tactile mobile. */}
            <th className={`hidden lg:table-cell ${TH_CLASS} text-right`} style={TH_STYLE}>
              {COPY.columnAmount}
            </th>
            {/* M2-5.11.E / .K — colonne Pilote masquée < lg, accessible
                dans le drawer (Assigner) sur les vues petites. */}
            <th className={`hidden lg:table-cell ${TH_CLASS}`} style={TH_STYLE}>
              {COPY.columnOwner}
            </th>
            <th className={`${TH_CLASS} text-center`} style={TH_STYLE}>
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
                {/* État — pill lifecycle Sol. Masqué < md (mobile). */}
                <td className={`hidden md:table-cell ${TD_CLASS}`}>
                  <LifecycleBadge state={item.lifecycle_state} />
                </td>
                {/* Domaine — chip MONO Sol, ou « — » si absent. Masqué < lg. */}
                <td className={`hidden lg:table-cell ${TD_CLASS}`}>
                  {item.domain ? (
                    <DomainChip domain={item.domain} />
                  ) : (
                    <span style={{ color: 'var(--sol-ink-500)' }}>—</span>
                  )}
                </td>
                {/* M2-6.B.frontend — colonne « Impact estimé » (Q16). Source
                    backend: `estimated_impact_euros` scalaire (vs ancien
                    `impact_at_risk_eur` dérivé `impact_payload.at_risk` qui
                    devient drill-down drawer ImpactSection M3+).
                    `formatEurosColumn` bascule auto < 10k → full (« 3 200 € »)
                    vs ≥ 10k → compact (« 35 k€ »). NULL → « — » (tiret
                    cadratin). Couleur ink-700 si valeur, ink-500 si NULL
                    (WCAG AA 5.2:1). Aligné droite + tabular-nums pour scan
                    colonne CFO. */}
                <td
                  className={`hidden lg:table-cell ${TD_CLASS} text-right whitespace-nowrap`}
                  title={
                    item.estimated_impact_euros != null
                      ? COPY.amountTooltip
                      : COPY.amountTooltipMissing
                  }
                >
                  <span
                    className="font-mono text-[12.5px] font-medium"
                    style={{
                      color:
                        item.estimated_impact_euros != null
                          ? 'var(--sol-ink-700)'
                          : 'var(--sol-ink-500)',
                    }}
                  >
                    {formatEurosColumn(item.estimated_impact_euros)}
                  </span>
                </td>
                {/* M2-5.11.E / .G — Pilote (snapshot display_name). Si pas
                    assigné : libellé « Non assigné » italique. Le bouton
                    Assigner vit dans le drawer (ouvrable via clic sur la
                    ligne) — pas d'action inline pour ne pas encombrer.
                    M2-5.11.G : ink-400 (3.45:1) → ink-500 (5.2:1) WCAG AA. */}
                <td className={`hidden lg:table-cell ${TD_CLASS}`}>
                  {item.owner_display_name ? (
                    <span className="text-[12.5px]" style={{ color: 'var(--sol-ink-900)' }}>
                      {item.owner_display_name}
                    </span>
                  ) : (
                    <span
                      className="text-[12px] italic"
                      style={{
                        color: 'var(--sol-ink-500)',
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
