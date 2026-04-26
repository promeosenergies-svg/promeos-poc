/**
 * PROMEOS — Format helpers (FR locale)
 * k€, m², plurals, compact numbers, guards anti-NaN/Infinity.
 */

const FR = 'fr-FR';

/**
 * Kicker mono uppercase pour SolPageHeader éditorial — pattern
 * « LABEL · ORG · N SITE(S) ». Centralise la dupliction CommandCenter +
 * Cockpit (audit /simplify Phase 3).
 *
 * @example
 *   scopeKicker('ACCUEIL', 'Groupe HELIOS', 5)
 *   // → 'ACCUEIL · GROUPE HELIOS · 5 SITES'
 */
export function scopeKicker(label, orgName, sitesCount) {
  const safeOrg = (orgName || 'Patrimoine').toUpperCase();
  const n = Number.isFinite(sitesCount) ? sitesCount : 0;
  const plural = n > 1 ? 'SITES' : 'SITE';
  return `${label} · ${safeOrg} · ${n} ${plural}`;
}

// ── Guard universel ──────────────────────────────────────────────────────────
function _safe(v) {
  if (v == null) return null;
  const n = Number(v);
  if (!isFinite(n)) return null;
  return n;
}

/**
 * 23 995 => "24 k€"  |  1 234 567 => "1,2 M€"  |  850 => "850 €"
 * Threshold for k€ : >= 1 000
 */
export function fmtEur(v) {
  const n = _safe(v);
  if (n == null || n === 0) return '—';
  if (Math.abs(n) >= 1_000_000)
    return `${(n / 1_000_000).toLocaleString(FR, { maximumFractionDigits: 1 })} M€`;
  if (Math.abs(n) >= 1_000) return `${Math.round(n / 1_000).toLocaleString(FR)} k€`;
  return `${n.toLocaleString(FR)} €`;
}

/** Full precision: 23 995 => "23 995 €" */
export function fmtEurFull(v) {
  const n = _safe(v);
  if (n == null || n === 0) return '—';
  return `${n.toLocaleString(FR)} €`;
}

/** 11 562 => "11 562 m²" */
export function fmtArea(v) {
  const n = _safe(v);
  if (n == null || n === 0) return '—';
  return `${n.toLocaleString(FR)}\u00A0m²`;
}

/** Compact area: 11 562 => "11,6k m²" */
export function fmtAreaCompact(v) {
  const n = _safe(v);
  if (n == null || n === 0) return '—';
  if (n >= 1_000) return `${(n / 1_000).toLocaleString(FR, { maximumFractionDigits: 1 })}k\u00A0m²`;
  return `${n.toLocaleString(FR)}\u00A0m²`;
}

/** 125 000 => "125 MWh"  |  1 200 000 => "1,2 GWh"  |  800 => "800 kWh"
 *  1 500 => "1,500 MWh" (3 décimales pour MWh) */
export function fmtKwh(v) {
  const n = _safe(v);
  if (n == null || n === 0) return '—';
  if (Math.abs(n) >= 1_000_000)
    return `${(n / 1_000_000).toLocaleString(FR, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} GWh`;
  if (Math.abs(n) >= 1_000) {
    const mwh = n / 1_000;
    // 3 décimales visibles pour garantir la précision des calculs
    const decimals = Math.abs(mwh) >= 100 ? 1 : 3;
    return `${mwh.toLocaleString(FR, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })} MWh`;
  }
  return `${n.toLocaleString(FR)} kWh`;
}

/** Pour les valeurs déjà en MWh (backend `total_mwh`, etc.) — évite la
 *  conversion manuelle `mwh * 1000` au site d'appel. */
export function fmtMwh(v) {
  const n = _safe(v);
  if (n == null || n === 0) return '—';
  if (Math.abs(n) >= 1_000)
    return `${(n / 1_000).toLocaleString(FR, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} GWh`;
  return `${Math.round(n).toLocaleString(FR)} MWh`;
}

