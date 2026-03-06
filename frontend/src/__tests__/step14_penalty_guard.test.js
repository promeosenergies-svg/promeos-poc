/**
 * Step 14 — C7 : Impact financier EUR systematique
 * Source-guard tests for penalty display on findings.
 */
import { describe, it, expect } from 'vitest';
import fs from 'fs';

describe('Step 14 — RegOps penalty display', () => {
  it('RegOps.jsx imports fmtEur', () => {
    const src = fs.readFileSync('src/pages/RegOps.jsx', 'utf8');
    expect(src).toContain('fmtEur');
  });

  it('RegOps.jsx displays estimated_penalty_eur', () => {
    const src = fs.readFileSync('src/pages/RegOps.jsx', 'utf8');
    expect(src).toContain('estimated_penalty_eur');
  });

  it('RegOps.jsx shows Risque financier label', () => {
    const src = fs.readFileSync('src/pages/RegOps.jsx', 'utf8');
    expect(src).toContain('Risque financier');
  });

  it('RegOps.jsx shows penalty_basis', () => {
    const src = fs.readFileSync('src/pages/RegOps.jsx', 'utf8');
    expect(src).toContain('penalty_basis');
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
  it('Cockpit imports fmtEur', () => {
    const src = fs.readFileSync('src/pages/Cockpit.jsx', 'utf8');
    expect(src).toContain('fmtEur');
  });

  it('Cockpit stores totalPenaltyExposure', () => {
    const src = fs.readFileSync('src/pages/Cockpit.jsx', 'utf8');
    expect(src).toContain('totalPenaltyExposure');
  });

  it('Cockpit shows Exposition totale', () => {
    const src = fs.readFileSync('src/pages/Cockpit.jsx', 'utf8');
    expect(src).toContain('Exposition totale');
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
