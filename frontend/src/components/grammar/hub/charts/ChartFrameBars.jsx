/**
 * grammar/hub/charts/ChartFrameBars — Variante chart barres SVG tone-aware (L11.4).
 *
 * Sprint Grammaire v1.2 / Phase 3.4 / Phase F.10 (audit user F.9) :
 *   - viewBox 340×150 (élargi vs 320×130 F.8) pour cohérence avec
 *     ChartFrameLine et marges latérales sûres pour annotations / Y-axis.
 *   - Axe Y avec 3 graduations + label baseline dashed (référence visuelle)
 *   - Labels jours en bas mono, samedi/dimanche distingués
 *   - Annotation textuelle au-dessus de la barre anomalie (« + 72 % »)
 *   - Padding interne : axe Y en x=38, plot area en x=38→308
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

// Geometrie maquette V2 (viewBox 0 0 340 160) — Phase F.11 :
// alignée sur ChartFrameLine (hauteur 160) pour cohérence d'aspect ratio
// entre les 2 charts du briefing.
const PLOT_LEFT = 38;
const PLOT_RIGHT = 308;
const PLOT_TOP = 40;
const PLOT_BOTTOM = 132;
const Y_LABEL_X = 34;
const X_LABEL_Y = 148;

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

/** Calcule 3 graduations Y arrondies à des nombres ronds (Phase F.9 fix).
 *  Stratégie : choisir un pas qui donne des valeurs entières (5/10/15
 *  pour yMax≈15, 50/100/150 pour yMax≈150, etc.). Aucune décimale.
 */
function yTicks(yMax) {
  if (yMax <= 0) return [];
  // Choix du pas selon l'ordre de grandeur de yMax.
  let step;
  if (yMax <= 6) step = 2;
  else if (yMax <= 15) step = 5;
  else if (yMax <= 30) step = 10;
  else if (yMax <= 60) step = 20;
  else if (yMax <= 150) step = 50;
  else step = Math.ceil(yMax / 300) * 100;
  return [step, step * 2, step * 3];
}

/** Formate un nombre en français : virgule décimale, espace milliers (non-breaking). */
const _FR_NUMBER = new Intl.NumberFormat('fr-FR', {
  maximumFractionDigits: 1,
  useGrouping: true,
});
function formatFr(n) {
  // Phase F.9 — Intl.NumberFormat fr-FR émet U+202F (narrow nbsp) comme
  // séparateur de milliers ; on remplace par U+00A0 (nbsp standard) pour
  // un rendu SVG cohérent. Échappements unicode pour passer ESLint
  // no-irregular-whitespace (incident F.10 pre-commit).
  return _FR_NUMBER.format(n).replace(/\u202F/g, '\u00A0');
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
  // Y-axis ceiling Phase F.9 — basé directement sur yTicks rounder pour
  // que le tick supérieur soit toujours ≥ rawMax + padding visuel 15 %.
  const padded = rawMax * 1.15;
  const ticks = yTicks(padded);
  const yMax = ticks.length > 0 ? ticks[ticks.length - 1] : padded;
  const plotWidth = PLOT_RIGHT - PLOT_LEFT;
  const barW = (plotWidth / data.length) * 0.7; // 70 % de chaque slot → gap 30 %
  const slotW = plotWidth / data.length;

  return (
    <svg
      data-component="ChartFrameBars"
      role="img"
      aria-label={ariaLabel}
      viewBox="0 0 340 160"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={{ width: '100%', height: 'auto', display: 'block' }}
    >
      {/* Axe Y — 3 graduations (Phase F.9 : valeurs formatées FR virgule décimale) */}
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
              {formatFr(t)}
            </text>
          </g>
        );
      })}

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

      {/* Baseline (référence métier, eg 6,5 MWh/j) — Phase F.20c-1 :
          rendu APRÈS les bars pour z-order SVG (la ligne dashed et le label
          doivent être visibles devant les barres, sinon "référence" est
          rogné par la barre L). Label déplacé à droite du chart pour
          ne pas chevaucher les premières barres. */}
      {typeof baseline === 'number' && baseline > 0 && (
        <g data-baseline={baseline}>
          <line
            x1={PLOT_LEFT}
            y1={valueToY(baseline, yMax)}
            x2={PLOT_RIGHT}
            y2={valueToY(baseline, yMax)}
            stroke="var(--sol-ink-700)"
            strokeOpacity="0.7"
            strokeDasharray="4,3"
            strokeWidth="1.2"
          />
          <text
            x={PLOT_RIGHT - 2}
            y={valueToY(baseline, yMax) - 3}
            textAnchor="end"
            fontFamily="var(--sol-font-mono)"
            fontSize="9"
            fill="var(--sol-ink-700)"
            fillOpacity="0.95"
          >
            {`réf. ${formatFr(baseline)}${unit ? ' ' + unit : ''}`}
          </text>
        </g>
      )}
    </svg>
  );
}
