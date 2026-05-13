/**
 * grammar/hub/charts/ChartFrameOpportunityMap — Scatter ROI × effort (Phase 3.6 CC).
 *
 * Synthèse Stratégique mode OPPORTUNITY_DRIVEN.
 * Affiche un scatter plot des opportunités : axe X = effort (1-10),
 * axe Y = ROI k€/an. Couleur par tier (warn/neutral/pos).
 *
 * Props :
 *   question, answer  — texte (ReactNode + string)
 *   data              — list[{ name, roi_keur_an, effort_score, tier }]
 *   footScm           — string footer SCM
 *
 * Display-only.
 */

const VIEWBOX_W = 520;
const VIEWBOX_H = 220;
const PLOT_LEFT = 60;
const PLOT_RIGHT = 470;
const PLOT_TOP = 25;
const PLOT_BOTTOM = 175;

export default function ChartFrameOpportunityMap({ question, answer, data = [], footScm }) {
  const items = Array.isArray(data) ? data : [];
  if (items.length === 0) return null;

  const maxRoi = Math.max(...items.map((d) => d.roi_keur_an || 0), 10) * 1.15;
  const xFor = (effort) => PLOT_LEFT + ((effort - 1) / 9) * (PLOT_RIGHT - PLOT_LEFT);
  const yFor = (roi) => PLOT_BOTTOM - (roi / maxRoi) * (PLOT_BOTTOM - PLOT_TOP);

  const tierColor = (tier) =>
    tier === 'pos'
      ? 'var(--sol-succes, #3F7C5A)'
      : tier === 'warn'
        ? 'var(--sol-afaire, #B8612E)'
        : 'var(--sol-ink-500, #7A6E5C)';

  return (
    <article
      data-component="ChartFrameOpportunityMap"
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
        <p style={{ fontSize: '13px', color: 'var(--sol-ink-700, #3D362C)', margin: '0 0 14px' }}>
          {answer}
        </p>
      )}
      <svg viewBox={`0 0 ${VIEWBOX_W} ${VIEWBOX_H}`} role="img" aria-label="Opportunity map">
        {/* Axes */}
        <line
          x1={PLOT_LEFT}
          y1={PLOT_TOP}
          x2={PLOT_LEFT}
          y2={PLOT_BOTTOM}
          stroke="var(--sol-ink-300, #CFC4B2)"
        />
        <line
          x1={PLOT_LEFT}
          y1={PLOT_BOTTOM}
          x2={PLOT_RIGHT}
          y2={PLOT_BOTTOM}
          stroke="var(--sol-ink-300, #CFC4B2)"
        />
        {/* Labels axes */}
        <text
          x={PLOT_LEFT - 10}
          y={PLOT_TOP - 8}
          fontSize="10"
          fontFamily="var(--sol-font-mono, monospace)"
          fill="var(--sol-ink-500, #7A6E5C)"
          textAnchor="start"
        >
          ROI k€/an ↑
        </text>
        <text
          x={PLOT_RIGHT}
          y={PLOT_BOTTOM + 18}
          fontSize="10"
          fontFamily="var(--sol-font-mono, monospace)"
          fill="var(--sol-ink-500, #7A6E5C)"
          textAnchor="end"
        >
          Effort →
        </text>
        {/* Points + labels */}
        {items.map((d, idx) => {
          const cx = xFor(d.effort_score ?? 5);
          const cy = yFor(d.roi_keur_an ?? 0);
          return (
            <g key={idx}>
              <circle cx={cx} cy={cy} r="10" fill={tierColor(d.tier)} opacity="0.85" />
              <text
                x={cx + 14}
                y={cy + 4}
                fontSize="11"
                fontFamily="var(--sol-font-display, serif)"
                fill="var(--sol-ink-900, #1A1612)"
              >
                {d.name}
              </text>
              <text
                x={cx + 14}
                y={cy + 18}
                fontSize="10"
                fontFamily="var(--sol-font-mono, monospace)"
                fill="var(--sol-ink-500, #7A6E5C)"
              >
                {d.roi_keur_an} k€/an
              </text>
            </g>
          );
        })}
      </svg>
      {footScm && (
        <p
          style={{
            fontFamily: 'var(--sol-font-mono, monospace)',
            fontSize: '10.5px',
            color: 'var(--sol-ink-500, #7A6E5C)',
            margin: '8px 0 0',
          }}
        >
          {footScm}
        </p>
      )}
    </article>
  );
}
