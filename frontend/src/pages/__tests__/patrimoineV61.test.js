/**
 * patrimoineV61.test.js — Guards V61 Portfolio Health Bar enrichi
 *
 * Source guards (AST-free, regex-based) :
 *   A. PatrimoinePortfolioHealthBar.jsx : sites_health, HealthBar, trend, FrameworkPill counts
 *   B. routes/patrimoine.py : PortfolioSitesHealth, PortfolioTrend, champs V61
 *
 * Vérifications clés :
 *   - HealthBar affiche healthy_pct + breakdown
 *   - FrameworkPill accepte count prop → affiche "(N)"
 *   - TrendBadge null-safe (affiche "—" quand null)
 *   - sites_health dans Pydantic PortfolioSummaryResponse
 *   - trend Optional dans Pydantic
 *   - empty scope → sites_health zeros dans backend
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import path from 'path';

const src = (rel) => readFileSync(path.resolve(__dirname, '..', '..', rel), 'utf8');
const backend = (rel) =>
  readFileSync(path.resolve(__dirname, '..', '..', '..', '..', 'backend', rel), 'utf8');

const HEALTH_BAR_JSX = src('components/PatrimoinePortfolioHealthBar.jsx');
const ROUTES_PY = backend('routes/patrimoine.py');

// ── HealthBar sous-composant ──────────────────────────────────────────────

describe('HealthBar V61 — breakdown santé', () => {
  test('composant HealthBar défini', () => {
    expect(HEALTH_BAR_JSX).toMatch(/function HealthBar/);
  });

  test('sites_health utilisé dans HealthBar', () => {
    expect(HEALTH_BAR_JSX).toMatch(/sites_health/);
  });

  test('healthy_pct affiché', () => {
    expect(HEALTH_BAR_JSX).toMatch(/healthy_pct/);
  });

  test('breakdown healthy/warning/critical présent', () => {
    expect(HEALTH_BAR_JSX).toMatch(/healthy/);
    expect(HEALTH_BAR_JSX).toMatch(/warning/);
    expect(HEALTH_BAR_JSX).toMatch(/critical/);
  });

  test('barre de progression mini présente (bg-green bg-amber bg-red)', () => {
    expect(HEALTH_BAR_JSX).toMatch(/bg-green-400/);
    expect(HEALTH_BAR_JSX).toMatch(/bg-amber-400/);
    expect(HEALTH_BAR_JSX).toMatch(/bg-red-400/);
  });

  test('icône ShieldCheck utilisée', () => {
    expect(HEALTH_BAR_JSX).toMatch(/ShieldCheck/);
  });

  test('null-safe : ?? 0 ou nullish coalescing sur healthy/warning/critical', () => {
    expect(HEALTH_BAR_JSX).toMatch(/\?\? 0/);
  });
});

// ── TrendBadge — null-safe ────────────────────────────────────────────────

describe('TrendBadge V61 — trend null-safe', () => {
  test('composant TrendBadge défini', () => {
    expect(HEALTH_BAR_JSX).toMatch(/function TrendBadge/);
  });

  test('prop trend utilisée', () => {
    expect(HEALTH_BAR_JSX).toMatch(/\{ trend \}|trend\?|trend ==|trend !=/);
  });

  test('direction null → fallback "—" ou Minus ou Tendance', () => {
    expect(HEALTH_BAR_JSX).toMatch(/Minus|Tendance|—/);
  });

  test('"up" → TrendingUp', () => {
    expect(HEALTH_BAR_JSX).toMatch(/TrendingUp/);
  });

  test('"down" → TrendingDown', () => {
    expect(HEALTH_BAR_JSX).toMatch(/TrendingDown/);
  });

  test('import TrendingUp TrendingDown Minus depuis lucide-react', () => {
    expect(HEALTH_BAR_JSX).toMatch(/TrendingUp.*TrendingDown.*Minus|Minus.*TrendingUp/s);
  });

  test('trend utilisé dans vue nominale (pas seulement déclaré)', () => {
    expect(HEALTH_BAR_JSX).toMatch(/<TrendBadge\s+trend/);
  });
});

// ── FrameworkPill V61 — avec count ───────────────────────────────────────

describe('FrameworkPill V61 — avec comptes anomalies', () => {
  test('FrameworkPill accepte prop count', () => {
    expect(HEALTH_BAR_JSX).toMatch(/function FrameworkPill.*\{.*count|count.*FrameworkPill/s);
  });

  test('count affiché entre parenthèses', () => {
    expect(HEALTH_BAR_JSX).toMatch(/\(\s*\{count\}|\{count\}\s*\)/);
  });

  test('count null-safe (count != null)', () => {
    expect(HEALTH_BAR_JSX).toMatch(/count\s*!=\s*null/);
  });

  test('top 3 frameworks avec counts dans vue nominale', () => {
    expect(HEALTH_BAR_JSX).toMatch(/slice\s*\(\s*0\s*,\s*3\s*\)/);
    expect(HEALTH_BAR_JSX).toMatch(/fw\.anomalies_count/);
  });
});

// ── Vue nominale V61 ──────────────────────────────────────────────────────

describe('PatrimoinePortfolioHealthBar V61 — vue nominale', () => {
  test('sites_health destructuré dans vue nominale', () => {
    expect(HEALTH_BAR_JSX).toMatch(/sites_health/);
  });

  test('trend destructuré dans vue nominale', () => {
    expect(HEALTH_BAR_JSX).toMatch(/trend/);
  });

  test('top3Fw slice(0, 3) présent', () => {
    expect(HEALTH_BAR_JSX).toMatch(/slice\s*\(\s*0\s*,\s*3\s*\)/);
  });

  test('HealthBar rendu dans JSX', () => {
    expect(HEALTH_BAR_JSX).toMatch(/<HealthBar/);
  });

  test('TrendBadge rendu dans JSX', () => {
    expect(HEALTH_BAR_JSX).toMatch(/<TrendBadge/);
  });

  test('états V60 toujours présents (loading, error, empty)', () => {
    expect(HEALTH_BAR_JSX).toMatch(/loading/);
    expect(HEALTH_BAR_JSX).toMatch(/error/);
    expect(HEALTH_BAR_JSX).toMatch(/sites_count === 0/);
    expect(HEALTH_BAR_JSX).toMatch(/Charger HELIOS/);
  });
});

// ── Backend Pydantic models V61 ───────────────────────────────────────────

describe('routes/patrimoine.py — V61 Pydantic models', () => {
  test('PortfolioSitesHealth présent', () => {
    expect(ROUTES_PY).toMatch(/class PortfolioSitesHealth/);
  });

  test('healthy field dans PortfolioSitesHealth', () => {
    expect(ROUTES_PY).toMatch(/healthy.*int|int.*healthy/);
  });

  test('warning field dans PortfolioSitesHealth', () => {
    expect(ROUTES_PY).toMatch(/warning.*int|int.*warning/);
  });

  test('healthy_pct field dans PortfolioSitesHealth', () => {
    expect(ROUTES_PY).toMatch(/healthy_pct/);
  });

  test('PortfolioTrend présent', () => {
    expect(ROUTES_PY).toMatch(/class PortfolioTrend/);
  });

  test('risk_eur_delta Optional dans PortfolioTrend', () => {
    expect(ROUTES_PY).toMatch(/risk_eur_delta.*Optional|Optional.*risk_eur_delta/);
  });

  test('direction Optional dans PortfolioTrend', () => {
    expect(ROUTES_PY).toMatch(/direction.*Optional|Optional.*direction/);
  });

  test('PortfolioSummaryResponse contient sites_health', () => {
    expect(ROUTES_PY).toMatch(
      /sites_health.*PortfolioSitesHealth|PortfolioSitesHealth.*sites_health/
    );
  });

  test('PortfolioSummaryResponse contient trend Optional', () => {
    expect(ROUTES_PY).toMatch(/trend.*Optional.*PortfolioTrend|Optional.*PortfolioTrend.*trend/);
  });
});

describe('routes/patrimoine.py — V61 logique endpoint', () => {
  test('seuils HEALTH_HEALTHY et HEALTH_WARNING présents', () => {
    expect(ROUTES_PY).toMatch(/_HEALTH_HEALTHY/);
    expect(ROUTES_PY).toMatch(/_HEALTH_WARNING/);
  });

  test('seuil 85 pour healthy', () => {
    expect(ROUTES_PY).toMatch(/85/);
  });

  test('seuil 50 pour warning', () => {
    expect(ROUTES_PY).toMatch(/50/);
  });

  test('trend: None dans la réponse', () => {
    expect(ROUTES_PY).toMatch(/"trend".*None|trend.*None/);
  });

  test("healthy_pct calculé dans l'endpoint", () => {
    expect(ROUTES_PY).toMatch(/healthy_pct/);
  });

  test('sites_health dans scope vide', () => {
    // Le cas "not all_sites" doit aussi retourner sites_health.
    // Vérification : "not all_sites" et "sites_health" sont dans la même fonction (même fichier).
    // Guard simple : les deux patterns sont présents et "not all_sites" précède sites_health.
    const idxEmpty = ROUTES_PY.indexOf('not all_sites');
    const idxHealth = ROUTES_PY.indexOf('"sites_health"', idxEmpty);
    expect(idxEmpty).toBeGreaterThan(-1);
    // sites_health doit apparaître dans les 600 chars suivant "not all_sites"
    expect(idxHealth).toBeGreaterThan(idxEmpty);
    expect(idxHealth - idxEmpty).toBeLessThan(600);
  });
});
