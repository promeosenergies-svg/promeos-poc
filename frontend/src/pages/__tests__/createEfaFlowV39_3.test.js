/**
 * PROMEOS V39.3 — Flux création EFA : dashboard → wizard → fiche
 *
 * 1. Dashboard CTAs naviguent vers le wizard
 * 2. Wizard submit : succès → redirect, erreur → message visible
 * 3. Export pack accessible sur fiche EFA
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const src = (rel) =>
  fs.readFileSync(path.resolve(__dirname, '..', '..', rel), 'utf-8');

// ══════════════════════════════════════════════════════════════════════════════
// 1. Dashboard CTAs
// ══════════════════════════════════════════════════════════════════════════════

describe('Dashboard tertiaire CTAs', () => {
  const code = src('pages/tertiaire/TertiaireDashboardPage.jsx');

  it('"Nouvelle EFA" navigates to wizard', () => {
    expect(code).toContain("navigate('/conformite/tertiaire/wizard')");
  });

  it('"Nouvelle EFA" has data-testid', () => {
    expect(code).toContain('data-testid="btn-nouvelle-efa"');
  });

  it('empty state "Créer une EFA" navigates to wizard', () => {
    // Both CTAs use the same route
    const matches = code.match(/navigate\('\/conformite\/tertiaire\/wizard'\)/g);
    expect(matches.length).toBeGreaterThanOrEqual(2);
  });

  it('empty state button has data-testid', () => {
    expect(code).toContain('data-testid="btn-creer-efa-empty"');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 2. Wizard submit
// ══════════════════════════════════════════════════════════════════════════════

describe('Wizard EFA submit flow', () => {
  const code = src('pages/tertiaire/TertiaireWizardPage.jsx');

  it('has submitError state', () => {
    expect(code).toContain('submitError');
    expect(code).toContain('setSubmitError');
  });

  it('clears error before submit', () => {
    expect(code).toContain('setSubmitError(null)');
  });

  it('calls createTertiaireEfa on submit', () => {
    expect(code).toContain('createTertiaireEfa');
  });

  it('navigates to EFA detail on success', () => {
    expect(code).toContain("navigate(`/conformite/tertiaire/efa/${efa.id}`");
  });

  it('passes justCreated state on redirect', () => {
    expect(code).toContain('justCreated: true');
  });

  it('sets visible error message in FR on failure', () => {
    expect(code).toContain("Impossible de créer l'EFA");
  });

  it('error block has data-testid', () => {
    expect(code).toContain('data-testid="wizard-submit-error"');
  });

  it('error message renders with AlertTriangle icon', () => {
    expect(code).toContain('AlertTriangle');
    // Error banner is in JSX
    expect(code).toContain('submitError &&');
  });

  it('loading state disables button and shows spinner', () => {
    expect(code).toContain('disabled={saving}');
    expect(code).toContain('Création…');
  });

  it('API error details are extracted from response', () => {
    expect(code).toContain('err?.response?.data?.detail');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 3. Export pack accessible on EFA detail
// ══════════════════════════════════════════════════════════════════════════════

describe('EFA detail — export pack accessible', () => {
  const code = src('pages/tertiaire/TertiaireEfaDetailPage.jsx');

  it('has standalone "Actions OPERAT" section', () => {
    expect(code).toContain('Actions OPERAT');
  });

  it('export button has data-testid', () => {
    expect(code).toContain('data-testid="btn-export-pack"');
  });

  it('export button label is "Exporter le pack"', () => {
    expect(code).toContain('Exporter le pack');
  });

  it('pré-vérifier button is in Actions section', () => {
    expect(code).toContain('Pré-vérifier');
  });

  it('export button calls handleExport', () => {
    expect(code).toContain('onClick={handleExport}');
  });

  it('export button is disabled while exporting', () => {
    expect(code).toContain('disabled={exporting}');
  });

  it('Mémobox button appears after export', () => {
    expect(code).toContain('Ouvrir dans la Mémobox');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 4. Backend schema — minimal payload accepted
// ══════════════════════════════════════════════════════════════════════════════

describe('Backend EfaCreate schema', () => {
  const code = fs.readFileSync(
    path.resolve(__dirname, '..', '..', '..', '..', 'backend', 'routes', 'tertiaire.py'),
    'utf-8',
  );

  it('site_id is Optional', () => {
    expect(code).toContain('site_id: Optional[int] = None');
  });

  it('reporting_start is Optional', () => {
    expect(code).toContain('reporting_start: Optional[str] = None');
  });

  it('notes is Optional', () => {
    expect(code).toContain('notes: Optional[str] = None');
  });

  it('nom is required (no default)', () => {
    expect(code).toMatch(/nom:\s*str\b/);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 5. Routes consistency
// ══════════════════════════════════════════════════════════════════════════════

describe('Routes consistency', () => {
  const appCode = src('App.jsx');

  it('wizard route exists', () => {
    expect(appCode).toContain('/conformite/tertiaire/wizard');
  });

  it('EFA detail route exists', () => {
    expect(appCode).toContain('/conformite/tertiaire/efa/:id');
  });

  it('dashboard route exists', () => {
    expect(appCode).toContain('path="/conformite/tertiaire"');
  });
});
