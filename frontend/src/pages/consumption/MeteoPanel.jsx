/**
 * PROMEOS — MeteoPanel (Sprint V21)
 * Consumption vs synthetic temperature overlay + DJU badge + Pearson correlation.
 *
 * - Left Y-axis: consumption (kWh, AreaChart)
 * - Right Y-axis: synthetic temperature (°C, dashed Line)
 * - DJU badge: sum of max(0, 18 - T) for each period
 * - Pearson R between consumption and temperature
 *
 * Temperature is synthetic (deterministic seasonal sine wave) — no external API needed.
 *
 * Props:
 *   siteIds     — selected site IDs
 *   energyType  — 'electricity' | 'gas'
 *   days        — period in days (from main explorer state)
 */
import { useMemo } from 'react';
import {
  ComposedChart, Area, Line,
  XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { Cloud } from 'lucide-react';
import useEmsTimeseries from './useEmsTimeseries';

// ── Synthetic temperature (deterministic, no external API) ────────────────────

/**
 * Generate synthetic outside temperature for a date string.
 * Sine wave: peak ~25°C in summer (July 15 ≈ day 196), trough ~3°C in winter.
 * @param {string} dateStr — any date string parseable by Date
 * @returns {number} temperature in °C
 */
export function generateSyntheticTemp(dateStr) {
  if (!dateStr) return 14;
  const d = new Date(typeof dateStr === 'string' ? dateStr.replace(' ', 'T') : dateStr);
  if (isNaN(d.getTime())) return 14;
  const start = new Date(d.getFullYear(), 0, 0);
  const dayOfYear = Math.floor((d - start) / 86400000);
  // Cosine: peak at day 196 (July 15), trough at day 0/365
  return 14 + 11 * Math.cos((2 * Math.PI * (dayOfYear - 196)) / 365);
}

/**
 * Compute Pearson correlation coefficient between two numeric arrays.
 * Returns 0 if any array is empty or variance is zero.
 * @param {number[]} xs
 * @param {number[]} ys
 * @returns {number} r ∈ [-1, 1]
 */
export function computeCorrelation(xs, ys) {
  if (!xs?.length || xs.length !== ys?.length) return 0;
  const n = xs.length;
  const mx = xs.reduce((a, b) => a + b, 0) / n;
  const my = ys.reduce((a, b) => a + b, 0) / n;
  const cov = xs.reduce((s, x, i) => s + (x - mx) * (ys[i] - my), 0) / n;
  const sx = Math.sqrt(xs.reduce((s, x) => s + (x - mx) ** 2, 0) / n);
  const sy = Math.sqrt(ys.reduce((s, y) => s + (y - my) ** 2, 0) / n);
  if (sx === 0 || sy === 0) return 0;
  return Math.max(-1, Math.min(1, cov / (sx * sy)));
}

// ── Custom tooltip ────────────────────────────────────────────────────────────

function MeteoTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm px-3 py-2 text-xs">
      <p className="font-medium text-gray-700 mb-1">{label}</p>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: p.color }} />
          <span className="text-gray-500">{p.name}</span>
          <span className="font-medium text-gray-800 ml-auto pl-4">
            {p.value != null ? Number(p.value).toLocaleString('fr-FR', { maximumFractionDigits: 1 }) : '—'}
            {p.dataKey === 'temp' ? ' °C' : ' kWh'}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Main panel ────────────────────────────────────────────────────────────────

