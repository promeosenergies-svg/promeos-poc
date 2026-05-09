/**
 * grammar/KPISol — Wrapper grammaire KPI avec contrat KpiResult backend.
 *
 * Delegue vers KpiCard (variant 'confidence') en exposant le contrat
 * KpiResult issu de `backend/services/kpi_service.py` (champ pour champ).
 *
 * Rendu :
 *   - value en font numerique tabular-nums (via KpiCard Fraunces)
 *   - label mono uppercase
 *   - bouton ? (aria-label: "Details {label}") avec tooltip metadata riche
 *     (source, formula, periode, confiance, calcule)
 *   - badge statut mini : real→mesure, calculated→calcule, modeled→modelise,
 *     estimated→estime, demo→demo
 *
 * Display-only — zero calcul metier.
 *
 * @param {Object} props
 * @param {Object} props.descriptor - Structure KpiResult backend
 * @param {string} props.descriptor.kpi_id - Identifiant KPI canonique
 * @param {string} props.descriptor.label - Label affiche
 * @param {number|string} props.descriptor.value - Valeur principale
 * @param {string} [props.descriptor.unit] - Unite (MWh, /100, k€...)
 * @param {string} [props.descriptor.source] - Source des donnees
 * @param {string} [props.descriptor.formula_ref] - Reference formule
 * @param {string} [props.descriptor.period] - Periodicite (mensuel, annuel...)
 * @param {'real'|'calculated'|'modeled'|'estimated'|'demo'} [props.descriptor.status='calculated']
 * @param {string} [props.descriptor.computed_at] - ISO datetime de calcul
 * @param {'high'|'medium'|'low'} [props.descriptor.confidence='high']
 * @param {'hero'|'inline'|'compact'} [props.variant='hero'] - Variante visuelle
 * @param {string} [props.className=''] - Classes CSS supplementaires
 */
import { useState, useId } from 'react';
import { HelpCircle } from 'lucide-react';

const STATUS_LABELS = Object.freeze({
  real: 'mesure',
  calculated: 'calcule',
  modeled: 'modelise',
  estimated: 'estime',
  demo: 'demo',
});

const STATUS_TONE = Object.freeze({
  real: { bg: 'var(--sol-succes-bg)', fg: 'var(--sol-succes-fg)' },
  calculated: { bg: 'var(--sol-calme-bg)', fg: 'var(--sol-calme-fg)' },
  modeled: { bg: 'var(--sol-attention-bg)', fg: 'var(--sol-attention-fg)' },
  estimated: { bg: 'var(--sol-attention-bg)', fg: 'var(--sol-attention-fg)' },
  demo: { bg: 'var(--sol-ink-100)', fg: 'var(--sol-ink-700)' },
});

const CONFIDENCE_LABELS = Object.freeze({
  high: 'haute',
  medium: 'moyenne',
  low: 'faible',
});

function formatComputedAt(iso) {
  if (!iso) return null;
  try {
    return new Intl.DateTimeFormat('fr-FR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

const VALUE_SIZE = Object.freeze({
  hero: { fontSize: 32 },
  inline: { fontSize: 24 },
  compact: { fontSize: 18 },
});

export default function KPISol({ descriptor = {}, variant = 'hero', className = '' }) {
  const [tooltipOpen, setTooltipOpen] = useState(false);
  const tooltipId = useId();

  const {
    label = '',
    value,
    unit,
    source,
    formula_ref,
    period,
    status = 'calculated',
    computed_at,
    confidence = 'high',
  } = descriptor;

  const statusLabel = STATUS_LABELS[status] ?? status;
  const statusTone = STATUS_TONE[status] ?? STATUS_TONE.calculated;
  const valueFontSize = VALUE_SIZE[variant]?.fontSize ?? 32;

  const tooltipContent = [
    source ? `Source : ${source}` : null,
    formula_ref ? `Formule : ${formula_ref}` : null,
    period ? `Periode : ${period}` : null,
    confidence ? `Confiance : ${CONFIDENCE_LABELS[confidence] ?? confidence}` : null,
    computed_at ? `Calcule : ${formatComputedAt(computed_at)}` : null,
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <div
      data-testid="kpi-sol"
      data-kpi-id={descriptor.kpi_id}
      className={`rounded-lg p-4 ${className}`}
      style={{ background: 'var(--sol-bg-canvas)' }}
    >
      {/* Label + bouton ? */}
      <div className="flex items-center justify-between gap-2 mb-2">
        <span
          className="font-mono uppercase tracking-[0.07em] text-[11px]"
          style={{ color: 'var(--sol-ink-500)' }}
        >
          {label}
        </span>
        {tooltipContent && (
          <span style={{ position: 'relative', display: 'inline-block' }}>
            <button
              type="button"
              aria-label={`Details ${label}`}
              aria-describedby={tooltipOpen ? tooltipId : undefined}
              onClick={() => setTooltipOpen((v) => !v)}
              onBlur={() => setTooltipOpen(false)}
              className="flex items-center justify-center rounded-full text-[var(--sol-ink-400)] hover:text-[var(--sol-ink-700)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--sol-calme-fg)]"
              style={{ width: 18, height: 18 }}
            >
              <HelpCircle size={13} aria-hidden="true" />
            </button>
            {tooltipOpen && (
              <span
                id={tooltipId}
                role="tooltip"
                style={{
                  position: 'absolute',
                  zIndex: 50,
                  bottom: 'calc(100% + 6px)',
                  right: 0,
                  maxWidth: 300,
                  minWidth: 180,
                  padding: '8px 10px',
                  background: 'var(--sol-bg-paper)',
                  color: 'var(--sol-ink-900)',
                  border: '0.5px solid var(--sol-ink-300)',
                  borderRadius: 6,
                  fontSize: 11,
                  lineHeight: 1.5,
                  fontFamily: 'var(--sol-font-body)',
                  boxShadow: '0 6px 16px rgba(15, 23, 42, 0.10)',
                  whiteSpace: 'normal',
                }}
              >
                {tooltipContent}
              </span>
            )}
          </span>
        )}
      </div>

      {/* Valeur numerique tabular-nums */}
      <div className="flex items-baseline gap-2 flex-wrap mb-2">
        <span
          className="tabular-nums"
          style={{
            fontFamily: 'var(--sol-font-display)',
            fontSize: valueFontSize,
            fontWeight: 500,
            lineHeight: 1,
            color: 'var(--sol-ink-900)',
          }}
        >
          {value}
        </span>
        {unit && (
          <span className="text-sm font-medium" style={{ color: 'var(--sol-ink-700)' }}>
            {unit}
          </span>
        )}
      </div>

      {/* Badge statut mini */}
      <span
        data-testid="kpi-sol-status-badge"
        className="inline-flex items-center px-1.5 py-0.5 rounded font-mono uppercase tracking-[0.06em]"
        style={{
          fontSize: 9.5,
          background: statusTone.bg,
          color: statusTone.fg,
          fontWeight: 500,
        }}
      >
        {statusLabel}
      </span>
    </div>
  );
}
