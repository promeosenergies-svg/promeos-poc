/**
 * Phase 3 — TabResume refonte source guards.
 */
import { describe, test, expect } from 'vitest';
import fs from 'fs';

const SITE360 = fs.readFileSync('src/pages/Site360.jsx', 'utf-8');

describe('Phase 3 — TabResume refonte', () => {
  test('Header scores ont des labels explicites (Conformité)', () => {
    expect(SITE360).toMatch(/Conformité/);
  });

  test('Completeness badge a un label Complétude', () => {
    expect(SITE360).toMatch(/[Cc]omplétude|completeness/);
  });

  test('Breadcrumb contient des Link cliquables vers patrimoine', () => {
    expect(SITE360).toMatch(/Link[\s\S]*?to.*patrimoine/);
  });

  test('Breadcrumb affiche organisation_nom', () => {
    expect(SITE360).toMatch(/organisation_nom/);
  });

  test('Breadcrumb affiche entite_juridique_nom', () => {
    expect(SITE360).toMatch(/entite_juridique_nom/);
  });

  test('Intensité utilise backend #146 avec fallback statique', () => {
    expect(SITE360).toContain('kWh_m2_final');
    expect(SITE360).toMatch(/conso_kwh_an.*surface_m2/);
  });

  test('Benchmark OID référencé avec getBenchmark', () => {
    expect(SITE360).toMatch(/getBenchmark/);
    expect(SITE360).toMatch(/benchmark OID/);
  });

  test('Accès rapide cross-module présent', () => {
    expect(SITE360).toMatch(/Accès rapide/);
    expect(SITE360).toMatch(/Bill Intelligence/);
    expect(SITE360).toMatch(/Conformité/);
    expect(SITE360).toMatch(/Radar contrats/);
    expect(SITE360).toMatch(/Actions/);
  });

  test('benchmarks.js est importé', () => {
    expect(SITE360).toMatch(/from.*benchmarks/);
  });
});
