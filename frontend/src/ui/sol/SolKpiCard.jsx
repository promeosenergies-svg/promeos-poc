/**
 * PROMEOS — SolKpiCard
 *
 * KPI card signature Sol : label uppercase mono + value JetBrains Mono
 * 30px tabular-nums + unit DM Sans petit + delta pill colored + headline
 * humain + source chip en bas.
 *
 * Source maquette : .kpi / .kpi-label / .kpi-value / .kpi-unit / .kpi-delta
 *                 / .kpi-headline / .source-chip
 */
import SolSourceChip from './SolSourceChip';

export default function SolKpiCard({
  label,
  value,
  unit,
  delta,
  headline,
  source,
}) {
  const deltaDirection = delta?.direction; // 'up' | 'down'
  const deltaText = delta?.text;

  return (
    <div
      style={{
        background: 'var(--sol-bg-paper)',
        border: '1px solid var(--sol-ink-200)',
        borderRadius: 6,
        padding: '14px 16px 12px',
      }}
    >
      <div
        style={{
          fontSize: 10.5,
          color: 'var(--sol-ink-500)',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          marginBottom: 8,
          fontWeight: 500,
        }}
      >
        {label}
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', flexWrap: 'wrap', gap: 4 }}>
        <span
          style={{
            fontFamily: 'var(--sol-font-mono)',
            fontSize: 24,
            fontWeight: 600,
            color: 'var(--sol-ink-900)',
            lineHeight: 1,
            letterSpacing: '-0.025em',
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {value}
        </span>
        {unit && (
          <span
            style={{
              fontFamily: 'var(--sol-font-body)',
              fontSize: 12,
              color: 'var(--sol-ink-400)',
              fontWeight: 400,
              marginLeft: 3,
            }}
          >
            {unit}
          </span>
        )}
        {deltaText && (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 2,
              marginLeft: 4,
              fontSize: 11,
              fontFamily: 'var(--sol-font-mono)',
              fontWeight: 500,
              fontVariantNumeric: 'tabular-nums',
              color:
                deltaDirection === 'down' ? 'var(--sol-succes-fg)' : 'var(--sol-afaire-fg)',
            }}
          >
            {deltaText}
          </span>
        )}
      </div>

      {headline && (
        <div
          style={{
            fontSize: 11.5,
            color: 'var(--sol-ink-700)',
            marginTop: 8,
            lineHeight: 1.45,
            fontWeight: 400,
          }}
        >
          {headline}
        </div>
      )}

      {source && (
        <div style={{ marginTop: 10 }}>
          <SolSourceChip
            kind={source.kind}
            origin={source.origin ?? source.ref}
            freshness={source.freshness}
          />
        </div>
      )}
    </div>
  );
}
