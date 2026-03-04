/**
 * PROMEOS — MeteoPanel (Sprint P1-3)
 * Consumption vs temperature overlay + DJU badge + Pearson correlation.
 *
 * - Left Y-axis: consumption (kWh, AreaChart)
 * - Right Y-axis: temperature (°C, dashed Line)
 * - DJU badge: sum of max(0, 18 - T) for each period
 * - Pearson R between consumption and temperature
 *
 * Temperature source:
 *   1) UTC hourly data from /api/ems/weather_hourly (DST-safe, all timestamps in Z)
 *   2) Fallback to synthetic (deterministic seasonal sine wave) if API unavailable
 *
 * Toggle "Afficher la température" controls weather visibility.
 *
 * Props:
 *   siteIds     — selected site IDs
 *   energyType  — 'electricity' | 'gas'
 *   days        — period in days (from main explorer state)
 */
import { useState, useMemo, useEffect } from 'react';
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Cloud, Thermometer } from 'lucide-react';
import useEmsTimeseries from './useEmsTimeseries';
import { getEmsWeatherHourly } from '../../services/api';

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
    <div className="bg-white/95 backdrop-blur border border-gray-200 rounded-xl shadow-lg px-3.5 py-2.5 text-xs min-w-[180px]">
      <p className="font-semibold text-gray-800 mb-1.5 pb-1 border-b border-gray-100">{label}</p>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center gap-2 py-0.5">
          <span
            className="w-2.5 h-2.5 shrink-0"
            style={{
              backgroundColor: p.color,
              borderRadius: p.dataKey === 'temp' ? '2px' : '50%',
            }}
          />
          <span className="text-gray-500">{p.name}</span>
          <span className="font-semibold text-gray-900 ml-auto pl-4 tabular-nums">
            {p.value != null
              ? Number(p.value).toLocaleString('fr-FR', { maximumFractionDigits: 1 })
              : '—'}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Main panel ────────────────────────────────────────────────────────────────

