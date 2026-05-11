/**
 * grammar/hub/charts/ChartFrameLine — Variante chart courbe SVG 2 series + seuil (L11.4).
 *
 * Sprint Grammaire v1.2 / Phase 3.4 / Phase F.2 — extraction de LineCharge24h
 * inline depuis pages/CockpitJour.jsx vers le namespace canonique charts/.
 *
 * Pattern composition : enfant d'un wrapper <ChartFrame>. Ce primitif n'expose
 * QUE le SVG (2 polylines HP/HC + ligne seuil optionnelle + labels axe).
 *
 * 2 series :
 *   - seriesHP : couleur var(--sol-hph-fg) (HP = signal fort)
 *   - seriesHC : couleur var(--sol-hch-fg) (HC = calme)
 *   - threshold : ligne dashed couleur var(--sol-refuse-line) avec label
 *
 * Fallback synthetique : si seriesHP ET seriesHC sont absents, genere un
 * profil 24h HELIOS demo (creux 0h-6h, plateau jour, pic 18h-20h) sur
 * seriesHC seul. Permet de migrer sans dependance backend immediate.
 * Backend pourra fournir les vraies CDC HP/HC dans une evolution future.
 *
 * Source-guards : `data-component="ChartFrameLine"`.
 *
 * @typedef {Object} TimePoint
 * @property {number} hour  - Heure 0-23 (ou index 0-N)
 * @property {number} kw    - Puissance en kW (ou unite homogene threshold)
 *
 * @typedef {Object} Threshold
 * @property {number} value
 * @property {string} [unit='kW']
 * @property {string} [label]   - Libelle affiche au-dessus de la ligne
 *
 * @param {Object} props
 * @param {TimePoint[]} [props.seriesHP]    - Optionnel : courbe HP
 * @param {TimePoint[]} [props.seriesHC]    - Optionnel : courbe HC
 * @param {Threshold} [props.threshold]     - Optionnel : ligne seuil dashed
 * @param {string} [props.ariaLabel='Courbe de charge']
 * @param {string} [props.className='']
 */

const STROKE_HP = 'var(--sol-hph-fg)';
const STROKE_HC = 'var(--sol-hch-fg)';
const STROKE_THRESHOLD = 'var(--sol-refuse-line)';
const FG_THRESHOLD_LABEL = 'var(--sol-refuse-fg)';
const FG_GRID = 'var(--sol-ink-200)';
const FG_AXIS = 'var(--sol-ink-500)';

/** Genere un profil synthetique 24h HELIOS demo (fallback si pas de data backend).
 *  Note : valeurs en kW homogenes avec threshold.value (defaut 1500 kW).
 *
 *  @deprecated when backend.cockpit_jour.charts.series_hp_hc available
 *              See docs/debt/p2_backlog.md#P2-debt-BE-cockpit-jour-charts-series-hp-hc
 */
function generateSyntheticHC() {
  const hours = Array.from({ length: 25 }, (_, i) => i);
  return hours.map((h) => {
    let kw;
    if (h < 6) kw = 60 + Math.sin(h * 0.6) * 10;
    else if (h < 9) kw = 80 + (h - 6) * 8;
    else if (h < 12) kw = 105 + Math.sin(h * 0.4) * 5;
    else if (h < 14) kw = 95 + Math.sin(h * 0.7) * 4;
    else if (h < 18) kw = 100 + Math.cos(h * 0.3) * 6;
    else if (h < 21) kw = 115 + Math.sin((h - 18) * 1.1) * 6;
    else kw = 75 + Math.sin(h * 0.5) * 8;
    return { hour: h, kw };
  });
}

/** Convertit une serie en string points SVG (viewBox 0..100 x 0..60).
 *  thresholdMax : valeur max de l'axe Y (= threshold.value × 4 pour laisser de
 *  la marge visuelle entre la courbe et la ligne seuil au sommet).
 */
