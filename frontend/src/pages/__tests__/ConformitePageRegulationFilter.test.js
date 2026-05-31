// @vitest-environment node
/**
 * PROMEOS — Sprint Site360 P1 (2026-05-31).
 * Tests statiques de propagation du `regulationFilter` (chips
 * Décret Tertiaire / BACS / APER / SMÉ-BEGES) dans ConformitePage.jsx.
 *
 * Doctrine : ces tests interdisent la régression du bug où les 4 chips
 * changeaient l'URL mais ne filtraient pas les blocs de synthèse, le
 * bandeau urgence, le parcours et les constats.
 */
import { describe, expect, it } from 'vitest';
const { readFileSync } = require('fs');
const { resolve } = require('path');

const SRC = readFileSync(resolve(__dirname, '../ConformitePage.jsx'), 'utf8');

describe('ConformitePage — propagation regulationFilter (Site360 P1)', () => {
  it('déclare une useMemo `filteredObligationsByRegulation`', () => {
    expect(SRC).toContain('filteredObligationsByRegulation');
    expect(SRC).toContain('REGULATION_FILTER_MAP[regulationFilter]');
  });

  it('déclare une useMemo `filteredActionableFindings`', () => {
    expect(SRC).toContain('filteredActionableFindings');
  });

  it('déclare une useMemo `scoreFiltered` qui dérive du sous-ensemble', () => {
    expect(SRC).toContain('scoreFiltered');
    // Le calcul doit recompter conformes / total sur le subset
    expect(SRC).toMatch(/conformes\s*\/\s*subset\.length/);
  });

  it('déclare une useMemo `timelineFiltered`', () => {
    expect(SRC).toContain('timelineFiltered');
  });

  it('déclare une useMemo `proofsMissingCountFiltered`', () => {
    expect(SRC).toContain('proofsMissingCountFiltered');
  });

  it('passe les versions filtrées à `ConformiteSyntheseCompacte`', () => {
    // La synthèse compacte DOIT consommer scoreFiltered / timelineFiltered /
    // filteredActionableFindings / proofsMissingCountFiltered.
    expect(SRC).toMatch(/score=\{scoreFiltered\}/);
    expect(SRC).toMatch(/nextDeadline=\{timelineFiltered\?\.next_deadline/);
    expect(SRC).toMatch(/actionsCount=\{filteredActionableFindings\.length\}/);
    expect(SRC).toMatch(/proofsMissingCount=\{proofsMissingCountFiltered\}/);
  });

  it('passe les versions filtrées à `ComplianceSummaryBanner`', () => {
    expect(SRC).toMatch(
      /ComplianceSummaryBanner[\s\S]*?score=\{scoreFiltered\}[\s\S]*?timeline=\{timelineFiltered\}/
    );
  });

  it('passe les obligations filtrées à `computeGuidedSteps`', () => {
    expect(SRC).toMatch(/computeGuidedSteps[\s\S]*?obligations:\s*filteredObligationsByRegulation/);
  });

  it('passe les obligations filtrées à `computeNextBestAction`', () => {
    expect(SRC).toMatch(
      /computeNextBestAction[\s\S]*?obligations:\s*filteredObligationsByRegulation/
    );
  });

  it('expose le bandeau visuel « Vue filtrée » avec testid stable', () => {
    expect(SRC).toContain('data-testid="regulation-filter-banner"');
    expect(SRC).toContain('Vue filtrée');
    expect(SRC).toContain('voir toutes les obligations');
    expect(SRC).toContain('data-testid="regulation-filter-clear"');
  });

  it("n'utilise plus `score` / `timeline` / `actionableFindings` bruts pour la synthèse", () => {
    // Vérifie que les anciens props ne réapparaissent pas accidentellement.
    expect(SRC).not.toMatch(
      /<ConformiteSyntheseCompacte[\s\S]*?score=\{score\}[\s\S]*?nextDeadline=\{timeline\?\.next_deadline/
    );
    expect(SRC).not.toMatch(
      /<ComplianceSummaryBanner[\s\S]*?score=\{score\}[\s\S]*?timeline=\{timeline\}/
    );
  });
});
