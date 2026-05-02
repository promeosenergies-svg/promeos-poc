/**
 * V7 Navigation Refactor — Guard-rail tests
 * Remplace V114 obsolète. Vérifie la structure V7 :
 *  - Cockpit: 3 items (Synthèse stratégique + Briefing du jour + Centre
 *    d'action) — libellés canoniques Sol §11.3 (Phase 1.A P0.2) + Centre
 *    d'action exposé en panel Accueil (Phase 1.C P0.3)
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
  // / + /cockpit qui exposait une inversion.
  //
  // Phase 1.A — P0.2 (audit navigation_audit_20260501.md, 2026-05-01) :
  // hard-cut renommage des libellés panel Cockpit vers les libellés canoniques
  // Sol §11.3 — "Vue exécutive" → "Synthèse stratégique", "Tableau de bord"
  // → "Briefing du jour". Anciens libellés conservés en `keywords`
  // (rétro-compat ⌘K).
  //
  // Phase 1.C — P0.3 ordre révisé : Briefing du jour → Synthèse stratégique
  // → Centre d'action. Cohérent avec persona dominant Energy Manager (Marc),
  // entrée par le briefing opérationnel 30 s puis montée vers la synthèse 3 min.
  // Override l'ordre Phase 13.D (Synthèse premier pour démo CFO) — la démo
  // CFO reste servie par le redirect /cockpit → /cockpit/strategique.
  it("Cockpit has exactly 3 items (Briefing + Synthèse + Centre d'action)", () => {
    // Phase 1.C — P0.3 (audit navigation_audit_20260501.md §4.4 + Q2) :
    // Centre d'action exposé en 3e position du panel Accueil, complémentaire
    // de la cloche header AppShell + raccourci Ctrl+Shift+L. Les 3 surfaces
    // sont contextes d'usage distincts (cf. doctrine §6.2 anti-pattern
    // "chemins multiples" — exception justifiée).
    const cockpit = NAV_SECTIONS.find((s) => s.key === 'cockpit');
    expect(cockpit.items).toHaveLength(3);
    expect(cockpit.items.map((i) => i.to)).toEqual([
      '/cockpit/jour',
      '/cockpit/strategique',
      '/action-center',
    ]);
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
