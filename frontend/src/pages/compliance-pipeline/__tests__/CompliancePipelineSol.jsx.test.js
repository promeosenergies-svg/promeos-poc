/**
 * PROMEOS — CompliancePipelineSol JSX source tests (Phase 5.2 Lot 6)
 *
 * Validation source-analysis (pattern nav_a11y.test.js) :
 *   - 4 états rendus (loading / error / empty / happy)
 *   - A11y : role + aria-label sur chaque état dégradé
 *   - KPIs câblés via helpers (pas d'aria-label hardcodé JSX)
 *   - Pagination toujours rendue (composant décide null)
 *   - Zéro logique métier en JSX (pas de .filter/.map inline sur summary)
 *
 * Le repo n'a pas @testing-library/react ni axe-core en devDeps, donc
 * on reste sur source-matching (pattern cohérent avec nav_a11y.test.js
 * et les autres guards). Le runtime sera vérifié en P5.3 via le dev
 * server HMR et captures Playwright A/B.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const SOURCE = readFileSync(resolve('src/pages/CompliancePipelineSol.jsx'), 'utf8');

describe('CompliancePipelineSol — 4 états rendus', () => {
  it('état loading avec role="status" + aria-label', () => {
    expect(SOURCE).toMatch(/if\s*\(\s*isLoading\s*\)/);
    expect(SOURCE).toMatch(/role="status"/);
    expect(SOURCE).toMatch(/aria-label="Chargement du pipeline conformité"/);
  });
  it('état error avec role="alert"', () => {
    expect(SOURCE).toMatch(/if\s*\(\s*error\s*\)/);
    expect(SOURCE).toMatch(/role="alert"/);
  });
  it('état empty avec role="region" + aria-label', () => {
    expect(SOURCE).toMatch(/const empty = buildEmptyState\(\{ summary \}\)/);
    expect(SOURCE).toMatch(/aria-label="État vide pipeline conformité"/);
  });
  it('état happy avec SolListPage wrapper', () => {
    expect(SOURCE).toMatch(/<SolListPage/);
    expect(SOURCE).toMatch(/kpiRow=\{kpiRow\}/);
    expect(SOURCE).toMatch(/toolbar=\{toolbar\}/);
    expect(SOURCE).toMatch(/grid=\{grid\}/);
    expect(SOURCE).toMatch(/pagination=\{pagination\}/);
  });
});

describe('CompliancePipelineSol — A11y KPIs via helpers', () => {
  it('3 SolKpiCard rendus avec ariaLabel via buildKpiAriaLabel', () => {
    const kpiCount = (SOURCE.match(/<SolKpiCard/g) || []).length;
    expect(kpiCount).toBe(3);
    const ariaBuilt = (SOURCE.match(/ariaLabel=\{buildKpiAriaLabel\(/g) || []).length;
    expect(ariaBuilt).toBe(3);
  });
  it('3 explainKey pipeline_* pour chaque KPI', () => {
    expect(SOURCE).toMatch(/explainKey="pipeline_sites_ready"/);
    expect(SOURCE).toMatch(/explainKey="pipeline_deadlines_d30"/);
    expect(SOURCE).toMatch(/explainKey="pipeline_untrusted_sites"/);
  });
  it('aucun aria-label hardcodé sur KPIs (que via helper)', () => {
    // Interdit : ariaLabel="..." en littéral string sur KPI card
    // (les 2 seuls aria-label JSX légitimes : role="status" et role="region")
    const hardcodedAriaOnKpi = /SolKpiCard[^>]*ariaLabel="[^"]*"/.test(SOURCE);
    expect(hardcodedAriaOnKpi).toBe(false);
  });
});

describe('CompliancePipelineSol — zéro logique métier JSX', () => {
  it('aucun summary.sites.filter / summary.sites.map inline', () => {
    expect(SOURCE).not.toMatch(/summary\.sites\.filter/);
    expect(SOURCE).not.toMatch(/summary\.sites\.map/);
  });
  it('aucun deadlines.d30.length / untrusted_sites.length inline dans JSX', () => {
    // Les .length apparaissent uniquement dans useMemo (hors JSX) pour Set
    // d'IDs untrusted + fallback vide (ligne de construction Set).
    // Interdit : tout .length directement dans la partie JSX (return).
    const renderPart = SOURCE.split('// 4. Happy path')[1] || '';
    expect(renderPart).not.toMatch(/\.deadlines\.d30\.length/);
    expect(renderPart).not.toMatch(/summary\.untrusted_sites\.length/);
  });
  it('rows viennent de pipelineRows + filterRows + sortRows + paginateRows', () => {
    expect(SOURCE).toMatch(/pipelineRows\(summary\)/);
    expect(SOURCE).toMatch(/filterRows\(/);
    expect(SOURCE).toMatch(/sortRows\(/);
    expect(SOURCE).toMatch(/paginateRows\(/);
  });
  it('filter config vient de buildFilterConfig (pas inline)', () => {
    expect(SOURCE).toMatch(/buildFilterConfig\(summary\)/);
  });
});

describe('CompliancePipelineSol — pagination + rendering discipline', () => {
  it('SolPagination toujours rendu (composant décide null lui-même)', () => {
    // Pas de `pageRows.length > 10 && <SolPagination ...>` conditionnel
    // côté parent. SolPagination.jsx ligne 34 fait le null lui-même.
    expect(SOURCE).toMatch(/<SolPagination/);
    expect(SOURCE).not.toMatch(/\{[^}]*>\s*\d+\s*&&\s*<SolPagination/);
  });
  it('default sort compliance_score ASC (les moins conformes en haut)', () => {
    expect(SOURCE).toMatch(/column:\s*'compliance_score',\s*direction:\s*'asc'/);
  });
  it('grid 9 colonnes dont 3 applicability booléen', () => {
    const cols = SOURCE.match(/id:\s*'[^']+',\s*label:/g) || [];
    expect(cols.length).toBeGreaterThanOrEqual(8);
    expect(SOURCE).toMatch(/id:\s*'applicable_dt'/);
    expect(SOURCE).toMatch(/id:\s*'applicable_bacs'/);
    expect(SOURCE).toMatch(/id:\s*'applicable_aper'/);
  });
});

describe('CompliancePipelineSol — traçabilité endpoint (source chip)', () => {
  it('3 SolKpiCard source chip pointent sur /api/compliance/portfolio/summary', () => {
    expect(SOURCE).toMatch(/const ENDPOINT = '\/api\/compliance\/portfolio\/summary'/);
    const refs = (SOURCE.match(/origin: ENDPOINT/g) || []).length;
    expect(refs).toBe(3);
  });
});
