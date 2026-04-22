/**
 * Test invariance structurelle — PANEL_DEEP_LINKS_BY_ROUTE (GATE 2 TDD).
 *
 * Protège la SSOT NAV_SECTIONS contre la re-divergence observée pré-fix
 * f679f14c (14 entrées PANEL_SECTIONS_BY_ROUTE avec sections concurrentes,
 * labels divergents, items cachés ré-exposés).
 *
 * Ce test est créé AVANT le remplissage de PANEL_DEEP_LINKS_BY_ROUTE (TDD
 * strict). Initialement trivialement vert (constant = {}). À mesure que des
 * deep-links sont ajoutés en GATE 4 Vague 1, les 4 assertions restent vertes
 * par design.
 *
 * 4 règles enforcées :
 *   1. Chaque deep-link contient un query param (?...=) OU un sous-path qui
 *      n'est PAS un item top-level NAV_SECTIONS.
 *   2. Aucun deep-link ne duplique un href (to) d'item top-level NAV_SECTIONS.
 *   3. Aucun deep-link ne ré-expose un item masqué volontairement
 *      (/actions, /notifications redirigés vers Centre d'actions header).
 *   4. Aucun label deep-link ne duplique un label top-level NAV_SECTIONS
 *      (risque redrift SSOT).
 *   + bonus : chaque route key PANEL_DEEP_LINKS_BY_ROUTE résout via
 *     matchRouteToModule à un module NAV_MODULES valide (anti-typo).
 *
 * Schéma deep-link attendu : `{ href: string, label: string, hint?: string }`
 * (vs NAV_SECTIONS qui utilise `{ to, label, desc, icon, ... }`).
 */
import { describe, it, expect } from 'vitest';
import {
  NAV_SECTIONS,
  PANEL_DEEP_LINKS_BY_ROUTE,
  matchRouteToModule,
} from '../NavRegistry';

const HIDDEN_ITEMS = ['/actions', '/notifications'];

describe('PANEL_DEEP_LINKS_BY_ROUTE — invariance structurelle (GATE 2)', () => {
  // Pré-calculs issus de NAV_SECTIONS (SSOT main) — property name = 'to'
  const topLevelPaths = new Set(
    NAV_SECTIONS.flatMap((s) => (s.items || []).map((i) => i.to)),
  );
  const topLevelLabels = new Set(
    NAV_SECTIONS.flatMap((s) => (s.items || []).map((i) => i.label)),
  );

  it('règle 1 : chaque deep-link est query-param OU sous-path (pas un item top-level)', () => {
    const violations = [];
    for (const [route, deeplinks] of Object.entries(PANEL_DEEP_LINKS_BY_ROUTE)) {
      for (const link of deeplinks) {
        const isQueryParam = /\?[a-z_]+=/i.test(link.href);
        const isSubPath = /^\/[a-z-]+\/[a-z-]+/i.test(link.href);
        if (!isQueryParam && !isSubPath) {
          violations.push(
            `Route "${route}" link "${link.label}" → href "${link.href}" n'est ni query-param ni sous-path (interdit)`,
          );
        }
      }
    }
    expect(violations, violations.join('\n')).toEqual([]);
  });

  it('règle 2 : aucun deep-link ne duplique un href top-level NAV_SECTIONS', () => {
    const violations = [];
    for (const [route, deeplinks] of Object.entries(PANEL_DEEP_LINKS_BY_ROUTE)) {
      for (const link of deeplinks) {
        if (topLevelPaths.has(link.href)) {
          violations.push(
            `Route "${route}" link "${link.label}" → href "${link.href}" duplique un item top-level NAV_SECTIONS (divergence SSOT)`,
          );
        }
      }
    }
    expect(violations, violations.join('\n')).toEqual([]);
  });

  it('règle 3 : aucun deep-link ne ré-expose /actions ou /notifications (masqués volontairement)', () => {
    const violations = [];
    for (const [route, deeplinks] of Object.entries(PANEL_DEEP_LINKS_BY_ROUTE)) {
      for (const link of deeplinks) {
        for (const hidden of HIDDEN_ITEMS) {
          if (link.href === hidden || link.href.startsWith(`${hidden}?`)) {
            violations.push(
              `Route "${route}" link "${link.label}" ré-expose item masqué "${hidden}"`,
            );
          }
        }
      }
    }
    expect(violations, violations.join('\n')).toEqual([]);
  });

  it('règle 4 : aucun label deep-link ne duplique un label top-level NAV_SECTIONS', () => {
    const violations = [];
    for (const [route, deeplinks] of Object.entries(PANEL_DEEP_LINKS_BY_ROUTE)) {
      for (const link of deeplinks) {
        if (topLevelLabels.has(link.label)) {
          violations.push(
            `Route "${route}" label "${link.label}" duplique un label top-level NAV_SECTIONS (risque redrift SSOT)`,
          );
        }
      }
    }
    expect(violations, violations.join('\n')).toEqual([]);
  });

  it('bonus : chaque route key PANEL_DEEP_LINKS_BY_ROUTE résout à un module NAV_MODULES (anti-typo)', () => {
    const violations = [];
    for (const route of Object.keys(PANEL_DEEP_LINKS_BY_ROUTE)) {
      const { pattern } = matchRouteToModule(route);
      // pattern === null signifie fallback au default 'cockpit' (pas de match
      // explicite dans ROUTE_MODULE_MAP) — très probablement une typo.
      if (pattern === null) {
        violations.push(
          `Route "${route}" ne résout pas via ROUTE_MODULE_MAP (typo ou route absente)`,
        );
      }
    }
    expect(violations, violations.join('\n')).toEqual([]);
  });

  it('schéma : chaque deep-link a {href, label} (hint optionnel)', () => {
    const violations = [];
    for (const [route, deeplinks] of Object.entries(PANEL_DEEP_LINKS_BY_ROUTE)) {
      if (!Array.isArray(deeplinks)) {
        violations.push(`Route "${route}" valeur doit être un Array (pas ${typeof deeplinks})`);
        continue;
      }
      for (const link of deeplinks) {
        if (typeof link.href !== 'string' || !link.href.startsWith('/')) {
          violations.push(`Route "${route}" link ${JSON.stringify(link)} : href invalide`);
        }
        if (typeof link.label !== 'string' || link.label.length === 0) {
          violations.push(`Route "${route}" link ${JSON.stringify(link)} : label manquant ou vide`);
        }
        if (link.hint != null && typeof link.hint !== 'string') {
          violations.push(`Route "${route}" link ${JSON.stringify(link)} : hint doit être string ou absent`);
        }
      }
    }
    expect(violations, violations.join('\n')).toEqual([]);
  });
});
