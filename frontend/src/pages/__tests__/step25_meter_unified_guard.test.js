/**
 * Step 25 — Unification Compteur → Meter (source guards)
 */
import { describe, test, expect } from 'vitest';
import fs from 'fs';

const readFront = (...parts) => fs.readFileSync(`src/${parts.join('/')}`, 'utf8');
const readBack = (...parts) => fs.readFileSync(`../backend/${parts.join('/')}`, 'utf8');

// ── A. Backend — meter_unified_service ────────────────────────────────────

describe('A. meter_unified_service', () => {
  test('service file exists', () => {
    expect(fs.existsSync('../backend/services/meter_unified_service.py')).toBe(true);
  });

  test('exports get_site_meters', () => {
    const src = readBack('services', 'meter_unified_service.py');
    expect(src).toContain('def get_site_meters');
  });

  test('handles legacy compteur fallback', () => {
    const src = readBack('services', 'meter_unified_service.py');
    expect(src).toContain('compteur_legacy');
  });

  test('deduplicates by numero_serie and meter_id', () => {
    const src = readBack('services', 'meter_unified_service.py');
    expect(src).toContain('meter_serials');
    expect(src).toContain('meter_prms');
  });
});

// ── B. Backend — Meter model enriched ─────────────────────────────────────

describe('B. Meter model enriched', () => {
  test('has parent_meter_id', () => {
    const src = readBack('models', 'energy_models.py');
    expect(src).toContain('parent_meter_id');
  });

  test('has delivery_point_id', () => {
    const src = readBack('models', 'energy_models.py');
    expect(src).toContain('delivery_point_id');
  });

  test('has numero_serie', () => {
    const src = readBack('models', 'energy_models.py');
    expect(src).toMatch(/numero_serie.*Column/);
  });

  test('has type_compteur', () => {
    const src = readBack('models', 'energy_models.py');
    expect(src).toMatch(/type_compteur.*Column/);
  });

  test('has sub_meters relationship', () => {
    const src = readBack('models', 'energy_models.py');
    expect(src).toContain('sub_meters');
  });
});

// ── C. Patrimoine routes integration ──────────────────────────────────────

describe('C. Patrimoine routes integration', () => {
  test('imports unified service', () => {
    const src = readBack('routes', 'patrimoine.py');
    expect(src).toContain('meter_unified_service');
  });

  test('has /meters endpoint', () => {
    const src = readBack('routes', 'patrimoine.py');
    expect(src).toContain('/meters');
  });

  test('serialized compteur has source field', () => {
    const src = readBack('routes', 'patrimoine.py');
    expect(src).toContain('"source"');
  });
});

// ── D. Activation dual-write ──────────────────────────────────────────────

describe('D. Activation dual-write', () => {
  test('patrimoine_service creates Meter', () => {
    const src = readBack('services', 'patrimoine_service.py');
    expect(src).toContain('Meter(');
  });

  test('patrimoine_service imports Meter', () => {
    const src = readBack('services', 'patrimoine_service.py');
    expect(src).toContain('Meter');
  });
});

// ── E. Frontend — MeterSourceBadge ────────────────────────────────────────

describe('E. MeterSourceBadge component', () => {
  test('file exists', () => {
    expect(fs.existsSync('src/components/MeterSourceBadge.jsx')).toBe(true);
  });

  test('has EMS and Import labels', () => {
    const src = readFront('components', 'MeterSourceBadge.jsx');
    expect(src).toContain('EMS');
    expect(src).toContain('Import');
  });

  test('handles meter and compteur_legacy sources', () => {
    const src = readFront('components', 'MeterSourceBadge.jsx');
    expect(src).toContain('meter');
    expect(src).toContain('compteur_legacy');
  });
});

// ── F. Frontend — Patrimoine integration ──────────────────────────────────

describe('F. Patrimoine integration', () => {
  test('imports MeterSourceBadge', () => {
    const src = readFront('pages', 'Patrimoine.jsx');
    expect(src).toContain('MeterSourceBadge');
  });

  test('imports patrimoineSiteMeters', () => {
    const src = readFront('pages', 'Patrimoine.jsx');
    expect(src).toContain('patrimoineSiteMeters');
  });

  test('api.js exports patrimoineSiteMeters', () => {
    const src = readFront('services', 'api.js');
    expect(src).toContain('patrimoineSiteMeters');
  });
});

// ── G. Migration ──────────────────────────────────────────────────────────

describe('G. Migration', () => {
  test('migration adds meter unified columns', () => {
    const src = readBack('database', 'migrations.py');
    expect(src).toContain('_add_meter_unified_columns');
  });

  test('migration adds parent_meter_id', () => {
    const src = readBack('database', 'migrations.py');
    expect(src).toContain('parent_meter_id');
  });
});