/** Return the appropriate unit for a kWh value: 'kWh', 'MWh', or 'GWh' */
export function kwhUnit(v) {
  const n = _safe(v);
  if (n == null) return 'kWh';
  if (Math.abs(n) >= 1_000_000) return 'GWh';
  if (Math.abs(n) >= 1_000) return 'MWh';
  return 'kWh';
}

/** 1 200 => "1,2k kW"  |  0.5 => "0,5 kW" */
export function fmtKw(v) {
  const n = _safe(v);
  if (n == null || n === 0) return '—';
  if (Math.abs(n) >= 1_000_000)
    return `${(n / 1_000_000).toLocaleString(FR, { maximumFractionDigits: 1 })} MW`;
  if (Math.abs(n) >= 1_000)
    return `${(n / 1_000).toLocaleString(FR, { maximumFractionDigits: 1 })}k kW`;
  return `${n.toLocaleString(FR, { maximumFractionDigits: 1 })} kW`;
}

/** Generic number with configurable decimals + unit. fmtNum(1234.5, 1, '°C') => "1 234,5 °C" */
export function fmtNum(v, decimals = 0, unit = '') {
  const n = _safe(v);
  if (n == null) return '—';
  const formatted = n.toLocaleString(FR, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  return unit ? `${formatted} ${unit}` : formatted;
}

/** Percentage from ratio (0-1) or value (0-100). fmtPct(0.85) => "85%" | fmtPct(85, false) => "85%" */
export function fmtPct(v, isRatio = true, decimals = 0) {
  const n = _safe(v);
  if (n == null) return '—';
  const pct = isRatio ? n * 100 : n;
  return `${pct.toLocaleString(FR, { maximumFractionDigits: decimals })}%`;
}

/** Simple pluralize: pl(3, 'site') => "3 sites", pl(1, 'site') => "1 site" */
export function pl(n, word) {
  return `${n}\u00A0${word}${n > 1 ? 's' : ''}`;
}

/** 35 725 kg => "35,7 t CO₂" | 800 kg => "800 kg CO₂" */
export function fmtCo2(kgValue) {
  const n = _safe(kgValue);
  if (n == null || n === 0) return '—';
  if (Math.abs(n) >= 1_000)
    return `${(n / 1_000).toLocaleString(FR, { maximumFractionDigits: 1 })} t CO₂`;
  return `${Math.round(n).toLocaleString(FR)} kg CO₂`;
}

/** Format date FR: "14 fev. 2026" */
export function fmtDateFR(v) {
  if (!v) return '—';
  const d = new Date(v);
  if (isNaN(d.getTime())) return '—';
  return d.toLocaleDateString(FR, { day: 'numeric', month: 'short', year: 'numeric' });
}

/** Format date long: "14 février 2026" */
export function fmtDateLong(v) {
  if (!v) return '—';
  const d = new Date(v);
  if (isNaN(d.getTime())) return '—';
  return d.toLocaleDateString(FR, { day: 'numeric', month: 'long', year: 'numeric' });
}

/** Format date range: "mars 2025 — juin 2025" */
export function fmtDateRange(start, end) {
  if (!start && !end) return '—';
  const fmtMonth = (v) => {
    if (!v) return '…';
    const d = new Date(v);
    if (isNaN(d.getTime())) return '…';
    return d.toLocaleDateString(FR, { month: 'long', year: 'numeric' });
  };
  return `${fmtMonth(start)} — ${fmtMonth(end)}`;
}

/**
 * Format a percentage value (0–100) with FR locale.
 * Uses Intl.NumberFormat which produces a proper non-breaking space: "24 %"
 * @param {number} value — a value between 0 and 100
 * @returns {string} e.g. "24 %"
 */
export function formatPercentFR(value) {
  const n = _safe(value);
  if (n == null) return '—';
  return new Intl.NumberFormat(FR, { style: 'percent', maximumFractionDigits: 0 }).format(n / 100);
}
