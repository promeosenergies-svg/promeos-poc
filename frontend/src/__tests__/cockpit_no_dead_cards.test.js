/**
 * Source-guard préventif Phase 0.5 — anti-cards mortes Cockpit dual sol2.
 *
 * Sprint refonte cockpit dual sol2 (28/04/2026) — étape 0.5 : verrouille
 * que les anti-patterns visuels listés dans
 * `docs/maquettes/cockpit-sol2/README.md` ne sont pas réintroduits dans
 * Cockpit.jsx ou ses sous-composants.
 *
 * Anti-patterns Doctrine §6.3 + arbitrages Amine :
 * - Card "Bienvenue PROMEOS" en pleine largeur sans densité d'info
 * - Card "Gain simulé empty" anti-pattern empty state
 * - 4 KPI hero (le triptyque est inviolable — exactement 3)
 * - Acronymes bruts en titres (DT/BACS/GTB/TURPE) — déjà couvert par
 *   SolAcronym + glossary, on duplique le check ici pour Cockpit
 * - Bandeau Pilotage usages avec 4 sub-cards en Vue Exécutive
 * - Card Hypermarché Montreuil en scope HELIOS (déjà couvert par
 *   test_helios_no_demo_sites_leak Phase 0.7, on ne duplique pas)
 *
 * Phase 0.5 actuelle : aucune card morte trouvée dans le code, donc le
 * delete est vide. Ce source-guard joue le rôle de gardien préventif
 * pour empêcher toute future réintroduction.
 */

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const COCKPIT_PATH = resolve(__dirname, '..', 'pages', 'Cockpit.jsx');
const COCKPIT_SRC = readFileSync(COCKPIT_PATH, 'utf-8');

describe('test_cockpit_no_dead_cards_leak — source-guard Phase 0.5', () => {
  it('Cockpit.jsx ne contient pas de card "Bienvenue PROMEOS"', () => {
    // Pattern anti-pattern §6.3 : card pleine largeur sans densité
    expect(COCKPIT_SRC).not.toMatch(/Bienvenue\s+PROMEOS/i);
    expect(COCKPIT_SRC).not.toMatch(/Bienvenue\s+chez\s+PROMEOS/i);
  });

  it('Cockpit.jsx ne contient pas de card "Gain simulé empty"', () => {
    // L'empty state du NebcoSimulationCard interne reste OK (composant
    // orphelin retiré du Cockpit Phase 0.4). On vérifie ici qu'aucun
    // empty state « Gain simulé » ne réapparaît directement dans Cockpit.
    const lines = COCKPIT_SRC.split('\n');
    const leakLines = lines.filter((line) => {
      if (line.trim().startsWith('//') || line.trim().startsWith('*')) return false;
      return /Gain\s+simul[éeée]/i.test(line);
    });
    expect(
      leakLines,
      'Card "Gain simulé" leakée dans Cockpit.jsx (anti-pattern §6.1 empty state)'
    ).toHaveLength(0);
  });

  it("Cockpit.jsx n'utilise plus le bandeau Pilotage usages 4 sub-cards", () => {
    // Phase 0.4 a remplacé le bandeau par <SolFlexTeaser>. Anti-régression :
    // les 4 imports doivent rester absents.
    expect(COCKPIT_SRC).not.toMatch(/import\s+RadarPrixNegatifsCard/);
    expect(COCKPIT_SRC).not.toMatch(
      /import\s+RoiFlexReadyCard\s+from\s+'\.\.\/components\/pilotage/
    );
    expect(COCKPIT_SRC).not.toMatch(
      /import\s+PortefeuilleScoringCard\s+from\s+'\.\.\/components\/pilotage/
    );
    expect(COCKPIT_SRC).not.toMatch(
      /import\s+NebcoSimulationCard\s+from\s+'\.\.\/components\/pilotage/
    );
  });

  it('Cockpit.jsx utilise le SolFlexTeaser canonique (Phase 0.4)', () => {
    expect(COCKPIT_SRC).toMatch(/import\s+SolFlexTeaser/);
    expect(COCKPIT_SRC).toMatch(/<SolFlexTeaser\b/);
  });

  it('Cockpit.jsx ne contient pas un dashboard de ≥ 10 cards (widget-empilement)', () => {
    // Heuristique : compter les data-testid="*-card" + classes "rounded-xl border" récurrentes.
    // Anti-pattern §6.3 : ≥10 cards = dérive widget-empilement.
    const cardTestids = (COCKPIT_SRC.match(/data-testid="[a-z-]*-card"/g) || []).length;
    expect(
      cardTestids,
      `Cockpit contient ${cardTestids} data-testid='*-card' — au-delà de 10 = dérive widget-empilement §6.3`
    ).toBeLessThan(10);
  });

  it('Cockpit.jsx ne réintroduit pas ExecutiveKpiRow (Phase 0.2 décommission)', () => {
    expect(COCKPIT_SRC).not.toMatch(/ExecutiveKpiRow/);
  });

  it('Cockpit.jsx ne réintroduit pas ImpactDecisionPanel (Phase 0.3 décommission)', () => {
    expect(COCKPIT_SRC).not.toMatch(/ImpactDecisionPanel/);
  });
});