function toSvgPoints(series, thresholdMax) {
  if (!Array.isArray(series) || series.length === 0) return '';
  const xMax = series.length - 1;
  return series
    .map((p, i) => {
      const x = (i / xMax) * 100;
      const yRaw = 60 - (p.kw / thresholdMax) * 60 * 4;
      const y = Math.max(2, Math.min(58, yRaw));
      return `${x},${y}`;
    })
    .join(' ');
}

export default function ChartFrameLine({
  seriesHP,
  seriesHC,
  threshold,
  ariaLabel = 'Courbe de charge',
  className = '',
}) {
  const hasHP = Array.isArray(seriesHP) && seriesHP.length > 0;
  const hasHC = Array.isArray(seriesHC) && seriesHC.length > 0;
  // Fallback synthetique : si AUCUNE des deux series, on genere HC pour HELIOS demo.
  const effectiveHC = hasHC ? seriesHC : !hasHP ? generateSyntheticHC() : null;
  const effectiveHP = hasHP ? seriesHP : null;

  // Aucune donnee + aucun fallback (threshold seul) -> render minimal (axes only).
  // Si threshold absent on quitte (rien a afficher).
  const thresholdValue = threshold?.value ?? 1500;
  const thresholdUnit = threshold?.unit ?? 'kW';
  const thresholdLabel = threshold?.label;

  return (
    <svg
      data-component="ChartFrameLine"
      data-has-hp={hasHP || undefined}
      data-has-hc={hasHC || undefined}
      data-has-threshold={threshold != null || undefined}
      role="img"
      aria-label={ariaLabel}
      viewBox="0 0 100 60"
      preserveAspectRatio="none"
      className={className}
      style={{ width: '100%', height: '120px' }}
    >
      {/* Grille horizontale (3 lignes) */}
      <line x1="0" y1="15" x2="100" y2="15" stroke={FG_GRID} strokeWidth="0.2" />
      <line x1="0" y1="30" x2="100" y2="30" stroke={FG_GRID} strokeWidth="0.2" />
      <line x1="0" y1="45" x2="100" y2="45" stroke={FG_GRID} strokeWidth="0.2" />

      {/* Threshold dashed + label */}
      {threshold && (
        <>
          <line
            x1="0"
            y1="3"
            x2="100"
            y2="3"
            stroke={STROKE_THRESHOLD}
            strokeWidth="0.4"
            strokeDasharray="1.5,1.5"
            data-threshold-line
          />
          <text
            x="0"
            y="2"
            fontSize="2.5"
            fill={FG_THRESHOLD_LABEL}
            fontFamily="var(--sol-font-mono)"
          >
            {thresholdLabel ?? `Seuil ${thresholdValue} ${thresholdUnit}`}
          </text>
        </>
      )}

      {/* Series HC (courbe principale ou fallback synthetique) */}
      {effectiveHC && (
        <polyline
          data-series="hc"
          points={toSvgPoints(effectiveHC, thresholdValue)}
          fill="none"
          stroke={STROKE_HC}
          strokeWidth="0.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}

      {/* Series HP (overlay si fourni) */}
      {effectiveHP && (
        <polyline
          data-series="hp"
          points={toSvgPoints(effectiveHP, thresholdValue)}
          fill="none"
          stroke={STROKE_HP}
          strokeWidth="0.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}

      {/* Labels axe X (3 reperes) */}
      <text x="0" y="59" fontSize="2.8" fill={FG_AXIS} fontFamily="var(--sol-font-mono)">
        0h
      </text>
      <text
        x="48"
        y="59"
        fontSize="2.8"
        fill={FG_AXIS}
        fontFamily="var(--sol-font-mono)"
        textAnchor="middle"
      >
        12h
      </text>
      <text
        x="100"
        y="59"
        fontSize="2.8"
        fill={FG_AXIS}
        fontFamily="var(--sol-font-mono)"
        textAnchor="end"
      >
        24h
      </text>
    </svg>
  );
}
