/**
 * PROMEOS — Step 32 source-guard : SiteCreationWizard
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

const src_dir = join(__dirname, '..');
const wizardPath = join(src_dir, 'components', 'SiteCreationWizard.jsx');
const patrimoinePath = join(src_dir, 'pages', 'Patrimoine.jsx');
const appPath = join(src_dir, 'App.jsx');
const apiPath = join(src_dir, 'services', 'api.js');

function read(p) {
  return existsSync(p) ? readFileSync(p, 'utf-8') : null;
}

describe('Step 32 — SiteCreationWizard', () => {
  const wizardSrc = read(wizardPath);

  it('wizard component exists', () => {
    expect(wizardSrc).not.toBeNull();
  });

  it('has 7 steps defined', () => {
    expect(wizardSrc).toMatch(/STEPS/);
    // All 7 step IDs present
    expect(wizardSrc).toMatch(/org/);
    expect(wizardSrc).toMatch(/entite/);
    expect(wizardSrc).toMatch(/portefeuille/);
    expect(wizardSrc).toMatch(/site/);
    expect(wizardSrc).toMatch(/batiments/);
    expect(wizardSrc).toMatch(/compteurs/);
    expect(wizardSrc).toMatch(/recap/);
  });

  it('has organisation step', () => {
    expect(wizardSrc).toMatch(/Organisation/);
    expect(wizardSrc).toMatch(/StepOrganisation/);
  });

  it('has entite juridique step', () => {
    expect(wizardSrc).toMatch(/Entite/);
    expect(wizardSrc).toMatch(/StepEntite/);
  });

  it('has site creation fields', () => {
    expect(wizardSrc).toMatch(/nom/);
    expect(wizardSrc).toMatch(/SITE_TYPES/);
  });

  it('has recap/confirmation step', () => {
    expect(wizardSrc).toMatch(/StepRecap/);
    expect(wizardSrc).toMatch(/Confirmer la creation/);
    expect(wizardSrc).toMatch(/Recapitulatif/);
  });

  it('has optional batiment step', () => {
    expect(wizardSrc).toMatch(/StepBatiments/);
    expect(wizardSrc).toMatch(/batiment/i);
  });

  it('has optional compteur step', () => {
    expect(wizardSrc).toMatch(/StepCompteurs/);
    expect(wizardSrc).toMatch(/compteur/i);
  });

  it('validates SIREN (9 digits)', () => {
    expect(wizardSrc).toMatch(/validateSiren/);
    expect(wizardSrc).toMatch(/9/);
  });

  it('validates PRM (14 digits)', () => {
    expect(wizardSrc).toMatch(/validatePrm/);
    expect(wizardSrc).toMatch(/14/);
  });

  it('uses CRUD API functions', () => {
    expect(wizardSrc).toMatch(/crudCreateSite/);
    expect(wizardSrc).toMatch(/crudCreateOrganisation/);
    expect(wizardSrc).toMatch(/crudCreateEntite/);
    expect(wizardSrc).toMatch(/crudCreatePortefeuille/);
    expect(wizardSrc).toMatch(/crudCreateBatiment/);
    expect(wizardSrc).toMatch(/createMeter/);
  });

  it('has error handling (does not close on error)', () => {
    expect(wizardSrc).toMatch(/setError/);
    expect(wizardSrc).toMatch(/error/);
  });

  it('navigates to new site on success', () => {
    expect(wizardSrc).toMatch(/navigate.*sites/);
  });
});

describe('Patrimoine page integration', () => {
  const src = read(patrimoinePath);

  it('imports SiteCreationWizard', () => {
    expect(src).toMatch(/SiteCreationWizard/);
  });

  it('has "Ajouter un site" button', () => {
    expect(src).toMatch(/Ajouter un site/);
  });

  it('has showSiteWizard state', () => {
    expect(src).toMatch(/showSiteWizard/);
  });

  it('renders SiteCreationWizard conditionally', () => {
    expect(src).toMatch(/showSiteWizard.*SiteCreationWizard/s);
  });
});

describe('App.jsx routing', () => {
  const src = read(appPath);

  it('has /patrimoine/nouveau redirect', () => {
    expect(src).toMatch(/patrimoine\/nouveau/);
    expect(src).toMatch(/wizard=open/);
  });
});

describe('API functions', () => {
  const src = read(apiPath);

  it('has crudCreateBatiment', () => {
    expect(src).toMatch(/crudCreateBatiment/);
    expect(src).toMatch(/\/patrimoine\/crud\/batiments/);
  });
});
