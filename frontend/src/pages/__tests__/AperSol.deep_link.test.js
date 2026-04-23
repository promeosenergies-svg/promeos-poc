/**
 * AperSol — deep-link filter (Vague 1) — source guard tests
 *
 * Vérifie que AperSol consomme `?filter=parking|toiture` et que le helper
 * pur `applyAperFilter` filtre bien le dashboard.
 *
 * Convention projet : source-guard (readFileSync + regex), pas de RTL.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { applyAperFilter, normalizeAperFilter } from '../aper/sol_presenters';

const __dirname = dirname(fileURLToPath(import.meta.url));
const pageSrc = readFileSync(join(__dirname, '..', 'AperSol.jsx'), 'utf-8');

describe('AperSol — deep-link filter wiring', () => {
  it('imports useSearchParams from react-router-dom', () => {
    expect(pageSrc).toMatch(
      /import\s*\{[^}]*useSearchParams[^}]*\}\s*from\s*['"]react-router-dom['"]/
    );
  });

  it('imports applyAperFilter and normalizeAperFilter from presenters', () => {
    expect(pageSrc).toMatch(/applyAperFilter/);
    expect(pageSrc).toMatch(/normalizeAperFilter/);
  });

  it('reads `filter` query param', () => {
    expect(pageSrc).toMatch(/searchParams\.get\(\s*['"]filter['"]\s*\)/);
  });

  it('wraps dashboard with applyAperFilter + useMemo (filter propagated downstream)', () => {
    expect(pageSrc).toMatch(/applyAperFilter\(\s*data\.dashboard\s*,\s*activeFilter\s*\)/);
  });

  it('F2 fix P1-3 : live region on inner span (not on wrapping div with button)', () => {
    // role=status + aria-live sur le span texte uniquement, pas sur le
    // wrapper qui contient le bouton Reset (éviter annonces parasites)
    expect(pageSrc).toMatch(/role=["']status["']/);
    expect(pageSrc).toMatch(/aria-live=["']polite["']/);
  });

  it('filter banner has data-testid="aper-active-filter"', () => {
    expect(pageSrc).toMatch(/data-testid=["']aper-active-filter["']/);
  });

  it('F2 fix P1-2 : Reset button has minHeight >=44 + minWidth >=44 (WCAG 2.5.5)', () => {
    expect(pageSrc).toMatch(/minHeight:\s*44/);
    expect(pageSrc).toMatch(/minWidth:\s*44/);
  });

  it('F2 : Reset button has focus-visible ring (keyboard users)', () => {
    expect(pageSrc).toMatch(/focus-visible:ring-2/);
    expect(pageSrc).toMatch(/focus-visible:ring-blue-500/);
  });

  it('reset button navigates to /conformite/aper (no query)', () => {
    expect(pageSrc).toMatch(/navigate\(\s*['"]\/conformite\/aper['"]\s*\)/);
  });

  it('exposes FILTER_LABELS for parking + toiture', () => {
    expect(pageSrc).toMatch(/parking:\s*['"]Parkings\s*>\s*1\s*500\s*m²['"]/);
    expect(pageSrc).toMatch(/toiture:\s*['"]Toitures\s*>\s*500\s*m²['"]/);
  });
});

describe('normalizeAperFilter', () => {
  it('accepts parking', () => {
    expect(normalizeAperFilter('parking')).toBe('parking');
  });

  it('accepts toiture', () => {
    expect(normalizeAperFilter('toiture')).toBe('toiture');
  });

  it('rejects unknown values → null', () => {
    expect(normalizeAperFilter('roof')).toBe(null);
    expect(normalizeAperFilter('')).toBe(null);
    expect(normalizeAperFilter(null)).toBe(null);
    expect(normalizeAperFilter(undefined)).toBe(null);
  });
});

describe('applyAperFilter', () => {
  const dashboard = {
    parking: {
      eligible_count: 2,
      total_surface_m2: 3200,
      sites: [
        { site_id: 1, site_nom: 'Site A', surface_m2: 1800 },
        { site_id: 2, site_nom: 'Site B', surface_m2: 1400 },
      ],
    },
    roof: {
      eligible_count: 1,
      total_surface_m2: 750,
      sites: [{ site_id: 3, site_nom: 'Site C', surface_m2: 750 }],
    },
    total_eligible_sites: 3,
    next_deadline: '2028-06-30',
  };

  it('null filter returns dashboard unchanged (identity)', () => {
    expect(applyAperFilter(dashboard, null)).toBe(dashboard);
  });

  it('undefined filter returns dashboard unchanged', () => {
    expect(applyAperFilter(dashboard, undefined)).toBe(dashboard);
  });

  it('parking filter empties roof + recomputes total', () => {
    const out = applyAperFilter(dashboard, 'parking');
    expect(out.parking.sites).toHaveLength(2);
    expect(out.roof.sites).toHaveLength(0);
    expect(out.roof.eligible_count).toBe(0);
    expect(out.roof.total_surface_m2).toBe(0);
    expect(out.total_eligible_sites).toBe(2);
  });

  it('toiture filter empties parking + recomputes total', () => {
    const out = applyAperFilter(dashboard, 'toiture');
    expect(out.parking.sites).toHaveLength(0);
    expect(out.parking.eligible_count).toBe(0);
    expect(out.parking.total_surface_m2).toBe(0);
    expect(out.roof.sites).toHaveLength(1);
    expect(out.total_eligible_sites).toBe(1);
  });

  it('preserves next_deadline after filtering', () => {
    expect(applyAperFilter(dashboard, 'parking').next_deadline).toBe('2028-06-30');
    expect(applyAperFilter(dashboard, 'toiture').next_deadline).toBe('2028-06-30');
  });

  it('handles missing category gracefully', () => {
    const partial = { total_eligible_sites: 0 };
    const out = applyAperFilter(partial, 'parking');
    expect(out.parking.sites).toEqual([]);
    expect(out.total_eligible_sites).toBe(0);
  });

  it('null dashboard returns null', () => {
    expect(applyAperFilter(null, 'parking')).toBe(null);
  });
});
