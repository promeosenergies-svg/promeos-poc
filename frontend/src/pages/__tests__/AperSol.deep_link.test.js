/**
 * AperSol — deep-link filter wiring (Sprint 1 Vague A phase A1)
 *
 * Convention projet : source-guard (readFileSync + regex).
 *
 * F3 fix P1-10 : les tests purs de `normalizeAperFilter` + `applyAperFilter`
 * vivent dans `aper/__tests__/sol_presenters_filter.test.js` (source-unique).
 * Ce fichier vérifie UNIQUEMENT le wiring AperSol.jsx (imports, props, ARIA).
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

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
    // wrapper qui contient le bouton Reset (éviter annonces parasites).
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
    expect(pageSrc).toMatch(/parking:\s*['"]Parkings\s*>\s*1[\s\u00A0]*500\s*m²['"]/);
    expect(pageSrc).toMatch(/toiture:\s*['"]Toitures\s*>\s*500\s*m²['"]/);
  });
});
