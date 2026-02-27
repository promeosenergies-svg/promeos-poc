/**
 * PROMEOS — Achat Énergie V72 — UX V2 tests
 * Tests 100% readFileSync / regex — no DOM mock needed.
 *
 * A. Scope lock: isScopeLocked, scope-aware selection, CTA "Changer"
 * B. Single CTA: "Comparer les scénarios" — no double "Sauvegarder"
 * C. Volume toggle: estimation vs manuel
 * D. Autosave: debounced save on assumption/preference change
 * E. Confidence badges
 * F. V71 backward compat preserved
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');

// ============================================================
// A. Scope lock
// ============================================================
describe('A · Scope lock', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('destructures selectedSiteId as scopeSiteId from useScope', () => {
    expect(code).toContain('selectedSiteId: scopeSiteId');
  });

  it('defines isScopeLocked from scopeSiteId', () => {
    expect(code).toContain('const isScopeLocked = !!scopeSiteId');
  });

  it('has scope-locked site indicator with data-testid', () => {
    expect(code).toContain('data-testid="scope-locked-site"');
  });

  it('shows Lock icon when scope is locked', () => {
    expect(code).toContain('<Lock');
    expect(code).toContain('isScopeLocked');
  });

  it('has "Changer" CTA with data-testid', () => {
    expect(code).toContain('data-testid="cta-change-site"');
    expect(code).toContain('Changer');
  });

  it('shows open site selector when scope is NOT locked', () => {
    expect(code).toContain('data-testid="site-selector-open"');
  });

  it('scope-aware useEffect pre-selects scopeSiteId', () => {
    expect(code).toContain('if (scopeSiteId)');
    expect(code).toContain('setSelectedSiteId(scopeSiteId)');
  });

  it('falls back to first site when scope has no site', () => {
    expect(code).toContain('scopedSites[0].id');
  });
});

// ============================================================
// B. Single CTA — no double "Sauvegarder"
// ============================================================
describe('B · Single CTA — no double Sauvegarder', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('has "Comparer les scénarios" CTA with data-testid', () => {
    expect(code).toContain('data-testid="cta-comparer-scenarios"');
    expect(code).toContain('Comparer les scénarios');
  });

  it('does NOT have handleSaveAssumptions', () => {
    expect(code).not.toContain('handleSaveAssumptions');
  });

  it('does NOT have handleSavePreferences', () => {
    expect(code).not.toContain('handleSavePreferences');
  });

  it('does NOT have savingAssumptions state', () => {
    expect(code).not.toContain('savingAssumptions');
  });

  it('does NOT have savingPrefs state', () => {
    expect(code).not.toContain('savingPrefs');
  });

  it('CTA calls handleCompute', () => {
    expect(code).toContain('onClick={handleCompute}');
  });

  it('handleCompute saves assumptions before computing', () => {
    expect(code).toContain('await putPurchaseAssumptions(selectedSiteId, assumptions)');
    expect(code).toContain('await putPurchasePreferences(preferences)');
    expect(code).toContain('await computePurchaseScenarios(selectedSiteId,');
  });
});

// ============================================================
// C. Volume toggle: estimation vs manual
// ============================================================
describe('C · Volume toggle', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('has useEstimation state', () => {
    expect(code).toContain('const [useEstimation, setUseEstimation] = useState(true)');
  });

  it('has volume-toggle button with data-testid', () => {
    expect(code).toContain('data-testid="volume-toggle"');
  });

  it('toggle shows "Estimation" when useEstimation is true', () => {
    expect(code).toContain("useEstimation ? 'Estimation' : 'Manuel'");
  });

  it('has estimation display with data-testid', () => {
    expect(code).toContain('data-testid="volume-estimation"');
  });

  it('has manual input with data-testid', () => {
    expect(code).toContain('data-testid="volume-manual"');
  });

  it('uses ToggleLeft and ToggleRight icons', () => {
    expect(code).toContain('ToggleLeft');
    expect(code).toContain('ToggleRight');
  });

  it('syncs volume from estimate when toggling to estimation', () => {
    expect(code).toContain('if (useEstimation && estimate)');
    expect(code).toContain('estimate.volume_kwh_an');
  });
});

// ============================================================
// D. Autosave
// ============================================================
describe('D · Autosave', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('has autosaveTimer ref', () => {
    expect(code).toContain('const autosaveTimer = useRef(null)');
  });

  it('defines autosave callback', () => {
    expect(code).toContain('const autosave = useCallback(');
  });

  it('autosave uses 1500ms debounce', () => {
    expect(code).toContain('1500');
  });

  it('autosave calls putPurchaseAssumptions and putPurchasePreferences', () => {
    expect(code).toContain('putPurchaseAssumptions(selectedSiteId, assumptions)');
    expect(code).toContain('putPurchasePreferences(preferences)');
  });

  it('autosave triggered via useEffect', () => {
    expect(code).toContain('useEffect(() => { autosave(); }, [autosave])');
  });
});

// ============================================================
// E. Confidence badges
// ============================================================
describe('E · Confidence badges', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('has confidence-badges container with data-testid', () => {
    expect(code).toContain('data-testid="confidence-badges"');
  });

  it('uses BadgeCheck icon', () => {
    expect(code).toContain('BadgeCheck');
  });

  it('shows "Relevé réel" for compteur source', () => {
    expect(code).toContain('Relevé réel');
  });

  it('shows "Estimé" for non-compteur source', () => {
    expect(code).toContain("estimate.source === 'compteur' ? 'Relevé réel' : 'Estimé'");
  });

  it('shows months covered badge', () => {
    expect(code).toContain('estimate.months_covered');
  });
});

// ============================================================
// F. V71 backward compat preserved
// ============================================================
describe('F · V71 backward compat preserved', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('still has 4 tabs (simulation, portefeuille, echeances, historique)', () => {
    expect(code).toContain("'simulation'");
    expect(code).toContain("'portefeuille'");
    expect(code).toContain("'echeances'");
    expect(code).toContain("'historique'");
  });

  it('still uses useScope', () => {
    expect(code).toContain('useScope');
  });

  it('still uses useSearchParams for deep-linking', () => {
    expect(code).toContain('useSearchParams');
  });

  it('still has FILTER_TO_TAB for renewal/missing', () => {
    expect(code).toContain('FILTER_TO_TAB');
    expect(code).toContain("renewal: 'echeances'");
    expect(code).toContain("missing: 'portefeuille'");
  });

  it('still has Exporter Note de Decision', () => {
    expect(code).toContain('Exporter Note de Decision');
  });

  it('still imports computePurchaseScenarios', () => {
    expect(code).toContain('computePurchaseScenarios');
  });

  it('still has STRATEGY_META (fixe/indexe/spot)', () => {
    expect(code).toContain('STRATEGY_META');
    expect(code).toContain("label: 'Prix Fixe'");
    expect(code).toContain("label: 'Indexe'");
    expect(code).toContain("label: 'Spot'");
  });

  it('still has scenarios cockpit (V71)', () => {
    expect(code).toContain('data-section="scenarios-cockpit"');
    expect(code).toContain('data-testid="scenario-kpi-strip"');
  });

  it('still has "Créer action" CTA (V71)', () => {
    expect(code).toContain('Créer action');
    expect(code).toContain("source: 'purchase'");
  });

  it('still has "Voir les actions" CTA (V71)', () => {
    expect(code).toContain('data-testid="cta-voir-actions-purchase"');
    expect(code).toContain('Voir les actions');
  });

  it('still imports toActionNew and toActionsList (V71)', () => {
    expect(code).toContain('toActionNew');
    expect(code).toContain('toActionsList');
    expect(code).toContain("from '../services/routes'");
  });

  it('V72 header comment', () => {
    expect(code).toContain('V72: + Scope lock, autosave, volume toggle, confidence badges');
  });
});
