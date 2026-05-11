/**
 * grammar/hub/charts/ChartFrameBars — Variante chart barres SVG tone-aware (L11.4).
 *
 * Sprint Grammaire v1.2 / Phase 3.4 / Phase F.2 — extraction de BarsDaily7d
 * inline depuis pages/CockpitJour.jsx vers le namespace canonique charts/.
 *
 * Pattern composition : enfant d'un wrapper <ChartFrame> qui apporte
 * question/réponse/footScm. Ce primitif n'expose QUE le SVG.
 *
 * Tone-aware fill : chaque barre peut être colorée par :
 *   1. la prop `data[i].tone` explicite ('crit'|'warn'|'pos'|'neutral')
 *   2. les `toneRules` passées (premier match gagne)
 *   3. défaut 'neutral'
 *
 * Display-only — zero calcul metier (PROMEOS §8.1). Les valeurs viennent
 * du backend (`_build_cockpit_jour_charts` series 7j), seul le mapping
 * valeur → coordonnée SVG est fait ici (responsabilité présentation).
 *
 * Source-guards : `data-component="ChartFrameBars"`.
 *
 * @typedef {Object} BarsDatum
 * @property {string} label              - Libelle court (ex. 'L', 'M', 'S')
 * @property {number} value              - Valeur numerique
 * @property {'crit'|'warn'|'pos'|'neutral'} [tone] - Tone explicite (override toneRules)
 *
 * @typedef {Object} ToneRule
 * @property {(value: number, datum: BarsDatum) => boolean} when
 * @property {'crit'|'warn'|'pos'|'neutral'} tone
 *
 * @param {Object} props
 * @param {BarsDatum[]} props.data
 * @param {ToneRule[]} [props.toneRules]
 * @param {string} [props.ariaLabel='Histogramme tone-aware']
 * @param {string} [props.className='']
 */

const TONE_FILL = Object.freeze({
  crit: 'var(--sol-refuse-line)',
  warn: 'var(--sol-attention-line)',
  pos: 'var(--sol-succes-line)',
  neutral: 'var(--sol-ink-300)',
});

/** Resolves the effective tone of a datum.
 *  Priority : explicit datum.tone → first matching toneRule → 'neutral'.
 */
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

export default function ChartFrameBars({
  data,
  toneRules,
  ariaLabel = 'Histogramme tone-aware',
  className = '',
}) {
  if (!Array.isArray(data) || data.length === 0) return null;
  const max = Math.max(...data.map((d) => d.value || 0), 1);
  const barW = 100 / data.length - 3;

  return (
    <svg
      data-component="ChartFrameBars"
      role="img"
      aria-label={ariaLabel}
      viewBox="0 0 100 60"
      preserveAspectRatio="none"
      className={className}
      style={{ width: '100%', height: '120px' }}
    >
      {data.map((d, i) => {
        const h = (d.value / max) * 50;
        const x = i * (barW + 3);
        const tone = resolveTone(d, toneRules);
        const fill = TONE_FILL[tone] ?? TONE_FILL.neutral;
        return (
          <g key={`bar-${i}`} data-bar-index={i} data-bar-tone={tone}>
            <rect x={x} y={55 - h} width={barW} height={h} fill={fill} rx="0.5">
              <title>
                {d.label} : {d.value}
              </title>
            </rect>
            <text
              x={x + barW / 2}
              y={59}
              textAnchor="middle"
              fontSize="3.5"
              fill="var(--sol-ink-500)"
              fontFamily="var(--sol-font-mono)"
            >
              {d.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
