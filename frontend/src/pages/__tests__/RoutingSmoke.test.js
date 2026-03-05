/**
 * PROMEOS — Routing + audit guard tests
 * Vérifie que:
 *   1. NavRegistry pointe chaque route vers le bon composant (source of truth)
 *   2. Les labels clés du menu sont en français avec accents
 *   3. /cockpit-2min n'est plus une destination navigable du menu
 *   4. normalizeDashboardModel (CommandCenter) est importable (module non cassé)
 *   5. Le marquage de route est canonique (un seul chemin vers chaque page primaire)
 *   6. (Audit) Aucune route nav ne pointe vers un chemin cassé
 *   7. (Audit) Zéro label anglais résiduel dans les routes principales
 *
 * Ces tests rendent le crash "FileText is not defined" ou un import manquant
 * impossible à passer silencieusement.
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

// ── NavRegistry: routes canoniques ───────────────────────────────────────────

describe('NavRegistry — routes canoniques', () => {
  it('"Tableau de bord" pointe vers "/"', () => {
    const item = ALL_NAV_ITEMS.find((i) => i.label === 'Tableau de bord');
    expect(item).toBeDefined();
    expect(item.to).toBe('/');
  });

  it('"Vue exécutive" (avec accent) pointe vers "/cockpit"', () => {
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

// ── Labels français avec accents ─────────────────────────────────────────────

describe('NavRegistry — labels FR avec accents', () => {
  it('label "Vue exécutive" contient l\'accent sur le "e"', () => {
    const item = ALL_NAV_ITEMS.find((i) => i.to === '/cockpit');
    expect(item?.label).toBe('Vue exécutive');
    expect(item?.label).not.toBe('Vue executive');
  });

  it('module Marché a l\'accent sur le "e"', () => {
    const mod = NAV_MODULES.find((m) => m.key === 'marche');
    expect(mod?.label).toBe('Marché');
  });

  it('"Achats d\'énergie" via longLabel a les accents', () => {
    const item = ALL_NAV_ITEMS.find((i) => i.to === '/achat-energie');
    expect(item?.longLabel).toBe("Achats d'énergie & scénarios");
  });
});

// ── CommandCenter module health check ────────────────────────────────────────

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

// ── Unicité des routes primaires dans le menu ─────────────────────────────────

describe('NavRegistry — pas de doublons de routes primaires', () => {
  it("chaque route n'apparaît qu'une fois dans ALL_NAV_ITEMS", () => {
    const routes = ALL_NAV_ITEMS.map((i) => i.to);
    const unique = new Set(routes);
    expect(routes.length).toBe(unique.size);
  });
});

// ── Audit guard: zéro label anglais résiduel ──────────────────────────────────

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

// ── Audit guard: toutes les routes nav commencent par / ───────────────────────

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
      const found = mapRoutes.some((r) => item.to === r || item.to.startsWith(r + '/'));
      expect(found).toBe(true);
    }
  });
});
