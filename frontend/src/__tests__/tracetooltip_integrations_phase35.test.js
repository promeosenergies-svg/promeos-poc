/**
 * tracetooltip_integrations_phase35.test.js — Sprint C-3 Phase 3.5
 *
 * Vérifie l'intégration de TraceTooltip sur 5 KPIs stratégiques (R10 différenciateur).
 *
 * Pattern repo : readFileSync + regex (env=node).
 *
 * Intégrations vérifiées :
 * 1. CockpitDecision.jsx — termId="COMPLIANCE_DT_PENALTY_EUR" sur "Pénalité légale"
 * 2. Patrimoine.jsx — termId="OPERAT_SURFACE_CONSO_DEFINITION" sur "kWh/m²"
 * 3. RegOps.jsx — termId="REGOPS_WEIGHT_DT_DEFAULT" sur "Score de Conformité"
 * 4. Cockpit.jsx — termId="READINESS_WEIGHT_CONFORMITY_PCT" sur poids
 * 5. ObligationsTab.jsx — termId="REGOPS_WEIGHT_DT/BACS/APER_DEFAULT" sur pondérations
 */
import { readFileSync } from 'fs';
import { dirname, resolve } from 'path';
import { fileURLToPath } from 'url';
import { describe, it, expect } from 'vitest';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = resolve(__dirname, '..');

function readSrc(rel) {
  return readFileSync(resolve(SRC_ROOT, rel), 'utf8');
}

// ─── Intégration 1 : CockpitDecision.jsx ────────────────────────────────────
// Suite retirée (#303 P0 cleanup cockpit) : CockpitDecision.jsx supprimé.
// La pénalité légale est désormais portée par CadreApplicable (panel
// DataMissingPanel) + payload.kpis backend Strategique.

// ─── Intégration 2 : Patrimoine.jsx ─────────────────────────────────────────

describe('Phase 3.5 — Intégration #2 Patrimoine kWh/m² doctrine OPERAT', () => {
  const src = readSrc('pages/Patrimoine.jsx');

  it('importe TraceTooltip', () => {
    expect(src).toMatch(/import\s+TraceTooltip\s+from\s+['"]\.\.\/ui\/TraceTooltip['"]/);
  });

  it('wrap "kWh/m²" avec termId OPERAT_SURFACE_CONSO_DEFINITION', () => {
    expect(src).toMatch(/<TraceTooltip\s+termId="OPERAT_SURFACE_CONSO_DEFINITION">[\s\n]*kWh\/m²/);
  });
});

// ─── Intégration 3 : RegOps.jsx ─────────────────────────────────────────────

describe('Phase 3.5 — Intégration #3 RegOps Score de Conformité', () => {
  const src = readSrc('pages/RegOps.jsx');

  it('importe TraceTooltip', () => {
    expect(src).toMatch(/import\s+TraceTooltip\s+from\s+['"]\.\.\/ui\/TraceTooltip['"]/);
  });

  it('wrap "Score de Conformité" avec termId REGOPS_WEIGHT_DT_DEFAULT', () => {
    expect(src).toMatch(
      /<TraceTooltip\s+termId="REGOPS_WEIGHT_DT_DEFAULT">Score de Conformité<\/TraceTooltip>/
    );
  });
});

// ─── Intégration 4 : Cockpit.jsx ────────────────────────────────────────────
// Suite retirée (#303) : Cockpit.jsx supprimé. Le poids readiness conformité
// n'est plus rendu dans la nouvelle Synthèse Stratégique (qui consomme
// payload.kpis backend). À recréer si exposition explicite des poids
// readiness redevient utile (à voir Cockpit P1+).

// ─── Intégration 5 : ObligationsTab.jsx (3 TraceTooltip pondérations RegOps) ─

describe('Phase 3.5 — Intégration #5 ObligationsTab pondérations DT/BACS/APER', () => {
  const src = readSrc('pages/conformite-tabs/ObligationsTab.jsx');

  it('importe TraceTooltip', () => {
    expect(src).toMatch(/import\s+TraceTooltip\s+from\s+['"]\.\.\/\.\.\/ui\/TraceTooltip['"]/);
  });

  it('wrap "DT 45%" avec termId REGOPS_WEIGHT_DT_DEFAULT', () => {
    expect(src).toMatch(/<TraceTooltip\s+termId="REGOPS_WEIGHT_DT_DEFAULT">DT 45%<\/TraceTooltip>/);
  });

  it('wrap "BACS 30%" avec termId REGOPS_WEIGHT_BACS_DEFAULT', () => {
    expect(src).toMatch(
      /<TraceTooltip\s+termId="REGOPS_WEIGHT_BACS_DEFAULT">BACS 30%<\/TraceTooltip>/
    );
  });

  it('wrap "APER 25%" avec termId REGOPS_WEIGHT_APER_DEFAULT', () => {
    expect(src).toMatch(
      /<TraceTooltip\s+termId="REGOPS_WEIGHT_APER_DEFAULT">APER 25%<\/TraceTooltip>/
    );
  });
});
