/**
 * V7 Navigation Refactor — Guard-rail tests
 * Remplace V114 obsolète. Vérifie la structure V7 :
 *  - Cockpit: 2 items (Tableau de bord + Vue exécutive)
 *  - Conformité: module autonome 4-5 items
 *  - Achat visible en normal
 *  - /actions et /notifications retirés de la nav (déplacés vers Centre d'actions)
 */
import { describe, it, expect } from 'vitest';
import {
  NAV_SECTIONS,
  QUICK_ACTIONS,
  ALL_NAV_ITEMS,
  ROUTE_MODULE_MAP,
} from '../../layout/NavRegistry';

describe('V7 Nav Refactor guard-rails', () => {
  // Refonte WOW Cockpit dual sol2 (29/04/2026) : routes canoniques §11.3 doctrine
  // /cockpit/jour (Briefing du jour = Pilotage 30s) + /cockpit/strategique
  // (Synthèse stratégique = Décision 3min) — au lieu de l'ancienne paire
  // / + /cockpit qui exposait une inversion (cf. issue sidebar Tableau de bord).
  // Phase 13.D : ordre inversé pour démo CFO/investisseur — Vue exécutive
  // (Synthèse stratégique 3min) en premier, Tableau de bord (Briefing
  // Energy Manager 30s) en second. Cohérent avec audience démo principale.
  it('Cockpit has exactly 2 items (Vue exécutive + Tableau de bord)', () => {
    const cockpit = NAV_SECTIONS.find((s) => s.key === 'cockpit');
    expect(cockpit.items).toHaveLength(2);
    expect(cockpit.items.map((i) => i.to)).toEqual(['/cockpit/strategique', '/cockpit/jour']);
  });

  it('Patrimoine has 3 items (Sites + Contrats + Facturation expert)', () => {
    const patrimoine = NAV_SECTIONS.find((s) => s.key === 'patrimoine');
    expect(patrimoine.items).toHaveLength(3);
    expect(patrimoine.items.map((i) => i.to)).toEqual(['/patrimoine', '/contrats', '/bill-intel']);
  });

  it("/actions and /notifications are NOT in nav items (moved to Centre d'actions)", () => {
    const paths = ALL_NAV_ITEMS.map((i) => i.to.split('?')[0].split('#')[0]);
    expect(paths).not.toContain('/actions');
    expect(paths).not.toContain('/notifications');
  });

  it('/notifications is still mapped in ROUTE_MODULE_MAP (backward compat redirect)', () => {
    expect(ROUTE_MODULE_MAP['/notifications']).toBe('cockpit');
  });

  it('/actions is still mapped in ROUTE_MODULE_MAP (backward compat redirect)', () => {
    expect(ROUTE_MODULE_MAP['/actions']).toBe('cockpit');
  });

  it('Energie section does NOT contain payment-rules and portfolio-reconciliation', () => {
    const energie = NAV_SECTIONS.find((s) => s.key === 'energie');
    const routes = energie.items.map((i) => i.to);
    expect(routes).not.toContain('/payment-rules');
    expect(routes).not.toContain('/portfolio-reconciliation');
  });

  it('Admin-data section does NOT contain payment-rules or portfolio-reconciliation', () => {
    const adminData = NAV_SECTIONS.find((s) => s.key === 'admin-data');
    expect(adminData.label).toBe('Données');
    const routes = adminData.items.map((i) => i.to);
    expect(routes).not.toContain('/payment-rules');
    expect(routes).not.toContain('/portfolio-reconciliation');
  });

  it('QUICK_ACTIONS has 15 entries (14 base + 1 sirene V118)', () => {
    expect(QUICK_ACTIONS).toHaveLength(15);
  });

  it('/import is visible in admin-data', () => {
    const adminData = NAV_SECTIONS.find((s) => s.key === 'admin-data');
    const importItem = adminData.items.find((i) => i.to === '/import');
    expect(importItem).toBeDefined();
    expect(importItem.hidden).toBeFalsy();
  });

  it('no English labels in nav items', () => {
    const blacklist = ['Center', 'Dashboard', 'Home', 'Knowledge Base', 'Settings'];
    for (const item of ALL_NAV_ITEMS) {
      for (const word of blacklist) {
        expect(item.label.toLowerCase()).not.toContain(word.toLowerCase());
      }
    }
  });
});
