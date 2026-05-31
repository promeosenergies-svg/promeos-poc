// @vitest-environment jsdom
/**
 * PROMEOS — Tests EnergyProvenanceCoverage (Sprint P1.S7 polish).
 *
 * Vérifie statiquement que tous les composants Énergie qui affichent
 * un KPI utilisent `KpiCardWithProvenance` (ou exposent leur propre
 * tooltip provenance documenté). Aucun KPI affiché sans provenance.
 *
 * Couvre :
 * - MonitoringSynthesisStrip
 * - LoadCurveTab
 * - WeekProfileTab
 * - CostContractTab
 * - MarketExposureTab
 * - Composants UI : ExposureScoreGauge, BaseloadComparisonCard,
 *   TopExpensiveHoursTable, FavorableHoursPanel, WeekProfileHeatmap,
 *   PriceDecompositionTable, CostVsContractCard,
 *   DisplacementSimulationCard
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

function readSrc(rel) {
  return readFileSync(resolve(__dirname, rel), 'utf8');
}

describe('Provenance coverage — Tabs Énergie utilisent KpiCardWithProvenance', () => {
  const TABS = [
    '../ui/energy/MonitoringSynthesisStrip.jsx',
    '../pages/consumption/LoadCurveTab.jsx',
    '../pages/usages/WeekProfileTab.jsx',
    '../pages/consumption/CostContractTab.jsx',
    '../pages/consumption/MarketExposureTab.jsx',
  ];

  for (const tab of TABS) {
    it(`${tab.split('/').pop()} importe KpiCardWithProvenance`, () => {
      const src = readSrc(tab);
      expect(src).toMatch(
        /import\s+KpiCardWithProvenance\s+from\s+['"][^'"]+KpiCardWithProvenance['"]/
      );
    });
  }
});

describe('Provenance coverage — composants UI Énergie exposent provenance', () => {
  const PROV_EXPOSING = [
    {
      file: '../ui/energy/ExposureScoreGauge.jsx',
      testid: 'exposure-score-provenance',
    },
    {
      file: '../ui/energy/BaseloadComparisonCard.jsx',
      testid: 'baseload-provenance',
    },
    {
      file: '../ui/energy/TopExpensiveHoursTable.jsx',
      testid: 'top-hour-provenance',
    },
    {
      file: '../ui/energy/PriceDecompositionTable.jsx',
      testid: 'price-component-provenance',
    },
    {
      file: '../ui/energy/CostVsContractCard.jsx',
      testid: 'scenario-provenance',
    },
    {
      file: '../ui/energy/DisplacementSimulationCard.jsx',
      testid: 'simulation-provenance',
    },
    {
      file: '../ui/energy/WeekProfileHeatmap.jsx',
      testid: 'heatmap-provenance',
    },
  ];

  for (const { file, testid } of PROV_EXPOSING) {
    it(`${file.split('/').pop()} expose un data-testid="${testid}"`, () => {
      const src = readSrc(file);
      expect(src).toContain(`data-testid="${testid}"`);
    });
  }
});

describe('Provenance coverage — KpiCardWithProvenance affiche les 5 axes', () => {
  it('rend Source / Service / Formule / Période / Confiance / Hypothèses', () => {
    const src = readSrc('../ui/energy/KpiCardWithProvenance.jsx');
    expect(src).toMatch(/label="Source"/);
    expect(src).toMatch(/label="Service"/);
    expect(src).toMatch(/label="Formule"/);
    expect(src).toMatch(/label="Période"/);
    expect(src).toMatch(/label="Confiance"/);
    expect(src).toMatch(/Hypothèses\s*:/);
  });
});

describe('Provenance coverage — état confidenceDisplay P2.1 (déplacement effectif)', () => {
  it('utils/confidenceDisplay.js SUPPRIMÉ en P2.1 (déplacé sous pages/monitoring/)', () => {
    const { existsSync } = require('fs');
    const { resolve } = require('path');
    expect(existsSync(resolve(__dirname, '../utils/confidenceDisplay.js'))).toBe(false);
  });

  it('pages/monitoring/monitoringConfidenceHelper.js documenté P2.1', () => {
    const src = readSrc('../pages/monitoring/monitoringConfidenceHelper.js');
    expect(src).toMatch(/P2\.1/);
    expect(src).toMatch(/déplacé/i);
    expect(src).toContain('computeConfidence');
  });

  it("MonitoringSynthesisStrip n'importe PAS computeConfidence (consomme data_quality_score backend)", () => {
    const src = readSrc('../ui/energy/MonitoringSynthesisStrip.jsx');
    expect(src).not.toContain('computeConfidence');
    expect(src).not.toContain('confidenceDisplay');
  });
});

describe('Sprint P2.4 — Provenance visible obligatoire (extension P1.S7)', () => {
  it('FavorableHoursPanel expose désormais data-testid="favorable-hours-provenance"', () => {
    const src = readSrc('../ui/energy/FavorableHoursPanel.jsx');
    expect(src).toContain('data-testid="favorable-hours-provenance"');
    expect(src).toMatch(/aria-label=\{[^}]*[Pp]rovenance/);
  });

  it('CostVsContractCard scenarios — ScenarioProvenanceDot exposé', () => {
    const src = readSrc('../ui/energy/CostVsContractCard.jsx');
    expect(src).toContain('ScenarioProvenanceDot');
    expect(src).toContain('data-testid="scenario-provenance"');
  });

  it('DisplacementSimulationCard — SimulationProvenanceDot exposé', () => {
    const src = readSrc('../ui/energy/DisplacementSimulationCard.jsx');
    expect(src).toContain('SimulationProvenanceDot');
    expect(src).toContain('data-testid="simulation-provenance"');
  });

  const METIER_COMPONENTS_WITH_PROVENANCE = [
    { file: '../ui/energy/BaseloadComparisonCard.jsx', testid: 'baseload-provenance' },
    { file: '../ui/energy/CostVsContractCard.jsx', testid: 'scenario-provenance' },
    { file: '../ui/energy/DisplacementSimulationCard.jsx', testid: 'simulation-provenance' },
    { file: '../ui/energy/ExposureScoreGauge.jsx', testid: 'exposure-score-provenance' },
    { file: '../ui/energy/FavorableHoursPanel.jsx', testid: 'favorable-hours-provenance' },
    { file: '../ui/energy/PriceDecompositionTable.jsx', testid: 'price-component-provenance' },
    { file: '../ui/energy/TopExpensiveHoursTable.jsx', testid: 'top-hour-provenance' },
    { file: '../ui/energy/WeekProfileHeatmap.jsx', testid: 'heatmap-provenance' },
  ];

  for (const { file, testid } of METIER_COMPONENTS_WITH_PROVENANCE) {
    it(`${file.split('/').pop()} expose data-testid="${testid}"`, () => {
      const src = readSrc(file);
      expect(src).toContain(`data-testid="${testid}"`);
    });
  }

  it('KpiCardWithProvenance reste le composant canonique délégation', () => {
    const tabsAndStrips = [
      '../ui/energy/MonitoringSynthesisStrip.jsx',
      '../pages/consumption/LoadCurveTab.jsx',
      '../pages/usages/WeekProfileTab.jsx',
      '../pages/consumption/CostContractTab.jsx',
      '../pages/consumption/MarketExposureTab.jsx',
    ];
    for (const file of tabsAndStrips) {
      const src = readSrc(file);
      expect(src).toMatch(/import\s+KpiCardWithProvenance/);
    }
  });

  const NON_METIER_WHITELIST = [
    '../ui/energy/EnergyCrossLinks.jsx',
    '../ui/energy/EnergyFilterBar.jsx',
    '../ui/energy/SiteRequiredState.jsx',
  ];

  for (const file of NON_METIER_WHITELIST) {
    it(`${file.split('/').pop()} (non-métier whitelist) n'accepte pas \`kpi\`/\`provenance\` en prop`, () => {
      const src = readSrc(file);
      // Vérifie que le composant ne déclare pas ces props (signature default function)
      const exportMatch = src.match(/export\s+default\s+function\s+\w+\s*\(([^)]*)\)/);
      if (exportMatch) {
        const props = exportMatch[1];
        expect(props).not.toMatch(/\bkpi\b/);
        expect(props).not.toMatch(/\bkpis\b/);
        expect(props).not.toMatch(/\bprovenance\b/);
      }
    });
  }
});
