/**
 * billingV67.page.test.js — V67 Billing Timeline & Coverage
 * Source-guard tests (readFileSync + regex) — no DOM, no mocks needed.
 * 6 groupes, ~26 tests.
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');

function src(relPath) {
  return readFileSync(resolve(root, relPath), 'utf-8');
}

/* ── A. api.js — 3 nouveaux wrappers V67 ── */
describe('A. api.js — V67 coverage wrappers', () => {
  const code = src('src/services/api.js');

  it('exports getBillingPeriods', () => {
    expect(code).toMatch(/export const getBillingPeriods/);
  });

  it('getBillingPeriods calls /billing/periods', () => {
    expect(code).toMatch(/\/billing\/periods/);
  });

  it('exports getCoverageSummary', () => {
    expect(code).toMatch(/export const getCoverageSummary/);
  });

  it('getCoverageSummary calls /billing/coverage-summary', () => {
    expect(code).toMatch(/\/billing\/coverage-summary/);
  });

  it('exports getMissingPeriods', () => {
    expect(code).toMatch(/export const getMissingPeriods/);
  });

  it('getMissingPeriods calls /billing/missing-periods', () => {
    expect(code).toMatch(/\/billing\/missing-periods/);
  });
});

/* ── B. BillingPage.jsx — page timeline complète ── */
describe('B. BillingPage.jsx — timeline & coverage page', () => {
  const code = src('src/pages/BillingPage.jsx');

  it('imports getBillingPeriods', () => {
    expect(code).toMatch(/getBillingPeriods/);
  });

  it('imports getCoverageSummary', () => {
    expect(code).toMatch(/getCoverageSummary/);
  });

  it('imports getMissingPeriods', () => {
    expect(code).toMatch(/getMissingPeriods/);
  });

  it('has siteFilter state for site filtering', () => {
    expect(code).toMatch(/siteFilter/);
  });

  it('reads site_id from URL search params', () => {
    expect(code).toMatch(/useSearchParams|site_id/);
  });

  it('has pagination with load more (periodsOffset)', () => {
    expect(code).toMatch(/periodsOffset|loadingMore|hasMore/);
  });

  it('imports CoverageBar component', () => {
    expect(code).toMatch(/CoverageBar/);
  });

  it('imports BillingTimeline component', () => {
    expect(code).toMatch(/BillingTimeline/);
  });

  it('navigates to /bill-intel for import CTA', () => {
    expect(code).toMatch(/\/bill-intel/);
  });
});

/* ── C. BillingTimeline.jsx — liste mensuelle ── */
describe('C. BillingTimeline.jsx — monthly rows component', () => {
  const code = src('src/components/BillingTimeline.jsx');

  it('has default export function BillingTimeline', () => {
    expect(code).toMatch(/export default function BillingTimeline/);
  });

  it('handles covered status', () => {
    expect(code).toMatch(/covered/);
  });

  it('handles partial status', () => {
    expect(code).toMatch(/partial/);
  });

  it('handles missing status', () => {
    expect(code).toMatch(/missing/);
  });

  it('has Importer CTA navigating to /bill-intel', () => {
    expect(code).toMatch(/bill-intel/);
    expect(code).toMatch(/[Ii]mport/);
  });
});

/* ── D. CoverageBar.jsx — barre visuelle ── */
describe('D. CoverageBar.jsx — visual coverage bar', () => {
  const code = src('src/components/CoverageBar.jsx');

  it('has default export function CoverageBar', () => {
    expect(code).toMatch(/export default function CoverageBar/);
  });

  it('accepts covered prop', () => {
    expect(code).toMatch(/covered/);
  });

  it('accepts partial prop', () => {
    expect(code).toMatch(/partial/);
  });

  it('accepts missing prop', () => {
    expect(code).toMatch(/missing/);
  });
});

/* ── E. Site360.jsx — lien timeline ── */
describe('E. Site360.jsx — timeline link in Factures tab', () => {
  const code = src('src/pages/Site360.jsx');

  it('navigates to /billing with site_id query param', () => {
    expect(code).toMatch(/\/billing\?site_id/);
  });

  it('has "Voir timeline" CTA text', () => {
    expect(code).toMatch(/timeline/i);
  });
});

/* ── F. App.jsx + NavRegistry.js — routing ── */
describe('F. App.jsx + NavRegistry.js — /billing registered', () => {
  const appCode = src('src/App.jsx');
  const navCode = src('src/layout/NavRegistry.js');

  it('/billing route declared in App.jsx', () => {
    expect(appCode).toMatch(/path="\/billing"/);
  });

  it('BillingPage lazily imported in App.jsx', () => {
    expect(appCode).toMatch(/BillingPage/);
  });

  it('/billing appears in NavRegistry ROUTE_MODULE_MAP', () => {
    expect(navCode).toMatch(/['"]\/billing['"]/);
  });

  it('CalendarRange icon imported in NavRegistry', () => {
    expect(navCode).toMatch(/CalendarRange/);
  });

  it('Facturation label in NavRegistry', () => {
    expect(navCode).toMatch(/Facturation/);
  });
});
