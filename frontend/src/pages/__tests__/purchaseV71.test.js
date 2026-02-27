/**
 * PROMEOS — Achat Énergie V71 — Scénarios cockpit + Actions CTAs
 * Tests 100% readFileSync / regex — no DOM mock needed.
 *
 * A. Scénarios 2026–2030: KPI strip + "Pourquoi ?" + data-sections
 * B. Actions CTAs: Créer action préremplie + Voir actions deep-link
 * C. Empty state guidé
 * D. Route helpers: toActionNew + toActionsList imported
 * E. V70 backward compat preserved
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');

// ============================================================
// A. Scénarios 2026–2030 cockpit
// ============================================================
describe('A · Scénarios 2026–2030 cockpit', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('has data-section="scenarios-cockpit"', () => {
    expect(code).toContain('data-section="scenarios-cockpit"');
  });

  it('has KPI strip with data-testid="scenario-kpi-strip"', () => {
    expect(code).toContain('data-testid="scenario-kpi-strip"');
  });

  it('shows Budget annuel KPI', () => {
    expect(code).toContain('Budget annuel');
  });

  it('shows Risque moyen KPI', () => {
    expect(code).toContain('Risque moyen');
  });

  it('shows Recommandation KPI', () => {
    expect(code).toContain('Recommandation');
  });

  it('renders scenario cards with data-testid', () => {
    expect(code).toContain('data-testid={`scenario-card-${s.strategy}`}');
  });

  it('has "Pourquoi ?" details for each strategy', () => {
    expect(code).toContain('data-testid={`scenario-why-${s.strategy}`}');
    expect(code).toContain('Pourquoi cette');
  });

  it('defines STRATEGY_WHY with fixe/indexe/spot explanations', () => {
    expect(code).toContain('STRATEGY_WHY');
    expect(code).toContain('Budget prévisible');
    expect(code).toContain('indice marché');
    expect(code).toContain('temps réel');
  });

  it('displays horizon and volume in subtitle', () => {
    expect(code).toContain('assumptions.horizon_months');
    expect(code).toContain('assumptions.volume_kwh_an');
  });

  it('shows fourchette des N stratégies (dynamic)', () => {
    expect(code).toContain('Fourchette des {scenarios.length} stratégies');
  });
});

// ============================================================
// B. Actions CTAs
// ============================================================
describe('B · Actions CTAs', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('imports toActionNew from routes', () => {
    expect(code).toContain("toActionNew");
    expect(code).toContain("toActionsList");
    expect(code).toContain("from '../services/routes'");
  });

  it('has "Créer action" CTA per accepted scenario', () => {
    expect(code).toContain('data-testid={`cta-create-action-${s.strategy}`}');
    expect(code).toContain('Créer action');
  });

  it('"Créer action" passes source=purchase', () => {
    expect(code).toContain("source: 'purchase'");
  });

  it('"Créer action" passes source_type=achat', () => {
    expect(code).toContain("source_type: 'achat'");
  });

  it('"Créer action" passes site_id', () => {
    expect(code).toContain('site_id: selectedSiteId');
  });

  it('"Créer action" passes title with strategy label', () => {
    expect(code).toContain('title: `Achat');
    expect(code).toContain('meta.label');
  });

  it('"Créer action" passes impact_eur when savings > 0', () => {
    expect(code).toContain('impact_eur:');
    expect(code).toContain('savings_vs_current_pct');
  });

  it('has "Voir les actions" CTA with data-testid', () => {
    expect(code).toContain('data-testid="cta-voir-actions-purchase"');
    expect(code).toContain('Voir les actions');
  });

  it('"Voir les actions" navigates to action list filtered by achat', () => {
    expect(code).toContain("toActionsList({ source_type: 'achat' })");
  });

  it('imports useNavigate', () => {
    expect(code).toContain('useNavigate');
  });
});

// ============================================================
// C. Empty state guidé
// ============================================================
describe('C · Empty state guidé', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('has guided empty state with data-testid', () => {
    expect(code).toContain('data-testid="empty-state-scenarios"');
  });

  it('empty state shows instruction text', () => {
    expect(code).toContain('Aucun scénario calculé');
    expect(code).toContain('Comparer les scénarios');
  });
});

// ============================================================
// D. Route helpers used correctly
// ============================================================
describe('D · Route helpers integration', () => {
  const routes = readSrc('services', 'routes.js');

  it('toActionNew is exported', () => {
    expect(routes).toContain('export function toActionNew');
  });

  it('toActionsList is exported', () => {
    expect(routes).toContain('export function toActionsList');
  });

  it('toPurchase still exported (V70)', () => {
    expect(routes).toContain('export function toPurchase');
  });
});

// ============================================================
// E. V70 backward compat
// ============================================================
describe('E · V70 backward compat preserved', () => {
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

  it('still shows STRATEGY_META (fixe/indexe/spot)', () => {
    expect(code).toContain('STRATEGY_META');
    expect(code).toContain("label: 'Prix Fixe'");
    expect(code).toContain("label: 'Indexe'");
    expect(code).toContain("label: 'Spot'");
  });
});
