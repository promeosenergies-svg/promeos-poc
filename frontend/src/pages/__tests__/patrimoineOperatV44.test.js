/**
 * PROMEOS V44 — Patrimoine → OPERAT integration guards
 *
 * 1. Wizard prefills EFA name from site_nom
 * 2. Lever engine deep-links with site_id
 * 3. Surface read-only (unchanged)
 * 4. Backend dedup warning
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const src = (rel) => fs.readFileSync(path.resolve(__dirname, '..', '..', rel), 'utf-8');

const backendSrc = (rel) =>
  fs.readFileSync(path.resolve(__dirname, '..', '..', '..', '..', 'backend', rel), 'utf-8');

// ══════════════════════════════════════════════════════════════════════════════
// 1. Wizard — EFA name prefill from site_nom
// ══════════════════════════════════════════════════════════════════════════════

describe('Wizard V44 prefills EFA name from site_nom', () => {
  const wizard = src('pages/tertiaire/TertiaireWizardPage.jsx');

  it('has prefillSiteId from useSearchParams', () => {
    expect(wizard).toContain('prefillSiteId');
    expect(wizard).toContain("searchParams.get('site_id')");
  });

  it('prefills nom from site name', () => {
    expect(wizard).toContain("updateField('nom'");
    expect(wizard).toContain('targetSite.site_nom');
  });

  it('generates EFA name with site name template', () => {
    expect(wizard).toContain('EFA —');
    expect(wizard).toContain('targetSite.site_nom');
  });

  it('surface is read-only (computed, not editable)', () => {
    expect(wizard).toContain('Surface totale');
    expect(wizard).toContain('totalSurface');
    // No input for surface editing
    expect(wizard).not.toContain("onChange={(e) => updateField('surface");
  });

  it('buildings auto-selected from prefill site', () => {
    expect(wizard).toContain('preselected');
    expect(wizard).toContain("updateField('selectedBuildings'");
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 2. Lever engine — site_id in ctaPath
// ══════════════════════════════════════════════════════════════════════════════

describe('Lever engine V44 deep-links with site_id', () => {
  const engine = src('models/leverEngineModel.js');

  it('has ctaSiteId variable for create-efa lever', () => {
    expect(engine).toContain('ctaSiteId');
  });

  it('builds ctaPath with site_id query param', () => {
    expect(engine).toContain('wizard?site_id=');
    expect(engine).toContain('ctaSiteId');
  });

  it('falls back to /conformite/tertiaire without site_id', () => {
    expect(engine).toContain("'/conformite/tertiaire'");
  });

  it('extracts site_id from sampleSite', () => {
    expect(engine).toContain('sampleSite?.site_id');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 3. Backend — dedup warning
// ══════════════════════════════════════════════════════════════════════════════

describe('Backend V44 dedup warning (source guards)', () => {
  const routes = backendSrc('routes/tertiaire.py');

  it('has dedup_warning logic', () => {
    expect(routes).toContain('dedup_warning');
  });

  it('checks existing_efas for same site', () => {
    expect(routes).toContain('existing_efas');
  });

  it('returns dedup_warning in response', () => {
    expect(routes).toContain('"dedup_warning"');
  });

  it('V44 comment present', () => {
    expect(routes).toContain('V44');
  });

  it('dedup is non-blocking (warning not exception)', () => {
    // dedup_warning should be set but EFA creation proceeds
    expect(routes).toContain('dedup_warning = None');
    expect(routes).toContain('result["dedup_warning"]');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 4. Surface snapshot — still intact from V41
// ══════════════════════════════════════════════════════════════════════════════

describe('Surface snapshot V41 still intact', () => {
  const routes = backendSrc('routes/tertiaire.py');

  it('snapshots surface_m2 from patrimoine batiment', () => {
    expect(routes).toContain('surface_m2=bat.surface_m2');
    expect(routes).toContain('snapshot from patrimoine');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 5. No duplicate data entry — zero manual surface input
// ══════════════════════════════════════════════════════════════════════════════

describe('Zero duplicate data entry (V44 principle)', () => {
  const wizard = src('pages/tertiaire/TertiaireWizardPage.jsx');

  it('surface comes from patrimoine (read-only display)', () => {
    // Surface is computed from selectedBuildings, never user-input
    expect(wizard).toContain('totalSurface');
    expect(wizard).toContain('reduce((s, b) => s + (b.surface_m2 || 0), 0)');
  });

  it('buildings come from catalog (patrimoine)', () => {
    expect(wizard).toContain('getTertiaireCatalog');
    expect(wizard).toContain('catalog.sites');
  });

  it('submit payload sends building_id + usage_label only (no surface)', () => {
    expect(wizard).toContain('building_id: b.building_id');
    expect(wizard).toContain('usage_label: b.usage_label');
  });
});
