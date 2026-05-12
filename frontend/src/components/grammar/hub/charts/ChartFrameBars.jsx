/**
 * grammar/hub/charts/ChartFrameBars — Variante chart barres SVG tone-aware (L11.4).
 *
 * Sprint Grammaire v1.2 / Phase 3.4 / Phase F.8 polish maquette V2 :
 *   - viewBox 320×130 (vs 100×60 F.2) — respire correctement sur 1440px
 *   - Axe Y avec 3 graduations + label baseline dashed (référence visuelle)
 *   - Labels jours en bas mono, samedi/dimanche distingués
 *   - Annotation textuelle au-dessus de la barre anomalie (« + 72 % »)
 *   - Padding interne : axe Y en x=32, plot area en x=32→320
 *
 * Tone-aware fill :
 *   1. `data[i].tone` explicite ('crit'|'warn'|'pos'|'neutral')
 *   2. `toneRules` passées (premier match gagne)
 *   3. défaut 'neutral'
 *
 * Display-only — zero calcul metier (PROMEOS §8.1).
 *
 * @typedef {Object} BarsDatum
 * @property {string} label              - Libelle court ('L', 'M', 'S', ...)
 * @property {number} value              - Valeur numerique
 * @property {'crit'|'warn'|'pos'|'neutral'} [tone]
 *
 * @typedef {Object} ToneRule
 * @property {(value: number, datum: BarsDatum) => boolean} when
 * @property {'crit'|'warn'|'pos'|'neutral'} tone
 *
 * @typedef {Object} BarsAnnotation
 * @property {string} label              - Texte affiché au-dessus (eg "+ 72 %")
 * @property {string} day                - Label de la barre cible (eg "S")
 * @property {'crit'|'warn'|'pos'} [tone='crit']
 *
 * @param {Object} props
 * @param {BarsDatum[]} props.data
 * @param {ToneRule[]} [props.toneRules]
 * @param {number} [props.baseline]      - Valeur baseline (ligne dashed)
 * @param {string} [props.unit='']       - Unité affichée discrètement
 * @param {BarsAnnotation} [props.annotation]
 * @param {string} [props.ariaLabel='Histogramme tone-aware']
 * @param {string} [props.className='']
 */

const TONE_FILL = Object.freeze({
  crit: 'var(--sol-refuse-line)',
  warn: 'var(--sol-attention-line)',
  pos: 'var(--sol-succes-line)',
  neutral: 'var(--sol-ink-300)',
});

const TONE_FG = Object.freeze({
  crit: 'var(--sol-refuse-fg)',
  warn: 'var(--sol-attention-fg)',
  pos: 'var(--sol-succes-fg)',
  neutral: 'var(--sol-ink-500)',
});

// Geometrie maquette V2 (viewBox 0 0 320 130).
const PLOT_LEFT = 32;
const PLOT_RIGHT = 320;
const PLOT_TOP = 18;
const PLOT_BOTTOM = 105;
const Y_LABEL_X = 28;
const X_LABEL_Y = 120;

function resolveTone(datum, toneRules) {
  if (datum?.tone && TONE_FILL[datum.tone]) return datum.tone;
  if (Array.isArray(toneRules)) {
    for (const rule of toneRules) {
      try {
        if (rule?.when?.(datum?.value, datum)) return rule.tone;
      } catch {
        /* rule.when threw — skip to next */
      }
    }
  }
  return 'neutral';
}

/** Mappe une valeur métier à une coordonnée Y SVG (PLOT_TOP → PLOT_BOTTOM). */
function valueToY(value, yMax) {
  if (yMax <= 0) return PLOT_BOTTOM;
  const ratio = value / yMax;
  return PLOT_BOTTOM - ratio * (PLOT_BOTTOM - PLOT_TOP);
}

/** Calcule 3 graduations Y arrondies pour un yMax donné (eg yMax=12 → [4, 8, 12]). */
function yTicks(yMax) {
  if (yMax <= 0) return [];
  // Arrondi au multiple de 4 supérieur pour 3 ticks ronds.
  const rounded = Math.ceil(yMax / 4) * 4;
  return [rounded / 3, (2 * rounded) / 3, rounded].map((v) => Math.round(v * 10) / 10);
}

