/**
 * PROMEOS — MeterBreakdownChart (Step 26)
 * Donut chart : répartition de la consommation entre sous-compteurs.
 * Affiche le delta (pertes & parties communes) comme tranche distincte.
 */
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];
const DELTA_COLOR = '#94a3b8';

export default function MeterBreakdownChart({ breakdown }) {
  if (!breakdown || !breakdown.sub_meters?.length) return null;

  const data = [
    ...breakdown.sub_meters.map((sm) => ({
      name: sm.name,
      value: Math.round(sm.kwh),
    })),
  ];

  if (breakdown.delta_kwh > 0) {
    data.push({
      name: breakdown.delta_label || 'Pertes & parties communes',
      value: Math.round(breakdown.delta_kwh),
    });
  }

  const total = breakdown.principal_kwh;

  return (
    <div className="w-full" data-testid="meter-breakdown-chart">
      <div className="text-xs text-gray-500 mb-2 text-center">
        Total principal :{' '}
        <span className="font-medium text-gray-700">
          {Math.round(total).toLocaleString('fr-FR')} kWh
        </span>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={80}
            paddingAngle={2}
            dataKey="value"
            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
            labelLine={false}
          >
            {data.map((_, i) => (
              <Cell
                key={i}
                fill={i < breakdown.sub_meters.length ? COLORS[i % COLORS.length] : DELTA_COLOR}
              />
            ))}
          </Pie>
          <Tooltip formatter={(value) => [`${value.toLocaleString('fr-FR')} kWh`, '']} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
