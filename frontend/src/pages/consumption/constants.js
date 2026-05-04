/**
 * PROMEOS — Consumption Explorer shared constants
 * Extracted from ConsumptionExplorerPage for use by extracted panels.
 */

export const CONFIDENCE_BADGE = {
  high: { label: 'Haute', variant: 'ok' },
  medium: { label: 'Moyenne', variant: 'warn' },
  low: { label: 'Basse', variant: 'crit' },
};

// CO2E_FACTOR_KG_PER_KWH retiré Sprint C-2 Phase 4.4 (2026-05-04).
// SoT canonique = endpoint /api/config/emission-factors consommé par
// EmissionFactorsContext.jsx (hook useElecCo2Factor). Fallback inline 0.052
// (ADEME Base Empreinte V23.6) directement dans le Context.

export const ALERT_COLOR = {
  on_track: {
    bg: 'bg-green-50',
    text: 'text-green-700',
    border: 'border-green-200',
    label: 'En bonne voie',
  },
  at_risk: {
    bg: 'bg-amber-50',
    text: 'text-amber-700',
    border: 'border-amber-200',
    label: 'A risque',
  },
  over_budget: {
    bg: 'bg-red-50',
    text: 'text-red-700',
    border: 'border-red-200',
    label: 'Hors budget',
  },
};
