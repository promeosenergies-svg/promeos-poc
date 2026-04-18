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
        border: '1px solid var(--sol-rule)',
        borderRadius: 6,
        padding: '18px 20px 16px',
      }}
    >
      <div
        style={{
          fontSize: 11,
          color: 'var(--sol-ink-500)',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          marginBottom: 10,
          fontWeight: 500,
        }}
      >
        {label}
      </div>

      <div>
        <span
          style={{
            fontFamily: 'var(--sol-font-mono)',
            fontSize: 30,
            fontWeight: 600,
            color: 'var(--sol-ink-900)',
            lineHeight: 1,
            letterSpacing: '-0.02em',
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {value}
        </span>
        {unit && (
          <span
            style={{
              fontFamily: 'var(--sol-font-body)',
              fontSize: 13,
              color: 'var(--sol-ink-400)',
              fontWeight: 400,
              marginLeft: 4,
            }}
          >
            {unit}
          </span>
        )}
      </div>

      {deltaText && (
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            fontSize: 12,
            fontFamily: 'var(--sol-font-mono)',
            marginTop: 8,
            color:
              deltaDirection === 'down' ? 'var(--sol-succes-fg)' : 'var(--sol-afaire-fg)',
          }}
        >
          {deltaText}
        </div>
      )}

      {headline && (
        <div
          style={{
            fontSize: 12.5,
            color: 'var(--sol-ink-700)',
            marginTop: 10,
            lineHeight: 1.45,
            fontWeight: 400,
          }}
        >
          {headline}
        </div>
      )}

      {source && (
        <div style={{ marginTop: 12 }}>
          <SolSourceChip kind={source.kind} ref={source.ref} freshness={source.freshness} />
        </div>
      )}
    </div>
  );
}
