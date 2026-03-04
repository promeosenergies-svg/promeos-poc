/**
 * PROMEOS — V27: Product Invariant Guards
 * 10 invariants metier critiques — tests fonctionnels (pas techniques).
 *
 * INV-1: total === sites.length
 * INV-2: risqueTotal = sum(sites.risque_eur)
 * INV-3: conformite hierarchy (NOK > A_RISQUE > OK)
 * INV-4: couvertureDonnees = sites avec conso / total
 * INV-5: api.js injecte X-Org-Id (sauf /demo/)
 * INV-6: setOrg() reset siteId + portefeuilleId
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

import {
  buildDashboardEssentials,
  buildExecutiveKpis,
  checkConsistency,
} from '../../models/dashboardEssentials';

const readSrc = (relPath) => readFileSync(resolve(__dirname, '..', '..', relPath), 'utf8');

// ── Mock sites factory ──────────────────────────────────────────────────────

function makeSite(overrides = {}) {
  return {
    id: 1,
    nom: 'Site Test',
    statut_conformite: 'conforme',
    risque_eur: 0,
    conso_kwh_an: 1000,
    ...overrides,
  };
}

// ══════════════════════════════════════════════════════════════════════════════
// INV-1: Cockpit total_sites === sites.length
// ══════════════════════════════════════════════════════════════════════════════

describe('INV-1: total === sites.length', () => {
  it('returns total equal to input array length', () => {
    const sites = [makeSite({ id: 1 }), makeSite({ id: 2 }), makeSite({ id: 3 })];
    const result = buildDashboardEssentials(sites);
    expect(result.kpis.total).toBe(3);
  });

  it('returns 0 for empty sites array', () => {
    const result = buildDashboardEssentials([]);
    expect(result.kpis.total).toBe(0);
  });

  it('handles single site', () => {
    const result = buildDashboardEssentials([makeSite()]);
    expect(result.kpis.total).toBe(1);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// INV-2: risqueTotal = SUM(sites.risque_eur)
// ══════════════════════════════════════════════════════════════════════════════

describe('INV-2: risqueTotal = sum(sites.risque_eur)', () => {
  it('sums risque_eur across all sites', () => {
    const sites = [
      makeSite({ id: 1, risque_eur: 5000 }),
      makeSite({ id: 2, risque_eur: 12000 }),
      makeSite({ id: 3, risque_eur: 3000 }),
    ];
    const result = buildDashboardEssentials(sites);
    expect(result.kpis.risqueTotal).toBe(20000);
  });

  it('treats null/undefined risque_eur as 0', () => {
    const sites = [
      makeSite({ id: 1, risque_eur: 5000 }),
      makeSite({ id: 2, risque_eur: null }),
      makeSite({ id: 3, risque_eur: undefined }),
    ];
    const result = buildDashboardEssentials(sites);
    expect(result.kpis.risqueTotal).toBe(5000);
  });

  it('returns 0 when no sites', () => {
    const result = buildDashboardEssentials([]);
    expect(result.kpis.risqueTotal).toBe(0);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// INV-3: Conformite hierarchy (NOK > A_RISQUE > OK)
// ══════════════════════════════════════════════════════════════════════════════

describe('INV-3: conformite hierarchy', () => {
  it('status=crit if any site is non_conforme', () => {
    const sites = [
      makeSite({ id: 1, statut_conformite: 'conforme' }),
      makeSite({ id: 2, statut_conformite: 'non_conforme', risque_eur: 10000 }),
      makeSite({ id: 3, statut_conformite: 'a_risque', risque_eur: 5000 }),
    ];
    const kpis = buildDashboardEssentials(sites).kpis;
    const tiles = buildExecutiveKpis(kpis, sites);
    const conformiteTile = tiles.find((t) => t.id === 'conformite');
    expect(conformiteTile.status).toBe('crit');
  });

  it('status=warn if a_risque but no non_conforme', () => {
    const sites = [
      makeSite({ id: 1, statut_conformite: 'conforme' }),
      makeSite({ id: 2, statut_conformite: 'a_risque', risque_eur: 5000 }),
    ];
    const kpis = buildDashboardEssentials(sites).kpis;
    const tiles = buildExecutiveKpis(kpis, sites);
    const conformiteTile = tiles.find((t) => t.id === 'conformite');
    expect(conformiteTile.status).toBe('warn');
  });

  it('status=ok if all sites are conforme', () => {
    const sites = [
      makeSite({ id: 1, statut_conformite: 'conforme' }),
      makeSite({ id: 2, statut_conformite: 'conforme' }),
    ];
    const kpis = buildDashboardEssentials(sites).kpis;
    const tiles = buildExecutiveKpis(kpis, sites);
    const conformiteTile = tiles.find((t) => t.id === 'conformite');
    expect(conformiteTile.status).toBe('ok');
  });

  it('risque tile = crit if risqueTotal > 50k', () => {
    const sites = [makeSite({ id: 1, statut_conformite: 'non_conforme', risque_eur: 60000 })];
    const kpis = buildDashboardEssentials(sites).kpis;
    const tiles = buildExecutiveKpis(kpis, sites);
    const risqueTile = tiles.find((t) => t.id === 'risque');
    expect(risqueTile.status).toBe('crit');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// INV-4: couvertureDonnees = pct sites avec conso > 0
// ══════════════════════════════════════════════════════════════════════════════

describe('INV-4: couvertureDonnees formula', () => {
  it('60% when 3/5 sites have consumption', () => {
    const sites = [
      makeSite({ id: 1, conso_kwh_an: 1000 }),
      makeSite({ id: 2, conso_kwh_an: 500 }),
      makeSite({ id: 3, conso_kwh_an: 200 }),
      makeSite({ id: 4, conso_kwh_an: 0 }),
      makeSite({ id: 5, conso_kwh_an: 0 }),
    ];
    const result = buildDashboardEssentials(sites);
    expect(result.kpis.couvertureDonnees).toBe(60);
  });

  it('0% when no sites have consumption', () => {
    const sites = [makeSite({ id: 1, conso_kwh_an: 0 }), makeSite({ id: 2, conso_kwh_an: 0 })];
    const result = buildDashboardEssentials(sites);
    expect(result.kpis.couvertureDonnees).toBe(0);
  });

  it('100% when all sites have consumption', () => {
    const sites = [makeSite({ id: 1, conso_kwh_an: 1000 }), makeSite({ id: 2, conso_kwh_an: 500 })];
    const result = buildDashboardEssentials(sites);
    expect(result.kpis.couvertureDonnees).toBe(100);
  });

  it('0 for empty array (no division by zero)', () => {
    const result = buildDashboardEssentials([]);
    expect(result.kpis.couvertureDonnees).toBe(0);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// INV-5: api.js injecte X-Org-Id sur tous les appels (sauf /demo/)
// ══════════════════════════════════════════════════════════════════════════════

describe('INV-5: scope injection in api.js', () => {
  const apiSrc = readSrc('services/api.js');

  it('injects X-Org-Id header from _apiScope', () => {
    expect(apiSrc).toContain("config.headers['X-Org-Id']");
  });

  it('injects X-Site-Id header from _apiScope', () => {
    expect(apiSrc).toContain("config.headers['X-Site-Id']");
  });

  it('skips scope injection for /demo/ paths', () => {
    expect(apiSrc).toContain('isDemoPath');
    expect(apiSrc).toMatch(/if\s*\(\s*!isDemoPath/);
  });

  it('exports setApiScope function', () => {
    expect(apiSrc).toMatch(/export\s+function\s+setApiScope/);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// INV-6: setOrg() resets siteId + portefeuilleId
// ══════════════════════════════════════════════════════════════════════════════

describe('INV-6: scope reset on org change', () => {
  const scopeSrc = readSrc('contexts/ScopeContext.jsx');

  it('setOrg nullifies portefeuilleId', () => {
    // setOrg creates next with portefeuilleId: null
    expect(scopeSrc).toMatch(/setOrg.*portefeuilleId:\s*null/s);
  });

  it('setOrg nullifies siteId', () => {
    // setOrg creates next with siteId: null
    expect(scopeSrc).toMatch(/setOrg.*siteId:\s*null/s);
  });

  it('setPortefeuille nullifies siteId', () => {
    // setPortefeuille creates next with siteId: null
    expect(scopeSrc).toMatch(/setPortefeuille.*siteId:\s*null/s);
  });

  it('resetScope preserves orgId but clears portefeuille and site', () => {
    expect(scopeSrc).toMatch(/resetScope.*portefeuilleId:\s*null.*siteId:\s*null/s);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// INV-3 extended: checkConsistency flags impossible states
// ══════════════════════════════════════════════════════════════════════════════

describe('INV-3 extended: consistency checks', () => {
  it('flags all_conformes_low_data when 100% conforme but coverage < 30%', () => {
    const kpis = {
      total: 5,
      conformes: 5,
      nonConformes: 0,
      aRisque: 0,
      risqueTotal: 0,
      couvertureDonnees: 20,
    };
    const result = checkConsistency(kpis);
    expect(result.ok).toBe(false);
    expect(result.issues.some((i) => i.code === 'all_conformes_low_data')).toBe(true);
  });

  it('flags no_data_coverage when coverage=0 with sites', () => {
    const kpis = {
      total: 3,
      conformes: 0,
      nonConformes: 0,
      aRisque: 0,
      risqueTotal: 0,
      couvertureDonnees: 0,
    };
    const result = checkConsistency(kpis);
    expect(result.ok).toBe(false);
    expect(result.issues.some((i) => i.code === 'no_data_coverage')).toBe(true);
  });

  it('returns ok when data is consistent', () => {
    const kpis = {
      total: 5,
      conformes: 3,
      nonConformes: 1,
      aRisque: 1,
      risqueTotal: 10000,
      couvertureDonnees: 80,
    };
    const result = checkConsistency(kpis);
    expect(result.ok).toBe(true);
    expect(result.issues).toHaveLength(0);
  });
});
