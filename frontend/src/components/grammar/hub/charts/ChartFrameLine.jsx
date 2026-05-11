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

/** Convertit une serie en string points SVG (viewBox 0..100 x 0..60).
 *  Y_SCALE_FACTOR=4 laisse ~75 % de marge visuelle sous le threshold (le pic
 *  attendu sur un site tertiaire est typiquement < threshold/4). Au-delà,
 *  le clamp Y∈[2,58] s'applique pour empêcher la sortie de viewBox.
 *
 *  Audit /simplify P2 fix : constante nommée vs magic 4 inline.
 */
const Y_SCALE_FACTOR = 4;

function toSvgPoints(series, thresholdMax) {
  if (!Array.isArray(series) || series.length === 0 || !thresholdMax) return '';
  const xMax = series.length - 1;
  return series
    .map((p, i) => {
      const x = (i / xMax) * 100;
      const yRaw = 60 - (p.kw / thresholdMax) * 60 * Y_SCALE_FACTOR;
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
  // Audit /simplify + CS P1 fix : SUPPRESSION du fallback synthétique
  // (anciennement function helper). Le frontend ne fabrique plus de
  // données « plausibles » qui pourraient être prises pour de vraies CDC
  // en démo investisseur. Si le backend ne fournit ni seriesHP ni seriesHC,
  // on render uniquement axes + threshold (lecture honnête : « pas de
  // données disponibles » plutôt qu'une courbe trompeuse).
  const effectiveHC = hasHC ? seriesHC : null;
  const effectiveHP = hasHP ? seriesHP : null;

  const thresholdValue = threshold?.value;
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
