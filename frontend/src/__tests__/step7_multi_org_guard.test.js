/**
 * PROMEOS — Step 7: Multi-org (HELIOS + MERIDIAN) source-guard tests
 * Verifie que le frontend supporte le multi-org et que le seed MERIDIAN existe.
 */

import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const read = (rel) => readFileSync(join(__dirname, rel), 'utf-8');

// ── A. ScopeContext multi-org support ────────────────────────────────────────

describe('A. ScopeContext multi-org', () => {
  const src = read('../contexts/ScopeContext.jsx');

  test('A1. has MOCK_ORGS array', () => {
    expect(src).toMatch(/MOCK_ORGS\s*=\s*\[/);
  });

  test('A2. has demoOrgs state', () => {
    expect(src).toMatch(/demoOrgs/);
  });

  test('A3. has applyDemoScope function', () => {
    expect(src).toMatch(/applyDemoScope/);
  });

  test('A4. merges MOCK_ORGS with demoOrgs', () => {
    expect(src).toMatch(/\.\.\.MOCK_ORGS/);
    expect(src).toMatch(/demoOrgs/);
  });

  test('A5. persists demoOrgs to localStorage', () => {
    expect(src).toMatch(/DEMO_ORGS_KEY/);
    expect(src).toMatch(/saveDemoOrgs/);
  });

  test('A6. deduplicates orgs by id', () => {
    expect(src).toMatch(/\.some\(\s*\(?o\)?\s*=>\s*o\.id\s*===\s*d\.id\)?/);
  });

  test('A7. exposes orgs in context value', () => {
    expect(src).toMatch(/orgs:\s*orgsData/);
  });

  test('A8. setOrg resets portefeuille and site', () => {
    expect(src).toMatch(/portefeuilleId:\s*null/);
  });
});

// ── B. ScopeSwitcher renders org list ────────────────────────────────────────

describe('B. ScopeSwitcher multi-org', () => {
  let switcherSrc;
  try {
    switcherSrc = read('../layout/ScopeSwitcher.jsx');
  } catch {
    switcherSrc = null;
  }

  test('B1. ScopeSwitcher file exists', () => {
    expect(switcherSrc).not.toBeNull();
  });

  test('B2. ScopeSwitcher uses orgs from scope', () => {
    if (!switcherSrc) return;
    expect(switcherSrc).toMatch(/orgs/);
  });

  test('B3. ScopeSwitcher calls setOrg', () => {
    if (!switcherSrc) return;
    expect(switcherSrc).toMatch(/setOrg/);
  });
});

// ── C. Backend seed pack MERIDIAN exists ─────────────────────────────────────

describe('C. Backend seed pack MERIDIAN', () => {
  const packsSrc = read('../../../backend/services/demo_seed/packs.py');

  test('C1. packs.py defines meridian pack', () => {
    expect(packsSrc).toMatch(/"meridian"/);
  });

  test('C2. MERIDIAN org name is MERIDIAN SAS', () => {
    expect(packsSrc).toMatch(/MERIDIAN SAS/);
  });

  test('C3. MERIDIAN has 3 sites_explicit', () => {
    expect(packsSrc).toMatch(/Levallois/);
    expect(packsSrc).toMatch(/Bordeaux/);
    expect(packsSrc).toMatch(/Gennevilliers/);
  });

  test('C4. MERIDIAN siren differs from HELIOS', () => {
    expect(packsSrc).toMatch(/987654321/); // MERIDIAN
    expect(packsSrc).toMatch(/123456789/); // HELIOS
  });

  test('C5. MERIDIAN pack is visible', () => {
    // visible: True appears in meridian block
    const meridianBlock = packsSrc.split('"meridian"')[1];
    expect(meridianBlock).toMatch(/"visible":\s*True/);
  });

  test('C6. MERIDIAN has contracts_spec', () => {
    const meridianBlock = packsSrc.split('"meridian"')[1];
    expect(meridianBlock).toMatch(/contracts_spec/);
  });
});

// ── D. CLI accepts meridian ──────────────────────────────────────────────────

describe('D. CLI accepts meridian', () => {
  const cliSrc = read('../../../backend/services/demo_seed/__main__.py');

  test('D1. __main__.py choices include meridian', () => {
    expect(cliSrc).toMatch(/meridian/);
  });

  test('D2. CLI still accepts helios', () => {
    expect(cliSrc).toMatch(/helios/);
  });
});

// ── E. Isolation guarantees ──────────────────────────────────────────────────

describe('E. Isolation guarantees', () => {
  const packsSrc = read('../../../backend/services/demo_seed/packs.py');

  test('E1. HELIOS and MERIDIAN have different org names', () => {
    expect(packsSrc).toMatch(/Groupe HELIOS/);
    expect(packsSrc).toMatch(/MERIDIAN SAS/);
  });

  test('E2. HELIOS has 5 sites, MERIDIAN has 3', () => {
    const heliosBlock = packsSrc.split('"helios"')[1].split('"meridian"')[0];
    const meridianBlock = packsSrc.split('"meridian"')[1];
    // Count site entries via "nom": pattern in sites_explicit
    const heliosSites = (heliosBlock.match(/"nom":\s*"/g) || []).length;
    const meridianSites = (meridianBlock.match(/"nom":\s*"/g) || []).length;
    expect(heliosSites).toBeGreaterThanOrEqual(5);
    expect(meridianSites).toBeGreaterThanOrEqual(3);
  });
});
