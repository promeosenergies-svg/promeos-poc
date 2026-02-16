/**
 * PROMEOS — Brique 3 "Achat post-ARENH"
 * Barrel export
 */

// Types & constants
export {
  EnergyType, OfferStructure, ScenarioPreset, Persona, Confidence,
  ScoreLevel, EvidenceSource, BreakdownComponentType,
  BREAKDOWN_LABELS, BREAKDOWN_DEFAULTS_ELEC, BREAKDOWN_DEFAULTS_GAZ,
  SEASONALITY_ELEC, SEASONALITY_GAZ,
  BRIQUE3_VERSION,
} from './types.js';

// Assumptions & config
export {
  DEFAULT_MARKET, SCENARIO_PRESETS, PERSONA_PROFILES,
  createDefaultWizardState, getSeasonality, distributeMonthly,
} from './assumptions.js';

// Scenario & trajectory
export {
  createRng, generateTrajectory,
  generateMonteCarloTrajectories, generateDeterministicTrajectory,
} from './scenarioLibrary.js';

// Risk & Monte Carlo
export {
  computeOfferMonthlyPrices, computeTco,
  monteCarloOffer, computeWorstMonth,
  probExceedBudget, cvar90, volatilityProxy,
} from './risk.js';

// Engine
export {
  runEngine, clearEngineCache,
  normalizeHybridShares, validateBreakdown, fillBreakdownDefaults,
} from './engine.js';

// Scoring
export {
  scoreBudgetRisk, scoreTransparency, scoreContractRisk,
  scoreDataReadiness, scoreOffer,
} from './scoring.js';

// Recommendation
export { recommend } from './recommend.js';

// RFP & exports
export {
  generateDecisionNote, generateRfpPack, generateComparisonCsv,
} from './rfp.js';

// Audit trail
export {
  appendDecision, getAuditLog, getAuditCount,
  getRecentDecisions, getDecisionById,
  exportAsJsonl, exportAsJson, downloadAuditFile,
  _clearAuditLog,
} from './audit.js';

// Demo data
export {
  DEMO_ORGANIZATIONS, DEMO_OFFERS,
  aggregateDemoSites, getAllDemoSites,
} from './demoData.js';

// Data adapter (B1/B2 bridge)
export {
  fetchSites, fetchSiteWithBilling, fetchAnomalies,
  fetchPreferences, fetchAssumptions, getDemoDataset,
} from './dataAdapter.js';
