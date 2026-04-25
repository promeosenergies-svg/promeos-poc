/**
 * Step 14 — C7 : Impact financier EUR systematique
 * Source-guard tests for penalty display on findings.
 */
import { describe, it, expect } from 'vitest';
import fs from 'fs';

// Lot 3 Phase 3 : pénalités affichées via RegOpsSol.jsx
// + regops/sol_presenters.js (RegOps.jsx réduit à un loader).
describe('Step 14 — RegOps penalty display (Pattern C Lot 3)', () => {
  it('regops/sol_presenters utilise formatFREur pour afficher les pénalités', () => {
    const src = fs.readFileSync('src/pages/regops/sol_presenters.js', 'utf8');
    expect(src).toContain('formatFREur');
  });

  it('regops/sol_presenters lit estimated_penalty_eur', () => {
    const src = fs.readFileSync('src/pages/regops/sol_presenters.js', 'utf8');
    expect(src).toContain('estimated_penalty_eur');
  });

  it('RegOpsSol affiche le KPI « Pénalité potentielle »', () => {
    const src = fs.readFileSync('src/pages/RegOpsSol.jsx', 'utf8');
    expect(src).toMatch(/Pénalité potentielle/);
  });

  it('sumPenalties exclut COMPLIANT (filtre AT_RISK + NON_COMPLIANT)', () => {
    const src = fs.readFileSync('src/pages/regops/sol_presenters.js', 'utf8');
    expect(src).toMatch(/AT_RISK.*NON_COMPLIANT|NON_COMPLIANT.*AT_RISK/s);
  });
});

describe('Step 14 — ObligationsTab penalty display', () => {
  it('ObligationsTab imports fmtEur', () => {
    const src = fs.readFileSync('src/pages/conformite-tabs/ObligationsTab.jsx', 'utf8');
    expect(src).toContain('fmtEur');
  });

  it('ObligationsTab imports Coins icon', () => {
    const src = fs.readFileSync('src/pages/conformite-tabs/ObligationsTab.jsx', 'utf8');
    expect(src).toContain('Coins');
  });

  it('ObligationsTab displays estimated_penalty_eur', () => {
    const src = fs.readFileSync('src/pages/conformite-tabs/ObligationsTab.jsx', 'utf8');
    expect(src).toContain('estimated_penalty_eur');
  });
});

describe('Step 14 — Cockpit penalty exposure', () => {
  // fmtEur et "Exposition totale" retirés dans Cockpit V3 (exposition inline via RiskBadge)

  it('Cockpit stores totalPenaltyExposure', () => {
    const src = fs.readFileSync('src/pages/Cockpit.jsx', 'utf8');
    expect(src).toContain('totalPenaltyExposure');
  });

  it('Cockpit reads total_penalty_exposure_eur from timeline', () => {
    const src = fs.readFileSync('src/pages/Cockpit.jsx', 'utf8');
    expect(src).toContain('total_penalty_exposure_eur');
  });
});

describe('Step 14 — Glossary', () => {
  it('glossary.js has impact_financier entry', () => {
    const src = fs.readFileSync('src/ui/glossary.js', 'utf8');
    expect(src).toContain('impact_financier');
  });

  it('glossary.js impact_financier has penalty source info', () => {
    const src = fs.readFileSync('src/ui/glossary.js', 'utf8');
    expect(src).toContain('penalty_source');
  });
});
