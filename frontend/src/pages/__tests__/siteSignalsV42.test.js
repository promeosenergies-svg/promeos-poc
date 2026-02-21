/**
 * PROMEOS V42 — Site Signals + Levers + Wizard Prefill guards
 * Source guards : site-signals API, lever engine, lever templates,
 *                 wizard prefill, dashboard section
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const src = (rel) =>
  fs.readFileSync(path.resolve(__dirname, '..', '..', rel), 'utf-8');

const backendSrc = (rel) =>
  fs.readFileSync(
    path.resolve(__dirname, '..', '..', '..', '..', 'backend', rel),
    'utf-8',
  );

// ══════════════════════════════════════════════════════════════════════════════
// 1. API module
// ══════════════════════════════════════════════════════════════════════════════

describe('API exports getTertiaireSiteSignals (V42)', () => {
  const api = src('services/api.js');

  it('exports getTertiaireSiteSignals', () => {
    expect(api).toContain('getTertiaireSiteSignals');
  });

  it('calls /site-signals endpoint', () => {
    expect(api).toContain('/site-signals');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 2. Lever engine — new levers
// ══════════════════════════════════════════════════════════════════════════════

describe('Lever engine has V42 site signal levers', () => {
  const engine = src('models/leverEngineModel.js');

  it('has lev-tertiaire-create-efa lever', () => {
    expect(engine).toContain('lev-tertiaire-create-efa');
  });

  it('has lev-tertiaire-complete-patrimoine lever', () => {
    expect(engine).toContain('lev-tertiaire-complete-patrimoine');
  });

  it('reads _tertiaireSiteSignals from kpis', () => {
    expect(engine).toContain('_tertiaireSiteSignals');
  });

  it('checks uncovered_probable count', () => {
    expect(engine).toContain('uncoveredProbable');
  });

  it('checks incompleteData count', () => {
    expect(engine).toContain('incompleteData');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 3. Lever action templates
// ══════════════════════════════════════════════════════════════════════════════

describe('Lever action templates have V42 entries', () => {
  const actions = src('models/leverActionModel.js');

  it('has lev-tertiaire-create-efa template', () => {
    expect(actions).toContain('lev-tertiaire-create-efa');
  });

  it('has lev-tertiaire-complete-patrimoine template', () => {
    expect(actions).toContain('lev-tertiaire-complete-patrimoine');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 4. Wizard prefill
// ══════════════════════════════════════════════════════════════════════════════

describe('Wizard supports site_id prefill (V42)', () => {
  const wizard = src('pages/tertiaire/TertiaireWizardPage.jsx');

  it('imports useSearchParams', () => {
    expect(wizard).toContain('useSearchParams');
  });

  it('reads site_id from search params', () => {
    expect(wizard).toContain("site_id");
  });

  it('auto-selects buildings from prefill site', () => {
    expect(wizard).toContain('prefillSiteId');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 5. Dashboard "Sites à traiter"
// ══════════════════════════════════════════════════════════════════════════════

describe('Dashboard shows "Sites à traiter" (V42)', () => {
  const dash = src('pages/tertiaire/TertiaireDashboardPage.jsx');

  it('imports getTertiaireSiteSignals', () => {
    expect(dash).toContain('getTertiaireSiteSignals');
  });

  it('has sites-a-traiter section', () => {
    expect(dash).toContain('sites-a-traiter');
  });

  it('shows assujetti_probable sites with CTA', () => {
    expect(dash).toContain('assujetti_probable');
    expect(dash).toContain('Créer une EFA');
  });

  it('deep-links to wizard with site_id', () => {
    expect(dash).toContain('wizard?site_id=');
  });

  it('shows incomplete data sites', () => {
    expect(dash).toContain('Données incomplètes');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 6. Backend guards
// ══════════════════════════════════════════════════════════════════════════════

describe('Backend site-signals (V42)', () => {
  const service = backendSrc('services/tertiaire_service.py');
  const route = backendSrc('routes/tertiaire.py');

  it('has compute_site_signals function', () => {
    expect(service).toContain('def compute_site_signals');
  });

  it('uses 1000 m² threshold', () => {
    expect(service).toContain('1000');
    expect(service).toContain('assujetti_probable');
  });

  it('route imports compute_site_signals', () => {
    expect(route).toContain('compute_site_signals');
  });

  it('route has site-signals endpoint', () => {
    expect(route).toContain('site-signals');
  });
});
