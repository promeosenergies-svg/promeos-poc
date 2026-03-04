/**
 * PROMEOS — Evidence model V0
 * Structured proof metadata for "Pourquoi ce chiffre ?" drawer.
 *
 * @typedef {Object} EvidenceSource
 * @property {'enedis'|'invoice'|'manual'|'calc'} kind
 * @property {string}  label       — ex "Enedis - Courbe de charge"
 * @property {string}  [freshness] — ex "Dernière synchro: 2026-03-01 08:12"
 * @property {'high'|'medium'|'low'} [confidence]
 * @property {string}  [details]   — 1-2 lines
 * @property {Array<{label:string, href:string}>} [links] — internal routes only
 *
 * @typedef {Object} Evidence
 * @property {string}  id
 * @property {string}  title       — ex "kWh total — 90 jours"
 * @property {string}  [valueLabel] — ex "124 078 kWh"
 * @property {string}  [scopeLabel] — ex "Groupe HELIOS • Tous les sites"
 * @property {string}  [periodLabel] — ex "90 jours"
 * @property {EvidenceSource[]} sources
 * @property {string[]} method     — bullet points
 * @property {string[]} [assumptions]
 * @property {string}  [lastComputedAt]
 * @property {string}  [owner]     — ex "PROMEOS Engine"
 */

/** Confidence level display config */
export const CONFIDENCE_CFG = {
  high: {
    label: 'Haute',
    dot: 'bg-emerald-500',
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    border: 'border-emerald-200',
  },
  medium: {
    label: 'Moyenne',
    dot: 'bg-amber-400',
    bg: 'bg-amber-50',
    text: 'text-amber-700',
    border: 'border-amber-200',
  },
  low: {
    label: 'Basse',
    dot: 'bg-red-400',
    bg: 'bg-red-50',
    text: 'text-red-700',
    border: 'border-red-200',
  },
};

/** Source kind icons/labels */
export const SOURCE_KIND = {
  enedis: { label: 'Compteur Enedis', emoji: '📡' },
  invoice: { label: 'Facture énergie', emoji: '🧾' },
  manual: { label: 'Saisie manuelle', emoji: '✏️' },
  calc: { label: 'Calcul PROMEOS', emoji: '⚙️' },
};

/**
 * Build an Evidence object from contextual data.
 * Used to generate V0 evidence from whatever scope/period is available.
 */
export function buildEvidence({
  id,
  title,
  valueLabel,
  scopeLabel,
  periodLabel,
  sources,
  method,
  assumptions,
  owner = 'PROMEOS Engine',
}) {
  return {
    id,
    title,
    valueLabel: valueLabel || null,
    scopeLabel: scopeLabel || null,
    periodLabel: periodLabel || null,
    sources: sources || [],
    method: method || [],
    assumptions: assumptions || [],
    lastComputedAt: new Date().toISOString(),
    owner,
  };
}
