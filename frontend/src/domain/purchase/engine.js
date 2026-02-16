/**
 * PROMEOS — Brique 3 "Achat post-ARENH"
 * Engine — Main computation orchestrator
 *
 * Coordinates scenario generation, pricing, risk, and corridor computation.
 * Memoized: only recomputes when params change.
 */
import { OfferStructure, BREAKDOWN_DEFAULTS_ELEC, BREAKDOWN_DEFAULTS_GAZ, EnergyType } from './types.js';
import { distributeMonthly, DEFAULT_MARKET } from './assumptions.js';
import { monteCarloOffer, computeWorstMonth, probExceedBudget, cvar90, volatilityProxy } from './risk.js';

// ── Memoization ────────────────────────────────────────────────────

let _lastParamsHash = null;
let _lastResults = null;

function hashParams(params) {
  return JSON.stringify(params);
}

// ── Hybrid Share Normalization ──────────────────────────────────────

/**
 * Normalize hybrid share percentages to sum to 1.0 (tolerance ±0.5%)
 * @param {import('./types.js').PricingModel} pricing
 * @returns {{ pricing: import('./types.js').PricingModel, normalized: boolean, message: string|null }}
 */
export function normalizeHybridShares(pricing) {
  const total = (pricing.fixedSharePct || 0) + (pricing.indexedSharePct || 0) + (pricing.spotSharePct || 0);

  if (Math.abs(total - 1.0) <= 0.005) {
    return { pricing, normalized: false, message: null };
  }

  if (total === 0) {
    return {
      pricing: { ...pricing, fixedSharePct: 1, indexedSharePct: 0, spotSharePct: 0 },
      normalized: true,
      message: 'Parts a zero — fixe a 100% par defaut',
    };
  }

  return {
    pricing: {
      ...pricing,
      fixedSharePct: Math.round((pricing.fixedSharePct || 0) / total * 1000) / 1000,
      indexedSharePct: Math.round((pricing.indexedSharePct || 0) / total * 1000) / 1000,
      spotSharePct: Math.round((pricing.spotSharePct || 0) / total * 1000) / 1000,
    },
    normalized: true,
    message: `Parts normalisees (somme etait ${(total * 100).toFixed(1)}%, ajustee a 100%)`,
  };
}

// ── Breakdown Validation ───────────────────────────────────────────

/**
 * Validate breakdown completeness (7+ components expected)
 * @param {import('./types.js').BreakdownLine[]} breakdown
 * @returns {{ complete: boolean, knownCount: number, totalComponents: number, missingComponents: string[] }}
 */
export function validateBreakdown(breakdown) {
  const knownComponents = new Set(breakdown.filter(b => b.status === 'KNOWN').map(b => b.component));
  const allComponents = Object.keys(BREAKDOWN_DEFAULTS_ELEC);
  const missing = allComponents.filter(c => !knownComponents.has(c));

  return {
    complete: knownComponents.size >= 7,
    knownCount: knownComponents.size,
    totalComponents: allComponents.length,
    missingComponents: missing,
  };
}

/**
 * Fill missing breakdown components with defaults
 * @param {import('./types.js').BreakdownLine[]} breakdown
 * @param {string} energyType
 * @returns {import('./types.js').BreakdownLine[]}
 */
export function fillBreakdownDefaults(breakdown, energyType) {
  const defaults = energyType === EnergyType.GAZ ? BREAKDOWN_DEFAULTS_GAZ : BREAKDOWN_DEFAULTS_ELEC;
  const existing = new Set(breakdown.map(b => b.component));
  const filled = [...breakdown];

  for (const [component, share] of Object.entries(defaults)) {
    if (!existing.has(component)) {
      filled.push({ component, sharePct: share, eurPerMwh: null, status: 'ESTIMATED' });
    }
  }

  return filled;
}

// ── Main Engine ────────────────────────────────────────────────────

/**
 * @typedef {Object} EngineParams
 * @property {import('./types.js').Offer[]} offers
 * @property {number} annualKwh
 * @property {string} energyType
 * @property {number} horizonMonths
 * @property {string} scenarioPreset
 * @property {number} mcIterations
 * @property {number} mcSeed
 * @property {number|null} budgetEur
 */

