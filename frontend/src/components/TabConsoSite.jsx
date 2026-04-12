/**
 * PROMEOS — TabConsoSite
 * Onglet Consommation dans Site360 : mini-chart 30j + KPI strip
 * Remplace le TabStub "à venir"
 */
import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Zap, TrendingUp, Activity, Grid3X3 } from 'lucide-react';
import { Card, CardBody, EmptyState } from '../ui';
import { SkeletonCard } from '../ui/Skeleton';
import { getEmsTimeseries } from '../services/api';
import { fmtNum } from '../utils/format';
import CarpetPlot from './CarpetPlot';
import UsageBreakdownCard from './analytics/UsageBreakdownCard';
import UsageAnomaliesCard from './analytics/UsageAnomaliesCard';
import OptimizationPlanCard from './analytics/OptimizationPlanCard';

function formatDateLabel(isoStr) {
  if (!isoStr) return '';
  const normalized = typeof isoStr === 'string' ? isoStr.replace(' ', 'T') : isoStr;
  const d = new Date(normalized);
  if (isNaN(d.getTime())) return isoStr;
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' });
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-xs">
      <p className="font-medium text-gray-700 mb-1">{label}</p>
      <p className="text-blue-600">{fmtNum(payload[0].value, 0, 'kWh')}</p>
    </div>
  );
}

