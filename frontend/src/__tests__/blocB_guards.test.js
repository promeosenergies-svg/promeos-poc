/**
 * PROMEOS — Bloc B Scalabilité / Performance — Source Guards
 * Vérifie skeleton, ErrorState, EmptyState, pagination, hook sur les 8 pages P0.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const pagesDir = join(__dirname, '..', 'pages');
const hooksDir = join(__dirname, '..', 'hooks');
const uiDir = join(__dirname, '..', 'ui');

function readSrc(dir, file) {
  return readFileSync(join(dir, file), 'utf-8');
}

// ── P0: Skeleton loading on 8 pages ──────────────────────────────────────

describe('P0 — Skeleton loading components', () => {
  const pages = [
    'Cockpit.jsx',
    'Dashboard.jsx',
    'ConformitePage.jsx',
    'Site360.jsx',
    'PurchasePage.jsx',
    'BillIntelPage.jsx',
    'MonitoringPage.jsx',
    'Patrimoine.jsx',
  ];

  for (const page of pages) {
    it(`${page} imports a Skeleton variant (SkeletonKpi, SkeletonTable, SkeletonCard, or Skeleton)`, () => {
      const src = readSrc(pagesDir, page);
      const hasSkeleton = /Skeleton(Kpi|Table|Card)?/.test(src);
      expect(hasSkeleton).toBe(true);
    });
  }
});

// ── P0: ErrorState on 8 pages ────────────────────────────────────────────

describe('P0 — ErrorState on all pages', () => {
  const pages = [
    'Cockpit.jsx',
    'Dashboard.jsx',
    'ConformitePage.jsx',
    'Site360.jsx',
    'PurchasePage.jsx',
    'BillIntelPage.jsx',
    'MonitoringPage.jsx',
    'Patrimoine.jsx',
  ];

  for (const page of pages) {
    it(`${page} imports ErrorState`, () => {
      const src = readSrc(pagesDir, page);
      expect(src).toContain('ErrorState');
    });
  }
});

// ── P0: EmptyState on pages with tables/lists ────────────────────────────

describe('P0 — EmptyState on key pages', () => {
  const pages = [
    'Dashboard.jsx',
    'PurchasePage.jsx',
    'BillIntelPage.jsx',
    'Patrimoine.jsx',
  ];

  for (const page of pages) {
    it(`${page} imports EmptyState`, () => {
      const src = readSrc(pagesDir, page);
      expect(src).toContain('EmptyState');
    });
  }
});

// ── P1: useApiWithToast hook exists ──────────────────────────────────────

describe('P1 — useApiWithToast hook', () => {
  it('hook file exists and exports useApiWithToast', () => {
    const src = readSrc(hooksDir, 'useApiWithToast.js');
    expect(src).toContain('export function useApiWithToast');
  });

  it('hook uses useToast from ToastProvider', () => {
    const src = readSrc(hooksDir, 'useApiWithToast.js');
    expect(src).toContain('useToast');
  });
});

// ── P1: Dashboard pagination ─────────────────────────────────────────────

describe('P1 — Dashboard pagination', () => {
  const src = readSrc(pagesDir, 'Dashboard.jsx');

  it('imports Pagination component', () => {
    expect(src).toContain('Pagination');
  });

  it('has ROWS_PER_PAGE constant', () => {
    expect(src).toMatch(/ROWS_PER_PAGE\s*=\s*25/);
  });

  it('uses currentPage state', () => {
    expect(src).toContain('currentPage');
  });
});

// ── P0: SkeletonKpi component exists in UI ───────────────────────────────

describe('UI — SkeletonKpi component', () => {
  const src = readSrc(uiDir, 'Skeleton.jsx');

  it('exports SkeletonKpi', () => {
    expect(src).toContain('SkeletonKpi');
  });

  it('SkeletonKpi accepts count prop', () => {
    expect(src).toMatch(/SkeletonKpi.*count/);
  });
});
