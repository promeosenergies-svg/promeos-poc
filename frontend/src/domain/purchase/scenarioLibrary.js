/**
 * PROMEOS — Brique 3 "Achat post-ARENH"
 * Scenario Library — Trajectory generation & Monte Carlo
 *
 * Deterministic + stochastic trajectories for energy price simulation.
 * Max 200 iterations, seeded RNG for reproducibility.
 */
import { ScenarioPreset } from './types.js';
import { SCENARIO_PRESETS, DEFAULT_MARKET } from './assumptions.js';

// ── Seeded PRNG (Mulberry32) ───────────────────────────────────────

/**
 * Mulberry32 PRNG — fast, seeded, deterministic
 * @param {number} seed
 * @returns {() => number} next() -> [0, 1)
 */
export function createRng(seed) {
  let state = seed | 0;
  return function next() {
    state = (state + 0x6D2B79F5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Box-Muller transform: uniform -> normal
 * @param {() => number} rng
 * @returns {number} standard normal sample
 */
function normalSample(rng) {
  const u1 = rng();
  const u2 = rng();
  return Math.sqrt(-2 * Math.log(Math.max(u1, 1e-10))) * Math.cos(2 * Math.PI * u2);
}

// ── Trajectory Generation ──────────────────────────────────────────

/**
 * Generate a single price trajectory using GBM + jump diffusion
 * @param {Object} params
 * @param {number} params.horizonMonths
 * @param {string} params.preset - ScenarioPreset key
 * @param {number} params.basePrice - starting price €/MWh
 * @param {() => number} rng - seeded PRNG
 * @returns {number[]} monthly prices (length = horizonMonths)
 */
export function generateTrajectory({ horizonMonths, preset, basePrice, rng }) {
  const config = SCENARIO_PRESETS[preset] || SCENARIO_PRESETS[ScenarioPreset.STABLE];
  const vol = DEFAULT_MARKET.volatilityAnnual * config.volMultiplier;
  const drift = config.driftAnnual;
  const dt = 1 / 12; // monthly step

  const prices = new Array(horizonMonths);
  let price = basePrice;

  for (let m = 0; m < horizonMonths; m++) {
    const z = normalSample(rng);
    // GBM step
    const logReturn = (drift - 0.5 * vol * vol) * dt + vol * Math.sqrt(dt) * z;
    price = price * Math.exp(logReturn);

    // Jump diffusion (Poisson-like shock)
    if (rng() < config.shockProb * dt) {
      const shockDir = rng() > 0.5 ? 1 : -1;
      price *= (1 + shockDir * config.shockMagnitude * rng());
    }

    // Floor at 10 €/MWh (market doesn't go negative in practice)
    prices[m] = Math.max(price, 10);
  }

  return prices;
}

/**
 * Generate N Monte Carlo trajectories
 * @param {Object} params
 * @param {number} params.horizonMonths
 * @param {string} params.preset
 * @param {number} params.basePrice
 * @param {number} params.iterations - max 200
 * @param {number} params.seed
 * @returns {{ trajectories: number[][], meanTrajectory: number[] }}
 */
export function generateMonteCarloTrajectories({ horizonMonths, preset, basePrice, iterations, seed }) {
  const n = Math.min(iterations, 200); // hard cap
  const rng = createRng(seed);
  const trajectories = [];

  for (let i = 0; i < n; i++) {
    trajectories.push(generateTrajectory({ horizonMonths, preset, basePrice, rng }));
  }

  // Mean trajectory
  const meanTrajectory = new Array(horizonMonths).fill(0);
  for (let m = 0; m < horizonMonths; m++) {
    for (let i = 0; i < n; i++) {
      meanTrajectory[m] += trajectories[i][m];
    }
    meanTrajectory[m] /= n;
  }

  return { trajectories, meanTrajectory };
}

/**
 * Compute deterministic scenario trajectory (no randomness)
 * @param {Object} params
 * @param {number} params.horizonMonths
 * @param {string} params.preset
 * @param {number} params.basePrice
 * @returns {number[]} monthly prices
 */
export function generateDeterministicTrajectory({ horizonMonths, preset, basePrice }) {
  const config = SCENARIO_PRESETS[preset] || SCENARIO_PRESETS[ScenarioPreset.STABLE];
  const drift = config.driftAnnual;
  const dt = 1 / 12;

  const prices = new Array(horizonMonths);
  let price = basePrice;
  for (let m = 0; m < horizonMonths; m++) {
    price = price * Math.exp(drift * dt);
    prices[m] = Math.max(price, 10);
  }
  return prices;
}
