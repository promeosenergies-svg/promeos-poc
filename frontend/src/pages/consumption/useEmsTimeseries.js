/**
 * PROMEOS — useEmsTimeseries (Sprint V14.3)
 * Hook wrapping /api/ems/timeseries for the Consumption Explorer.
 * Handles date computation, granularity suggestion, series → Recharts mapping.
 *
 * Returns: { status, chartData, seriesData, meta, granularity, error, debugInfo }
 *   status: 'loading' | 'ready' | 'empty' | 'error'
 *   chartData: [{ date: string, value: number|null, ...per-site keys }]
 *   seriesData: raw series array from API
 *   meta: { granularity, n_points, n_meters, date_from, date_to, metric }
 *   granularity: effective granularity string
 *   error: error message or null
 *   debugInfo: { endpoint, params, responseMs, seriesCount, pointsCount, yMin, yMax }
 */
import { useState, useEffect } from 'react';
import { getEmsTimeseries, getEmsTimeseriesSuggest } from '../../services/api';

// ── Mode mapping: PROMEOS UI → EMS API ────────────────────────────────────────

export const MODE_MAP = {
  agrege:   'aggregate',
  superpose: 'overlay',
  empile:   'stack',
  separe:   'split',
};

// ── Date formatting by granularity (French) ───────────────────────────────────

