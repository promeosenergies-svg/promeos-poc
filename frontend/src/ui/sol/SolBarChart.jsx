/**
 * PROMEOS — SolBarChart (Phase 4.1.1, préparation Phase 4.2 Bill Intelligence)
 *
 * Bar chart mensuel signature pour comparaisons current vs previous.
 * Utilisé par Bill Intelligence (factures mensuelles), futur /monitoring,
 * et tout graphe comparatif mensuel.
 *
 * Props :
 *   data               : [{ month: 'janv.', current: 42380, previous: 38920 }, ...]
 *   metric             : 'euros' | 'mwh' | 'count' — détermine format Y axis
 *   showDeltaPct       : bool — affiche +/-X % au-dessus de chaque barre current
 *   sourceChip         : <SolSourceChip /> optionnel légende basse
 *   highlightCurrent   : bool — mois courant en couleur calme-fg plutôt qu'ink-700
 *   caption            : phrase narrative sous chart (JSX)
 *   height             : pixels (défaut 220)
 *
 * Structure Recharts :
 *   - BarChart responsive
 *   - XAxis mois (12 derniers)
 *   - YAxis format selon metric
 *   - Bar "previous" fill ink-300 opacity 0.7 barSize smaller (comparateur)
 *   - Bar "current" fill ink-900 (ou calme-fg si highlightCurrent + dernière)
 *   - LabelList delta pct au-dessus current si showDeltaPct
 *   - Tooltip mono minimal
 *   - Source chip + caption en légende basse
 */
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

