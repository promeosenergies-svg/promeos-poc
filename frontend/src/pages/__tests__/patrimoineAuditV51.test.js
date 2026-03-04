/**
 * PROMEOS V51 — Patrimoine Audit: routing guards + API contract + CTA integrity
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const src = (rel) => fs.readFileSync(path.resolve(__dirname, '..', '..', rel), 'utf-8');

// ═══════════════════════════════════════════════════════════════════════════════
// 1. Router — Patrimoine routes exist
// ═══════════════════════════════════════════════════════════════════════════════

describe('Router defines Patrimoine routes', () => {
  const app = src('App.jsx');

  it('has /patrimoine route', () => {
    expect(app).toContain('/patrimoine');
  });

  it('has /sites/:id route', () => {
    expect(app).toContain('/sites/:id');
  });

  it('lazy-loads Patrimoine page', () => {
    expect(app).toContain("import('./pages/Patrimoine')");
  });

  it('lazy-loads Site360 page', () => {
    expect(app).toContain("import('./pages/Site360')");
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// 2. NavRegistry — Patrimoine in navigation
// ═══════════════════════════════════════════════════════════════════════════════

describe('NavRegistry includes Patrimoine', () => {
  const nav = src('layout/NavRegistry.js');

  it('has /patrimoine route-module mapping', () => {
    expect(nav).toContain("'/patrimoine'");
  });

  it('has Patrimoine nav item with Building2 icon', () => {
    expect(nav).toContain('Building2');
    expect(nav).toContain('Patrimoine');
  });

  it('includes patrimoine in donnees section', () => {
    expect(nav).toContain('donnees');
    expect(nav).toContain('/patrimoine');
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// 3. API contract — all patrimoine endpoints covered
// ═══════════════════════════════════════════════════════════════════════════════

describe('API service covers all patrimoine endpoints', () => {
  const api = src('services/api.js');

  // Staging
  it('exports stagingImport', () => expect(api).toContain('stagingImport'));
  it('exports stagingSummary', () => expect(api).toContain('stagingSummary'));
  it('exports stagingRows', () => expect(api).toContain('stagingRows'));
  it('exports stagingIssues', () => expect(api).toContain('stagingIssues'));
  it('exports stagingValidate', () => expect(api).toContain('stagingValidate'));
  it('exports stagingFix ', () => expect(api).toContain('stagingFix'));
  it('exports stagingAutofix', () => expect(api).toContain('stagingAutofix'));
  it('exports stagingActivate', () => expect(api).toContain('stagingActivate'));
  it('exports stagingResult', () => expect(api).toContain('stagingResult'));
  it('exports stagingAbandon', () => expect(api).toContain('stagingAbandon'));

  // Sites CRUD
  it('exports patrimoineSites', () => expect(api).toContain('patrimoineSites'));
  it('exports patrimoineSiteDetail', () => expect(api).toContain('patrimoineSiteDetail'));
  it('exports patrimoineSiteUpdate', () => expect(api).toContain('patrimoineSiteUpdate'));
  it('exports patrimoineSiteArchive', () => expect(api).toContain('patrimoineSiteArchive'));
  it('exports patrimoineSiteRestore', () => expect(api).toContain('patrimoineSiteRestore'));
  it('exports patrimoineSiteMerge', () => expect(api).toContain('patrimoineSiteMerge'));

  // Compteurs
  it('exports patrimoineCompteurs', () => expect(api).toContain('patrimoineCompteurs'));
  it('exports patrimoineCompteurUpdate', () => expect(api).toContain('patrimoineCompteurUpdate'));
  it('exports patrimoineCompteurMove', () => expect(api).toContain('patrimoineCompteurMove'));
  it('exports patrimoineCompteurDetach', () => expect(api).toContain('patrimoineCompteurDetach'));

  // Contracts
  it('exports patrimoineContracts', () => expect(api).toContain('patrimoineContracts'));
  it('exports patrimoineContractCreate', () => expect(api).toContain('patrimoineContractCreate'));
  it('exports patrimoineContractUpdate', () => expect(api).toContain('patrimoineContractUpdate'));
  it('exports patrimoineContractDelete', () => expect(api).toContain('patrimoineContractDelete'));

  // V51 — previously missing wrappers
  it('exports getImportTemplate', () => expect(api).toContain('getImportTemplate'));
  it('exports stagingExportReport', () => expect(api).toContain('stagingExportReport'));
  it('exports patrimoineDeliveryPoints', () => expect(api).toContain('patrimoineDeliveryPoints'));
  it('exports patrimoineKpis', () => expect(api).toContain('patrimoineKpis'));
  it('exports patrimoineSitesExport', () => expect(api).toContain('patrimoineSitesExport'));

  // Demo
  it('exports loadPatrimoineDemo', () => expect(api).toContain('loadPatrimoineDemo'));
  it('exports getImportTemplateColumns', () => expect(api).toContain('getImportTemplateColumns'));
});

// ═══════════════════════════════════════════════════════════════════════════════
// 4. CTAs from other modules to Patrimoine
// ═══════════════════════════════════════════════════════════════════════════════

describe('CTAs from other modules point to valid patrimoine routes', () => {
  it('Cockpit links to /sites/', () => {
    const cockpit = src('pages/Cockpit.jsx');
    expect(cockpit).toContain('/sites/');
  });

  it('CommandCenter links to /patrimoine', () => {
    const cc = src('pages/CommandCenter.jsx');
    expect(cc).toContain('/patrimoine');
  });

  it('CommandCenter links to /sites/', () => {
    const cc = src('pages/CommandCenter.jsx');
    expect(cc).toContain('/sites/');
  });

  it('ImpactDecisionPanel links to /patrimoine', () => {
    const panel = src('pages/cockpit/ImpactDecisionPanel.jsx');
    expect(panel).toContain('/patrimoine');
  });

  it('TertiaireDashboardPage links to /patrimoine', () => {
    const dash = src('pages/tertiaire/TertiaireDashboardPage.jsx');
    expect(dash).toContain('/patrimoine');
  });

  it('Site360 back button goes to /patrimoine', () => {
    const s360 = src('pages/Site360.jsx');
    expect(s360).toContain("'/patrimoine'");
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// 5. PatrimoineWizard component exists
// ═══════════════════════════════════════════════════════════════════════════════

describe('PatrimoineWizard component', () => {
  const wizard = src('components/PatrimoineWizard.jsx');

  it('has 6-step import pipeline', () => {
    expect(wizard).toContain('stagingImport');
    expect(wizard).toContain('stagingValidate');
    expect(wizard).toContain('stagingActivate');
  });

  it('supports express mode', () => {
    expect(wizard).toContain('express');
  });

  it('supports demo mode', () => {
    expect(wizard).toContain('demo');
  });

  it('calls refreshSites on success', () => {
    expect(wizard).toContain('refreshSites');
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// 6. Patrimoine page features
// ═══════════════════════════════════════════════════════════════════════════════

describe('Patrimoine page features', () => {
  const page = src('pages/Patrimoine.jsx');

  it('has URL-synced filters', () => {
    expect(page).toContain('useSearchParams');
  });

  it('has KPI cards', () => {
    expect(page).toContain('Sites actif');
  });

  it('has site drawer', () => {
    expect(page).toContain('Drawer');
  });

  it('has risk-first table', () => {
    expect(page).toContain('risque');
  });

  it('links to site detail via /sites/', () => {
    expect(page).toContain('/sites/');
  });

  it('displays FR status labels', () => {
    expect(page).toContain('Conforme');
    expect(page).toContain('Non conforme');
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// 7. Backend patrimoine source guards
// ═══════════════════════════════════════════════════════════════════════════════

const backendSrc = (rel) =>
  fs.readFileSync(path.resolve(__dirname, '..', '..', '..', '..', 'backend', rel), 'utf-8');

describe('Backend patrimoine routes exist', () => {
  const route = backendSrc('routes/patrimoine.py');

  it('has GET /sites endpoint', () => {
    expect(route).toContain('/sites');
    expect(route).toContain('api/patrimoine');
  });

  it('has PATCH /sites/{site_id}', () => {
    expect(route).toContain('.patch(');
    expect(route).toContain('site_id');
  });

  it('has staging import endpoint', () => {
    expect(route).toContain('staging/import');
  });

  it('has quality gate (validate)', () => {
    expect(route).toContain('validate');
  });

  it('has activation endpoint', () => {
    expect(route).toContain('activate');
  });

  it('has KPIs endpoint', () => {
    expect(route).toContain('kpis');
  });

  it('has contracts CRUD', () => {
    expect(route).toContain('contracts');
  });

  it('has compteurs CRUD', () => {
    expect(route).toContain('compteurs');
  });

  it('has delivery-points endpoint', () => {
    expect(route).toContain('delivery-points');
  });

  it('has demo/load endpoint', () => {
    expect(route).toContain('demo/load');
  });
});