export function formatDate(isoStr, granularity) {
  if (!isoStr) return '';
  // V20-B (RC2): normalize "YYYY-MM-DD HH:MM:SS" (space) to ISO 8601 "YYYY-MM-DDTHH:MM:SS"
  // Some browsers fail to parse space-separated datetime strings.
  const normalized = typeof isoStr === 'string' ? isoStr.replace(' ', 'T') : isoStr;
  const d = new Date(normalized);
  if (isNaN(d.getTime())) return isoStr;

  if (granularity === 'monthly') {
    return d.toLocaleDateString('fr-FR', { month: 'short', year: '2-digit' });
  }
  if (granularity === 'daily') {
    return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' });
  }
  if (granularity === 'hourly') {
    return d.toLocaleString('fr-FR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
  }
  // 15min / 30min
  return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}

// ── Date computation from `days` ───────────────────────────────────────────────

function computeDateRange(days, startDate, endDate) {
  const dateTo = new Date();
  dateTo.setSeconds(0, 0);

  if (startDate && endDate) {
    return { dateFrom: new Date(startDate), dateTo: new Date(endDate) };
  }

  if (days === 'ytd') {
    const dateFrom = new Date(dateTo.getFullYear(), 0, 1);
    return { dateFrom, dateTo };
  }

  const dateFrom = new Date(dateTo);
  dateFrom.setDate(dateFrom.getDate() - Number(days));
  return { dateFrom, dateTo };
}

// ── Map multi-series overlay to chartData ─────────────────────────────────────

function seriesToChartData(series, granularity) {
  if (!series || series.length === 0) return [];

  if (series.length === 1) {
    // Single aggregate series
    return series[0].data.map(p => ({
      date: formatDate(p.t, granularity),
      value: p.v ?? null,
    }));
  }

  // Multi-series (overlay/superpose): merge by timestamp
  const byTs = {};
  for (const s of series) {
    for (const p of s.data) {
      const dateKey = formatDate(p.t, granularity);
      if (!byTs[dateKey]) byTs[dateKey] = { date: dateKey };
      byTs[dateKey][s.key] = p.v ?? null;
      // Also store as 'value' for first series (backward compat)
      if (series.indexOf(s) === 0) byTs[dateKey].value = p.v ?? null;
    }
  }
  return Object.values(byTs);
}

// ── Main hook ──────────────────────────────────────────────────────────────────

export default function useEmsTimeseries({
  siteIds = [],
  energyType = 'electricity',
  days = 30,
  startDate = null,
  endDate = null,
  unit = 'kwh',
  mode = 'agrege',
  granularityOverride = null,  // V21-C: user-selected granularity ('30min'|'hourly'|'daily'|'monthly') or null for auto
} = {}) {
  const [state, setState] = useState({
    status: 'loading',
    chartData: [],
    seriesData: [],
    meta: null,
    granularity: 'daily',
    error: null,
    debugInfo: null,
  });

  useEffect(() => {
    if (!siteIds.length) {
      setState(s => ({ ...s, status: 'empty', chartData: [], seriesData: [] }));
      return;
    }

    let cancelled = false;
    const t0 = Date.now();

    setState(s => ({ ...s, status: 'loading' }));

    async function fetchData() {
      try {
        const { dateFrom, dateTo } = computeDateRange(days, startDate, endDate);

        // 1. Get granularity: use override if provided, else auto-suggest
        let granularity = 'daily';
        if (granularityOverride && granularityOverride !== 'auto') {
          granularity = granularityOverride;
        } else {
          try {
            const suggestion = await getEmsTimeseriesSuggest(
              dateFrom.toISOString(),
              dateTo.toISOString(),
            );
            granularity = suggestion?.granularity || 'daily';
          } catch {
            // fallback to daily
          }
        }

        // 2. Build params
        const emsMode = MODE_MAP[mode] || 'aggregate';
        // V19-D: EUR is display-only; API only accepts 'kwh' | 'kw'
        const apiMetric = unit === 'eur' ? 'kwh' : unit;
        const params = {
          site_ids: siteIds.join(','),
          date_from: dateFrom.toISOString(),
          date_to: dateTo.toISOString(),
          granularity,
          mode: emsMode,
          metric: apiMetric,
          energy_vector: energyType,
        };

        // 3. Fetch timeseries
        const result = await getEmsTimeseries(params);
        const responseMs = Date.now() - t0;

        if (cancelled) return;

        const series = result?.series || [];
        const meta = result?.meta || null;
        const chartData = seriesToChartData(series, granularity);

        // Compute debug info
        const rawValues = chartData.map(p => p.value);
        const allValidValues = rawValues.filter(v => v != null && !isNaN(v));
        const yMin = allValidValues.length ? Math.min(...allValidValues) : null;
        const yMax = allValidValues.length ? Math.max(...allValidValues) : null;

        // V20-A: validity breakdown for debug
        const validCount = allValidValues.length;
        const zerosCount = rawValues.filter(v => v === 0).length;
        const nullsCount = rawValues.filter(v => v === null || v === undefined).length;
        const nanCount = rawValues.filter(v => v != null && typeof v === 'number' && isNaN(v)).length;

        const debugInfo = {
          endpoint: '/api/ems/timeseries',
          params,
          responseMs,
          seriesCount: series.length,
          pointsCount: chartData.length,
          validCount,       // V20-A: non-null, non-NaN values
          zerosCount,       // V20-A: 0 values (valid! must not be dropped)
          nullsCount,       // V20-A: null/undefined values
          nanCount,         // V20-A: NaN values
          samplePoints: chartData.slice(0, 5),  // V20-A: first 5 raw points for inspection
          yMin,
          yMax,
          xRange: chartData.length
            ? [chartData[0].date, chartData[chartData.length - 1].date]
            : null,
        };

        const status = series.length === 0 ? 'empty' : 'ready';

        setState({
          status,
          chartData,
          seriesData: series,
          meta,
          granularity,
          error: null,
          debugInfo,
        });
      } catch (err) {
        if (cancelled) return;
        setState(s => ({
          ...s,
          status: 'error',
          error: err?.message || 'Erreur de chargement des données',
          debugInfo: { endpoint: '/api/ems/timeseries', responseMs: Date.now() - t0, error: err?.message },
        }));
      }
    }

    fetchData();
    return () => { cancelled = true; };
  }, [siteIds.join(','), energyType, days, startDate, endDate, unit, mode, granularityOverride]); // eslint-disable-line react-hooks/exhaustive-deps

  return state;
}
