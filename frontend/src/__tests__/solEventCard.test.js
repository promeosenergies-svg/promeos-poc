/**
 * Sprint 2 Vague C ét12c — SolEventCard natif §10.
 *
 * Tests source-guard (convention projet) : valide que le composant expose
 * la pile §10 complète (severity / source.system / source.confidence /
 * source.freshness_status / action.owner_role / impact.mitigation) — résout
 * compromis Marie audit Vague C ét11.
 *
 * Pas de RTL ici (cf solBriefingSection.test.js convention) — on lit le
 * source et vérifie la présence des hooks d'intégration. Les tests RTL
 * (rendu DOM réel) seront ajoutés Vague D si besoin.
 */

import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

const SRC = join(__dirname, '..');
const readSrc = (rel) => readFileSync(join(SRC, rel), 'utf-8');

// ── A. SolEventCard — fichier + structure ───────────────────────────

describe('A. SolEventCard — structure', () => {
  it('le fichier existe au bon emplacement', () => {
    expect(existsSync(join(SRC, 'ui/sol/SolEventCard.jsx'))).toBe(true);
  });

  const src = readSrc('ui/sol/SolEventCard.jsx');

  it('exporte un composant React par défaut', () => {
    expect(src).toMatch(/export default function SolEventCard/);
  });

  it('exporte aussi SolEventStream (wrapper grille top N)', () => {
    expect(src).toMatch(/export function SolEventStream/);
  });

  it('importe le validator isValidEvent depuis eventTypes.js (SoT mirror JS)', () => {
    expect(src).toMatch(
      /import\s*{[^}]*isValidEvent[^}]*}\s*from\s*'\.\.\/\.\.\/domain\/events\/eventTypes'/
    );
  });

  it('valide event via isValidEvent et rend null si invalide (garde-fou §6 P13)', () => {
    expect(src).toMatch(/isValidEvent\(event\)/);
    expect(src).toMatch(/if \(!isValid\) return null/);
  });
});

// ── B. SolEventCard — exposition pile §10 (Marie unblock visuel) ────

