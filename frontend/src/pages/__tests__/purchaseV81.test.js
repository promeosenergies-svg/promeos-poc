/**
 * PROMEOS — V81 — THS visible & testable: header dynamique, CTA assistant, deep-link
 * Tests 100% readFileSync / regex — no DOM mock needed.
 *
 * A. Scenarios header dynamique (pas "3 stratégies" hardcodé)
 * B. CTA "Tester dans l'Assistant" dans reflex-cross-ctas
 * C. Route helper toPurchaseAssistant accepts params
 * D. Assistant deep-link support (step + offer URL params)
 * E. HEURES_SOLAIRES in demo data
 * F. No hardcoded URLs
 * G. V80 backward compat
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');

// ============================================================
// A. Scenarios header dynamique
// ============================================================
describe('A · Scenarios header dynamique', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('header uses scenarios.length, not hardcoded "3"', () => {
    expect(code).toContain('{scenarios.length} scénarios comparés');
  });

  it('no hardcoded "3 scénarios" anywhere', () => {
    expect(code).not.toContain('3 scénarios comparés');
  });

  it('fourchette uses dynamic count', () => {
    expect(code).toContain('Fourchette des {scenarios.length} scénarios');
  });

  it('no hardcoded "Fourchette des 3" anywhere', () => {
    expect(code).not.toContain('Fourchette des 3');
  });
});

// ============================================================
// B. CTA "Tester dans l'Assistant"
// ============================================================
describe("B · CTA Tester dans l'Assistant", () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('has cta-assistant-ths data-testid', () => {
    expect(code).toContain('data-testid="cta-assistant-ths"');
  });

  it('CTA text says "Tester dans l\'Assistant"', () => {
    expect(code).toContain("Tester dans l'Assistant");
  });

  it('CTA navigates via toPurchaseAssistant with step + offer + site_id', () => {
    const match = code.match(
      /cta-assistant-ths[\s\S]*?toPurchaseAssistant\(\{[\s\S]*?site_id[\s\S]*?step:\s*'offres'[\s\S]*?offer:\s*'HEURES_SOLAIRES'/
    );
    expect(match).not.toBeNull();
  });

  it('uses Rocket icon', () => {
    const match = code.match(/cta-assistant-ths[\s\S]*?Rocket/);
    expect(match).not.toBeNull();
  });

  it('CTA is inside reflex-cross-ctas container', () => {
    const block = code.match(/reflex-cross-ctas[\s\S]*?<\/div>\s*\n\s*<\/div>/);
    expect(block).not.toBeNull();
    expect(block[0]).toContain('cta-assistant-ths');
  });
});

// ============================================================
// C. Route helper toPurchaseAssistant
// ============================================================
describe('C · Route helper toPurchaseAssistant', () => {
  const routes = readSrc('services', 'routes.js');

  it('exports toPurchaseAssistant function', () => {
    expect(routes).toContain('export function toPurchaseAssistant');
  });

  it('accepts opts.site_id param', () => {
    const match = routes.match(/toPurchaseAssistant[\s\S]*?opts\.site_id/);
    expect(match).not.toBeNull();
  });

  it('accepts opts.step param', () => {
    const match = routes.match(/toPurchaseAssistant[\s\S]*?opts\.step/);
    expect(match).not.toBeNull();
  });

  it('accepts opts.offer param', () => {
    const match = routes.match(/toPurchaseAssistant[\s\S]*?opts\.offer/);
    expect(match).not.toBeNull();
  });

  it('returns /achat-assistant path', () => {
    expect(routes).toContain('/achat-assistant');
  });
});

// ============================================================
// D. Assistant deep-link support
// ============================================================
describe('D · Assistant deep-link', () => {
  const code = readSrc('pages', 'PurchaseAssistantPage.jsx');

  it('imports useSearchParams', () => {
    expect(code).toContain('useSearchParams');
  });

  it('reads step param from URL', () => {
    expect(code).toContain("searchParams.get('step')");
  });

  it('reads offer param from URL', () => {
    expect(code).toContain("searchParams.get('offer')");
  });

  it('reads site_id param from URL', () => {
    expect(code).toContain("searchParams.get('site_id')");
  });

  it('jumps to step index based on STEPS key', () => {
    const match = code.match(/STEPS\.findIndex[\s\S]*?deepLinkStep/);
    expect(match).not.toBeNull();
  });

  it('passes highlightOffer to StepOffers', () => {
    expect(code).toContain('highlightOffer={deepLinkOffer}');
  });

  it('OfferCard accepts highlighted prop', () => {
    expect(code).toContain('highlighted={highlightOffer');
  });

  it('highlighted card has ring/border styling', () => {
    expect(code).toContain('ring-2 ring-amber-200');
    expect(code).toContain('border-amber-400');
  });

  it('highlighted card has offer-highlighted testid', () => {
    expect(code).toContain("'offer-highlighted'");
  });

  it('V81 header comment in PurchaseAssistantPage', () => {
    expect(code).toContain('V81:');
  });

  it('demo button uses dynamic count', () => {
    expect(code).toContain('{DEMO_OFFERS.length} offres demo');
  });
});

// ============================================================
// E. HEURES_SOLAIRES in demo data
// ============================================================
describe('E · HEURES_SOLAIRES demo data', () => {
  const data = readSrc('domain', 'purchase', 'demoData.js');

  it('has HEURES_SOLAIRES offer', () => {
    expect(data).toContain('HEURES_SOLAIRES');
  });

  it('offer has solarSlots', () => {
    expect(data).toContain('solarSlots');
  });

  it('offer has summer + winter slots', () => {
    expect(data).toContain('summer:');
    expect(data).toContain('winter:');
  });

  it('offer has earlyTerminationPenalty: NONE', () => {
    expect(data).toContain("earlyTerminationPenalty: 'NONE'");
  });

  it('has 6 demo offers total', () => {
    const matches = data.match(/id: 'offer-/g);
    expect(matches).not.toBeNull();
    expect(matches.length).toBe(6);
  });
});

// ============================================================
// F. No hardcoded URLs
// ============================================================
describe('F · No hardcoded URLs', () => {
  const purchase = readSrc('pages', 'PurchasePage.jsx');

  it('no hardcoded /achat-assistant in PurchasePage', () => {
    expect(purchase).not.toContain("'/achat-assistant");
  });

  it('no hardcoded /monitoring in PurchasePage', () => {
    expect(purchase).not.toContain("'/monitoring");
  });

  it('no hardcoded /consommations/ in PurchasePage', () => {
    expect(purchase).not.toContain("'/consommations/");
  });

  it('no hardcoded /bill-intel in PurchasePage', () => {
    expect(purchase).not.toContain("'/bill-intel");
  });
});

// ============================================================
// G. V80 backward compat
// ============================================================
describe('G · V80 backward compat', () => {
  const code = readSrc('pages', 'PurchasePage.jsx');

  it('still has reflex-sans-penalite badge (V80)', () => {
    expect(code).toContain('data-testid="reflex-sans-penalite"');
  });

  it('still has reflex-creneaux (V78)', () => {
    expect(code).toContain('data-testid="reflex-creneaux"');
  });

  it('still has Voir performance CTA (V79)', () => {
    expect(code).toContain('data-testid="cta-perf-monitoring-reflex"');
  });

  it('still has reflex-delta-vs-fixe (V77)', () => {
    expect(code).toContain('data-testid="reflex-delta-vs-fixe"');
  });

  it('still has 4 tabs', () => {
    expect(code).toContain("'simulation'");
    expect(code).toContain("'portefeuille'");
    expect(code).toContain("'echeances'");
    expect(code).toContain("'historique'");
  });

  it('V81 header comment', () => {
    expect(code).toContain('V81:');
  });
});
