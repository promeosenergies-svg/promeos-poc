/**
 * PROMEOS — ObjectivesLayer
 * Composable chart layer: monthly target reference lines + forecast area.
 * Renders Recharts elements for use inside <ExplorerChart> or <ComposedChart>.
 *
 * Props:
 *   targets  {object[]}  array of { month, target_kwh, actual_kwh }
 *   visible  {boolean}   show/hide the layer (default true)
 *   unit     {string}    kwh|kw|eur (for label formatting)
 *
 * Usage:
 *   <ExplorerChart data={chartData}>
 *     <ObjectivesLayer targets={targets} visible={layers.objectifs} unit={unit} />
 *   </ExplorerChart>
 */
import { ReferenceLine, Area } from 'recharts';

const UNIT_SUFFIX = { kwh: 'kWh', kw: 'kW', eur: 'EUR' };

export default function ObjectivesLayer({ targets = [], visible = true, unit = 'kwh' }) {
  if (!visible || !targets.length) return null;

  const suffix = UNIT_SUFFIX[unit] || 'kWh';

  // Compute average monthly target for reference line
  const targetsWithValues = targets.filter(t => t.target_kwh != null);
  const avgMonthlyTarget = targetsWithValues.length
    ? Math.round(targetsWithValues.reduce((s, t) => s + t.target_kwh, 0) / targetsWithValues.length)
    : null;

  // Identify future (forecast) months — months with no actual_kwh
  const currentMonth = new Date().getMonth() + 1;
  const forecastMonths = targets.filter(t => t.month > currentMonth && t.target_kwh != null);

  return (
    <>
      {/* Average target reference line */}
      {avgMonthlyTarget != null && (
        <ReferenceLine
          y={avgMonthlyTarget}
          stroke="#8b5cf6"
          strokeDasharray="6 3"
          strokeWidth={1.5}
          label={{
            value: `Obj. moy. ${avgMonthlyTarget.toLocaleString()} ${suffix}`,
            position: 'insideTopRight',
            style: { fontSize: 10, fill: '#8b5cf6' },
          }}
        />
      )}

      {/* Per-month target reference lines */}
      {targetsWithValues.map((t) => (
        <ReferenceLine
          key={`obj-${t.month}`}
          x={t.month}
          stroke="#c4b5fd"
          strokeDasharray="3 3"
          strokeWidth={1}
          label={{
            value: `${t.target_kwh.toLocaleString()}`,
            position: 'top',
            style: { fontSize: 9, fill: '#8b5cf6' },
          }}
        />
      ))}

      {/* Forecast area (future months lighter fill) */}
      {forecastMonths.length > 0 && (
        <Area
          type="monotone"
          dataKey="forecast_kwh"
          stroke="#a78bfa"
          fill="#ddd6fe"
          fillOpacity={0.3}
          name="Prevision"
          strokeDasharray="4 2"
        />
      )}
    </>
  );
}
