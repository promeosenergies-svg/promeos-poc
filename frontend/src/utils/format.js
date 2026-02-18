/**
 * PROMEOS — Format helpers (FR locale)
 * k€, m², plurals, compact numbers.
 */

const FR = 'fr-FR';

/**
 * 23 995 => "24 k€"  |  1 234 567 => "1,2 M€"  |  850 => "850 €"
 * Threshold for k€ : >= 1 000
 */
export function fmtEur(v) {
  if (v == null || v === 0) return '—';
  const n = Number(v);
  if (Number.isNaN(n)) return '—';
  if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toLocaleString(FR, { maximumFractionDigits: 1 })} M€`;
  if (Math.abs(n) >= 1_000) return `${Math.round(n / 1_000).toLocaleString(FR)} k€`;
  return `${n.toLocaleString(FR)} €`;
}

/** Full precision: 23 995 => "23 995 €" */
export function fmtEurFull(v) {
  if (v == null || v === 0) return '—';
  return `${Number(v).toLocaleString(FR)} €`;
}

/** 11 562 => "11 562 m²" */
export function fmtArea(v) {
  if (v == null || v === 0) return '—';
  return `${Number(v).toLocaleString(FR)}\u00A0m²`;
}

/** Compact area: 11 562 => "11,6k m²" */
export function fmtAreaCompact(v) {
  if (v == null || v === 0) return '—';
  const n = Number(v);
  if (n >= 1_000) return `${(n / 1_000).toLocaleString(FR, { maximumFractionDigits: 1 })}k\u00A0m²`;
  return `${n.toLocaleString(FR)}\u00A0m²`;
}

/** 125 000 => "125k kWh"  |  1 200 000 => "1,2 GWh" */
export function fmtKwh(v) {
  if (v == null || v === 0) return '—';
  const n = Number(v);
  if (n >= 1_000_000) return `${(n / 1_000_000).toLocaleString(FR, { maximumFractionDigits: 1 })} GWh`;
  if (n >= 1_000) return `${Math.round(n / 1_000).toLocaleString(FR)}k kWh`;
  return `${n.toLocaleString(FR)} kWh`;
}

/** Simple pluralize: pl(3, 'site') => "3 sites", pl(1, 'site') => "1 site" */
export function pl(n, word) {
  return `${n}\u00A0${word}${n > 1 ? 's' : ''}`;
}

/** Format date FR: "14 fev. 2026" */
export function fmtDateFR(v) {
  if (!v) return '—';
  return new Date(v).toLocaleDateString(FR, { day: 'numeric', month: 'short', year: 'numeric' });
}

/**
 * Format a percentage value (0–100) with FR locale.
 * Uses Intl.NumberFormat which produces a proper non-breaking space: "24 %"
 * @param {number} value — a value between 0 and 100
 * @returns {string} e.g. "24 %"
 */
export function formatPercentFR(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return new Intl.NumberFormat(FR, { style: 'percent', maximumFractionDigits: 0 }).format(Number(value) / 100);
}
