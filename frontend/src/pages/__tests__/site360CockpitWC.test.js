/**
 * site360CockpitWC.test.js — Cockpit World-Class source guards
 *
 * Verifies 4 features added to Site360:
 *   A. Scores header labellisés (compliance, data quality, completeness)
 *   B. Breadcrumb cliquable (Org > Entité > Portefeuille > Site)
 *   C. Intensité vs benchmark dans TabResume
 *   D. Bloc Accès rapide cross-module
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import path from 'path';

const src = (rel) => readFileSync(path.resolve(__dirname, '..', '..', rel), 'utf8');

const SITE360 = src('pages/Site360.jsx');
const BENCHMARKS = src('utils/benchmarks.js');

// ── A. Scores header labellisés ─────────────────────────────────────────

describe('A. Scores header — compliance, data quality, completeness', () => {
  test('fetches compliance score from API', () => {
    expect(SITE360).toMatch(/\/api\/compliance\/sites\/.*\/score/);
  });

  test('has compliance-score-badge with grade letter', () => {
    expect(SITE360).toMatch(/data-testid="compliance-score-badge"/);
    expect(SITE360).toMatch(/getComplianceGrade/);
    expect(SITE360).toMatch(/getComplianceScoreColor/);
  });

  test('displays score /100 format', () => {
    expect(SITE360).toMatch(/\/100/);
  });

  test('has DataQualityBadge component', () => {
    expect(SITE360).toMatch(/DataQualityBadge/);
    expect(SITE360).toMatch(/getDataQualityScore/);
  });

  test('has completeness badge with level-based colors', () => {
    expect(SITE360).toMatch(/data-testid="completeness-badge"/);
    expect(SITE360).toMatch(/getSiteCompleteness/);
    expect(SITE360).toMatch(/[Cc]omplétude|completeness/);
  });

  test('has dq-partial-banner when score < 50', () => {
    expect(SITE360).toMatch(/data-testid="dq-partial-banner"/);
    expect(SITE360).toMatch(/dataQuality\.score < 50/);
  });

  test('has freshness-expired-banner', () => {
    expect(SITE360).toMatch(/data-testid="freshness-expired-banner"/);
    expect(SITE360).toMatch(/staleness_days/);
  });
});

// ── B. Breadcrumb cliquable ─────────────────────────────────────────────

describe("B. Breadcrumb cliquable (Fil d'Ariane)", () => {
  test('has nav element with aria-label', () => {
    expect(SITE360).toMatch(/aria-label="Fil d'Ariane"/);
  });

  test('links back to /patrimoine', () => {
    expect(SITE360).toMatch(/to="\/patrimoine"/);
  });

  test('shows organisation_nom in breadcrumb', () => {
    expect(SITE360).toMatch(/organisation_nom.*Patrimoine/s);
  });

  test('shows entite_juridique_nom conditionally', () => {
    expect(SITE360).toMatch(/site\.entite_juridique_nom/);
  });

  test('shows portefeuille_nom conditionally', () => {
    expect(SITE360).toMatch(/site\.portefeuille_nom/);
  });

  test('uses ChevronRight separators', () => {
    expect(SITE360).toMatch(/ChevronRight/);
  });

  test('ends with site.nom as non-link', () => {
    // The last breadcrumb item is a span (not a Link) with site.nom
    expect(SITE360).toMatch(/<span className="font-medium text-gray-800">\{site\.nom\}<\/span>/);
  });
});

// ── C. Intensité vs benchmark dans TabResume ────────────────────────────

describe('C. Intensité vs benchmark dans TabResume', () => {
  test('imports getBenchmark from utils', () => {
    expect(SITE360).toMatch(/import.*getBenchmark.*from.*benchmarks/);
  });

  test('calculates intensity = conso / surface', () => {
    expect(SITE360).toMatch(/conso_kwh_an.*\/.*surface_m2/);
  });

  test('calls getBenchmark(site.usage)', () => {
    expect(SITE360).toMatch(/getBenchmark\(site\.usage\)/);
  });

  test('shows ratio vs benchmark OID', () => {
    expect(SITE360).toMatch(/benchmark OID/);
  });

  test('has color-coded bar (green/amber/red)', () => {
    expect(SITE360).toMatch(/bg-green-500/);
    expect(SITE360).toMatch(/bg-amber-500/);
    expect(SITE360).toMatch(/bg-red-500/);
  });

  test('threshold: green <= 1x, amber <= 1.5x, red > 1.5x', () => {
    expect(SITE360).toMatch(/intensityRatio <= 1.*green/s);
    expect(SITE360).toMatch(/intensityRatio <= 1\.5.*amber/s);
  });

  test('displays kWh/m² unit', () => {
    expect(SITE360).toMatch(/kWh\/m²/);
  });

  test('intensity is integrated in header KPI cards (kWh/m² + OID)', () => {
    expect(SITE360).toMatch(/kWh\/m²/);
    expect(SITE360).toMatch(/OID/);
  });
});

describe('C.2 Benchmarks module', () => {
  test('exports OID_BENCHMARKS with key usages', () => {
    expect(BENCHMARKS).toMatch(/bureau:\s*210/);
    expect(BENCHMARKS).toMatch(/hotellerie:\s*280/);
    expect(BENCHMARKS).toMatch(/commerce:\s*330/);
    expect(BENCHMARKS).toMatch(/sante:\s*250/);
  });

  test('exports getBenchmark function', () => {
    expect(BENCHMARKS).toMatch(/export function getBenchmark/);
  });

  test('has default fallback', () => {
    expect(BENCHMARKS).toMatch(/default:\s*210/);
  });
});

// ── D. Bloc Accès rapide cross-module ───────────────────────────────────

describe('D. Bloc Accès rapide cross-module', () => {
  test('has Accès rapide section title', () => {
    expect(SITE360).toMatch(/Accès rapide/);
  });

  test('links to Bill Intelligence with site_id', () => {
    expect(SITE360).toMatch(/to: 'billing'.*label: 'Bill Intelligence'/s);
  });

  test('builds URLs with site_id param', () => {
    expect(SITE360).toMatch(/\/\$\{to\}\?site_id=\$\{site\.id\}/);
  });

  test('links to Conformité with site_id', () => {
    expect(SITE360).toMatch(/to: 'conformite'.*label: 'Conformité'/s);
  });

  test('links to Radar contrats (achat-assistant) with site_id', () => {
    expect(SITE360).toMatch(/to: 'achat-assistant'.*label: 'Radar contrats'/s);
  });

  test('links to Actions with site_id', () => {
    expect(SITE360).toMatch(/to: 'actions'.*label: 'Actions'/s);
  });

  test('uses grid layout for quick access links', () => {
    expect(SITE360).toMatch(/grid grid-cols-2/);
  });
});
