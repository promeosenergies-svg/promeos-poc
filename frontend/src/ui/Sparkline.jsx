/**
 * PROMEOS — Step 33 : Mini sparkline (Recharts LineChart).
 * Compact (120x40 par defaut), sans axes ni labels.
 * Dernier point = dot visible. Tooltip au survol.
 */
import { LineChart, Line, Tooltip, ResponsiveContainer } from 'recharts';

function SparklineTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-gray-800 text-white text-[10px] px-2 py-1 rounded shadow">
      {d.label || d.month} : {d.value}/100
    </div>
  );
}

export default function Sparkline({
  data = [],
  color = '#3b82f6',
  width = 120,
  height = 40,
  showDot = true,
}) {
  if (!data.length) return null;

  // Ensure data has "value" key
  const chartData = data.map((d, i) => ({
    ...d,
    value: d.value ?? d.score ?? 0,
    label: d.label || d.month || `${i + 1}`,
  }));

  return (
    <div style={{ width, height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 2, right: 4, bottom: 2, left: 4 }}>
          <Tooltip content={<SparklineTooltip />} cursor={false} />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            dot={false}
            activeDot={showDot ? { r: 3, fill: color } : false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
