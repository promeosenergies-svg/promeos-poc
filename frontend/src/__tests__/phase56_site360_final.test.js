/**
 * phase56_site360_final.test.js — Sprint final quality gates
 *
 * Verifies the complete Site360 sprint delivery:
 *   A. Zero stubs, zero hardcoded values
 *   B. All 6 tabs active with real components
 *   C. Intelligence features (KB, savings, flex, segmentation)
 *   D. CarpetPlot integration
 *   E. Scores header + breadcrumb + accès rapide
 *   F. Backend services exist (flex, intelligence)
 */
import { describe, test, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import path from 'path';

const src = (rel) => readFileSync(path.resolve(__dirname, '..', rel), 'utf8');
const backend = (rel) =>
  readFileSync(path.resolve(__dirname, '..', '..', '..', 'backend', rel), 'utf8');

const SITE360 = src('pages/Site360.jsx');

// ── A. Zero stubs, zero hardcoded values ────────────────────────────────

describe('A. Sprint cleanliness', () => {
  test('zero TabStub in Site360', () => {
    const stubs = SITE360.split('\n').filter(
      (l) => l.includes('TabStub') && !l.includes('//') && !l.includes('import')
    );
    expect(stubs.length).toBe(0);
  });

  test('zero "Bientôt disponible" in Site360', () => {
    expect(SITE360).not.toMatch(/Bientôt disponible/);
  });

  test('no hardcoded CO2 factor 0.052', () => {
    expect(SITE360).not.toContain('0.052');
  });

  test('no hardcoded penalty 7500', () => {
    expect(SITE360).not.toContain('7500');
  });
});

// ── B. All 6 tabs active ────────────────────────────────────────────────

describe('B. 6 onglets vivants', () => {
  const expectedTabs = ['resume', 'conso', 'factures', 'reconciliation', 'conformite', 'actions'];

  test('all 6 tab IDs in TABS constant', () => {
    for (const id of expectedTabs) {
      expect(SITE360).toContain(`'${id}'`);
    }
  });

  test('TabConsoSite imported and rendered', () => {
    expect(SITE360).toMatch(/import.*TabConsoSite/);
    expect(SITE360).toMatch(/<TabConsoSite/);
  });

  test('TabActionsSite imported and rendered', () => {
    expect(SITE360).toMatch(/import.*TabActionsSite/);
    expect(SITE360).toMatch(/<TabActionsSite/);
  });

  test('TabReconciliation rendered', () => {
    expect(SITE360).toMatch(/<TabReconciliation/);
  });

  test('TabConformite rendered', () => {
    expect(SITE360).toMatch(/<TabConformite/);
  });

  test('TabResume rendered with props', () => {
    expect(SITE360).toMatch(/<TabResume.*site=/s);
  });
});

// ── C. Intelligence features ────────────────────────────────────────────

describe('C. Intelligence KB + Flex + Segmentation', () => {
  test('SiteIntelligencePanel imported and rendered', () => {
    expect(SITE360).toMatch(/import.*SiteIntelligencePanel/);
    expect(SITE360).toMatch(/<SiteIntelligencePanel/);
  });

  test('FlexPotentialCard imported and rendered', () => {
    expect(SITE360).toMatch(/FlexPotentialCard/);
    expect(SITE360).toMatch(/<FlexPotentialCard/);
  });

  test('FlexPotentialCard component file exists', () => {
    expect(
      existsSync(path.resolve(__dirname, '..', 'components', 'flex', 'FlexPotentialCard.jsx'))
    ).toBe(true);
  });

  test('SegmentationWidget imported and rendered', () => {
    expect(SITE360).toMatch(/SegmentationWidget/);
    expect(SITE360).toMatch(/<SegmentationWidget/);
  });

  test('top recommendation fetched from KB', () => {
    expect(SITE360).toMatch(/getTopRecommendation/);
  });

  test('unified anomalies (patrimoine + KB)', () => {
    expect(SITE360).toMatch(/getUnifiedAnomalies/);
    expect(SITE360).toMatch(/unifiedAnomalies/);
  });
});

// ── D. CarpetPlot ───────────────────────────────────────────────────────

describe('D. CarpetPlot integration', () => {
  test('CarpetPlot component file exists', () => {
    expect(existsSync(path.resolve(__dirname, '..', 'components', 'CarpetPlot.jsx'))).toBe(true);
  });

  test('TabConsoSite imports CarpetPlot', () => {
    const tabConso = src('components/TabConsoSite.jsx');
    expect(tabConso).toMatch(/import CarpetPlot/);
    expect(tabConso).toMatch(/<CarpetPlot/);
  });

  test('TabConsoSite fetches hourly data', () => {
    const tabConso = src('components/TabConsoSite.jsx');
    expect(tabConso).toMatch(/granularity: 'hourly'/);
  });
});

// ── E. Scores header + breadcrumb + accès rapide ────────────────────────

describe('E. Header features', () => {
  test('compliance score badge', () => {
    expect(SITE360).toMatch(/data-testid="compliance-score-badge"/);
  });

  test('completeness badge', () => {
    expect(SITE360).toMatch(/data-testid="completeness-badge"/);
  });

  test('DataQualityBadge', () => {
    expect(SITE360).toMatch(/DataQualityBadge/);
  });

  test('breadcrumb with aria-label', () => {
    expect(SITE360).toMatch(/aria-label="Fil d'Ariane"/);
  });

  test('accès rapide cross-module block', () => {
    expect(SITE360).toMatch(/Accès rapide/);
  });

  test('intensity vs benchmark', () => {
    expect(SITE360).toMatch(/getBenchmark/);
    expect(SITE360).toMatch(/intensityRatio/);
  });
});

// ── F. Backend services ─────────────────────────────────────────────────

describe('F. Backend services exist', () => {
  test('flex_assessment_service.py has compute_flex_assessment', () => {
    const svc = backend('services/flex_assessment_service.py');
    expect(svc).toMatch(/def compute_flex_assessment/);
  });

  test('flex_mini.py has compute_flex_mini', () => {
    const svc = backend('services/flex_mini.py');
    expect(svc).toMatch(/def compute_flex_mini/);
  });

  test('site_intelligence.py returns potential_savings_eur_year', () => {
    const route = backend('routes/site_intelligence.py');
    expect(route).toMatch(/potential_savings_eur_year/);
  });

  test('site_intelligence.py has /intelligence endpoint', () => {
    const route = backend('routes/site_intelligence.py');
    expect(route).toMatch(/\/intelligence/);
  });
});
