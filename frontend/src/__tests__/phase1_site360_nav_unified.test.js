/**
 * Phase 1 Site360 — Nav redirect + Unified anomalies
 * Source-guard tests.
 */
import { describe, it, expect } from 'vitest';
import fs from 'fs';

const APP_SRC = fs.readFileSync('src/App.jsx', 'utf8');
const SITE360_SRC = fs.readFileSync('src/pages/Site360.jsx', 'utf8');
const API_SRC = fs.readFileSync('src/services/api/patrimoine.js', 'utf8');

describe('Phase 1 — Navigation /sites redirect', () => {
  it('/sites route redirects to /patrimoine in App.jsx', () => {
    // Vérifie qu'il existe une route path="/sites" avec Navigate to="/patrimoine"
    expect(APP_SRC).toMatch(/path="\/sites"/);
    expect(APP_SRC).toMatch(/Navigate\s+to="\/patrimoine"/);
  });

  it('/sites/:id route still exists for Site360', () => {
    expect(APP_SRC).toMatch(/path="\/sites\/:id"/);
    expect(APP_SRC).toMatch(/Site360/);
  });
});

describe('Phase 1 — Unified anomalies', () => {
  it('getUnifiedAnomalies is exported from patrimoine API', () => {
    expect(API_SRC).toMatch(/export\s+(const|function)\s+getUnifiedAnomalies/);
  });

  it('getUnifiedAnomalies calls anomalies-unified endpoint', () => {
    expect(API_SRC).toMatch(/anomalies-unified/);
  });

  it('Site360 imports getUnifiedAnomalies', () => {
    expect(SITE360_SRC).toMatch(/getUnifiedAnomalies/);
  });

  it('Site360 uses unifiedCount for MiniKpi', () => {
    expect(SITE360_SRC).toMatch(/unifiedCount/);
  });

  it('Site360 renders source badges (Données/Analyse)', () => {
    expect(SITE360_SRC).toMatch(/Donn[ée]+es/);
    expect(SITE360_SRC).toMatch(/Analyse/);
  });

  it('Site360 still imports getPatrimoineAnomalies as fallback', () => {
    expect(SITE360_SRC).toMatch(/getPatrimoineAnomalies/);
  });
});
