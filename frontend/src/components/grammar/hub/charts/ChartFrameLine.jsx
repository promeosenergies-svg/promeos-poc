/**
 * grammar/hub/charts/ChartFrameLine — Variante chart courbe 24h HP/HC + seuil (L11.4).
 *
 * Sprint Grammaire v1.2 / Phase 3.4 / Phase F.10 (audit user F.9) :
 *   - viewBox 340×150 (élargi vs 320×130 F.8) — donne de l'air aux labels :
 *     fini "1 000" rogné à gauche, fini "kW" rogné à droite, fini la
 *     courbe HC coupée nette au bord. Phase F.10 fix.
 *   - Légende HP/HC en haut à gauche (segments + texte "Heures pleines (HP)"
 *     / "Heures creuses (HC)") — F.10 fix audit "légende absente".
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

// Geometrie maquette V2 (viewBox 0 0 340 160) — Phase F.11 :
// hauteur 150→160 et PLOT_TOP 30→40 pour décoller VISUELLEMENT la légende
// HP/HC (y=14) du label seuil "P. souscrite … kW" (y=36) qui se
// superposaient sur des seuils >> yMax (le seuil clamp à PLOT_TOP).
// Audit user F.10 "tronqué, superposé".
const PLOT_LEFT = 38;
const PLOT_RIGHT = 308;
const PLOT_TOP = 40;
const PLOT_BOTTOM = 132;
const Y_LABEL_X = 34;
const X_LABEL_Y = 148;
const LEGEND_Y = 14;
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

/** Découpe une série en segments contigus (gap > 1h crée un nouveau segment).
 *  Phase F.12 fix audit user "problème courbe HP/HC" : la série HC enchaîne
 *  les points 0h-7h puis 22h-23h ; sans split, SVG trace une ligne droite
 *  de 7h à 22h qui traverse toute la zone HP visuellement. Le split rend
 *  2 polylines distinctes (matin + soir) qui ne se chevauchent plus. */
function splitIntoSegments(series) {
  if (!Array.isArray(series) || series.length === 0) return [];
  const segments = [];
  let current = [series[0]];
  for (let i = 1; i < series.length; i++) {
    if (series[i].hour - series[i - 1].hour > 1) {
      segments.push(current);
      current = [series[i]];
    } else {
      current.push(series[i]);
    }
  }
  segments.push(current);
  return segments;
}

/** Calcule 3 graduations Y arrondies à pas régulier (Phase F.20c-2 fix
 *  dynamique : ne retourne que les ticks qui rentrent dans yMax, pour
 *  éviter d'afficher "1 000" alors que yMax=300). */
function yTicks(yMax) {
  if (yMax <= 0) return [];
  let step;
  if (yMax <= 100) step = 25;
  else if (yMax <= 300) step = 100;
  else if (yMax <= 600) step = 200;
  else if (yMax <= 1500) step = 500;
  else step = Math.ceil(yMax / 3000) * 1000;
  return [step, step * 2, step * 3].filter((t) => t <= yMax + step * 0.1);
}

/** Formate un nombre en français : virgule décimale, espace milliers (NBSP).
 *  Phase F.9 — convention FR (audit user "métriques et nombres convention fr").
 */
