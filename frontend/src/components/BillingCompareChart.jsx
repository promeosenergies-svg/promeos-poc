/**
 * BillingCompareChart — Comparaison mensuelle N vs N-1
 * BarChart groupé (Recharts) : current_eur vs previous_eur par mois.
 */
import { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

const fmtK = (v) => {
  if (v == null) return '—';
  if (Math.abs(v) >= 1000) return `${(v / 1000).toFixed(1)} k€`;
  return `${v.toFixed(0)} €`;
};

function CompareTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-xs">
      <p className="font-medium text-gray-700 mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.name} : {fmtK(p.value)}
        </p>
      ))}
      {payload.length === 2 &&
        payload[0].value != null &&
        payload[1].value != null &&
        payload[1].value > 0 && (
          <p className="text-gray-500 mt-1 border-t border-gray-100 pt-1">
            Delta : {fmtK(payload[0].value - payload[1].value)} (
            {(((payload[0].value - payload[1].value) / payload[1].value) * 100).toFixed(1)}%)
          </p>
        )}
    </div>
  );
}

export default function BillingCompareChart({ data, currentYear, previousYear }) {
  const chartData = useMemo(() => {
    if (!data?.months) return [];
    return data.months.map((m) => ({
      label: m.label,
      current: m.current_eur,
      previous: m.previous_eur,
    }));
  }, [data]);

  if (!chartData.length) return null;

  const hasAnyData = chartData.some((d) => d.current != null || d.previous != null);
  if (!hasAnyData) return null;

  return (
    <div data-testid="billing-compare-chart">
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="label" tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={fmtK} tick={{ fontSize: 11 }} width={60} />
          <Tooltip content={<CompareTooltip />} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar
            dataKey="current"
            name={`${currentYear || 'N'}`}
            fill="#3b82f6"
            radius={[3, 3, 0, 0]}
            maxBarSize={32}
          />
          <Bar
            dataKey="previous"
            name={`${previousYear || 'N-1'}`}
            fill="#d1d5db"
            radius={[3, 3, 0, 0]}
            maxBarSize={32}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
