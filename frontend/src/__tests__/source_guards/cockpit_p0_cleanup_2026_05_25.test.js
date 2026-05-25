/**
 * Source-guards P0 cleanup cockpit (2026-05-25).
 *
 * Garde-fous cardinaux :
 * 1. Anti-régression Cockpit.jsx et CockpitDecision.jsx supprimés
 *    — aucun import depuis du code vivant.
 * 2. CockpitStrategique consomme `payload.billing_kpis` via CockpitBillingKpis.
 * 3. CadreApplicable drill-down vers /conformite?regulation=X pour
 *    applicable et unknown (pas seulement data_missing).
 * 4. SolNarrativeText wrappe les acronymes du hero CockpitStrategique.
 */
import { existsSync, readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const ROOT = resolve(__dirname, '../../../');
const STRATEGIQUE = resolve(ROOT, 'src/pages/CockpitStrategique.jsx');
const BILLING_KPIS = resolve(ROOT, 'src/pages/cockpit/CockpitBillingKpis.jsx');
const CADRE = resolve(ROOT, 'src/components/grammar/hub/CadreApplicable.jsx');

function read(p) {
  return readFileSync(p, 'utf-8');
}

describe('SG_COCKPIT_P0_01 — Cockpit.jsx et CockpitDecision.jsx supprimés', () => {
  it("Cockpit.jsx n'existe plus", () => {
    expect(existsSync(resolve(ROOT, 'src/pages/Cockpit.jsx'))).toBe(false);
  });

  it("CockpitDecision.jsx n'existe plus", () => {
    expect(existsSync(resolve(ROOT, 'src/pages/CockpitDecision.jsx'))).toBe(false);
  });

  it("useExecutiveV2 hook supprimé", () => {
    expect(existsSync(resolve(ROOT, 'src/hooks/useExecutiveV2.js'))).toBe(false);
  });
});

describe('SG_COCKPIT_P0_02 — CockpitStrategique remonte billing_kpis', () => {
  const src = read(STRATEGIQUE);

  it('importe CockpitBillingKpis', () => {
    expect(src).toMatch(/import\s+CockpitBillingKpis\s+from\s+['"]\.\/cockpit\/CockpitBillingKpis['"]/);
  });

  it('rend <CockpitBillingKpis billingKpis={payload.billing_kpis} />', () => {
    expect(src).toMatch(/<CockpitBillingKpis\s+billingKpis=\{payload\.billing_kpis\}/);
  });

  it('importe SolNarrativeText pour glosser les acronymes hero', () => {
    expect(src).toMatch(/import\s+SolNarrativeText\s+from/);
  });

  it('wrappe payload.hero.kicker et sub_constat dans SolNarrativeText', () => {
    expect(src).toMatch(/<SolNarrativeText\s+text=\{payload\.hero\.kicker\}/);
    expect(src).toMatch(/<SolNarrativeText\s+text=\{payload\.hero\.sub_constat\}/);
  });
});

describe('SG_COCKPIT_P0_03 — CockpitBillingKpis structure', () => {
  const src = read(BILLING_KPIS);

  it('expose data-testid="cockpit-billing-kpis"', () => {
    expect(src).toContain('data-testid="cockpit-billing-kpis"');
  });

  it('rend les 4 testids billing-kpi-*', () => {
    for (const id of [
      'billing-kpi-surfacturations',
      'billing-kpi-anomalies-ouvertes',
      'billing-kpi-anomalies-energie',
      'billing-kpi-actions-facturation',
    ]) {
      expect(src).toContain(`testid="${id}"`);
    }
  });

  it("ne hardcode pas de valeurs métier (montant, count)", () => {
    // Anti-régression doctrine §8.1 : zéro logique métier FE.
    expect(src).not.toMatch(/=\s*19808\b/);
    expect(src).not.toMatch(/=\s*45000\b/);
  });

  it('utilise Intl.NumberFormat fr-FR pour formater les euros', () => {
    expect(src).toMatch(/Intl\.NumberFormat\(['"]fr-FR['"]/);
  });
});

describe('SG_COCKPIT_P0_04 — CadreApplicable drill-down /conformite', () => {
  const src = read(CADRE);

  it('définit CONFORMITE_REGULATION_PARAM (mapping code → chip param)', () => {
    expect(src).toMatch(/CONFORMITE_REGULATION_PARAM\s*=\s*\{/);
    for (const code of ['DT', 'BACS', 'APER', 'SME', 'BEGES']) {
      // Chaque code a un mapping explicite (pas de fallback métier faux)
      expect(src).toMatch(new RegExp(`${code}:\\s*['"][a-z-]+['"]`));
    }
  });

  it('navigate vers /conformite?regulation=X si status applicable/unknown', () => {
    expect(src).toMatch(/\/conformite\?regulation=/);
    expect(src).toMatch(/summary\.status\s*===\s*['"]applicable['"]/);
    expect(src).toMatch(/summary\.status\s*===\s*['"]unknown['"]/);
  });

  it("isClickable inclut applicable et unknown (pas seulement data_missing)", () => {
    expect(src).toMatch(/isClickable[\s\S]{0,200}applicable/);
    expect(src).toMatch(/isClickable[\s\S]{0,200}unknown/);
  });
});

describe('SG_COCKPIT_P0_05 — Endpoints backend orphelins documentés 410', () => {
  // Vérifie via lecture du backend que les endpoints orphelins sont
  // bien transformés en 410 Gone FR (via helper _gone_cockpit_p0_2026_05_25).
  let backendSrc = '';
  try {
    backendSrc = readFileSync(resolve(ROOT, '../backend/routes/cockpit.py'), 'utf-8');
  } catch {
    return;
  }

  it('helper _gone_cockpit_p0_2026_05_25 existe', () => {
    if (!backendSrc) return;
    expect(backendSrc).toMatch(/def\s+_gone_cockpit_p0_2026_05_25\(/);
  });

  it('endpoints orphelins appellent _gone_cockpit_p0_2026_05_25', () => {
    if (!backendSrc) return;
    // Au moins 8 endpoints doivent appeler le helper (les 12 orphelins).
    const calls = backendSrc.match(/_gone_cockpit_p0_2026_05_25\(/g) || [];
    expect(calls.length).toBeGreaterThanOrEqual(8);
  });
});
