/**
 * PROMEOS — Achat Énergie V73 Audit — Route, scope, CTA, deep-link tests
 * Tests 100% readFileSync / regex — no DOM mock needed.
 *
 * A. toPurchaseAssistant route fix (was /achat-energie/assistant → now /achat-assistant)
 * B. Scope lock "Changer" fix (scopeOverride state)
 * C. skipSiteHeader on portfolio/renewals calls
 * D. Renewals re-fetch on scope change (orgId passed)
 * E. Tab deep-link (?tab= param support)
 * F. orgName dynamic (no hardcoded "PROMEOS")
 * G. Empty state text consistency + Assistant CTA
 * H. Breadcrumb label for achat-assistant
 * I. V72 backward compat preserved
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');

// ============================================================
// A. toPurchaseAssistant route fix
// ============================================================
describe('A · toPurchaseAssistant route fix', () => {
  const routes = readSrc('services', 'routes.js');

  it('toPurchaseAssistant returns /achat-assistant (not /achat-energie/assistant)', () => {
    expect(routes).toContain('/achat-assistant');
    expect(routes).not.toContain('/achat-energie/assistant');
  });

  it('toPurchaseAssistant is still exported', () => {
    expect(routes).toContain('export function toPurchaseAssistant');
  });

  it('toPurchase still exported (unchanged)', () => {
    expect(routes).toContain('export function toPurchase');
  });
});

// ============================================================
// B. Scope lock "Changer" fix — scopeOverride
// ============================================================
describe('B · Scope lock Changer fix', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('has scopeOverride state', () => {
    expect(code).toContain('const [scopeOverride, setScopeOverride] = useState(false)');
  });

  it('isScopeLocked uses scopeOverride', () => {
    expect(code).toContain('const isScopeLocked = !!scopeSiteId && !scopeOverride');
  });

  it('"Changer" CTA sets scopeOverride to true', () => {
    expect(code).toContain('setScopeOverride(true)');
  });

  it('scope change resets scopeOverride to false', () => {
    expect(code).toContain('setScopeOverride(false)');
  });

  it('still has data-testid="cta-change-site"', () => {
    expect(code).toContain('data-testid="cta-change-site"');
  });

  it('still has data-testid="scope-locked-site"', () => {
    expect(code).toContain('data-testid="scope-locked-site"');
  });
});

// ============================================================
// C. skipSiteHeader on portfolio/renewals calls
// ============================================================
describe('C · skipSiteHeader on org-wide calls', () => {
  const api = readSrc('services', 'api.js');

  it('computePortfolio uses skipSiteHeader: true', () => {
    // Must contain skipSiteHeader in the computePortfolio call
    const match = api.match(/computePortfolio[\s\S]*?skipSiteHeader:\s*true/);
    expect(match).not.toBeNull();
  });

  it('getPortfolioResults uses skipSiteHeader: true', () => {
    const match = api.match(/getPortfolioResults[\s\S]*?skipSiteHeader:\s*true/);
    expect(match).not.toBeNull();
  });

  it('getPurchaseRenewals uses skipSiteHeader: true', () => {
    const match = api.match(/getPurchaseRenewals[\s\S]*?skipSiteHeader:\s*true/);
    expect(match).not.toBeNull();
  });
});

// ============================================================
// D. Renewals re-fetch on scope change
// ============================================================
describe('D · Renewals re-fetch on scope change', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('passes orgId to getPurchaseRenewals', () => {
    expect(code).toContain('getPurchaseRenewals(orgId)');
  });

  it('uses renewalsOrgRef to track org changes', () => {
    expect(code).toContain('renewalsOrgRef');
  });

  it('scope.orgId is in the useEffect dependency array', () => {
    expect(code).toContain('scope.orgId, toast');
  });
});

// ============================================================
// E. Tab deep-link (?tab= param)
// ============================================================
describe('E · Tab deep-link', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('reads ?tab= from searchParams', () => {
    expect(code).toContain("searchParams.get('tab')");
  });

  it('validates tab against VALID_TABS set', () => {
    expect(code).toContain('VALID_TABS');
  });

  it('toPurchase still supports tab param', () => {
    const routes = readSrc('services', 'routes.js');
    expect(routes).toContain("opts.tab");
  });
});

// ============================================================
// F. orgName dynamic
// ============================================================
describe('F · orgName dynamic (no hardcoded PROMEOS)', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('ExportPackRFP uses scope.org?.nom (not hardcoded)', () => {
    expect(code).toContain("scope.org?.nom || 'Organisation'");
    expect(code).not.toContain('orgName="PROMEOS"');
  });
});

// ============================================================
// G. Empty state text + Assistant CTA
// ============================================================
describe('G · Empty state consistency + Assistant CTA', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('empty state says "Comparer les scénarios" (not "Calculer")', () => {
    expect(code).toContain('Comparer les scénarios');
    // Should not contain the old "Calculer les scénarios" in the empty state
    expect(code).not.toContain('Calculer les scénarios');
  });

  it('has CTA to Assistant Achat with data-testid', () => {
    expect(code).toContain('data-testid="cta-assistant-achat"');
  });

  it('imports toPurchaseAssistant from routes', () => {
    expect(code).toContain('toPurchaseAssistant');
  });

  it('Assistant CTA navigates via toPurchaseAssistant()', () => {
    expect(code).toContain('navigate(toPurchaseAssistant())');
  });
});

// ============================================================
// H. Breadcrumb label
// ============================================================
describe('H · Breadcrumb label for achat-assistant', () => {
  const code = readSrc('layout', 'Breadcrumb.jsx');

  it('has label for achat-assistant', () => {
    expect(code).toContain("'achat-assistant': 'Assistant Achat'");
  });
});

// ============================================================
// I. V72 backward compat preserved
// ============================================================
describe('I · V72 backward compat preserved', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('still has 4 tabs', () => {
    expect(code).toContain("'simulation'");
    expect(code).toContain("'portefeuille'");
    expect(code).toContain("'echeances'");
    expect(code).toContain("'historique'");
  });

  it('still has FILTER_TO_TAB', () => {
    expect(code).toContain("renewal: 'echeances'");
    expect(code).toContain("missing: 'portefeuille'");
  });

  it('still has scope lock (V72)', () => {
    expect(code).toContain('isScopeLocked');
    expect(code).toContain('data-testid="scope-locked-site"');
  });

  it('still has volume toggle (V72)', () => {
    expect(code).toContain('data-testid="volume-toggle"');
    expect(code).toContain('useEstimation');
  });

  it('still has autosave (V72)', () => {
    expect(code).toContain('autosaveTimer');
    expect(code).toContain('autosave');
  });

  it('still has confidence badges (V72)', () => {
    expect(code).toContain('data-testid="confidence-badges"');
  });

  it('still has scenarios cockpit (V71)', () => {
    expect(code).toContain('data-section="scenarios-cockpit"');
  });

  it('still has "Créer action" + "Voir les actions" CTAs (V71)', () => {
    expect(code).toContain('Créer action');
    expect(code).toContain('Voir les actions');
  });

  it('still has Exporter Note de Decision', () => {
    expect(code).toContain('Exporter Note de Decision');
  });

  it('V73 header comment', () => {
    expect(code).toContain('V73: + Scope unlock fix, skipSiteHeader, tab deep-link, assistant CTA, renewals re-fetch');
  });
});
