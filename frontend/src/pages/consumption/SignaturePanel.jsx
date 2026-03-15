/**
 * PROMEOS — SignaturePanel (Sprint P1.1)
 * Heatmap weekday x hour showing average kWh consumption pattern.
 * Uses its own useEmsTimeseries call (hourly, 90 days) — independent of main granularity.
 * Reuses HeatmapChart from consumption/HeatmapChart.jsx.
 *
 * P1.1: FR labels (Jours ouvres / Week-ends), drill-down CTAs
 *   "Analyser ce creneau" → /diagnostic-conso?site_id=X
 *   "Voir facture" → deepLinkWithContext(siteId, month)
 *
 * Props:
 *   siteIds     — selected site IDs
 *   energyType  — 'electricity' | 'gas'
 */
import { useState, useMemo } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RTooltip,
  ResponsiveContainer,
} from 'recharts';
import useEmsTimeseries from './useEmsTimeseries';
import HeatmapChart from './HeatmapChart';
import { Card, CardBody } from '../../ui';
import { BarChart3, ArrowRight, FileText } from 'lucide-react';
import { deepLinkWithContext } from '../../services/deepLink';

// French weekday index: 0=Mon, 1=Tue, ..., 5=Sat, 6=Sun
// JS getDay(): 0=Sun, 1=Mon, ..., 6=Sat -> convert: frDay = (jsDay + 6) % 7
function toFrDay(jsDay) {
  return (jsDay + 6) % 7;
}

// HP = Heures Pleines (peak), HC = Heures Creuses (off-peak)
// Simplified French standard: HP on weekdays 6h-22h, HC otherwise
function getHpHc(frDay, hour) {
  const isWeekend = frDay >= 5; // Sam=5, Dim=6
  if (isWeekend) return 'HC';
  return hour >= 6 && hour < 22 ? 'HP' : 'HC';
}

/**
 * Aggregate raw series data into HeatmapChart format.
 * @param {Array} seriesData — raw series from useEmsTimeseries
 * @returns {Array<{day, hour, avg_kwh, period}>} — 7x24 cells (only non-zero)
 */
export function aggregateToHeatmap(seriesData) {
  if (!seriesData?.length || !seriesData[0]?.data?.length) return [];

  const matrix = {}; // `${frDay}-${hour}` -> { sum, count }

  for (const point of seriesData[0].data) {
    if (point.v == null || isNaN(point.v)) continue;

    // Normalize ISO string (some backends return "YYYY-MM-DD HH:MM:SS")
    const normalized = typeof point.t === 'string' ? point.t.replace(' ', 'T') : point.t;
    const d = new Date(normalized);
    if (isNaN(d.getTime())) continue;

    const frDay = toFrDay(d.getDay());
    const hour = d.getHours();
    const key = `${frDay}-${hour}`;

    if (!matrix[key]) matrix[key] = { sum: 0, count: 0 };
    matrix[key].sum += point.v;
    matrix[key].count += 1;
  }

  const cells = [];
  for (const [key, { sum, count }] of Object.entries(matrix)) {
    const [frDay, hour] = key.split('-').map(Number);
    const avg_kwh = count > 0 ? Math.round((sum / count) * 100) / 100 : 0;
    cells.push({
      day: frDay,
      hour,
      avg_kwh,
      period: getHpHc(frDay, hour),
    });
  }

  return cells;
}

