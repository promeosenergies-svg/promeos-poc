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
import { ROUTE_MODULE_MAP } from '../NavRegistry';

const RETIRED_ROUTES = ['/conformite/dt', '/conformite/bacs', '/conformite/audit-sme'];

describe('Conformité deep-links retired (A5)', () => {
  it.each(RETIRED_ROUTES)('%s is not in ROUTE_MODULE_MAP anymore', (route) => {
    expect(ROUTE_MODULE_MAP[route]).toBeUndefined();
  });

  it('real /conformite base routes remain mapped', () => {
    expect(ROUTE_MODULE_MAP['/conformite']).toBe('conformite');
    expect(ROUTE_MODULE_MAP['/conformite/aper']).toBe('conformite');
    expect(ROUTE_MODULE_MAP['/conformite/tertiaire']).toBe('conformite');
  });
});
