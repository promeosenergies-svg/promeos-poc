/**
 * PROMEOS — SolTrajectoryChart (Phase 4.1 ; étendu Phase 4.4 Achat)
 *
 * Graphe trajectoire / évolution temporelle signature.
 * Utilisé par :
 *   - Conformité DT (score compliance 6-12 mois + zones seuil + cible)
 *   - Achat énergie (prix marché spot 12 mois + ligne prix contracté utilisateur
 *                    + fenêtre d'opportunité)
 *
 * Props :
 *   data             : [{month, score}] ou [{month, value}] — X temporel
 *   dataKey          : clé numérique lue — défaut 'score'
 *   targetLine       : nombre cible (null → pas de ReferenceLine target) — défaut null
 *   targetLabel      : texte sous la cible (ex "Cible DT 2030")
 *   userLine         : nombre pour une ligne horizontale user (ex "Votre prix actuel")
 *   userLabel        : texte près de userLine
 *   yDomain          : [min, max] — défaut [0, 100] adapté score
 *   yLabel           : unité Y axis
 *   showThresholdZones : bool — défaut true pour Conformité (0-60/60-75/75-100)
 *                        false pour Achat (pas de zones de seuil)
 *   opportunityArea  : { x1, x2, label } — ReferenceArea calme-fg opacity 0.2
 *                      (optionnel — affiché seulement si non-null)
 *   sourceChip       : <SolSourceChip /> optionnel
 *   caption          : phrase narrative JSX
 *   height           : pixels (défaut 200)
 *
 * Zones de couleur (showThresholdZones=true) :
 *   0–60    : rouge léger (risque)
 *   60–75   : ambre léger (vigilance)
 *   75–100  : vert léger (solide)
 *
 * Dernier point annoté circle calme-fg + text mono dans tous les cas.
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
  'janv.',
  'févr.',
  'mars',
  'avril',
  'mai',
  'juin',
  'juil.',
  'août',
  'sept.',
  'oct.',
  'nov.',
  'déc.',
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
  dataKey = 'score',
  targetLine,
  targetLabel,
  userLine = null,
  userLabel = '',
  yDomain = [0, 100],
  yLabel = 'score',
  showThresholdZones = true,
  opportunityArea = null,
  sourceChip = null,
  caption = null,
  height = 200,
  // Lot 3 Phase 4 — jalons verticaux (ex : DT 2030/2040/2050).
  // Shape : [{ x, label, tone: 'attention'|'succes'|'afaire'|'refuse' }]
  // `x` doit correspondre à la valeur exacte d'une entrée data[i].month
  // pour que recharts place la ReferenceLine sur un tick existant.
  verticalMarkers = null,
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
  const peakAnnotation = last ? { month: last.month, score: last[dataKey] } : null;

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

            {/* Zones de seuil conformité — affichées seulement si showThresholdZones */}
            {showThresholdZones && (
              <>
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
              </>
            )}

            {/* Opportunity area (Achat : fenêtre favorable prix marché bas) */}
            {opportunityArea && (
              <ReferenceArea
                x1={opportunityArea.x1}
                x2={opportunityArea.x2}
                fill="var(--sol-calme-bg)"
                fillOpacity={0.35}
                ifOverflow="visible"
                label={{
                  value: opportunityArea.label || 'Fenêtre favorable',
                  position: 'insideTop',
                  fill: 'var(--sol-calme-fg)',
                  fontFamily: 'var(--sol-font-mono)',
                  fontSize: 9.5,
                  fontWeight: 600,
                }}
              />
            )}

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
              domain={yDomain}
              axisLine={false}
              tickLine={false}
              tick={{
                fontFamily: 'var(--sol-font-mono)',
                fontSize: 10,
                fill: 'var(--sol-ink-400)',
              }}
              width={44}
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
              formatter={(value) => [`${Number(value).toFixed(1)}`, yLabel]}
            />

            <Line
              type="monotone"
              dataKey={dataKey}
              stroke="var(--sol-ink-900)"
              strokeWidth={1.8}
              dot={false}
              activeDot={{ r: 4, stroke: 'var(--sol-calme-fg)', strokeWidth: 2, fill: 'white' }}
            />

            {/* Jalons verticaux (Lot 3 P4 : DT 2030/2040/2050). Optional. */}
            {Array.isArray(verticalMarkers) &&
              verticalMarkers.map((m, i) => {
                const toneColor =
                  {
                    attention: 'var(--sol-attention-fg)',
                    afaire: 'var(--sol-afaire-fg)',
                    succes: 'var(--sol-succes-fg)',
                    refuse: 'var(--sol-refuse-fg)',
                    calme: 'var(--sol-calme-fg)',
                  }[m.tone || 'attention'] || 'var(--sol-attention-fg)';
                return (
                  <ReferenceLine
                    key={`vmarker-${i}-${m.x}`}
                    x={m.x}
                    stroke={toneColor}
                    strokeDasharray="3 3"
                    strokeWidth={1.1}
                    label={{
                      value: m.label,
                      position: 'insideTop',
                      fill: toneColor,
                      fontFamily: 'var(--sol-font-mono)',
                      fontSize: 9.5,
                      fontWeight: 600,
                    }}
                  />
                );
              })}

            {/* Ligne cible (ex : DT 75 pts ≈ -25% conso). Optional. */}
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

            {/* Ligne utilisateur (Achat : prix pondéré contracté actuel). Optional. */}
            {userLine != null && (
              <ReferenceLine
                y={userLine}
                stroke="var(--sol-afaire-fg)"
                strokeDasharray="6 3"
                strokeWidth={1.4}
                label={{
                  value: userLabel || `votre niveau ${userLine}`,
                  position: 'left',
                  fill: 'var(--sol-afaire-fg)',
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

      {/* Micro-légende zones (conformité seulement) */}
      {showThresholdZones && (
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
      )}
    </div>
  );
}

// Re-export unused chart primitives pour type safety (évite tree-shaking warning)
export { Area, AreaChart };