export default function ChartFrameBars({
  data,
  toneRules,
  baseline,
  unit = '',
  annotation,
  ariaLabel = 'Histogramme tone-aware',
  className = '',
}) {
  if (!Array.isArray(data) || data.length === 0) return null;
  const rawMax = Math.max(...data.map((d) => d.value || 0), 1);
  // Y-axis ceiling : 20 % plus haut que rawMax pour respirer (et accueillir
  // l'annotation textuelle au-dessus de la barre la plus haute).
  const yMax = Math.ceil((rawMax * 1.2) / 2) * 2;
  const ticks = yTicks(yMax);
  const plotWidth = PLOT_RIGHT - PLOT_LEFT;
  const barW = (plotWidth / data.length) * 0.7; // 70 % de chaque slot → gap 30 %
  const slotW = plotWidth / data.length;

  return (
    <svg
      data-component="ChartFrameBars"
      role="img"
      aria-label={ariaLabel}
      viewBox="0 0 320 130"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={{ width: '100%', height: 'auto', display: 'block' }}
    >
      {/* Axe Y — 3 graduations + label baseline dashed (si baseline fourni) */}
      {ticks.map((t, i) => {
        const y = valueToY(t, yMax);
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
              fill="var(--sol-ink-400)"
            >
              {t}
            </text>
          </g>
        );
      })}

      {/* Baseline (référence métier, eg 6,5 MWh/j) — dashed plus marqué */}
      {typeof baseline === 'number' && baseline > 0 && (
        <g data-baseline={baseline}>
          <line
            x1={PLOT_LEFT}
            y1={valueToY(baseline, yMax)}
            x2={PLOT_RIGHT}
            y2={valueToY(baseline, yMax)}
            stroke="var(--sol-ink-500)"
            strokeOpacity="0.55"
            strokeDasharray="3,3"
            strokeWidth="1"
          />
          <text
            x={Y_LABEL_X}
            y={valueToY(baseline, yMax) - 3}
            textAnchor="end"
            fontFamily="var(--sol-font-mono)"
            fontSize="8.5"
            fill="var(--sol-ink-500)"
            fillOpacity="0.7"
          >
            baseline
          </text>
        </g>
      )}

      {/* Barres + labels jours */}
      {data.map((d, i) => {
        const tone = resolveTone(d, toneRules);
        const fill = TONE_FILL[tone] ?? TONE_FILL.neutral;
        const labelColor = TONE_FG[tone] ?? TONE_FG.neutral;
        const x = PLOT_LEFT + i * slotW + (slotW - barW) / 2;
        const yTop = valueToY(d.value, yMax);
        const h = PLOT_BOTTOM - yTop;
        const xLabel = PLOT_LEFT + i * slotW + slotW / 2;
        const isAnnotated = annotation && annotation.day === d.label;
        return (
          <g key={`bar-${i}`} data-bar-index={i} data-bar-tone={tone}>
            {/* Annotation au-dessus de la barre cible */}
            {isAnnotated && (
              <text
                x={xLabel}
                y={yTop - 6}
                textAnchor="middle"
                fontFamily="var(--sol-font-body)"
                fontSize="10"
                fontWeight="500"
                fill={TONE_FG[annotation.tone ?? tone] ?? TONE_FG.crit}
              >
                {annotation.label}
              </text>
            )}
            <rect x={x} y={yTop} width={barW} height={h} fill={fill} rx="2">
              <title>
                {d.label} : {d.value} {unit}
              </title>
            </rect>
            <text
              x={xLabel}
              y={X_LABEL_Y}
              textAnchor="middle"
              fontFamily="var(--sol-font-mono)"
              fontSize="10"
              fontWeight={isAnnotated ? '500' : '400'}
              fill={isAnnotated ? labelColor : 'var(--sol-ink-500)'}
              fillOpacity={isAnnotated ? '1' : '0.7'}
            >
              {d.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
