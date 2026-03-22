/**
 * PROMEOS — V24: Design System & UX Standardisation
 * Source-level guards: conventions, shared components, loading/empty/error states.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const readUi = (name) => readFileSync(resolve(__dirname, '..', name), 'utf8');
const readPage = (name) => readFileSync(resolve(__dirname, '..', '..', 'pages', name), 'utf8');

// ── 1. Conventions exports ──────────────────────────────────────────────────

describe('conventions.js exports', () => {
  const src = readUi('conventions.js');

  it('exports LAYOUT constants', () => {
    expect(src).toMatch(/export\s+const\s+LAYOUT/);
  });

  it('exports TYPO constants', () => {
    expect(src).toMatch(/export\s+const\s+TYPO/);
  });

  it('exports LABELS_FR constants', () => {
    expect(src).toMatch(/export\s+const\s+LABELS_FR/);
  });

  it('LABELS_FR contains FR loading label', () => {
    expect(src).toContain("loading: 'Chargement...'");
  });
});

// ── 2. KpiCardCompact shared export ─────────────────────────────────────────

describe('KpiCard.jsx shared exports', () => {
  const src = readUi('KpiCard.jsx');

  it('exports KpiCardCompact as named export', () => {
    expect(src).toMatch(/export\s+function\s+KpiCardCompact/);
  });
});

// ── 3. EmptyState accepts actions prop ──────────────────────────────────────

describe('EmptyState enhanced API', () => {
  const src = readUi('EmptyState.jsx');

  it('destructures actions prop', () => {
    expect(src).toContain('actions');
  });

  it('renders actions in a flex container', () => {
    expect(src).toContain('{actions}');
  });
});

// ── 4. Barrel exports (index.js) ────────────────────────────────────────────

describe('ui/index.js barrel exports', () => {
  const src = readUi('index.js');

  it('exports KpiCardCompact', () => {
    expect(src).toContain('KpiCardCompact');
  });

  it('exports conventions (LAYOUT, TYPO, LABELS_FR)', () => {
    expect(src).toContain('LAYOUT');
    expect(src).toContain('TYPO');
    expect(src).toContain('LABELS_FR');
  });
});

// ── 5. Dashboard.jsx — error state + FR labels ─────────────────────────────

describe('Dashboard V24 standardisation', () => {
  const src = readPage('Dashboard.jsx');

  it('imports ErrorState', () => {
    expect(src).toContain('ErrorState');
  });

  it('has error state management', () => {
    expect(src).toContain('setError');
  });

  it('uses FR label "Sites total" (not "Total Sites")', () => {
    expect(src).toContain('Sites total');
    expect(src).not.toContain('Total Sites');
  });

  it('uses FR label "Historique" (not "Legacy")', () => {
    expect(src).toContain('Historique');
    expect(src).not.toContain('Legacy');
  });

  it('uses FR label "Sites actifs" (not "Sites Actifs")', () => {
    expect(src).toContain('Sites actifs');
  });
});

// ── 6. Patrimoine.jsx — shared components + loading state ──────────────────

describe('Patrimoine V24 standardisation', () => {
  const src = readPage('Patrimoine.jsx');

  it('imports KpiCardCompact from ../ui (not defined locally)', () => {
    expect(src).toContain('KpiCardCompact');
    expect(src).not.toMatch(/function\s+KpiCardCompact/);
  });

  it('imports SkeletonCard and SkeletonTable', () => {
    expect(src).toContain('SkeletonCard');
    expect(src).toContain('SkeletonTable');
  });

  it('uses sitesLoading from useScope', () => {
    expect(src).toContain('sitesLoading');
  });

  // EmptyState + "Bienvenue" retiré dans Patrimoine V3
});
