/**
 * PROMEOS — ProfileHeatmapTab
 * Tab 1: Heatmap 7×24 + daily profile (24pts) + baseload/peak/load_factor.
 */
import { memo, useMemo } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RTooltip,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardBody, Badge, KpiCard } from '../../ui';
import { fmtNum } from '../../utils/format';
import HeatmapLegend from './HeatmapLegend';

const DAY_LABELS = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];

function intensityColor(val, max) {
  if (!max || val === 0) return 'bg-gray-50';
  const ratio = val / max;
  if (ratio > 0.8) return 'bg-red-400 text-white';
  if (ratio > 0.6) return 'bg-orange-300';
  if (ratio > 0.4) return 'bg-amber-200';
  if (ratio > 0.2) return 'bg-yellow-100';
  return 'bg-green-50';
}

const HeatmapGrid = memo(function HeatmapGrid({ heatmap }) {
  const grid = useMemo(() => {
    const matrix = Array.from({ length: 7 }, () => Array(24).fill(0));
    let maxVal = 0;
    (heatmap || []).forEach((cell) => {
      const d = cell.day ?? 0;
      const h = cell.hour ?? 0;
      const v = cell.avg_kwh ?? 0;
      if (d < 7 && h < 24) {
        matrix[d][h] = v;
        if (v > maxVal) maxVal = v;
      }
    });
    return { matrix, maxVal };
  }, [heatmap]);

  return (
    <div className="overflow-x-auto">
      <div className="inline-grid gap-px" style={{ gridTemplateColumns: 'auto repeat(24, 1fr)' }}>
        {/* Header row */}
        <div className="w-10" />
        {Array.from({ length: 24 }, (_, h) => (
          <div key={h} className="text-[10px] text-gray-400 text-center w-7">
            {h}h
          </div>
        ))}
        {/* Data rows */}
        {grid.matrix.map((row, d) => (
          <>
            <div key={`l${d}`} className="text-xs text-gray-500 pr-1 flex items-center">
              {DAY_LABELS[d]}
            </div>
            {row.map((val, h) => (
              <div
                key={`${d}-${h}`}
                className={`w-7 h-5 rounded-sm ${intensityColor(val, grid.maxVal)}`}
                title={`${DAY_LABELS[d]} ${h}h — ${fmtNum(val, 1)} kWh`}
              />
            ))}
          </>
        ))}
      </div>
    </div>
  );
});

const DailyProfileChart = memo(function DailyProfileChart({ dailyProfile }) {
  const chartData = useMemo(
    () =>
      (dailyProfile || []).map((pt) => ({
        hour: `${pt.hour}h`,
        avg: pt.avg_kwh,
        min: pt.min_kwh,
        max: pt.max_kwh,
      })),
    [dailyProfile]
  );

  if (!chartData.length) return null;

  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="hour" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} unit=" kWh" />
        <RTooltip />
        <Area type="monotone" dataKey="max" stroke="none" fill="#fde68a" fillOpacity={0.4} />
        <Area type="monotone" dataKey="avg" stroke="#3b82f6" fill="#93c5fd" fillOpacity={0.5} />
        <Area type="monotone" dataKey="min" stroke="none" fill="#bbf7d0" fillOpacity={0.4} />
      </AreaChart>
    </ResponsiveContainer>
  );
});

export default function ProfileHeatmapTab({ profile, loading, schedule, stats, isExpert }) {
  if (loading)
    return (
      <Card>
        <CardBody>
          <div className="h-64 animate-pulse bg-gray-100 rounded" />
        </CardBody>
      </Card>
    );

  const {
    heatmap,
    daily_profile,
    baseload_kw,
    peak_kw,
    load_factor,
    total_kwh,
    confidence,
    readings_count,
  } = profile || {};

  return (
    <div className="space-y-6">
      {/* Heatmap */}
      <Card>
        <CardBody>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-700">Heatmap 7×24</h3>
            {confidence && (
              <Badge
                variant={
                  confidence === 'high' ? 'success' : confidence === 'medium' ? 'info' : 'neutral'
                }
              >
                {confidence === 'high'
                  ? 'Élevée'
                  : confidence === 'medium'
                    ? 'Moyenne'
                    : confidence === 'low'
                      ? 'Faible'
                      : confidence}
              </Badge>
            )}
          </div>
          <HeatmapLegend schedule={schedule} stats={stats} isExpert={isExpert} />
          <HeatmapGrid heatmap={heatmap} />
          <p className="text-xs text-gray-400 mt-2">
            {readings_count ?? 0} relevés · {total_kwh ?? 0} kWh total
          </p>
        </CardBody>
      </Card>

      {/* Daily profile chart */}
      <Card>
        <CardBody>
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Profil journalier (24h)</h3>
          <DailyProfileChart dailyProfile={daily_profile} />
        </CardBody>
      </Card>

      {/* Baseload / Peak / Load Factor */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KpiCard
          label="Talon (Q10)"
          value={`${baseload_kw ?? 0}`}
          suffix="kW"
          detail="Puissance min nuit jours ouvrés"
        />
        <KpiCard
          label="Pointe (P90)"
          value={`${peak_kw ?? 0}`}
          suffix="kW"
          detail="Puissance de pointe"
        />
        <KpiCard
          label="Facteur de charge"
          value={fmtNum((load_factor ?? 0) * 100, 1)}
          suffix="%"
          detail="Talon / Pointe"
        />
      </div>
    </div>
  );
}
