/**
 * PROMEOS — Achat Énergie V74 RéFlex Solar — Source-guard tests
 * Tests 100% readFileSync / regex — no DOM mock needed.
 *
 * A. STRATEGY_META: reflex_solar entry (icon, color, label, desc)
 * B. STRATEGY_WHY: reflex_solar entry (non-empty)
 * C. RéFlex card: badges (Budget / Risque / Effort), blocs detail, report %
 * D. Cross-brique CTAs: toConsoExplorer + toBillIntel
 * E. Grid layout: 4-column on lg
 * F. Routes/imports: toConsoExplorer, toBillIntel imported
 * G. V73 backward compat preserved
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');

// ============================================================
// A. STRATEGY_META: reflex_solar entry
// ============================================================
describe('A · STRATEGY_META reflex_solar', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('has reflex_solar key in STRATEGY_META', () => {
    expect(code).toContain("reflex_solar: {");
  });

  it("reflex_solar label is 'ReFlex Solar'", () => {
    expect(code).toContain("label: 'ReFlex Solar'");
  });

  it('reflex_solar uses Sun icon', () => {
    expect(code).toContain('icon: Sun');
  });

  it("reflex_solar color is 'amber'", () => {
    expect(code).toContain("color: 'amber'");
  });

  it('reflex_solar has a desc string', () => {
    expect(code).toContain("desc: 'Blocs horaires solaires/pointe");
  });
});

// ============================================================
// B. STRATEGY_WHY: reflex_solar entry (non-empty)
// ============================================================
describe('B · STRATEGY_WHY reflex_solar', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('has reflex_solar key in STRATEGY_WHY', () => {
    const match = code.match(/STRATEGY_WHY\s*=\s*\{[\s\S]*?reflex_solar:\s*["']/);
    expect(match).not.toBeNull();
  });

  it('reflex_solar WHY mentions blocs horaires solaires', () => {
    expect(code).toContain('blocs horaires solaires');
  });

  it('reflex_solar WHY mentions report', () => {
    expect(code).toContain('Report optionnel');
  });
});

// ============================================================
// C. RéFlex card: badges, blocs, report
// ============================================================
describe('C · RéFlex card detail', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('renders reflex-solar-detail container', () => {
    expect(code).toContain('data-testid="reflex-solar-detail"');
  });

  it('conditionally renders for reflex_solar strategy', () => {
    expect(code).toContain("s.strategy === 'reflex_solar'");
  });

  it('has reflex-badges container', () => {
    expect(code).toContain('data-testid="reflex-badges"');
  });

  it('shows Budget badge', () => {
    expect(code).toContain('Budget');
    // Budget badge shows savings_vs_current_pct
    expect(code).toContain('savings_vs_current_pct');
  });

  it('shows Risque badge', () => {
    // reflex badges section has a Risque badge
    const match = code.match(/reflex-badges[\s\S]*?Risque\s*\{s\.risk_score\}/);
    expect(match).not.toBeNull();
  });

  it('shows Effort badge with data-testid', () => {
    expect(code).toContain('data-testid="reflex-effort-badge"');
    expect(code).toContain('Effort');
    expect(code).toContain('effort_score');
  });

  it('has reflex-blocs-detail expandable section', () => {
    expect(code).toContain('data-testid="reflex-blocs-detail"');
  });

  it('renders bloc names and prices', () => {
    expect(code).toContain('b.bloc');
    expect(code).toContain('b.weight_pct');
    expect(code).toContain('b.price_eur_kwh');
  });

  it('shows report percentage when > 0', () => {
    expect(code).toContain('data-testid="reflex-report-pct"');
    expect(code).toContain('Report HP');
    expect(code).toContain('report_pct');
  });
});

// ============================================================
// D. Cross-brique CTAs
// ============================================================
describe('D · Cross-brique CTAs', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('has reflex-cross-ctas container', () => {
    expect(code).toContain('data-testid="reflex-cross-ctas"');
  });

  it('has "Voir preuves conso" CTA with data-testid', () => {
    expect(code).toContain('data-testid="cta-conso-explorer-reflex"');
    expect(code).toContain('Voir preuves conso');
  });

  it('Conso CTA navigates via toConsoExplorer', () => {
    expect(code).toContain('toConsoExplorer(');
  });

  it('has "Contrôler facture" CTA with data-testid', () => {
    expect(code).toContain('data-testid="cta-bill-intel-reflex"');
    expect(code).toContain('Contrôler facture');
  });

  it('Bill CTA navigates via toBillIntel', () => {
    expect(code).toContain('toBillIntel(');
  });

  it('both CTAs pass selectedSiteId as site_id', () => {
    const consoMatch = code.match(/toConsoExplorer\(\{[^}]*site_id:\s*selectedSiteId/);
    expect(consoMatch).not.toBeNull();
    const billMatch = code.match(/toBillIntel\(\{[^}]*site_id:\s*selectedSiteId/);
    expect(billMatch).not.toBeNull();
  });

  it('no hardcoded URLs in cross-brique CTAs', () => {
    // Should use route helpers, not raw strings
    expect(code).not.toContain("'/consommations/explorer");
    expect(code).not.toContain("'/bill-intel");
  });
});

// ============================================================
// E. Grid layout
// ============================================================
describe('E · Grid layout updated for 4 cards', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('scenario grid uses lg:grid-cols-4', () => {
    expect(code).toContain('lg:grid-cols-4');
  });

  it('scenario grid uses md:grid-cols-2 for medium screens', () => {
    expect(code).toContain('md:grid-cols-2');
  });
});

// ============================================================
// F. Routes/imports
// ============================================================
describe('F · Routes and imports', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('imports toConsoExplorer from routes', () => {
    expect(code).toContain('toConsoExplorer');
    expect(code).toContain("from '../services/routes'");
  });

  it('imports toBillIntel from routes', () => {
    expect(code).toContain('toBillIntel');
  });

  it('imports Sun icon from lucide-react', () => {
    expect(code).toContain('Sun');
    expect(code).toContain("from 'lucide-react'");
  });

  it('imports BarChart3 icon', () => {
    expect(code).toContain('BarChart3');
  });

  it('imports FileSearch icon', () => {
    expect(code).toContain('FileSearch');
  });
});

// ============================================================
// G. V73 backward compat preserved
// ============================================================
describe('G · V73 backward compat preserved', () => {
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

  it('still has scopeOverride (V73)', () => {
    expect(code).toContain('scopeOverride');
  });

  it('still has volume toggle (V72)', () => {
    expect(code).toContain('data-testid="volume-toggle"');
    expect(code).toContain('useEstimation');
  });

  it('still has autosave (V72)', () => {
    expect(code).toContain('autosaveTimer');
  });

  it('still has confidence badges (V72)', () => {
    expect(code).toContain('data-testid="confidence-badges"');
  });

  it('still has scenarios cockpit (V71)', () => {
    expect(code).toContain('data-section="scenarios-cockpit"');
  });

  it('still has 3 classic strategies in STRATEGY_META', () => {
    expect(code).toContain("label: 'Prix Fixe'");
    expect(code).toContain("label: 'Indexe'");
    expect(code).toContain("label: 'Spot'");
  });

  it('still has "Créer action" + "Voir les actions" CTAs (V71)', () => {
    expect(code).toContain('Créer action');
    expect(code).toContain('Voir les actions');
  });

  it('still has Exporter Note de Decision', () => {
    expect(code).toContain('Exporter Note de Decision');
  });

  it('still has assistant CTA (V73)', () => {
    expect(code).toContain('data-testid="cta-assistant-achat"');
    expect(code).toContain('toPurchaseAssistant');
  });

  it('V74 header comment', () => {
    expect(code).toContain('V74: + ReFlex Solar card, blocs horaires badges, effort score, cross-brique CTAs');
  });
});
