/**
 * PROMEOS — Routing + audit guard tests (V7)
 * Vérifie que NavRegistry pointe chaque route vers le bon module.
 */
import { describe, it, expect } from 'vitest';
import {
  NAV_SECTIONS,
  NAV_MODULES,
  ROUTE_MODULE_MAP,
  resolveModule,
  ALL_NAV_ITEMS,
} from '../../layout/NavRegistry';
import { normalizeDashboardModel } from '../CommandCenter';

describe('NavRegistry V7 — routes canoniques', () => {
  it('"Vue exécutive" pointe vers "/cockpit"', () => {
    const item = ALL_NAV_ITEMS.find((i) => i.label === 'Vue exécutive');
    expect(item).toBeDefined();
    expect(item.to).toBe('/cockpit');
  });

  it("/cockpit-2min n'est pas une destination de menu (canonique = /cockpit)", () => {
    const item = ALL_NAV_ITEMS.find((i) => i.to === '/cockpit-2min');
    expect(item).toBeUndefined();
  });

  it('/ est dans le module cockpit', () => {
    expect(ROUTE_MODULE_MAP['/']).toBe('cockpit');
  });

  it('/cockpit est dans le module cockpit', () => {
    expect(ROUTE_MODULE_MAP['/cockpit']).toBe('cockpit');
  });

  it('resolveModule("/") retourne "cockpit"', () => {
    expect(resolveModule('/')).toBe('cockpit');
  });

  it('resolveModule("/cockpit") retourne "cockpit"', () => {
    expect(resolveModule('/cockpit')).toBe('cockpit');
  });
});

describe('NavRegistry V7 — labels FR avec accents', () => {
  it('label "Vue exécutive" pour /cockpit', () => {
    const item = ALL_NAV_ITEMS.find((i) => i.to === '/cockpit');
    expect(item?.label).toBe('Vue exécutive');
  });

  it('module Achat has correct label', () => {
    const mod = NAV_MODULES.find((m) => m.key === 'achat');
    expect(mod?.label).toBe('Achat');
  });

  it("'Scénarios d'achat' is in achat section", () => {
    const item = ALL_NAV_ITEMS.find((i) => i.label === "Scénarios d'achat");
    expect(item).toBeDefined();
    expect(item?.module).toBe('achat');
  });
});

describe('CommandCenter — exports fonctionnels', () => {
  it('normalizeDashboardModel est une fonction', () => {
    expect(typeof normalizeDashboardModel).toBe('function');
  });

  it('normalizeDashboardModel retourne isAllClear=true quand tout est ok', () => {
    const kpis = { pctConf: 100, nonConformes: 0, aRisque: 0, risque: 0 };
    const { isAllClear } = normalizeDashboardModel({ kpis, topActions: [], alertsCount: 0 });
    expect(isAllClear).toBe(true);
  });

  it('normalizeDashboardModel retourne isAllClear=false si alertsCount > 0', () => {
    const kpis = { pctConf: 100, nonConformes: 0, aRisque: 0, risque: 0 };
    const { isAllClear } = normalizeDashboardModel({ kpis, topActions: [], alertsCount: 1 });
    expect(isAllClear).toBe(false);
  });
});

describe('NavRegistry V7 — pas de doublons de routes primaires', () => {
  it("chaque route n'apparaît qu'une fois dans ALL_NAV_ITEMS", () => {
    const routes = ALL_NAV_ITEMS.map((i) => i.to);
    const unique = new Set(routes);
    expect(routes.length).toBe(unique.size);
  });
});

const ENGLISH_BLACKLIST = [
  'Dashboard',
  'Assignments',
  'Roles & Permissions',
  'Settings',
  'Loading',
  'Submit',
  'Save',
  'Delete',
  'Cancel',
];

describe('Audit guard — zéro anglais dans le menu', () => {
  it('aucun label de nav ne contient de mot anglais blacklisté', () => {
    for (const item of ALL_NAV_ITEMS) {
      for (const word of ENGLISH_BLACKLIST) {
        expect(item.label).not.toContain(word);
      }
    }
  });

  it('aucune section de nav ne contient de mot anglais blacklisté', () => {
    for (const section of NAV_SECTIONS) {
      for (const word of ENGLISH_BLACKLIST) {
        expect(section.label).not.toContain(word);
      }
    }
  });
});

describe('Audit guard — routes valides', () => {
  it('chaque route nav commence par /', () => {
    for (const item of ALL_NAV_ITEMS) {
      expect(item.to).toMatch(/^\//);
    }
  });

  it('aucune route nav ne pointe vers /consumption-explorer (ancien chemin)', () => {
    for (const item of ALL_NAV_ITEMS) {
      expect(item.to).not.toBe('/consumption-explorer');
    }
  });

  it('ROUTE_MODULE_MAP couvre toutes les routes du menu', () => {
    const mapRoutes = Object.keys(ROUTE_MODULE_MAP);
    for (const item of ALL_NAV_ITEMS) {
      const basePath = item.to.split('?')[0].split('#')[0];
      const found = mapRoutes.some((r) => basePath === r || basePath.startsWith(r + '/'));
      expect(found).toBe(true);
    }
  });
});
