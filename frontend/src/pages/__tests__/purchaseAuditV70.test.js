/**
 * PROMEOS — Achat Énergie V70 Audit — Source-guard + structure tests
 * Tests 100% readFileSync / regex — no DOM mock needed.
 *
 * A. Route helpers: toPurchase / toPurchaseAssistant
 * B. No hardcoded /achat-energie in models or cockpit components
 * C. Backend purchase.py: _check_seed_enabled defined
 * D. Backend purchase_seed.py: no hardcoded org_id
 * E. API functions: purchase endpoints exported
 * F. PurchasePage: CTAs, scope, deep-links
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');
const backendRoot = resolve(root, '../backend');
const readBackend = (...parts) => readFileSync(resolve(backendRoot, ...parts), 'utf-8');

// ============================================================
// A. Route Registry: toPurchase / toPurchaseAssistant
// ============================================================
describe('A · Route helpers toPurchase + toPurchaseAssistant', () => {
  const code = readSrc('services', 'routes.js');

  it('exports toPurchase', () => {
    expect(code).toContain('export function toPurchase');
  });

  it('exports toPurchaseAssistant', () => {
    expect(code).toContain('export function toPurchaseAssistant');
  });

  it('toPurchase builds /achat-energie base path', () => {
    expect(code).toContain('/achat-energie');
  });

  it('toPurchase supports filter param', () => {
    expect(code).toContain('opts.filter');
  });

  it('toPurchase supports tab param', () => {
    expect(code).toContain('opts.tab');
  });

  it('toPurchaseAssistant returns /achat-assistant', () => {
    expect(code).toContain('/achat-assistant');
  });
});

// ============================================================
// B. No hardcoded /achat-energie in models or cockpit
// ============================================================
describe('B · No hardcoded /achat-energie in models/cockpit', () => {
  it('leverEngineModel uses toPurchase import', () => {
    const code = readSrc('models', 'leverEngineModel.js');
    expect(code).toContain("import { toPurchase } from '../services/routes'");
    expect(code).toContain("toPurchase({ filter: 'renewal' })");
    expect(code).toContain("toPurchase({ filter: 'missing' })");
    // Must NOT have raw string path
    expect(code).not.toContain("'/achat-energie");
  });

  it('dataActivationModel uses toPurchase import', () => {
    const code = readSrc('models', 'dataActivationModel.js');
    expect(code).toContain("import { toPurchase } from '../services/routes'");
    expect(code).toContain('toPurchase()');
    expect(code).not.toContain("'/achat-energie");
  });

  it('ImpactDecisionPanel uses toPurchase import', () => {
    const code = readSrc('pages', 'cockpit', 'ImpactDecisionPanel.jsx');
    expect(code).toContain("import { toPurchase } from '../../services/routes'");
    expect(code).toContain("toPurchase({ filter: 'renewal' })");
    expect(code).toContain("toPurchase({ filter: 'missing' })");
    expect(code).not.toContain("navigate('/achat-energie");
  });
});

// ============================================================
// C. Backend: _check_seed_enabled defined
// ============================================================
describe('C · Backend purchase.py seed guard', () => {
  const code = readBackend('routes', 'purchase.py');

  it('defines _check_seed_enabled function', () => {
    expect(code).toContain('def _check_seed_enabled()');
  });

  it('_check_seed_enabled checks DEMO_SEED_ENABLED', () => {
    expect(code).toContain('DEMO_SEED_ENABLED');
  });

  it('_check_seed_enabled raises HTTPException when disabled', () => {
    expect(code).toContain('raise HTTPException');
    expect(code).toContain('Demo seed is disabled');
  });

  it('seed-demo endpoint calls _check_seed_enabled()', () => {
    expect(code).toContain('_check_seed_enabled()');
  });

  it('seed-wow-happy endpoint calls _check_seed_enabled()', () => {
    const matches = code.match(/_check_seed_enabled\(\)/g);
    expect(matches.length).toBeGreaterThanOrEqual(3);
  });
});

// ============================================================
// D. Backend: purchase_seed.py no hardcoded org_id
// ============================================================
describe('D · Backend purchase_seed.py org_id param', () => {
  const code = readBackend('services', 'purchase_seed.py');

  it('seed_purchase_demo accepts org_id parameter', () => {
    expect(code).toContain('def seed_purchase_demo(db: Session, org_id');
  });

  it('PurchasePreference uses org_id param (not hardcoded)', () => {
    expect(code).toContain('org_id=org_id');
  });
});

// ============================================================
// E. API: purchase endpoint functions
// ============================================================
describe('E · API purchase endpoint functions', () => {
  const code = readSrc('services', 'api.js');

  it('has /purchase/ base path', () => {
    expect(code).toContain('/purchase/');
  });

  it('exports getPurchaseRenewals', () => {
    expect(code).toContain('getPurchaseRenewals');
  });

  it('exports getPurchaseEstimate', () => {
    expect(code).toContain('getPurchaseEstimate');
  });

  it('exports computePurchaseScenarios', () => {
    expect(code).toContain('computePurchaseScenarios');
  });

  it('exports getPurchaseAssistantData', () => {
    expect(code).toContain('getPurchaseAssistantData');
  });

  it('exports getPurchaseHistory', () => {
    expect(code).toContain('getPurchaseHistory');
  });

  it('exports getPurchaseActions', () => {
    expect(code).toContain('getPurchaseActions');
  });
});

// ============================================================
// F. PurchasePage: scope + deep-links
// ============================================================
describe('F · PurchasePage scope + deep-links', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('uses useScope for org context', () => {
    expect(code).toContain('useScope');
  });

  it('uses useSearchParams for deep-linking', () => {
    expect(code).toContain('useSearchParams');
  });

  it('has simulation tab', () => {
    expect(code).toContain('simulation');
  });

  it('has portefeuille tab', () => {
    expect(code).toContain('portefeuille');
  });

  it('has echeances tab', () => {
    expect(code).toContain('echeances');
  });

  it('has historique tab', () => {
    expect(code).toContain('historique');
  });
});

// ============================================================
// G. Backend routes: purchase endpoints structure
// ============================================================
describe('G · Backend purchase routes structure', () => {
  const code = readBackend('routes', 'purchase.py');

  it('has GET /estimate/{site_id}', () => {
    expect(code).toContain('@router.get("/estimate/{site_id}")');
  });

  it('has GET /assumptions/{site_id}', () => {
    expect(code).toContain('@router.get("/assumptions/{site_id}")');
  });

  it('has PUT /assumptions/{site_id}', () => {
    expect(code).toContain('@router.put("/assumptions/{site_id}")');
  });

  it('has GET /renewals', () => {
    expect(code).toContain('@router.get("/renewals")');
  });

  it('has GET /actions', () => {
    expect(code).toContain('@router.get("/actions")');
  });

  it('has POST /compute', () => {
    expect(code).toContain('@router.post("/compute")');
  });

  it('has POST /compute/{site_id}', () => {
    expect(code).toContain('@router.post("/compute/{site_id}")');
  });

  it('has GET /results', () => {
    expect(code).toContain('@router.get("/results")');
  });

  it('has GET /results/{site_id}', () => {
    expect(code).toContain('@router.get("/results/{site_id}")');
  });

  it('has GET /history/{site_id}', () => {
    expect(code).toContain('@router.get("/history/{site_id}")');
  });

  it('has PATCH /results/{result_id}/accept', () => {
    expect(code).toContain('@router.patch("/results/{result_id}/accept")');
  });

  it('has GET /assistant', () => {
    expect(code).toContain('@router.get("/assistant")');
  });

  it('has POST /seed-demo', () => {
    expect(code).toContain('@router.post("/seed-demo")');
  });

  it('seed-demo passes org_id to seed function', () => {
    expect(code).toContain('seed_purchase_demo(db, org_id=org_id)');
  });

  it('uses Energy Gate (ALLOWED_ENERGY_TYPES)', () => {
    expect(code).toContain('ALLOWED_ENERGY_TYPES');
  });

  it('uses check_site_access for site endpoints', () => {
    expect(code).toContain('check_site_access(auth, site_id)');
  });
});