export default function SignaturePanel({ siteIds = [], energyType = 'electricity', days = 90 }) {
  const { status, seriesData, meta } = useEmsTimeseries({
    siteIds,
    energyType,
    days,
    granularityOverride: 'hourly',
  });

  const heatmapData = useMemo(() => aggregateToHeatmap(seriesData), [seriesData]);

  // P1-2: Filter ouvres/week-ends + drill-down state
  const [dayFilter, setDayFilter] = useState('all');
  const [drillDown, setDrillDown] = useState(null);

  const primarySiteId = siteIds?.[0] || null;

  // Build drill-down chart data from raw series for clicked day+hour
  const drillDownData = useMemo(() => {
    if (!drillDown || !seriesData?.[0]?.data) return [];
    const points = [];
    for (const pt of seriesData[0].data) {
      if (pt.v == null) continue;
      const normalized = typeof pt.t === 'string' ? pt.t.replace(' ', 'T') : pt.t;
      const d = new Date(normalized);
      if (isNaN(d.getTime())) continue;
      const frDay = (d.getDay() + 6) % 7;
      const hour = d.getHours();
      if (frDay === drillDown.day && hour === drillDown.hour) {
        points.push({
          date: d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' }),
          rawDate: d.toISOString().slice(0, 7), // YYYY-MM for deep link
          kwh: Math.round(pt.v * 100) / 100,
        });
      }
    }
    return points;
  }, [drillDown, seriesData]);

  // Loading state
  if (status === 'loading') {
    return (
      <div className="space-y-2 animate-pulse">
        {[...Array(7)].map((_, i) => (
          <div key={i} className="flex gap-1">
            <div className="w-10 h-6 bg-gray-100 rounded" />
            {[...Array(24)].map((_, j) => (
              <div key={j} className="w-7 h-6 bg-gray-100 rounded" />
            ))}
          </div>
        ))}
      </div>
    );
  }

  // Empty or insufficient data
  if (status === 'empty' || heatmapData.length < 48) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="w-14 h-14 rounded-full bg-blue-50 flex items-center justify-center mb-4">
          <BarChart3 size={28} className="text-blue-400" />
        </div>
        <h3 className="text-base font-semibold text-gray-700 mb-1">
          Données insuffisantes pour la signature
        </h3>
        <p className="text-sm text-gray-500 max-w-xs">
          La signature horaire nécessite au moins 48 heures de données. Importez ou générez des
          données pour ce site.
        </p>
      </div>
    );
  }

  const totalPoints = meta?.n_points || heatmapData.length;

  // Most recent month from drillDownData for deep-link
  const drillMonth =
    drillDownData.length > 0 ? drillDownData[drillDownData.length - 1].rawDate : null;

  return (
    <div className="space-y-3">
      {/* Header + filter */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h3 className="text-sm font-semibold text-gray-800">Signature de consommation</h3>
          <p className="text-xs text-gray-500">
            Moyenne kWh par créneau horaire ({days} derniers jours)
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* P1-2: Day filter pills — FR labels */}
          {['all', 'weekday', 'weekend'].map((f) => (
            <button
              key={f}
              onClick={() => {
                setDayFilter(f);
                setDrillDown(null);
              }}
              className={`px-3 py-1 rounded-full text-xs font-medium transition ${
                dayFilter === f
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {f === 'all' ? 'Semaine typique' : f === 'weekday' ? 'Jours ouvres' : 'Week-ends'}
            </button>
          ))}
          <span className="text-xs text-gray-400 ml-2">
            {totalPoints.toLocaleString('fr-FR')} mesures
          </span>
        </div>
      </div>

      {/* Heatmap — now clickable */}
      <HeatmapChart data={heatmapData} unit="kWh" filter={dayFilter} onCellClick={setDrillDown} />

      {/* Drill-down chart for selected cell */}
      {drillDown && drillDownData.length > 0 && (
        <Card>
          <CardBody>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-semibold text-gray-700">
                Detail : {drillDown.dayLabel} {drillDown.hour}h ({drillDown.period})
              </h4>
              <button
                onClick={() => setDrillDown(null)}
                className="text-xs text-gray-400 hover:text-gray-600"
              >
                Fermer
              </button>
            </div>
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={drillDownData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 9 }}
                  angle={-30}
                  textAnchor="end"
                  height={40}
                />
                <YAxis
                  tick={{ fontSize: 10 }}
                  label={{
                    value: 'kWh',
                    angle: -90,
                    position: 'insideLeft',
                    style: { fontSize: 10 },
                  }}
                />
                <RTooltip />
                <Area type="monotone" dataKey="kwh" stroke="#3b82f6" fill="#dbeafe" name="kWh" />
              </AreaChart>
            </ResponsiveContainer>
            <p className="text-[10px] text-gray-400 mt-1">
              {drillDownData.length} points sur {days} jours pour {drillDown.dayLabel} a{' '}
              {drillDown.hour}h
            </p>

            {/* P1.1: Cross-brique CTAs */}
            <div className="flex items-center gap-3 mt-3 pt-3 border-t border-gray-100">
              {primarySiteId && (
                <a
                  href={`/diagnostic-conso?site_id=${primarySiteId}&hour=${drillDown.hour}&day_type=${drillDown.day < 5 ? 'weekday' : 'weekend'}`}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 rounded-lg hover:bg-blue-100 transition"
                >
                  <ArrowRight size={12} />
                  Analyser ce creneau
                </a>
              )}
              {primarySiteId && drillMonth && (
                <a
                  href={deepLinkWithContext(primarySiteId, drillMonth)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-50 rounded-lg hover:bg-gray-100 transition"
                >
                  <FileText size={12} />
                  Voir facture
                </a>
              )}
            </div>
          </CardBody>
        </Card>
      )}

      {drillDown && drillDownData.length === 0 && (
        <p className="text-xs text-gray-400 text-center py-4">Aucune donnée pour ce créneau.</p>
      )}

      {/* Legend note */}
      <p className="text-[11px] text-gray-400">
        HP = Heures Pleines (lun-ven 6h-22h) · HC = Heures Creuses (nuits + week-ends) · Intensite =
        consommation moyenne par creneau
      </p>
    </div>
  );
}
