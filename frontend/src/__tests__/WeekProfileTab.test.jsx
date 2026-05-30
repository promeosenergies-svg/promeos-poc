// @vitest-environment jsdom
/**
 * PROMEOS — Tests WeekProfileTab (Sprint P1.S4).
 *
 * Couvre la checklist QA de sortie S4 :
 * 1. onglet « Semaine type » visible dans /usages → cf. integration test
 *    UsagesDashboardPage (validInitialTab + ALL_TABS contiennent
 *    'semaine-type') ;
 * 2. getWeekProfile appelé avec scope_id et days=90 par défaut ;
 * 3. loading state visible ;
 * 4. empty state visible (matrix vide + 0 KPI) ;
 * 5. error state affiche hint + correlation_id ;
 * 6. 4 KPI affichés avec provenance ;
 * 7. heatmap affiche 168 cellules si matrix complète (via WeekProfileHeatmap) ;
 * 8. status normal/vigilance/critique/missing propagé ;
 * 9. aucun calcul métier interdit dans WeekProfileTab.
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';

vi.mock('../services/api/energy', () => ({
  getWeekProfile: vi.fn(),
}));

// Sprint P2.2 — EnergyCrossLinks utilise <Link>. Override comme <a>
// pour éviter besoin de MemoryRouter wrapper. Préserve actual export.
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    Link: ({ to, children, replace: _replace, state: _state, ...rest }) => (
      <a href={to} {...rest}>
        {children}
      </a>
    ),
  };
});

const mockSetSite = vi.fn();
let _mockScopeOverride = null;

vi.mock('../contexts/ScopeContext', () => ({
  useScope: () =>
    _mockScopeOverride
      ? { ...{ setSite: mockSetSite }, ..._mockScopeOverride }
      : {
          selectedSiteId: 42,
          scope: { orgId: 1, entiteId: null, portefeuilleId: null, siteId: 42 },
          setSite: mockSetSite,
        },
}));

function setScope(next) {
  _mockScopeOverride = next;
}

import WeekProfileTab, { KPI_ORDER, DEFAULT_DAYS } from '../pages/usages/WeekProfileTab';
import { getWeekProfile } from '../services/api/energy';

const PROV = (service) => ({
  source: 'PROMEOS energy_orchestration',
  service,
  formula: 'Σ MeterReading.value_kwh par (day_of_week, hour)',
  period: '2026-02-28 → 2026-05-29',
  confidence: 0.85,
  assumptions: ['timezone Europe/Paris', 'agrégation 90 jours glissants'],
});

const KPI = (key, label, value, unit, state = 'sain') => ({
  key,
  label,
  value,
  unit,
  state,
  scope: { kind: 'site', scope_id: 42, org_id: 1 },
  period: { label: '90d', days: 90, timezone: 'Europe/Paris' },
  provenance: PROV(`energy_orchestration.week_profile._kpi (${key})`),
});

function buildFullMatrix() {
  const m = [];
  for (let d = 0; d < 7; d++) {
    for (let h = 0; h < 24; h++) {
      m.push({
        day_of_week: d,
        hour: h,
        kwh: 8 + d + h * 0.2,
        kw_avg: 3 + h * 0.1,
        status: d === 5 || d === 6 ? 'vigilance' : 'normal',
        quality_status: 'measured',
      });
    }
  }
  return m;
}

const SAMPLE_PAYLOAD = {
  scope: { kind: 'site', scope_id: 42, org_id: 1 },
  period: { label: '90d', days: 90, timezone: 'Europe/Paris' },
  matrix: buildFullMatrix(),
  kpis: {
    highest_day: KPI('highest_day', 'Jour le plus consommateur', 'Mer (425 kWh)', 'kWh'),
    highest_hour: KPI('highest_hour', 'Heure la plus consommatrice', 'Mer 14h (28 kWh)', 'kWh'),
    night_baseload_kw: KPI('night_baseload_kw', 'Talon nuit (0h-5h)', 3.4, 'kW'),
    weekend_consumption_pct: KPI(
      'weekend_consumption_pct',
      'Part conso week-end',
      18.5,
      '%',
      'vigilance'
    ),
  },
  provenance: PROV('energy_orchestration.week_profile.build_week_profile'),
  warnings: [],
};

describe('WeekProfileTab — checklist QA S4', () => {
  beforeEach(() => {
    getWeekProfile.mockReset();
    mockSetSite.mockReset();
    setScope(null);
  });
  afterEach(() => cleanup());

  it('Critère 2 : appelle getWeekProfile avec scope_id + days=90 par défaut', async () => {
    getWeekProfile.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    render(<WeekProfileTab />);
    await waitFor(() => expect(getWeekProfile).toHaveBeenCalledTimes(1));
    const args = getWeekProfile.mock.calls[0][0];
    expect(args.scope).toBe('site');
    expect(args.scope_id).toBe(42);
    expect(args.days).toBe(DEFAULT_DAYS);
    expect(DEFAULT_DAYS).toBe(90);
    expect(args.org_id).toBe(1);
  });

  it('Critère 3 : loading state visible avant la réponse', async () => {
    let resolveFn;
    const pending = new Promise((res) => {
      resolveFn = res;
    });
    getWeekProfile.mockReturnValueOnce(pending);
    render(<WeekProfileTab />);
    expect(screen.getByTestId('week-profile-loading')).toBeTruthy();
    resolveFn(SAMPLE_PAYLOAD);
    await waitFor(() => screen.getByTestId('week-profile-kpis-grid'));
  });

  it('Critère 4 : empty state visible quand matrix vide ET 0 KPI', async () => {
    getWeekProfile.mockResolvedValueOnce({
      ...SAMPLE_PAYLOAD,
      matrix: [],
      kpis: {},
    });
    render(<WeekProfileTab />);
    await waitFor(() => expect(screen.queryByTestId('week-profile-kpis-grid')).toBeNull());
    expect(screen.getByText(/Données insuffisantes/i)).toBeTruthy();
    // CTA "Élargir la période" présent
    expect(screen.getByText('Élargir la période')).toBeTruthy();
  });

  it('Critère 5 : error state affiche code + hint + correlation_id', async () => {
    const err = new Error('Request failed');
    err.response = {
      status: 400,
      data: {
        detail: {
          code: 'ENERGY_DAYS_INSUFFICIENT',
          message: 'days=14 insuffisant pour calculer une semaine type fiable',
          hint: 'demander au moins days=30, idéalement 90',
          correlation_id: 'corr-week-1234',
        },
      },
    };
    getWeekProfile.mockRejectedValueOnce(err);
    render(<WeekProfileTab />);
    await waitFor(() => screen.getByTestId('week-profile-error'));
    expect(screen.getByTestId('error-code').textContent).toContain('ENERGY_DAYS_INSUFFICIENT');
    expect(screen.getByTestId('error-hint').textContent).toContain('au moins days=30');
    expect(screen.getByTestId('error-correlation-id').textContent).toContain('corr-week-1234');
  });

  it('Critère 6 : 4 KPI rendus avec provenance backend', async () => {
    getWeekProfile.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    render(<WeekProfileTab />);
    await waitFor(() => screen.getByTestId('week-profile-kpis-grid'));
    for (const key of KPI_ORDER) {
      expect(screen.getByTestId(`week-profile-kpi-${key}`)).toBeTruthy();
    }
    // 4 tooltips provenance (cf. KpiCardWithProvenance)
    const tooltips = screen.getAllByTestId('kpi-provenance-tooltip');
    expect(tooltips.length).toBe(4);
    expect(tooltips[0].textContent).toContain('energy_orchestration.week_profile');
    expect(tooltips[0].textContent).toContain('Σ MeterReading.value_kwh');
  });

  it('Critère 6 bis : ordre canonique KPI_ORDER (4 entrées, highest_day → weekend_consumption_pct)', () => {
    expect(KPI_ORDER).toEqual([
      'highest_day',
      'highest_hour',
      'night_baseload_kw',
      'weekend_consumption_pct',
    ]);
  });

  it('Critère 7 : heatmap rendue avec 168 cellules quand matrix complète', async () => {
    getWeekProfile.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    render(<WeekProfileTab />);
    await waitFor(() => screen.getByTestId('week-profile-heatmap'));
    let count = 0;
    for (let d = 0; d < 7; d++) {
      for (let h = 0; h < 24; h++) {
        if (screen.queryByTestId(`heatmap-cell-${d}-${h}`)) count++;
      }
    }
    expect(count).toBe(168);
  });

  it('Critère 8 : status normal/vigilance propagés sur les cellules', async () => {
    getWeekProfile.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    render(<WeekProfileTab />);
    await waitFor(() => screen.getByTestId('week-profile-heatmap'));
    // Cellule jour=5 (samedi) → vigilance dans SAMPLE_PAYLOAD
    expect(screen.getByTestId('heatmap-cell-5-12').getAttribute('data-status')).toBe('vigilance');
    // Cellule jour=0 (lundi) → normal
    expect(screen.getByTestId('heatmap-cell-0-8').getAttribute('data-status')).toBe('normal');
  });

  it('Critère partial : bandeau warnings affiché si backend renvoie warnings', async () => {
    getWeekProfile.mockResolvedValueOnce({
      ...SAMPLE_PAYLOAD,
      warnings: ['12 cellules estimées (qualité_status=estimated)', 'fenêtre 90j incomplète'],
    });
    render(<WeekProfileTab />);
    await waitFor(() => screen.getByTestId('week-profile-partial'));
    const banner = screen.getByTestId('week-profile-partial').textContent || '';
    expect(banner).toContain('Données partielles');
    expect(banner).toContain('12 cellules estimées');
  });

  it('Sprint P1.S6 — scope=org (pas de site) : SiteRequiredState rendu, aucun appel API', () => {
    setScope({
      selectedSiteId: null,
      scope: { orgId: 1, entiteId: null, portefeuilleId: null, siteId: null },
    });
    render(<WeekProfileTab />);
    expect(screen.getByTestId('site-required-state')).toBeTruthy();
    expect(screen.getByText(/Sélectionnez un site/i)).toBeTruthy();
    expect(getWeekProfile).not.toHaveBeenCalled();
  });

  it('Header microcopy FR conforme au brief', async () => {
    getWeekProfile.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    render(<WeekProfileTab />);
    await waitFor(() => screen.getByTestId('week-profile-header'));
    const header = screen.getByTestId('week-profile-header').textContent || '';
    expect(header).toContain('Semaine type');
    expect(header).toContain('Votre comportement du lundi au dimanche');
    expect(header).toContain('Repérez les pics, le talon de nuit');
  });
});

describe('WeekProfileTab — doctrine zéro calcul métier (critère 9)', () => {
  it('WeekProfileTab.jsx ne contient aucun calcul métier interdit', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../pages/usages/WeekProfileTab.jsx'), 'utf8');
    // Pas d'agrégation métier sur kwh/kw_avg FE
    expect(src).not.toMatch(/Math\.max\s*\(\s*\.{3}\s*\w+\.map\s*\(/);
    expect(src).not.toMatch(/\.reduce\s*\(\s*\([\w,\s]*\)\s*=>\s*\w+\s*\+\s*\w+\.kwh/);
    expect(src).not.toMatch(/\.reduce\s*\(\s*\([\w,\s]*\)\s*=>\s*\w+\s*\+\s*\w+\.kw_avg/);
    // Pas de calcul talon nuit / weekend FE (hors clés KPI backend consommées)
    expect(src).not.toMatch(/const\s+nightBaseload\s*=/);
    expect(src).not.toMatch(/const\s+weekendPct\s*=/);
    expect(src).not.toMatch(/weekendKwh|nightKwh|peakKw\s*=/);
    // Pas de CO₂/coût/facteur émission FE
    expect(src).not.toMatch(/kwhToCo2|emission_factor|co2Factor/);
    expect(src).not.toMatch(/cost_eur\s*=\s*\w+\s*\*/);
    // L'appel API et le rendu KPI fournis backend sont OK
    expect(src).toContain('getWeekProfile');
    expect(src).toContain('KpiCardWithProvenance');
  });

  it('Sprint P2.2 : cross-link Conformité (données R.174-22) ajouté', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../pages/usages/WeekProfileTab.jsx'), 'utf8');
    expect(src).toMatch(/import\s+EnergyCrossLinks/);
    expect(src).toMatch(/WEEK_PROFILE_CROSS_LINKS\s*=\s*\[/);
    expect(src).toContain("'/conformite?tab=donnees'");
    expect(src).toContain("'Voir données réglementaires'");
    expect(src).toMatch(/testId="week-profile-cross-links"/);
  });

  it('UsagesDashboardPage importe WeekProfileTab et déclare le tab', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../pages/UsagesDashboardPage.jsx'), 'utf8');
    expect(src).toContain("import WeekProfileTab from './usages/WeekProfileTab'");
    expect(src).toMatch(/id:\s*['"]semaine-type['"]/);
    expect(src).toMatch(/label:\s*['"]Semaine type['"]/);
    // validInitialTab whitelist contient 'semaine-type'
    expect(src).toMatch(/['"]semaine-type['"]/);
  });

  it('Rail NavRegistry inchangé (pas de top-level Semaine type)', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../layout/NavRegistry.js'), 'utf8');
    expect(src).not.toMatch(/['"]Semaine type['"]/);
    expect(src).not.toMatch(/['"]semaine-type['"]/);
  });
});
