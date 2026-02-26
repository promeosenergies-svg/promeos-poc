/**
 * PROMEOS — Actions Console V1 — Source-guard + route registry tests
 * Verify:
 * 1. Route registry helpers work correctly
 * 2. No hardcoded /actions URLs in key pages
 * 3. CTA structure present in key pages
 * 4. ActionsPage has required constructs
 *
 * Tests 100% readFileSync / regex + unit tests — no DOM mock needed.
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');

// ============================================================
// A. Route Registry — unit tests
// ============================================================
describe('A · Route Registry helpers', () => {
  let routes;

  // Dynamic import to test the actual module
  it('module exports all helpers', async () => {
    routes = await import('../../services/routes.js');
    expect(routes.toActionNew).toBeTypeOf('function');
    expect(routes.toAction).toBeTypeOf('function');
    expect(routes.toActionsList).toBeTypeOf('function');
    expect(routes.toConsoExplorer).toBeTypeOf('function');
    expect(routes.toConsoDiag).toBeTypeOf('function');
    expect(routes.toBillIntel).toBeTypeOf('function');
  });

  it('toActionNew() returns /actions/new without params', async () => {
    routes = await import('../../services/routes.js');
    expect(routes.toActionNew()).toBe('/actions/new');
  });

  it('toActionNew() includes type and site_id params', async () => {
    routes = await import('../../services/routes.js');
    const url = routes.toActionNew({ source_type: 'facture', site_id: 42 });
    expect(url).toContain('/actions/new?');
    expect(url).toContain('type=facture');
    expect(url).toContain('site_id=42');
  });

  it('toActionNew() includes impact_eur param', async () => {
    routes = await import('../../services/routes.js');
    const url = routes.toActionNew({ impact_eur: 5000 });
    expect(url).toContain('impact_eur=5000');
  });

  it('toActionNew() includes date_from and date_to params', async () => {
    routes = await import('../../services/routes.js');
    const url = routes.toActionNew({ date_from: '2026-01-01', date_to: '2026-12-31' });
    expect(url).toContain('date_from=2026-01-01');
    expect(url).toContain('date_to=2026-12-31');
  });

  it('toActionNew() includes campaign_sites array', async () => {
    routes = await import('../../services/routes.js');
    const url = routes.toActionNew({ site_ids: [1, 2, 3] });
    expect(url).toContain('campaign_sites=1%2C2%2C3');
  });

  it('toAction() returns /actions/:id', async () => {
    routes = await import('../../services/routes.js');
    expect(routes.toAction(42)).toBe('/actions/42');
    expect(routes.toAction('abc')).toBe('/actions/abc');
  });

  it('toActionsList() returns /actions without params', async () => {
    routes = await import('../../services/routes.js');
    expect(routes.toActionsList()).toBe('/actions');
  });

  it('toActionsList() includes status param', async () => {
    routes = await import('../../services/routes.js');
    const url = routes.toActionsList({ status: 'backlog' });
    expect(url).toContain('status=backlog');
  });

  it('toActionsList() includes source_type param', async () => {
    routes = await import('../../services/routes.js');
    const url = routes.toActionsList({ source_type: 'billing' });
    expect(url).toContain('source_type=billing');
  });

  it('toActionsList() includes date_from/date_to params', async () => {
    routes = await import('../../services/routes.js');
    const url = routes.toActionsList({ date_from: '2026-01-01', date_to: '2026-06-30' });
    expect(url).toContain('date_from=2026-01-01');
    expect(url).toContain('date_to=2026-06-30');
  });
});

// ============================================================
// B. No hardcoded /actions URLs in key pages
// ============================================================
describe('B · Zero hardcoded /actions URL in navigate()', () => {
  const PAGES_TO_CHECK = [
    ['pages', 'Cockpit.jsx'],
    ['pages', 'CommandCenter.jsx'],
  ];

  PAGES_TO_CHECK.forEach(([...pathParts]) => {
    const fileName = pathParts[pathParts.length - 1];

    it(`${fileName}: no navigate('/actions') hardcoded`, () => {
      const code = readSrc(...pathParts);
      // Match navigate('/actions') or navigate("/actions") — literal string
      const hardcoded = code.match(/navigate\(\s*['"]\/actions['"]\s*\)/g);
      expect(hardcoded, `Found hardcoded navigate('/actions') in ${fileName}`).toBeNull();
    });

    it(`${fileName}: imports toActionsList from route registry`, () => {
      const code = readSrc(...pathParts);
      expect(code).toMatch(/import\s*\{[^}]*toActionsList[^}]*\}\s*from\s*['"]\.\.\/services\/routes['"]/);
    });
  });
});

// ============================================================
// C. ActionsPage structure
// ============================================================
describe('C · ActionsPage required constructs', () => {
  const code = readSrc('pages', 'ActionsPage.jsx');

  it('has route params (useParams for actionId)', () => {
    expect(code).toMatch(/useParams/);
    expect(code).toMatch(/actionId/);
  });

  it('has search params (useSearchParams)', () => {
    expect(code).toMatch(/useSearchParams/);
  });

  it('has status filter', () => {
    expect(code).toMatch(/filterStatut|setFilterStatut/);
  });

  it('has type filter', () => {
    expect(code).toMatch(/filterType|setFilterType/);
  });

  it('has search functionality', () => {
    expect(code).toMatch(/searchQuery|setSearchQuery/);
    expect(code).toMatch(/Rechercher/);
  });

  it('has empty state with "Aucune action"', () => {
    expect(code).toMatch(/Aucune action/);
  });

  it('has empty state with "Reinitialiser" CTA', () => {
    expect(code).toMatch(/[Rr][eé]initialiser/);
  });

  it('has "Creer action" CTA', () => {
    expect(code).toMatch(/Cr[eé]er action/);
  });

  it('has Kanban view', () => {
    expect(code).toMatch(/KanbanBoard|viewMode.*kanban/);
  });

  it('has table view with sort', () => {
    expect(code).toMatch(/handleSort|sortCol/);
  });

  it('has bulk operations', () => {
    expect(code).toMatch(/bulkChangeStatus|bulkAssign/);
  });

  it('has inline status change', () => {
    expect(code).toMatch(/handleInlineStatusChange/);
  });

  it('has detail drawer', () => {
    expect(code).toMatch(/ActionDetailDrawer/);
  });

  it('has create modal', () => {
    expect(code).toMatch(/CreateActionModal/);
  });

  it('maps created_at from backend', () => {
    expect(code).toMatch(/created_at:\s*a\.created_at/);
  });

  it('maps campaign_sites from backend', () => {
    expect(code).toMatch(/campaign_sites:\s*a\.campaign_sites/);
  });

  it('has auto-open detail on /actions/:actionId', () => {
    expect(code).toMatch(/urlActionId.*actions.*length/);
  });

  it('has auto-open create on /actions/new', () => {
    expect(code).toMatch(/autoCreate/);
  });
});

// ============================================================
// D. Route registry source integrity
// ============================================================
describe('D · Route registry source integrity', () => {
  const code = readSrc('services', 'routes.js');

  it('exports toActionNew', () => {
    expect(code).toMatch(/export function toActionNew/);
  });

  it('exports toAction', () => {
    expect(code).toMatch(/export function toAction/);
  });

  it('exports toActionsList', () => {
    expect(code).toMatch(/export function toActionsList/);
  });

  it('toActionNew supports impact_eur param', () => {
    expect(code).toMatch(/impact_eur/);
  });

  it('toActionNew supports date_from param', () => {
    expect(code).toMatch(/date_from/);
  });

  it('toActionsList supports status param', () => {
    expect(code).toMatch(/opts\.status/);
  });

  it('toActionsList supports source_type param', () => {
    expect(code).toMatch(/opts\.source_type/);
  });
});

// ============================================================
// E. CTA presence in source pages
// ============================================================
describe('E · CTA "Creer action" in source pages', () => {
  const CTA_PAGES = [
    ['pages', 'BillIntelPage.jsx'],
    ['pages', 'AnomaliesPage.jsx'],
  ];

  CTA_PAGES.forEach(([...pathParts]) => {
    const fileName = pathParts[pathParts.length - 1];

    it(`${fileName}: has "Creer action" CTA text`, () => {
      const code = readSrc(...pathParts);
      expect(code).toMatch(/Cr[eé]er action/);
    });
  });
});

// ============================================================
// F. Deep link helpers integrity
// ============================================================
describe('F · Deep link helpers', () => {
  const code = readSrc('services', 'deepLink.js');

  it('exports deepLinkAction', () => {
    expect(code).toMatch(/export function deepLinkAction/);
  });

  it('exports deepLinkNewAction', () => {
    expect(code).toMatch(/export function deepLinkNewAction/);
  });

  it('deepLinkAction builds /actions/:id', () => {
    expect(code).toMatch(/\/actions\/\$\{actionId\}/);
  });
});

// ============================================================
// G. App routing
// ============================================================
describe('G · App.jsx actions routing', () => {
  const code = readSrc('App.jsx');

  it('has /actions route', () => {
    expect(code).toMatch(/path="\/actions"/);
  });

  it('has /actions/new route', () => {
    expect(code).toMatch(/path="\/actions\/new"/);
  });

  it('has /actions/:actionId route', () => {
    expect(code).toMatch(/path="\/actions\/:actionId"/);
  });

  it('ActionsPage receives autoCreate prop on /new', () => {
    expect(code).toMatch(/autoCreate/);
  });
});

// ============================================================
// H. Backend test file exists
// ============================================================
describe('H · Backend actions test exists', () => {
  it('test_actions_console.py exists', () => {
    const backendRoot = resolve(root, '..', 'backend');
    const code = readFileSync(resolve(backendRoot, 'tests', 'test_actions_console.py'), 'utf-8');
    expect(code).toContain('TestActionCreate');
    expect(code).toContain('TestActionPatch');
    expect(code).toContain('campaign_sites');
    expect(code).toContain('created_at');
  });
});
