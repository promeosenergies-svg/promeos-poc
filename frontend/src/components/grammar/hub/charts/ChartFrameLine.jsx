/**
 * grammar/hub/charts/ChartFrameLine — Variante chart courbe 24h HP/HC + seuil (L11.4).
 *
 * Sprint Grammaire v1.2 / Phase 3.4 / Phase F.8 polish maquette V2 :
 *   - viewBox 320×130 (vs 100×60 F.2) — respire correctement sur 1440px
 *   - Axe Y avec 3 graduations en kW (rendu mono gris)
 *   - Zones HC (heures creuses) en fond bleu très clair
 *   - Courbe HP (jour) en orange avec gradient fill subtil
 *   - Courbe HC (nuit + soir) en bleu (lignes seules, pas de fill)
 *   - Threshold (puissance souscrite) en rouge dashed avec label
 *   - Pic annoté avec circle + label texte ("528 kW")
 *
 * Coordonnées source-of-truth :
 *   - hour ∈ [0, 23] (entier ou semi-horaire) → x ∈ [PLOT_LEFT, PLOT_RIGHT]
 *   - kw → y inversé : 0 = PLOT_BOTTOM, yMax = PLOT_TOP
 *   - yMax calculé automatiquement comme `max(peak.kw, threshold.value) × 1.25`
 *
 * Display-only — zero calcul metier (PROMEOS §8.1).
 *
 * @typedef {Object} TimePoint
 * @property {number} hour  - Heure 0-23
 * @property {number} kw    - Puissance en kW
 *
 * @typedef {Object} Threshold
 * @property {number} value
 * @property {string} [unit='kW']
 * @property {string} [label]
 *
 * @typedef {Object} Peak
 * @property {number} hour    - Heure du pic
 * @property {number} kw      - Valeur kW au pic
 * @property {string} [label] - Texte annotation (eg "528 kW")
 *
 * @typedef {Object} HcZone
 * @property {number} from_h
 * @property {number} to_h
 *
 * @param {Object} props
 * @param {TimePoint[]} [props.seriesHP]
 * @param {TimePoint[]} [props.seriesHC]
 * @param {Threshold} [props.threshold]
 * @param {Peak} [props.peak]
 * @param {HcZone[]} [props.hcZones]
 * @param {string} [props.ariaLabel='Courbe de charge']
 * @param {string} [props.className='']
 */

const STROKE_HP = 'var(--sol-attention-fg)'; // orange HP
const STROKE_HC = 'var(--sol-hch-fg)'; // bleu HC
const STROKE_THRESHOLD = 'var(--sol-refuse-line)';
const FG_THRESHOLD_LABEL = 'var(--sol-refuse-fg)';
const FG_AXIS = 'var(--sol-ink-400)';
const FG_PEAK_LABEL = 'var(--sol-attention-fg)';
const FILL_HC_ZONE = 'var(--sol-hch-bg)';
const FILL_HP_GRADIENT_ID = 'chartFrameLine-hp-gradient';

// Geometrie maquette V2 (viewBox 0 0 320 130).
const PLOT_LEFT = 32;
const PLOT_RIGHT = 320;
const PLOT_TOP = 18;
const PLOT_BOTTOM = 105;
const Y_LABEL_X = 28;
const X_LABEL_Y = 120;
const HOURS_RANGE = 24; // 0h → 23h (24 points horaires)

function hourToX(hour) {
  return PLOT_LEFT + (hour / (HOURS_RANGE - 1)) * (PLOT_RIGHT - PLOT_LEFT);
}

function kwToY(kw, yMax) {
  if (yMax <= 0) return PLOT_BOTTOM;
  const clamped = Math.max(0, Math.min(yMax, kw));
  return PLOT_BOTTOM - (clamped / yMax) * (PLOT_BOTTOM - PLOT_TOP);
}

/** Convertit une série en string `points` SVG polyline. */
function seriesToPoints(series, yMax) {
  if (!Array.isArray(series) || series.length === 0) return '';
  return series.map((p) => `${hourToX(p.hour)},${kwToY(p.kw, yMax)}`).join(' ');
}

/** Calcule 3 graduations Y arrondies pour un yMax donné (eg yMax=600 → [200, 400, 600]). */
function yTicks(yMax) {
  if (yMax <= 0) return [];
  const rounded = Math.ceil(yMax / 100) * 100;
  return [rounded / 3, (2 * rounded) / 3, rounded].map((v) => Math.round(v / 50) * 50);
}

