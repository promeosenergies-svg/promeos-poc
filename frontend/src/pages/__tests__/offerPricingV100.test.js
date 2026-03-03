/**
 * PROMEOS — V100 Offer Pricing V1 + Reconciliation Tests
 * Source-guard tests for backend wiring, feature flag, and deprecated constants.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const read = (rel) => readFileSync(resolve(__dirname, '..', '..', rel), 'utf-8');

// ── API Functions ──────────────────────────────────────────────────

describe('api.js V100 offer pricing functions', () => {
  const code = read('services/api.js');

  it('exports quoteOffer', () => {
    expect(code).toMatch(/export\s+(const|function)\s+quoteOffer/);
  });

  it('exports quoteMultiStrategy', () => {
    expect(code).toMatch(/export\s+(const|function)\s+quoteMultiStrategy/);
  });

  it('exports reconcileOfferVsInvoice', () => {
    expect(code).toMatch(/export\s+(const|function)\s+reconcileOfferVsInvoice/);
  });

  it('calls /purchase/quote-offer endpoint', () => {
    expect(code).toMatch(/\/purchase\/quote-offer/);
  });

  it('calls /purchase/quote-multi endpoint', () => {
    expect(code).toMatch(/\/purchase\/quote-multi/);
  });

  it('calls /purchase/reconcile endpoint', () => {
    expect(code).toMatch(/\/purchase\/reconcile/);
  });
});

// ── Feature Flag ───────────────────────────────────────────────────

describe('types.js V100 feature flag', () => {
  const code = read('domain/purchase/types.js');

  it('exports USE_BACKEND_PRICING flag', () => {
    expect(code).toMatch(/export\s+const\s+USE_BACKEND_PRICING/);
  });

  it('USE_BACKEND_PRICING defaults to true', () => {
    expect(code).toMatch(/USE_BACKEND_PRICING\s*=\s*true/);
  });

  it('marks BREAKDOWN_DEFAULTS_ELEC as deprecated', () => {
    expect(code).toMatch(/@deprecated/);
    expect(code).toMatch(/BREAKDOWN_DEFAULTS_ELEC/);
  });
});

// ── Engine V100 Wiring ─────────────────────────────────────────────

describe('engine.js V100 wiring', () => {
  const code = read('domain/purchase/engine.js');

  it('imports USE_BACKEND_PRICING from types', () => {
    expect(code).toMatch(/USE_BACKEND_PRICING/);
  });

  it('re-exports USE_BACKEND_PRICING', () => {
    expect(code).toMatch(/export\s*\{.*USE_BACKEND_PRICING.*\}/);
  });
});

// ── Assumptions Deprecation ────────────────────────────────────────

describe('assumptions.js V100 deprecation', () => {
  const code = read('domain/purchase/assumptions.js');

  it('marks DEFAULT_MARKET as deprecated', () => {
    expect(code).toMatch(/@deprecated/);
  });

  it('still exports DEFAULT_MARKET for backward compat', () => {
    expect(code).toMatch(/export\s+const\s+DEFAULT_MARKET/);
  });
});

// ── Backend Services ───────────────────────────────────────────────

describe('backend offer_pricing_v1.py exists', () => {
  const code = read('../../backend/services/offer_pricing_v1.py');

  it('has compute_offer_quote function', () => {
    expect(code).toMatch(/def compute_offer_quote/);
  });

  it('has compute_multi_strategy_quotes function', () => {
    expect(code).toMatch(/def compute_multi_strategy_quotes/);
  });

  it('uses tax_catalog_service', () => {
    expect(code).toMatch(/tax_catalog_service/);
  });

  it('has STRATEGY_FACTORS', () => {
    expect(code).toMatch(/STRATEGY_FACTORS/);
  });

  it('returns offer_v1 model version', () => {
    expect(code).toMatch(/offer_v1/);
  });

  it('has convert_eur_mwh_to_eur_kwh helper', () => {
    expect(code).toMatch(/def convert_eur_mwh_to_eur_kwh/);
  });

  it('has safe_div helper', () => {
    expect(code).toMatch(/def safe_div/);
  });
});

describe('backend offer_invoice_reconcile_v1.py exists', () => {
  const code = read('../../backend/services/offer_invoice_reconcile_v1.py');

  it('has reconcile_offer_vs_invoice function', () => {
    expect(code).toMatch(/def reconcile_offer_vs_invoice/);
  });

  it('has reconcile_offer_vs_shadow function', () => {
    expect(code).toMatch(/def reconcile_offer_vs_shadow/);
  });

  it('computes component deltas', () => {
    expect(code).toMatch(/_compute_component_deltas/);
  });

  it('builds explanations', () => {
    expect(code).toMatch(/_build_explanations/);
  });

  it('assesses confidence level', () => {
    expect(code).toMatch(/confidence/);
  });
});

describe('backend purchase.py V100 endpoints', () => {
  const code = read('../../backend/routes/purchase.py');

  it('has quote-offer endpoint', () => {
    expect(code).toMatch(/\/quote-offer/);
  });

  it('has quote-multi endpoint', () => {
    expect(code).toMatch(/\/quote-multi/);
  });

  it('has reconcile endpoint', () => {
    expect(code).toMatch(/\/reconcile/);
  });

  it('has QuoteOfferRequest schema', () => {
    expect(code).toMatch(/class\s+QuoteOfferRequest/);
  });

  it('has ReconcileRequest schema', () => {
    expect(code).toMatch(/class\s+ReconcileRequest/);
  });

  it('imports offer_pricing_v1', () => {
    expect(code).toMatch(/offer_pricing_v1/);
  });

  it('imports offer_invoice_reconcile_v1', () => {
    expect(code).toMatch(/offer_invoice_reconcile_v1/);
  });
});
