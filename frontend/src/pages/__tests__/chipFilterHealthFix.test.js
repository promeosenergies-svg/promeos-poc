/**
 * chipFilterHealthFix.test.js — Regression tests for 2 UX fixes:
 *
 * A. Chip filters on TertiaireDashboardPage now filter "Sites à traiter"
 * B. HealthSummary "Points d'attention" card hidden when reasons.length===0
 *
 * Sections:
 *  A.  Source-guard: filteredSites default + chip filtering
 *  B.  Unit: computeHealthState AMBER requires reasons
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { computeHealthState } from '../../models/dashboardEssentials';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');

// ============================================================
// A. Chip filters — source-guard (TertiaireDashboardPage)
// ============================================================
describe('A · Chip filters actually filter "Sites à traiter"', () => {
  const code = readSrc('pages', 'tertiaire', 'TertiaireDashboardPage.jsx');

  it('filteredSites memo includes default subset logic (assujetti_probable + a_verifier)', () => {
    // The default filter should restrict to actionable sites when no chip is active
    expect(code).toMatch(/assujetti_probable.*!s\.is_covered/s);
    expect(code).toMatch(/a_verifier.*!s\.data_complete/s);
  });

  it('does NOT have the inline .filter() that overrides chip filtering', () => {
    // The old bug: .filter((s) => !hasActiveFilters ? (...) : true) was overriding chips
    expect(code).not.toMatch(/filteredSites\s*\.filter\(\(s\)\s*=>\s*!hasActiveFilters/);
  });

  it('renders filteredSites.map directly (no intermediate filter)', () => {
    expect(code).toMatch(/filteredSites\.map\(\(site\)/);
  });

  it('filteredSites applies signalFilter correctly', () => {
    expect(code).toMatch(/signalFilter.*sites\.filter.*s\.signal\s*===\s*signalFilter/s);
  });

  it('filteredSites applies uncoveredOnly correctly', () => {
    expect(code).toMatch(/uncoveredOnly.*sites\.filter.*!s\.is_covered/s);
  });

  it('filteredSites applies missingFieldFilter correctly', () => {
    expect(code).toMatch(/missingFieldFilter.*sites\.filter.*missing_fields/s);
  });

  it('shows empty message when filteredSites is empty', () => {
    expect(code).toContain('filteredSites.length === 0');
    expect(code).toContain('Aucun site ne correspond');
  });

  it('has Réinitialiser button to clear all filters', () => {
    expect(code).toContain('Réinitialiser');
    expect(code).toMatch(/setSignalFilter\(null\)/);
    expect(code).toMatch(/setUncoveredOnly\(false\)/);
    expect(code).toMatch(/setMissingFieldFilter\(null\)/);
  });
});

// ============================================================
// B. HealthSummary — no AMBER when reasons.length===0
// ============================================================
describe('B · computeHealthState: no AMBER card with 0 reasons', () => {
  const BASE = { total: 10, conformes: 10, nonConformes: 0, aRisque: 0, risqueTotal: 0, couvertureDonnees: 80 };

  it('AMBER when alertsCount > 0 (alerts surface as reasons)', () => {
    const state = computeHealthState({ kpis: BASE, watchlist: [], alertsCount: 5 });
    expect(state.level).toBe('AMBER');
    expect(state.reasons.length).toBeGreaterThan(0);
    expect(state.reasons.some(r => r.id === 'alerts-active')).toBe(true);
  });

  it('AMBER when kpis.aRisque > 0 even without watchlist items', () => {
    const state = computeHealthState({ kpis: { ...BASE, aRisque: 2 }, watchlist: [], alertsCount: 0 });
    expect(state.level).toBe('AMBER');
  });

  it('AMBER when warn reasons exist (regression: still works)', () => {
    const watchlist = [{ id: 'w1', label: 'Site à risque', severity: 'warn', path: '/actions' }];
    const state = computeHealthState({ kpis: { ...BASE, aRisque: 1 }, watchlist, alertsCount: 0 });
    expect(state.level).toBe('AMBER');
    expect(state.reasons.length).toBeGreaterThan(0);
  });

  it('RED still works with critical watchlist item', () => {
    const watchlist = [{ id: 'c1', label: 'Critical issue', severity: 'critical', path: '/' }];
    const state = computeHealthState({ kpis: BASE, watchlist, alertsCount: 0 });
    expect(state.level).toBe('RED');
  });

  it('RED still works when nonConformes > 0 even without watchlist', () => {
    const state = computeHealthState({ kpis: { ...BASE, nonConformes: 1 }, watchlist: [], alertsCount: 0 });
    expect(state.level).toBe('RED');
  });

  it('subtitle never says "0 points" for AMBER', () => {
    // alertsCount > 0 now creates an alerts-active reason, so reasons.length > 0
    const state = computeHealthState({ kpis: BASE, watchlist: [], alertsCount: 10 });
    expect(state.level).toBe('AMBER');
    expect(state.subtitle).not.toMatch(/0 point/);
  });
});

// ============================================================
// B2. Source-guard: computeHealthState condition
// ============================================================
describe('B2 · Source-guard: computeHealthState alerts become reasons', () => {
  const code = readSrc('models', 'dashboardEssentials.js');

  it('alerts > 0 creates an alerts-active reason', () => {
    expect(code).toMatch(/alerts-active/);
    expect(code).toMatch(/alertsCount\s*>\s*0/);
  });
});
