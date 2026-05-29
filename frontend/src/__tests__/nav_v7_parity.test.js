/**
 * PROMEOS Nav V7 — Tests de parité & garde-fous
 *
 * 1. Parité routes: chaque item de NAV_SECTIONS doit avoir une <Route> dans App.jsx
 * 2. Source guard: labels interdits absents de NavRegistry
 * 3. Structure: 5 modules normal + admin expert, 13 items normal, 17 items expert
 */
import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { describe, it, expect } from 'vitest';
import {
  NAV_MODULES,
  NAV_SECTIONS,
  ALL_NAV_ITEMS,
  ROUTE_MODULE_MAP,
  getVisibleItems,
} from '../layout/NavRegistry';

const __dirname = dirname(fileURLToPath(import.meta.url));
const appJsxPath = resolve(__dirname, '../App.jsx');
const appSource = readFileSync(appJsxPath, 'utf-8');

describe('Nav V7 — Parité routes ↔ App.jsx', () => {
  it('each nav item base path has a <Route> in App.jsx', () => {
    const missing = [];
    for (const item of ALL_NAV_ITEMS) {
      const basePath = item.to.split('?')[0].split('#')[0];
      // Allow for redirects (Navigate to=...) too
      const escaped = basePath.replace(/\//g, '\\/');
      const reExact = new RegExp(`path=["']${escaped}["']`);
      const reSub = new RegExp(`path=["']${escaped}(?:/|["'])`);
      if (!reExact.test(appSource) && !reSub.test(appSource)) {
        // Check if parent segment is present (for nested routes)
        const parent = basePath.split('/').slice(0, 2).join('/');
        const reParent = new RegExp(`path=["']${parent.replace(/\//g, '\\/')}["']`);
        if (!reParent.test(appSource)) {
          missing.push(basePath);
        }
      }
    }
    expect(missing).toEqual([]);
  });

  it('ROUTE_MODULE_MAP has no orphan routes (all base paths exist in map)', () => {
    for (const item of ALL_NAV_ITEMS) {
      const basePath = item.to.split('?')[0].split('#')[0];
      expect(ROUTE_MODULE_MAP).toHaveProperty(basePath);
    }
  });
});

describe('Nav V7 — Source guard (labels interdits)', () => {
  it('no "Actions & Suivi" label in nav', () => {
    const flat = JSON.stringify(NAV_SECTIONS);
    expect(flat).not.toContain('Actions & Suivi');
  });

  it('no "Notifications" label in nav items', () => {
    const labels = ALL_NAV_ITEMS.map((i) => i.label);
    expect(labels).not.toContain('Notifications');
  });

  it("no deprecated labels: BACS (GTB/GTC), Loi APER (ENR), Stratégies d'achat", () => {
    const labels = ALL_NAV_ITEMS.map((i) => i.label);
    expect(labels).not.toContain('BACS (GTB/GTC)');
    expect(labels).not.toContain('Loi APER (ENR)');
    expect(labels).not.toContain("Stratégies d'achat");
  });

  it('/actions and /notifications are NOT base paths in nav items', () => {
    const basePaths = ALL_NAV_ITEMS.map((i) => i.to.split('?')[0].split('#')[0]);
    expect(basePaths).not.toContain('/actions');
    expect(basePaths).not.toContain('/notifications');
  });
});

describe('Nav V7 — Structure', () => {
  // Phase 1.D — P0.1 : Bill Intelligence promu module rail (compteur passe
  // de 5 → 6 normal). Ordre rail final cible Sol v1.1 sera fixé par P0.5.
  it('6 modules visible in normal mode (Phase 1.D — Facturation promue)', () => {
    const normalModules = NAV_MODULES.filter((m) => !m.expertOnly);
    expect(normalModules).toHaveLength(6);
    expect(normalModules.map((m) => m.key)).toEqual([
      'cockpit',
      'conformite',
      'energie',
      'patrimoine',
      'achat',
      'facturation',
    ]);
  });

  it('admin module is the only expertOnly module', () => {
    const expertModules = NAV_MODULES.filter((m) => m.expertOnly);
    expect(expertModules).toHaveLength(1);
    expect(expertModules[0].key).toBe('admin');
  });

  // Phase 17.bis.B : Flex Intelligence ajouté module Énergie ;
  // Phase 17.bis.C : Décret Tertiaire / OPERAT promu module Conformité ;
  // Phase 1.C P0.3 : Centre d'action exposé en panel Accueil → 15 → 16 items.
  // Cleanup sidebar Conformité (2026-05-24, PR #300) : retrait des 2 sous-items
  // DT/APER (hub unique /conformite + chips internes) → 16 → 14 items.
  // Cleanup navigation pré-usage steering (2026-05-27, PR #314) : Flex
  // Intelligence déclassé en deep-link (sortie du rail visible) → 14 → 13 items.
  // → maintenance 2026-05-29 : test aligné sur la valeur effective post-#314.
  it('13 items visible in normal mode (post déclassement Flex Intelligence #314)', () => {
    const mainSections = NAV_SECTIONS.filter((s) => !s.expertOnly);
    const items = mainSections.flatMap((s) => getVisibleItems(s.items, false));
    expect(items).toHaveLength(13);
  });

  it('same count in expert mode (no expertOnly items left)', () => {
    const mainSections = NAV_SECTIONS.filter((s) => !s.expertOnly);
    const items = mainSections.flatMap((s) => getVisibleItems(s.items, true));
    expect(items).toHaveLength(13);
  });

  it('zero expertOnly items in main modules (tabs merged into parent pages)', () => {
    const expertItems = NAV_SECTIONS.filter((s) => !s.expertOnly).flatMap((s) =>
      s.items.filter((i) => i.expertOnly)
    );
    expect(expertItems).toHaveLength(0);
  });
});

describe('Nav V7 — Cibles de redirects résolues par le rail', () => {
  // Capture chaque <Route path="X" element={<Navigate to="Y" replace />} />.
  // On veut s'assurer que la cible Y est résolue par matchRouteToModule, sinon
  // un lien externe vers un ancien slug (/achats, /purchase, /contracts-radar…)
  // mène à une page valide MAIS le rail tombe sur le module par défaut (cockpit)
  // — ce qui crée un mismatch UX silencieux.
  const navigateRe =
    /path=["']([^"']+)["']\s*element=\{\s*<Navigate\s+to=["']([^"'?#]+)(?:[?#][^"']*)?["']\s+replace\s*\/?>/g;

  const redirects = [];
  let m;
  while ((m = navigateRe.exec(appSource)) !== null) {
    redirects.push({ from: m[1], to: m[2] });
  }

  it('au moins 10 redirects détectés (sanity check du parser)', () => {
    // Phase 3.bis.a : redirects factorisés dans routes/legacyRedirects.js
    const redirectsSrc = readFileSync(
      resolve(__dirname, '..', 'routes', 'legacyRedirects.js'),
      'utf8'
    );
    const matches = redirectsSrc.match(/\[['"]\/[^'"]+['"],\s*['"]\/[^'"]+['"]\]/g);
    expect(matches).toBeTruthy();
    expect(matches.length).toBeGreaterThanOrEqual(10);
  });

  it('chaque cible de redirect est mappée à un module dans ROUTE_MODULE_MAP', () => {
    // Le matcher fait du préfixe-fallback, donc une cible nested type
    // /consommations/portfolio est résolue si /consommations est dans la map.
    const isResolved = (target) => {
      if (ROUTE_MODULE_MAP[target]) return true;
      // Préfixe-fallback : on cherche le plus long préfixe sans `:`
      const candidates = Object.keys(ROUTE_MODULE_MAP)
        .filter((k) => !k.includes(':'))
        .sort((a, b) => b.length - a.length);
      return candidates.some((p) => target === p || target.startsWith(p + '/'));
    };
    const orphans = redirects.filter((r) => !isResolved(r.to));
    expect(orphans).toEqual([]);
  });
});

describe('Nav V7 — ActionCenterSlideOver intégré', () => {
  const appShellPath = resolve(__dirname, '../layout/AppShell.jsx');
  const appShellSource = readFileSync(appShellPath, 'utf-8');

  it('AppShell imports ActionCenterSlideOver', () => {
    expect(appShellSource).toContain('ActionCenterSlideOver');
  });

  it('AppShell has bell button for action center', () => {
    expect(appShellSource).toContain('Bell');
    expect(appShellSource).toMatch(/aria-label=["']Centre d'actions["']/);
  });

  it('AppShell handles backward compat ?actionCenter=open', () => {
    expect(appShellSource).toContain('actionCenter');
  });

  it('AppShell preserves other query params when stripping actionCenter/tab', () => {
    // Guard against regression: navigate(location.pathname, …) would drop
    // coexisting params like ?regulation=dt alongside ?actionCenter=open.
    expect(appShellSource).toMatch(/params\.delete\(['"]actionCenter['"]\)/);
    expect(appShellSource).toMatch(/params\.delete\(['"]tab['"]\)/);
    expect(appShellSource).not.toMatch(
      /navigate\(\s*location\.pathname\s*,\s*\{\s*replace:\s*true\s*\}\s*\)/
    );
  });
});
