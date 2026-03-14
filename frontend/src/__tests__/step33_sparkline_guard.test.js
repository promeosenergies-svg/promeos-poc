/**
 * PROMEOS — Step 33 source-guard : Score trend sparkline
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

const src = join(__dirname, '..');
const sparklinePath = join(src, 'ui', 'Sparkline.jsx');
const cockpitPath = join(src, 'pages', 'Cockpit.jsx');
const execKpiPath = join(src, 'pages', 'cockpit', 'ExecutiveKpiRow.jsx');
const apiPath = join(src, 'services', 'api.js');

function read(p) {
  return existsSync(p) ? readFileSync(p, 'utf-8') : null;
}

describe('Step 33 — Sparkline component', () => {
  const src = read(sparklinePath);

  it('Sparkline component exists', () => {
    expect(src).not.toBeNull();
  });

  it('uses Recharts LineChart', () => {
    expect(src).toMatch(/LineChart/);
    expect(src).toMatch(/recharts/);
  });

  it('has ResponsiveContainer', () => {
    expect(src).toMatch(/ResponsiveContainer/);
  });

  it('has tooltip', () => {
    expect(src).toMatch(/Tooltip/);
  });

  it('supports data/color/width/height props', () => {
    expect(src).toMatch(/data/);
    expect(src).toMatch(/color/);
    expect(src).toMatch(/width/);
    expect(src).toMatch(/height/);
  });
});

describe('Step 33 — Cockpit integration', () => {
  const src = read(cockpitPath);

  it('imports getComplianceScoreTrend', () => {
    expect(src).toMatch(/getComplianceScoreTrend/);
  });

  it('has scoreTrend state', () => {
    expect(src).toMatch(/scoreTrend/);
    expect(src).toMatch(/setScoreTrend/);
  });

  it('fetches score-trend on org change', () => {
    expect(src).toMatch(/getComplianceScoreTrend/);
    expect(src).toMatch(/org\?\.id/);
  });

  it('passes scoreTrend to ExecutiveKpiRow', () => {
    expect(src).toMatch(/scoreTrend.*ExecutiveKpiRow|ExecutiveKpiRow.*scoreTrend/s);
  });
});

describe('Step 33 — ExecutiveKpiRow sparkline', () => {
  const src = read(execKpiPath);

  it('accepts scoreTrend prop', () => {
    expect(src).toMatch(/scoreTrend/);
  });

  it('shows trend text for conformite KPI', () => {
    expect(src).toMatch(/conformite/);
    expect(src).toMatch(/→/);
    expect(src).toMatch(/mois/);
  });

  it('has conformite-sparkline testid', () => {
    expect(src).toMatch(/conformite-sparkline/);
  });
});

describe('Step 33 — API function', () => {
  const src = read(apiPath);

  it('has getComplianceScoreTrend', () => {
    expect(src).toMatch(/getComplianceScoreTrend/);
  });

  it('calls score-trend endpoint', () => {
    expect(src).toMatch(/score-trend/);
  });
});
