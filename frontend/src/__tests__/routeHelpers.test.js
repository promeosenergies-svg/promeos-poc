/**
 * PROMEOS — Tests route helpers (Sprint QA XS)
 * Vérifie que les helpers de navigation retournent les bons paths avec query params.
 */
import { describe, it, expect } from 'vitest';

import {
  toConformite,
  toRenewals,
  toSite,
  toConsoExplorer,
  toBillIntel,
  toPatrimoine,
  toPurchase,
  toConsoImport,
  toActionsList,
  toConsoDiag,
  toMonitoring,
  toPurchaseAssistant,
} from '../services/routes';

// ── Nouveaux helpers (Sprint Front S) ────────────────────────────────────────

describe('toConformite()', () => {
  it('returns /conformite without params', () => {
    expect(toConformite()).toBe('/conformite');
  });

  it('includes tab param', () => {
    expect(toConformite({ tab: 'obligations' })).toBe('/conformite?tab=obligations');
  });

  it('includes site_id param', () => {
    expect(toConformite({ site_id: 42 })).toBe('/conformite?site_id=42');
  });

  it('includes both tab and site_id', () => {
    const url = toConformite({ tab: 'donnees', site_id: 7 });
    expect(url).toContain('tab=donnees');
    expect(url).toContain('site_id=7');
  });
});

describe('toRenewals()', () => {
  it('returns /renouvellements without params', () => {
    expect(toRenewals()).toBe('/renouvellements');
  });

  it('includes site_id param', () => {
    expect(toRenewals({ site_id: 5 })).toBe('/renouvellements?site_id=5');
  });
});

describe('toSite()', () => {
  it('returns /sites/{id} without options', () => {
    expect(toSite(42)).toBe('/sites/42');
  });

  it('includes tab as hash', () => {
    expect(toSite(42, { tab: 'factures' })).toBe('/sites/42#factures');
  });

  it('works with string id', () => {
    expect(toSite('99')).toBe('/sites/99');
  });
});

// ── Helpers existants (régression) ───────────────────────────────────────────

describe('toConsoExplorer()', () => {
  it('returns base path without params', () => {
    expect(toConsoExplorer()).toBe('/consommations/explorer');
  });

  it('includes sites param as comma-separated', () => {
    expect(toConsoExplorer({ site_id: [1, 2, 3] })).toContain('sites=1%2C2%2C3');
  });

  it('includes days param', () => {
    expect(toConsoExplorer({ days: 90 })).toContain('days=90');
  });
});

describe('toBillIntel()', () => {
  it('returns /bill-intel without params', () => {
    expect(toBillIntel()).toBe('/bill-intel');
  });

  it('includes site_id and month', () => {
    const url = toBillIntel({ site_id: 5, month: '2026-03' });
    expect(url).toContain('site_id=5');
    expect(url).toContain('month=2026-03');
  });
});

describe('toPatrimoine()', () => {
  it('returns /patrimoine without params', () => {
    expect(toPatrimoine()).toBe('/patrimoine');
  });

  it('includes site_id param', () => {
    expect(toPatrimoine({ site_id: 3 })).toBe('/patrimoine?site_id=3');
  });
});

describe('toPurchase()', () => {
  it('returns /achat-energie without params', () => {
    expect(toPurchase()).toBe('/achat-energie');
  });

  it('includes tab param', () => {
    expect(toPurchase({ tab: 'simulation' })).toContain('tab=simulation');
  });
});

describe('toConsoImport()', () => {
  it('returns /consommations/import', () => {
    expect(toConsoImport()).toBe('/consommations/import');
  });
});

describe('toActionsList()', () => {
  it('returns /anomalies with tab=actions', () => {
    expect(toActionsList()).toContain('tab=actions');
  });

  it('includes source_type filter', () => {
    expect(toActionsList({ source_type: 'compliance' })).toContain('source_type=compliance');
  });
});

describe('toConsoDiag()', () => {
  it('includes site_id', () => {
    expect(toConsoDiag({ site_id: 7 })).toContain('site_id=7');
  });
});

describe('toMonitoring()', () => {
  it('includes site_id', () => {
    expect(toMonitoring({ site_id: 3 })).toContain('site_id=3');
  });
});

describe('toPurchaseAssistant()', () => {
  it('includes step param', () => {
    expect(toPurchaseAssistant({ step: 'offers' })).toContain('step=offers');
  });
});
