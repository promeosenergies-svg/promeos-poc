/**
 * Phase 26 — Source-guards migration billing/summary → _facts.billing.
 *
 * Avant Phase 26 : `useActivationData` appelait `getBillingSummary()`
 * inconditionnellement. Sur /cockpit/strategique, mesure preview prod
 * 2026-05-01 (Phase 25) montrait 2× /api/billing/summary au mount.
 *
 * Ces source-guards verrouillent l'API du nouveau contrat :
 *   1. `useActivationData` accepte un param `opts.cockpitFactsBilling`
 *   2. `useDataReadiness` propage ce param via opts
 *   3. `DataReadinessBadge` consomme `useCockpitFacts()` + passe
 *      `facts.billing` à `useDataReadiness`
 *   4. `useCockpitFacts` a un cache in-flight (dédup multi-mount)
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const FE_SRC = resolve(__dirname, '..');
const read = (p) => readFileSync(resolve(FE_SRC, p), 'utf-8');

describe('Phase 26 — Source-guards billing/summary → _facts.billing', () => {
  it('useActivationData accepte opts.cockpitFactsBilling', () => {
    const src = read('hooks/useActivationData.js');
    expect(src).toMatch(/cockpitFactsBilling/);
    expect(src).toMatch(/opts\s*=\s*\{\}/);
    // Skip getBillingSummary si cockpitFactsBilling fourni
    expect(src).toMatch(/cockpitFactsBilling\s*\n?\s*\?\s*Promise\.resolve/);
  });

  it('useActivationData skippe getBillingSummary quand cockpitFactsBilling fourni', () => {
    const src = read('hooks/useActivationData.js');
    // Pattern : `cockpitFactsBilling ? Promise.resolve(...) : getBillingSummary()`
    const billingPromiseSection = src.split('billingPromise')[1] || '';
    expect(billingPromiseSection).toMatch(/cockpitFactsBilling/);
    expect(billingPromiseSection).toMatch(/Promise\.resolve/);
    expect(billingPromiseSection).toMatch(/getBillingSummary/);
  });

  it('useDataReadiness propage cockpitFactsBilling à useActivationData', () => {
    const src = read('hooks/useDataReadiness.js');
    expect(src).toMatch(/cockpitFactsBilling/);
    // Pattern multiline-tolérant : useActivationData(<arg1>, { cockpitFactsBilling, ... })
    // Phase 26 timing fix : l'objet contient aussi `waitForFacts` désormais.
    expect(src).toMatch(/useActivationData\(([\s\S]*?)cockpitFactsBilling([\s\S]*?)\)/);
  });

  it('useDataReadiness propage waitForFacts (timing fix)', () => {
    const src = read('hooks/useDataReadiness.js');
    expect(src).toMatch(/waitForFacts/);
  });

  it('useActivationData skippe le fetch si waitForFacts && !cockpitFactsBilling', () => {
    const src = read('hooks/useActivationData.js');
    expect(src).toMatch(/waitForFacts/);
    expect(src).toMatch(/if\s*\(\s*waitForFacts\s*&&\s*!cockpitFactsBilling\s*\)\s*return/);
  });

  it('DataReadinessBadge consomme useCockpitFacts + passe facts.billing', () => {
    const src = read('components/DataReadinessBadge.jsx');
    expect(src).toMatch(/import\s+\{\s*useCockpitFacts\s*\}\s+from/);
    expect(src).toMatch(/useCockpitFacts\(['"]current_week['"]\)/);
    expect(src).toMatch(/cockpitFactsBilling:\s*cockpitFacts\?\.billing/);
  });

  it('useCockpitFacts a un cache in-flight pour dédup multi-mount', () => {
    const src = read('hooks/useCockpitFacts.js');
    expect(src).toMatch(/_inflight/);
    expect(src).toMatch(/new Map\(\)/);
    expect(src).toMatch(/_fetchOnce/);
    // Le fetch direct via getCockpitFacts(period) est wrappé
    expect(src).not.toMatch(/return getCockpitFacts\(period\)\s*\.then/);
  });
});
