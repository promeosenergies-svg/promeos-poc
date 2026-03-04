/**
 * PROMEOS — Consumption Explorer helpers (pure, testable)
 * V11: computeGranularity, computeAutoRange, classifyEmptyReason
 * WoW: aggregateSeries, convertUnit, colorForSite
 * V17: normalizeId
 */

/**
 * Normalize a site/org ID to string for type-safe comparisons.
 * Prevents number/string mismatch (e.g. scope.siteId=5 vs "5" from localStorage).
 * Returns null for null/undefined.
 * @param {any} x
 * @returns {string|null}
 */
export function normalizeId(x) {
  if (x == null) return null;
  return String(x);
}

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

  // Build a date-keyed index for each site (align by date, not by array index)
  const siteIndexes = entries.map(([siteId, series]) => {
    const byDate = {};
    for (const p of series || []) {
      const key = p.date || p.hour || p.t || '';
      byDate[key] = p;
    }
    return [siteId, byDate];
  });

  // Collect all dates across all sites, sorted
  const allDates = [
    ...new Set(
      entries.flatMap(([, series]) => (series || []).map((p) => p.date || p.hour || p.t || ''))
    ),
  ].sort();

  if (mode === 'agrege') {
    return allDates.map((dateKey) => {
      let base = null;
      let sum = 0;
      for (const [, byDate] of siteIndexes) {
        const p = byDate[dateKey];
        if (p) {
          if (!base) base = { ...p };
          sum += p.kwh ?? p.p50 ?? 0;
        }
      }
      return { ...(base || { date: dateKey }), kwh: sum, p50: sum };
    });
  }

  // For superpose / empile / separe: attach per-site keys
  return allDates.map((dateKey) => {
    let base = null;
    for (const [, byDate] of siteIndexes) {
      if (byDate[dateKey]) {
        base = byDate[dateKey];
        break;
      }
    }
    const merged = { ...(base || { date: dateKey }) };
    for (const [siteId, byDate] of siteIndexes) {
      const p = byDate[dateKey] || {};
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

// Sampling interval in minutes for each granularity key (must match backend)
const GRANULARITY_MINUTES = {
  '30min': 30,
  hourly: 60,
  daily: 1440,
  monthly: 43200,
};

/**
 * Available granularity options — intersection of:
 *   (a) period-based constraints (too fine for long periods)
 *   (b) data-frequency constraints (can't be finer than actual readings)
 *
 * @param {number}       days             — selected period length
 * @param {number|null}  samplingMinutes  — actual meter reading interval from backend meta
 *                                          (null = unknown → period-only filtering)
 * @returns {Array<{ key: string, label: string }>}
 */
export function getAvailableGranularities(days, samplingMinutes = null) {
  const all = [
    { key: 'auto', label: 'Auto' },
    { key: '30min', label: '30 min', maxDays: 14 },
    { key: 'hourly', label: '1 h', maxDays: 200 },
    { key: 'daily', label: '1 j', minDays: 7 },
    { key: 'monthly', label: 'Mois', minDays: 30 },
  ];
  return all.filter((g) => {
    if (g.key === 'auto') return true;
    // Period-based constraint
    const periodOk = (!g.minDays || days >= g.minDays) && (!g.maxDays || days <= g.maxDays);
    if (!periodOk) return false;
    // Data-frequency constraint: granularity must not be finer than actual readings
    if (samplingMinutes != null) {
      const gMinutes = GRANULARITY_MINUTES[g.key];
      if (gMinutes != null && gMinutes < samplingMinutes) return false;
    }
    return true;
  });
}
