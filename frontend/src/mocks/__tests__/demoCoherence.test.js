/**
 * PROMEOS — Demo data coherence tests
 * Prevents regressions: all mock data must stay internally consistent.
 * Each test validates a cross-reference between mock files.
 */
import { describe, it, expect } from 'vitest';
import { mockSites } from '../sites';
import { mockKpis, mockTodos, mockTopAnomalies } from '../kpis';
import { mockActions } from '../actions';
import { mockObligations, getObligationScore } from '../obligations';

const SITE_IDS = new Set(mockSites.map((s) => s.id));
const SITE_NOMS = new Set(mockSites.map((s) => s.nom));

// ── Site invariants ─────────────────────────────────────────────────────

describe('mockSites — invariants', () => {
  it('has exactly 5 HELIOS sites', () => {
    expect(mockSites).toHaveLength(5);
  });

  it('all sites have required fields', () => {
    for (const s of mockSites) {
      expect(s.id).toBeGreaterThan(0);
      expect(s.nom).toBeTruthy();
      expect(s.ville).toBeTruthy();
      expect(s.surface_m2).toBeGreaterThan(0);
      expect(s.conso_kwh_an).toBeGreaterThan(0);
      expect(typeof s.risque_eur).toBe('number');
      expect(typeof s.anomalies_count).toBe('number');
      expect(s.portefeuille_id).toBeGreaterThan(0);
    }
  });

  it('IDs are unique', () => {
    expect(SITE_IDS.size).toBe(mockSites.length);
  });

  it('covers all 4 statut_conformite values', () => {
    const statuts = new Set(mockSites.map((s) => s.statut_conformite));
    expect(statuts).toContain('conforme');
    expect(statuts).toContain('non_conforme');
    expect(statuts).toContain('en_cours');
    expect(statuts).toContain('a_risque');
  });

  it('portefeuille_id covers 3 portfolios', () => {
    const pfs = new Set(mockSites.map((s) => s.portefeuille_id));
    expect(pfs.size).toBe(3);
  });
});

// ── KPIs coherence ──────────────────────────────────────────────────────

describe('mockKpis — coherence with sites', () => {
  it('conformite counts match mockSites', () => {
    const conformes = mockSites.filter((s) => s.statut_conformite === 'conforme').length;
    const nonConformes = mockSites.filter((s) => s.statut_conformite === 'non_conforme').length;
    expect(mockKpis.conformite.conformes).toBe(conformes);
    expect(mockKpis.conformite.non_conformes).toBe(nonConformes);
    expect(mockKpis.conformite.total_sites).toBe(mockSites.length);
  });

  it('risque_financier matches sum of site risks', () => {
    const totalRisque = mockSites.reduce((sum, s) => sum + s.risque_eur, 0);
    expect(mockKpis.risque_financier.total_eur).toBe(totalRisque);
  });

  it('anomalies total matches sum of site anomalies', () => {
    const totalAnomalies = mockSites.reduce((sum, s) => sum + s.anomalies_count, 0);
    expect(mockKpis.anomalies.total).toBe(totalAnomalies);
  });

  it('action_prioritaire.nb_sites <= mockSites.length', () => {
    expect(mockKpis.action_prioritaire.nb_sites).toBeLessThanOrEqual(mockSites.length);
  });
});

// ── Todos coherence ─────────────────────────────────────────────────────

describe('mockTodos — coherence with sites', () => {
  it('all todos reference existing site names', () => {
    for (const todo of mockTodos) {
      expect(SITE_NOMS).toContain(todo.site);
    }
  });

  it('all todos have site_id matching a real site', () => {
    for (const todo of mockTodos) {
      expect(SITE_IDS).toContain(todo.site_id);
    }
  });

  it('site_id and site name are consistent', () => {
    for (const todo of mockTodos) {
      const site = mockSites.find((s) => s.id === todo.site_id);
      expect(site).toBeDefined();
      expect(site.nom).toBe(todo.site);
    }
  });

  it('todos have valid echeance dates', () => {
    for (const todo of mockTodos) {
      expect(todo.echeance).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    }
  });
});

// ── Top anomalies coherence ─────────────────────────────────────────────

describe('mockTopAnomalies — coherence with sites', () => {
  it('all anomalies reference existing site IDs', () => {
    for (const a of mockTopAnomalies) {
      expect(SITE_IDS).toContain(a.site_id);
    }
  });

  it('anomaly site_nom matches actual site name', () => {
    for (const a of mockTopAnomalies) {
      const site = mockSites.find((s) => s.id === a.site_id);
      expect(site).toBeDefined();
      expect(a.site_nom).toBe(site.nom);
    }
  });
});

// ── Actions coherence ───────────────────────────────────────────────────

describe('mockActions — coherence with sites', () => {
  it('all actions reference existing site IDs', () => {
    for (const a of mockActions) {
      expect(SITE_IDS).toContain(a.site_id);
    }
  });

  it('action site_nom matches actual site name', () => {
    for (const a of mockActions) {
      const site = mockSites.find((s) => s.id === a.site_id);
      expect(site).toBeDefined();
      expect(a.site_nom).toBe(site.nom);
    }
  });

  it('all actions are deterministic (no Math.random)', async () => {
    const fs = await import('fs');
    const src = fs.readFileSync(
      'c:/Users/amine/promeos-poc/promeos-poc/frontend/src/mocks/actions.js',
      'utf-8'
    );
    expect(src).not.toContain('Math.random');
  });

  it('actions cover all 4 types', () => {
    const types = new Set(mockActions.map((a) => a.type));
    expect(types).toContain('conformite');
    expect(types).toContain('conso');
    expect(types).toContain('facture');
    expect(types).toContain('maintenance');
  });

  it('actions cover all 4 statuts', () => {
    const statuts = new Set(mockActions.map((a) => a.statut));
    expect(statuts).toContain('backlog');
    expect(statuts).toContain('planned');
    expect(statuts).toContain('in_progress');
    expect(statuts).toContain('done');
  });

  it('actions cover all 4 priorities', () => {
    const prios = new Set(mockActions.map((a) => a.priorite));
    expect(prios).toContain('critical');
    expect(prios).toContain('high');
    expect(prios).toContain('medium');
    expect(prios).toContain('low');
  });

  it('all 5 sites have at least 1 action', () => {
    for (const siteId of SITE_IDS) {
      expect(mockActions.some((a) => a.site_id === siteId)).toBe(true);
    }
  });

  it('action IDs are unique', () => {
    const ids = new Set(mockActions.map((a) => a.id));
    expect(ids.size).toBe(mockActions.length);
  });
});

