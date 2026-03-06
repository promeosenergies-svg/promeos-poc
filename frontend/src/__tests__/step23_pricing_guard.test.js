/**
 * Step 23 — Modèle pricing réaliste (forward + spread + cap)
 * Source-guard tests: vérifie que les fichiers contiennent les patterns attendus.
 */
import fs from 'fs';
import { describe, it, expect } from 'vitest';

const readFront = (...parts) => fs.readFileSync(`src/${parts.join('/')}`, 'utf8');
const readBack = (...parts) => fs.readFileSync(`../backend/${parts.join('/')}`, 'utf8');

// ── A. purchase_pricing.py — pricing engine ──
describe('A. purchase_pricing engine', () => {
  const src = readBack('services', 'purchase_pricing.py');

  it('has get_market_context function', () => {
    expect(src).toContain('def get_market_context');
  });

  it('has compute_strategy_price function', () => {
    expect(src).toContain('def compute_strategy_price');
  });

  it('computes forward price for fixe strategy', () => {
    expect(src).toContain('terme_premium');
    expect(src).toContain('supplier_margin');
  });

  it('has spread for indexe strategy', () => {
    expect(src).toContain('spread');
    expect(src).toContain('cap');
  });

  it('has aggregator_fee for spot strategy', () => {
    expect(src).toContain('aggregator_fee');
  });

  it('returns price in EUR/MWh and EUR/kWh', () => {
    expect(src).toContain('price_eur_mwh');
    expect(src).toContain('price_eur_kwh');
  });

  it('includes breakdown and methodology', () => {
    expect(src).toContain('breakdown');
    expect(src).toContain('methodology');
  });

  it('computes volatility and risk_score', () => {
    expect(src).toContain('volatility');
    expect(src).toContain('risk_score');
  });
});

// ── B. purchase_service.py — integration ──
describe('B. purchase_service integration', () => {
  const src = readBack('services', 'purchase_service.py');

  it('imports from purchase_pricing', () => {
    expect(src).toContain('from services.purchase_pricing import');
  });

  it('calls get_market_context', () => {
    expect(src).toContain('get_market_context');
  });

  it('calls compute_strategy_price', () => {
    expect(src).toContain('compute_strategy_price');
  });

  it('attaches market_context to scenarios', () => {
    expect(src).toContain('market_context');
  });
});

// ── C. market route — context endpoint ──
describe('C. market context endpoint', () => {
  const src = readBack('routes', 'market.py');

  it('has /context endpoint', () => {
    expect(src).toContain('/context');
  });

  it('calls get_market_context', () => {
    expect(src).toContain('get_market_context');
  });
});

// ── D. api.js — getMarketContext ──
describe('D. api.js market context', () => {
  const src = readFront('services', 'api.js');

  it('exports getMarketContext', () => {
    expect(src).toContain('getMarketContext');
  });

  it('calls /market/context', () => {
    expect(src).toContain('/market/context');
  });
});

// ── E. glossary — pricing terms ──
describe('E. glossary pricing terms', () => {
  const src = readFront('ui', 'glossary.js');

  it('has forward_price entry', () => {
    expect(src).toContain('forward_price');
  });

  it('has spread_fournisseur entry', () => {
    expect(src).toContain('spread_fournisseur');
  });
});
