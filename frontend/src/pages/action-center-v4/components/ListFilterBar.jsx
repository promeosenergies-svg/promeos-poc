import { RotateCcw } from 'lucide-react';

import { COPY, KIND_LABELS, LIFECYCLE_LABELS, LIFECYCLE_ORDER, SOL_COPY } from '../constants';

/**
 * M2-5.2 / M2-5.10.A / .bis — Filtres du référentiel (maquette §8.3 lignes 740-783).
 *
 * Doctrine cardinale : `kind` (Row 1 « Classement ») et `priority/lifecycle/
 * domain/...` (Row 2 « Priorisation ») sont **séparés visuellement** — c'est
 * la traduction littérale de l'axe orthogonal kind ≠ priority de la doctrine
 * v0.3 §3.
 *
 * MV3 limité : Row 1 = filtre kind (7 valeurs + Tous) · Row 2 = lifecycle
 * dropdown. Les 6 autres filtres maquette (Priorité, Domaine, Site,
 * Responsable, Blocker, Source, Confiance) = dette M3+ (besoin endpoints
 * serveur — cf. BACKLOG_M3). Filtres client-side sur page courante (note
 * `filterScopeNote` portée par la page).
 *
 * Hotfix M2-5.10.A.bis :
 * - `chip-count` MONO sur chaque chip kind (maquette ligne 745-752) → audit UI
 * - `<select>` natif → custom Sol (chevron SVG, appearance:none) → audit UI/CS
 * - bouton « Réinitialiser » promu chip 12px avec icône RotateCcw, accent
 *   attention si filtre actif (audit CS — invisibilité sub-WCAG)
 * - focus ring `--sol-ink-900` au lieu de blue-500 Tailwind (audit UI Sol)
 */

// 7 kinds (ordre maquette) + entrée « Tous » en tête.
const KIND_FILTER_ORDER = [
  'anomaly',
  'action',
  'decision',
  'signal',
  'evidence_request',
  'deadline',
  'recommendation',
];

const CHIP_BASE =
  'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-sans text-[12px] font-medium ' +
  'cursor-pointer transition focus-visible:outline-none focus-visible:ring-2 ' +
  'focus-visible:ring-[color:var(--sol-ink-900)]';

function KindChip({ value, label, count, active, onClick }) {
  const style = active
    ? {
        background: 'var(--sol-ink-900)',
        color: 'var(--sol-bg-paper)',
        borderColor: 'var(--sol-ink-900)',
      }
    : {
        background: 'var(--sol-bg-paper)',
        color: 'var(--sol-ink-700)',
        borderColor: 'var(--sol-ink-300)',
      };
  return (
    <button
      type="button"
      onClick={() => onClick(value)}
      className={`${CHIP_BASE} border`}
      style={style}
      aria-pressed={active}
      aria-label={SOL_COPY.kindChipAria(label)}
    >
      {label}
      {typeof count === 'number' && (
        <span
          className="font-mono text-[10px] font-normal"
          style={{
            color: active ? 'var(--sol-ink-200)' : 'var(--sol-ink-500)',
            marginLeft: '2px',
          }}
        >
          {count}
        </span>
      )}
    </button>
  );
}

/**
 * Dropdown custom Sol pour lifecycle (audit UI Sol P1-2 + CS P0-1).
 *
 * Conserve un `<select>` natif pour l'a11y et la simplicité (clavier,
 * lecteur d'écran, mobile) mais le rend invisible (`appearance: none` +
 * fond/padding/font/border alignés sur les chips). On ajoute un chevron SVG
 * en absolute à droite pour la signature visuelle maquette.
 */
