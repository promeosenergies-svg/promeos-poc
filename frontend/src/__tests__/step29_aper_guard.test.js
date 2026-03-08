/**
 * PROMEOS — Step 29 source-guard : APER page + API + glossary + nav
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';

const root = join(__dirname, '..', '..');

function readSrc(relPath) {
  return readFileSync(join(root, 'src', relPath), 'utf-8');
}

// ── A. AperPage exists and has key elements ─────────────────────────────

describe('AperPage', () => {
  const src = readSrc('pages/AperPage.jsx');

  it('file exists and is non-empty', () => {
    expect(src.length).toBeGreaterThan(100);
  });

  it('contains production / MWh / kWh references', () => {
    expect(src).toMatch(/production|MWh|kWh/i);
  });

  it('uses BarChart from recharts', () => {
    expect(src).toMatch(/BarChart/);
  });

  it('imports getAperDashboard and getAperEstimate', () => {
    expect(src).toMatch(/getAperDashboard/);
    expect(src).toMatch(/getAperEstimate/);
  });

  it('displays eligible sites', () => {
    expect(src).toMatch(/eligible/i);
  });

  it('shows CO2 data', () => {
    expect(src).toMatch(/co2|CO2/i);
  });
});

// ── B. App.jsx has the route ────────────────────────────────────────────

describe('App.jsx route', () => {
  const src = readSrc('App.jsx');

  it('contains /conformite/aper route', () => {
    expect(src).toMatch(/conformite\/aper/);
  });

  it('imports AperPage', () => {
    expect(src).toMatch(/AperPage/);
  });
});

// ── C. NavRegistry integration ─────────────────────────────────────────

describe('NavRegistry', () => {
  const src = readSrc('layout/NavRegistry.js');

  it('has /conformite/aper in ROUTE_MODULE_MAP', () => {
    expect(src).toMatch(/\/conformite\/aper/);
  });

  it('has Solarisation label', () => {
    expect(src).toMatch(/Solarisation/);
  });
});

// ── D. API functions ────────────────────────────────────────────────────

describe('API functions', () => {
  const src = readSrc('services/api.js');

  it('has getAperDashboard', () => {
    expect(src).toMatch(/getAperDashboard/);
  });

  it('has getAperEstimate', () => {
    expect(src).toMatch(/getAperEstimate/);
  });

  it('uses /aper/ endpoint', () => {
    expect(src).toMatch(/\/aper\//);
  });
});

// ── E. Glossary entries ─────────────────────────────────────────────────

describe('Glossary', () => {
  const src = readSrc('ui/glossary.js');

  it('has aper entry', () => {
    expect(src).toMatch(/aper:/);
  });

  it('has production_pv entry', () => {
    expect(src).toMatch(/production_pv:/);
  });
});