export default function MeteoPanel({ siteIds = [], energyType = 'electricity', days = 90 }) {
  const { status, chartData } = useEmsTimeseries({ siteIds, energyType, days });

  // P1-3: Toggle temperature visibility
  const [showTemp, setShowTemp] = useState(true);

  // P1-3: UTC weather from backend (DST-safe)
  const [utcWeather, setUtcWeather] = useState(null);

  useEffect(() => {
    if (!siteIds?.length) return;
    const siteId = siteIds[0];
    const now = new Date();
    const from = new Date(now.getTime() - days * 86400000);
    const dateFrom = from.toISOString().slice(0, 10);
    const dateTo = now.toISOString().slice(0, 10);
    getEmsWeatherHourly(siteId, dateFrom, dateTo)
      .then((res) => {
        // Build date→temp lookup from UTC hours
        const lookup = {};
        for (const h of res?.hours || []) {
          // Aggregate hourly to daily average for overlay
          const dayKey = h.t?.slice(0, 10);
          if (!dayKey) continue;
          if (!lookup[dayKey]) lookup[dayKey] = { sum: 0, count: 0 };
          lookup[dayKey].sum += h.temp_c;
          lookup[dayKey].count += 1;
        }
        const daily = {};
        for (const [k, v] of Object.entries(lookup)) {
          daily[k] = Math.round((v.sum / v.count) * 10) / 10;
        }
        setUtcWeather(daily);
      })
      .catch(() => setUtcWeather(null)); // Fallback to synthetic
  }, [siteIds, days]);

  // Enrich chartData with temperature — prefer UTC weather, fallback to synthetic
  const enrichedData = useMemo(() => {
    return chartData.map((p) => {
      let temp = null;
      // Use rawDate (ISO "YYYY-MM-DD HH:MM:SS") for matching against utcWeather keys
      const raw = p.rawDate || p.date;
      if (raw) {
        const dayKey = typeof raw === 'string' ? raw.replace('T', ' ').slice(0, 10) : null;
        if (utcWeather && dayKey && utcWeather[dayKey] != null) {
          temp = utcWeather[dayKey];
        } else {
          temp = Math.round(generateSyntheticTemp(raw) * 10) / 10;
        }
      }
      return { ...p, temp };
    });
  }, [chartData, utcWeather]);

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

  const absCorr = Math.abs(correlation);
  const correlationLabel = absCorr > 0.5 ? 'Forte' : absCorr > 0.2 ? 'Modérée' : 'Faible';
  const correlationDir =
    correlation < -0.15 ? 'Chauffage' : correlation > 0.15 ? 'Climatisation' : 'Neutre';
  // Okabe-Ito colorblind-safe: blue #0072B2 (strong), orange #E69F00 (moderate), gray (weak)
  const correlationColor =
    absCorr > 0.5
      ? 'ring-1'
      : absCorr > 0.2
        ? 'ring-1'
        : 'text-gray-600 bg-gray-100 ring-1 ring-gray-200';
  const correlationStyle =
    absCorr > 0.5
      ? { color: '#005a8e', backgroundColor: '#0072B210', borderColor: '#0072B240' }
      : absCorr > 0.2
        ? { color: '#b07d00', backgroundColor: '#E69F0015', borderColor: '#E69F0040' }
        : {};

  const isRealWeather = !!utcWeather;
  const _weatherSource = isRealWeather
    ? 'Temperature reelle (UTC)'
    : 'Temperature synthetique (modele)';

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
      {/* Header + badges + toggle */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h3 className="text-sm font-semibold text-gray-800">Influence climatique</h3>
          <p className="text-xs text-gray-500">Consommation vs temperature exterieure</p>
          <span
            className={`inline-flex items-center gap-1 mt-0.5 px-2 py-0.5 rounded-full text-[10px] font-medium ${isRealWeather ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'}`}
          >
            {isRealWeather ? 'Meteo reelle' : 'Meteo synthetique'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {/* P1-3: Temperature toggle */}
          <label className="flex items-center gap-1.5 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={showTemp}
              onChange={(e) => setShowTemp(e.target.checked)}
              className="w-3.5 h-3.5 rounded border-gray-300 text-amber-600 focus:ring-amber-500"
            />
            <Thermometer size={13} className="text-amber-600" />
            <span className="text-xs text-gray-600">Afficher la temperature</span>
          </label>
          <span className="text-xs text-gray-300">|</span>
          <span className="text-xs text-gray-500">DJU :</span>
          <span className="px-2 py-0.5 text-xs font-medium bg-indigo-50 text-indigo-700 rounded-full">
            {dju.toLocaleString('fr-FR')} °C·j
          </span>
          <span className="text-xs text-gray-500">Correlation :</span>
          <span
            className={`inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-semibold rounded-full ${correlationColor}`}
            style={correlationStyle}
          >
            {correlationLabel} · r={correlation >= 0 ? '+' : ''}
            {correlation.toFixed(2)}
            <span className="text-[10px] font-normal opacity-75">({correlationDir})</span>
          </span>
        </div>
      </div>

      {/* Dual-axis chart */}
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={enrichedData} margin={{ top: 10, right: 44, left: 4, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
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
            tick={{ fontSize: 11, fill: '#64748b' }}
            tickLine={false}
            axisLine={false}
            width={55}
            label={{
              value: 'kWh',
              angle: -90,
              position: 'insideLeft',
              fontSize: 10,
              fill: '#0072B2',
            }}
          />
          {/* Right Y: temperature — hidden when toggle off */}
          {showTemp && (
            <YAxis
              yAxisId="temp"
              orientation="right"
              tick={{ fontSize: 11, fill: '#64748b' }}
              tickLine={false}
              axisLine={false}
              width={42}
              label={{
                value: '°C',
                angle: 90,
                position: 'insideRight',
                fontSize: 10,
                fill: '#E69F00',
              }}
            />
          )}
          <Tooltip content={<MeteoTooltip />} />
          <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
          <Area
            yAxisId="kwh"
            type="monotone"
            dataKey="value"
            name="Consommation (kWh)"
            stroke="#0072B2"
            fill="#0072B2"
            fillOpacity={0.15}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 2, fill: '#fff' }}
          />
          {showTemp && (
            <Line
              yAxisId="temp"
              type="monotone"
              dataKey="temp"
              name="Température (°C)"
              stroke="#E69F00"
              strokeWidth={2.5}
              strokeDasharray="6 3"
              dot={false}
              activeDot={{ r: 4, strokeWidth: 2, fill: '#fff' }}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>

      {/* Interprétation + disclaimer */}
      <div className="flex items-start gap-2 p-2.5 rounded-lg bg-slate-50 border border-slate-100">
        <span className="text-xs text-slate-400 shrink-0 mt-0.5">ℹ</span>
        <div className="text-[11px] text-slate-500 leading-relaxed">
          <span className="font-medium text-slate-600">
            {absCorr > 0.5
              ? `Dépendance climatique forte (r=${correlation.toFixed(2)}) — la consommation est très sensible à la température.`
              : absCorr > 0.2
                ? `Dépendance climatique modérée (r=${correlation.toFixed(2)}) — influence partielle de la température.`
                : `Faible corrélation (r=${correlation.toFixed(2)}) — la consommation semble peu liée à la température.`}
          </span>
          <br />
          Source : {utcWeather ? 'météo réelle UTC' : 'modèle saisonnier synthétique'}
          {' · '}DJU base 18 °C · Coefficient de Pearson sur la période ({enrichedData.length} pts)
        </div>
      </div>
    </div>
  );
}