describe('B. SolEventCard — pile doctrine §10 affichée', () => {
  const src = readSrc('ui/sol/SolEventCard.jsx');

  it('expose 4 niveaux severity natifs (info/watch/warning/critical)', () => {
    expect(src).toMatch(/critical:\s*{/);
    expect(src).toMatch(/warning:\s*{/);
    expect(src).toMatch(/watch:\s*{/);
    expect(src).toMatch(/info:\s*{/);
  });

  it('affiche source.system (badge ShieldCheck)', () => {
    expect(src).toMatch(/event\.source\.system/);
    expect(src).toMatch(/ShieldCheck/);
  });

  it('affiche source.confidence avec libellé FR humain', () => {
    expect(src).toMatch(/CONFIDENCE_LABELS/);
    expect(src).toMatch(/fiabilité élevée/);
    expect(src).toMatch(/fiabilité moyenne/);
    expect(src).toMatch(/fiabilité limitée/);
  });

  it('affiche source.freshness_status (badge §7.2 statuts obligatoires)', () => {
    expect(src).toMatch(/FRESHNESS_LABELS/);
    expect(src).toMatch(/freshness_status/);
    expect(src).toMatch(/Estimé/);
    expect(src).toMatch(/Démo/);
  });

  it('affiche source.last_updated_at en relatif FR (« il y a X »)', () => {
    expect(src).toMatch(/formatRelativeTime/);
    expect(src).toMatch(/il y a/);
  });

  it('affiche action.owner_role (badge User « Suivi {role} »)', () => {
    expect(src).toMatch(/owner_role/);
    expect(src).toMatch(/Suivi/);
  });

  it('affiche action.label + route avec CTA cliquable', () => {
    expect(src).toMatch(/event\.action\.label/);
    expect(src).toMatch(/onNavigate\?\.\(route\)/);
  });

  it('affiche impact.mitigation si présent (CAPEX/payback/NPV — arbitrage CFO)', () => {
    expect(src).toMatch(/mitigation\?\.capex_eur/);
    expect(src).toMatch(/mitigation\?\.payback_months/);
    expect(src).toMatch(/mitigation\?\.npv_eur/);
    expect(src).toMatch(/CAPEX/);
    expect(src).toMatch(/payback/);
    expect(src).toMatch(/NPV/);
  });
});

// ── B-bis. ét12d corrections P0 audit (a11y + granularité site) ─────

describe('B-bis. SolEventCard — corrections P0 audit ét12d', () => {
  const src = readSrc('ui/sol/SolEventCard.jsx');

  it("utilise role='button' + tabIndex + onKeyDown au lieu de <button><article> (P0-1 a11y)", () => {
    // Doctrine §13 a11y : <button> ne peut pas contenir <article>.
    // Pattern correct : <article role="button" tabIndex={0} onKeyDown>.
    expect(src).toMatch(/role: 'button'/);
    expect(src).toMatch(/tabIndex: 0/);
    expect(src).toMatch(/onKeyDown/);
    // Anti-régression : pas de Wrapper dynamique button|article
    expect(src).not.toMatch(/Wrapper = route \? 'button'/);
  });

  it('expose aria-label agrégé (lecteurs écran, UX P0-C)', () => {
    expect(src).toMatch(/ariaLabelParts/);
    expect(src).toMatch(/aria-label=\{route \? ariaLabel/);
  });

  it('affiche linked_assets.site_ids count (granularité site EM P0-2)', () => {
    expect(src).toMatch(/event\.linked_assets\?\.site_ids/);
    expect(src).toMatch(/siteCount/);
  });

  it('passe le footer text à 11px minimum (UX P0-C WCAG)', () => {
    // Anti-régression : plus de text-[10px] dans le composant
    expect(src).not.toMatch(/text-\[10px\]/);
  });
});

// ── C. SolEventStream — grille top N ────────────────────────────────

describe('C. SolEventStream — collection', () => {
  const src = readSrc('ui/sol/SolEventCard.jsx');

  it('limite par défaut à 3 événements (cohérent week-cards §5)', () => {
    expect(src).toMatch(/max\s*=\s*3/);
    expect(src).toMatch(/\.slice\(0, max\)/);
  });

  it("rend null si aucun événement (pas d'empty state pleine largeur §6.1)", () => {
    expect(src).toMatch(/if \(visible\.length === 0\) return null/);
  });

  it('grille responsive 1 col mobile / 3 cols sm (cohérent SolWeekCards)', () => {
    expect(src).toMatch(/grid-cols-1 sm:grid-cols-3/);
  });
});

// ── D. usePageBriefing — exposition events ──────────────────────────

describe('D. usePageBriefing — exposition events', () => {
  const src = readSrc('hooks/usePageBriefing.js');

  it('expose events depuis payload.events (parallèle à week_cards rétro-compat)', () => {
    expect(src).toMatch(/events:\s*payload\?\.events\s*\|\|\s*\[\]/);
  });
});

// ── E. Cockpit — pilote opt-in SolBriefingHead useEventStream ───────

describe('E. Cockpit page-pilote opt-in useEventStream (P0-2)', () => {
  const src = readSrc('pages/Cockpit.jsx');

  it('passe useEventStream à SolBriefingHead (switch week-cards → events)', () => {
    expect(src).toMatch(/<SolBriefingHead[^>]*useEventStream/);
  });

  it("n'importe plus SolEventStream directement (factorisé via HOC ét12d)", () => {
    expect(src).not.toMatch(/import\s*{\s*SolEventStream\s*}\s*from/);
  });
});

// ── F. SolBriefingHead — switch SolWeekCards ↔ SolEventStream ───────

describe('F. SolBriefingHead — switch week-cards / event-stream (P0-2)', () => {
  const src = readSrc('ui/sol/SolBriefingHead.jsx');

  it('importe SolEventStream depuis SolEventCard', () => {
    expect(src).toMatch(/import\s*{\s*SolEventStream\s*}\s*from\s*'\.\/SolEventCard'/);
  });

  it('expose useEventStream prop (défaut false → rétro-compat)', () => {
    expect(src).toMatch(/useEventStream\s*=\s*false/);
  });

  it('bascule vers SolEventStream si useEventStream && events.length > 0', () => {
    expect(src).toMatch(/showEventStream\s*=\s*useEventStream\s*&&\s*hasEvents/);
    expect(src).toMatch(/showEventStream\s*\?[\s\S]*<SolEventStream/);
  });

  it("fallback SolWeekCards si pas d'events ou pas opt-in", () => {
    expect(src).toMatch(/<SolWeekCards/);
  });
});

// ── G. Backend freshness helper ─────────────────────────────────────

describe('G. Backend event_bus.freshness — P0-3 TTL réel', () => {
  const helperPath = join(SRC, '../../backend/services/event_bus/freshness.py');

  it('le helper compute_freshness existe (3 détecteurs partagent la SoT)', () => {
    expect(existsSync(helperPath)).toBe(true);
  });
});