// ── Obligations coherence ───────────────────────────────────────────────

describe('mockObligations — coherence with sites', () => {
  it('sites_concernes never exceeds mockSites.length', () => {
    for (const o of mockObligations) {
      expect(o.sites_concernes).toBeLessThanOrEqual(mockSites.length);
    }
  });

  it('sites_conformes never exceeds sites_concernes', () => {
    for (const o of mockObligations) {
      expect(o.sites_conformes).toBeLessThanOrEqual(o.sites_concernes);
    }
  });

  it('getObligationScore returns consistent aggregate', () => {
    const score = getObligationScore();
    expect(score.total).toBe(mockObligations.length);
    expect(score.conformes + score.non_conformes + score.a_risque).toBeLessThanOrEqual(score.total);
    expect(score.pct).toBeGreaterThanOrEqual(0);
    expect(score.pct).toBeLessThanOrEqual(100);
  });

  it('all obligations have valid severity', () => {
    const validSeverities = new Set(['critical', 'high', 'medium', 'low']);
    for (const o of mockObligations) {
      expect(validSeverities).toContain(o.severity);
    }
  });

  it('all obligations have valid proof_status', () => {
    const validStatuses = new Set(['ok', 'in_progress', 'missing']);
    for (const o of mockObligations) {
      expect(validStatuses).toContain(o.proof_status);
    }
  });
});

// ── Cross-file consistency ──────────────────────────────────────────────

describe('Cross-file consistency', () => {
  it('total risque in KPIs matches sites sum', () => {
    const fromSites = mockSites.reduce((s, site) => s + site.risque_eur, 0);
    expect(mockKpis.risque_financier.total_eur).toBe(fromSites);
  });

  it('no English text in todo labels', () => {
    for (const todo of mockTodos) {
      expect(todo.texte).not.toMatch(/^[A-Z][a-z]+ the |Fix |Update |Install the /);
    }
  });

  it('no English text in action titles', () => {
    for (const a of mockActions) {
      expect(a.titre).not.toMatch(/^[A-Z][a-z]+ the |Fix |Update |Install the /);
    }
  });

  it('no English text in obligation descriptions', () => {
    for (const o of mockObligations) {
      expect(o.description).not.toMatch(/^[A-Z][a-z]+ the |Must |Should /);
    }
  });

  it('mockKpis.conformite.a_risque > 0 (code path exercised)', () => {
    expect(mockKpis.conformite.a_risque).toBeGreaterThan(0);
  });
});

// ── Single source of truth ─────────────────────────────────────────────

describe('Single source of truth — all mocks derive from sites.js', () => {
  it('kpis.js imports from ./sites', async () => {
    const fs = await import('fs');
    const src = fs.readFileSync(
      'c:/Users/amine/promeos-poc/promeos-poc/frontend/src/mocks/kpis.js',
      'utf-8'
    );
    expect(src).toContain("from './sites'");
  });

  it('actions.js imports from ./sites', async () => {
    const fs = await import('fs');
    const src = fs.readFileSync(
      'c:/Users/amine/promeos-poc/promeos-poc/frontend/src/mocks/actions.js',
      'utf-8'
    );
    expect(src).toContain("from './sites'");
  });

  it('no Math.random in any mock file', async () => {
    const fs = await import('fs');
    const files = ['sites.js', 'kpis.js', 'actions.js', 'obligations.js'];
    for (const f of files) {
      const src = fs.readFileSync(
        `c:/Users/amine/promeos-poc/promeos-poc/frontend/src/mocks/${f}`,
        'utf-8'
      );
      expect(src).not.toContain('Math.random');
    }
  });

  it('no Date.now() in any mock file', async () => {
    const fs = await import('fs');
    const files = ['sites.js', 'kpis.js', 'actions.js', 'obligations.js'];
    for (const f of files) {
      const src = fs.readFileSync(
        `c:/Users/amine/promeos-poc/promeos-poc/frontend/src/mocks/${f}`,
        'utf-8'
      );
      expect(src).not.toContain('Date.now()');
    }
  });

  it('mockTodos derive site names from mockSites (no hardcoded names)', async () => {
    const fs = await import('fs');
    const src = fs.readFileSync(
      'c:/Users/amine/promeos-poc/promeos-poc/frontend/src/mocks/kpis.js',
      'utf-8'
    );
    // Todos should use SITE[id].nom pattern, not hardcoded strings
    expect(src).toMatch(/SITE\[\d+\]\.nom/);
    // Should NOT contain hardcoded site names in todo definitions
    const todoSection = src.slice(src.indexOf('mockTodos'));
    expect(todoSection).not.toMatch(/site:\s*'(Siege|Bureau|Usine|Hotel|Ecole)/);
  });
});
