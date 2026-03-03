/**
 * PROMEOS — Brique 3 "Achat post-ARENH"
 * Risk Module — Monte Carlo pricing + corridor + metrics
 *
 * Computes price distributions, P10/P50/P90 corridor, TCO,
 * budget exceedance probability, and CVaR90 (light).
 */
import { OfferStructure } from './types.js';
import { DEFAULT_MARKET } from './assumptions.js';
import { generateMonteCarloTrajectories } from './scenarioLibrary.js';

// ── Percentile Helper ──────────────────────────────────────────────

/**
 * @param {number[]} sorted array (ascending)
 * @param {number} p percentile 0..1
 * @returns {number}
 */
function percentile(sorted, p) {
  if (sorted.length === 0) return 0;
  if (sorted.length === 1) return sorted[0];
  const idx = Math.max(0, Math.min(p * (sorted.length - 1), sorted.length - 1));
  const lo = Math.floor(idx);
  const hi = Math.ceil(idx);
  if (lo === hi) return sorted[lo];
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (idx - lo);
}

// ── Offer Price Computation ────────────────────────────────────────

/**
 * Compute effective monthly price for an offer given a spot price trajectory
 * @param {import('./types.js').Offer} offer
 * @param {number[]} spotTrajectory - monthly spot prices €/MWh
 * @returns {number[]} monthly effective prices €/MWh
 */
export function computeOfferMonthlyPrices(offer, spotTrajectory) {
  const { structure, pricing } = offer;
  const months = spotTrajectory.length;
  const prices = new Array(months);

  for (let m = 0; m < months; m++) {
    const spot = spotTrajectory[m];

    switch (structure) {
      case OfferStructure.FIXE:
        prices[m] = pricing.fixedPriceEurPerMwh ?? 0;
        break;

      case OfferStructure.INDEXE: {
        let indexed = spot + (pricing.spreadEurPerMwh || 0);
        if (pricing.capEurPerMwh != null) indexed = Math.min(indexed, pricing.capEurPerMwh);
        if (pricing.floorEurPerMwh != null) indexed = Math.max(indexed, pricing.floorEurPerMwh);
        prices[m] = indexed;
        break;
      }

      case OfferStructure.SPOT:
        prices[m] = spot;
        break;

      case OfferStructure.HYBRIDE:
      case OfferStructure.HEURES_SOLAIRES: {
        const fixedPart = (pricing.fixedSharePct || 0) * (pricing.fixedPriceEurPerMwh ?? 0);
        let indexedPrice = spot + (pricing.spreadEurPerMwh || 0);
        if (pricing.capEurPerMwh != null) indexedPrice = Math.min(indexedPrice, pricing.capEurPerMwh);
        const indexedPart = (pricing.indexedSharePct || 0) * indexedPrice;
        const spotPart = (pricing.spotSharePct || 0) * spot;
        prices[m] = fixedPart + indexedPart + spotPart;
        break;
      }

      default:
        prices[m] = spot;
    }
  }

  return prices;
}

/**
 * Compute TCO for a monthly price trajectory and monthly consumption
 * @param {number[]} monthlyPrices - €/MWh
 * @param {number[]} monthlyKwh - kWh
 * @returns {number} total cost in EUR
 */
export function computeTco(monthlyPrices, monthlyKwh) {
  let total = 0;
  const n = Math.min(monthlyPrices.length, monthlyKwh.length);
  for (let m = 0; m < n; m++) {
    const price = monthlyPrices[m] || 0;
    const kwh = monthlyKwh[m] || 0;
    if (!isFinite(price) || !isFinite(kwh)) continue;
    total += (price / 1000) * kwh; // €/MWh * kWh / 1000
  }
  return total;
}

// ── Monte Carlo Risk Engine ────────────────────────────────────────

/**
 * Run Monte Carlo simulation for a single offer
 * @param {Object} params
 * @param {import('./types.js').Offer} params.offer
 * @param {number[]} params.monthlyKwh - 12 monthly consumption values (repeated for horizon)
 * @param {number} params.horizonMonths
 * @param {string} params.preset - ScenarioPreset
 * @param {number} params.iterations - max 200
 * @param {number} params.seed
 * @returns {import('./types.js').CorridorResult}
 */
