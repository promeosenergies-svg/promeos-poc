// @vitest-environment jsdom
/**
 * PROMEOS — Tests Site360 onglets (Sprint Site360 P0 routes mortes).
 *
 * Garde-fou statique contre la régression de la registry Site360 :
 * - aucun jargon anglais (« Analytics », « TODO », « Coming soon ») ;
 * - aucun lien `#` ou route 404 ;
 * - chaque tab visible expose un panel ou redirige vers une route
 *   canonique présente dans App.jsx.
 */
import { describe, expect, it } from 'vitest';
import {
  SITE360_TABS,
  SITE360_CANONICAL_ROUTES,
  getEnabledSite360Tabs,
  findSite360Tab,
} from '../pages/site360/site360TabsRegistry';

const { readFileSync } = require('fs');
const { resolve } = require('path');

const FORBIDDEN_LABELS = [
  'Analytics',
  'TODO',
  'Coming soon',
  'À venir',
  'Lorem',
  'undefined',
  'NaN',
  '[object Object]',
];

describe('Site360 — registry canonique des onglets', () => {
  it('expose les 9 onglets attendus', () => {
    expect(SITE360_TABS.length).toBe(9);
    const ids = SITE360_TABS.map((t) => t.id);
    expect(ids).toEqual([
      'resume',
      'conso',
      'analytics',
      'factures',
      'reconciliation',
      'conformite',
      'actions',
      'puissance',
      'usages',
    ]);
  });

  it('chaque tab possède le contrat complet (id/label/status/renderMode/testId)', () => {
    for (const tab of SITE360_TABS) {
      expect(typeof tab.id).toBe('string');
      expect(tab.id.length).toBeGreaterThan(0);
      expect(typeof tab.label).toBe('string');
      expect(tab.label.length).toBeGreaterThan(0);
      expect(['enabled', 'hidden']).toContain(tab.status);
      expect(['panel', 'redirect', 'link']).toContain(tab.renderMode);
      expect(tab.testId).toMatch(/^site360-tab-/);
    }
  });

  it('aucun label de tab ne contient un jargon interdit', () => {
    for (const tab of SITE360_TABS) {
      for (const forbidden of FORBIDDEN_LABELS) {
        expect(tab.label).not.toContain(forbidden);
      }
    }
  });

  it('le tab « analytics » porte le libellé FR métier « Analyse énergétique »', () => {
    const t = findSite360Tab('analytics');
    expect(t).toBeTruthy();
    expect(t.label).toBe('Analyse énergétique');
  });

  it('chaque tab visible expose un emptyState FR métier (pas vide)', () => {
    for (const tab of getEnabledSite360Tabs()) {
      expect(tab.emptyState).toBeTruthy();
      expect(typeof tab.emptyState).toBe('string');
      expect(tab.emptyState.length).toBeGreaterThan(10);
    }
  });

  it('un tab de type redirect/link DOIT déclarer un targetRoute (jamais null)', () => {
    for (const tab of SITE360_TABS) {
      if (tab.renderMode === 'redirect' || tab.renderMode === 'link') {
        expect(tab.targetRoute).toBeTruthy();
        expect(tab.targetRoute).not.toBe('#');
        expect(tab.targetRoute.startsWith('/')).toBe(true);
      }
    }
  });
});

describe('Site360 — routes canoniques', () => {
  it('aucune route canonique ne vaut `#`, `undefined`, ou vide', () => {
    for (const [key, route] of Object.entries(SITE360_CANONICAL_ROUTES)) {
      expect(route, `route ${key}`).toBeTruthy();
      expect(route).not.toBe('#');
      expect(route).not.toContain('undefined');
      expect(route.startsWith('/')).toBe(true);
    }
  });

  it('toutes les routes canoniques sont déclarées dans App.jsx (zéro 404)', () => {
    const appSrc = readFileSync(resolve(__dirname, '../App.jsx'), 'utf8');
    for (const [key, route] of Object.entries(SITE360_CANONICAL_ROUTES)) {
      // App.jsx déclare les routes via path="..." parfois nested.
      // On vérifie que CHAQUE segment de la route apparaît comme
      // path="segment" (avec ou sans slash initial). Cela couvre les
      // routes nested (ex. /consommations → courbe).
      const segments = route.split('/').filter(Boolean);
      for (const segment of segments) {
        const re = new RegExp(
          `path=["'](?:/)?${segment.replace(/[/.*+?^${}()|[\]\\]/g, '\\$&')}(?:[/"' ?:])`
        );
        expect(
          re.test(appSrc),
          `segment « ${segment} » de la route canonique « ${key} » (${route}) doit exister dans App.jsx`
        ).toBe(true);
      }
    }
  });

  it('ne contient PAS la route morte `/achat-assistant`', () => {
    // Smoke : la route fantôme historique doit être bannie de la registry
    expect(SITE360_CANONICAL_ROUTES).not.toHaveProperty('achatAssistant');
    expect(Object.values(SITE360_CANONICAL_ROUTES)).not.toContain('/achat-assistant');
  });
});

describe('Site360.jsx — fichier composant', () => {
  it('importe la registry canonique', () => {
    const src = readFileSync(resolve(__dirname, '../pages/Site360.jsx'), 'utf8');
    expect(src).toContain("from './site360/site360TabsRegistry'");
    expect(src).toContain('getEnabledSite360Tabs');
  });

  it("n'affiche plus le label jargon « Analytics » (utilise registry)", () => {
    const src = readFileSync(resolve(__dirname, '../pages/Site360.jsx'), 'utf8');
    // Le mot Analytics ne doit plus apparaître comme literal de label
    // (les usages internes id='analytics' / TabAnalytics / commentaire OK)
    expect(src).not.toMatch(/label:\s*['"]Analytics['"]/);
  });

  it('ne contient plus de navigation vers la route morte `/achat-assistant`', () => {
    const src = readFileSync(resolve(__dirname, '../pages/Site360.jsx'), 'utf8');
    expect(src).not.toContain('achat-assistant');
  });

  it("utilise l'accent correct « Évaluation RegOps » (pas « Evaluation »)", () => {
    const src = readFileSync(resolve(__dirname, '../pages/Site360.jsx'), 'utf8');
    expect(src).toContain('Évaluation RegOps');
    // L'ancien label sans accent ne doit plus être présent comme texte rendu
    expect(src).not.toMatch(/>\s*Evaluation RegOps\s*</);
  });
});

describe('Site360 — DoD onglet → contenu', () => {
  it.each(getEnabledSite360Tabs())(
    'tab « $label » ($id) a renderMode défini et emptyState FR',
    (tab) => {
      expect(['panel', 'redirect', 'link']).toContain(tab.renderMode);
      expect(tab.emptyState).toBeTruthy();
      // FR métier : pas d'anglais détecté dans l'emptyState
      expect(tab.emptyState).not.toMatch(/\b(coming soon|todo|under construction|click here)\b/i);
    }
  );
});
