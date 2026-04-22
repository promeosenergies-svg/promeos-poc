/**
 * Test présence Vague 1 — PANEL_DEEP_LINKS_BY_ROUTE (GATE 4).
 *
 * Lock les 8 deep-links livrés en Vague 1 du sprint nav-deep-links :
 *   - /anomalies × 3 frameworks (DECRET_TERTIAIRE, FACTURATION, BACS)
 *   - /renouvellements × 3 horizons (90j, 180j, 365j)
 *   - /conformite/aper × 2 filtres (parking, toiture)
 *
 * Complémentaire du test invariance (__tests__/panel_deep_links_invariant.test.js)
 * qui enforce les règles structurelles. Ce test-ci fige le contenu concret.
 */
import { describe, it, expect } from 'vitest';
import { PANEL_DEEP_LINKS_BY_ROUTE } from '../NavRegistry';

describe('PANEL_DEEP_LINKS_BY_ROUTE — Vague 1 présence (GATE 4)', () => {
  it('/anomalies expose 3 filtres framework (all, DT, FACT, BACS)', () => {
    const links = PANEL_DEEP_LINKS_BY_ROUTE['/anomalies'];
    expect(links).toBeDefined();
    expect(links).toHaveLength(3);
    expect(links.map((l) => l.href)).toEqual([
      '/anomalies?fw=DECRET_TERTIAIRE',
      '/anomalies?fw=FACTURATION',
      '/anomalies?fw=BACS',
    ]);
  });

  it('/renouvellements expose 3 horizons (90/180/365)', () => {
    const links = PANEL_DEEP_LINKS_BY_ROUTE['/renouvellements'];
    expect(links).toBeDefined();
    expect(links).toHaveLength(3);
    expect(links.map((l) => l.href)).toEqual([
      '/renouvellements?horizon=90',
      '/renouvellements?horizon=180',
      '/renouvellements?horizon=365',
    ]);
  });

  it('/conformite/aper expose 2 filtres (parking, toiture)', () => {
    const links = PANEL_DEEP_LINKS_BY_ROUTE['/conformite/aper'];
    expect(links).toBeDefined();
    expect(links).toHaveLength(2);
    expect(links.map((l) => l.href)).toEqual([
      '/conformite/aper?filter=parking',
      '/conformite/aper?filter=toiture',
    ]);
  });

  it('Vague 1 total = 8 deep-links sur 3 routes', () => {
    const total = Object.values(PANEL_DEEP_LINKS_BY_ROUTE).reduce(
      (sum, links) => sum + links.length,
      0,
    );
    expect(total).toBe(8);
    expect(Object.keys(PANEL_DEEP_LINKS_BY_ROUTE)).toHaveLength(3);
  });

  it('chaque deep-link Vague 1 a label + hint non-vides', () => {
    for (const [route, links] of Object.entries(PANEL_DEEP_LINKS_BY_ROUTE)) {
      for (const link of links) {
        expect(link.label, `${route}:${link.href} label`).toBeTruthy();
        expect(link.hint, `${route}:${link.href} hint`).toBeTruthy();
      }
    }
  });
});
