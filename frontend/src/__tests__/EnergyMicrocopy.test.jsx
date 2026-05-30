// @vitest-environment jsdom
/**
 * PROMEOS — Tests EnergyMicrocopy (Sprint P1.S7 polish).
 *
 * Vérifie l'homogénéité de la microcopy FR cross-vues Énergie :
 * - SiteRequiredState « Sélectionnez un site pour analyser cette vue. »
 * - Warning « Simulation indicative — ne constitue pas une promesse
 *   d'économie. » (CostVsContract + DisplacementSimulation)
 * - États sain/vigilance/critique/inactif harmonisés
 * - Pas d'émoji
 * - Pas de message technique ENERGY_SCOPE_INVALID exposé en clair
 * - correlation_id affiché uniquement dans ApiErrorState (erreurs)
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

function readSrc(rel) {
  return readFileSync(resolve(__dirname, rel), 'utf8');
}

describe('Microcopy — SiteRequiredState uniforme cross-vues', () => {
  it('le composant porte la phrase canonique', () => {
    const src = readSrc('../ui/energy/SiteRequiredState.jsx');
    expect(src).toContain('Sélectionnez un site pour analyser cette vue.');
  });

  it('WeekProfileTab importe SiteRequiredState', () => {
    const src = readSrc('../pages/usages/WeekProfileTab.jsx');
    expect(src).toMatch(/import\s+SiteRequiredState/);
  });

  it('CostContractTab importe SiteRequiredState', () => {
    const src = readSrc('../pages/consumption/CostContractTab.jsx');
    expect(src).toMatch(/import\s+SiteRequiredState/);
  });

  it('MarketExposureTab importe SiteRequiredState', () => {
    const src = readSrc('../pages/consumption/MarketExposureTab.jsx');
    expect(src).toMatch(/import\s+SiteRequiredState/);
  });
});

describe('Microcopy — warning « Simulation indicative » obligatoire', () => {
  const PHRASE = "Simulation indicative — ne constitue pas une promesse d'économie.";

  it('CostVsContractCard contient le warning hardcodé fallback', () => {
    const src = readSrc('../ui/energy/CostVsContractCard.jsx');
    expect(src).toContain(PHRASE);
  });

  it('DisplacementSimulationCard contient le warning hardcodé fallback', () => {
    const src = readSrc('../ui/energy/DisplacementSimulationCard.jsx');
    expect(src).toContain(PHRASE);
  });
});

describe('Microcopy — états canoniques sain/vigilance/critique/inactif', () => {
  it('KpiCardWithProvenance définit STATE_TINT pour les 4 states', () => {
    const src = readSrc('../ui/energy/KpiCardWithProvenance.jsx');
    expect(src).toMatch(/sain:\s*['"]/);
    expect(src).toMatch(/vigilance:\s*['"]/);
    expect(src).toMatch(/critique:\s*['"]/);
    expect(src).toMatch(/inactif:\s*['"]/);
  });

  it('ExposureScoreGauge définit les 4 states', () => {
    const src = readSrc('../ui/energy/ExposureScoreGauge.jsx');
    expect(src).toMatch(/sain:\s*['"]/);
    expect(src).toMatch(/vigilance:\s*['"]/);
    expect(src).toMatch(/critique:\s*['"]/);
    expect(src).toMatch(/inactif:\s*['"]/);
  });
});

describe("Microcopy — pas d'émoji dans les composants Énergie", () => {
  const FILES = [
    '../ui/energy/KpiCardWithProvenance.jsx',
    '../ui/energy/MonitoringSynthesisStrip.jsx',
    '../ui/energy/EnergyFilterBar.jsx',
    '../ui/energy/WeekProfileHeatmap.jsx',
    '../ui/energy/CostVsContractCard.jsx',
    '../ui/energy/PriceDecompositionTable.jsx',
    '../ui/energy/ExposureScoreGauge.jsx',
    '../ui/energy/TopExpensiveHoursTable.jsx',
    '../ui/energy/FavorableHoursPanel.jsx',
    '../ui/energy/BaseloadComparisonCard.jsx',
    '../ui/energy/DisplacementSimulationCard.jsx',
    '../ui/energy/SiteRequiredState.jsx',
    '../ui/energy/EnergyCrossLinks.jsx',
    '../pages/consumption/CostContractTab.jsx',
    '../pages/consumption/MarketExposureTab.jsx',
    '../pages/usages/WeekProfileTab.jsx',
  ];

  // Liste d'émojis fréquents (extensible). Pas exhaustive — vérifie
  // qu'aucun caractère emoji des plages les plus communes n'apparaît.
  // Whitelist : caractères techniques ASCII + accents FR + symboles
  // typographiques (—, ·, ², ³, π, Σ, ², ✓, ², ÷, ×) ne sont PAS des
  // emojis.
  const EMOJI_REGEX =
    /[\u{1F300}-\u{1FAFF}\u{1F600}-\u{1F64F}\u{1F680}-\u{1F6FF}\u{1F900}-\u{1F9FF}\u{2600}-\u{26FF}]/u;

  for (const file of FILES) {
    it(`${file.split('/').pop()} ne contient pas d'émoji`, () => {
      const src = readSrc(file);
      expect(src).not.toMatch(EMOJI_REGEX);
    });
  }
});

describe('Microcopy — pas de code technique ENERGY_* exposé en clair', () => {
  // Le code technique apparaît dans les error states (data-testid="error-code")
  // mais n'est jamais en dur dans le JSX (toujours sur err.response.data.detail.code).
  const TABS = [
    '../pages/consumption/CostContractTab.jsx',
    '../pages/consumption/MarketExposureTab.jsx',
    '../pages/usages/WeekProfileTab.jsx',
    '../ui/energy/MonitoringSynthesisStrip.jsx',
  ];

  for (const tab of TABS) {
    it(`${tab.split('/').pop()} ne contient pas de string ENERGY_SCOPE_INVALID en dur`, () => {
      const src = readSrc(tab);
      // Code stable doit venir de detail.code, jamais d'un literal
      expect(src).not.toMatch(/['"`]ENERGY_SCOPE_INVALID['"`]/);
      expect(src).not.toMatch(/['"`]ENERGY_DAYS_INSUFFICIENT['"`]/);
    });
  }
});

describe('Microcopy — correlation_id affiché uniquement dans les error states', () => {
  const TABS = [
    '../pages/consumption/CostContractTab.jsx',
    '../pages/consumption/MarketExposureTab.jsx',
    '../pages/usages/WeekProfileTab.jsx',
    '../ui/energy/MonitoringSynthesisStrip.jsx',
  ];

  for (const tab of TABS) {
    it(`${tab.split('/').pop()} affiche correlation_id dans error-correlation-id`, () => {
      const src = readSrc(tab);
      expect(src).toMatch(/data-testid="error-correlation-id"/);
    });
  }
});

describe('Microcopy — partial data banner FR', () => {
  it('WeekProfileTab : « Données partielles »', () => {
    const src = readSrc('../pages/usages/WeekProfileTab.jsx');
    expect(src).toContain('Données partielles');
  });

  it('CostContractTab : « Simulation partielle »', () => {
    const src = readSrc('../pages/consumption/CostContractTab.jsx');
    expect(src).toContain('Simulation partielle');
  });

  it('MarketExposureTab : « Analyse partielle »', () => {
    const src = readSrc('../pages/consumption/MarketExposureTab.jsx');
    expect(src).toContain('Analyse partielle');
  });
});

describe('Microcopy — cross-links sobres P1.S7', () => {
  it('EnergyCrossLinks définit le label "Aller plus loin"', () => {
    const src = readSrc('../ui/energy/EnergyCrossLinks.jsx');
    expect(src).toContain('Aller plus loin');
  });

  it('CostContractTab pointe vers /bill-intel + /achat-energie', () => {
    const src = readSrc('../pages/consumption/CostContractTab.jsx');
    expect(src).toContain('/bill-intel');
    expect(src).toContain('/achat-energie');
    expect(src).toContain('Comparer à la facture');
    expect(src).toContain('Simuler une offre alternative');
  });

  it('MarketExposureTab pointe vers /achat-energie + /action-center-v4', () => {
    const src = readSrc('../pages/consumption/MarketExposureTab.jsx');
    expect(src).toContain('/achat-energie');
    expect(src).toContain('/action-center-v4');
    expect(src).toContain('Créer une action');
  });
});
