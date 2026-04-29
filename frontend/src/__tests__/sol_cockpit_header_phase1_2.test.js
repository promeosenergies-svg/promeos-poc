/**
 * Source-guard Phase 1.2 — SolKickerWithSwitch + SolCockpitHeaderPills.
 *
 * Sprint refonte cockpit dual sol2 (29/04/2026) — étape 1.2 : verrouille
 * les contrats des 2 composants header (kicker switch + pills CTA) qui
 * matérialisent la mécanique réciproque op↔exé doctrine §11.3.
 *
 * Cibles maquettes :
 *   - cockpit-pilotage-briefing-jour.html lignes 219-235 (header complet)
 *   - cockpit-synthese-strategique.html même section (mode strategique)
 *
 * Anti-patterns §6.3 verrouillés :
 *   - Pas de tabs séparées doublonnant la nav (switch intégré au kicker)
 *   - data-testid stables pour Playwright
 *   - Préfixe Sol* obligatoire (déjà respecté par naming)
 *   - aria roles/labels pour a11y WCAG 2.2
 */

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const KICKER_PATH = resolve(__dirname, '..', 'ui', 'sol', 'SolKickerWithSwitch.jsx');
const PILLS_PATH = resolve(__dirname, '..', 'ui', 'sol', 'SolCockpitHeaderPills.jsx');

const KICKER_SRC = readFileSync(KICKER_PATH, 'utf-8');
const PILLS_SRC = readFileSync(PILLS_PATH, 'utf-8');

