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
import Explain from '../Explain';
import SolSourceChip from './SolSourceChip';

// Mapping sémantique delta → tone.
// - cost / conso : hausse = mauvais (orange), baisse = bon (vert)
// - score        : hausse = bon (vert), baisse = mauvais (orange)
// - neutral      : gris mono, pas de jugement
const SEMANTIC_TONE = {
  cost:    { up: 'bad',  down: 'good' },
  conso:   { up: 'bad',  down: 'good' },
  score:   { up: 'good', down: 'bad'  },
  neutral: { up: 'neutral', down: 'neutral' },
};

function resolveDeltaColor(semantic, direction) {
  const map = SEMANTIC_TONE[semantic] || SEMANTIC_TONE.neutral;
  const tone = map[direction];
  if (tone === 'good') return 'var(--sol-succes-fg)';
  if (tone === 'bad') return 'var(--sol-afaire-fg)';
  return 'var(--sol-ink-500)';
}

export default function SolKpiCard({
  label,
  value,
  unit,
  delta,
  semantic = 'neutral',
  explainKey,
  headline,
  source,
}) {
  const deltaDirection = delta?.direction; // 'up' | 'down' | 'flat'
  const deltaText = delta?.text;
  const deltaColor = resolveDeltaColor(semantic, deltaDirection);

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
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 6,
          fontSize: 10.5,
          color: 'var(--sol-ink-500)',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          marginBottom: 8,
          fontWeight: 500,
        }}
      >
        <span>{label}</span>
        {explainKey && (
          <Explain
            term={explainKey}
            position="bottom"
            className="sol-kpi-explain"
          >
            <span
              aria-label="Voir la d\u00e9finition"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 14,
                height: 14,
                borderRadius: '50%',
                border: '1px solid var(--sol-ink-300)',
                color: 'var(--sol-ink-400)',
                fontFamily: 'var(--sol-font-mono)',
                fontSize: 9,
                fontWeight: 600,
                lineHeight: 1,
                cursor: 'help',
                letterSpacing: 0,
                textTransform: 'none',
                transition: 'color 120ms, border-color 120ms',
              }}
            >
              ?
            </span>
          </Explain>
        )}
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
              color: deltaColor,
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