export default function MeteoPanel({ siteIds = [], energyType = 'electricity', days = 90 }) {
  const { status, chartData } = useEmsTimeseries({ siteIds, energyType, days });

  // Enrich chartData with synthetic temperature
  const enrichedData = useMemo(() => {
    return chartData.map((p) => ({
      ...p,
      temp: p.date ? Math.round(generateSyntheticTemp(p.date) * 10) / 10 : null,
    }));
  }, [chartData]);

  // DJU computation (base 18°C): sum of max(0, 18 - T) per period
  const dju = useMemo(() => {
    return Math.round(
      enrichedData.reduce((sum, p) => sum + (p.temp != null ? Math.max(0, 18 - p.temp) : 0), 0)
    );
  }, [enrichedData]);

  // Pearson correlation between consumption and temperature
  const correlation = useMemo(() => {
    const validPairs = enrichedData.filter((p) => p.value != null && p.temp != null);
    const cons = validPairs.map((p) => p.value);
    const temps = validPairs.map((p) => p.temp);
    return computeCorrelation(cons, temps);
  }, [enrichedData]);

  const correlationLabel = correlation > 0.5 ? 'Forte' : correlation > 0.2 ? 'Modérée' : 'Faible';
  const correlationColor = correlation > 0.5 ? 'text-blue-700 bg-blue-50' : correlation > 0.2 ? 'text-amber-700 bg-amber-50' : 'text-gray-600 bg-gray-100';

  // Loading state
  if (status === 'loading') {
    return (
      <div className="space-y-3 animate-pulse">
        <div className="flex gap-3">
          <div className="h-8 w-24 bg-gray-100 rounded-lg" />
          <div className="h-8 w-32 bg-gray-100 rounded-lg" />
        </div>
        <div className="h-64 bg-gray-100 rounded-xl" />
      </div>
    );
  }

  // Empty state
  if (status === 'empty' || !enrichedData.length) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="w-14 h-14 rounded-full bg-blue-50 flex items-center justify-center mb-4">
          <Cloud size={28} className="text-blue-400" />
        </div>
        <h3 className="text-base font-semibold text-gray-700 mb-1">
          Données de consommation manquantes
        </h3>
        <p className="text-sm text-gray-500 max-w-xs">
          Importez ou générez des données de consommation pour afficher l'analyse climatique.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Header + badges */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h3 className="text-sm font-semibold text-gray-800">Influence climatique</h3>
          <p className="text-xs text-gray-500">Consommation vs température extérieure (synthétique)</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">DJU :</span>
          <span className="px-2 py-0.5 text-xs font-medium bg-indigo-50 text-indigo-700 rounded-full">
            {dju.toLocaleString('fr-FR')} °C·j
          </span>
          <span className="text-xs text-gray-500">Corrélation :</span>
          <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${correlationColor}`}>
            {correlationLabel} ({correlation >= 0 ? '+' : ''}{correlation.toFixed(2)})
          </span>
        </div>
      </div>

      {/* Dual-axis chart */}
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={enrichedData} margin={{ top: 8, right: 40, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: '#94a3b8' }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          {/* Left Y: consumption */}
          <YAxis
            yAxisId="kwh"
            orientation="left"
            tick={{ fontSize: 11, fill: '#94a3b8' }}
            tickLine={false}
            axisLine={false}
            width={50}
            label={{ value: 'kWh', angle: -90, position: 'insideLeft', fontSize: 10, fill: '#94a3b8' }}
          />
          {/* Right Y: temperature */}
          <YAxis
            yAxisId="temp"
            orientation="right"
            tick={{ fontSize: 11, fill: '#60a5fa' }}
            tickLine={false}
            axisLine={false}
            width={40}
            label={{ value: '°C', angle: 90, position: 'insideRight', fontSize: 10, fill: '#60a5fa' }}
          />
          <Tooltip content={<MeteoTooltip />} />
          <Legend
            iconType="circle"
            iconSize={8}
            wrapperStyle={{ fontSize: 11 }}
          />
          <Area
            yAxisId="kwh"
            type="monotone"
            dataKey="value"
            name="Consommation"
            stroke="#6366f1"
            fill="#e0e7ff"
            fillOpacity={0.6}
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 3 }}
          />
          <Line
            yAxisId="temp"
            type="monotone"
            dataKey="temp"
            name="Température"
            stroke="#60a5fa"
            strokeWidth={1.5}
            strokeDasharray="4 2"
            dot={false}
            activeDot={{ r: 3 }}
          />
        </ComposedChart>
      </ResponsiveContainer>

      {/* Disclaimer */}
      <p className="text-[11px] text-gray-400">
        Température synthétique (modèle saisonnier) · DJU base 18 °C · R de Pearson sur la période
      </p>
    </div>
  );
}