export function monteCarloOffer({ offer, monthlyKwh, horizonMonths, preset, iterations, seed }) {
  const basePrice = DEFAULT_MARKET.baseSpotEurPerMwh;
  const { trajectories } = generateMonteCarloTrajectories({
    horizonMonths, preset, basePrice, iterations, seed,
  });

  // Extend monthlyKwh to horizon (repeat annual cycle)
  const avgKwh = monthlyKwh.reduce((a, b) => a + b, 0) / 12;
  const extendedKwh = new Array(horizonMonths);
  for (let m = 0; m < horizonMonths; m++) {
    extendedKwh[m] = monthlyKwh[m % 12] ?? avgKwh;
  }

  // Compute TCO distribution
  const tcoSamples = trajectories.map(traj => {
    const monthlyPrices = computeOfferMonthlyPrices(offer, traj);
    return computeTco(monthlyPrices, extendedKwh);
  });

  // Compute avg price distribution (€/MWh weighted by consumption)
  const avgPriceSamples = trajectories.map(traj => {
    const monthlyPrices = computeOfferMonthlyPrices(offer, traj);
    let weightedSum = 0;
    let totalKwh = 0;
    for (let m = 0; m < horizonMonths; m++) {
      weightedSum += monthlyPrices[m] * extendedKwh[m];
      totalKwh += extendedKwh[m];
    }
    return totalKwh > 0 ? weightedSum / totalKwh : 0; // still €/MWh
  });

  // Sort for percentiles
  const sortedTco = [...tcoSamples].sort((a, b) => a - b);
  const sortedPrice = [...avgPriceSamples].sort((a, b) => a - b);

  return {
    p10: percentile(sortedPrice, 0.10),
    p50: percentile(sortedPrice, 0.50),
    p90: percentile(sortedPrice, 0.90),
    mean: sortedPrice.reduce((a, b) => a + b, 0) / sortedPrice.length,
    tcoP10: percentile(sortedTco, 0.10),
    tcoP50: percentile(sortedTco, 0.50),
    tcoP90: percentile(sortedTco, 0.90),
    distribution: tcoSamples,
  };
}

/**
 * Compute worst month (max monthly cost) from a corridor result
 * @param {import('./types.js').Offer} offer
 * @param {number[]} monthlyKwh
 * @param {number} horizonMonths
 * @param {string} preset
 * @param {number} seed
 * @returns {{ worstMonthEur: number, worstMonthIndex: number }}
 */
export function computeWorstMonth(offer, monthlyKwh, horizonMonths, preset, seed) {
  const basePrice = DEFAULT_MARKET.baseSpotEurPerMwh;
  const { trajectories } = generateMonteCarloTrajectories({
    horizonMonths, preset, basePrice, iterations: 50, seed,
  });

  let worstCost = 0;
  let worstIdx = 0;

  for (const traj of trajectories) {
    const prices = computeOfferMonthlyPrices(offer, traj);
    for (let m = 0; m < horizonMonths; m++) {
      const kwh = monthlyKwh[m % 12] || 0;
      const cost = (prices[m] / 1000) * kwh;
      if (cost > worstCost) {
        worstCost = cost;
        worstIdx = m;
      }
    }
  }

  return { worstMonthEur: worstCost, worstMonthIndex: worstIdx };
}

/**
 * Probability of exceeding a budget ceiling
 * @param {number[]} tcoDistribution
 * @param {number} budgetEur
 * @returns {number} probability 0..1
 */
export function probExceedBudget(tcoDistribution, budgetEur) {
  if (!budgetEur || tcoDistribution.length === 0) return 0;
  const exceeding = tcoDistribution.filter(t => t > budgetEur).length;
  return exceeding / tcoDistribution.length;
}

/**
 * CVaR90 (light) — average of worst 10% outcomes
 * @param {number[]} distribution
 * @returns {number}
 */
export function cvar90(distribution) {
  const valid = distribution.filter(v => isFinite(v));
  if (valid.length === 0) return 0;
  const sorted = [...valid].sort((a, b) => a - b);
  const cutoff = Math.ceil(sorted.length * 0.9);
  const tail = sorted.slice(cutoff);
  if (tail.length === 0) return sorted[sorted.length - 1];
  return tail.reduce((a, b) => a + b, 0) / tail.length;
}

/**
 * Volatility proxy — standard deviation of TCO distribution
 * @param {number[]} distribution
 * @returns {number}
 */
export function volatilityProxy(distribution) {
  const valid = distribution.filter(v => isFinite(v));
  if (valid.length < 2) return 0;
  const mean = valid.reduce((a, b) => a + b, 0) / valid.length;
  const variance = valid.reduce((sum, v) => sum + (v - mean) ** 2, 0) / (valid.length - 1);
  const result = Math.sqrt(variance);
  return isFinite(result) ? result : 0;
}
