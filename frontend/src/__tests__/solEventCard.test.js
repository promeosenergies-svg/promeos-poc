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

// ── B-ter. ét12e corrections P0 résiduels (mitigation 14px + drill-down) ─

describe('B-ter. SolEventCard — corrections P0 résiduels ét12e', () => {
  const src = readSrc('ui/sol/SolEventCard.jsx');

  it('mitigation rendue en 14px (text-sm) sur fond --sol-calme-bg (CFO P0 #2)', () => {
    // ét12e : text-sm bandeau dédié. ét16 : variant aQualifier ajouté avec
    // fond --sol-attention-bg pour signaler "à creuser" sans crier.
    expect(src).toMatch(/text-sm font-medium text-\[var\(--sol-ink-900\)\]/);
    expect(src).toMatch(/var\(--sol-calme-bg\)/);
    // Wallet size 12 (variant aQualifier) ou 14 (chiffrée)
    expect(src).toMatch(/<Wallet[\s\S]*?size=\{mitigationVariant === 'aQualifier' \? 12 : 14\}/);
  });

  it('expose mitigation à qualifier en italic ambré quand impact € sans chiffres (ét16 P0 CFO)', () => {
    expect(src).toMatch(/mitigationVariant/);
    expect(src).toMatch(/Mitigation à qualifier/);
    expect(src).toMatch(/var\(--sol-attention-bg\)/);
  });

  it('expose drill-down methodology via popover (CFO P0 #3)', () => {
    expect(src).toMatch(/methodology = event\.source\?\.methodology/);
    // ét16 : Info size 11 → 14 (a11y target size 24×24 px)
    expect(src).toMatch(/<Info size=\{14\}/);
    expect(src).toMatch(/methodologyOpen/);
    expect(src).toMatch(/setMethodologyOpen/);
    // Le popover s'ouvre/ferme indépendamment de la navigation card
    expect(src).toMatch(/e\.stopPropagation\(\)/);
    // Le bouton porte un aria-label explicite
    expect(src).toMatch(/aria-label="Voir la méthodologie de calcul"/);
    expect(src).toMatch(/aria-expanded=\{methodologyOpen\}/);
  });

  it('a11y popover ét16 : target 24×24 + Escape close + focus retour + aria-controls', () => {
    // ét16 audit EM #3 a11y WCAG 2.5.8 + 2.4.3 + 2.1.2
    expect(src).toMatch(/w-6 h-6/); // target 24×24 px
    expect(src).toMatch(/methodologyButtonRef/); // ref pour focus retour
    expect(src).toMatch(/'Escape'/); // close au clavier
    expect(src).toMatch(/methodologyButtonRef\.current\?\.focus\(\)/);
    expect(src).toMatch(/aria-controls=\{`sol-event-\$\{event\.id\}-methodology`\}/);
  });

  it('le popover affiche la méthodologie complète (rôle region accessible)', () => {
    expect(src).toMatch(/role="region"/);
    expect(src).toMatch(/aria-label="Méthodologie de calcul"/);
  });
});

// ── H. Backend mitigation YAML loader (P0 #4 ét12e) ─────────────────

describe('H. Backend mitigation_defaults.yaml + loader (P0 #4 ét12e)', () => {
  const yamlPath = join(SRC, '../../backend/config/mitigation_defaults.yaml');
  const loaderPath = join(SRC, '../../backend/config/mitigation_loader.py');

  it('le YAML versionné existe (SoT canonique constantes mitigation)', () => {
    expect(existsSync(yamlPath)).toBe(true);
  });

  it('le loader Python expose compute_npv_actualized (P0 #1 CFO)', () => {
    expect(existsSync(loaderPath)).toBe(true);
    const src = readFileSync(loaderPath, 'utf-8');
    expect(src).toMatch(/def compute_npv_actualized/);
    expect(src).toMatch(/discount_rate/);
    // Formule annuité actualisée : (1 - (1+r)^-N) / r
    expect(src).toMatch(/annuity_factor/);
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

// ── I. Backend détecteurs ét13a/b (flex_opportunity + market_window) ─

describe('I. Backend détecteurs ét13a/b — différenciants VC Series A', () => {
  const flexPath = join(
    SRC,
    '../../backend/services/event_bus/detectors/flex_opportunity_detector.py'
  );
  const marketPath = join(
    SRC,
    '../../backend/services/event_bus/detectors/market_window_detector.py'
  );
  const registryPath = join(SRC, '../../backend/services/event_bus/detectors/__init__.py');

  it('flex_opportunity_detector existe (P0 #3 Sarah Sequoia — NEBCO post-ARENH)', () => {
    expect(existsSync(flexPath)).toBe(true);
    const src = readFileSync(flexPath, 'utf-8');
    expect(src).toMatch(/event_type="flex_opportunity"/);
    expect(src).toMatch(/owner_role="Energy Manager"/);
    expect(src).toMatch(/route="\/flex"/);
    // Réutilise SoT canonique flex_nebco_service (règle §10 P3)
    expect(src).toMatch(/from services\.flex_nebco_service import compute_flex_portfolio/);
  });

  it('market_window_detector existe (P0 #3 Sarah Sequoia — capacité 1/11/2026)', () => {
    expect(existsSync(marketPath)).toBe(true);
    const src = readFileSync(marketPath, 'utf-8');
    expect(src).toMatch(/event_type="market_window"/);
    // ét12g : deadline externalisée vers YAML versionné (mitigation_defaults)
    expect(src).toMatch(/get_market_capacity_2026_defaults/);
    expect(src).toMatch(/owner_role="DAF"/);
    expect(src).toMatch(/route="\/achat-energie"/);
  });

  it('les 2 détecteurs sont enregistrés dans DETECTORS registry', () => {
    const src = readFileSync(registryPath, 'utf-8');
    expect(src).toMatch(/flex_opportunity_detector/);
    expect(src).toMatch(/market_window_detector/);
    // Total 5 détecteurs maintenant (3 ét12 + 2 ét13)
    const matches = src.match(/_detector,\s*#\s*type:\s*ignore/g) || [];
    expect(matches.length).toBeGreaterThanOrEqual(5);
  });
});

// ── J. Backend σ amont consumption_diagnostic (P0 EM ét12f-C) ──────

describe('J. consumption_diagnostic._detect_derive expose σ + z-score (P0 EM)', () => {
  const cdPath = join(SRC, '../../backend/services/consumption_diagnostic.py');

  it('_detect_derive calcule sigma_baseline_kwh dans metrics', () => {
    const src = readFileSync(cdPath, 'utf-8');
    expect(src).toMatch(/sigma_baseline_kwh/);
    expect(src).toMatch(/z_score/);
    // Calcul σ : variance + sqrt
    expect(src).toMatch(/math\.sqrt\(variance\)/);
  });
});
