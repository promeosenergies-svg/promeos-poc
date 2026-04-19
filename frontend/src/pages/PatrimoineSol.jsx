/**
 * PROMEOS — PatrimoineSol (Phase 4.3, refonte Sol V1 Pattern A)
 *
 * Rebuild intégral de /patrimoine selon le Pattern A :
 *   SolPageHeader → SolHeadline → SolKpiRow (3 KPIs neutral/neutral/cost)
 *   → SolWeekGrid (3 cards top-drivers/risque/succès)
 *   → SolBarChart axe catégoriel sites (conso MWh vs N-1).
 *
 * APIs consommées (inchangées) :
 *   - getPatrimoineKpis({scope})  → total, conformes, totalSurface, totalRisque, ...
 *   - getSites({org_id, limit})   → liste sites avec type, surface, conso, compliance
 *
 * Filtre ?type= : client-side via useSearchParams. Les items du panel Sol
 * /patrimoine naviguent vers /patrimoine?type=bureau/entrepot/enseignement.
 * Quand présent, filtre sites.type pour scope visuel (KPIs, week-cards, chart).
 *
 * EUI moyen calculé frontend (pondéré surface) vs benchmark ADEME ODP 2024
 * (utils/benchmarks.js).
 *
 * Drawer préservé : navigation vers /sites/:id (Site360) via onClick week-card.
 * Pas de drawer custom PatrimoineSol — la fiche détail site est une route dédiée.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  SolPageHeader,
  SolKpiRow,
  SolKpiCard,
  SolSourceChip,
  SolSectionHead,
  SolWeekGrid,
  SolWeekCard,
  SolBarChart,
} from '../ui/sol';
import { useScope } from '../contexts/ScopeContext';
import { getSites, getPatrimoineKpis } from '../services/api';
import {
  NBSP,
  buildPatrimoineKicker,
  buildPatrimoineNarrative,
  buildPatrimoineSubNarrative,
  buildPatrimoineWeekCards,
  adaptSitesToBarChart,
  computeAvgEui,
  computeAvgBenchmark,
  topEuiDrivers,
  interpretSites,
  interpretSurface,
  interpretEUI,
  formatFR,
  formatFREur,
  freshness,
} from './patrimoine/sol_presenters';
import { SkeletonCard } from '../ui/Skeleton';

// ──────────────────────────────────────────────────────────────────────────────

function usePatrimoineSolData({ orgId, typeFilter } = {}) {
  const [state, setState] = useState({
    status: 'loading',
    kpis: null,
    sites: null,
  });

  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, status: 'loading' }));

    Promise.allSettled([
      getPatrimoineKpis().catch(() => null),
      getSites({ org_id: orgId, limit: 200 }).catch(() => null),
    ]).then(([kpis, sites]) => {
      if (cancelled) return;
      const rawSites = sites.status === 'fulfilled' ? sites.value : null;
      // Normalisation : l'API peut retourner { sites: [...], total } OU [...] direct
      const sitesList = Array.isArray(rawSites)
        ? rawSites
        : Array.isArray(rawSites?.sites)
          ? rawSites.sites
          : [];
      // Filtre client-side ?type=
      const filtered = typeFilter
        ? sitesList.filter((s) => (s?.type || s?.usage || '').toLowerCase() === typeFilter)
        : sitesList;
      setState({
        status: 'ready',
        kpis: kpis.status === 'fulfilled' ? kpis.value : null,
        sites: filtered,
        allSitesCount: sitesList.length,
      });
    });

    return () => { cancelled = true; };
  }, [orgId, typeFilter]);

  return state;
}

// ──────────────────────────────────────────────────────────────────────────────

export default function PatrimoineSol() {
  const scopeCtx = useScope();
  const scope = scopeCtx?.scope || {};
  const org = scopeCtx?.org;
  const scopeLabel = scopeCtx?.scopeLabel;
  const sitesCount = scopeCtx?.sitesCount;
  const orgName = org?.name || org?.label || scopeLabel || 'votre patrimoine';

  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const typeFilter = (searchParams.get('type') || '').toLowerCase() || null;

  const data = usePatrimoineSolData({ orgId: scope.orgId, typeFilter });

  // ─── Dérivations présentation ──────────────────────────────────────────────

  const kicker = buildPatrimoineKicker({
    scope: { orgName, sitesCount },
    typeFilter,
  });

  const kpis = data.kpis ?? {};
  const sites = Array.isArray(data.sites) ? data.sites : [];

  // Si filtre type, recalculer KPIs agrégés sur la vue filtrée
  const displayKpis = typeFilter
    ? {
        total: sites.length,
        totalSurface: sites.reduce((acc, s) => acc + (Number(s.surface_m2) || 0), 0),
        conformes: sites.filter((s) => s.statut_conformite === 'conforme').length,
        aRisque: sites.filter((s) => s.statut_conformite === 'a_risque').length,
        nonConformes: sites.filter((s) => s.statut_conformite === 'non_conforme').length,
        nb_contrats_expiring_90j: 0, // pas recalculable sans data contrats
      }
    : kpis;

  const euiAvg = useMemo(() => computeAvgEui(sites), [sites]);
  const benchmarkAvg = useMemo(() => computeAvgBenchmark(sites), [sites]);
  const topDrivers = useMemo(() => topEuiDrivers(sites), [sites]);

  const euiDelta = useMemo(() => {
    if (euiAvg == null || benchmarkAvg == null) return null;
    const gap = ((euiAvg - benchmarkAvg) / benchmarkAvg) * 100;
    if (Math.abs(gap) < 0.5) return { direction: 'flat', text: `aligné ADEME`, value: 0 };
    const sign = gap > 0 ? '▲' : '▼';
    const formatted = Math.abs(gap).toFixed(0);
    return {
      direction: gap > 0 ? 'up' : 'down',
      value: gap,
      text: `${sign} ${formatted}${NBSP}% vs ADEME`,
    };
  }, [euiAvg, benchmarkAvg]);

  const weekCards = useMemo(
    () =>
      buildPatrimoineWeekCards({
        sites,
        topDrivers,
        onNavigateSite: (siteId) => navigate(`/sites/${siteId}`),
      }),
    [sites, topDrivers, navigate]
  );

  const barChartData = useMemo(() => adaptSitesToBarChart(sites, { limit: 8 }), [sites]);

  const narrative = buildPatrimoineNarrative({
    kpis: displayKpis,
    sites,
    euiAvg,
    benchmarkAvg,
  });
  const subNarrative = buildPatrimoineSubNarrative({ kpis: displayKpis });

  // ─── Rendu ───────────────────────────────────────────────────────────────

  if (data.status === 'loading') {
    return (
      <div>
        <SkeletonCard lines={1} />
        <SkeletonCard lines={3} />
        <SkeletonCard lines={5} />
      </div>
    );
  }

  return (
    <>
      <SolPageHeader
        kicker={kicker}
        title="Votre patrimoine "
        titleEm={typeFilter ? `— ${typeFilter}s uniquement` : '— sites, contrats et conformité'}
        narrative={narrative}
        subNarrative={subNarrative}
      />

      <SolKpiRow>
        <SolKpiCard
          label="Nombre de sites"
          explainKey="patrimoine_sites_count"
          value={displayKpis.total != null ? formatFR(displayKpis.total, 0) : '—'}
          unit={displayKpis.total > 1 ? 'sites' : 'site'}
          semantic="neutral"
          headline={interpretSites({ kpis: displayKpis, sites })}
          source={{
            kind: 'Sites actifs',
            origin: typeFilter ? `filtre ${typeFilter}` : 'tous types',
          }}
        />
        <SolKpiCard
          label="Surface totale"
          explainKey="patrimoine_surface_m2"
          value={displayKpis.totalSurface != null ? formatFR(displayKpis.totalSurface, 0) : '—'}
          unit={`${NBSP}m²`}
          semantic="neutral"
          headline={interpretSurface({ kpis: displayKpis, sites })}
          source={{
            kind: 'Patrimoine',
            origin: 'surfaces renseignées',
          }}
        />
        <SolKpiCard
          label="EUI moyen"
          explainKey="patrimoine_eui_moyen"
          value={euiAvg != null ? formatFR(euiAvg, 0) : '—'}
          unit={`${NBSP}kWh/m²/an`}
          delta={euiDelta}
          semantic="cost"
          headline={interpretEUI({ euiAvg, benchmarkAvg, topDrivers })}
          source={{
            kind: 'Consommations',
            origin: 'Enedis + GRDF · ADEME ODP 2024',
            freshness: benchmarkAvg != null
              ? `réf. ${formatFR(benchmarkAvg, 0)}${NBSP}kWh/m²`
              : undefined,
          }}
        />
      </SolKpiRow>

      <SolSectionHead
        title="Cette semaine chez vous"
        meta={`${weekCards.length} points · actualisé à l'instant`}
      />
      <SolWeekGrid>
        {weekCards.map((c) => (
          <SolWeekCard
            key={c.id}
            tagKind={c.tagKind}
            tagLabel={c.tagLabel}
            title={c.title}
            body={c.body}
            footerLeft={c.footerLeft}
            footerRight={c.footerRight}
            onClick={c.onClick}
          />
        ))}
      </SolWeekGrid>

      <SolSectionHead
        title="Consommation par site"
        meta={`${barChartData.length}${NBSP}sites · 12${NBSP}mois glissants`}
      />
      <div
        style={{
          background: 'var(--sol-bg-paper)',
          border: '1px solid var(--sol-ink-200)',
          borderRadius: 8,
          padding: 16,
          boxShadow: '0 1px 2px rgba(15, 23, 42, 0.03)',
        }}
      >
        <SolBarChart
          data={barChartData}
          metric="mwh"
          xAxisType="category"
          xAxisKey="site"
          xAxisAngle={-20}
          showDeltaPct
          highlightCurrent={false}
          caption={
            euiAvg != null ? (
              <>
                <strong style={{ color: 'var(--sol-ink-900)' }}>
                  EUI moyen {formatFR(euiAvg, 0)}{NBSP}kWh/m²
                </strong>{' '}
                · référence ADEME ODP 2024 pondérée surface : {formatFR(benchmarkAvg || 0, 0)}{NBSP}kWh/m².
              </>
            ) : (
              <>Conso annuelle par site · tri décroissant.</>
            )
          }
          sourceChip={
            <SolSourceChip
              kind="Enedis + GRDF"
              origin="12 mois glissants"
              freshness={kpis.completude_moyenne_pct != null ? `${kpis.completude_moyenne_pct}% complet` : undefined}
            />
          }
        />
      </div>
    </>
  );
}
