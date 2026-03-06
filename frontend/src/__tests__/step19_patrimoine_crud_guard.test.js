/**
 * Step 19 — O3 : CRUD Organisation / Entité / Portefeuille / Site
 * Source-guard tests.
 */
import { describe, it, expect } from 'vitest';
import fs from 'fs';

describe('Step 19 — CRUD API functions', () => {
  const src = fs.readFileSync('src/services/api.js', 'utf8');

  it('has crudCreateOrganisation', () => {
    expect(src).toContain('crudCreateOrganisation');
  });

  it('has crudCreateEntite', () => {
    expect(src).toContain('crudCreateEntite');
  });

  it('has crudCreatePortefeuille', () => {
    expect(src).toContain('crudCreatePortefeuille');
  });

  it('has crudCreateSite', () => {
    expect(src).toContain('crudCreateSite');
  });

  it('calls /patrimoine/crud/organisations', () => {
    expect(src).toContain('/patrimoine/crud/organisations');
  });

  it('calls /patrimoine/crud/entites', () => {
    expect(src).toContain('/patrimoine/crud/entites');
  });

  it('calls /patrimoine/crud/portefeuilles', () => {
    expect(src).toContain('/patrimoine/crud/portefeuilles');
  });

  it('calls /patrimoine/crud/sites', () => {
    expect(src).toContain('/patrimoine/crud/sites');
  });

  it('has crudUpdateOrganisation (PATCH)', () => {
    expect(src).toContain('crudUpdateOrganisation');
  });

  it('has crudDeleteOrganisation (DELETE)', () => {
    expect(src).toContain('crudDeleteOrganisation');
  });

  it('has crudListOrganisations (GET)', () => {
    expect(src).toContain('crudListOrganisations');
  });

  it('has crudUpdateSite (PATCH)', () => {
    expect(src).toContain('crudUpdateSite');
  });

  it('has crudDeleteSite (DELETE)', () => {
    expect(src).toContain('crudDeleteSite');
  });
});
