/**
 * PROMEOS — Consumption Explorer shared constants
 * Extracted from ConsumptionExplorerPage for use by extracted panels.
 */

export const CONFIDENCE_BADGE = {
  high: { label: 'Haute', variant: 'ok' },
  medium: { label: 'Moyenne', variant: 'warn' },
  low: { label: 'Basse', variant: 'crit' },
};

/**
 * kgCO₂e per kWh — ADEME Base Empreinte V23.6, France electricity mix ACV.
 * Source unique backend : backend/config/emission_factors.py (ELEC = 0.052).
 *
 * ⚠️ AFFICHAGE UNIQUEMENT (presentation-layer).
 * - JAMAIS utiliser pour alimenter un payload POST/PATCH qui sera persisté.
 *   Si tu fais `co2e_savings_est_kg: savingsKwh * CO2E_FACTOR_KG_PER_KWH` dans
 *   un payload, tu pourris la DB (bug P0 QA Guardian 2026-04-15, fix dans
 *   `kbRecoActionModel.js` + backend `_resolve_co2e_kg`).
 * - Pour une valeur persistée : envoie `estimated_savings_kwh_year` au backend,
 *   qui calcule via `config.emission_factors.get_emission_factor("ELEC")`.
 * - Roadmap (P0 findings #1-5, non fixés dans ce sprint) : migrer vers un
 *   endpoint `GET /api/config/emission-factors` + Context Provider React pour
 *   supprimer ce hardcode. Voir docs/architecture/AGENT_ORCHESTRATION.md.
 */
export const CO2E_FACTOR_KG_PER_KWH = 0.052;

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
