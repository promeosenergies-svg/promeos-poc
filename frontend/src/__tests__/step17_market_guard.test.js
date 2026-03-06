/**
 * Step 17 — M1 : Seed prix marché EPEX Spot FR
 * Source-guard tests.
 */
import { describe, it, expect } from 'vitest';
import fs from 'fs';

describe('Step 17 — API function', () => {
  it('api.js exports getMarketPrices', () => {
    const src = fs.readFileSync('src/services/api.js', 'utf8');
    expect(src).toContain('getMarketPrices');
  });

  it('api.js calls /market/prices', () => {
    const src = fs.readFileSync('src/services/api.js', 'utf8');
    expect(src).toContain('/market/prices');
  });
});

describe('Step 17 — Glossary', () => {
  it('glossary.js has prix_marche_epex entry', () => {
    const src = fs.readFileSync('src/ui/glossary.js', 'utf8');
    expect(src).toContain('prix_marche_epex');
  });

  it('glossary.js mentions EPEX', () => {
    const src = fs.readFileSync('src/ui/glossary.js', 'utf8');
    expect(src).toContain('EPEX');
  });

  it('glossary.js mentions EUR/MWh', () => {
    const src = fs.readFileSync('src/ui/glossary.js', 'utf8');
    expect(src).toContain('EUR/MWh');
  });
});
