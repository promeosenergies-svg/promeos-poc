/**
 * Guard tests — Demo Journey (Cockpit → Patrimoine → Site360)
 * Ensures the demo vertical journey stays consistent and polished.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const readPage = (name) => readFileSync(resolve(__dirname, '..', name), 'utf8');

// ── Site360: scope discipline (no mock data) ──────────────────────────────

describe('Site360 scope discipline', () => {
  const src = readPage('Site360.jsx');

  it('imports useScope from ScopeContext', () => {
    expect(src).toContain('useScope');
  });

  it('does NOT import getMockSite', () => {
    expect(src).not.toContain('getMockSite');
  });

  it('does NOT import from mocks/sites', () => {
    expect(src).not.toContain('mocks/sites');
  });

  it('has a sitesLoading guard', () => {
    expect(src).toContain('sitesLoading');
  });

  it('uses scopedSites.find for site lookup', () => {
    expect(src).toContain('scopedSites.find');
  });

  it('imports SkeletonCard for loading state', () => {
    expect(src).toContain('SkeletonCard');
  });
});

// ── Demo journey accent guards ────────────────────────────────────────────

describe('Demo journey — no bare "A risque" / "A evaluer"', () => {
  it('Site360: uses accented labels', () => {
    const src = readPage('Site360.jsx');
    expect(src).not.toMatch(/label:\s*'A risque'/);
    expect(src).not.toMatch(/label:\s*'A evaluer'/);
  });

  it('Patrimoine: uses accented labels in STATUT maps', () => {
    const src = readPage('Patrimoine.jsx');
    expect(src).not.toMatch(/label:\s*'A risque'/);
    expect(src).not.toMatch(/label:\s*'A evaluer'/);
  });
});

describe('Demo journey — no "EUR" currency label (use € sign)', () => {
  it('Site360: no EUR', () => {
    const src = readPage('Site360.jsx');
    // Should not contain EUR as a standalone word in display strings
    expect(src).not.toMatch(/['"`]\s*[^'"`]*\bEUR\b/);
  });

  it('Cockpit: no EUR', () => {
    const src = readPage('Cockpit.jsx');
    expect(src).not.toMatch(/['"`]\s*[^'"`]*\bEUR\b/);
  });

  it('TopSitesCard: no EUR', () => {
    const src = readPage('cockpit/TopSitesCard.jsx');
    expect(src).not.toMatch(/\bEUR\b/);
  });
});

describe('Demo journey — Cockpit loading skeleton', () => {
  const src = readPage('Cockpit.jsx');

  it('imports SkeletonCard for loading state', () => {
    expect(src).toContain('SkeletonCard');
  });

  it('imports SkeletonTable for loading state', () => {
    expect(src).toContain('SkeletonTable');
  });
});
