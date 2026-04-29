/**
 * SolTrajectoryDT — SVG trajectoire Décret Tertiaire 2030 (réel + cible + projection).
 *
 * Phase 1.5 du sprint refonte cockpit dual sol2 (29/04/2026). Composant
 * pur display SVG pour la page Synthèse stratégique. Trace 3 séries :
 *   - Cible DT (rouge dashed) — trajectoire réglementaire continue
 *   - Réel (bleu plein) — historique mesuré jusqu'à l'année en cours
 *   - Projection (vert plein) — extrapolation actions planifiées au-delà
 *
 * Cible maquette : `docs/maquettes/cockpit-sol2/cockpit-synthese-strategique.html`
 * lignes 255-292 (SVG inline natif, pas de Recharts — Performance + cohérence).
 *
 * Endpoint backend cible : `/api/cockpit/trajectory` (existe déjà — contrat
 * `routes/cockpit.py:393` retourne {annees, reel_mwh, objectif_mwh,
 * projection_mwh, ref_year, jalons}). Doctrine §8.1 : zero business logic
 * frontend, ce composant ne fait QUE le rendu.
 *
 * Anti-patterns évités (doctrine §6.3) :
 *   - Pas de Recharts (lourd + cohérence maquettes SVG natif)
 *   - Pas de hex hardcodé hors var() — tokens Sol obligatoires
 *   - aria-label complet pour lecteurs d'écran (a11y WCAG 2.2 §13)
 *   - Empty state propre si données insuffisantes (anti-pattern §6.1
 *     « empty state pleine largeur »)
 *
 * Props :
 *   - annees : int[] — années couvertes (≥ 2 pour rendu)
 *   - reelMwh : (number|null)[] — conso réelle par année (null = pas de mesure)
 *   - objectifMwh : number[] — trajectoire cible DT par année
 *   - projectionMwh : (number|null)[] — projection actions par année (null = passé)
 *   - todayYear : number — année en cours (marker vertical, défaut année courante)
 *   - yMin : number — borne basse axe Y (défaut 2000)
 *   - yMax : number — borne haute axe Y (défaut 5000)
 *   - ariaLabel : string|null — override aria-label (sinon généré)
 *   - className : string
 */

const X_MIN = 64;
const X_MAX = 780;
const Y_MIN = 20;
const Y_MAX = 220;

function fmtMwh(v) {
  return Math.round(v)
    .toLocaleString('fr-FR')
    .replace(/\u202f/g, ' ');
}

