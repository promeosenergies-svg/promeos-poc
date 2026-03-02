/**
 * PROMEOS — InsightsPanel (Sprint V22)
 * Full-tab statistical analysis panel: P05 / P95 / load factor / anomalies.
 * Uses its own useEmsTimeseries call (daily, days prop) — independent of main granularity.
 *
 * Props:
 *   siteIds     {number[]}  — selected site IDs
 *   energyType  {string}    — 'electricity' | 'gas'
 *   days        {number}    — analysis window (default 90)
 */
import { useMemo } from 'react';
import { TrendingUp, TrendingDown, Zap, Activity, AlertTriangle, BarChart3 } from 'lucide-react';
import useEmsTimeseries from './useEmsTimeseries';

// ── Pure statistical helpers (exported for tests) ───────────────────────────

/**
 * Extract a flat array of valid numeric values from seriesData.
 * Filters null / NaN / undefined values.
 * @param {Array} seriesData — raw series from useEmsTimeseries
 * @returns {number[]}
 */
export function extractValues(seriesData) {
  if (!seriesData?.length) return [];
  const values = [];
  for (const series of seriesData) {
    for (const point of series.data || []) {
      if (point.v != null && !isNaN(point.v)) {
        values.push(point.v);
      }
    }
  }
  return values;
}

/**
 * Compute percentile from a sorted array (ascending).
 * @param {number[]} sorted — ascending sorted array
 * @param {number} p        — percentile 0–100
 * @returns {number}
 */
export function percentile(sorted, p) {
  if (!sorted.length) return 0;
  const idx = (p / 100) * (sorted.length - 1);
  const lo = Math.floor(idx);
  const hi = Math.ceil(idx);
  if (lo === hi) return sorted[lo];
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (idx - lo);
}

/**
 * Compute the 6 insight KPIs from raw series data.
 *
 * @param {Array}  seriesData — raw series from useEmsTimeseries
 * @param {number} days       — analysis window (for avg/day computation)
 * @returns {{
 *   total_kwh: number,
 *   avg_per_day: number,
 *   p95: number,
 *   p05: number,
 *   load_factor: number,
 *   anomaly_count: number,
 *   n_valid: number,
 * }}
 */
export function computeInsightKpis(seriesData, days) {
  const values = extractValues(seriesData);
  if (!values.length) {
    return { total_kwh: 0, avg_per_day: 0, p95: 0, p05: 0, load_factor: 0, anomaly_count: 0, n_valid: 0 };
  }

  const sorted = [...values].sort((a, b) => a - b);
  const total_kwh = values.reduce((s, v) => s + v, 0);
  const avg_per_day = days > 0 ? total_kwh / days : 0;
  const p95 = percentile(sorted, 95);
  const p05 = percentile(sorted, 5);
  // P99 threshold for anomaly detection
  const p99 = percentile(sorted, 99);
  const anomaly_threshold = p99 * 1.0;  // values above P99 are anomalies
  const anomaly_count = values.filter(v => v > anomaly_threshold && anomaly_threshold > 0).length;
  const load_factor = p95 > 0 ? (total_kwh / values.length) / p95 : 0;

  return {
    total_kwh: Math.round(total_kwh * 10) / 10,
    avg_per_day: Math.round(avg_per_day * 10) / 10,
    p95: Math.round(p95 * 10) / 10,
    p05: Math.round(p05 * 10) / 10,
    load_factor: Math.round(load_factor * 1000) / 1000,
    anomaly_count,
    n_valid: values.length,
  };
}

// ── KPI card ─────────────────────────────────────────────────────────────────

const u = (energyType) => energyType === 'gas' ? 'kWh PCS' : 'kWh';
const uDay = (energyType) => energyType === 'gas' ? 'kWh PCS/j' : 'kWh/j';
const uMwh = (energyType) => energyType === 'gas' ? 'MWh PCS' : 'MWh';

