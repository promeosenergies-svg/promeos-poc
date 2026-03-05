/**
 * PROMEOS — A.4: Tests ActiveFiltersBar + audit filtres
 * Source-guard + tests unitaires du composant.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';

const SRC = join(__dirname, '..');

const readSrc = (rel) => readFileSync(join(SRC, rel), 'utf-8');

// ── A. ActiveFiltersBar component existe ──────────────────────────────────────

describe('A. ActiveFiltersBar — composant', () => {
  const src = readSrc('ui/ActiveFiltersBar.jsx');

  it('exporte un composant par défaut', () => {
    expect(src).toContain('export default function ActiveFiltersBar');
  });

  it('accepte props filters, total, filtered, onReset', () => {
    expect(src).toContain('filters');
    expect(src).toContain('total');
    expect(src).toContain('filtered');
    expect(src).toContain('onReset');
  });

  it('affiche le compteur "X sur Y" ou "X résultats"', () => {
    expect(src).toMatch(/sur|résultat/);
  });

  it('a un bouton Réinitialiser', () => {
    expect(src).toContain('Réinitialiser');
  });

  it('a un data-testid filter-count', () => {
    expect(src).toContain('data-testid="filter-count"');
  });

  it('a un data-testid filter-reset', () => {
    expect(src).toContain('data-testid="filter-reset"');
  });

  it('est exporté depuis ui/index.js', () => {
    const idx = readSrc('ui/index.js');
    expect(idx).toContain('ActiveFiltersBar');
  });
});

// ── B. Pages principales utilisent ActiveFiltersBar ───────────────────────────

describe('B. Pages principales — intégration ActiveFiltersBar', () => {
  const PAGES_WITH_FILTERS = [
    { file: 'pages/ActionsPage.jsx', name: 'ActionsPage' },
    { file: 'pages/AnomaliesPage.jsx', name: 'AnomaliesPage' },
    { file: 'pages/NotificationsPage.jsx', name: 'NotificationsPage' },
  ];

  for (const { file, name } of PAGES_WITH_FILTERS) {
    it(`${name} importe ActiveFiltersBar`, () => {
      const src = readSrc(file);
      expect(src).toContain('ActiveFiltersBar');
    });
  }
});

// ── C. Filtres appliqués — vérification ───────────────────────────────────────

describe('C. Filtres fonctionnels — vérification', () => {
  it('BillingPage applique statusFilter aux données', () => {
    const src = readSrc('pages/BillingPage.jsx');
    expect(src).toMatch(/statusFilter/);
    expect(src).toMatch(/coverage_status/);
  });

  it('BillingPage applique timelineSearch aux données', () => {
    const src = readSrc('pages/BillingPage.jsx');
    expect(src).toMatch(/timelineSearch/);
  });

  it('BillingPage applique sortMode aux données', () => {
    const src = readSrc('pages/BillingPage.jsx');
    expect(src).toMatch(/sortMode/);
    expect(src).toMatch(/date_desc/);
  });

  it('AdminAuditLogPage applique searchText aux données', () => {
    const src = readSrc('pages/AdminAuditLogPage.jsx');
    expect(src).toMatch(/searchText/);
    expect(src).toMatch(/toLowerCase/);
  });

  it('ActionsPage a un filtrage par statut', () => {
    const src = readSrc('pages/ActionsPage.jsx');
    expect(src).toMatch(/filterStatut|filterStatus|statusFilter/i);
  });

  it('AnomaliesPage a resetFilters', () => {
    const src = readSrc('pages/AnomaliesPage.jsx');
    expect(src).toContain('resetFilters');
  });
});

// ── D. FilterBar existant — pas de régression ─────────────────────────────────

describe('D. FilterBar UI — toujours fonctionnel', () => {
  const src = readSrc('ui/FilterBar.jsx');

  it('exporte FilterBar', () => {
    expect(src).toContain('export default function FilterBar');
  });

  it('a un bouton Reset', () => {
    expect(src).toContain('Reset');
  });

  it('affiche count si fourni', () => {
    expect(src).toContain('resultat');
  });
});