export default function ChartFrameLine({
  seriesHP,
  seriesHC,
  threshold,
  peak,
  hcZones,
  ariaLabel = 'Courbe de charge',
  className = '',
}) {
  const hasHP = Array.isArray(seriesHP) && seriesHP.length > 0;
  const hasHC = Array.isArray(seriesHC) && seriesHC.length > 0;
  const thresholdValue = threshold?.value;
  const thresholdUnit = threshold?.unit ?? 'kW';
  const thresholdLabel = threshold?.label;

  // yMax = max entre peak.kw, threshold/3 (pour donner de l'air vs souscrite si
  // très haute), et la max des séries. Multiplié par 1.25 pour padding visuel.
  const seriesMaxHP = hasHP ? Math.max(...seriesHP.map((p) => p.kw)) : 0;
  const seriesMaxHC = hasHC ? Math.max(...seriesHC.map((p) => p.kw)) : 0;
  const peakKw = peak?.kw ?? 0;
  const rawMax = Math.max(seriesMaxHP, seriesMaxHC, peakKw, (thresholdValue ?? 0) / 3);
  const yMax = rawMax > 0 ? Math.ceil((rawMax * 1.25) / 100) * 100 : 0;
  const ticks = yTicks(yMax);

  // HC zones : rendre les bandes verticales en fond avant tout le reste.
  const renderHcZones = (hcZones || []).map((z, i) => {
    const x1 = hourToX(z.from_h);
    const x2 = hourToX(Math.min(z.to_h + 1, HOURS_RANGE - 1));
    return (
      <rect
        key={`hc-zone-${i}`}
        x={x1}
        y={PLOT_TOP}
        width={x2 - x1}
        height={PLOT_BOTTOM - PLOT_TOP}
        fill={FILL_HC_ZONE}
        fillOpacity="0.4"
        data-hc-zone-index={i}
      />
    );
  });

  return (
    <svg
      data-component="ChartFrameLine"
      data-has-hp={hasHP || undefined}
      data-has-hc={hasHC || undefined}
      data-has-threshold={threshold != null || undefined}
      data-has-peak={peak != null || undefined}
      role="img"
      aria-label={ariaLabel}
      viewBox="0 0 320 130"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={{ width: '100%', height: 'auto', display: 'block' }}
    >
      <defs>
        <linearGradient id={FILL_HP_GRADIENT_ID} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="var(--sol-attention-fg)" stopOpacity="0.22" />
          <stop offset="100%" stopColor="var(--sol-attention-fg)" stopOpacity="0" />
        </linearGradient>
      </defs>

      {/* Zones HC en fond */}
      {renderHcZones}

      {/* Axe Y — 3 graduations + grid lines dashed */}
      {ticks.map((t, i) => {
        const y = kwToY(t, yMax);
        return (
          <g key={`y-tick-${i}`} data-y-tick={t}>
            <line
              x1={PLOT_LEFT}
              y1={y}
              x2={PLOT_RIGHT}
              y2={y}
              stroke="var(--sol-ink-300)"
              strokeOpacity="0.4"
              strokeDasharray="2,3"
            />
            <text
              x={Y_LABEL_X}
              y={y + 3}
              textAnchor="end"
              fontFamily="var(--sol-font-mono)"
              fontSize="9"
              fill={FG_AXIS}
            >
              {t}
            </text>
          </g>
        );
      })}

      {/* Threshold (puissance souscrite) — ligne dashed rouge + label */}
      {threshold && yMax > 0 && (
        <g data-threshold-value={thresholdValue}>
          <line
            x1={PLOT_LEFT}
            y1={kwToY(thresholdValue, yMax)}
            x2={PLOT_RIGHT}
            y2={kwToY(thresholdValue, yMax)}
            stroke={STROKE_THRESHOLD}
            strokeOpacity="0.65"
            strokeDasharray="3,3"
            strokeWidth="1"
            data-threshold-line
          />
          <text
            x={PLOT_RIGHT - 2}
            y={kwToY(thresholdValue, yMax) - 4}
            textAnchor="end"
            fontFamily="var(--sol-font-mono)"
            fontSize="9"
            fill={FG_THRESHOLD_LABEL}
            fillOpacity="0.85"
          >
            {thresholdLabel ?? `P. souscrite ${thresholdValue} ${thresholdUnit}`}
          </text>
        </g>
      )}

      {/* HP fill gradient (uniquement sous la courbe HP) */}
      {hasHP && yMax > 0 && (
        <polygon
          data-series="hp-fill"
          points={`${seriesToPoints(seriesHP, yMax)} ${hourToX(seriesHP[seriesHP.length - 1].hour)},${PLOT_BOTTOM} ${hourToX(seriesHP[0].hour)},${PLOT_BOTTOM}`}
          fill={`url(#${FILL_HP_GRADIENT_ID})`}
        />
      )}

      {/* Courbe HC (heures creuses, bleue) */}
      {hasHC && yMax > 0 && (
        <polyline
          data-series="hc"
          points={seriesToPoints(seriesHC, yMax)}
          fill="none"
          stroke={STROKE_HC}
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}

      {/* Courbe HP (heures pleines, orange) */}
      {hasHP && yMax > 0 && (
        <polyline
          data-series="hp"
          points={seriesToPoints(seriesHP, yMax)}
          fill="none"
          stroke={STROKE_HP}
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}

      {/* Pic annoté (circle + label texte) */}
      {peak && yMax > 0 && (
        <g data-peak={`${peak.hour}h-${peak.kw}kw`}>
          <circle cx={hourToX(peak.hour)} cy={kwToY(peak.kw, yMax)} r="2.8" fill={STROKE_HP} />
          <text
            x={hourToX(peak.hour)}
            y={kwToY(peak.kw, yMax) - 8}
            textAnchor="middle"
            fontFamily="var(--sol-font-body)"
            fontSize="10"
            fontWeight="500"
            fill={FG_PEAK_LABEL}
          >
            {peak.label ?? `${peak.kw} kW`}
          </text>
        </g>
      )}

      {/* Labels axe X — 5 repères horaires */}
      <g fontFamily="var(--sol-font-mono)" fontSize="9" fill={FG_AXIS}>
        <text x={hourToX(0)} y={X_LABEL_Y} textAnchor="start">
          0 h
        </text>
        <text x={hourToX(8)} y={X_LABEL_Y} textAnchor="middle">
          8 h
        </text>
        <text x={hourToX(12)} y={X_LABEL_Y} textAnchor="middle">
          12 h
        </text>
        <text x={hourToX(18)} y={X_LABEL_Y} textAnchor="middle">
          18 h
        </text>
        <text x={hourToX(23)} y={X_LABEL_Y} textAnchor="end">
          22 h
        </text>
      </g>
    </svg>
  );
}
