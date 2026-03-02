/**
 * PROMEOS — Performance UX V2 — Source-guard tests
 * Verify:
 * 1. 4 data-section markers present (header-pilotage, a-retenir, plan-action, details)
 * 2. No forbidden English labels in JSX
 * 3. CTA "Créer une action" present and wired to handler
 * 4. "Comprendre" CTA present and opens drawer
 * 5. Route registry usage (zero hardcoded URLs)
 * 6. Expert mode gating
 * 7. toPatrimoine route helper
 *
 * Tests 100% readFileSync / regex + unit — no DOM mock needed.
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');

// ============================================================
// A. 4 data-section markers
// ============================================================
describe('A · 4 data-section markers', () => {
  const code = readSrc('pages', 'MonitoringPage.jsx');

  it('has data-section="header-pilotage"', () => {
    expect(code).toContain('data-section="header-pilotage"');
  });

  it('has data-section="a-retenir"', () => {
    expect(code).toContain('data-section="a-retenir"');
  });

  it('has data-section="plan-action"', () => {
    expect(code).toContain('data-section="plan-action"');
  });

  it('has data-section="details"', () => {
    expect(code).toContain('data-section="details"');
  });

  it('has data-section="metriques-avancees" (expert accordion)', () => {
    expect(code).toContain('data-section="metriques-avancees"');
  });
});

// ============================================================
// B. No forbidden English labels in JSX output
// ============================================================
describe('B · No forbidden English labels', () => {
  const code = readSrc('pages', 'MonitoringPage.jsx');

  const FORBIDDEN = [
    'off-hours',      // should be "Hors horaires"
    'validated',      // should be "Validé"
    'anomaly',        // should be "Anomalie"
    '>OK<',           // bare "OK" as a visible label — except in confidence where it's expected
  ];

  FORBIDDEN.forEach((term) => {
    it(`no "${term}" in JSX (except in constants/tooltips)`, () => {
      // Match only in JSX output strings (inside > < or in template literals)
      // Allow in const definitions and comments
      const lines = code.split('\n');
      const violations = lines.filter((line, _i) => {
        const lower = line.toLowerCase();
        if (!lower.includes(term.toLowerCase())) return false;
        // Allow in const/comment/tooltip/import lines
        if (line.match(/^\s*(\/\/|\/\*|\*|const |import |export |\/\*\*)/)) return false;
        // Allow in variable names or object keys (snake_case constant mappings)
        if (line.match(/^\s+\w+:\s*'/)) return false;
        // For '>OK<' specifically, allow in confidence/status badge context
        if (term === '>OK<' && (line.includes("'OK'") || line.includes('"OK"'))) return false;
        return true;
      });
      expect(violations, `Found "${term}" in JSX output:\n${violations.join('\n')}`).toHaveLength(0);
    });
  });
});

// ============================================================
// C. CTA "Créer une action" present
// ============================================================
describe('C · CTA "Créer une action"', () => {
  const code = readSrc('pages', 'MonitoringPage.jsx');

  it('has "Créer une action" button text', () => {
    expect(code).toMatch(/Cr[eé]er une action/);
  });

  it('QuickActionsBar has primary CTA', () => {
    expect(code).toContain('Créer une action');
  });

  it('Plan d\'action section has "Créer action" CTAs', () => {
    // The plan-action section has per-priority "Créer action" buttons
    expect(code).toMatch(/data-section="plan-action"[\s\S]*?Créer action/);
  });

  it('InsightDrawer has "Créer une action" CTA', () => {
    expect(code).toContain('Créer une action');
  });
});

// ============================================================
// D. "Comprendre" CTA opens drawer
// ============================================================
describe('D · "Comprendre" CTA', () => {
  const code = readSrc('pages', 'MonitoringPage.jsx');

  it('has "Comprendre" label in ExecutiveSummary CTAs', () => {
    expect(code).toMatch(/label:\s*'Comprendre'/);
  });

  it('Comprendre on risk card calls onInsight', () => {
    // Risk card: { label: 'Comprendre', action: () => onInsight(topAlert) }
    expect(code).toMatch(/Comprendre.*onInsight/);
  });

  it('Comprendre on confidence card calls onConfidenceDetail', () => {
    // Confidence card: { label: 'Comprendre', action: onConfidenceDetail }
    expect(code).toMatch(/Comprendre.*onConfidenceDetail/);
  });

  it('ConfidenceDrawer has "Source" or "Facteurs" tab', () => {
    expect(code).toMatch(/label:\s*'Facteurs'/);
  });

  it('ConfidenceDrawer has "Confiance" info', () => {
    // The drawer displays confidence level (Forte/Moyenne/Faible)
    expect(code).toContain('Confiance données');
  });
});

// ============================================================
// E. Route registry — zero hardcoded URLs in navigate/Link
// ============================================================
describe('E · Route registry — zero hardcoded URLs', () => {
  const code = readSrc('pages', 'MonitoringPage.jsx');

  it('no navigate(\'/...\') hardcoded patterns', () => {
    const hardcoded = code.match(/navigate\(\s*['"]\/[a-z]/g);
    expect(hardcoded, 'Found hardcoded navigate() calls').toBeNull();
  });

  it('no to="/..." hardcoded Link patterns', () => {
    const hardcoded = code.match(/to="\/[a-z]/g);
    expect(hardcoded, 'Found hardcoded Link to= props').toBeNull();
  });

  it('imports toConsoExplorer from route registry', () => {
    expect(code).toMatch(/import\s*\{[^}]*toConsoExplorer[^}]*\}\s*from\s*['"]\.\.\/services\/routes['"]/);
  });

  it('imports toConsoDiag from route registry', () => {
    expect(code).toMatch(/import\s*\{[^}]*toConsoDiag[^}]*\}\s*from\s*['"]\.\.\/services\/routes['"]/);
  });

  it('imports toActionsList from route registry', () => {
    expect(code).toMatch(/import\s*\{[^}]*toActionsList[^}]*\}\s*from\s*['"]\.\.\/services\/routes['"]/);
  });

  it('imports toPatrimoine from route registry', () => {
    expect(code).toMatch(/import\s*\{[^}]*toPatrimoine[^}]*\}\s*from\s*['"]\.\.\/services\/routes['"]/);
  });
});

// ============================================================
// F. Expert mode gating
// ============================================================
describe('F · Expert mode gating', () => {
  const code = readSrc('pages', 'MonitoringPage.jsx');

  it('uses useExpertMode hook', () => {
    expect(code).toMatch(/useExpertMode/);
  });

  it('gates metriques-avancees behind isExpert', () => {
    // {isExpert && ( <details data-section="metriques-avancees" ...
    expect(code).toMatch(/isExpert\s*&&[\s\S]*?data-section="metriques-avancees"/);
  });

  it('Métriques avancées accordion uses <details> element', () => {
    expect(code).toMatch(/<details\s+data-section="metriques-avancees"/);
  });
});

// ============================================================
// G. toPatrimoine route helper
// ============================================================
describe('G · toPatrimoine route helper', () => {
  let routes;

  it('module exports toPatrimoine', async () => {
    routes = await import('../../services/routes.js');
    expect(routes.toPatrimoine).toBeTypeOf('function');
  });

  it('toPatrimoine() returns /patrimoine without params', async () => {
    routes = await import('../../services/routes.js');
    expect(routes.toPatrimoine()).toBe('/patrimoine');
  });

  it('toPatrimoine() includes site_id param', async () => {
    routes = await import('../../services/routes.js');
    const url = routes.toPatrimoine({ site_id: 42 });
    expect(url).toContain('/patrimoine?');
    expect(url).toContain('site_id=42');
  });
});

// ============================================================
// H. Plan d'action section structure
// ============================================================
describe('H · Plan d\'action section', () => {
  const code = readSrc('pages', 'MonitoringPage.jsx');

  it('has "Plan d\'action" heading', () => {
    expect(code).toContain("Plan d'action");
  });

  it('shows top 3 priorities (slice 0,3)', () => {
    expect(code).toMatch(/\.slice\(0,\s*3\)/);
  });

  it('sorts priorities by impact desc', () => {
    expect(code).toMatch(/\.sort\(\(a,\s*b\)\s*=>\s*\(b\.estimated_impact_eur/);
  });

  it('has empty state with "Aucune priorité"', () => {
    expect(code).toMatch(/Aucune priorit[eé]/);
  });

  it('shows EUR/an for each priority', () => {
    expect(code).toMatch(/EUR\/an/);
  });
});

// ============================================================
// I. "À retenir" section
// ============================================================
describe('I · "À retenir" section', () => {
  const code = readSrc('pages', 'MonitoringPage.jsx');

  it('has "À retenir" heading', () => {
    expect(code).toContain('À retenir');
  });

  it('contains ExecutiveSummary inside a-retenir section', () => {
    expect(code).toMatch(/data-section="a-retenir"[\s\S]*?<ExecutiveSummary/);
  });

  it('ExecutiveSummary has 4+ card definitions (including THS)', () => {
    // cards array has risk, waste, confidence, CO₂e, Tarif Heures Solaires
    expect(code).toMatch(/Risque principal/);
    expect(code).toMatch(/Gaspillage estim[eé]/);
    expect(code).toMatch(/Confiance donn[eé]es/);
    expect(code).toMatch(/Tarif Heures Solaires/);
  });

  it('has kpi-tarif-heures-solaires testid', () => {
    expect(code).toContain('kpi-tarif-heures-solaires');
  });

  it('THS card has "Simuler" CTA linking to toPurchase', () => {
    expect(code).toContain('toPurchase');
  });

  it('imports toPurchase from routes', () => {
    expect(code).toContain('toPurchase');
    expect(code).toContain("from '../services/routes'");
  });

  it('no hardcoded /achat-energie in MonitoringPage', () => {
    expect(code).not.toContain("'/achat-energie");
  });

  it('V79 header comment', () => {
    expect(code).toContain('V79:');
  });
});

// ============================================================
// J. Hors horaires label fix (no "Off-hours" in French UI)
// ============================================================
describe('J · "Hors horaires" label consistency', () => {
  const code = readSrc('pages', 'MonitoringPage.jsx');

  it('waste card sub uses "Hors horaires" not "Off-hours"', () => {
    // In the ExecutiveSummary waste card sub text
    const execSummaryBlock = code.slice(
      code.indexOf('function ExecutiveSummary'),
      code.indexOf('function QuickActionsBar')
    );
    expect(execSummaryBlock).not.toMatch(/Off-hours:\s*\$\{/);
    expect(execSummaryBlock).toContain('Hors horaires');
  });
});