const _FR_NUMBER = new Intl.NumberFormat('fr-FR', {
  maximumFractionDigits: 0,
  useGrouping: true,
});
function formatFr(n) {
  return _FR_NUMBER.format(n);
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

  // Phase F.20c-2 — yMax DYNAMIQUE basé sur les données réelles (peak +
  // série) avec 15 % de headroom, snappé sur des nombres ronds. La
  // puissance souscrite (souvent 1 480-1 500 kW) est volontairement
  // ignorée du calcul d'échelle car elle écrasait toute la courbe à
  // 245 kW (peak réel) dans le bas du graphique. Elle reste affichée
  // comme ligne dashed clampée en haut quand au-delà de yMax.
  const seriesMaxHP = hasHP ? Math.max(...seriesHP.map((p) => p.kw)) : 0;
  const seriesMaxHC = hasHC ? Math.max(...seriesHC.map((p) => p.kw)) : 0;
  const peakKw = peak?.kw ?? 0;
  const rawMax = Math.max(seriesMaxHP, seriesMaxHC, peakKw);
  // Padding 15 % + snap nice number (50 kW ≤500, 100 kW >500).
  const padded = rawMax * 1.15;
  const roundTo = padded > 500 ? 100 : 50;
  const yMax = padded > 0 ? Math.ceil(padded / roundTo) * roundTo : 0;
  const ticks = yTicks(yMax);
  // Indicateur "threshold above scale" : le seuil dépasse yMax → on l'affiche
  // au top avec un libellé qui explicite la valeur réelle (sinon l'utilisateur
  // peut croire que la ligne dashed est à yMax kW).
  const thresholdAboveScale = thresholdValue && thresholdValue > yMax;

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
      viewBox="0 0 340 160"
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

      {/* Légende HP / HC (Phase F.10 — fix audit "légende absente").
          Segments courts + texte mono, alignés en haut à gauche du plot. */}
      <g data-legend>
        <line
          x1={PLOT_LEFT}
          y1={LEGEND_Y}
          x2={PLOT_LEFT + 14}
          y2={LEGEND_Y}
          stroke={STROKE_HP}
          strokeWidth="1.6"
          strokeLinecap="round"
        />
        <text
          x={PLOT_LEFT + 18}
          y={LEGEND_Y + 3}
          fontFamily="var(--sol-font-mono)"
          fontSize="9"
          fill="var(--sol-ink-500)"
        >
          Heures pleines (HP)
        </text>
        <line
          x1={PLOT_LEFT + 130}
          y1={LEGEND_Y}
          x2={PLOT_LEFT + 144}
          y2={LEGEND_Y}
          stroke={STROKE_HC}
          strokeWidth="1.6"
          strokeLinecap="round"
        />
        <text
          x={PLOT_LEFT + 148}
          y={LEGEND_Y + 3}
          fontFamily="var(--sol-font-mono)"
          fontSize="9"
          fill="var(--sol-ink-500)"
        >
          Heures creuses (HC)
        </text>
      </g>

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
              {formatFr(t)}
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
            {thresholdLabel ?? `P. souscrite ${formatFr(thresholdValue)} ${thresholdUnit}`}
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

      {/* Courbe HC (heures creuses, bleue) — F.12 : split en segments
          contigus pour éviter la ligne traversante 7h→22h. */}
      {hasHC &&
        yMax > 0 &&
        splitIntoSegments(seriesHC).map((seg, i) => (
          <polyline
            key={`hc-${i}`}
            data-series="hc"
            data-segment={i}
            points={seriesToPoints(seg, yMax)}
            fill="none"
            stroke={STROKE_HC}
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ))}

      {/* Courbe HP (heures pleines, orange) — F.12 : split par cohérence
          (HP est généralement contiguë, mais sécurise les futures données). */}
      {hasHP &&
        yMax > 0 &&
        splitIntoSegments(seriesHP).map((seg, i) => (
          <polyline
            key={`hp-${i}`}
            data-series="hp"
            data-segment={i}
            points={seriesToPoints(seg, yMax)}
            fill="none"
            stroke={STROKE_HP}
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ))}

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
            {peak.label ?? `${formatFr(peak.kw)} kW`}
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
          23 h
        </text>
      </g>

      {/* Phase F.20c-3 — Tooltips invisibles par point (hover natif SVG).
          Cercles transparents de rayon 8px sur chaque data point ; le
          <title> est lu par le browser comme tooltip natif au survol.
          tariff label "HP"/"HC" + heure + valeur kW. */}
      {hasHC &&
        yMax > 0 &&
        seriesHC.map((p, i) => (
          <circle
            key={`hover-hc-${i}`}
            cx={hourToX(p.hour)}
            cy={kwToY(p.kw, yMax)}
            r="8"
            fill="transparent"
            style={{ pointerEvents: 'all', cursor: 'crosshair' }}
          >
            <title>{`HC · ${p.hour} h · ${formatFr(p.kw)} kW`}</title>
          </circle>
        ))}
      {hasHP &&
        yMax > 0 &&
        seriesHP.map((p, i) => (
          <circle
            key={`hover-hp-${i}`}
            cx={hourToX(p.hour)}
            cy={kwToY(p.kw, yMax)}
            r="8"
            fill="transparent"
            style={{ pointerEvents: 'all', cursor: 'crosshair' }}
          >
            <title>{`HP · ${p.hour} h · ${formatFr(p.kw)} kW`}</title>
          </circle>
        ))}
    </svg>
  );
}
