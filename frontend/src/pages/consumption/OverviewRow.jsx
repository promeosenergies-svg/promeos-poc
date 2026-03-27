/**
 * PROMEOS — OverviewRow (Sprint V12-B)
 * Compact KPI row displayed above the chart.
 * Shows: total_kwh, avg_kwh, peak_kw, talon_kw, off_hours_pct, co2e_kg, eur_est
 * Supports optional delta vs previous period (Δ%).
 *
 * Props:
 *   data  { total_kwh, avg_kwh, peak_kw, talon_kw, off_hours_pct, co2e_kg, eur_est,
 *           delta_total_pct, delta_avg_pct }
 *   unit  'kwh' | 'kw' | 'eur'
 */

import { CO2E_FACTOR_KG_PER_KWH } from './constants';
import { fmtNum } from '../../utils/format';

const EUR_FACTOR = 0.068; // €/kWh — spot moyen 30j bridgé, aligné backend

function fmt(value, decimals = 0) {
  if (value == null || isNaN(value)) return null;
  return value.toLocaleString('fr-FR', { maximumFractionDigits: decimals });
}

function DeltaBadge({ pct }) {
  if (pct == null) return null;
  const pos = pct > 0;
  return (
    <span className={`ml-1 text-[10px] font-medium ${pos ? 'text-red-500' : 'text-green-600'}`}>
      {pos ? '+' : ''}
      {fmtNum(pct, 1)}%
    </span>
  );
}

export default function OverviewRow({ data, unit }) {
  if (!data) return null;

  const totalKwh = data.total_kwh ?? null;
  const avgKwh = data.avg_kwh ?? null;
  const peakKw = data.peak_kw ?? null;
  const talonKw = data.talon_kw ?? null;
  const offHours = data.off_hours_pct ?? null;
  const co2e = totalKwh != null ? totalKwh * CO2E_FACTOR_KG_PER_KWH : null;
  const eur = totalKwh != null ? totalKwh * EUR_FACTOR : null;

  const kpis = [
    totalKwh != null && {
      label: unit === 'eur' ? 'Total estimé' : 'Total',
      value: unit === 'eur' ? fmt(eur, 0) + ' €' : fmt(totalKwh, 0) + ' kWh',
      delta: data.delta_total_pct,
    },
    avgKwh != null && {
      label: 'Moyenne/j',
      value: fmt(avgKwh, 1) + ' kWh',
      delta: data.delta_avg_pct,
    },
    peakKw != null && {
      label: 'Pic',
      value: fmt(peakKw, 1) + ' kW',
    },
    talonKw != null && {
      label: 'Talon',
      value: fmt(talonKw, 1) + ' kW',
    },
    offHours != null && {
      label: 'Hors-horaires',
      value: fmt(offHours, 1) + ' %',
    },
    co2e != null && {
      label: 'CO₂e',
      value: fmt(co2e, 0) + ' kg',
    },
  ].filter(Boolean);

  if (!kpis.length) return null;

  return (
    <div
      className="flex flex-wrap gap-x-5 gap-y-1 px-1 py-2 rounded-lg bg-gray-50 border border-gray-100 text-xs"
      aria-label="Résumé de la période"
    >
      {kpis.map((k) => (
        <div key={k.label} className="flex flex-col">
          <span className="text-gray-400">{k.label}</span>
          <span className="font-semibold text-gray-700 whitespace-nowrap">
            {k.value}
            <DeltaBadge pct={k.delta} />
          </span>
        </div>
      ))}
    </div>
  );
}

/**
 * Compute OverviewRow data from tunnel data (single site or aggregated).
 * @param {object} tunnel — tunnel API response (or merged aggregate)
 * @returns {object} data for OverviewRow
 */
export function computeOverviewData(tunnel) {
  if (!tunnel) return null;
  const envelope = tunnel.envelope?.weekday || [];
  if (!envelope.length) return null;

  const p50Values = envelope.map((s) => s.p50 ?? 0).filter((v) => v > 0);
  const avgP50 = p50Values.length ? p50Values.reduce((a, b) => a + b, 0) / p50Values.length : null;
  const peakKw = p50Values.length ? Math.max(...p50Values) : null;

  // Talon: min hourly p50 (off-peak night hours 0-5)
  const nightSlots = envelope.filter((s) => s.hour >= 0 && s.hour < 6);
  const talonKw = nightSlots.length
    ? Math.min(...nightSlots.map((s) => s.p50 ?? Infinity).filter((v) => v < Infinity))
    : null;

  // total_kwh: sum of p50 * 24h per year approximation — use readings if available
  const totalKwh =
    tunnel.readings_count && avgP50
      ? avgP50 * 24 * (tunnel.readings_count / 48) // rough estimate from half-hourly readings
      : null;

  // avg per day
  const avgKwh = avgP50 ? avgP50 * 24 : null;

  // off-hours pct: fraction of consumption outside 8h-20h
  const daySlots = envelope.filter((s) => s.hour >= 8 && s.hour < 20);
  const nightSum = envelope
    .filter((s) => s.hour < 8 || s.hour >= 20)
    .reduce((s, slot) => s + (slot.p50 ?? 0), 0);
  const daySum = daySlots.reduce((s, slot) => s + (slot.p50 ?? 0), 0);
  const total = nightSum + daySum;
  const offHoursPct = total > 0 ? (nightSum / total) * 100 : null;

  return {
    total_kwh: totalKwh != null ? Math.round(totalKwh) : null,
    avg_kwh: avgKwh != null ? Math.round(avgKwh * 10) / 10 : null,
    peak_kw: peakKw != null ? Math.round(peakKw * 10) / 10 : null,
    talon_kw: talonKw != null && talonKw < Infinity ? Math.round(talonKw * 10) / 10 : null,
    off_hours_pct: offHoursPct != null ? Math.round(offHoursPct * 10) / 10 : null,
  };
}
