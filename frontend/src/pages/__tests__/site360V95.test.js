/**
 * site360V95.test.js — V95 "Patrimoine World-Class Closure" source guards
 *
 * Verifies:
 *   A. Site360 uses real API data (no mockAnomalies)
 *   B. Import page marked as legacy, hidden from nav
 *   C. Backend import hardened (MIME, _parse_surface)
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import path from 'path';

const src = (rel) => readFileSync(path.resolve(__dirname, '..', '..', rel), 'utf8');
const backend = (rel) => readFileSync(path.resolve(__dirname, '..', '..', '..', '..', 'backend', rel), 'utf8');

const SITE360     = src('pages/Site360.jsx');
const NAV_REG     = src('layout/NavRegistry.js');
const NAV_PANEL   = src('layout/NavPanel.jsx');
const IMPORT_PAGE = src('pages/ImportPage.jsx');
const IMPORT_PY   = backend('routes/import_sites.py');

// ── A. Site360 — real anomalies data ─────────────────────────────────────

describe('A. Site360 — real anomalies', () => {
  test('no more mockAnomalies', () => {
    expect(SITE360).not.toMatch(/mockAnomalies/);
  });

  test('imports getPatrimoineAnomalies from API', () => {
    expect(SITE360).toMatch(/getPatrimoineAnomalies/);
  });

  test('has useEffect that calls getPatrimoineAnomalies', () => {
    expect(SITE360).toMatch(/useEffect/);
    expect(SITE360).toMatch(/getPatrimoineAnomalies\(site\.id\)/);
  });

  test('has loading state for anomalies', () => {
    expect(SITE360).toMatch(/anomLoading/);
  });

  test('maps real API fields (anomaly_type, title_fr, business_impact)', () => {
    expect(SITE360).toMatch(/anomaly_type/);
    expect(SITE360).toMatch(/title_fr/);
    expect(SITE360).toMatch(/business_impact/);
  });
});

// ── B. Import Legacy + nav hiding ────────────────────────────────────────

describe('B. Import legacy + nav', () => {
  test('NavRegistry /import item has hidden: true', () => {
    expect(NAV_REG).toMatch(/to:\s*'\/import'.*hidden:\s*true/s);
  });

  test('NavPanel filters hidden items', () => {
    expect(NAV_PANEL).toMatch(/\.hidden/);
  });

  test('ImportPage has legacy banner', () => {
    expect(IMPORT_PAGE).toMatch(/legacy|Legacy/i);
  });

  test('Quick action "Importer" points to /patrimoine', () => {
    // The quick action key='import' should now point to /patrimoine
    expect(NAV_REG).toMatch(/key:\s*'import'.*to:\s*'\/patrimoine'/s);
  });
});

// ── C. Backend import hardening ──────────────────────────────────────────

describe('C. Backend import hardening', () => {
  test('has _parse_surface function', () => {
    expect(IMPORT_PY).toMatch(/_parse_surface/);
  });

  test('has MIME / content_type validation', () => {
    expect(IMPORT_PY).toMatch(/content_type/);
  });

  test('has extension validation (.csv, .txt)', () => {
    expect(IMPORT_PY).toMatch(/\.csv.*\.txt|\.txt.*\.csv/s);
  });

  test('has row count warning for large files', () => {
    expect(IMPORT_PY).toMatch(/10000|10_000/);
  });

  test('uses _parse_surface instead of raw float()', () => {
    // _parse_surface should be called on surface_raw
    expect(IMPORT_PY).toMatch(/_parse_surface\(surface_raw\)/);
  });
});
