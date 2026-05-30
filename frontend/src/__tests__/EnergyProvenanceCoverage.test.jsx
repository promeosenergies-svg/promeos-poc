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

describe('Provenance coverage — état confidenceDisplay.js documenté P1.S7', () => {
  it('confidenceDisplay.js contient la justification P1.S7 Option B', () => {
    const src = readSrc('../utils/confidenceDisplay.js');
    expect(src).toMatch(/P1\.S7/);
    expect(src).toMatch(/Option B/);
    expect(src).toMatch(/P2\.1/);
  });

  it("MonitoringSynthesisStrip n'importe PAS computeConfidence (consomme data_quality_score backend)", () => {
    const src = readSrc('../ui/energy/MonitoringSynthesisStrip.jsx');
    expect(src).not.toContain('computeConfidence');
    expect(src).not.toContain('confidenceDisplay');
  });
});
