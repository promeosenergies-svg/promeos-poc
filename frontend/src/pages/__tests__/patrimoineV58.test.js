/**
 * patrimoineV58.test.js — Guards V58 Patrimoine Snapshot & Anomalies
 *
 * Source guards (AST-free, regex-based) pour :
 *   - API wrappers présents dans api.js
 *   - PatrimoineHealthCard composant
 *   - Intégration dans Patrimoine.jsx
 *   - Codes d'anomalie P0 couverts
 *   - Zéro Organisation.first() dans les services
 *   - CTAs pointent vers des routes existantes
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import path from 'path';

// src/pages/__tests__ → src/  (up 2 levels)
const src = (rel) => readFileSync(path.resolve(__dirname, '..', '..', rel), 'utf8');
// src/pages/__tests__ → promeos-poc/backend/  (up 4 levels + backend/)
const backend = (rel) =>
  readFileSync(path.resolve(__dirname, '..', '..', '..', '..', 'backend', rel), 'utf8');

const API_JS = src('services/api.js');
const PATRIMOINE_JSX = src('pages/Patrimoine.jsx');
const HEALTH_CARD_JSX = src('components/PatrimoineHealthCard.jsx');
const SNAPSHOT_PY = backend('services/patrimoine_snapshot.py');
const ANOMALIES_PY = backend('services/patrimoine_anomalies.py');

// ── API Wrappers ───────────────────────────────────────────────────────────

describe('API wrappers V58', () => {
  test('getPatrimoineSnapshot est exporté', () => {
    expect(API_JS).toMatch(/export const getPatrimoineSnapshot/);
  });

  test('getPatrimoineSnapshot appelle /patrimoine/sites/${siteId}/snapshot', () => {
    expect(API_JS).toMatch(/patrimoine\/sites\/.*snapshot/);
  });

  test('getPatrimoineAnomalies est exporté', () => {
    expect(API_JS).toMatch(/export const getPatrimoineAnomalies/);
  });

  test('getPatrimoineAnomalies appelle /patrimoine/sites/${siteId}/anomalies', () => {
    expect(API_JS).toMatch(/patrimoine\/sites\/.*anomalies/);
  });

  test('listPatrimoineAnomalies est exporté', () => {
    expect(API_JS).toMatch(/export const listPatrimoineAnomalies/);
  });

  test('listPatrimoineAnomalies appelle /patrimoine/anomalies', () => {
    expect(API_JS).toMatch(/\/patrimoine\/anomalies/);
  });
});

// ── PatrimoineHealthCard ───────────────────────────────────────────────────

describe('PatrimoineHealthCard composant', () => {
  test('importe getPatrimoineAnomalies depuis api', () => {
    expect(HEALTH_CARD_JSX).toMatch(/getPatrimoineAnomalies/);
  });

  test('accepte prop siteId', () => {
    expect(HEALTH_CARD_JSX).toMatch(/siteId/);
  });

  test('affiche ScoreGauge (completude_score)', () => {
    expect(HEALTH_CARD_JSX).toMatch(/completude_score/);
  });

  test('affiche les anomalies (anomalies)', () => {
    expect(HEALTH_CARD_JSX).toMatch(/anomalies/);
  });

  test('CTA utilise navigate pour redirection', () => {
    expect(HEALTH_CARD_JSX).toMatch(/useNavigate|navigate/);
  });

  test("gère l'état loading", () => {
    expect(HEALTH_CARD_JSX).toMatch(/loading/);
  });

  test("gère l'état error", () => {
    expect(HEALTH_CARD_JSX).toMatch(/error/);
  });

  test('affiche message "Patrimoine complet" si score 100', () => {
    expect(HEALTH_CARD_JSX).toMatch(/Patrimoine complet|Aucune anomalie/);
  });

  test('top 3 anomalies seulement (slice 0,3)', () => {
    expect(HEALTH_CARD_JSX).toMatch(/slice\s*\(\s*0\s*,\s*3\s*\)/);
  });
});

// ── Intégration dans Patrimoine.jsx ───────────────────────────────────────

describe('Intégration PatrimoineHealthCard dans Patrimoine.jsx', () => {
  test('importe SiteAnomalyPanel (V65: replaces PatrimoineHealthCard)', () => {
    expect(PATRIMOINE_JSX).toMatch(/import SiteAnomalyPanel/);
  });

  test("utilise SiteAnomalyPanel dans l'onglet anomalies (V65)", () => {
    // V65: replaced PatrimoineHealthCard with SiteAnomalyPanel in the drawer
    expect(PATRIMOINE_JSX).toMatch(/<SiteAnomalyPanel/);
  });

  test('passe siteId à PatrimoineHealthCard', () => {
    expect(PATRIMOINE_JSX).toMatch(/siteId=\{site\.id\}/);
  });
});

// ── Codes d'anomalie P0 couverts (backend guard) ──────────────────────────

describe('Codes anomalie P0 dans patrimoine_anomalies.py', () => {
  const P0_CODES = [
    'SURFACE_MISSING',
    'SURFACE_MISMATCH',
    'BUILDING_MISSING',
    'BUILDING_USAGE_MISSING',
    'METER_NO_DELIVERY_POINT',
    'CONTRACT_DATE_INVALID',
    'CONTRACT_OVERLAP_SITE',
    'ORPHANS_DETECTED',
  ];

  P0_CODES.forEach((code) => {
    test(`règle ${code} présente`, () => {
      expect(ANOMALIES_PY).toContain(`"${code}"`);
    });
  });
});

// ── Sévérités valides ─────────────────────────────────────────────────────

describe('Sévérités valides dans patrimoine_anomalies.py', () => {
  ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].forEach((sev) => {
    test(`sévérité ${sev} utilisée`, () => {
      expect(ANOMALIES_PY).toContain(`"${sev}"`);
    });
  });
});

// ── Guard multi-org : pas d'Organisation.first() ──────────────────────────

describe("Guard multi-org V57 — pas d'Organisation.first()", () => {
  test('patrimoine_snapshot.py ne contient pas Organisation.first()', () => {
    expect(SNAPSHOT_PY).not.toMatch(/Organisation\s*\)\s*\.first\(\)/);
  });

  test('patrimoine_anomalies.py ne contient pas Organisation.first()', () => {
    expect(ANOMALIES_PY).not.toMatch(/Organisation\s*\)\s*\.first\(\)/);
  });
});

// ── Soft-delete filtering ──────────────────────────────────────────────────

describe('Soft-delete filtering strict dans les services', () => {
  test('snapshot utilise not_deleted() pour Batiment', () => {
    expect(SNAPSHOT_PY).toMatch(/not_deleted\(Batiment\)/);
  });

  test('snapshot utilise not_deleted() pour Compteur', () => {
    expect(SNAPSHOT_PY).toMatch(/not_deleted\(Compteur\)/);
  });

  test('anomalies utilise not_deleted() pour Batiment', () => {
    expect(ANOMALIES_PY).toMatch(/not_deleted\(Batiment\)/);
  });
});

// ── Surface SoT (D1) ──────────────────────────────────────────────────────

describe('Surface SoT D1 dans patrimoine_snapshot.py', () => {
  test('utilise sum(batiment.surface_m2) si batiments présents', () => {
    expect(SNAPSHOT_PY).toMatch(/sum\(b\.surface_m2/);
  });

  test('contient le fallback site.surface_m2', () => {
    expect(SNAPSHOT_PY).toMatch(/site\.surface_m2/);
  });

  test('expose surface_sot_m2 dans le résultat', () => {
    expect(SNAPSHOT_PY).toMatch(/surface_sot_m2/);
  });
});

// ── Score de complétude (D7) ──────────────────────────────────────────────

describe('Score de complétude D7 dans patrimoine_anomalies.py', () => {
  test('calcule le score (max 0, 100 - penalty)', () => {
    expect(ANOMALIES_PY).toMatch(/max\s*\(\s*0\s*,\s*100\s*-/);
  });

  test('pénalité CRITICAL = 30', () => {
    expect(ANOMALIES_PY).toMatch(/"CRITICAL":\s*30/);
  });

  test('pénalité HIGH = 15', () => {
    expect(ANOMALIES_PY).toMatch(/"HIGH":\s*15/);
  });

  test('expose completude_score dans le résultat', () => {
    expect(ANOMALIES_PY).toMatch(/completude_score/);
  });
});

// ── CTAs pointent vers des routes existantes ──────────────────────────────

describe('CTAs dans PatrimoineHealthCard pointent vers des routes valides', () => {
  // Les CTAs du backend passent des chemins comme "/patrimoine" ou "/sites/:id"
  // Le frontend a ces routes dans App.jsx
  test('PatrimoineHealthCard utilise navigate pour les CTAs', () => {
    expect(HEALTH_CARD_JSX).toMatch(/navigate\s*\(\s*(to|anomaly\.cta\.to)/);
  });
});

// ── Tolérance SURFACE_MISMATCH configurable ───────────────────────────────

describe('Tolérance SURFACE_MISMATCH dans patrimoine_snapshot.py', () => {
  test('constante SURFACE_MISMATCH_TOLERANCE définie', () => {
    expect(SNAPSHOT_PY).toMatch(/SURFACE_MISMATCH_TOLERANCE/);
  });
});
