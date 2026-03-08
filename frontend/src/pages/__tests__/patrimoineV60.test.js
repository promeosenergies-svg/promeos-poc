/**
 * patrimoineV60.test.js — Guards V60 Cockpit Patrimoine (Portfolio Summary)
 *
 * Source guards (AST-free, regex-based) :
 *   - api.js                              : getPatrimoinePortfolioSummary wrapper
 *   - PatrimoinePortfolioHealthBar.jsx    : composant V60, états, CTA
 *   - Patrimoine.jsx                      : import + wiring + openDrawerOnAnomalies
 *   - routes/patrimoine.py                : endpoint /portfolio-summary, Pydantic models
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
const HEALTH_BAR_JSX = src('components/PatrimoinePortfolioHealthBar.jsx');
const PATRIMOINE_JSX = src('pages/Patrimoine.jsx');
const ROUTES_PY = backend('routes/patrimoine.py');

// ── API wrapper V60 ────────────────────────────────────────────────────────

describe('API wrapper V60 — getPatrimoinePortfolioSummary', () => {
  test('getPatrimoinePortfolioSummary est exporté dans api.js', () => {
    expect(API_JS).toMatch(/export const getPatrimoinePortfolioSummary/);
  });

  test('getPatrimoinePortfolioSummary appelle /patrimoine/portfolio-summary', () => {
    expect(API_JS).toMatch(/\/patrimoine\/portfolio-summary/);
  });

  test('utilise _cachedGet (pas api.get direct)', () => {
    expect(API_JS).toMatch(/_cachedGet.*portfolio-summary|portfolio-summary.*_cachedGet/s);
  });

  test('V59 wrappers toujours présents (backward compat)', () => {
    expect(API_JS).toMatch(/export const getPatrimoineAssumptions/);
    expect(API_JS).toMatch(/export const getPatrimoineAnomalies/);
    expect(API_JS).toMatch(/export const listPatrimoineAnomalies/);
  });
});

// ── PatrimoinePortfolioHealthBar.jsx — structure ──────────────────────────

describe('PatrimoinePortfolioHealthBar — structure', () => {
  test('composant exporté par défaut', () => {
    expect(HEALTH_BAR_JSX).toMatch(/export default function PatrimoinePortfolioHealthBar/);
  });

  test('prop onSiteClick utilisée', () => {
    expect(HEALTH_BAR_JSX).toMatch(/onSiteClick/);
  });

  test('appelle getPatrimoinePortfolioSummary', () => {
    expect(HEALTH_BAR_JSX).toMatch(/getPatrimoinePortfolioSummary/);
  });

  test('FRAMEWORK_LABEL défini avec DECRET_TERTIAIRE', () => {
    expect(HEALTH_BAR_JSX).toMatch(/FRAMEWORK_LABEL/);
    expect(HEALTH_BAR_JSX).toMatch(/DECRET_TERTIAIRE/);
    expect(HEALTH_BAR_JSX).toMatch(/D.cret Tertiaire|Décret Tertiaire/);
  });
});

describe('PatrimoinePortfolioHealthBar — états', () => {
  test('état loading skeleton présent', () => {
    expect(HEALTH_BAR_JSX).toMatch(/loading/);
    expect(HEALTH_BAR_JSX).toMatch(/animate-pulse/);
  });

  test('état error + retry présent', () => {
    expect(HEALTH_BAR_JSX).toMatch(/error/);
    expect(HEALTH_BAR_JSX).toMatch(/Réessayer|retry/i);
  });

  test('état vide : sites_count === 0 géré', () => {
    expect(HEALTH_BAR_JSX).toMatch(/sites_count/);
  });

  test('CTA Charger la démo présent', () => {
    expect(HEALTH_BAR_JSX).toMatch(/Charger la démo|Charger/);
  });

  test('navigate vers /import présent', () => {
    expect(HEALTH_BAR_JSX).toMatch(/\/import/);
  });
});

describe('PatrimoinePortfolioHealthBar — affichage risque', () => {
  test('total_estimated_risk_eur affiché', () => {
    expect(HEALTH_BAR_JSX).toMatch(/total_estimated_risk_eur/);
  });

  test('sites_at_risk affiché', () => {
    expect(HEALTH_BAR_JSX).toMatch(/sites_at_risk/);
  });

  test('top_sites affiché', () => {
    expect(HEALTH_BAR_JSX).toMatch(/top_sites/);
  });

  test('framework_breakdown affiché', () => {
    expect(HEALTH_BAR_JSX).toMatch(/framework_breakdown/);
  });

  test('fmtRisk function définie', () => {
    expect(HEALTH_BAR_JSX).toMatch(/function fmtRisk/);
  });

  test('CTA "Voir anomalies" présent', () => {
    expect(HEALTH_BAR_JSX).toMatch(/Voir anomalies/);
  });
});

// ── Patrimoine.jsx — wiring V60 ───────────────────────────────────────────

describe('Patrimoine.jsx — import + wiring V60', () => {
  test('PatrimoinePortfolioHealthBar importé', () => {
    expect(PATRIMOINE_JSX).toMatch(/import PatrimoinePortfolioHealthBar/);
  });

  test('PatrimoinePortfolioHealthBar utilisé dans le JSX', () => {
    expect(PATRIMOINE_JSX).toMatch(/<PatrimoinePortfolioHealthBar/);
  });

  test('openDrawerOnAnomalies défini', () => {
    expect(PATRIMOINE_JSX).toMatch(/openDrawerOnAnomalies/);
  });

  test('onSiteClick câblé sur openDrawerOnAnomalies', () => {
    expect(PATRIMOINE_JSX).toMatch(
      /onSiteClick.*openDrawerOnAnomalies|openDrawerOnAnomalies.*onSiteClick/s
    );
  });

  test('drawerInitialTab state présent', () => {
    expect(PATRIMOINE_JSX).toMatch(/drawerInitialTab/);
  });

  test('SiteDrawerContent reçoit initialTab', () => {
    expect(PATRIMOINE_JSX).toMatch(/initialTab/);
  });
});

describe('Patrimoine.jsx — null safety V60', () => {
  test('openDrawerOnAnomalies fallback navigate si site non trouvé', () => {
    expect(PATRIMOINE_JSX).toMatch(/navigate.*site_id|site_id.*navigate/s);
  });

  test('scopedSites.find utilisé pour retrouver le site', () => {
    expect(PATRIMOINE_JSX).toMatch(/scopedSites\.find/);
  });
});

// ── routes/patrimoine.py — V60 backend ───────────────────────────────────

describe('routes/patrimoine.py — V60 Pydantic models', () => {
  test('PortfolioSummaryResponse présent', () => {
    expect(ROUTES_PY).toMatch(/class PortfolioSummaryResponse/);
  });

  test('PortfolioSitesAtRisk présent', () => {
    expect(ROUTES_PY).toMatch(/class PortfolioSitesAtRisk/);
  });

  test('PortfolioFrameworkItem présent', () => {
    expect(ROUTES_PY).toMatch(/class PortfolioFrameworkItem/);
  });

  test('PortfolioTopSiteItem présent', () => {
    expect(ROUTES_PY).toMatch(/class PortfolioTopSiteItem/);
  });

  test('endpoint /portfolio-summary présent', () => {
    expect(ROUTES_PY).toMatch(/\/portfolio-summary/);
  });

  test('total_estimated_risk_eur dans PortfolioSummaryResponse', () => {
    expect(ROUTES_PY).toMatch(/total_estimated_risk_eur/);
  });

  test('top_sites dans PortfolioSummaryResponse', () => {
    expect(ROUTES_PY).toMatch(/top_sites/);
  });

  test('framework_breakdown dans PortfolioSummaryResponse', () => {
    expect(ROUTES_PY).toMatch(/framework_breakdown/);
  });
});

describe('routes/patrimoine.py — V60 logique endpoint', () => {
  test('top_n param présent (default=3)', () => {
    expect(ROUTES_PY).toMatch(/top_n/);
    expect(ROUTES_PY).toMatch(/default=3/);
  });

  test('portefeuille_id filtre optionnel', () => {
    expect(ROUTES_PY).toMatch(/portefeuille_id/);
  });

  test('cas scope vide retourne 0', () => {
    expect(ROUTES_PY).toMatch(/not all_sites/);
  });

  test('enrich_anomalies_with_impact réutilisé', () => {
    expect(ROUTES_PY).toMatch(/enrich_anomalies_with_impact/);
  });

  test('compute_site_anomalies réutilisé', () => {
    expect(ROUTES_PY).toMatch(/compute_site_anomalies/);
  });

  test('sans Organisation.first() (multi-org guard)', () => {
    // Dans la fonction get_portfolio_summary uniquement
    const fnMatch = ROUTES_PY.match(/def get_portfolio_summary[\s\S]*?(?=\n@router|\nclass |$)/);
    if (fnMatch) {
      expect(fnMatch[0]).not.toMatch(/Organisation\s*\)\s*\.first\(\)/);
    }
  });

  test('tri top_sites par risk_eur DESC', () => {
    expect(ROUTES_PY).toMatch(/risk_eur.*reverse.*True|reverse.*True.*risk_eur/);
  });
});