function formatValue(value, metric) {
  if (value == null || isNaN(value)) return '—';
  const n = Number(value);
  if (metric === 'euros') {
    if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace('.', ',')}${'\u00A0'}M€`;
    if (Math.abs(n) >= 1_000) return `${(n / 1_000).toFixed(0)}${'\u00A0'}k€`;
    return `${n.toFixed(0)}${'\u00A0'}€`;
  }
  if (metric === 'mwh') {
    if (Math.abs(n) >= 1_000) return `${(n / 1_000).toFixed(1).replace('.', ',')}${'\u00A0'}GWh`;
    return `${n.toFixed(0)}${'\u00A0'}MWh`;
  }
  // count / default
  return `${n.toLocaleString('fr-FR').replace(/,/g, '\u202F')}`;
}

function computeDeltaPct(current, previous) {
  if (current == null || previous == null || previous === 0) return null;
  return Math.round(((current - previous) / previous) * 100);
}

/**
 * LabelList content renderer — signed delta pct au-dessus des barres current.
 * Coloration : baisse = succes-fg (bon pour coûts), hausse = afaire-fg.
 * Sémantique cost ici (contexte Bill Intelligence). Pour d'autres usages
 * où hausse=bon (score), utiliser semantic prop à l'avenir.
 */
function DeltaPctLabel({ x, y, width, value, payload }) {
  // value injecté par LabelList.dataKey, fallback calcul depuis payload
  const current = payload?.current ?? value;
  const previous = payload?.previous;
  const delta = computeDeltaPct(current, previous);
  if (delta == null) return null;
  const sign = delta > 0 ? '+' : delta < 0 ? '−' : '';
  const color = delta > 0 ? 'var(--sol-afaire-fg)' : 'var(--sol-succes-fg)';
  return (
    <text
      x={x + width / 2}
      y={y - 6}
      textAnchor="middle"
      fontFamily="var(--sol-font-mono)"
      fontSize={9.5}
      fontWeight={600}
      fill={color}
    >
      {sign}
      {Math.abs(delta)}%
    </text>
  );
}

export default function SolBarChart({
  data = [],
  metric = 'euros',
  showDeltaPct = false,
  sourceChip = null,
  highlightCurrent = false,
  caption = null,
  height = 220,
}) {
  if (!Array.isArray(data) || data.length === 0) {
    return (
      <p
        style={{
          fontSize: 13,
          color: 'var(--sol-ink-400)',
          fontStyle: 'italic',
          padding: '24px 0',
          margin: 0,
          textAlign: 'center',
        }}
      >
        Historique non disponible.
      </p>
    );
  }

  // Mois courant = dernier de la série
  const lastIdx = data.length - 1;
  const dataWithFlag = data.map((d, i) => ({ ...d, isCurrent: i === lastIdx }));

  const currentFillFn = (entry) => {
    if (highlightCurrent && entry?.isCurrent) return 'var(--sol-calme-fg)';
    return 'var(--sol-ink-700)';
  };

  return (
    <div>
      <div style={{ width: '100%', height }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={dataWithFlag} margin={{ top: 24, right: 24, bottom: 28, left: 24 }}>
            <CartesianGrid strokeDasharray="2 3" stroke="var(--sol-ink-200)" vertical={false} />
            <XAxis
              dataKey="month"
              axisLine={false}
              tickLine={false}
              tick={{
                fontFamily: 'var(--sol-font-mono)',
                fontSize: 10,
                fill: 'var(--sol-ink-500)',
              }}
              interval="preserveStartEnd"
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{
                fontFamily: 'var(--sol-font-mono)',
                fontSize: 10,
                fill: 'var(--sol-ink-400)',
              }}
              width={48}
              tickFormatter={(v) => formatValue(v, metric)}
            />
            <Tooltip
              contentStyle={{
                background: 'var(--sol-bg-paper)',
                border: '1px solid var(--sol-rule)',
                borderRadius: 4,
                fontFamily: 'var(--sol-font-mono)',
                fontSize: 11,
                color: 'var(--sol-ink-900)',
              }}
              formatter={(value, name) => [formatValue(value, metric), name === 'current' ? 'mois' : 'année\u00A0N\u202F−\u202F1']}
            />

            {/* Barre previous (comparateur, ink-300, opacity 0.7) */}
            <Bar
              dataKey="previous"
              fill="var(--sol-ink-300)"
              fillOpacity={0.7}
              barSize={16}
              radius={[3, 3, 0, 0]}
            />

            {/* Barre current — ink-700 normal, calme-fg si highlightCurrent sur dernier mois */}
            <Bar
              dataKey="current"
              fill="var(--sol-ink-700)"
              barSize={24}
              radius={[3, 3, 0, 0]}
              shape={(props) => {
                const color = currentFillFn(props.payload);
                return (
                  <rect
                    x={props.x}
                    y={props.y}
                    width={props.width}
                    height={props.height}
                    rx={3}
                    ry={3}
                    fill={color}
                  />
                );
              }}
            >
              {showDeltaPct && <LabelList dataKey="current" content={<DeltaPctLabel />} />}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Légende (current / previous) + caption + source */}
      <div
        style={{
          display: 'flex',
          alignItems: 'baseline',
          justifyContent: 'space-between',
          gap: 12,
          marginTop: 8,
          fontSize: 12.5,
          color: 'var(--sol-ink-500)',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', gap: 16, fontFamily: 'var(--sol-font-mono)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
          <span>
            <span
              style={{
                display: 'inline-block',
                width: 10,
                height: 10,
                background: highlightCurrent ? 'var(--sol-calme-fg)' : 'var(--sol-ink-700)',
                marginRight: 5,
                verticalAlign: 'middle',
                borderRadius: 2,
              }}
            />
            année en cours
          </span>
          <span>
            <span
              style={{
                display: 'inline-block',
                width: 10,
                height: 10,
                background: 'var(--sol-ink-300)',
                opacity: 0.7,
                marginRight: 5,
                verticalAlign: 'middle',
                borderRadius: 2,
              }}
            />
            année N−1
          </span>
        </div>
        <div style={{ flex: 1, minWidth: 200, lineHeight: 1.45 }}>{caption}</div>
        {sourceChip}
      </div>
    </div>
  );
}
