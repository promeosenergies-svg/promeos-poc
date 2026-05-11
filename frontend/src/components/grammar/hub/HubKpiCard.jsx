/**
 * grammar/hub/HubKpiCard — Carte KPI premium L11 Hub Page (doctrine §L11.2).
 *
 * Sprint Grammaire v1.2 / Phase 3.4 / Phase F.1 — extraction de KpiTriptychCard
 * inline depuis pages/CockpitJour.jsx vers le namespace canonique grammar/hub/.
 *
 * Source-guards : `data-component="HubKpiCard"` `data-kpi-id={kpi.id}`
 *                 `data-delta-sentiment={delta.sentiment}`
 *
 * Display-only — zero calcul metier (regle d'or PROMEOS §8.1).
 * Tous les libelles (eyebrow, label, value, unit, delta, footScm,
 * helpTooltip) sont fournis par le backend via `_build_cockpit_jour_kpis`.
 *
 * Doctrine ref : `docs/vision/promeos_sol_doctrine.md` §12 (L11.2) +
 *                `docs/adr/ADR-021-hub-page-grammar-l11.md`.
 *
 * @typedef {Object} HubKpiDelta
 * @property {number} value             - Valeur du delta (peut etre signe)
 * @property {string} [unit]            - Unite (ex. "%", "MWh", "kW")
 * @property {'up'|'down'|'stable'} [direction]
 * @property {string} [label]           - Sous-libelle ("vs T-1", "vs baseline")
 * @property {'positive'|'negative'|'neutral'} [sentiment]
 *
 * @typedef {Object} HubKpi
 * @property {string} id
 * @property {string} [eyebrow]         - Label mono uppercase haut de carte
 * @property {string} [label]           - Libelle principal
 * @property {string|number} [value]
 * @property {string} [unit]
 * @property {HubKpiDelta} [delta]
 * @property {string} [helpTooltip]     - Tooltip d'aide (KPI 3 obligatoire L11.2)
 * @property {string} [footScm]         - Foot SCM (Source · Confiance)
 *
 * @param {Object} props
 * @param {HubKpi} props.kpi
 * @param {string} [props.className='']
 */

const DELTA_FG = Object.freeze({
  positive: 'var(--sol-succes-fg)',
  negative: 'var(--sol-refuse-fg)',
  neutral: 'var(--sol-ink-500)',
});

const DELTA_BG = Object.freeze({
  positive: 'var(--sol-succes-bg)',
  negative: 'var(--sol-refuse-bg)',
  neutral: 'var(--sol-bg-canvas)',
});

export default function HubKpiCard({ kpi, className = '' }) {
  if (!kpi) return null;
  const { id, eyebrow, label, value, unit, delta, footScm, helpTooltip } = kpi;
  const sentiment = delta?.sentiment || 'neutral';
  const deltaColor = DELTA_FG[sentiment] ?? DELTA_FG.neutral;
  const deltaBg = DELTA_BG[sentiment] ?? DELTA_BG.neutral;

  return (
    <div
      data-component="HubKpiCard"
      data-kpi-id={id}
      data-delta-sentiment={sentiment}
      className={`rounded-xl border p-4 flex flex-col ${className}`}
      style={{
        background: 'var(--sol-bg-paper)',
        borderColor: 'var(--sol-rule)',
        minHeight: '128px',
      }}
      title={helpTooltip || undefined}
    >
      {eyebrow && (
        <div
          className="font-mono uppercase"
          style={{
            fontSize: '10px',
            letterSpacing: '0.14em',
            color: 'var(--sol-ink-400)',
            marginBottom: '6px',
          }}
        >
          {eyebrow}
        </div>
      )}
      {label && (
        <div
          style={{
            fontSize: '12.5px',
            color: 'var(--sol-ink-500)',
            marginBottom: '4px',
          }}
        >
          {label}
        </div>
      )}
      <div
        style={{
          display: 'flex',
          alignItems: 'baseline',
          gap: '8px',
          marginBottom: '8px',
        }}
      >
        <span
          className="tabular-nums"
          style={{
            fontFamily: 'var(--sol-font-display)',
            fontSize: '38px',
            fontWeight: 500,
            lineHeight: 1,
            letterSpacing: '-0.018em',
            fontVariantNumeric: 'tabular-nums',
            color: 'var(--sol-ink-900)',
          }}
        >
          {value ?? '—'}
        </span>
        {unit && (
          <span
            style={{
              fontSize: '13px',
              color: 'var(--sol-ink-500)',
              fontWeight: 500,
            }}
          >
            {unit}
          </span>
        )}
        {delta && delta.value != null && (
          <span
            className="font-mono"
            style={{
              marginLeft: 'auto',
              fontSize: '11px',
              padding: '3px 8px',
              borderRadius: '6px',
              background: deltaBg,
              color: deltaColor,
              whiteSpace: 'nowrap',
            }}
          >
            {delta.value > 0 ? '+' : ''}
            {delta.value}
            {delta.unit || ''}
          </span>
        )}
      </div>
      {delta?.label && (
        <div
          style={{
            fontSize: '11px',
            color: 'var(--sol-ink-500)',
            marginBottom: '6px',
          }}
        >
          {delta.label}
        </div>
      )}
      {footScm && (
        <div
          className="font-mono"
          style={{
            marginTop: 'auto',
            fontSize: '10px',
            color: 'var(--sol-ink-400)',
            paddingTop: '6px',
            borderTop: '1px solid var(--sol-rule)',
          }}
        >
          {footScm}
        </div>
      )}
    </div>
  );
}