const KPI_CONFIG = [
  {
    id: 'total_kwh',
    label: 'Total consommé',
    icon: Zap,
    iconBg: 'bg-blue-50',
    iconText: 'text-blue-500',
    format: (v, et) => v >= 1000 ? `${(v / 1000).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} ${uMwh(et)}` : `${v.toLocaleString('fr-FR')} ${u(et)}`,
    sub: (_kpis) => `sur la période analysée`,
  },
  {
    id: 'avg_per_day',
    label: 'Moyenne / jour',
    icon: Activity,
    iconBg: 'bg-indigo-50',
    iconText: 'text-indigo-500',
    format: (v, et) => `${v.toLocaleString('fr-FR', { maximumFractionDigits: 1 })} ${uDay(et)}`,
    sub: () => `Consommation journalière moyenne`,
  },
  {
    id: 'p95',
    label: 'Pic P95',
    icon: TrendingUp,
    iconBg: 'bg-red-50',
    iconText: 'text-red-500',
    format: (v, et) => `${v.toLocaleString('fr-FR', { maximumFractionDigits: 1 })} ${u(et)}`,
    sub: () => `95e centile — pic de consommation`,
  },
  {
    id: 'p05',
    label: 'Talon P05',
    icon: TrendingDown,
    iconBg: 'bg-emerald-50',
    iconText: 'text-emerald-500',
    format: (v, et) => `${v.toLocaleString('fr-FR', { maximumFractionDigits: 1 })} ${u(et)}`,
    sub: () => `5e centile — consommation plancher`,
  },
  {
    id: 'load_factor',
    label: 'Facteur de charge',
    icon: BarChart3,
    iconBg: 'bg-amber-50',
    iconText: 'text-amber-500',
    format: (v) => `${(v * 100).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} %`,
    sub: (kpis) => kpis.load_factor < 0.5
      ? 'Usages intermittents (< 50 %)'
      : kpis.load_factor < 0.75
        ? 'Charge modérée (50–75 %)'
        : 'Charge élevée (> 75 %)',
  },
  {
    id: 'anomaly_count',
    label: 'Anomalies détectées',
    icon: AlertTriangle,
    iconBg: 'bg-orange-50',
    iconText: 'text-orange-500',
    format: (v) => v === 0 ? 'Aucune' : `${v} point${v > 1 ? 's' : ''}`,
    sub: () => 'Valeurs au-dessus du seuil P99',
  },
];

function KpiCard({ config, value, kpis, energyType }) {
  const Icon = config.icon;
  return (
    <div className="rounded-xl border border-gray-100 bg-white px-4 py-3 flex items-start gap-3 hover:shadow-sm transition-shadow">
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${config.iconBg}`}>
        <Icon size={18} className={config.iconText} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[10px] font-medium uppercase tracking-wider text-gray-400">{config.label}</p>
        <p className="text-lg font-bold text-gray-900 leading-tight truncate">{config.format(value, energyType)}</p>
        <p className="text-xs text-gray-500 mt-0.5 truncate">{config.sub(kpis)}</p>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function InsightsPanel({ siteIds = [], energyType = 'electricity', days = 90 }) {
  const { status, seriesData } = useEmsTimeseries({
    siteIds,
    energyType,
    days,
    granularityOverride: 'daily',
  });

  const kpis = useMemo(
    () => computeInsightKpis(seriesData, days),
    [seriesData, days],
  );

  // Loading state
  if (status === 'loading') {
    return (
      <div className="space-y-3 animate-pulse">
        <div className="h-5 bg-gray-100 rounded w-40" />
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="rounded-xl border border-gray-100 h-20 bg-gray-50" />
          ))}
        </div>
      </div>
    );
  }

  // Empty state
  if (status === 'empty' || kpis.n_valid === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="w-14 h-14 rounded-full bg-blue-50 flex items-center justify-center mb-4">
          <Activity size={28} className="text-blue-400" />
        </div>
        <h3 className="text-base font-semibold text-gray-700 mb-1">
          Données insuffisantes pour l'analyse
        </h3>
        <p className="text-sm text-gray-500 max-w-xs">
          Importez ou générez des données de consommation pour ce site afin d'obtenir l'analyse statistique.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-gray-800">Analyse statistique</p>
          <p className="text-xs text-gray-500 mt-0.5">
            {kpis.n_valid} points valides · période {days}j
          </p>
        </div>
        {kpis.anomaly_count > 0 && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-orange-50 border border-orange-200 rounded-lg">
            <AlertTriangle size={13} className="text-orange-500" />
            <span className="text-xs font-medium text-orange-700">
              {kpis.anomaly_count} anomalie{kpis.anomaly_count > 1 ? 's' : ''} détectée{kpis.anomaly_count > 1 ? 's' : ''}
            </span>
          </div>
        )}
      </div>

      {/* KPI grid */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        {KPI_CONFIG.map(cfg => (
          <KpiCard
            key={cfg.id}
            config={cfg}
            value={kpis[cfg.id]}
            kpis={kpis}
            energyType={energyType}
          />
        ))}
      </div>

      {/* Load factor interpretation bar */}
      <div className="rounded-xl border border-gray-100 bg-white px-4 py-3">
        <p className="text-xs font-medium text-gray-500 mb-2">Distribution de charge</p>
        <div className="relative h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="absolute left-0 top-0 h-full bg-blue-500 rounded-full transition-all"
            style={{ width: `${Math.min(100, kpis.load_factor * 100)}%` }}
          />
        </div>
        <div className="flex justify-between mt-1">
          <span className="text-[10px] text-gray-400">Talon</span>
          <span className="text-[10px] font-medium text-gray-600">
            Facteur {(kpis.load_factor * 100).toFixed(1)} %
          </span>
          <span className="text-[10px] text-gray-400">Pic</span>
        </div>
      </div>
    </div>
  );
}