export default function SolTrajectoryDT({
  annees = [],
  reelMwh = [],
  objectifMwh = [],
  projectionMwh = [],
  todayYear = new Date().getFullYear(),
  yMin = 2000,
  yMax = 5000,
  ariaLabel = null,
  className = '',
}) {
  // Doctrine §6.1 : pas d'empty state pleine largeur — return null si données
  // insuffisantes. Le caller décide si la section reste visible ou non.
  if (!Array.isArray(annees) || annees.length < 2) return null;

  const xStep = (X_MAX - X_MIN) / (annees.length - 1);
  const xFor = (i) => X_MIN + i * xStep;
  const yScale = (mwh) => {
    if (mwh == null) return null;
    const t = (mwh - yMin) / (yMax - yMin);
    return Y_MAX - t * (Y_MAX - Y_MIN);
  };

  const buildPath = (series) => {
    if (!Array.isArray(series) || series.length === 0) return null;
    const pts = series
      .map((v, i) => ({ x: xFor(i), y: yScale(v) }))
      .filter((p) => p.y != null && Number.isFinite(p.y));
    if (pts.length < 2) return null;
    return 'M ' + pts.map((p) => `${p.x} ${p.y}`).join(' L ');
  };

  const objectifPath = buildPath(objectifMwh);
  const reelPath = buildPath(reelMwh);
  const projectionPath = buildPath(projectionMwh);

  const todayIdx = annees.indexOf(todayYear);
  const todayX = todayIdx >= 0 ? xFor(todayIdx) : null;

  // 4 ticks Y équirépartis (top, 2/3, 1/3, bottom)
  const range = yMax - yMin;
  const yTicks = [yMax, yMax - range / 3, yMin + range / 3, yMin];

  const generatedAriaLabel =
    ariaLabel ||
    `Trajectoire Décret Tertiaire de ${annees[0]} à ${annees[annees.length - 1]}, ` +
      `réel jusqu'en ${todayYear} puis projection actions planifiées vers la cible -40 % en 2030.`;

  return (
    <div data-testid="sol-trajectory-dt" className={className}>
      <svg
        viewBox="0 0 800 240"
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: '100%', height: 'auto', display: 'block', marginTop: 6 }}
        role="img"
        aria-label={generatedAriaLabel}
      >
        {/* Grille horizontale */}
        {yTicks.map((v, i) => (
          <line
            key={`grid-${i}`}
            x1={X_MIN}
            y1={yScale(v)}
            x2={X_MAX}
            y2={yScale(v)}
            stroke="currentColor"
            strokeOpacity={i === yTicks.length - 1 ? 0.15 : 0.08}
            strokeDasharray="2,3"
          />
        ))}
        {/* Labels axe Y */}
        {yTicks.map((v, i) => (
          <text
            key={`ylabel-${i}`}
            x={X_MIN - 6}
            y={yScale(v) + 3}
            textAnchor="end"
            fontFamily="var(--font-mono)"
            fontSize="10"
            fill="currentColor"
            fillOpacity="0.5"
          >
            {fmtMwh(v)}
          </text>
        ))}
        {/* Cible DT — rouge dashed */}
        {objectifPath && (
          <path
            data-testid="sol-trajectory-objectif-path"
            d={objectifPath}
            fill="none"
            stroke="var(--sol-refuse-fg, #A32D2D)"
            strokeWidth="1.4"
            strokeDasharray="4,4"
          />
        )}
        {/* Réel — bleu plein */}
        {reelPath && (
          <path
            data-testid="sol-trajectory-reel-path"
            d={reelPath}
            fill="none"
            stroke="var(--sol-info-fg, #378ADD)"
            strokeWidth="2"
          />
        )}
        {reelMwh.map((v, i) => {
          if (v == null) return null;
          const cy = yScale(v);
          if (cy == null) return null;
          return (
            <circle
              key={`reel-pt-${i}`}
              cx={xFor(i)}
              cy={cy}
              r={i === todayIdx ? 4 : 3}
              fill="var(--sol-info-fg, #378ADD)"
            />
          );
        })}
        {/* Projection — vert plein */}
        {projectionPath && (
          <path
            data-testid="sol-trajectory-projection-path"
            d={projectionPath}
            fill="none"
            stroke="var(--sol-succes-fg, #1D9E75)"
            strokeWidth="2"
          />
        )}
        {projectionMwh.map((v, i) => {
          if (v == null) return null;
          const cy = yScale(v);
          if (cy == null) return null;
          return (
            <circle
              key={`proj-pt-${i}`}
              cx={xFor(i)}
              cy={cy}
              r="3"
              fill="var(--sol-succes-fg, #1D9E75)"
            />
          );
        })}
        {/* Marker vertical "aujourd'hui" */}
        {todayX != null && (
          <>
            <line
              x1={todayX}
              y1={Y_MIN}
              x2={todayX}
              y2={Y_MAX}
              stroke="currentColor"
              strokeOpacity="0.25"
              strokeDasharray="2,3"
            />
            <text
              x={todayX}
              y={Y_MIN - 6}
              textAnchor="middle"
              fontFamily="var(--font-mono)"
              fontSize="10"
              fill="currentColor"
              fillOpacity="0.55"
            >
              aujourd&apos;hui
            </text>
          </>
        )}
        {/* Labels axe X — années paires uniquement (lisibilité) */}
        <g
          fontFamily="var(--font-mono)"
          fontSize="10"
          fill="currentColor"
          fillOpacity="0.55"
          textAnchor="middle"
        >
          {annees.map((year, i) => {
            if (year % 2 !== 0) return null;
            return (
              <text key={`xl-${year}`} x={xFor(i)} y={Y_MAX + 12}>
                {year}
              </text>
            );
          })}
        </g>
      </svg>
    </div>
  );
}
