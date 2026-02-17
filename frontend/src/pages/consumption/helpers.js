/**
 * PROMEOS — Consumption Explorer helpers (pure, testable)
 * V11: computeGranularity, computeAutoRange, classifyEmptyReason
 * WoW: aggregateSeries, convertUnit, colorForSite
 */

/**
 * Auto-granularity from period length.
 * @param {number} days
 * @returns {'30min'|'1h'|'jour'|'semaine'}
 */
export function computeGranularity(days) {
  if (days <= 7) return '30min';
  if (days <= 30) return '1h';
  if (days <= 180) return 'jour';
  return 'semaine';
}

/**
 * Auto-range from availability first/last timestamps.
 * @param {string|null} firstTs
 * @param {string|null} lastTs
 * @returns {number} days
 */
export function computeAutoRange(firstTs, lastTs) {
  if (!firstTs || !lastTs) return 90;
  const span = Math.ceil((new Date(lastTs) - new Date(firstTs)) / (1000 * 60 * 60 * 24));
  if (span < 30) return 30;
  if (span < 90) return Math.min(span, 60);
  return 90;
}

/**
 * Classify the primary reason from availability response.
 * @param {object|null} availability
 * @returns {string}
 */
export function classifyEmptyReason(availability) {
  if (!availability) return 'loading';
  if (availability.has_data) return 'has_data';
  if (!availability.reasons?.length) return 'unknown';
  return availability.reasons[0];
}

// ── Multi-site helpers (WoW) ──────────────────────────────────────────────

/**
 * Merge/stack series data from multiple sites according to display mode.
 * Each site's data is an array of { date, kwh } or { hour, p50, ... }.
 *
 * @param {Record<string, object[]>} seriesBySite  — { siteId: dataArray }
 * @param {'agrege'|'superpose'|'empile'|'separe'} mode
 * @returns {object[]} merged data array (for agrege: summed; for others: per-site keys)
 */
export function aggregateSeries(seriesBySite, mode) {
  const entries = Object.entries(seriesBySite || {});
  if (!entries.length) return [];
  if (mode === 'agrege') {
    // Sum all sites by index position
    const base = entries[0][1] || [];
    return base.map((point, i) => {
      const sum = entries.reduce((acc, [, series]) => acc + (series[i]?.kwh ?? series[i]?.p50 ?? 0), 0);
      return { ...point, kwh: sum, p50: sum };
    });
  }
  // For superpose / empile / separe: attach per-site keys
  const allKeys = new Set();
  for (const [, arr] of entries) {
    for (const p of arr || []) {
      Object.keys(p).forEach(k => allKeys.add(k));
    }
  }
  const base = entries[0][1] || [];
  return base.map((point, i) => {
    const merged = { ...point };
    for (const [siteId, series] of entries) {
      const p = series[i] || {};
      merged[`kwh_${siteId}`] = p.kwh ?? p.p50 ?? null;
    }
    return merged;
  });
}

/** Price per kWh used for EUR conversion when none provided */
const DEFAULT_PRICE_EUR_KWH = 0.18;

/**
 * Convert a kWh value to the target unit.
 * @param {number} kwh
 * @param {'kwh'|'kw'|'eur'} unit
 * @param {number} [pricePerKwh]  — EUR/kWh (default 0.18)
 * @param {number} [hoursPerInterval] — interval duration (default 1 for hourly data)
 * @returns {number}
 */
export function convertUnit(kwh, unit, pricePerKwh = DEFAULT_PRICE_EUR_KWH, hoursPerInterval = 1) {
  if (unit === 'kw') return hoursPerInterval > 0 ? +(kwh / hoursPerInterval).toFixed(3) : 0;
  if (unit === 'eur') return +(kwh * pricePerKwh).toFixed(2);
  return kwh; // kwh passthrough
}

/** Palette for multi-site coloring (stable by index) */
const SITE_COLORS = [
  '#3b82f6', // blue
  '#10b981', // emerald
  '#f59e0b', // amber
  '#8b5cf6', // violet
  '#ef4444', // red
];

/**
 * Stable color for a site given its index position.
 * @param {string} _siteId  — unused but kept for signature clarity
 * @param {number} index
 * @returns {string} hex color
 */
export function colorForSite(_siteId, index) {
  return SITE_COLORS[index % SITE_COLORS.length];
}

/**
 * Interpret DJU climate sensitivity from gas model.
 * @param {number} slope  — kWh per DJU
 * @param {number} r2     — R² coefficient
 * @returns {{ level: 'low'|'medium'|'high', label: string }}
 */
export function interpretClimateSensitivity(slope, r2) {
  if (r2 < 0.3) return { level: 'low', label: 'Correlation faible' };
  if (slope < 5) return { level: 'medium', label: 'Sensibilite moderee' };
  return { level: 'high', label: 'Forte sensibilite climatique' };
}
