/**
 * Step 26 — Sous-compteurs (source guards)
 */
import { describe, test, expect } from 'vitest';
import fs from 'fs';

const readFront = (...parts) => fs.readFileSync(`src/${parts.join('/')}`, 'utf8');
const readBack = (...parts) => fs.readFileSync(`../backend/${parts.join('/')}`, 'utf8');

// ── A. Backend — meter_unified_service tree & sub-meters ──────────────────

describe('A. meter_unified_service sub-meters', () => {
  test('has get_site_meters_tree', () => {
    const src = readBack('services', 'meter_unified_service.py');
    expect(src).toContain('def get_site_meters_tree');
  });

  test('has create_sub_meter', () => {
    const src = readBack('services', 'meter_unified_service.py');
    expect(src).toContain('def create_sub_meter');
  });

  test('has delete_sub_meter', () => {
    const src = readBack('services', 'meter_unified_service.py');
    expect(src).toContain('def delete_sub_meter');
  });

  test('has get_meter_breakdown', () => {
    const src = readBack('services', 'meter_unified_service.py');
    expect(src).toContain('def get_meter_breakdown');
  });

  test('enforces 1 level max', () => {
    const src = readBack('services', 'meter_unified_service.py');
    expect(src).toContain('1 niveau max');
  });
});

// ── B. Backend — patrimoine routes ────────────────────────────────────────

describe('B. Patrimoine routes sub-meters', () => {
  test('has tree endpoint', () => {
    const src = readBack('routes', 'patrimoine.py');
    expect(src).toContain('/meters/tree');
  });

  test('has sub-meters POST endpoint', () => {
    const src = readBack('routes', 'patrimoine.py');
    expect(src).toContain('sub-meters');
  });

  test('has breakdown endpoint', () => {
    const src = readBack('routes', 'patrimoine.py');
    expect(src).toContain('breakdown');
  });
});

// ── C. Seed — packs has sub_meters ───────────────────────────────────────

describe('C. Seed sub-meters', () => {
  test('packs.py has sub_meters config', () => {
    const src = readBack('services', 'demo_seed', 'packs.py');
    expect(src).toContain('sub_meters');
  });

  test('gen_master.py creates sub-meters', () => {
    const src = readBack('services', 'demo_seed', 'gen_master.py');
    expect(src).toContain('parent_meter_id');
  });

  test('gen_readings.py has sub-meter readings', () => {
    const src = readBack('services', 'demo_seed', 'gen_readings.py');
    expect(src).toContain('generate_sub_meter_readings');
  });
});

// ── D. Frontend — API functions ──────────────────────────────────────────

describe('D. Frontend API functions', () => {
  test('api.js exports getSiteMetersTree', () => {
    const src = readFront('services', 'api.js');
    expect(src).toContain('getSiteMetersTree');
  });

  test('api.js exports createSubMeter', () => {
    const src = readFront('services', 'api.js');
    expect(src).toContain('createSubMeter');
  });

  test('api.js exports getMeterBreakdown', () => {
    const src = readFront('services', 'api.js');
    expect(src).toContain('getMeterBreakdown');
  });
});

// ── E. Frontend — Patrimoine tree view ───────────────────────────────────

describe('E. Patrimoine tree view', () => {
  test('imports getSiteMetersTree', () => {
    const src = readFront('pages', 'Patrimoine.jsx');
    expect(src).toContain('getSiteMetersTree');
  });

  test('has sub_meters rendering', () => {
    const src = readFront('pages', 'Patrimoine.jsx');
    expect(src).toContain('sub_meters');
  });

  test('has add sub-meter form', () => {
    const src = readFront('pages', 'Patrimoine.jsx');
    expect(src).toContain('createSubMeter');
  });
});

// ── F. MeterBreakdownChart component ─────────────────────────────────────

describe('F. MeterBreakdownChart', () => {
  test('file exists', () => {
    expect(fs.existsSync('src/components/MeterBreakdownChart.jsx')).toBe(true);
  });

  test('uses PieChart from recharts', () => {
    const src = readFront('components', 'MeterBreakdownChart.jsx');
    expect(src).toContain('PieChart');
  });

  test('renders delta label', () => {
    const src = readFront('components', 'MeterBreakdownChart.jsx');
    expect(src).toContain('delta_label');
  });
});

// ── G. Glossary entry ────────────────────────────────────────────────────

describe('G. Glossary', () => {
  test('has sous_compteur entry', () => {
    const src = readFront('ui', 'glossary.js');
    expect(src).toContain('sous_compteur');
  });
});
