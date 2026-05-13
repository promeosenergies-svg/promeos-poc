/**
 * grammar/hub/charts/ChartFrameForwardCurve — Courbe forward Y+1 (Phase 3.6 CC).
 *
 * Synthèse Stratégique mode PROCUREMENT_DRIVEN.
 * Affiche la dynamique prix forward J→M+12 avec niveau spot actuel en
 * référence (orange dashed) et ligne forward (succes solide).
 *
 * Props :
 *   question, answer  — texte (ReactNode + string)
 *   data              — { forward: [{month, price}, ...], spot_now: number }
 *   footScm           — string footer SCM
 *
 * Display-only.
 */

const VIEWBOX_W = 520;
const VIEWBOX_H = 200;
const PLOT_LEFT = 50;
const PLOT_RIGHT = 500;
const PLOT_TOP = 25;
const PLOT_BOTTOM = 160;

export default function ChartFrameForwardCurve({ question, answer, data = {}, footScm }) {
  const forward = Array.isArray(data.forward) ? data.forward : [];
  const spotNow = data.spot_now ?? 0;
  if (forward.length === 0) return null;

  const prices = [...forward.map((p) => p.price), spotNow];
  const yMax = Math.max(...prices) * 1.15;
  const yMin = Math.min(...prices) * 0.85;
  const yFor = (p) => PLOT_BOTTOM - ((p - yMin) / (yMax - yMin)) * (PLOT_BOTTOM - PLOT_TOP);
  const xFor = (i) => PLOT_LEFT + (i / (forward.length - 1 || 1)) * (PLOT_RIGHT - PLOT_LEFT);

  const linePath = forward
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xFor(i)} ${yFor(p.price)}`)
    .join(' ');

  return (
    <article
      data-component="ChartFrameForwardCurve"
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
      <svg viewBox={`0 0 ${VIEWBOX_W} ${VIEWBOX_H}`} role="img" aria-label="Forward curve">
        {/* Spot actuel ligne dashed orange */}
        <line
          x1={PLOT_LEFT}
          y1={yFor(spotNow)}
          x2={PLOT_RIGHT}
          y2={yFor(spotNow)}
          stroke="var(--sol-afaire, #B8612E)"
          strokeWidth="1.5"
          strokeDasharray="6 4"
        />
        <text
          x={PLOT_RIGHT - 6}
          y={yFor(spotNow) - 6}
          fontSize="10"
          fontFamily="var(--sol-font-mono, monospace)"
          fill="var(--sol-afaire, #B8612E)"
          textAnchor="end"
        >
          Spot {spotNow} €/MWh
        </text>
        {/* Forward path */}
        <path d={linePath} stroke="var(--sol-succes, #3F7C5A)" strokeWidth="2.5" fill="none" />
        {/* Dots */}
        {forward.map((p, i) => (
          <g key={i}>
            <circle cx={xFor(i)} cy={yFor(p.price)} r="4" fill="var(--sol-succes, #3F7C5A)" />
            <text
              x={xFor(i)}
              y={PLOT_BOTTOM + 18}
              fontSize="10"
              fontFamily="var(--sol-font-mono, monospace)"
              fill="var(--sol-ink-500, #7A6E5C)"
              textAnchor="middle"
            >
              {p.month}
            </text>
            <text
              x={xFor(i)}
              y={yFor(p.price) - 8}
              fontSize="11"
              fontFamily="var(--sol-font-mono, monospace)"
              fill="var(--sol-succes, #3F7C5A)"
              textAnchor="middle"
              fontWeight="600"
            >
              {p.price}
            </text>
          </g>
        ))}
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
