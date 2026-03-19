/**
 * PROMEOS — Centralized risk normalization.
 * Single source of truth for risk levels, labels, and colors.
 */

/**
 * Risk level thresholds (EUR).
 * These match the backend compliance_engine.py logic:
 * BASE_PENALTY = 7500 EUR, NON_CONFORME = 100%, A_RISQUE = 50%.
 */
export const RISK_THRESHOLDS = {
  critique: 20000, // >= 20k EUR
  eleve: 10000, // >= 10k EUR
  modere: 3000, // >= 3k EUR
  faible: 0, // >= 0 EUR
};

export const RISK_LEVELS = {
  critique: {
    label: 'Critique',
    color: 'text-red-700',
    bg: 'bg-red-100',
    border: 'border-red-300',
    dot: 'bg-red-500',
  },
  eleve: {
    label: 'Élevé',
    color: 'text-orange-700',
    bg: 'bg-orange-100',
    border: 'border-orange-300',
    dot: 'bg-orange-500',
  },
  modere: {
    label: 'Modéré',
    color: 'text-amber-700',
    bg: 'bg-amber-100',
    border: 'border-amber-300',
    dot: 'bg-amber-500',
  },
  faible: {
    label: 'Faible',
    color: 'text-green-700',
    bg: 'bg-green-100',
    border: 'border-green-300',
    dot: 'bg-green-500',
  },
  inconnu: {
    label: 'Non évalué',
    color: 'text-gray-500',
    bg: 'bg-gray-100',
    border: 'border-gray-300',
    dot: 'bg-gray-400',
  },
};

/**
 * Normalize a raw EUR risk value to a canonical level.
 * @param {number|null|undefined} riskEur - Risk in EUR
 * @returns {{ level: string, label: string, color: string, bg: string, value: number }}
 */
export function normalizeRisk(riskEur) {
  if (riskEur == null || isNaN(riskEur)) {
    return { level: 'inconnu', ...RISK_LEVELS.inconnu, value: 0 };
  }
  const v = Number(riskEur);
  if (v >= RISK_THRESHOLDS.critique)
    return { level: 'critique', ...RISK_LEVELS.critique, value: v };
  if (v >= RISK_THRESHOLDS.eleve) return { level: 'eleve', ...RISK_LEVELS.eleve, value: v };
  if (v >= RISK_THRESHOLDS.modere) return { level: 'modere', ...RISK_LEVELS.modere, value: v };
  return { level: 'faible', ...RISK_LEVELS.faible, value: v };
}

/**
 * Format EUR amount for display.
 * @param {number} eur
 * @returns {string} e.g. "26 k€" or "1,2 M€" or "500 €"
 */
export function formatRiskEur(eur) {
  if (eur == null || isNaN(eur)) return '—';
  if (eur >= 1_000_000) return `${(eur / 1_000_000).toFixed(1)} M€`;
  if (eur >= 1000) return `${Math.round(eur / 1000)} k€`;
  return `${Math.round(eur)} €`;
}

/**
 * Get the canonical risk field from a site object.
 * Handles the multiple field names used across the codebase.
 * @param {object} site
 * @returns {number}
 */
export function getSiteRisk(site) {
  return (
    site?.risque_eur ?? site?.risque_financier_euro ?? site?.total_risk_eur ?? site?.risk_eur ?? 0
  );
}

/**
 * RiskBadge — inline badge component for risk display.
 */
export function RiskBadge({ riskEur, size = 'sm' }) {
  const { label, color, bg, border } = normalizeRisk(riskEur);
  const sizeClass = size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-3 py-1';
  return (
    <span
      className={`inline-flex items-center gap-1 rounded border ${sizeClass} ${color} ${bg} ${border}`}
    >
      {formatRiskEur(riskEur)} · {label}
    </span>
  );
}
