/**
 * PROMEOS — SolLoadCurve
 *
 * Courbe de charge signature Sol avec bandes tarifaires HP/HC, area fill
 * slate, stroke ink-900 tranchant, point "pic maintenant" emerald.
 *
 * Construit avec Recharts (déjà dans deps) pour héritage graphique
 * cohérent avec les autres charts PROMEOS.
 *
 * Source maquette : SVG inline de la maquette V2 raw — adapté Recharts.
 *
 * Data shape attendue :
 *   data : [{ time: '00:00', value: 42 }, ...]  — pas 30 min ou 1h
 *   peakPoint : { time: '14:00', value: 118, label: 'pic 14 h 32 · 118 kW' }
 *   hpStart : index timestamp HP start (ex: 6 pour 06:00)
 *   hpEnd : index timestamp HP end (ex: 22 pour 22:00)
 */
import {
  Area,
  AreaChart,
  ReferenceArea,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

const DEFAULT_DATA = [
  { time: '00:00', value: 40 },
  { time: '02:00', value: 38 },
  { time: '04:00', value: 35 },
  { time: '06:00', value: 48 },
  { time: '08:00', value: 70 },
  { time: '10:00', value: 95 },
  { time: '12:00', value: 110 },
  { time: '14:00', value: 118 },
  { time: '16:00', value: 95 },
  { time: '18:00', value: 75 },
  { time: '20:00', value: 58 },
  { time: '22:00', value: 45 },
  { time: '24:00', value: 40 },
];

// Arrondi vers le haut au prochain "nice number" pour ticks YAxis lisibles.
function niceMax(rawMax) {
  if (rawMax <= 50) return Math.ceil(rawMax / 10) * 10;
  if (rawMax <= 200) return Math.ceil(rawMax / 30) * 30;
  if (rawMax <= 500) return Math.ceil(rawMax / 50) * 50;
  return Math.ceil(rawMax / 100) * 100;
}

export default function SolLoadCurve({
  data = DEFAULT_DATA,
  peakPoint = { time: '14:00', value: 118, label: 'pic 14 h · 118 kW' },
  hpStart = '06:00',
  hpEnd = '22:00',
  unit = 'kW',
  // peakThreshold : fraction du pic (ex 0.8 = 80%) → ReferenceLine horizontale
  // pour pilotage discipline HP/HC. Si null/undefined, pas de ligne.
  peakThreshold = null,
  caption = (
    <>
      <strong style={{ color: 'var(--sol-ink-900)' }}>85{'\u00A0'}% de votre consommation</strong>{' '}
      tombe en heures pleines — attendu pour un bureau. Votre contrat est bien calibré.
    </>
  ),
  sourceChip = null,
}) {
  const thresholdValue =
    peakThreshold != null && peakPoint?.value != null
      ? Math.round(peakPoint.value * peakThreshold)
      : null;
  // YAxis domain — niceMax avec headroom pour label "pic"
  const dataMax = Math.max(
    ...data.map((p) => p.value || 0),
    peakPoint?.value || 0,
    thresholdValue || 0
  );
  const yMax = niceMax(dataMax * 1.18);
  return (
    <div>
      <div
        style={{
          width: '100%',
          height: 240,
          marginBottom: 8,
        }}
      >
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 20, right: 24, bottom: 30, left: 24 }}>
            <defs>
              <linearGradient id="solLoadCurveFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#0F172A" stopOpacity={0.12} />
                <stop offset="100%" stopColor="#0F172A" stopOpacity={0} />
              </linearGradient>
            </defs>

            {/* Bandes HP (rose très pâle) + HC avant/après */}
            <ReferenceArea
              x1="00:00"
              x2={hpStart}
              fill="var(--sol-hch-bg)"
              fillOpacity={0.45}
              ifOverflow="visible"
            />
            <ReferenceArea
              x1={hpStart}
              x2={hpEnd}
              fill="var(--sol-hph-bg)"
              fillOpacity={0.55}
              ifOverflow="visible"
            />
            <ReferenceArea
              x1={hpEnd}
              x2="24:00"
              fill="var(--sol-hch-bg)"
              fillOpacity={0.45}
              ifOverflow="visible"
            />

            <XAxis
              dataKey="time"
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
              width={36}
              // Domain niceMax pré-calculé → ticks ronds (multiple de 10/30/50)
              // au lieu de valeurs odd type 105/35.
              domain={[0, yMax]}
              tickCount={6}
              label={{
                value: unit,
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
              labelStyle={{ color: 'var(--sol-ink-500)', fontSize: 10 }}
              formatter={(value) => [`${value} ${unit}`, 'puissance']}
            />

            <Area
              type="monotone"
              dataKey="value"
              stroke="var(--sol-ink-900)"
              strokeWidth={1.8}
              fill="url(#solLoadCurveFill)"
            />

            {thresholdValue != null && (
              <ReferenceLine
                y={thresholdValue}
                stroke="var(--sol-attention-fg, #b45309)"
                strokeDasharray="4 3"
                strokeWidth={1}
                label={{
                  value: `seuil ${Math.round(peakThreshold * 100)}% · ${thresholdValue} ${unit}`,
                  position: 'insideTopRight',
                  fill: 'var(--sol-attention-fg, #b45309)',
                  fontFamily: 'var(--sol-font-mono)',
                  fontSize: 9,
                  fontWeight: 600,
                }}
              />
            )}

            {peakPoint && (
              <ReferenceDot
                x={peakPoint.time}
                y={peakPoint.value}
                r={5}
                fill="white"
                stroke="var(--sol-calme-fg)"
                strokeWidth={2.5}
                label={{
                  value: peakPoint.label,
                  position: 'top',
                  offset: 12,
                  fill: 'var(--sol-calme-fg)',
                  fontFamily: 'var(--sol-font-mono)',
                  fontSize: 10,
                  fontWeight: 700,
                }}
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Légende HP/HC */}
      <div
        style={{
          display: 'flex',
          gap: 24,
          fontFamily: 'var(--sol-font-mono)',
          fontSize: 10,
          color: 'var(--sol-ink-500)',
          marginBottom: 10,
        }}
      >
        <span>
          <span
            style={{
              display: 'inline-block',
              width: 10,
              height: 4,
              background: 'var(--sol-hch-bg)',
              marginRight: 6,
              verticalAlign: 'middle',
            }}
          />
          HC {`00:00 → ${hpStart}`}
        </span>
        <span style={{ color: 'var(--sol-hph-fg)', fontWeight: 600 }}>
          <span
            style={{
              display: 'inline-block',
              width: 10,
              height: 4,
              background: 'var(--sol-hph-bg)',
              marginRight: 6,
              verticalAlign: 'middle',
            }}
          />
          HP {`${hpStart} → ${hpEnd}`}
        </span>
        <span>
          <span
            style={{
              display: 'inline-block',
              width: 10,
              height: 4,
              background: 'var(--sol-hch-bg)',
              marginRight: 6,
              verticalAlign: 'middle',
            }}
          />
          HC {`${hpEnd} → 24:00`}
        </span>
      </div>

      {/* Caption prose + source chip */}
      <div
        style={{
          fontSize: 12.5,
          color: 'var(--sol-ink-500)',
          marginTop: 8,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          flexWrap: 'wrap',
        }}
      >
        {caption}
        {sourceChip && <span style={{ marginLeft: 'auto' }}>{sourceChip}</span>}
      </div>
    </div>
  );
}