export default function TabConsoSite({ siteId }) {
  const navigate = useNavigate();
  const [status, setStatus] = useState('loading'); // loading | ready | empty | error
  const [rawSeries, setRawSeries] = useState([]);
  const [meta, setMeta] = useState(null);
  const [hourlyData, setHourlyData] = useState(null);
  const [hourlyStatus, setHourlyStatus] = useState('loading');

  useEffect(() => {
    if (!siteId) return;
    setStatus('loading');

    const dateTo = new Date();
    const dateFrom = new Date();
    dateFrom.setDate(dateFrom.getDate() - 30);

    getEmsTimeseries({
      site_ids: String(siteId),
      date_from: dateFrom.toISOString(),
      date_to: dateTo.toISOString(),
      granularity: 'daily',
      mode: 'aggregate',
      metric: 'kwh',
    })
      .then((res) => {
        const series = res?.series ?? [];
        setRawSeries(series);
        setMeta(res?.meta ?? null);
        const hasData = series.some((s) => s.data?.length > 0);
        setStatus(hasData ? 'ready' : 'empty');
      })
      .catch(() => setStatus('error'));
  }, [siteId]);

  useEffect(() => {
    if (!siteId) return;
    let stale = false;
    setHourlyStatus('loading');

    const dateTo = new Date();
    const dateFrom = new Date();
    dateFrom.setDate(dateFrom.getDate() - 30);

    getEmsTimeseries({
      site_ids: String(siteId),
      date_from: dateFrom.toISOString(),
      date_to: dateTo.toISOString(),
      granularity: 'hourly',
      mode: 'aggregate',
      metric: 'kwh',
    })
      .then((res) => {
        if (stale) return;
        const series = res?.series ?? [];
        const pts = series[0]?.data ?? [];
        setHourlyData(pts.length > 0 ? pts : null);
        setHourlyStatus(pts.length > 0 ? 'ready' : 'empty');
      })
      .catch(() => {
        if (!stale) setHourlyStatus('error');
      });
    return () => {
      stale = true;
    };
  }, [siteId]);

  const chartData = useMemo(() => {
    if (!rawSeries.length) return [];
    // Aggregate series : une seule série
    const mainSeries = rawSeries[0];
    if (!mainSeries?.data) return [];
    return mainSeries.data.map((pt) => ({
      date: formatDateLabel(pt.t),
      rawDate: pt.t,
      value: pt.v != null ? Math.round(pt.v) : null,
    }));
  }, [rawSeries]);

  const kpis = useMemo(() => {
    if (!chartData.length) return { totalKwh: 0, peakKwhDay: 0 };
    const totalKwh = chartData.reduce((sum, pt) => sum + (pt.value || 0), 0);
    // Pic journalier (kWh/jour max)
    const peakKwhDay = Math.max(...chartData.map((pt) => pt.value || 0));
    return { totalKwh, peakKwhDay };
  }, [chartData]);

  if (status === 'loading') {
    return (
      <div className="pt-6 space-y-4">
        <SkeletonCard lines={1} />
        <SkeletonCard lines={6} />
      </div>
    );
  }

  if (status === 'empty' || status === 'error') {
    return (
      <div className="pt-6">
        <EmptyState
          title="Consommation"
          text={
            status === 'error'
              ? 'Erreur lors du chargement des données de consommation.'
              : 'Aucune donnée de consommation disponible. Connectez un compteur pour visualiser les courbes.'
          }
        />
      </div>
    );
  }

  return (
    <div className="pt-6 space-y-4">
      {/* KPI strip */}
      <div className="grid grid-cols-2 gap-4">
        <div className="flex items-center gap-3 px-4 py-3 bg-blue-50 rounded-lg">
          <Zap size={18} className="text-blue-600" />
          <div>
            <p className="text-xs text-gray-500">Total 30 jours</p>
            <p className="text-sm font-bold text-gray-800">{fmtNum(kpis.totalKwh, 0, 'kWh')}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 px-4 py-3 bg-indigo-50 rounded-lg">
          <TrendingUp size={18} className="text-indigo-600" />
          <div>
            <p className="text-xs text-gray-500">Pic journalier</p>
            <p className="text-sm font-bold text-gray-800">{fmtNum(kpis.peakKwhDay, 0, 'kWh/j')}</p>
          </div>
        </div>
      </div>

      {/* Chart */}
      <Card>
        <CardBody>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Activity size={16} className="text-blue-600" />
              <h3 className="text-sm font-semibold text-gray-700">
                Consommation journalière — 30 derniers jours
              </h3>
            </div>
            {meta && (
              <span className="text-xs text-gray-400">
                {meta.n_meters ?? '?'} compteur{(meta.n_meters ?? 0) > 1 ? 's' : ''}
              </span>
            )}
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <defs>
                <linearGradient id="colorConso" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3B82F6" stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fill: '#6B7280' }}
                tickLine={false}
                axisLine={{ stroke: '#E5E7EB' }}
              />
              <YAxis
                tick={{ fontSize: 11, fill: '#6B7280' }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `${v}`}
                width={50}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="value"
                stroke="#3B82F6"
                strokeWidth={2}
                fill="url(#colorConso)"
                dot={false}
                activeDot={{ r: 4, stroke: '#3B82F6', strokeWidth: 2, fill: '#fff' }}
                connectNulls
              />
            </AreaChart>
          </ResponsiveContainer>
        </CardBody>
      </Card>

      {/* Carpet Plot — heatmap horaire */}
      <Card>
        <CardBody>
          <div className="flex items-center gap-2 mb-4">
            <Grid3X3 size={16} className="text-indigo-600" />
            <h3 className="text-sm font-semibold text-gray-700">
              Carpet plot — profil horaire 30 jours
            </h3>
          </div>
          {hourlyStatus === 'loading' ? (
            <SkeletonCard lines={4} />
          ) : hourlyStatus === 'ready' && hourlyData ? (
            <CarpetPlot data={hourlyData} days={30} />
          ) : (
            <div className="text-center py-6 text-gray-400 text-sm">
              Données horaires non disponibles pour ce site.
            </div>
          )}
        </CardBody>
      </Card>

      {/* Repartition par usage (CDC -> usages via 3 couches) */}
      <UsageBreakdownCard siteId={siteId} />

      {/* Anomalies par usage (croisement decomposition x seuils archetype) */}
      <UsageAnomaliesCard siteId={siteId} />

      {/* Plan d'optimisation ROI chiffre (etage 3) */}
      <OptimizationPlanCard siteId={siteId} />

      {/* CTA Explorer */}
      <div className="flex justify-end">
        <button
          onClick={() => navigate(`/consommations/explorer?sites=${siteId}`)}
          className="text-sm font-medium text-blue-600 hover:text-blue-800 hover:underline"
        >
          Explorer en détail →
        </button>
      </div>
    </div>
  );
}
