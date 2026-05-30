// @vitest-environment jsdom
/**
 * PROMEOS — Tests MonitoringPageSplit (Sprint P2.1).
 *
 * Vérifie statiquement le split de MonitoringPage.jsx :
 * 1. Composant `ClimateScatter` inline retiré.
 * 2. Import `MonitoringClimateScatter` ajouté.
 * 3. Référence `<MonitoringClimateScatter climate={climate} />` présente.
 * 4. Import `computeConfidence` redirigé vers
 *    `pages/monitoring/monitoringConfidenceHelper`.
 * 5. Re-export `computeConfidence` préservé (rétro-compat tests).
 * 6. Fichier `utils/confidenceDisplay.js` supprimé effectivement.
 * 7. Helper `monitoringConfidenceHelper.js` créé sous pages/monitoring/.
 * 8. HELPER_WHITELIST source-guard réduite à 2 entrées documentées.
 */
import { describe, expect, it } from 'vitest';
import { existsSync, readFileSync } from 'fs';
import { resolve } from 'path';

function readSrc(rel) {
  return readFileSync(resolve(__dirname, rel), 'utf8');
}

describe('MonitoringPageSplit — Composant ClimateScatter extrait', () => {
  it('Composant inline `function ClimateScatter` retiré de MonitoringPage', () => {
    const src = readSrc('../pages/MonitoringPage.jsx');
    expect(src).not.toMatch(/function\s+ClimateScatter\s*\(/);
  });

  it('Import `MonitoringClimateScatter` depuis pages/monitoring/', () => {
    const src = readSrc('../pages/MonitoringPage.jsx');
    expect(src).toMatch(
      /import\s+MonitoringClimateScatter\s+from\s+['"]\.\/monitoring\/MonitoringClimateScatter['"]/
    );
  });

  it('Référence `<MonitoringClimateScatter climate={climate} />` présente', () => {
    const src = readSrc('../pages/MonitoringPage.jsx');
    expect(src).toMatch(/<MonitoringClimateScatter\s+climate=\{climate\}\s*\/>/);
  });

  it('Aucune référence résiduelle à `<ClimateScatter `', () => {
    const src = readSrc('../pages/MonitoringPage.jsx');
    expect(src).not.toMatch(/<ClimateScatter\s/);
  });
});

describe('MonitoringPageSplit — confidenceDisplay supprimé et déplacé', () => {
  it('Fichier utils/confidenceDisplay.js SUPPRIMÉ effectivement', () => {
    expect(existsSync(resolve(__dirname, '../utils/confidenceDisplay.js'))).toBe(false);
  });

  it('Helper monitoringConfidenceHelper.js créé sous pages/monitoring/', () => {
    expect(
      existsSync(resolve(__dirname, '../pages/monitoring/monitoringConfidenceHelper.js'))
    ).toBe(true);
  });

  it('Helper documente P2.1 et exporte computeConfidence', () => {
    const src = readSrc('../pages/monitoring/monitoringConfidenceHelper.js');
    expect(src).toMatch(/P2\.1/);
    expect(src).toMatch(/déplacé/i);
    expect(src).toMatch(/export\s+function\s+computeConfidence/);
  });

  it('MonitoringPage importe computeConfidence depuis le nouveau path', () => {
    const src = readSrc('../pages/MonitoringPage.jsx');
    expect(src).toMatch(
      /import\s+\{\s*computeConfidence\s*\}\s+from\s+['"]\.\/monitoring\/monitoringConfidenceHelper['"]/
    );
    // Plus aucune référence à l'ancien path `utils/confidenceDisplay`
    expect(src).not.toMatch(/from\s+['"]\.\.\/utils\/confidenceDisplay['"]/);
  });

  it('MonitoringPage préserve le re-export `computeConfidence` (rétro-compat tests)', () => {
    const src = readSrc('../pages/MonitoringPage.jsx');
    expect(src).toMatch(/export\s*\{\s*computeConfidence\s*\}/);
  });
});

describe('MonitoringPageSplit — HELPER_WHITELIST réduite 3 → 2 entrées', () => {
  it("Source-guard backend retire l'entrée utils/confidenceDisplay.js", () => {
    const { readFileSync: rfs } = require('fs');
    const { resolve: r } = require('path');
    const src = rfs(
      r(
        __dirname,
        '../../../backend/tests/source_guards/test_frontend_no_business_calc_source_guards.py'
      ),
      'utf8'
    );
    // L'entrée confidenceDisplay.js n'apparaît plus comme clé de
    // HELPER_WHITELIST (mais peut apparaître dans des commentaires
    // documentant le retrait).
    expect(src).not.toMatch(/"frontend\/src\/utils\/confidenceDisplay\.js":\s*\(/);
    // Les 2 entrées restantes sont préservées
    expect(src).toMatch(/"frontend\/src\/utils\/co2\.js":\s*\(/);
    expect(src).toMatch(/"frontend\/src\/utils\/scopedAggregates\.js":\s*\(/);
  });
});

describe('MonitoringPageSplit — comportement utilisateur préservé', () => {
  it('Tous les imports MonitoringPage existants restent (pas de massive refactor)', () => {
    const src = readSrc('../pages/MonitoringPage.jsx');
    // Imports clés MonitoringPage qui ne doivent PAS bouger
    expect(src).toContain('useScope');
    expect(src).toContain('SolBriefingHead');
    expect(src).toContain('MonitoringSynthesisStrip');
  });

  it('Les constantes CLIMATE_REASONS / CLIMATE_LABEL_FR restent exportées par MonitoringPage', () => {
    // Évite régression d'usage externe : si d'autres modules consomment
    // ces constantes depuis MonitoringPage, on les garde exportées même
    // si elles sont aussi dans le composant extrait.
    const src = readSrc('../pages/MonitoringPage.jsx');
    expect(src).toMatch(/export\s+const\s+CLIMATE_REASONS\s*=/);
    expect(src).toMatch(/export\s+const\s+CLIMATE_LABEL_FR\s*=/);
  });
});

describe('MonitoringPage — Sprint P2.2 cross-links transverses', () => {
  it('MonitoringPage importe EnergyCrossLinks', () => {
    const src = readSrc('../pages/MonitoringPage.jsx');
    expect(src).toMatch(
      /import\s+EnergyCrossLinks\s+from\s+['"]\.\.\/ui\/energy\/EnergyCrossLinks['"]/
    );
  });

  it('Constante MONITORING_CROSS_LINKS déclare les 2 liens canoniques', () => {
    const src = readSrc('../pages/MonitoringPage.jsx');
    expect(src).toMatch(/MONITORING_CROSS_LINKS\s*=\s*\[/);
    expect(src).toContain("'/action-center-v4'");
    expect(src).toContain("'Créer une action'");
    expect(src).toContain("'/conformite/tertiaire'");
    expect(src).toContain("'Voir trajectoire Décret Tertiaire'");
  });

  it('EnergyCrossLinks rendu avec testId="monitoring-cross-links"', () => {
    const src = readSrc('../pages/MonitoringPage.jsx');
    expect(src).toMatch(
      /<EnergyCrossLinks\s+links=\{MONITORING_CROSS_LINKS\}\s+testId="monitoring-cross-links"\s*\/>/
    );
  });

  it('Cross-links rendus APRÈS MonitoringSynthesisStrip (pied de synthèse)', () => {
    const src = readSrc('../pages/MonitoringPage.jsx');
    const stripIdx = src.indexOf('<MonitoringSynthesisStrip');
    const crossIdx = src.indexOf('<EnergyCrossLinks');
    expect(stripIdx).toBeGreaterThan(0);
    expect(crossIdx).toBeGreaterThan(stripIdx);
  });
});
