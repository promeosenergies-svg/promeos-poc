/**
 * PROMEOS — Brique 3 "Achat post-ARENH"
 * Assumptions & Presets
 */
import { ScenarioPreset, EnergyType, Persona, SEASONALITY_ELEC, SEASONALITY_GAZ } from './types.js';

// ── Default Market Assumptions ─────────────────────────────────────

export const DEFAULT_MARKET = {
  baseSpotEurPerMwh: 85,       // Base spot price (€/MWh)
  fixedPremiumPct: 0.12,       // Fixed = spot + 12%
  indexedSpreadEurPerMwh: 4,   // Indexed = index + spread
  volatilityAnnual: 0.25,      // 25% annual vol
  riskFreeRate: 0.03,          // 3%
  inflationRate: 0.02,         // 2%
};

// ── Scenario Presets ───────────────────────────────────────────────

export const SCENARIO_PRESETS = {
  [ScenarioPreset.STABLE]: {
    label: 'Stable',
    description: 'Marche calme, faible volatilite, tendance haussiere legere',
    driftAnnual: 0.02,
    volMultiplier: 0.6,
    shockProb: 0.02,
    shockMagnitude: 0.15,
  },
  [ScenarioPreset.VOLATILE]: {
    label: 'Volatile',
    description: 'Marche agite, forte volatilite, possibilite de pics',
    driftAnnual: 0.05,
    volMultiplier: 1.5,
    shockProb: 0.08,
    shockMagnitude: 0.40,
  },
  [ScenarioPreset.DEFENSIVE]: {
    label: 'Defensif',
    description: 'Scenario prudent : hausse moderee + volatilite elevee',
    driftAnnual: 0.08,
    volMultiplier: 1.2,
    shockProb: 0.05,
    shockMagnitude: 0.25,
  },
};

// ── Persona Profiles ───────────────────────────────────────────────

export const PERSONA_PROFILES = {
  [Persona.DG]: {
    label: 'DG / Direction Generale',
    description: 'Priorite: visibilite budgetaire, simplicite, faible risque contrat',
    weights: { budgetRisk: 0.40, transparency: 0.15, contractRisk: 0.35, dataReadiness: 0.10 },
    preferSimple: true,
    maxAcceptableRisk: 40,
  },
  [Persona.DAF]: {
    label: 'DAF / Direction Financiere',
    description: 'Priorite: transparence, SLA billing, faibles anomalies/ecarts',
    weights: { budgetRisk: 0.25, transparency: 0.40, contractRisk: 0.20, dataReadiness: 0.15 },
    preferSimple: false,
    maxAcceptableRisk: 55,
  },
  [Persona.ACHETEUR]: {
    label: 'Acheteur / Procurement',
    description: 'Priorite: comparabilite, clauses, pack RFP, meilleur prix',
    weights: { budgetRisk: 0.30, transparency: 0.25, contractRisk: 0.30, dataReadiness: 0.15 },
    preferSimple: false,
    maxAcceptableRisk: 65,
  },
  [Persona.RESP_ENERGIE]: {
    label: 'Responsable Energie',
    description: 'Priorite: hybride si data OK, sinon prudence, optimisation technique',
    weights: { budgetRisk: 0.20, transparency: 0.20, contractRisk: 0.20, dataReadiness: 0.40 },
    preferSimple: false,
    maxAcceptableRisk: 70,
  },
};

// ── Default Wizard State ───────────────────────────────────────────

export function createDefaultWizardState() {
  return {
    // Step 1: Portfolio
    organizationId: null,
    selectedSiteIds: [],
    sites: [],

    // Step 2: Consumption
    energyType: EnergyType.ELEC,
    totalAnnualKwh: 0,
    granularity: 'monthly',

    // Step 3: Persona
    persona: Persona.DAF,
    budgetEur: null, // optional budget ceiling

    // Step 4: Horizon & Risk
    horizonMonths: 24,
    scenarioPreset: ScenarioPreset.STABLE,
    mcIterations: 200,
    mcSeed: 42,

    // Step 5: Offers
    offers: [],

    // Step 6-8: Results (computed)
    results: null,
    scores: null,
    recommendation: null,
    auditRecord: null,
  };
}

/**
 * Get seasonality vector for energy type
 * @param {string} energyType
 * @returns {number[]}
 */
export function getSeasonality(energyType) {
  return energyType === EnergyType.GAZ ? [...SEASONALITY_GAZ] : [...SEASONALITY_ELEC];
}

/**
 * Distribute annual kWh into 12 monthly values using seasonality
 * @param {number} annualKwh
 * @param {string} energyType
 * @returns {number[]}
 */
export function distributeMonthly(annualKwh, energyType) {
  const seasonality = getSeasonality(energyType);
  const sum = seasonality.reduce((a, b) => a + b, 0);
  return seasonality.map(coeff => (annualKwh * coeff) / sum);
}
