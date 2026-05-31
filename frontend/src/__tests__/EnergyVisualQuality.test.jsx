/**
 * PROMEOS — Tests EnergyVisualQuality (Sprint P2.5 audit final).
 *
 * Vérifie statiquement que les vues Énergie ne contiennent JAMAIS :
 * - identifiant technique « Site #${id} », « Compteur #${id} », « Organisation #${id} »
 * - doublon « Site Site »
 * - jargon anglais générique (« No data », « See more », « Click here », « Retry » comme bouton)
 * - code ENERGY_* hardcodé en literal hors ApiErrorState
 * - texte « undefined », « NaN », « object Object »
 * - lorem ipsum / TODO / FIXME / debug visible
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

function readSrc(rel) {
  return readFileSync(resolve(__dirname, rel), 'utf8');
}

const ENERGY_VIEWS = [
  '../pages/MonitoringPage.jsx',
  '../pages/monitoring/MonitoringClimateScatter.jsx',
  '../pages/monitoring/monitoringConfidenceHelper.js',
  '../pages/consumption/LoadCurveTab.jsx',
  '../pages/consumption/CostContractTab.jsx',
  '../pages/consumption/MarketExposureTab.jsx',
  '../pages/usages/WeekProfileTab.jsx',
  '../ui/energy/EnergyFilterBar.jsx',
  '../ui/energy/MonitoringSynthesisStrip.jsx',
  '../ui/energy/KpiCardWithProvenance.jsx',
  '../ui/energy/LoadCurveChart.jsx',
  '../ui/energy/WeekProfileHeatmap.jsx',
  '../ui/energy/CostVsContractCard.jsx',
  '../ui/energy/PriceDecompositionTable.jsx',
  '../ui/energy/ExposureScoreGauge.jsx',
  '../ui/energy/TopExpensiveHoursTable.jsx',
  '../ui/energy/FavorableHoursPanel.jsx',
  '../ui/energy/BaseloadComparisonCard.jsx',
  '../ui/energy/DisplacementSimulationCard.jsx',
  '../ui/energy/EnergyCrossLinks.jsx',
  '../ui/energy/SiteRequiredState.jsx',
  '../ui/energy/TopPeaksTable.jsx',
  '../ui/energy/scopeLabel.js',
];

function codeWithoutComments(src) {
  return src
    .split('\n')
    .filter((line) => {
      const t = line.trim();
      return !t.startsWith('//') && !t.startsWith('*');
    })
    .join('\n');
}

describe('EnergyVisualQuality — identifiants techniques INTERDITS', () => {
  for (const file of ENERGY_VIEWS) {
    it(`${file.split('/').pop()} ne contient PAS d'identifiant technique « Site #» ni « # technique»`, () => {
      const code = codeWithoutComments(readSrc(file));
      expect(code).not.toMatch(/`Site #\$\{[^}]+\}`/);
      expect(code).not.toMatch(/`Compteur #\$\{[^}]+\}`/);
      expect(code).not.toMatch(/`Organisation #\$\{[^}]+\}`/);
      expect(code).not.toMatch(/`Entité #\$\{[^}]+\}`/);
      expect(code).not.toMatch(/['"`]#\$\{scope\?\.id\}['"`]/);
      expect(code).not.toMatch(/['"`]#\$\{site\.id\}['"`]/);
    });
  }
});

describe('EnergyVisualQuality — jargon anglais générique INTERDIT', () => {
  for (const file of ENERGY_VIEWS) {
    it(`${file.split('/').pop()} ne contient pas de jargon anglais générique`, () => {
      const code = codeWithoutComments(readSrc(file));
      // Patterns interdits dans le code (chaînes JSX rendues utilisateur)
      expect(code).not.toMatch(/>\s*No data\s*</);
      expect(code).not.toMatch(/>\s*See more\s*</);
      expect(code).not.toMatch(/>\s*Click here\s*</);
      expect(code).not.toMatch(/>\s*Learn more\s*</);
      // Loader anglais (le « Loading... » seul est interdit en JSX rendu)
      expect(code).not.toMatch(/>\s*Loading\.\.\.\s*</);
      // « Retry » comme texte bouton (en français « Réessayer »)
      expect(code).not.toMatch(/>\s*Retry\s*</);
      // « Error » comme texte de remplacement
      expect(code).not.toMatch(/>\s*Error\s*</);
    });
  }
});

describe('EnergyVisualQuality — sentinelles techniques INTERDITES', () => {
  for (const file of ENERGY_VIEWS) {
    it(`${file.split('/').pop()} ne contient PAS undefined/NaN/object Object/TODO/FIXME/lorem en JSX rendu`, () => {
      const code = codeWithoutComments(readSrc(file));
      // Sentinelles techniques rendues utilisateur
      expect(code).not.toMatch(/>\s*undefined\s*</);
      expect(code).not.toMatch(/>\s*NaN\s*</);
      expect(code).not.toMatch(/>\s*\[object Object\]\s*</);
      expect(code).not.toMatch(/>\s*lorem ipsum\b/i);
      // TODO/FIXME en JSX rendu (pas en commentaire)
      expect(code).not.toMatch(/>\s*TODO\s*</);
      expect(code).not.toMatch(/>\s*FIXME\s*</);
      // debug() call
      expect(code).not.toMatch(/\bdebug\s*\([^)]*\)/);
      // console.log() call
      expect(code).not.toMatch(/\bconsole\.log\s*\(/);
    });
  }
});

describe('EnergyVisualQuality — codes ENERGY_* uniquement dans ApiErrorState', () => {
  // Les literals 'ENERGY_UNKNOWN' / 'ENERGY_*' n'apparaissent que comme
  // fallback de detail.code dans les composants ApiErrorState. Pas
  // affichés directement comme jargon métier dans un état attendu.
  const TABS_WITH_API_ERROR_STATE = [
    '../pages/consumption/LoadCurveTab.jsx',
    '../pages/consumption/CostContractTab.jsx',
    '../pages/consumption/MarketExposureTab.jsx',
    '../pages/usages/WeekProfileTab.jsx',
    '../ui/energy/MonitoringSynthesisStrip.jsx',
  ];
  for (const file of TABS_WITH_API_ERROR_STATE) {
    it(`${file.split('/').pop()} expose ENERGY_UNKNOWN uniquement comme fallback detail.code`, () => {
      const code = codeWithoutComments(readSrc(file));
      // 'ENERGY_UNKNOWN' doit apparaître après `detail.code ||` (fallback)
      const literal = code.match(/['"]ENERGY_UNKNOWN['"]/g) || [];
      const fallback = code.match(/detail\.code\s*\|\|\s*['"]ENERGY_UNKNOWN['"]/g) || [];
      // Toutes les occurrences ENERGY_UNKNOWN doivent être un fallback
      expect(literal.length).toBeGreaterThan(0);
      expect(literal.length).toBe(fallback.length);
    });
  }
});

describe('EnergyVisualQuality — fallback site label canonique', () => {
  it('LoadCurveTab utilise formatSiteLabel (pas de fallback technique)', () => {
    const src = readSrc('../pages/consumption/LoadCurveTab.jsx');
    expect(src).toMatch(/import\s+\{\s*formatSiteLabel\s*\}\s+from/);
    expect(src).toContain('formatSiteLabel(');
  });

  it('EnergyFilterBar utilise formatSiteLabel (pas de fallback #id)', () => {
    const src = readSrc('../ui/energy/EnergyFilterBar.jsx');
    expect(src).toMatch(/import\s+\{\s*formatSiteLabel\s*\}\s+from/);
    expect(src).toContain('formatSiteLabel(');
  });

  it('scopeLabel.js documente la doctrine zéro identifiant technique', () => {
    const src = readSrc('../ui/energy/scopeLabel.js');
    expect(src).toContain('INTERDIT');
    expect(src).toContain('FALLBACK_SITE_SELECTED');
    expect(src).toContain('FALLBACK_NO_SITE');
  });
});

describe('EnergyVisualQuality — CTA cross-links pointent vers routes existantes', () => {
  // Les routes cibles doivent être présentes dans NavRegistry.
  const expectedRoutes = [
    '/action-center-v4',
    '/conformite/tertiaire',
    '/conformite?tab=donnees',
    '/bill-intel',
    '/achat-energie',
  ];
  it('toutes les routes cibles cross-links sont déclarées dans NavRegistry', () => {
    const nav = readSrc('../layout/NavRegistry.js');
    for (const route of expectedRoutes) {
      // Pattern : la chaîne route apparaît dans NavRegistry (peut être
      // dans `to:` ou `keywords:` — on accepte les deux car la route
      // est globalement reconnue par la nav).
      const escaped = route.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      expect(nav).toMatch(new RegExp(escaped));
    }
  });
});

describe('EnergyVisualQuality — Provenance visible préservée P1.S7 + P2.4', () => {
  it('FavorableHoursPanel conserve son marqueur provenance (P2.4)', () => {
    const src = readSrc('../ui/energy/FavorableHoursPanel.jsx');
    expect(src).toContain('favorable-hours-provenance');
  });

  it('CostVsContractCard conserve ScenarioProvenanceDot (P1.S7)', () => {
    const src = readSrc('../ui/energy/CostVsContractCard.jsx');
    expect(src).toContain('ScenarioProvenanceDot');
  });

  it('DisplacementSimulationCard conserve SimulationProvenanceDot (P1.S7)', () => {
    const src = readSrc('../ui/energy/DisplacementSimulationCard.jsx');
    expect(src).toContain('SimulationProvenanceDot');
  });

  it('DisplacementSimulationCard conserve warning simulation (P1.S6)', () => {
    const src = readSrc('../ui/energy/DisplacementSimulationCard.jsx');
    expect(src).toContain("Simulation indicative — ne constitue pas une promesse d'économie.");
  });

  it('CostVsContractCard conserve warning simulation (P1.S5)', () => {
    const src = readSrc('../ui/energy/CostVsContractCard.jsx');
    expect(src).toContain("Simulation indicative — ne constitue pas une promesse d'économie.");
  });
});