/**
 * @typedef {Object} OfferResult
 * @property {string} offerId
 * @property {string} supplierName
 * @property {string} structure
 * @property {import('./types.js').CorridorResult} corridor
 * @property {number} tcoEurPerMwh - TCO P50 in €/MWh
 * @property {number} annualCostP50 - Annual cost at P50
 * @property {number} worstMonthEur
 * @property {number} worstMonthIndex
 * @property {number} volatility
 * @property {number} probExceedBudget - 0..1 (null if no budget)
 * @property {number} cvar90
 * @property {boolean} hybridNormalized
 * @property {string|null} hybridNormMessage
 * @property {Object} breakdownValidation
 */

/**
 * @typedef {Object} EngineOutput
 * @property {OfferResult[]} results
 * @property {number} computedAt - timestamp
 * @property {EngineParams} params
 */

/**
 * Run the full engine computation for all offers
 * @param {EngineParams} params
 * @returns {EngineOutput}
 */
export function runEngine(params) {
  const { offers, annualKwh, energyType, horizonMonths, scenarioPreset, mcIterations, mcSeed, budgetEur } = params;

  // Memoization check
  const paramsHash = hashParams({ annualKwh, energyType, horizonMonths, scenarioPreset, mcIterations, mcSeed, budgetEur, offerIds: offers.map(o => o.id) });
  if (paramsHash === _lastParamsHash && _lastResults) {
    return _lastResults;
  }

  // Distribute annual consumption to monthly
  const monthlyKwh = distributeMonthly(annualKwh, energyType);

  const results = offers.map((offer, idx) => {
    // Normalize hybrid shares if needed
    let processedPricing = offer.pricing;
    let hybridNormalized = false;
    let hybridNormMessage = null;

    if (offer.structure === OfferStructure.HYBRIDE) {
      const norm = normalizeHybridShares(offer.pricing);
      processedPricing = norm.pricing;
      hybridNormalized = norm.normalized;
      hybridNormMessage = norm.message;
    }

    const processedOffer = { ...offer, pricing: processedPricing };

    // Run Monte Carlo — use different seed per offer for independence
    const offerSeed = mcSeed + idx * 1000;
    const corridor = monteCarloOffer({
      offer: processedOffer,
      monthlyKwh,
      horizonMonths,
      preset: scenarioPreset,
      iterations: mcIterations,
      seed: offerSeed,
    });

    // Worst month
    const { worstMonthEur, worstMonthIndex } = computeWorstMonth(
      processedOffer, monthlyKwh, horizonMonths, scenarioPreset, offerSeed,
    );

    // Metrics
    const vol = volatilityProxy(corridor.distribution);
    const probBudget = budgetEur ? probExceedBudget(corridor.distribution, budgetEur) : null;
    const cvarVal = cvar90(corridor.distribution);

    // TCO per MWh at P50
    const totalKwh = annualKwh * (horizonMonths / 12);
    const tcoEurPerMwh = totalKwh > 0 ? (corridor.tcoP50 / totalKwh) * 1000 : 0;
    const annualCostP50 = horizonMonths > 0 ? corridor.tcoP50 / (horizonMonths / 12) : 0;

    // Breakdown validation
    const breakdownValidation = validateBreakdown(offer.breakdown || []);

    return {
      offerId: offer.id,
      supplierName: offer.supplierName,
      structure: offer.structure,
      corridor,
      tcoEurPerMwh,
      annualCostP50,
      worstMonthEur,
      worstMonthIndex,
      volatility: vol,
      probExceedBudget: probBudget,
      cvar90: cvarVal,
      hybridNormalized,
      hybridNormMessage,
      breakdownValidation,
    };
  });

  const output = {
    results,
    computedAt: Date.now(),
    params,
  };

  // Cache
  _lastParamsHash = paramsHash;
  _lastResults = output;

  return output;
}

/**
 * Clear the engine cache (for testing or param change)
 */
export function clearEngineCache() {
  _lastParamsHash = null;
  _lastResults = null;
}
