import { COPY, KIND_LABELS, LIFECYCLE_LABELS, LIFECYCLE_ORDER, SOL_COPY } from '../constants';

/**
 * M2-5.2 / M2-5.10.A — Filtres du référentiel (maquette §8.3 lignes 740-783).
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
  'cursor-pointer transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500';

function KindChip({ value, label, active, onClick }) {
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
    </button>
  );
}

export function ListFilterBar({
  stateFilter,
  onStateFilterChange,
  kindFilter,
  onKindFilterChange,
  onReset,
}) {
  const isFilterActive = Boolean(stateFilter) || Boolean(kindFilter);

  return (
    <div
      className="mb-3.5 rounded-lg border p-3 px-4"
      style={{
        background: 'var(--sol-bg-paper)',
        borderColor: 'var(--sol-rule)',
      }}
    >
      {/* Row 1 — Classement (kind) : 8 chips. */}
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
          active={!kindFilter}
          onClick={() => onKindFilterChange(null)}
        />
        {KIND_FILTER_ORDER.map((k) => (
          <KindChip
            key={k}
            value={k}
            label={KIND_LABELS[k]}
            active={kindFilter === k}
            onClick={(v) => onKindFilterChange(v)}
          />
        ))}
      </div>

      {/* Row 2 — Priorisation : lifecycle dropdown (chip-style). */}
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
        <label
          className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[12px] font-medium"
          style={{
            background: 'var(--sol-bg-paper)',
            color: 'var(--sol-ink-700)',
            borderColor: 'var(--sol-ink-300)',
          }}
        >
          <span className="sr-only">{COPY.filterByState}</span>
          <span aria-hidden="true">{COPY.filterByState}</span>
          <select
            aria-label={COPY.filterByState}
            value={stateFilter || ''}
            onChange={(e) => onStateFilterChange(e.target.value || null)}
            className="cursor-pointer bg-transparent text-[12px] font-medium outline-none"
            style={{ color: 'var(--sol-ink-900)' }}
          >
            <option value="">{COPY.filterAllStates}</option>
            {LIFECYCLE_ORDER.map((state) => (
              <option key={state} value={state}>
                {LIFECYCLE_LABELS[state]}
              </option>
            ))}
          </select>
        </label>

        {isFilterActive && (
          <button
            type="button"
            onClick={onReset}
            aria-label={SOL_COPY.resetAria}
            className="ml-auto cursor-pointer border-none bg-transparent pb-0.5 font-mono text-[9.5px] font-medium uppercase tracking-[0.08em]"
            style={{
              color: 'var(--sol-ink-500)',
              borderBottom: '1px dotted var(--sol-ink-400)',
            }}
          >
            {SOL_COPY.filterReset} ↻
          </button>
        )}
      </div>

      {isFilterActive && (
        <p className="mt-1.5 px-1 text-[11px]" style={{ color: 'var(--sol-ink-400)' }}>
          {COPY.filterScopeNote}
        </p>
      )}
    </div>
  );
}
