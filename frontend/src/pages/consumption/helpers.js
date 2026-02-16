/**
 * PROMEOS — Consumption Explorer helpers (pure, testable)
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
