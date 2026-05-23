/**
 * P0-B 2026-05-23 — onboarding entry-points consolidés.
 *
 * Doctrine canonique (cf. docs/dev/patrimoine_routes_canonical.md §9) :
 *   - parcours initial : SireneOnboardingPage (SIREN/SIRET)
 *   - import bulk     : PatrimoineWizard (déclenché depuis Patrimoine)
 *   - création manuelle: QuickCreateSite drawer
 *   - SiteCreationWizard : sous-composant interne, pas d'entrée principale
 *   - OnboardingPage  : composant orphelin (réserve Phase 4), aucune route active
 *
 * Tests pure-grep alignés sur le pattern grammar/hub/__tests__/*.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const SRC = resolve(__dirname, '..');
const APP_JSX = readFileSync(resolve(SRC, 'App.jsx'), 'utf-8');
const PATRIMOINE_JSX = readFileSync(resolve(SRC, 'pages/Patrimoine.jsx'), 'utf-8');

describe('Onboarding entry-points (P0-B)', () => {
  it('/onboarding ne redirige plus vers /cockpit/jour', () => {
    // L'ancienne route morte renvoyait vers /cockpit/jour
    expect(APP_JSX).not.toMatch(/path="\/onboarding"[\s\S]{0,200}Navigate to="\/cockpit\/jour"/);
  });

  it('/onboarding redirige vers /onboarding/sirene (parcours canonique)', () => {
    expect(APP_JSX).toMatch(
      /path="\/onboarding"[\s\S]{0,200}Navigate to="\/onboarding\/sirene" replace/,
    );
  });

  it('/onboarding/sirene rend SireneOnboardingPage', () => {
    expect(APP_JSX).toMatch(/path="\/onboarding\/sirene"[\s\S]{0,250}<SireneOnboardingPage/);
  });

  it("OnboardingPage n'est ni importée ni montée en route active", () => {
    // OnboardingPage est conservée en fichier (Phase 4) mais aucune route ne la rend.
    expect(APP_JSX).not.toMatch(/<OnboardingPage\b/);
  });

  it('SiteCreationWizard est utilisé uniquement en sous-composant de Patrimoine', () => {
    // SiteCreationWizard ne doit pas être attaché à une <Route> de App.jsx.
    expect(APP_JSX).not.toMatch(/<SiteCreationWizard\b/);
    // Mais reste accessible comme option avancée de QuickCreateSite dans Patrimoine.jsx.
    expect(PATRIMOINE_JSX).toMatch(/<SiteCreationWizard\b/);
  });

  it("Patrimoine empty-state propose 3 options en français claires", () => {
    expect(PATRIMOINE_JSX).toContain('Depuis Sirene');
    expect(PATRIMOINE_JSX).toContain('Nouveau site manuel');
    expect(PATRIMOINE_JSX).toContain('Importer CSV');
  });

  it('aucune mention de route morte /cockpit/jour comme cible /onboarding', () => {
    // Sanity : la ligne explicative ancienne (Phase 4 / 2026-05-09) a disparu.
    expect(APP_JSX).not.toContain('test 2 doctrinal');
    expect(APP_JSX).not.toContain('Redirect vers /cockpit/jour le temps');
  });
});