// ── SolKickerWithSwitch ──────────────────────────────────────────────
describe('SolKickerWithSwitch — contrat Phase 1.2', () => {
  it('exporte un composant React par défaut', () => {
    expect(KICKER_SRC).toMatch(/export default function SolKickerWithSwitch/);
  });

  it('accepte les props canoniques scope + currentRoute', () => {
    expect(KICKER_SRC).toMatch(/scope\s*=\s*['"]?['"]?/);
    expect(KICKER_SRC).toMatch(/currentRoute\s*=\s*['"]jour['"]/);
  });

  it('utilise react-router-dom Link (pas de a href brut anti-pattern SPA)', () => {
    expect(KICKER_SRC).toMatch(/from\s+['"]react-router-dom['"]/);
    expect(KICKER_SRC).toMatch(/<Link/);
    // Vérifier qu'il n'y a pas de <a href="/cockpit/...
    const codeOnly = KICKER_SRC.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    expect(codeOnly, 'Anti-pattern SPA : <a href> direct au lieu de <Link>').not.toMatch(
      /<a\s+href=["']\/cockpit/
    );
  });

  it('cible les 2 routes canoniques /cockpit/jour et /cockpit/strategique', () => {
    expect(KICKER_SRC).toMatch(/['"]\/cockpit\/jour['"]/);
    expect(KICKER_SRC).toMatch(/['"]\/cockpit\/strategique['"]/);
  });

  it('utilise les labels canoniques "Briefing du jour" + "Synthèse stratégique"', () => {
    expect(KICKER_SRC).toMatch(/Briefing du jour/);
    expect(KICKER_SRC).toMatch(/Synthèse stratégique/);
  });

  it('expose les data-testid stables pour Playwright', () => {
    expect(KICKER_SRC).toMatch(/data-testid=["']sol-kicker-with-switch["']/);
    expect(KICKER_SRC).toMatch(/data-testid=["']sol-kicker-switch-jour["']/);
    expect(KICKER_SRC).toMatch(/data-testid=["']sol-kicker-switch-strategique["']/);
  });

  it('utilise role="tablist" + role="tab" + aria-selected (WCAG 2.2 §13)', () => {
    expect(KICKER_SRC).toMatch(/role=["']tablist["']/);
    expect(KICKER_SRC).toMatch(/role=["']tab["']/);
    expect(KICKER_SRC).toMatch(/aria-selected=\{currentRoute\s*===\s*['"]jour['"]\}/);
    expect(KICKER_SRC).toMatch(/aria-selected=\{currentRoute\s*===\s*['"]strategique['"]\}/);
  });

  it('aria-label décrit la nature du switch', () => {
    expect(KICKER_SRC).toMatch(/aria-label=["']Vue Cockpit["']/);
  });

  it('utilise les tokens Sol (pas de couleurs hardcodées hex)', () => {
    // Tolère les fallbacks dans var() : `var(--sol-x, #fallback)`. Anti-pattern
    // est un hex isolé hors var().
    const codeOnly = KICKER_SRC.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    const hexOutsideVar = codeOnly.match(/(?<!var\([^)]*)#[0-9a-fA-F]{3,6}(?![^()]*\))/g);
    expect(hexOutsideVar, 'Hex hardcodés hors var() détectés — utiliser tokens Sol').toBeNull();
  });
});

// ── SolCockpitHeaderPills ────────────────────────────────────────────
describe('SolCockpitHeaderPills — contrat Phase 1.2', () => {
  it('exporte un composant React par défaut', () => {
    expect(PILLS_SRC).toMatch(/export default function SolCockpitHeaderPills/);
  });

  it('accepte les props canoniques alertsCount + epexPriceEurMwh + onActionCenterClick', () => {
    expect(PILLS_SRC).toMatch(/alertsCount\s*=\s*0/);
    expect(PILLS_SRC).toMatch(/epexPriceEurMwh\s*=\s*null/);
    expect(PILLS_SRC).toMatch(/onActionCenterClick\s*=\s*null/);
  });

  it('utilise useNavigate par défaut si onActionCenterClick absent', () => {
    expect(PILLS_SRC).toMatch(/useNavigate/);
    expect(PILLS_SRC).toMatch(/navigate\(['"]\/actions['"]\)/);
  });

  it('rend la pill alertes uniquement si alertsCount > 0 (anti empty pill)', () => {
    expect(PILLS_SRC).toMatch(/alertsCount\s*>\s*0\s*&&/);
  });

  it('pluralise correctement "alerte" vs "alertes"', () => {
    expect(PILLS_SRC).toMatch(/alertsCount\s*>\s*1\s*\?\s*['"]s['"]\s*:\s*['"]['"]/);
  });

  it('rend la pill EPEX uniquement si prix > 0 (no-empty)', () => {
    expect(PILLS_SRC).toMatch(/epexPriceEurMwh\s*!=\s*null\s*&&\s*epexPriceEurMwh\s*>\s*0/);
  });

  it('arrondit le prix EPEX (Math.round) — densité éditoriale', () => {
    expect(PILLS_SRC).toMatch(/Math\.round\(epexPriceEurMwh\)/);
  });

  it('expose les data-testid stables pour Playwright', () => {
    expect(PILLS_SRC).toMatch(/data-testid=["']sol-cockpit-header-pills["']/);
    expect(PILLS_SRC).toMatch(/data-testid=["']sol-cockpit-pill-alerts["']/);
    expect(PILLS_SRC).toMatch(/data-testid=["']sol-cockpit-pill-epex["']/);
    expect(PILLS_SRC).toMatch(/data-testid=["']sol-cockpit-cta-action-center["']/);
  });

  it('CTA porte un aria-label explicite (WCAG 2.2 §13)', () => {
    expect(PILLS_SRC).toMatch(/aria-label=["']Ouvrir le centre d'action["']/);
  });

  it('CTA utilise type="button" (anti-submit involontaire)', () => {
    expect(PILLS_SRC).toMatch(/type=["']button["']/);
  });

  it('utilise les tokens Sol via CSS variables (--sol-*)', () => {
    expect(PILLS_SRC).toMatch(/var\(--sol-/);
    // Pas de #hex hors var() (tolère fallbacks dans var())
    const codeOnly = PILLS_SRC.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    const hexOutsideVar = codeOnly.match(/(?<!var\([^)]*)#[0-9a-fA-F]{3,6}(?![^()]*\))/g);
    expect(hexOutsideVar, 'Hex hardcodés hors var() détectés — utiliser tokens Sol').toBeNull();
  });
});

// ── Cohérence cross-composant ────────────────────────────────────────
describe('Phase 1.2 — cohérence cross-composant', () => {
  it('les 2 composants utilisent le préfixe Sol* canonique', () => {
    expect(KICKER_SRC).toMatch(/SolKickerWithSwitch/);
    expect(PILLS_SRC).toMatch(/SolCockpitHeaderPills/);
  });

  it('les 2 composants sont des display components (zero fetch)', () => {
    // Pas de useEffect, pas de useState pour data, pas de fetch/axios
    const codeOnlyKicker = KICKER_SRC.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    const codeOnlyPills = PILLS_SRC.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    expect(codeOnlyKicker).not.toMatch(/useEffect|useState|fetch\(|axios/);
    expect(codeOnlyPills).not.toMatch(/useEffect|useState|fetch\(|axios/);
  });
});
