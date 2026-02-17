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
  const d = new Date(isoStr);
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

        // 1. Get suggested granularity
        let granularity = 'daily';
        try {
          const suggestion = await getEmsTimeseriesSuggest(
            dateFrom.toISOString(),
            dateTo.toISOString(),
          );
          granularity = suggestion?.granularity || 'daily';
        } catch {
          // fallback to daily
        }

        // 2. Build params
        const emsMode = MODE_MAP[mode] || 'aggregate';
        const params = {
          site_ids: siteIds.join(','),
          date_from: dateFrom.toISOString(),
          date_to: dateTo.toISOString(),
          granularity,
          mode: emsMode,
          metric: unit,
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
        const allValues = chartData.map(p => p.value).filter(v => v != null && !isNaN(v));
        const yMin = allValues.length ? Math.min(...allValues) : null;
        const yMax = allValues.length ? Math.max(...allValues) : null;

        const debugInfo = {
          endpoint: '/api/ems/timeseries',
          params,
          responseMs,
          seriesCount: series.length,
          pointsCount: chartData.length,
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
  }, [siteIds.join(','), energyType, days, startDate, endDate, unit, mode]); // eslint-disable-line react-hooks/exhaustive-deps

  return state;
}
