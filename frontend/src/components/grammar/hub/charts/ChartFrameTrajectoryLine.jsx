/**
 * grammar/hub/charts/ChartFrameTrajectoryLine — Trajectoire DT 2030/2040/2050.
 *
 * Synthèse Stratégique mode REGULATORY_DRIVEN (Phase 3.5 Vague D.3).
 * Affiche :
 *  - ligne actuelle (atteint %) en orange/refuse
 *  - 3 cibles décret (2030 -40 %, 2040 -50 %, 2050 -60 %) en succes/dashed
 *  - écart drift labellisé
 *
 * Props :
 *   question        — ReactNode (titre Fraunces)
 *   answer          — ReactNode (sous-titre court)
 *   data            — { atteint_pct, cible_2030_pct, cible_2040_pct, cible_2050_pct }
 *   footScm         — string footer Source/Confiance/MAJ
 *
 * Display-only — zero calcul (les données viennent du builder backend).
 */

const VIEWBOX_W = 520;
const VIEWBOX_H = 220;
const PLOT_LEFT = 50;
const PLOT_RIGHT = 500;
const PLOT_TOP = 30;
const PLOT_BOTTOM = 180;

export default function ChartFrameTrajectoryLine({ question, answer, data = {}, footScm }) {
  // Phase 3.8 OO — garde-fou audit qa-guardian P3.7 :
  // si le constructeur backend n'envoie pas atteint_pct ni cible_2030_pct
  // (cas Décret Tertiaire non applicable), on rend une indication explicite
  // plutôt qu'un graphique trompeur avec valeur par défaut.
  const hasData = data && data.cible_2030_pct !== undefined && data.cible_2030_pct !== null;
  if (!hasData) {
    return (
      <article
        data-component="ChartFrameTrajectoryLine"
        data-state="not-applicable"
        className="sol-chart-frame rounded-md border p-5"
        style={{
          background: 'var(--sol-bg-card, #FFFFFF)',
          borderColor: 'var(--sol-ink-200, #E5DDD0)',
        }}
      >
        {question && (
          <h3
            style={{
              fontFamily: 'var(--sol-font-display, serif)',
              fontSize: '16px',
              color: 'var(--sol-ink-900, #1A1612)',
              margin: '0 0 8px',
            }}
          >
            {question}
          </h3>
        )}
        <p
          style={{
            fontSize: '13px',
            color: 'var(--sol-ink-500, #7A6E5C)',
            fontStyle: 'italic',
            margin: 0,
          }}
        >
          Décret tertiaire non applicable sur le périmètre — aucune trajectoire à représenter.
        </p>
      </article>
    );
  }

  const atteint = data.atteint_pct ?? 0;
  const cible2030 = data.cible_2030_pct;
  const cible2040 = data.cible_2040_pct ?? 50;
  const cible2050 = data.cible_2050_pct ?? 60;
  const drift = cible2030 - atteint;

  // Axe Y : 0% au top, 70% au bottom (laisser place au-dessus pour annotations)
  const yMax = 70;
  const yFor = (pct) => PLOT_TOP + ((yMax - pct) / yMax) * (PLOT_BOTTOM - PLOT_TOP);

  // Axe X jalon : 2026 (gauche), 2030, 2040, 2050 (droite)
  const xFor = (year) => {
    const ratio = (year - 2026) / (2050 - 2026);
    return PLOT_LEFT + ratio * (PLOT_RIGHT - PLOT_LEFT);
  };

  return (
    <article
      data-component="ChartFrameTrajectoryLine"
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
      <svg viewBox={`0 0 ${VIEWBOX_W} ${VIEWBOX_H}`} role="img" aria-label="Trajectoire DT">
        {/* Axe Y graduations */}
        {[0, 20, 40, 60].map((pct) => (
          <g key={pct}>
            <line
              x1={PLOT_LEFT}
              y1={yFor(pct)}
              x2={PLOT_RIGHT}
              y2={yFor(pct)}
              stroke="var(--sol-ink-200, #E5DDD0)"
              strokeDasharray="2 4"
            />
            <text
              x={PLOT_LEFT - 8}
              y={yFor(pct) + 4}
              fontSize="10"
              fontFamily="var(--sol-font-mono, monospace)"
              fill="var(--sol-ink-500, #7A6E5C)"
              textAnchor="end"
            >
              −{pct}%
            </text>
          </g>
        ))}
        {/* Axe X labels années */}
        {[2026, 2030, 2040, 2050].map((year) => (
          <text
            key={year}
            x={xFor(year)}
            y={PLOT_BOTTOM + 18}
            fontSize="10"
            fontFamily="var(--sol-font-mono, monospace)"
            fill="var(--sol-ink-500, #7A6E5C)"
            textAnchor="middle"
          >
            {year}
          </text>
        ))}
        {/* Cibles décret (dashed succes) */}
        <line
          x1={xFor(2026)}
          y1={yFor(0)}
          x2={xFor(2030)}
          y2={yFor(cible2030)}
          stroke="var(--sol-succes, #3F7C5A)"
          strokeWidth="2"
          strokeDasharray="6 4"
        />
        <line
          x1={xFor(2030)}
          y1={yFor(cible2030)}
          x2={xFor(2040)}
          y2={yFor(cible2040)}
          stroke="var(--sol-succes, #3F7C5A)"
          strokeWidth="2"
          strokeDasharray="6 4"
        />
        <line
          x1={xFor(2040)}
          y1={yFor(cible2040)}
          x2={xFor(2050)}
          y2={yFor(cible2050)}
          stroke="var(--sol-succes, #3F7C5A)"
          strokeWidth="2"
          strokeDasharray="6 4"
        />
        {/* Trajectoire actuelle (orange refuse) */}
        <line
          x1={xFor(2026)}
          y1={yFor(0)}
          x2={xFor(2030)}
          y2={yFor(atteint)}
          stroke="var(--sol-afaire, #B8612E)"
          strokeWidth="3"
        />
        {/* Dots cibles */}
        <circle cx={xFor(2030)} cy={yFor(cible2030)} r="4" fill="var(--sol-succes, #3F7C5A)" />
        <circle cx={xFor(2040)} cy={yFor(cible2040)} r="4" fill="var(--sol-succes, #3F7C5A)" />
        <circle cx={xFor(2050)} cy={yFor(cible2050)} r="4" fill="var(--sol-succes, #3F7C5A)" />
        {/* Dot actuel */}
        <circle cx={xFor(2030)} cy={yFor(atteint)} r="5" fill="var(--sol-afaire, #B8612E)" />
        <text
          x={xFor(2030) + 10}
          y={yFor(atteint) - 6}
          fontSize="11"
          fontFamily="var(--sol-font-mono, monospace)"
          fill="var(--sol-afaire, #B8612E)"
          fontWeight="600"
        >
          Atteint −{atteint}% (dérive {drift} pts)
        </text>
        <text
          x={xFor(2030) + 10}
          y={yFor(cible2030) - 6}
          fontSize="11"
          fontFamily="var(--sol-font-mono, monospace)"
          fill="var(--sol-succes, #3F7C5A)"
        >
          Cible décret −{cible2030}%
        </text>
      </svg>
      {footScm && (
        <p
          className="mt-2"
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
