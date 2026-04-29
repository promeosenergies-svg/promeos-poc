/**
 * KpiSkeleton — Placeholder Sol shimmer pendant fetch (Étape 11 · 29/04/2026).
 *
 * Factorise les 2 implémentations inlinées (CockpitPilotage + CockpitDecision).
 * Audit /simplify P1 : doublon verbatim entre les 2 pages.
 *
 * Props :
 *   - variant: 'temporal' (Pilotage 28px) | 'confidence' (Décision 32px)
 *   - scaleLabel: string optionnel — kicker COURT/MOYEN/CONTRACTUEL Pilotage
 */

const VALUE_HEIGHT_BY_VARIANT = {
  temporal: 28,
  confidence: 32,
};

export default function KpiSkeleton({ variant = 'temporal', scaleLabel }) {
  const isTemporal = variant === 'temporal';
  const valueHeight = VALUE_HEIGHT_BY_VARIANT[variant] || 28;

  return (
    <div
      className={`${isTemporal ? 'rounded-lg' : 'rounded-md'} p-4 animate-pulse`}
      style={{ background: 'var(--sol-bg-canvas)' }}
    >
      {isTemporal && scaleLabel && (
        <div
          className="font-mono uppercase tracking-[0.08em] mb-2"
          style={{ fontSize: '9.5px', color: 'var(--sol-ink-400)', letterSpacing: '0.1em' }}
        >
          {scaleLabel}
        </div>
      )}
      <div
        className="rounded mb-2"
        style={{ height: 11, width: '60%', background: 'var(--sol-ink-200)' }}
      />
      <div
        className="rounded"
        style={{ height: valueHeight, width: '50%', background: 'var(--sol-ink-200)' }}
      />
      <div
        className="rounded mt-2"
        style={{ height: 14, width: '70%', background: 'var(--sol-ink-200)', opacity: 0.7 }}
      />
    </div>
  );
}
