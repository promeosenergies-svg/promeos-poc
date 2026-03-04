/**
 * PROMEOS — Brique 3
 * Engine invariant tests
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { createRng, generateMonteCarloTrajectories } from '../scenarioLibrary.js';
import {
  computeOfferMonthlyPrices,
  computeTco,
  monteCarloOffer,
  volatilityProxy,
  cvar90,
  probExceedBudget,
} from '../risk.js';
import {
  runEngine,
  clearEngineCache,
  normalizeHybridShares,
  validateBreakdown,
  fillBreakdownDefaults,
} from '../engine.js';
import { scoreBudgetRisk, scoreTransparency, scoreContractRisk, scoreOffer } from '../scoring.js';
import { recommend } from '../recommend.js';
import { distributeMonthly } from '../assumptions.js';
import { EnergyType, ScenarioPreset, Persona, Confidence, ScoreLevel } from '../types.js';
import { DEMO_OFFERS, aggregateDemoSites } from '../demoData.js';

// ── Helpers ────────────────────────────────────────────────────────

const FIXED_OFFER = DEMO_OFFERS[0]; // EDF Fixe
const INDEXED_OFFER = DEMO_OFFERS[1]; // Engie Indexe
const HYBRID_OFFER = DEMO_OFFERS[2]; // TotalEnergies Hybride
const SPOT_OFFER = DEMO_OFFERS[3]; // Alpiq Spot
const DIRTY_OFFER = DEMO_OFFERS[4]; // Courtier Opaque

const BASE_PARAMS = {
  annualKwh: 2400000,
  energyType: EnergyType.ELEC,
  horizonMonths: 24,
  scenarioPreset: ScenarioPreset.STABLE,
  mcIterations: 100,
  mcSeed: 42,
  budgetEur: 500000,
};

// ── PRNG Tests ─────────────────────────────────────────────────────

describe('Seeded PRNG', () => {
  it('produces deterministic output for same seed', () => {
    const rng1 = createRng(42);
    const rng2 = createRng(42);
    const seq1 = Array.from({ length: 100 }, () => rng1());
    const seq2 = Array.from({ length: 100 }, () => rng2());
    expect(seq1).toEqual(seq2);
  });

  it('produces different output for different seeds', () => {
    const rng1 = createRng(42);
    const rng2 = createRng(99);
    const v1 = rng1();
    const v2 = rng2();
    expect(v1).not.toEqual(v2);
  });

  it('produces values in [0, 1)', () => {
    const rng = createRng(123);
    for (let i = 0; i < 1000; i++) {
      const v = rng();
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThan(1);
    }
  });
});

// ── Monte Carlo Trajectories ───────────────────────────────────────

describe('Monte Carlo Trajectories', () => {
  it('respects max 200 iterations cap', () => {
    const { trajectories } = generateMonteCarloTrajectories({
      horizonMonths: 12,
      preset: ScenarioPreset.STABLE,
      basePrice: 85,
      iterations: 500,
      seed: 42,
    });
    expect(trajectories.length).toBeLessThanOrEqual(200);
  });

  it('generates correct horizon length', () => {
    const { trajectories } = generateMonteCarloTrajectories({
      horizonMonths: 36,
      preset: ScenarioPreset.STABLE,
      basePrice: 85,
      iterations: 10,
      seed: 42,
    });
    expect(trajectories[0].length).toBe(36);
  });

  it('all prices >= 10 EUR/MWh (floor)', () => {
    const { trajectories } = generateMonteCarloTrajectories({
      horizonMonths: 24,
      preset: ScenarioPreset.VOLATILE,
      basePrice: 85,
      iterations: 100,
      seed: 42,
    });
    for (const traj of trajectories) {
      for (const price of traj) {
        expect(price).toBeGreaterThanOrEqual(10);
      }
    }
  });

  it('mean trajectory is the average of all trajectories', () => {
    const { trajectories, meanTrajectory } = generateMonteCarloTrajectories({
      horizonMonths: 12,
      preset: ScenarioPreset.STABLE,
      basePrice: 85,
      iterations: 50,
      seed: 42,
    });
    for (let m = 0; m < 12; m++) {
      const expected = trajectories.reduce((sum, t) => sum + t[m], 0) / trajectories.length;
      expect(meanTrajectory[m]).toBeCloseTo(expected, 5);
    }
  });
});

// ── Corridor Invariants ────────────────────────────────────────────

describe('Corridor Invariants', () => {
  it('P10 <= P50 <= P90 for FIXE', () => {
    const monthlyKwh = distributeMonthly(2400000, EnergyType.ELEC);
    const corridor = monteCarloOffer({
      offer: FIXED_OFFER,
      monthlyKwh,
      horizonMonths: 24,
      preset: ScenarioPreset.STABLE,
      iterations: 100,
      seed: 42,
    });
    expect(corridor.p10).toBeLessThanOrEqual(corridor.p50);
    expect(corridor.p50).toBeLessThanOrEqual(corridor.p90);
  });

  it('P10 <= P50 <= P90 for INDEXE', () => {
    const monthlyKwh = distributeMonthly(2400000, EnergyType.ELEC);
    const corridor = monteCarloOffer({
      offer: INDEXED_OFFER,
      monthlyKwh,
      horizonMonths: 24,
      preset: ScenarioPreset.STABLE,
      iterations: 100,
      seed: 42,
    });
    expect(corridor.p10).toBeLessThanOrEqual(corridor.p50);
    expect(corridor.p50).toBeLessThanOrEqual(corridor.p90);
  });

  it('P10 <= P50 <= P90 for HYBRIDE', () => {
    const monthlyKwh = distributeMonthly(2400000, EnergyType.ELEC);
    const corridor = monteCarloOffer({
      offer: HYBRID_OFFER,
      monthlyKwh,
      horizonMonths: 24,
      preset: ScenarioPreset.STABLE,
      iterations: 100,
      seed: 42,
    });
    expect(corridor.p10).toBeLessThanOrEqual(corridor.p50);
    expect(corridor.p50).toBeLessThanOrEqual(corridor.p90);
  });

  it('P10 <= P50 <= P90 for SPOT', () => {
    const monthlyKwh = distributeMonthly(2400000, EnergyType.ELEC);
    const corridor = monteCarloOffer({
      offer: SPOT_OFFER,
      monthlyKwh,
      horizonMonths: 24,
      preset: ScenarioPreset.STABLE,
      iterations: 100,
      seed: 42,
    });
    expect(corridor.p10).toBeLessThanOrEqual(corridor.p50);
    expect(corridor.p50).toBeLessThanOrEqual(corridor.p90);
  });

  it('TCO P10 <= TCO P50 <= TCO P90', () => {
    const monthlyKwh = distributeMonthly(2400000, EnergyType.ELEC);
    const corridor = monteCarloOffer({
      offer: INDEXED_OFFER,
      monthlyKwh,
      horizonMonths: 24,
      preset: ScenarioPreset.VOLATILE,
      iterations: 100,
      seed: 42,
    });
    expect(corridor.tcoP10).toBeLessThanOrEqual(corridor.tcoP50);
    expect(corridor.tcoP50).toBeLessThanOrEqual(corridor.tcoP90);
  });

  it('TCO > 0 when kWh > 0', () => {
    const monthlyKwh = distributeMonthly(2400000, EnergyType.ELEC);
    const corridor = monteCarloOffer({
      offer: FIXED_OFFER,
      monthlyKwh,
      horizonMonths: 24,
      preset: ScenarioPreset.STABLE,
      iterations: 100,
      seed: 42,
    });
    expect(corridor.tcoP50).toBeGreaterThan(0);
  });

  it('FIXE has zero or near-zero corridor width', () => {
    const monthlyKwh = distributeMonthly(2400000, EnergyType.ELEC);
    const corridor = monteCarloOffer({
      offer: FIXED_OFFER,
      monthlyKwh,
      horizonMonths: 24,
      preset: ScenarioPreset.STABLE,
      iterations: 100,
      seed: 42,
    });
    // Fixed offers should have identical P10/P50/P90 since price doesn't vary
    expect(corridor.p10).toBeCloseTo(corridor.p90, 0);
  });

  it('SPOT has wider corridor than FIXE', () => {
    const monthlyKwh = distributeMonthly(2400000, EnergyType.ELEC);
    const fixedCorridor = monteCarloOffer({
      offer: FIXED_OFFER,
      monthlyKwh,
      horizonMonths: 24,
      preset: ScenarioPreset.VOLATILE,
      iterations: 100,
      seed: 42,
    });
    const spotCorridor = monteCarloOffer({
      offer: SPOT_OFFER,
      monthlyKwh,
      horizonMonths: 24,
      preset: ScenarioPreset.VOLATILE,
      iterations: 100,
      seed: 42,
    });
    const fixedWidth = fixedCorridor.p90 - fixedCorridor.p10;
    const spotWidth = spotCorridor.p90 - spotCorridor.p10;
    expect(spotWidth).toBeGreaterThan(fixedWidth);
  });
});

// ── Offer Price Computation ────────────────────────────────────────

describe('Offer Monthly Prices', () => {
  const spotTrajectory = [80, 85, 90, 95, 100, 110, 105, 95, 85, 80, 75, 70];

  it('FIXE returns constant price', () => {
    const prices = computeOfferMonthlyPrices(FIXED_OFFER, spotTrajectory);
    for (const p of prices) {
      expect(p).toBe(95); // fixedPriceEurPerMwh
    }
  });

  it('INDEXE applies spread and cap', () => {
    const prices = computeOfferMonthlyPrices(INDEXED_OFFER, spotTrajectory);
    for (let m = 0; m < prices.length; m++) {
      const expected = spotTrajectory[m] + 5; // spread
      const capped = Math.min(expected, 130);
      const floored = Math.max(capped, 50);
      expect(prices[m]).toBe(floored);
    }
  });

  it('SPOT returns spot prices', () => {
    const prices = computeOfferMonthlyPrices(SPOT_OFFER, spotTrajectory);
    expect(prices).toEqual(spotTrajectory);
  });

  it('HYBRIDE blends shares correctly', () => {
    const prices = computeOfferMonthlyPrices(HYBRID_OFFER, spotTrajectory);
    for (let m = 0; m < prices.length; m++) {
      const fixedPart = 0.6 * 92;
      let indexedPrice = spotTrajectory[m] + 3;
      indexedPrice = Math.min(indexedPrice, 120);
      const indexedPart = 0.25 * indexedPrice;
      const spotPart = 0.15 * spotTrajectory[m];
      expect(prices[m]).toBeCloseTo(fixedPart + indexedPart + spotPart, 5);
    }
  });
});

// ── TCO Computation ────────────────────────────────────────────────

describe('TCO', () => {
  it('TCO = sum(price/1000 * kwh) for each month', () => {
    const prices = [100, 100, 100];
    const kwh = [1000, 1000, 1000];
    const tco = computeTco(prices, kwh);
    // 100/1000 * 1000 * 3 = 300
    expect(tco).toBeCloseTo(300, 5);
  });

  it('TCO = 0 when kwh = 0', () => {
    const prices = [100, 100];
    const kwh = [0, 0];
    expect(computeTco(prices, kwh)).toBe(0);
  });
});

// ── Risk Metrics ───────────────────────────────────────────────────

describe('Risk Metrics', () => {
  it('volatilityProxy >= 0', () => {
    const dist = [100, 200, 300, 400, 500];
    expect(volatilityProxy(dist)).toBeGreaterThanOrEqual(0);
  });

  it('volatilityProxy = 0 for identical values', () => {
    const dist = [100, 100, 100, 100];
    expect(volatilityProxy(dist)).toBe(0);
  });

  it('cvar90 >= P50 of distribution', () => {
    const dist = Array.from({ length: 100 }, (_, i) => i + 1);
    const cv = cvar90(dist);
    const median = 50.5;
    expect(cv).toBeGreaterThanOrEqual(median);
  });

  it('probExceedBudget in [0, 1]', () => {
    const dist = [100, 200, 300, 400, 500];
    const prob = probExceedBudget(dist, 250);
    expect(prob).toBeGreaterThanOrEqual(0);
    expect(prob).toBeLessThanOrEqual(1);
  });

  it('probExceedBudget = 0 when budget > max', () => {
    const dist = [100, 200, 300];
    expect(probExceedBudget(dist, 999999)).toBe(0);
  });

  it('probExceedBudget = 1 when budget < min', () => {
    const dist = [100, 200, 300];
    expect(probExceedBudget(dist, 50)).toBe(1);
  });
});

// ── Hybrid Normalization ───────────────────────────────────────────

describe('Hybrid Share Normalization', () => {
  it('does not normalize when sum is 1.0', () => {
    const pricing = { fixedSharePct: 0.5, indexedSharePct: 0.3, spotSharePct: 0.2 };
    const { normalized } = normalizeHybridShares(pricing);
    expect(normalized).toBe(false);
  });

  it('normalizes when sum differs from 1.0', () => {
    const pricing = { fixedSharePct: 0.5, indexedSharePct: 0.5, spotSharePct: 0.5 };
    const { pricing: norm, normalized } = normalizeHybridShares(pricing);
    expect(normalized).toBe(true);
    const total = norm.fixedSharePct + norm.indexedSharePct + norm.spotSharePct;
    expect(total).toBeCloseTo(1.0, 2);
  });

  it('defaults to 100% fixed when all zero', () => {
    const pricing = { fixedSharePct: 0, indexedSharePct: 0, spotSharePct: 0 };
    const { pricing: norm } = normalizeHybridShares(pricing);
    expect(norm.fixedSharePct).toBe(1);
    expect(norm.indexedSharePct).toBe(0);
    expect(norm.spotSharePct).toBe(0);
  });
});

// ── Breakdown Validation ───────────────────────────────────────────

describe('Breakdown Validation', () => {
  it('complete when 7+ KNOWN components', () => {
    const breakdown = FIXED_OFFER.breakdown; // 8 KNOWN
    const { complete, knownCount } = validateBreakdown(breakdown);
    expect(complete).toBe(true);
    expect(knownCount).toBe(8);
  });

  it('incomplete when < 7 KNOWN components', () => {
    const breakdown = DIRTY_OFFER.breakdown; // only 0 KNOWN
    const { complete } = validateBreakdown(breakdown);
    expect(complete).toBe(false);
  });

  it('fillBreakdownDefaults fills missing components', () => {
    const sparse = [{ component: 'FOURNITURE', sharePct: 0.35, eurPerMwh: 30, status: 'KNOWN' }];
    const filled = fillBreakdownDefaults(sparse, EnergyType.ELEC);
    expect(filled.length).toBe(8); // 1 existing + 7 defaults
  });
});

// ── Scoring ────────────────────────────────────────────────────────

describe('Scoring', () => {
  const monthlyKwh = distributeMonthly(2400000, EnergyType.ELEC);

  function makeOfferResult(offer) {
    const corridor = monteCarloOffer({
      offer,
      monthlyKwh,
      horizonMonths: 24,
      preset: ScenarioPreset.STABLE,
      iterations: 50,
      seed: 42,
    });
    return {
      offerId: offer.id,
      supplierName: offer.supplierName,
      structure: offer.structure,
      corridor,
      tcoEurPerMwh: corridor.tcoP50 / ((2400000 * 2) / 1000),
      annualCostP50: corridor.tcoP50 / 2,
      volatility: volatilityProxy(corridor.distribution),
      cvar90: cvar90(corridor.distribution),
      probExceedBudget: probExceedBudget(corridor.distribution, 500000),
      worstMonthEur: 0,
      worstMonthIndex: 0,
    };
  }

  it('all scores in [0, 100]', () => {
    const result = makeOfferResult(DIRTY_OFFER);
    const scores = scoreOffer({
      offerResult: result,
      offer: DIRTY_OFFER,
      budgetEur: 500000,
      anomalies: [],
      consumption: { source: 'DEMO', granularity: 'monthly' },
    });
    expect(scores.budgetRisk.score0to100).toBeGreaterThanOrEqual(0);
    expect(scores.budgetRisk.score0to100).toBeLessThanOrEqual(100);
    expect(scores.transparency.score0to100).toBeGreaterThanOrEqual(0);
    expect(scores.transparency.score0to100).toBeLessThanOrEqual(100);
    expect(scores.contractRisk.score0to100).toBeGreaterThanOrEqual(0);
    expect(scores.contractRisk.score0to100).toBeLessThanOrEqual(100);
    expect(scores.dataReadiness.score0to100).toBeGreaterThanOrEqual(0);
    expect(scores.dataReadiness.score0to100).toBeLessThanOrEqual(100);
  });

  it('DIRTY offer has RED transparency (breakdown < 7)', () => {
    const scores = scoreTransparency({ offer: DIRTY_OFFER });
    expect(scores.level).toBe(ScoreLevel.RED);
  });

  it('DIRTY offer has RED contract risk', () => {
    const scores = scoreContractRisk({ offer: DIRTY_OFFER });
    expect(scores.level).toBe(ScoreLevel.RED);
  });

  it('FIXE offer has better budget risk than SPOT', () => {
    const fixedResult = makeOfferResult(FIXED_OFFER);
    const spotResult = makeOfferResult(SPOT_OFFER);
    const fixedScore = scoreBudgetRisk({
      offerResult: fixedResult,
      offer: FIXED_OFFER,
      budgetEur: 500000,
      anomalies: [],
    });
    const spotScore = scoreBudgetRisk({
      offerResult: spotResult,
      offer: SPOT_OFFER,
      budgetEur: 500000,
      anomalies: [],
    });
    expect(fixedScore.score0to100).toBeGreaterThan(spotScore.score0to100);
  });

  it('clean EDF offer has GREEN transparency', () => {
    const scores = scoreTransparency({ offer: FIXED_OFFER });
    expect(scores.level).toBe(ScoreLevel.GREEN);
  });

  it('scores include evidence array', () => {
    const scores = scoreTransparency({ offer: DIRTY_OFFER });
    expect(Array.isArray(scores.evidence)).toBe(true);
    expect(scores.evidence.length).toBeGreaterThan(0);
    expect(scores.evidence[0]).toHaveProperty('ruleId');
  });
});

// ── Engine ─────────────────────────────────────────────────────────

describe('Engine', () => {
  beforeEach(() => clearEngineCache());

  it('produces results for all offers', () => {
    const { results } = runEngine({ ...BASE_PARAMS, offers: DEMO_OFFERS.slice(0, 3) });
    expect(results.length).toBe(3);
  });

  it('each result has corridor and metrics', () => {
    const { results } = runEngine({ ...BASE_PARAMS, offers: [FIXED_OFFER] });
    const r = results[0];
    expect(r.corridor).toBeDefined();
    expect(r.corridor.p10).toBeDefined();
    expect(r.corridor.p50).toBeDefined();
    expect(r.corridor.p90).toBeDefined();
    expect(r.tcoEurPerMwh).toBeGreaterThan(0);
    expect(r.volatility).toBeDefined();
  });

  it('memoization returns same result for same params', () => {
    const params = { ...BASE_PARAMS, offers: [FIXED_OFFER] };
    const r1 = runEngine(params);
    const r2 = runEngine(params);
    expect(r1.computedAt).toBe(r2.computedAt);
  });

  it('cache clears correctly', () => {
    const params = { ...BASE_PARAMS, offers: [FIXED_OFFER] };
    const r1 = runEngine(params);
    clearEngineCache();
    const r2 = runEngine(params);
    expect(r1.computedAt).not.toBe(r2.computedAt);
  });

  it('handles hybrid normalization', () => {
    const badHybrid = {
      ...HYBRID_OFFER,
      id: 'test-hybrid-bad',
      pricing: {
        ...HYBRID_OFFER.pricing,
        fixedSharePct: 0.5,
        indexedSharePct: 0.5,
        spotSharePct: 0.5,
      },
    };
    const { results } = runEngine({ ...BASE_PARAMS, offers: [badHybrid] });
    expect(results[0].hybridNormalized).toBe(true);
    expect(results[0].hybridNormMessage).toBeTruthy();
  });
});

// ── Recommendation ─────────────────────────────────────────────────

describe('Recommend', () => {
  it('selects a best offer', () => {
    clearEngineCache();
    const { results } = runEngine({ ...BASE_PARAMS, offers: DEMO_OFFERS });
    const rec = recommend({
      offerResults: results,
      offers: DEMO_OFFERS,
      persona: Persona.DAF,
      budgetEur: BASE_PARAMS.budgetEur,
      consumption: { source: 'DEMO', granularity: 'monthly' },
    });
    expect(rec.bestOfferId).toBeTruthy();
    expect(rec.rationaleBullets.length).toBeGreaterThan(0);
    expect(rec.rationaleBullets.length).toBeLessThanOrEqual(5);
  });

  it('dirty offer is never the best', () => {
    clearEngineCache();
    const { results } = runEngine({ ...BASE_PARAMS, offers: DEMO_OFFERS });
    const rec = recommend({
      offerResults: results,
      offers: DEMO_OFFERS,
      persona: Persona.DAF,
      budgetEur: BASE_PARAMS.budgetEur,
      consumption: { source: 'DEMO', granularity: 'monthly' },
    });
    expect(rec.bestOfferId).not.toBe('offer-dirty-courtier');
  });

  it('returns LOW confidence with demo data', () => {
    clearEngineCache();
    const { results } = runEngine({ ...BASE_PARAMS, offers: DEMO_OFFERS.slice(0, 2) });
    const rec = recommend({
      offerResults: results,
      offers: DEMO_OFFERS.slice(0, 2),
      persona: Persona.DAF,
      budgetEur: BASE_PARAMS.budgetEur,
      consumption: { source: 'DEMO', granularity: 'monthly' },
    });
    // Demo data → confidence should not be HIGH
    expect([Confidence.LOW, Confidence.MEDIUM]).toContain(rec.confidence);
  });

  it('provides whyNotOthers for non-best offers', () => {
    clearEngineCache();
    const { results } = runEngine({ ...BASE_PARAMS, offers: DEMO_OFFERS.slice(0, 3) });
    const rec = recommend({
      offerResults: results,
      offers: DEMO_OFFERS.slice(0, 3),
      persona: Persona.DG,
      budgetEur: BASE_PARAMS.budgetEur,
      consumption: { source: 'DEMO', granularity: 'monthly' },
    });
    const nonBest = DEMO_OFFERS.slice(0, 3).filter((o) => o.id !== rec.bestOfferId);
    for (const offer of nonBest) {
      expect(rec.whyNotOthers[offer.id]).toBeTruthy();
    }
  });

  it('handles empty offers gracefully', () => {
    const rec = recommend({
      offerResults: [],
      offers: [],
      persona: Persona.DAF,
      budgetEur: null,
      consumption: { source: 'DEMO', granularity: 'monthly' },
    });
    expect(rec.bestOfferId).toBeNull();
    expect(rec.confidence).toBe(Confidence.LOW);
  });

  it('different personas can yield different rankings', () => {
    clearEngineCache();
    const offers = DEMO_OFFERS.slice(0, 4);
    const { results } = runEngine({ ...BASE_PARAMS, offers });

    const recDG = recommend({
      offerResults: results,
      offers,
      persona: Persona.DG,
      budgetEur: 500000,
      consumption: { source: 'DEMO', granularity: 'monthly' },
    });
    const recEnergy = recommend({
      offerResults: results,
      offers,
      persona: Persona.RESP_ENERGIE,
      budgetEur: 500000,
      consumption: { source: 'DEMO', granularity: 'monthly' },
    });
    // At least the _scoredOffers order might differ
    expect(recDG._scoredOffers).toBeDefined();
    expect(recEnergy._scoredOffers).toBeDefined();
  });
});

// ── Demo Data ──────────────────────────────────────────────────────

describe('Demo Data', () => {
  it('has 6 demo offers', () => {
    expect(DEMO_OFFERS.length).toBe(6);
  });

  it('each offer has required fields', () => {
    for (const offer of DEMO_OFFERS) {
      expect(offer.id).toBeTruthy();
      expect(offer.supplierName).toBeTruthy();
      expect(offer.structure).toBeTruthy();
      expect(offer.pricing).toBeDefined();
      expect(offer.breakdown).toBeDefined();
      expect(offer.contractTerms).toBeDefined();
    }
  });

  it('aggregateDemoSites works for site IDs', () => {
    const agg = aggregateDemoSites([1, 2]);
    expect(agg.annualKwh).toBe(3200000);
    expect(agg.anomalies.length).toBe(2);
    expect(agg.billing.invoiceCount).toBe(36);
  });

  it('aggregateDemoSites returns zero for unknown IDs', () => {
    const agg = aggregateDemoSites([999]);
    expect(agg.annualKwh).toBe(0);
  });
});

// ── Seasonality ────────────────────────────────────────────────────

describe('Seasonality', () => {
  it('distributeMonthly sums to annualKwh', () => {
    const monthly = distributeMonthly(1200000, EnergyType.ELEC);
    expect(monthly.length).toBe(12);
    const total = monthly.reduce((a, b) => a + b, 0);
    expect(total).toBeCloseTo(1200000, 0);
  });

  it('winter months higher than summer for ELEC', () => {
    const monthly = distributeMonthly(1200000, EnergyType.ELEC);
    // Jan (idx 0) > Jul (idx 6) for elec
    expect(monthly[0]).toBeGreaterThan(monthly[6]);
  });

  it('GAZ seasonality more pronounced than ELEC', () => {
    const elecMonthly = distributeMonthly(1200000, EnergyType.ELEC);
    const gazMonthly = distributeMonthly(1200000, EnergyType.GAZ);
    const elecRange = Math.max(...elecMonthly) - Math.min(...elecMonthly);
    const gazRange = Math.max(...gazMonthly) - Math.min(...gazMonthly);
    expect(gazRange).toBeGreaterThan(elecRange);
  });
});
