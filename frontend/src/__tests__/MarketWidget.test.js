/**
 * PROMEOS — MarketWidget — Source Guards + Structure Tests
 * Widget compact : spot 7j + sparkline + décomposition barre empilée
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const widgetPath = join(__dirname, '..', 'pages', 'cockpit', 'MarketWidget.jsx');
const widgetSrc = readFileSync(widgetPath, 'utf-8');

const hookPath = join(__dirname, '..', 'hooks', 'useMarketData.js');
const hookSrc = readFileSync(hookPath, 'utf-8');

const apiPath = join(__dirname, '..', 'services', 'api', 'market.js');
const apiSrc = readFileSync(apiPath, 'utf-8');

// ── Source Guards (no-calc) ──────────────────────────────────────────

describe('MarketWidget — source guard (no-calc)', () => {
  it('ne contient pas de facteur CO2 (* 0.052)', () => {
    expect(widgetSrc).not.toMatch(/\*\s*0\.052/);
  });

  it('ne contient pas de CSPE hardcodée (* 26.58)', () => {
    expect(widgetSrc).not.toMatch(/\*\s*26\.58/);
  });

  it('ne contient pas de prix fallback (* 0.068)', () => {
    expect(widgetSrc).not.toMatch(/\*\s*0\.068/);
  });

  it('ne contient pas de pénalité DT (* 7500)', () => {
    expect(widgetSrc).not.toMatch(/\*\s*7500/);
  });

  it('ne contient pas de conversion MWh (* 1000)', () => {
    expect(widgetSrc).not.toMatch(/\*\s*1000/);
  });
});

// ── Structure widget ──────────────────────────────────────────

describe('MarketWidget — structure', () => {
  it('utilise useMarketData hook', () => {
    expect(widgetSrc).toMatch(/useMarketData/);
  });

  it('affiche data-testid market-widget', () => {
    expect(widgetSrc).toMatch(/data-testid="market-widget"/);
  });

  it('contient les 7 briques de décomposition', () => {
    expect(widgetSrc).toMatch(/energy/);
    expect(widgetSrc).toMatch(/turpe/);
    expect(widgetSrc).toMatch(/cspe/);
    expect(widgetSrc).toMatch(/capacity/);
    expect(widgetSrc).toMatch(/cee/);
    expect(widgetSrc).toMatch(/cta/);
    expect(widgetSrc).toMatch(/tva/);
  });

  it('affiche le total TTC', () => {
    expect(widgetSrc).toMatch(/total_ttc_eur_mwh/);
  });

  it('gère les 3 états : loading, error, data', () => {
    expect(widgetSrc).toMatch(/loading/);
    expect(widgetSrc).toMatch(/error/);
    expect(widgetSrc).toMatch(/animate-pulse/);
    expect(widgetSrc).toMatch(/indisponibles/);
  });

  it('utilise Recharts AreaChart pour la sparkline', () => {
    expect(widgetSrc).toMatch(/AreaChart/);
    expect(widgetSrc).toMatch(/ResponsiveContainer/);
  });

  it('affiche la tendance (hausse/baisse/stable)', () => {
    expect(widgetSrc).toMatch(/TrendingUp/);
    expect(widgetSrc).toMatch(/TrendingDown/);
    expect(widgetSrc).toMatch(/Hausse/);
    expect(widgetSrc).toMatch(/Baisse/);
    expect(widgetSrc).toMatch(/Stable/);
  });

  it('affiche la méthode de calcul et la version tarif', () => {
    expect(widgetSrc).toMatch(/calculation_method/);
    expect(widgetSrc).toMatch(/tariff_version/);
    expect(widgetSrc).toMatch(/SPOT_BASED/);
    expect(widgetSrc).toMatch(/FORWARD_BASED/);
    expect(widgetSrc).toMatch(/FALLBACK/);
  });

  it('affiche les forward CAL', () => {
    expect(widgetSrc).toMatch(/FORWARD_YEAR/);
    expect(widgetSrc).toMatch(/forwardCal/);
  });
});

// ── Hook useMarketData ──────────────────────────────────────────

describe('useMarketData — structure', () => {
  it('appelle 4 endpoints en parallèle via Promise.allSettled', () => {
    expect(hookSrc).toMatch(/Promise\.allSettled/);
    expect(hookSrc).toMatch(/getMarketSpotStats/);
    expect(hookSrc).toMatch(/getMarketSpotHistory/);
    expect(hookSrc).toMatch(/getMarketDecomposition/);
    expect(hookSrc).toMatch(/getMarketForwards/);
  });

  it('gère graceful degradation par endpoint', () => {
    expect(hookSrc).toMatch(/status\s*===\s*'fulfilled'/);
  });

  it('a un refresh automatique', () => {
    expect(hookSrc).toMatch(/setInterval/);
    expect(hookSrc).toMatch(/REFRESH_INTERVAL/);
  });

  it('expose refresh manuel', () => {
    expect(hookSrc).toMatch(/refresh:\s*fetchData/);
  });
});

// ── API market.js ──────────────────────────────────────────

describe('API market — endpoints', () => {
  it('exporte les 8 fonctions API', () => {
    expect(apiSrc).toMatch(/getMarketSpotLatest/);
    expect(apiSrc).toMatch(/getMarketSpotStats/);
    expect(apiSrc).toMatch(/getMarketSpotHistory/);
    expect(apiSrc).toMatch(/getMarketForwards/);
    expect(apiSrc).toMatch(/getMarketTariffsCurrent/);
    expect(apiSrc).toMatch(/getMarketDecomposition\b/);
    expect(apiSrc).toMatch(/getMarketDecompositionCompare/);
    expect(apiSrc).toMatch(/getMarketFreshness/);
  });

  it('utilise les bons paths API', () => {
    expect(apiSrc).toMatch(/\/market\/spot\/latest/);
    expect(apiSrc).toMatch(/\/market\/spot\/stats/);
    expect(apiSrc).toMatch(/\/market\/spot\/history/);
    expect(apiSrc).toMatch(/\/market\/forwards/);
    expect(apiSrc).toMatch(/\/market\/tariffs\/current/);
    expect(apiSrc).toMatch(/\/market\/decomposition\/compute/);
    expect(apiSrc).toMatch(/\/market\/decomposition\/compare/);
    expect(apiSrc).toMatch(/\/market\/freshness/);
  });
});
