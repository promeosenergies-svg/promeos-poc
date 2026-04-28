/**
 * PROMEOS UI Rescue Sprint — Source-guard tests
 * Validates KPI value-first system, layout robustness, formatter consistency,
 * label overflow rules, and French microcopy.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

function src(rel) {
  return readFileSync(resolve(__dirname, '..', '..', rel), 'utf-8');
}

// ── P0-3: KPI Value-First — no truncation on values ─────────────────────

describe('P0-3: KPI value-first — no truncate on numeric values', () => {
  it('KpiCard value uses break-words, not truncate', () => {
    const code = src('ui/KpiCard.jsx');
    // The main value line should NOT have truncate but should have break-words
    expect(code).toMatch(/text-2xl.*font-bold.*break-words/);
    expect(code).not.toMatch(/text-2xl.*font-bold.*truncate/);
  });

  it('ConsoKpiHeader KpiTile value uses break-words', () => {
    const code = src('components/ConsoKpiHeader.jsx');
    expect(code).toMatch(/text-base.*font-bold.*break-words/);
  });

  it('ConsoKpiHeader label uses line-clamp-2 (not whitespace-nowrap)', () => {
    const code = src('components/ConsoKpiHeader.jsx');
    expect(code).not.toMatch(/label[\s\S]{0,100}whitespace-nowrap/);
    expect(code).toMatch(/line-clamp-2/);
  });

  // Phase 0.2 (sprint Cockpit dual sol2) : ExecutiveKpiRow décommissionné —
  // remplacé par <KpiTriptyqueEnergetique> (Pilotage) et <KpiTriptyqueHybride>
  // (Synthèse stratégique) en Phase 2.1 (cf docs/maquettes/cockpit-sol2/).

  it('EssentialsRow value uses break-words', () => {
    const code = src('pages/cockpit/EssentialsRow.jsx');
    expect(code).toMatch(/font-bold.*text-gray-900.*break-words/);
  });

  // Phase 0.3 (sprint Cockpit dual sol2) : ImpactDecisionPanel décommissionné —
  // remplacé par <DecisionsTopThree> (3 décisions arbitrales narrées)
  // sur la page Synthèse stratégique en Phase 2.3 (cf docs/maquettes/cockpit-sol2/).
});

// ── P0-5: Performance page layout — responsive grid ─────────────────────

describe('P0-5: Performance page layout', () => {
  const code = src('pages/MonitoringPage.jsx');

  it('Executive summary uses xl:grid-cols-5 (not lg:)', () => {
    expect(code).toMatch(/xl:grid-cols-5/);
  });

  it('KPI strip uses xl:grid-cols-4 (not lg:)', () => {
    expect(code).toMatch(/xl:grid-cols-4/);
  });

  it('KPI card titles use line-clamp-2', () => {
    expect(code).toMatch(/line-clamp-2[\s\S]*?\{c\.title\}/);
  });

  it('KPI card values use break-words', () => {
    expect(code).toMatch(/break-words[\s\S]*?\{c\.value\}/);
  });
});

// ── P0-5: PageShell subtitle uses line-clamp-2 ─────────────────────────

describe('P0-5: PageShell layout robustness', () => {
  const code = src('ui/PageShell.jsx');

  it('subtitle has line-clamp-2', () => {
    expect(code).toMatch(/line-clamp-2.*subtitle|subtitle[\s\S]*?line-clamp-2/);
  });

  it('title section has min-width for readability', () => {
    expect(code).toMatch(/minWidth.*280/);
  });

  it('header uses flex-wrap', () => {
    expect(code).toMatch(/flex-wrap/);
  });
});

// ── P0-4: Formatter unification ─────────────────────────────────────────

describe('P0-4: Centralized formatters', () => {
  const code = src('utils/format.js');

  it('exports fmtKwh with auto-scaling (kWh/MWh/GWh)', () => {
    expect(code).toMatch(/export function fmtKwh/);
    expect(code).toContain('GWh');
    expect(code).toContain('MWh');
    expect(code).toContain('kWh');
  });

  it('exports fmtEur with auto-scaling (€/k€/M€)', () => {
    expect(code).toMatch(/export function fmtEur/);
    expect(code).toContain('M€');
    expect(code).toContain('k€');
  });

  it('exports fmtKw with auto-scaling', () => {
    expect(code).toMatch(/export function fmtKw/);
  });

  it('has guard against NaN/Infinity', () => {
    expect(code).toMatch(/isFinite/);
  });

  it('ConsoKpiHeader uses centralized fmtKwh', () => {
    const consoCode = src('components/ConsoKpiHeader.jsx');
    expect(consoCode).toContain('fmtKwh');
  });
});

// ── P0-6: French microcopy — accent fixes ───────────────────────────────

describe('P0-6: French accent correctness', () => {
  it('DataQualityWidget uses "Qualité des données"', () => {
    const code = src('pages/cockpit/DataQualityWidget.jsx');
    expect(code).toContain('Qualité des données');
    expect(code).not.toContain('Qualite des donnees');
  });

  it('DataQualityWidget uses "Voir le détail"', () => {
    const code = src('pages/cockpit/DataQualityWidget.jsx');
    expect(code).toContain('Voir le détail');
  });

  it('PurchasePage uses "Budget de référence" (not "Budget baseline")', () => {
    const code = src('pages/PurchasePage.jsx');
    expect(code).toContain('Budget de référence');
    expect(code).not.toContain('Budget baseline');
  });

  it('PurchasePage uses "Délai de préavis" (not "Deadline preavis")', () => {
    const code = src('pages/PurchasePage.jsx');
    expect(code).toContain('Délai de préavis');
    expect(code).not.toContain('Deadline preavis');
  });

  it('PurchasePage uses "Renouvellement auto" (not "Auto-renew")', () => {
    const code = src('pages/PurchasePage.jsx');
    expect(code).toContain('Renouvellement auto');
    expect(code).not.toContain('Auto-renew');
  });
});

// ── P0-6: ConsoKpiHeader grid responsive ────────────────────────────────

describe('P0-6: ConsoKpiHeader responsive grid', () => {
  const code = src('components/ConsoKpiHeader.jsx');

  it('uses flex-wrap inline strip layout for compact display (#90)', () => {
    expect(code).toMatch(/flex flex-wrap/);
  });
});
