/**
 * UsageBreakdownCard — Decomposition CDC en usages.
 *
 * Display-only. Toutes les valeurs viennent de GET /api/analytics/sites/{id}/usage-breakdown
 * Le donut montre la repartition %, la table les details par usage.
 */

import { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { getUsageBreakdown } from '../../services/api';

const COLORS = [
  '#3b82f6', // blue-500  — CVC
  '#f59e0b', // amber-500 — Eclairage
  '#8b5cf6', // violet-500 — IT
  '#10b981', // emerald-500 — ECS
  '#ef4444', // red-500 — Froid
  '#6366f1', // indigo-500 — IRVE
  '#ec4899', // pink-500 — Process
  '#14b8a6', // teal-500 — Pompes
  '#64748b', // slate-500 — Securite
  '#a855f7', // purple-500 — Data center
  '#78716c', // stone-500 — Autres
];

const CONFIDENCE_BADGE = {
  high: { label: 'Mesure', bg: 'bg-green-100', text: 'text-green-700' },
  medium: { label: 'Estime', bg: 'bg-blue-100', text: 'text-blue-700' },
  low: { label: 'Approx', bg: 'bg-gray-100', text: 'text-gray-500' },
};

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-xs">
      <p className="font-semibold text-gray-800">{d.label}</p>
      <p className="text-gray-600">
        {d.pct}% — {Math.round(d.kwh).toLocaleString('fr-FR')} kWh
      </p>
      <p className="text-gray-400">{d.method}</p>
    </div>
  );
}

export default function UsageBreakdownCard({ siteId, preloadedData }) {
  const [data, setData] = useState(preloadedData || null);
  const [loading, setLoading] = useState(!preloadedData);

  useEffect(() => {
    if (preloadedData) {
      setData(preloadedData);
      setLoading(false);
      return;
    }
    if (!siteId) return;
    setLoading(true);
    setData(null);
    let stale = false;
    getUsageBreakdown(siteId)
      .then((d) => {
        if (!stale) setData(d);
      })
      .catch(() => {
        if (!stale) setData(null);
      })
      .finally(() => {
        if (!stale) setLoading(false);
      });
    return () => {
      stale = true;
    };
  }, [siteId, preloadedData]);

  if (loading) {
    return (
      <div className="p-6 text-sm text-gray-400 animate-pulse">Analyse des usages en cours...</div>
    );
  }

  if (!data || !data.usages?.length) return null;

  const usages = data.usages;
  const chartData = usages.map((u, i) => ({
    name: u.code,
    label: u.label,
    value: u.pct,
    kwh: u.kwh,
    pct: u.pct,
    method: u.method,
    confidence: u.confidence,
    fill: COLORS[i % COLORS.length],
  }));

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-gray-900">Repartition par usage</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            {Math.round(data.total_kwh).toLocaleString('fr-FR')} kWh sur la periode
            {data.archetype_code !== 'DEFAULT' && (
              <> &middot; {data.archetype_code.replace(/_/g, ' ').toLowerCase()}</>
            )}
          </p>
        </div>
        {data.confidence_global && (
          <span
            className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
              data.confidence_global === 'high'
                ? 'bg-green-100 text-green-700'
                : data.confidence_global === 'medium'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-500'
            }`}
          >
            {data.confidence_global === 'high'
              ? 'Confiance haute'
              : data.confidence_global === 'medium'
                ? 'Confiance moyenne'
                : 'Estimation'}
          </span>
        )}
      </div>

      {/* Donut + Legend */}
      <div className="flex items-start gap-6">
        {/* Donut */}
        <div className="w-44 h-44 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={45}
                outerRadius={70}
                paddingAngle={2}
                dataKey="value"
                strokeWidth={0}
              >
                {chartData.map((entry, i) => (
                  <Cell key={entry.name} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Table */}
        <div className="flex-1 min-w-0">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-gray-400 border-b border-gray-100">
                <th className="text-left py-1.5 font-medium">Usage</th>
                <th className="text-right py-1.5 font-medium">kWh</th>
                <th className="text-right py-1.5 font-medium">%</th>
                <th className="text-right py-1.5 font-medium">Source</th>
              </tr>
            </thead>
            <tbody>
              {usages.map((u, i) => {
                const badge = CONFIDENCE_BADGE[u.confidence] || CONFIDENCE_BADGE.low;
                return (
                  <tr key={u.code} className="border-b border-gray-50 last:border-0">
                    <td className="py-1.5">
                      <div className="flex items-center gap-1.5">
                        <span
                          className="w-2.5 h-2.5 rounded-full shrink-0"
                          style={{ backgroundColor: COLORS[i % COLORS.length] }}
                        />
                        <span className="text-gray-800 truncate">{u.label}</span>
                      </div>
                    </td>
                    <td className="text-right text-gray-600 tabular-nums">
                      {Math.round(u.kwh).toLocaleString('fr-FR')}
                    </td>
                    <td className="text-right text-gray-800 font-medium tabular-nums">{u.pct}%</td>
                    <td className="text-right">
                      <span
                        className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium ${badge.bg} ${badge.text}`}
                      >
                        {badge.label}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Footer methode */}
      <p className="text-[10px] text-gray-400">
        Methode :{' '}
        {data.method === '3_layer_decomposition'
          ? 'DJU + temporel + archetype (3 couches)'
          : data.method === 'archetype_only'
            ? 'Estimation par archetype (pas de CDC)'
            : data.method}
        {data.thermal_signature?.r2 != null && (
          <> &middot; R&sup2; signature DJU : {(data.thermal_signature.r2 * 100).toFixed(0)}%</>
        )}
      </p>
    </div>
  );
}
