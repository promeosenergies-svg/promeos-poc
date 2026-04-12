/**
 * ForecastCard — Prevision energetique J+1 a J+7.
 * Graphe en barres avec intervalle de confiance + temperature.
 * Display-only. Donnees de GET /api/analytics/sites/{id}/forecast.
 */

import { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { TrendingUp, Thermometer } from 'lucide-react';
import { getSiteForecast } from '../../services/api';

const DAY_LABELS_FR = ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'];

function formatDay(dateStr) {
  const d = new Date(dateStr + 'T00:00:00');
  const day = DAY_LABELS_FR[d.getDay()];
  return `${day} ${d.getDate()}/${d.getMonth() + 1}`;
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-xs">
      <p className="font-semibold text-gray-800">{d.label}</p>
      <p className="text-blue-600">
        Prevision : {Math.round(d.predicted_kwh).toLocaleString('fr-FR')} kWh
      </p>
      <p className="text-gray-400">
        IC : [{Math.round(d.confidence_low)}&ndash;{Math.round(d.confidence_high)}] kWh
      </p>
      <p className="text-orange-500">Temperature : {d.temperature_forecast}&deg;C</p>
      <p className="text-gray-400">{d.is_business_day ? 'Jour ouvre' : 'Weekend/ferie'}</p>
    </div>
  );
}

export default function ForecastCard({ siteId, preloadedData }) {
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
    getSiteForecast(siteId)
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
    return <div className="p-6 text-sm text-gray-400 animate-pulse">Calcul de la prevision...</div>;
  }
  if (!data || !data.forecast_days?.length) return null;

  const chartData = data.forecast_days.map((d) => ({
    ...d,
    label: formatDay(d.date),
    margin_low: d.predicted_kwh - d.confidence_low,
    margin_high: d.confidence_high - d.predicted_kwh,
  }));

  const avgKwh = data.avg_kwh_day;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TrendingUp size={16} className="text-blue-600" />
          <h3 className="text-base font-semibold text-gray-900">Prevision J+1 a J+7</h3>
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
                ? 'R2 > 0.6'
                : data.confidence_global === 'medium'
                  ? 'R2 0.3-0.6'
                  : 'Estimation'}
            </span>
          )}
        </div>
        <div className="text-right text-xs">
          <div className="font-semibold text-gray-800">
            {Math.round(data.total_kwh_7d).toLocaleString('fr-FR')} kWh / 7j
          </div>
          <div className="text-gray-400">
            Moy. {Math.round(avgKwh).toLocaleString('fr-FR')} kWh/j
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} barCategoryGap="20%">
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="label" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine y={avgKwh} stroke="#94a3b8" strokeDasharray="4 4" />
            <Bar
              dataKey="predicted_kwh"
              fill="#3b82f6"
              radius={[4, 4, 0, 0]}
              name="Prevision kWh"
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Temperature row */}
      <div className="flex items-center gap-1 text-[10px] text-gray-400 overflow-x-auto">
        <Thermometer size={10} className="shrink-0 text-orange-400" />
        {chartData.map((d) => (
          <span
            key={d.date}
            className="px-1.5 py-0.5 rounded bg-orange-50 text-orange-600 shrink-0"
          >
            {d.temperature_forecast}&deg;C
          </span>
        ))}
      </div>

      {/* Footer */}
      {data.signature && (
        <p className="text-[10px] text-gray-400">
          Methode : signature thermique (base {Math.round(data.signature.base_kwh)} kWh/j +{' '}
          {data.signature.a_heating?.toFixed(1)} kWh/DJU chaud +{' '}
          {data.signature.b_cooling?.toFixed(1)} kWh/DJU froid) &middot; R&sup2;{' '}
          {((data.signature.r2 || 0) * 100).toFixed(0)}%
        </p>
      )}
    </div>
  );
}
