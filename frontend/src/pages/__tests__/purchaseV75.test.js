/**
 * PROMEOS — Achat Énergie V75 — RéFlex Simulation + Portefeuille tests
 * Tests 100% readFileSync / regex — no DOM mock needed.
 *
 * A. Report toggle + slider (Simulation)
 * B. handleCompute passes report_pct
 * C. RéFlex card: DYNAMIQUE badge, 3 bullets WHY, Créer action CTA
 * D. Portfolio: RéFlex table columns
 * E. Portfolio: top-lists (gains, risque, faciles)
 * F. Portfolio: campaign CTA
 * G. Navigation: no hardcoded URLs, route helpers
 * H. API: computePurchaseScenarios accepts report_pct
 * I. V74 backward compat preserved
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');

// ============================================================
// A. Report toggle + slider
// ============================================================
describe('A · Report toggle + slider', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('has reportEnabled state', () => {
    expect(code).toContain('const [reportEnabled, setReportEnabled] = useState(false)');
  });

  it('has reportPct state (default 0.15)', () => {
    expect(code).toContain('const [reportPct, setReportPct] = useState(0.15)');
  });

  it('has report-toggle button with data-testid', () => {
    expect(code).toContain('data-testid="report-toggle"');
  });

  it('toggle shows "Avec report" or "Sans report"', () => {
    expect(code).toContain("reportEnabled ? 'Avec report' : 'Sans report'");
  });

  it('has report-slider with data-testid (Expert)', () => {
    expect(code).toContain('data-testid="report-slider"');
  });

  it('slider is gated by isExpert', () => {
    expect(code).toContain('reportEnabled && isExpert');
  });

  it('has reflex-report-controls container', () => {
    expect(code).toContain('data-testid="reflex-report-controls"');
  });

  it('shows expert hint when not expert', () => {
    expect(code).toContain('Activez le mode Expert pour ajuster');
  });

  it('uses Sliders icon for slider', () => {
    expect(code).toContain('Sliders');
  });
});

// ============================================================
// B. handleCompute passes report_pct
// ============================================================
describe('B · handleCompute passes report_pct', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('passes report_pct to computePurchaseScenarios', () => {
    expect(code).toContain('report_pct: reportEnabled ? reportPct : 0');
  });

  it('computePurchaseScenarios called with second arg', () => {
    expect(code).toContain('computePurchaseScenarios(selectedSiteId, {');
  });
});

// ============================================================
// C. RéFlex card enhancements
// ============================================================
describe('C · RéFlex card enhancements', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('STRATEGY_META reflex_solar has dynamic: true', () => {
    expect(code).toContain('dynamic: true');
  });

  it('renders DYNAMIQUE badge with data-testid', () => {
    expect(code).toContain('data-testid="reflex-dynamic-badge"');
    expect(code).toContain('DYNAMIQUE');
  });

  it('STRATEGY_WHY reflex_solar has 3 bullet points', () => {
    // Bullets are separated by \n in the source string
    const match = code.match(/reflex_solar:\s*["'].*•.*\\n.*•.*\\n.*•/);
    expect(match).not.toBeNull();
  });

  it('Pourquoi uses whitespace-pre-line for bullet rendering', () => {
    expect(code).toContain('whitespace-pre-line');
  });

  it('has cta-create-action-reflex CTA', () => {
    expect(code).toContain('data-testid="cta-create-action-reflex"');
  });

  it('reflex action CTA prefills source_type=achat', () => {
    const match = code.match(/cta-create-action-reflex[\s\S]*?source_type:\s*'achat'/);
    expect(match).not.toBeNull();
  });

  it('still has cta-conso-explorer-reflex (V74)', () => {
    expect(code).toContain('data-testid="cta-conso-explorer-reflex"');
  });

  it('still has cta-bill-intel-reflex (V74)', () => {
    expect(code).toContain('data-testid="cta-bill-intel-reflex"');
  });
});

// ============================================================
// D. Portfolio RéFlex table
// ============================================================
describe('D · Portfolio RéFlex table', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('has reflex-portfolio-table with data-testid', () => {
    expect(code).toContain('data-testid="reflex-portfolio-table"');
  });

  it('table has Budget baseline column', () => {
    expect(code).toContain('Budget baseline');
  });

  it('table has Tarif Heures Solaires column', () => {
    expect(code).toContain('>Tarif Heures Solaires<');
  });

  it('table has Gain column', () => {
    expect(code).toContain('>Gain<');
  });

  it('table has Risque column', () => {
    expect(code).toContain('>Risque<');
  });

  it('table has Effort column', () => {
    expect(code).toContain('>Effort<');
  });

  it('table has Confiance column', () => {
    expect(code).toContain('>Confiance<');
  });

  it('displays site_nom from portfolio data', () => {
    expect(code).toContain('site.site_nom');
  });

  it('enriches sites with reflex scenario data', () => {
    expect(code).toContain("s.strategy === 'reflex_solar'");
    expect(code).toContain("s.strategy === 'fixe'");
  });
});

// ============================================================
// E. Portfolio top-lists
// ============================================================
describe('E · Portfolio top-lists', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('has reflex-top-lists container', () => {
    expect(code).toContain('data-testid="reflex-top-lists"');
  });

  it('has "Meilleurs gains Tarif Heures Solaires" top-list', () => {
    expect(code).toContain('Meilleurs gains Tarif Heures Solaires');
  });

  it('has "Risque pointe" top-list', () => {
    expect(code).toContain('Risque pointe');
  });

  it('has "Faciles à basculer" top-list', () => {
    expect(code).toContain('Faciles à basculer');
  });

  it('top-lists have 4 deep-link icons (Explorer/Diag/Facture/Action)', () => {
    expect(code).toContain('toConsoExplorer');
    expect(code).toContain('toConsoDiag');
    expect(code).toContain('toBillIntel');
    expect(code).toContain('toActionNew');
  });

  it('uses Award icon for gains list', () => {
    expect(code).toContain('Award');
  });

  it('uses Flame icon for risk list', () => {
    expect(code).toContain('Flame');
  });

  it('uses ArrowUpDown icon for easy list', () => {
    expect(code).toContain('ArrowUpDown');
  });
});

// ============================================================
// F. Campaign CTA
// ============================================================
describe('F · Campaign CTA', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('has cta-campaign-reflex with data-testid', () => {
    expect(code).toContain('data-testid="cta-campaign-reflex"');
  });

  it('campaign CTA text includes "Lancer campagne Tarif Heures Solaires"', () => {
    expect(code).toContain('Lancer campagne Tarif Heures Solaires');
  });

  it('campaign CTA passes site_ids array', () => {
    expect(code).toContain('site_ids: campaignSites.map');
  });

  it('campaign CTA passes impact_eur', () => {
    expect(code).toContain('impact_eur: campaignGainTotal');
  });

  it('uses Rocket icon', () => {
    expect(code).toContain('Rocket');
  });
});

// ============================================================
// G. Navigation: no hardcoded URLs
// ============================================================
describe('G · Navigation coherence', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('no hardcoded /consommations/ URLs', () => {
    expect(code).not.toContain("'/consommations/");
  });

  it('no hardcoded /bill-intel URLs', () => {
    expect(code).not.toContain("'/bill-intel");
  });

  it('no hardcoded /actions/ URLs', () => {
    expect(code).not.toContain("'/actions/");
  });

  it('imports toConsoDiag from routes', () => {
    expect(code).toContain('toConsoDiag');
    expect(code).toContain("from '../services/routes'");
  });
});

// ============================================================
// H. API: computePurchaseScenarios accepts report_pct
// ============================================================
describe('H · API report_pct', () => {
  const api = readSrc('services', 'api.js');

  it('computePurchaseScenarios accepts { report_pct } option', () => {
    expect(api).toContain('computePurchaseScenarios = (siteId, { report_pct }');
  });

  it('passes report_pct as query param', () => {
    expect(api).toContain('report_pct');
    expect(api).toContain('params:');
  });
});

// ============================================================
// I. V74 backward compat preserved
// ============================================================
describe('I · V74 backward compat preserved', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('still has 4 tabs', () => {
    expect(code).toContain("'simulation'");
    expect(code).toContain("'portefeuille'");
    expect(code).toContain("'echeances'");
    expect(code).toContain("'historique'");
  });

  it('still has STRATEGY_META with 4 strategies', () => {
    expect(code).toContain("label: 'Prix Fixe'");
    expect(code).toContain("label: 'Indexe'");
    expect(code).toContain("label: 'Spot'");
    expect(code).toContain("label: 'Tarif Heures Solaires'");
  });

  it('still has reflex-solar-detail (V74)', () => {
    expect(code).toContain('data-testid="reflex-solar-detail"');
  });

  it('still has reflex-badges (V74)', () => {
    expect(code).toContain('data-testid="reflex-badges"');
  });

  it('still has reflex-effort-badge (V74)', () => {
    expect(code).toContain('data-testid="reflex-effort-badge"');
  });

  it('still has scope lock (V72)', () => {
    expect(code).toContain('isScopeLocked');
  });

  it('still has autosave (V72)', () => {
    expect(code).toContain('autosaveTimer');
  });

  it('still has confidence badges (V72)', () => {
    expect(code).toContain('data-testid="confidence-badges"');
  });

  it('still has Exporter Note de Decision', () => {
    expect(code).toContain('Exporter Note de Decision');
  });

  it('still has Exporter Pack RFP', () => {
    expect(code).toContain('Exporter Pack RFP');
  });

  it('V75 header comment', () => {
    expect(code).toContain('V75: + ReFlex report toggle/slider, portfolio ReFlex table, top-lists, campaign CTA');
  });
});
