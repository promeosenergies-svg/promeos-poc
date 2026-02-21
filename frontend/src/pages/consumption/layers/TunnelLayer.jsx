/**
 * PROMEOS — TunnelLayer
 * Composable chart layer: P10-P90 envelope + P50 median.
 * Renders Recharts elements to be placed inside <ExplorerChart> or <ComposedChart>.
 *
 * Props:
 *   visible  {boolean}  show/hide the layer (default true)
 *   opacity  {number}   fill opacity for P10/P90 bands (default 0.2)
 *
 * Usage:
 *   <ExplorerChart data={...}>
 *     <TunnelLayer visible={layers.tunnel} />
 *   </ExplorerChart>
 *
 * Note: data must include p10, p25, p50, p75, p90 keys.
 */
import { Area, Line } from 'recharts';

export default function TunnelLayer({ visible = true, opacity = 0.2 }) {
  if (!visible) return null;

  return (
    <>
      {/* Outer band P10–P90 */}
      <Area
        type="monotone"
        dataKey="p90"
        stroke="#ef4444"
        fill="#fecaca"
        fillOpacity={opacity}
        name="P90"
        legendType="none"
      />
      <Area
        type="monotone"
        dataKey="p10"
        stroke="#6b7280"
        fill="#e5e7eb"
        fillOpacity={opacity}
        name="P10"
        legendType="none"
      />

      {/* Inner band P25–P75 */}
      <Area
        type="monotone"
        dataKey="p75"
        stroke="#f59e0b"
        fill="#fde68a"
        fillOpacity={opacity + 0.1}
        name="P75"
        legendType="none"
      />
      <Area
        type="monotone"
        dataKey="p25"
        stroke="#10b981"
        fill="#6ee7b7"
        fillOpacity={opacity + 0.1}
        name="P25"
        legendType="none"
      />

      {/* P50 median — dashed */}
      <Line
        type="monotone"
        dataKey="p50"
        stroke="#3b82f6"
        strokeWidth={2}
        strokeDasharray="5 3"
        dot={false}
        name="P50 (mediane)"
      />
    </>
  );
}
