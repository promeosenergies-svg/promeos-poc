/**
 * Retrait deep-links conformité cassés — Sprint 1 Vague A phase A5
 *
 * Les 3 entrées `/conformite/{dt,bacs,audit-sme}` étaient dans
 * ROUTE_MODULE_MAP mais aucune Route React correspondante → NotFound
 * avec rail éclairé en émeraude (promesse cassée).
 *
 * Audit fresh §8 Q7 arbitrage : **retrait** (Vague 1 propre), réintroduction
 * via `/conformite?tab=obligations&focus=X` prévue Vague D Sprint 2.
 */
import { describe, it, expect } from 'vitest';
import {
  ROUTE_MODULE_MAP,
  NAV_SECTIONS,
  HIDDEN_PAGES,
  QUICK_ACTIONS,
  COMMAND_SHORTCUTS,
  PANEL_DEEP_LINKS_BY_ROUTE,
} from '../NavRegistry';

const RETIRED_ROUTES = ['/conformite/dt', '/conformite/bacs', '/conformite/audit-sme'];

describe('Conformité deep-links retired (A5 + F3)', () => {
  it.each(RETIRED_ROUTES)('%s is not in ROUTE_MODULE_MAP anymore', (route) => {
    expect(ROUTE_MODULE_MAP[route]).toBeUndefined();
  });

  it('real /conformite base routes remain mapped', () => {
    expect(ROUTE_MODULE_MAP['/conformite']).toBe('conformite');
    expect(ROUTE_MODULE_MAP['/conformite/aper']).toBe('conformite');
    expect(ROUTE_MODULE_MAP['/conformite/tertiaire']).toBe('conformite');
  });

  // F3 fix P0-T2 : empêcher une réintroduction via NAV_SECTIONS items.to
  // OU via HIDDEN_PAGES / QUICK_ACTIONS / COMMAND_SHORTCUTS / deep-links
  // panel. Sinon le rail s'éclairerait (fallback préfixe sur /conformite)
  // mais la page tomberait sur NotFound = promesse cassée rétablie
  // silencieusement.
  it.each(RETIRED_ROUTES)('%s is not referenced anywhere in NAV_SECTIONS items', (route) => {
    const allItemTos = NAV_SECTIONS.flatMap((s) => s.items ?? []).map((i) => i.to);
    expect(allItemTos.filter((to) => to.split('?')[0] === route)).toEqual([]);
  });

  it.each(RETIRED_ROUTES)('%s is not referenced in HIDDEN_PAGES', (route) => {
    const hiddenTos = HIDDEN_PAGES.map((p) => p.to.split('?')[0]);
    expect(hiddenTos).not.toContain(route);
  });

  it.each(RETIRED_ROUTES)('%s is not referenced in QUICK_ACTIONS', (route) => {
    const quickTos = QUICK_ACTIONS.map((a) => a.to.split('?')[0]);
    expect(quickTos).not.toContain(route);
  });

  it.each(RETIRED_ROUTES)('%s is not referenced in COMMAND_SHORTCUTS', (route) => {
    const shortTos = COMMAND_SHORTCUTS.map((s) => s.to.split('?')[0]);
    expect(shortTos).not.toContain(route);
  });

  it.each(RETIRED_ROUTES)('%s is not a PANEL_DEEP_LINKS_BY_ROUTE key or href', (route) => {
    expect(PANEL_DEEP_LINKS_BY_ROUTE[route]).toBeUndefined();
    const allHrefs = Object.values(PANEL_DEEP_LINKS_BY_ROUTE)
      .flat()
      .map((l) => l.href.split('?')[0]);
    expect(allHrefs).not.toContain(route);
  });
});
