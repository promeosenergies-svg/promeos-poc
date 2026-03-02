/**
 * anomaliesV65.page.test.js — V65 Anomalies Centre d'actions
 * Source-guard tests (readFileSync + regex) — no DOM, no mocks needed.
 * 7 groups, ~30 tests.
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');

function src(relPath) {
  return readFileSync(resolve(root, relPath), 'utf-8');
}

/* ── A. anomalyActions.js ── */
describe('A. anomalyActions.js — localStorage helpers', () => {
  const code = src('src/services/anomalyActions.js');

  it('uses storage key promeos_anomaly_actions', () => {
    expect(code).toMatch(/promeos_anomaly_actions/);
  });

  it('exports ACTION_STATUS with todo / in_progress / resolved', () => {
    expect(code).toMatch(/export.*ACTION_STATUS/);
    expect(code).toMatch(/todo/);
    expect(code).toMatch(/in_progress/);
    expect(code).toMatch(/resolved/);
  });

  it('exports 5 public functions', () => {
    expect(code).toMatch(/export function getAnomalyAction/);
    expect(code).toMatch(/export function saveAnomalyAction/);
    expect(code).toMatch(/export function deleteAnomalyAction/);
    expect(code).toMatch(/export function getAllActionsForSite/);
    expect(code).toMatch(/export function getAllActionsForOrg/);
  });

  it('key format uses orgId ?? demo', () => {
    expect(code).toMatch(/orgId.*\?\?.*demo|demo.*\?\?.*orgId/);
  });

  it('exports ACTION_STATUS_LABEL', () => {
    expect(code).toMatch(/export.*ACTION_STATUS_LABEL/);
  });

  it('exports ACTION_STATUS_COLOR', () => {
    expect(code).toMatch(/export.*ACTION_STATUS_COLOR/);
  });
});

/* ── B. SiteAnomalyPanel.jsx ── */
describe('B. SiteAnomalyPanel.jsx — enriched drawer panel', () => {
  const code = src('src/components/SiteAnomalyPanel.jsx');

  it('has default export', () => {
    expect(code).toMatch(/export default function SiteAnomalyPanel/);
  });

  it('accepts siteId and orgId props', () => {
    expect(code).toMatch(/siteId/);
    expect(code).toMatch(/orgId/);
  });

  it('has quick filters: Critiques, Facturation, Décret Tertiaire, BACS', () => {
    expect(code).toMatch(/Critiques/);
    expect(code).toMatch(/Facturation/);
    expect(code).toMatch(/D.*cret Tertiaire/);
    expect(code).toMatch(/BACS/);
  });

  it('has "Créer action" CTA', () => {
    expect(code).toMatch(/Cr.*er action/);
  });

  it('sorts by priority_score', () => {
    expect(code).toMatch(/priority_score/);
  });

  it('imports getPatrimoineAnomalies', () => {
    expect(code).toMatch(/getPatrimoineAnomalies/);
  });

  it('uses useActionDrawer (V92 migration)', () => {
    expect(code).toMatch(/useActionDrawer/);
  });

  it('does not import AnomalyActionModal (V92 migration)', () => {
    expect(code).not.toMatch(/import.*AnomalyActionModal/);
  });
});

/* ── C. AnomalyActionModal.jsx ── */
describe('C. AnomalyActionModal.jsx — front-only action modal', () => {
  const code = src('src/components/AnomalyActionModal.jsx');

  it('has default export', () => {
    expect(code).toMatch(/export default function AnomalyActionModal/);
  });

  it('imports saveAnomalyAction', () => {
    expect(code).toMatch(/saveAnomalyAction/);
  });

  it('has "Marquer comme résolu" button', () => {
    expect(code).toMatch(/Marquer comme r.*solu/);
  });

  it('has all form fields: title, owner, due_date, notes', () => {
    expect(code).toMatch(/title/);
    expect(code).toMatch(/owner/);
    expect(code).toMatch(/due_date/);
    expect(code).toMatch(/notes/);
  });

  it('has status select with the 3 values', () => {
    expect(code).toMatch(/todo/);
    expect(code).toMatch(/in_progress/);
    expect(code).toMatch(/resolved/);
  });
});

/* ── D. AnomaliesPage.jsx ── */
describe('D. AnomaliesPage.jsx — cross-site action center', () => {
  const code = src('src/pages/AnomaliesPage.jsx');

  it('has default export', () => {
    expect(code).toMatch(/export default function AnomaliesPage/);
  });

  it('imports useScope', () => {
    expect(code).toMatch(/useScope/);
  });

  it('has "Ouvrir site" CTA', () => {
    expect(code).toMatch(/Ouvrir site/);
  });

  it('has "Créer action" CTA', () => {
    expect(code).toMatch(/Cr.*er action/);
  });

  it('uses Promise.all for bulk fetch', () => {
    expect(code).toMatch(/Promise\.all/);
  });

  it('navigates to /patrimoine with state', () => {
    expect(code).toMatch(/navigate.*\/patrimoine/);
    expect(code).toMatch(/openSiteId/);
  });

  it('uses useActionDrawer (V92 migration)', () => {
    expect(code).toMatch(/useActionDrawer/);
  });

  it('does not import AnomalyActionModal (V92 migration)', () => {
    expect(code).not.toMatch(/import.*AnomalyActionModal/);
  });
});

/* ── E. App.jsx ── */
describe('E. App.jsx — routing', () => {
  const code = src('src/App.jsx');

  it('lazy-imports AnomaliesPage', () => {
    expect(code).toMatch(/AnomaliesPage.*=.*lazy.*import.*AnomaliesPage/s);
  });

  it('/anomalies route uses AnomaliesPage, not a Navigate redirect', () => {
    // Check line by line so dotall does not span into adjacent routes
    const routeLine = code.split('\n').find(l => l.includes('path="/anomalies"'));
    expect(routeLine).toBeDefined();
    expect(routeLine).not.toMatch(/Navigate/);
    expect(routeLine).toMatch(/AnomaliesPage/);
  });
});

/* ── F. NavRegistry.js ── */
describe('F. NavRegistry.js — navigation', () => {
  const code = src('src/layout/NavRegistry.js');

  it('/anomalies is mapped to operations module', () => {
    expect(code).toMatch(/\/anomalies.*operations/);
  });

  it('"Centre d\'actions" label present in nav items', () => {
    expect(code).toMatch(/Centre d'actions/);
  });
});

/* ── G. Patrimoine.jsx ── */
describe('G. Patrimoine.jsx — SiteAnomalyPanel integration', () => {
  const code = src('src/pages/Patrimoine.jsx');

  it('imports SiteAnomalyPanel', () => {
    expect(code).toMatch(/import SiteAnomalyPanel/);
  });

  it('passes orgId to SiteDrawerContent', () => {
    expect(code).toMatch(/orgId=\{scope\.orgId\}/);
  });

  it('imports useLocation and uses location.state?.openSiteId', () => {
    expect(code).toMatch(/useLocation/);
    expect(code).toMatch(/location\.state\?\.openSiteId/);
  });
});
