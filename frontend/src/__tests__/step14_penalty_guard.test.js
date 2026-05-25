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

describe('Step 14 — Cockpit penalty exposure (migré post #303)', () => {
  // #303 P0 cleanup cockpit : Cockpit.jsx supprimé. La pénalité est désormais
  // remontée via /api/cockpit/strategique → payload.billing_kpis (cf. PR #303)
  // — backend (compute_billing_kpis_cockpit) + frontend (CockpitBillingKpis).
  // L'expose total_penalty_exposure_eur n'est plus une exposure cockpit mais
  // un signal Bill Intelligence dans payload.billing_kpis.surfacturations_a_contester.

  it('CockpitBillingKpis affiche surfacturations à contester (depuis BE)', () => {
    const src = fs.readFileSync('src/pages/cockpit/CockpitBillingKpis.jsx', 'utf8');
    expect(src).toContain('surfacturations_a_contester');
  });

  it('billing_kpis_cockpit_service expose estimated_loss_eur (somme insights)', () => {
    const src = fs.readFileSync('../backend/services/billing_kpis_cockpit_service.py', 'utf8');
    expect(src).toContain('estimated_loss_eur');
    expect(src).toContain('surfacturations_a_contester');
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
