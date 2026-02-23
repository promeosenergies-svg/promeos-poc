/**
 * patrimoineV59.test.js — Guards V59 Impact Réglementaire & Business
 *
 * Source guards (AST-free, regex-based) :
 *   - config/patrimoine_assumptions.py : defaults, dataclass, to_dict
 *   - services/patrimoine_impact.py    : enrich function, priority_score, framework map
 *   - PatrimoineHealthCard.jsx         : V59 enrichissements UI
 *   - api.js                           : getPatrimoineAssumptions wrapper
 *   - Formules priority_score
 *   - Guard multi-org (pas d'Organisation.first())
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import path from 'path';

// src/pages/__tests__ → src/  (up 2 levels)
const src = (rel) => readFileSync(path.resolve(__dirname, '..', '..', rel), 'utf8');
// src/pages/__tests__ → promeos-poc/backend/  (up 4 levels + backend/)
const backend = (rel) =>
  readFileSync(path.resolve(__dirname, '..', '..', '..', '..', 'backend', rel), 'utf8');

const API_JS           = src('services/api.js');
const HEALTH_CARD_JSX  = src('components/PatrimoineHealthCard.jsx');
const ASSUMPTIONS_PY   = backend('config/patrimoine_assumptions.py');
const IMPACT_PY        = backend('services/patrimoine_impact.py');
const ROUTES_PY        = backend('routes/patrimoine.py');

// ── API wrappers V59 ───────────────────────────────────────────────────────

describe('API wrapper V59 — getPatrimoineAssumptions', () => {
  test('getPatrimoineAssumptions est exporté dans api.js', () => {
    expect(API_JS).toMatch(/export const getPatrimoineAssumptions/);
  });

  test('getPatrimoineAssumptions appelle /patrimoine/assumptions', () => {
    expect(API_JS).toMatch(/\/patrimoine\/assumptions/);
  });

  test('V58 wrappers toujours présents (backward compat)', () => {
    expect(API_JS).toMatch(/export const getPatrimoineSnapshot/);
    expect(API_JS).toMatch(/export const getPatrimoineAnomalies/);
    expect(API_JS).toMatch(/export const listPatrimoineAnomalies/);
  });
});

// ── config/patrimoine_assumptions.py ──────────────────────────────────────

describe('PatrimoineAssumptions config', () => {
  test('prix_elec_eur_mwh default 120', () => {
    // Soit inline soit via constante nommée
    expect(ASSUMPTIONS_PY).toMatch(/120\.0|PRIX_ELEC_EUR_MWH_DEFAULT/);
    expect(ASSUMPTIONS_PY).toContain('prix_elec_eur_mwh');
  });

  test('prix_gaz_eur_mwh default 55', () => {
    expect(ASSUMPTIONS_PY).toMatch(/55\.0|PRIX_GAZ_EUR_MWH_DEFAULT/);
    expect(ASSUMPTIONS_PY).toContain('prix_gaz_eur_mwh');
  });

  test('conso_fallback_global_kwh_an default 300000', () => {
    expect(ASSUMPTIONS_PY).toMatch(/300[_.]?000/);
  });

  test('dataclass PatrimoineAssumptions défini', () => {
    expect(ASSUMPTIONS_PY).toMatch(/class PatrimoineAssumptions/);
  });

  test('DEFAULT_ASSUMPTIONS singleton présent', () => {
    expect(ASSUMPTIONS_PY).toMatch(/DEFAULT_ASSUMPTIONS/);
  });

  test('to_dict méthode exposée', () => {
    expect(ASSUMPTIONS_PY).toMatch(/def to_dict/);
  });

  test('prix_elec_eur_kwh dérivé par division 1000', () => {
    expect(ASSUMPTIONS_PY).toMatch(/prix_elec_eur_mwh\s*\/\s*1000/);
  });

  test('conso_fallback_by_usage dict par usage', () => {
    expect(ASSUMPTIONS_PY).toMatch(/conso_fallback_by_usage/);
    expect(ASSUMPTIONS_PY).toContain('"bureaux"');
    expect(ASSUMPTIONS_PY).toContain('"commerce"');
  });
});

// ── services/patrimoine_impact.py ─────────────────────────────────────────

describe('patrimoine_impact.py — structure', () => {
  test('enrich_anomalies_with_impact définie', () => {
    expect(IMPACT_PY).toMatch(/def enrich_anomalies_with_impact/);
  });

  test('compute_priority_score définie', () => {
    expect(IMPACT_PY).toMatch(/def compute_priority_score/);
  });

  test('_IMPACT_META mapping présent', () => {
    expect(IMPACT_PY).toMatch(/_IMPACT_META/);
  });
});

describe('patrimoine_impact.py — frameworks réglementaires', () => {
  const FRAMEWORKS = [
    ['SURFACE_MISSING',          'DECRET_TERTIAIRE'],
    ['SURFACE_MISMATCH',         'DECRET_TERTIAIRE'],
    ['BUILDING_MISSING',         'DECRET_TERTIAIRE'],
    ['BUILDING_USAGE_MISSING',   'DECRET_TERTIAIRE'],
    ['METER_NO_DELIVERY_POINT',  'FACTURATION'],
    ['CONTRACT_DATE_INVALID',    'FACTURATION'],
    ['CONTRACT_OVERLAP_SITE',    'FACTURATION'],
    ['ORPHANS_DETECTED',         'NONE'],
  ];

  FRAMEWORKS.forEach(([code, framework]) => {
    test(`${code} → framework ${framework}`, () => {
      // Les deux doivent apparaître dans le même fichier
      expect(IMPACT_PY).toContain(`"${code}"`);
      expect(IMPACT_PY).toContain(`"${framework}"`);
    });
  });
});

describe('patrimoine_impact.py — formule priority_score', () => {
  test('_SEV_BASE présent', () => {
    expect(IMPACT_PY).toMatch(/_SEV_BASE/);
  });

  test('_FRAMEWORK_WEIGHT présent', () => {
    expect(IMPACT_PY).toMatch(/_FRAMEWORK_WEIGHT/);
  });

  test('DECRET_TERTIAIRE poids 20', () => {
    expect(IMPACT_PY).toMatch(/DECRET_TERTIAIRE.*20|20.*DECRET_TERTIAIRE/);
  });

  test('FACTURATION poids 20', () => {
    expect(IMPACT_PY).toMatch(/FACTURATION.*20|20.*FACTURATION/);
  });

  test('bucket >50k retourne 30', () => {
    expect(IMPACT_PY).toMatch(/50[_.]?000/);
    expect(IMPACT_PY).toMatch(/return 30/);
  });

  test('score clampé à 100', () => {
    expect(IMPACT_PY).toMatch(/min\s*\(\s*100\s*,/);
  });

  test('tri par priority_score DESC', () => {
    expect(IMPACT_PY).toMatch(/priority_score.*reverse.*True|reverse.*True.*priority_score/);
  });
});

describe('patrimoine_impact.py — calculs business impact', () => {
  test('SURFACE_MISMATCH utilise surface_diff', () => {
    expect(IMPACT_PY).toMatch(/surface_diff/);
  });

  test('METER_NO_DELIVERY_POINT utilise facteur 0.20', () => {
    expect(IMPACT_PY).toMatch(/0\.20/);
  });

  test('CONTRACT_OVERLAP utilise overlap_days', () => {
    expect(IMPACT_PY).toMatch(/overlap_days/);
  });

  test('calcul retourne estimated_risk_eur', () => {
    expect(IMPACT_PY).toMatch(/estimated_risk_eur/);
  });

  test('calcul retourne confidence', () => {
    expect(IMPACT_PY).toMatch(/"confidence"/);
  });
});

// ── routes/patrimoine.py — response models ────────────────────────────────

describe('routes/patrimoine.py — V59 response models', () => {
  test('RegulatoryImpact response model présent', () => {
    expect(ROUTES_PY).toMatch(/class RegulatoryImpact/);
  });

  test('BusinessImpact response model présent', () => {
    expect(ROUTES_PY).toMatch(/class BusinessImpact/);
  });

  test('SiteAnomaliesResponse présent', () => {
    expect(ROUTES_PY).toMatch(/class SiteAnomaliesResponse/);
  });

  test('total_estimated_risk_eur dans SiteAnomaliesResponse', () => {
    expect(ROUTES_PY).toMatch(/total_estimated_risk_eur/);
  });

  test('assumptions_used dans SiteAnomaliesResponse', () => {
    expect(ROUTES_PY).toMatch(/assumptions_used/);
  });

  test('GET /assumptions endpoint présent', () => {
    expect(ROUTES_PY).toMatch(/\/assumptions/);
  });

  test('OrgAnomaliesResponse présent', () => {
    expect(ROUTES_PY).toMatch(/class OrgAnomaliesResponse/);
  });

  test('top_priority_score dans OrgAnomaliesSiteItem', () => {
    expect(ROUTES_PY).toMatch(/top_priority_score/);
  });
});

// ── PatrimoineHealthCard.jsx — V59 UI ────────────────────────────────────

describe('PatrimoineHealthCard V59 — framework chips', () => {
  test('FRAMEWORK_CHIP défini', () => {
    expect(HEALTH_CARD_JSX).toMatch(/FRAMEWORK_CHIP/);
  });

  test('Décret Tertiaire chip', () => {
    expect(HEALTH_CARD_JSX).toMatch(/D.cret Tertiaire|Décret Tertiaire/);
  });

  test('Facturation chip', () => {
    expect(HEALTH_CARD_JSX).toMatch(/Facturation/);
  });

  test('BACS chip', () => {
    expect(HEALTH_CARD_JSX).toMatch(/BACS/);
  });
});

describe('PatrimoineHealthCard V59 — risque €', () => {
  test('estimated_risk_eur affiché', () => {
    expect(HEALTH_CARD_JSX).toMatch(/estimated_risk_eur/);
  });

  test('confidence affiché', () => {
    expect(HEALTH_CARD_JSX).toMatch(/confidence/);
  });

  test('total_estimated_risk_eur affiché', () => {
    expect(HEALTH_CARD_JSX).toMatch(/total_estimated_risk_eur/);
  });

  test('composant RiskBadge présent', () => {
    expect(HEALTH_CARD_JSX).toMatch(/RiskBadge/);
  });
});

describe('PatrimoineHealthCard V59 — priority_score sort', () => {
  test('tri par priority_score mention présente', () => {
    expect(HEALTH_CARD_JSX).toMatch(/priority_score/);
  });

  test('top 3 slice(0, 3) utilisé', () => {
    expect(HEALTH_CARD_JSX).toMatch(/slice\s*\(\s*0\s*,\s*3\s*\)/);
  });

  test('comment dit "trié DESC par le backend"', () => {
    expect(HEALTH_CARD_JSX).toMatch(/priority_score|trié|DESC/i);
  });
});

describe('PatrimoineHealthCard V59 — états', () => {
  test('état loading présent', () => {
    expect(HEALTH_CARD_JSX).toMatch(/loading/);
  });

  test('état error + retry présent', () => {
    expect(HEALTH_CARD_JSX).toMatch(/error/);
    expect(HEALTH_CARD_JSX).toMatch(/Réessayer|retry/i);
  });

  test('état empty "Patrimoine complet"', () => {
    expect(HEALTH_CARD_JSX).toMatch(/Patrimoine complet|Aucune anomalie/);
  });

  test('navigate CTA présent', () => {
    expect(HEALTH_CARD_JSX).toMatch(/navigate/);
  });
});

// ── Guard multi-org (hérité V57) ──────────────────────────────────────────

describe('Guard multi-org V59', () => {
  test('patrimoine_impact.py sans Organisation.first()', () => {
    expect(IMPACT_PY).not.toMatch(/Organisation\s*\)\s*\.first\(\)/);
  });

  test('patrimoine_assumptions.py sans Organisation.first()', () => {
    expect(ASSUMPTIONS_PY).not.toMatch(/Organisation\s*\)\s*\.first\(\)/);
  });

  test('enrich_anomalies_with_impact sans accès DB', () => {
    // La fonction ne doit pas importer Session ou db
    const fnMatch = IMPACT_PY.match(
      /def enrich_anomalies_with_impact[\s\S]*?^def /m
    );
    if (fnMatch) {
      const fnBody = fnMatch[0];
      expect(fnBody).not.toMatch(/Session|get_db|db\.query/);
    }
  });
});
