/**
 * grammar/hub/charts/ChartFrameBenchSites — Bench sites vs médiane NAF.
 *
 * Synthèse Stratégique mode PERFORMANCE_DRIVEN (Phase 3.5 Vague D.3).
 * Affiche un set de barres horizontales par site avec :
 *  - longueur proportionnelle à l'intensité kWh/m²
 *  - tick médiane NAF en référence (gris)
 *  - couleur par tier (warn/neutral/pos)
 *  - label valeur + delta_pct à droite
 *
 * Props :
 *   question        — ReactNode (titre Fraunces)
 *   answer          — ReactNode (sous-titre)
 *   data            — list[{ site, value, ref, delta_pct, tier }]
 *   footScm         — string footer SCM
 *
 * Display-only.
 */

export default function ChartFrameBenchSites({ question, answer, data = [], footScm }) {
  const maxVal = Math.max(...data.map((d) => d.value), ...data.map((d) => d.ref || 0), 1);
  const medianePct = (ref) => Math.min((ref / maxVal) * 100, 100);

  return (
    <article
      data-component="ChartFrameBenchSites"
      className="sol-chart-frame rounded-md border p-5"
      style={{
        background: 'var(--sol-bg-card, #FFFFFF)',
        borderColor: 'var(--sol-ink-200, #E5DDD0)',
      }}
    >
      <h3
        style={{
          fontFamily: 'var(--sol-font-display, serif)',
          fontSize: '16px',
          color: 'var(--sol-ink-900, #1A1612)',
          margin: '0 0 4px',
        }}
      >
        {question}
      </h3>
      {answer && (
        <p
          style={{
            fontSize: '13px',
            color: 'var(--sol-ink-700, #3D362C)',
            margin: '0 0 14px',
          }}
        >
          {answer}
        </p>
      )}
      <div className="flex flex-col gap-3" style={{ marginTop: '8px' }}>
        {data.map((row, idx) => {
          const widthPct = Math.min((row.value / maxVal) * 100, 100);
          const medianX = medianePct(row.ref);
          const colorVar =
            row.tier === 'warn'
              ? 'var(--sol-afaire, #B8612E)'
              : row.tier === 'pos'
                ? 'var(--sol-succes, #3F7C5A)'
                : 'var(--sol-ink-500, #7A6E5C)';
          return (
            <div
              key={`${row.site}-${idx}`}
              className="grid items-center gap-3"
              style={{ gridTemplateColumns: '130px 1fr 110px' }}
            >
              <span
                style={{
                  fontFamily: 'var(--sol-font-display, serif)',
                  fontSize: '14px',
                  color: 'var(--sol-ink-900, #1A1612)',
                }}
              >
                {row.site}
              </span>
              <div
                style={{
                  height: '22px',
                  background: 'var(--sol-ink-100, #F2EDE5)',
                  borderRadius: '11px',
                  position: 'relative',
                  overflow: 'visible',
                }}
              >
                <div
                  style={{
                    height: '100%',
                    width: `${widthPct}%`,
                    background: colorVar,
                    borderRadius: '11px',
                  }}
                />
                {row.ref && (
                  <div
                    style={{
                      position: 'absolute',
                      left: `${medianX}%`,
                      top: '-4px',
                      bottom: '-4px',
                      width: '2px',
                      background: 'var(--sol-ink-500, #7A6E5C)',
                    }}
                    aria-label="Médiane NAF"
                  />
                )}
              </div>
              <span
                style={{
                  fontFamily: 'var(--sol-font-mono, monospace)',
                  fontSize: '12px',
                  textAlign: 'right',
                  color: 'var(--sol-ink-700, #3D362C)',
                  lineHeight: 1.2,
                }}
              >
                {row.value} kWh/m²
                <br />
                <span style={{ fontSize: '10.5px', color: 'var(--sol-ink-500, #7A6E5C)' }}>
                  {row.delta_pct >= 0 ? `+${row.delta_pct}` : row.delta_pct}%
                </span>
              </span>
            </div>
          );
        })}
      </div>
      {footScm && (
        <p
          className="mt-2"
          style={{
            fontFamily: 'var(--sol-font-mono, monospace)',
            fontSize: '10.5px',
            color: 'var(--sol-ink-500, #7A6E5C)',
            margin: '12px 0 0',
          }}
        >
          {footScm}
        </p>
      )}
    </article>
  );
}
