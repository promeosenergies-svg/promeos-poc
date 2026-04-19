/**
 * PROMEOS — SolTrajectoryChart (Phase 4.1 refonte)
 *
 * Graphe trajectoire signature Conformité DT (réutilisable Achat énergie
 * Phase 4.4 pour évolution prix marché).
 *
 * Props :
 *   data         : [{month: '2025-11', score: 42.0}, ...] 12 derniers mois
 *   targetLine   : nombre 0-100 — score cible (ex : 75 pour DT)
 *   targetLabel  : texte sous la ligne cible (ex : "Cible DT 2030")
 *   yLabel       : unité Y axis (défaut "score")
 *   sourceChip   : élément <SolSourceChip /> optionnel pour la légende basse
 *   caption      : phrase narrative sous le chart (JSX)
 *   height       : pixels (défaut 200)
 *
 * Zones de couleur (ReferenceArea) :
 *   0–60    : rouge léger (zone risque)
 *   60–75   : ambre léger (vigilance)
 *   75–100  : vert léger (solide)
 *
 * Dernier point annoté avec circle calme-fg + text mono.
 */
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

const MONTH_LABELS_FR = [
  'janv.', 'févr.', 'mars', 'avril', 'mai', 'juin',
  'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.',
];

function formatMonthLabel(monthKey) {
  // Accepte "2026-04" ou "April 2026" ou Date
  if (!monthKey) return '';
  if (typeof monthKey === 'string' && /^\d{4}-\d{2}$/.test(monthKey)) {
    const [, m] = monthKey.split('-');
    return MONTH_LABELS_FR[parseInt(m, 10) - 1] || monthKey;
  }
  return monthKey;
}

export default function SolTrajectoryChart({
  data = [],
  targetLine,
  targetLabel,
  yLabel = 'score',
  sourceChip = null,
  caption = null,
  height = 200,
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
        Historique de trajectoire non disponible.
      </p>
    );
  }

  const last = data[data.length - 1];
  const peakAnnotation = last
    ? { month: last.month, score: last.score }
    : null;

  return (
    <div>
      <div style={{ width: '100%', height }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 20, right: 24, bottom: 30, left: 24 }}>
            <defs>
              <linearGradient id="solTrajectoryFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#0F172A" stopOpacity={0.08} />
                <stop offset="100%" stopColor="#0F172A" stopOpacity={0} />
              </linearGradient>
            </defs>

            {/* Zones de seuil conformité (colorées en fond) */}
            <ReferenceArea
              y1={0}
              y2={60}
              fill="var(--sol-refuse-bg)"
              fillOpacity={0.35}
              ifOverflow="visible"
            />
            <ReferenceArea
              y1={60}
              y2={75}
              fill="var(--sol-attention-bg)"
              fillOpacity={0.3}
              ifOverflow="visible"
            />
            <ReferenceArea
              y1={75}
              y2={100}
              fill="var(--sol-succes-bg)"
              fillOpacity={0.25}
              ifOverflow="visible"
            />

            <CartesianGrid strokeDasharray="2 3" stroke="var(--sol-ink-200)" vertical={false} />
            <XAxis
              dataKey="month"
              tickFormatter={formatMonthLabel}
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
              domain={[0, 100]}
              axisLine={false}
              tickLine={false}
              tick={{
                fontFamily: 'var(--sol-font-mono)',
                fontSize: 10,
                fill: 'var(--sol-ink-400)',
              }}
              width={36}
              label={{
                value: yLabel,
                position: 'insideTopLeft',
                fontSize: 9,
                fill: 'var(--sol-ink-400)',
              }}
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
              labelFormatter={formatMonthLabel}
              formatter={(value) => [`${Number(value).toFixed(1)} pts`, yLabel]}
            />

            <Line
              type="monotone"
              dataKey="score"
              stroke="var(--sol-ink-900)"
              strokeWidth={1.8}
              dot={false}
              activeDot={{ r: 4, stroke: 'var(--sol-calme-fg)', strokeWidth: 2, fill: 'white' }}
            />

            {/* Ligne cible (ex : DT 75 pts ≈ -25% conso) */}
            {targetLine != null && (
              <ReferenceLine
                y={targetLine}
                stroke="var(--sol-attention-fg)"
                strokeDasharray="4 4"
                strokeWidth={1.2}
                label={{
                  value: targetLabel || `cible ${targetLine}`,
                  position: 'right',
                  fill: 'var(--sol-attention-fg)',
                  fontFamily: 'var(--sol-font-mono)',
                  fontSize: 10,
                  fontWeight: 600,
                }}
              />
            )}

            {/* Point dernier mois annoté */}
            {peakAnnotation && (
              <ReferenceDot
                x={peakAnnotation.month}
                y={peakAnnotation.score}
                r={5}
                fill="white"
                stroke="var(--sol-calme-fg)"
                strokeWidth={2.5}
                label={{
                  value: `${formatMonthLabel(peakAnnotation.month)} · ${Number(peakAnnotation.score).toFixed(1)} pts`,
                  position: 'top',
                  offset: 12,
                  fill: 'var(--sol-calme-fg)',
                  fontFamily: 'var(--sol-font-mono)',
                  fontSize: 10,
                  fontWeight: 700,
                }}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Légende + caption */}
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
        <div style={{ flex: 1, minWidth: 240, lineHeight: 1.45 }}>{caption}</div>
        {sourceChip}
      </div>

      {/* Micro-légende zones */}
      <div
        style={{
          display: 'flex',
          gap: 16,
          marginTop: 10,
          fontFamily: 'var(--sol-font-mono)',
          fontSize: 9.5,
          color: 'var(--sol-ink-500)',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
        }}
      >
        <span>
          <span
            style={{
              display: 'inline-block',
              width: 10,
              height: 4,
              background: 'var(--sol-refuse-bg)',
              marginRight: 5,
              verticalAlign: 'middle',
            }}
          />
          0–60 risque
        </span>
        <span>
          <span
            style={{
              display: 'inline-block',
              width: 10,
              height: 4,
              background: 'var(--sol-attention-bg)',
              marginRight: 5,
              verticalAlign: 'middle',
            }}
          />
          60–75 vigilance
        </span>
        <span>
          <span
            style={{
              display: 'inline-block',
              width: 10,
              height: 4,
              background: 'var(--sol-succes-bg)',
              marginRight: 5,
              verticalAlign: 'middle',
            }}
          />
          75–100 solide
        </span>
      </div>
    </div>
  );
}

// Re-export unused chart primitives pour type safety (évite tree-shaking warning)
export { Area, AreaChart };