function StateChipDropdown({ value, onChange }) {
  return (
    <span
      className="relative inline-flex items-center"
      style={{
        background: 'var(--sol-bg-paper)',
        color: 'var(--sol-ink-700)',
        border: '1px solid var(--sol-ink-300)',
        borderRadius: '9999px',
        paddingLeft: '10px',
        paddingRight: '26px', // place pour le chevron
      }}
    >
      <span
        className="pr-1.5 font-sans text-[12px] font-medium"
        style={{ color: 'var(--sol-ink-700)' }}
      >
        {COPY.filterByState}
      </span>
      <select
        aria-label={COPY.filterByState}
        value={value || ''}
        onChange={(e) => onChange(e.target.value || null)}
        className={
          'cursor-pointer appearance-none border-none bg-transparent py-1 ' +
          'font-sans text-[12px] font-medium outline-none ' +
          'focus-visible:outline-none focus-visible:ring-2 ' +
          'focus-visible:ring-[color:var(--sol-ink-900)] rounded-full'
        }
        style={{ color: 'var(--sol-ink-900)' }}
      >
        <option value="">{COPY.filterAllStates}</option>
        {LIFECYCLE_ORDER.map((state) => (
          <option key={state} value={state}>
            {LIFECYCLE_LABELS[state]}
          </option>
        ))}
      </select>
      <svg
        className="pointer-events-none absolute right-2 h-2.5 w-2.5"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        aria-hidden="true"
        style={{ color: 'var(--sol-ink-500)' }}
      >
        <polyline points="6 9 12 15 18 9" />
      </svg>
    </span>
  );
}

export function ListFilterBar({
  stateFilter,
  onStateFilterChange,
  kindFilter,
  onKindFilterChange,
  kindCounts = {},
  onReset,
}) {
  const isFilterActive = Boolean(stateFilter) || Boolean(kindFilter);
  // Total page courante = somme des counts par kind (utilisé sur le chip
  // « Tous les types »).
  const totalPage = Object.values(kindCounts).reduce((s, n) => s + n, 0);

  return (
    <div
      className="mb-3.5 rounded-lg border p-3 px-4"
      style={{
        background: 'var(--sol-bg-paper)',
        borderColor: 'var(--sol-rule)',
      }}
    >
      {/* Row 1 — Classement (kind) : 8 chips avec compteur MONO maquette
          ligne 745-752. Le compteur est limité à la page courante (cohérent
          avec filterScopeNote). */}
      <div className="flex flex-wrap items-center gap-2">
        <span
          className="mr-2 inline-block min-w-[78px] font-mono text-[9px] font-semibold uppercase tracking-[0.14em]"
          style={{ color: 'var(--sol-ink-500)' }}
        >
          {SOL_COPY.filterLabelClassement}
        </span>
        <KindChip
          value={null}
          label={SOL_COPY.filterAllKinds}
          count={totalPage > 0 ? totalPage : undefined}
          active={!kindFilter}
          onClick={() => onKindFilterChange(null)}
        />
        {KIND_FILTER_ORDER.map((k) => (
          <KindChip
            key={k}
            value={k}
            label={KIND_LABELS[k]}
            count={kindCounts[k]}
            active={kindFilter === k}
            onClick={(v) => onKindFilterChange(v)}
          />
        ))}
      </div>

      {/* Row 2 — Priorisation : lifecycle dropdown Sol + reset chip. */}
      <div
        className="mt-2 flex flex-wrap items-center gap-2 border-t pt-2.5"
        style={{ borderTopStyle: 'dashed', borderTopColor: 'var(--sol-rule)' }}
      >
        <span
          className="mr-2 inline-block min-w-[78px] font-mono text-[9px] font-semibold uppercase tracking-[0.14em]"
          style={{ color: 'var(--sol-ink-500)' }}
        >
          {SOL_COPY.filterLabelPriorisation}
        </span>

        <StateChipDropdown value={stateFilter} onChange={onStateFilterChange} />

        {isFilterActive && (
          <button
            type="button"
            onClick={onReset}
            aria-label={SOL_COPY.resetAria}
            className={
              'ml-auto inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 ' +
              'font-sans text-[12px] font-medium cursor-pointer transition ' +
              'focus-visible:outline-none focus-visible:ring-2 ' +
              'focus-visible:ring-[color:var(--sol-ink-900)]'
            }
            // Accent attention dès qu'au moins un filtre est actif (signal
            // « il y a quelque chose à reset » — audit CS P1-1 invisibilité
            // sub-WCAG 9.5px corrigée à 12px).
            style={{
              background: 'var(--sol-attention-bg)',
              color: 'var(--sol-attention-fg)',
              borderColor: 'var(--sol-attention-line)',
            }}
          >
            <RotateCcw size={12} aria-hidden="true" />
            {SOL_COPY.filterReset}
          </button>
        )}
      </div>

      {isFilterActive && (
        <p className="mt-1.5 px-1 text-[11px]" style={{ color: 'var(--sol-ink-500)' }}>
          {COPY.filterScopeNote}
        </p>
      )}
    </div>
  );
}
