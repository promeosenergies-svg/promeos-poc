/**
 * PROMEOS — MonitoringSol (Lot 1.3, route /monitoring)
 *
 * Monitoring Performance Pattern A : 3 KPIs sites actifs/alertes/dérive €
 * + 3 week-cards + SolTrajectoryChart consommation MWh 12 mois avec
 * baseline user line.
 *
 * APIs consommées (toutes existantes) :
 *   - getMonitoringAlertsByOrg(orgId) → [alertes détectées agrégées org]
 *   - getBillingCompareMonthly({months:12}) → courbe conso kWh
 *   - getSites({org_id, limit}) → enrichissement site_nom sur alertes
 *   - getPatrimoineKpis() → total_sites pour couverture
 */
import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  SolPageHeader,
  SolKpiRow,
  SolKpiCard,
  SolSourceChip,
  SolSectionHead,
  SolWeekGrid,
  SolWeekCard,
  SolTrajectoryChart,
} from '../ui/sol';
import { useScope } from '../contexts/ScopeContext';
import {
  getMonitoringAlertsByOrg,
  getBillingCompareMonthly,
  getSites,
  getPatrimoineKpis,
} from '../services/api';
import {
  NBSP,
  buildMonitoringKicker,
  buildMonitoringNarrative,
  buildMonitoringSubNarrative,
  buildMonitoringWeekCards,
  summarizeAlerts,
  enrichAlertsWithSites,
  adaptCompareToTrajectory,
  computeBaseline,
  interpretMonitoringSites,
  interpretMonitoringAlerts,
  interpretMonitoringDrift,
  formatFR,
  formatFREur,
  freshness,
} from './monitoring/sol_presenters';
import { SkeletonCard } from '../ui/Skeleton';

// ──────────────────────────────────────────────────────────────────────────────

function useMonitoringData({ orgId } = {}) {
  const [state, setState] = useState({
    status: 'loading',
    alerts: null,
    compare: null,
    sites: null,
    patrimoineKpis: null,
  });

  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, status: 'loading' }));

    Promise.allSettled([
      orgId ? getMonitoringAlertsByOrg(orgId).catch(() => []) : Promise.resolve([]),
      getBillingCompareMonthly({ months: 12 }).catch(() => null),
      orgId ? getSites({ org_id: orgId, limit: 200 }).catch(() => null) : Promise.resolve(null),
      getPatrimoineKpis().catch(() => null),
    ]).then(([alerts, compare, sites, patrimoineKpis]) => {
      if (cancelled) return;
      const sitesArr = sites.status === 'fulfilled'
        ? (Array.isArray(sites.value) ? sites.value : sites.value?.sites || [])
        : [];
      setState({
        status: 'ready',
        alerts: alerts.status === 'fulfilled' ? alerts.value : [],
        compare: compare.status === 'fulfilled' ? compare.value : null,
        sites: sitesArr,
        patrimoineKpis: patrimoineKpis.status === 'fulfilled' ? patrimoineKpis.value : null,
      });
    });

    return () => { cancelled = true; };
  }, [orgId]);

  return state;
}

// ──────────────────────────────────────────────────────────────────────────────

export default function MonitoringSol() {
  const scopeCtx = useScope();
  const scope = scopeCtx?.scope || {};
  const org = scopeCtx?.org;
  const scopeLabel = scopeCtx?.scopeLabel;
  const sitesCount = scopeCtx?.sitesCount;
  const orgName = org?.name || org?.label || scopeLabel || 'votre patrimoine';
  const navigate = useNavigate();

  const data = useMonitoringData({ orgId: scope.orgId });

  // ─── Dérivations présentation ──────────────────────────────────────────────

  const kicker = buildMonitoringKicker({ scope: { orgName, sitesCount } });

  const rawAlerts = Array.isArray(data.alerts) ? data.alerts : [];
  const sites = data.sites || [];
  const totalSites = data.patrimoineKpis?.total ?? data.patrimoineKpis?.nb_sites ?? sites.length;
  const activeSites = totalSites; // V2 : assume tous en surveillance active

  const enrichedAlerts = useMemo(() => enrichAlertsWithSites(rawAlerts, sites), [rawAlerts, sites]);
  const summary = useMemo(() => summarizeAlerts(enrichedAlerts), [enrichedAlerts]);

  const trajectoryData = useMemo(() => adaptCompareToTrajectory(data.compare), [data.compare]);
  const baseline = useMemo(() => computeBaseline(trajectoryData), [trajectoryData]);

  const weekCards = useMemo(
    () =>
      buildMonitoringWeekCards({
        alerts: enrichedAlerts,
        onNavigateSite: (siteId) => navigate(`/sites/${siteId}`),
      }),
    [enrichedAlerts, navigate]
  );

  const narrative = buildMonitoringNarrative({
    alertsCount: summary.total,
    totalImpact: summary.totalImpact,
    activeSites,
    totalSites,
  });
  const coveragePct = totalSites > 0 ? Math.round((activeSites / totalSites) * 100) : null;
  const subNarrative = buildMonitoringSubNarrative({ totalSites, coverage: coveragePct });

  // Domaine Y adapté aux données (min-max avec marge)
  const yDomain = useMemo(() => {
    if (trajectoryData.length === 0) return [0, 100];
    const values = trajectoryData.map((p) => p.value).filter((v) => v != null);
    if (values.length === 0) return [0, 100];
    const min = Math.min(...values);
    const max = Math.max(...values);
    const margin = Math.max(20, (max - min) * 0.3);
    return [Math.max(0, Math.round(min - margin)), Math.round(max + margin)];
  }, [trajectoryData]);

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
        title="Monitoring performance "
        titleEm="— baseline normalisée DJU et dérives actives"
        narrative={narrative}
        subNarrative={subNarrative}
      />

      <SolKpiRow>
        <SolKpiCard
          label="Sites en surveillance active"
          explainKey="monitoring_active_sites"
          value={activeSites != null ? `${activeSites}/${totalSites}` : '—'}
          unit={totalSites > 1 ? 'sites' : 'site'}
          semantic="neutral"
          headline={interpretMonitoringSites({ activeSites, totalSites })}
          source={{
            kind: 'EMS',
            origin: 'télérelève + baseline',
            freshness: coveragePct != null ? `${coveragePct}% couverture` : undefined,
          }}
        />
        <SolKpiCard
          label="Alertes de dérive actives"
          explainKey="monitoring_active_alerts"
          value={formatFR(summary.total, 0)}
          unit={summary.total > 1 ? 'alertes' : 'alerte'}
          semantic="cost"
          headline={interpretMonitoringAlerts({
            alertsCount: summary.total,
            bySeverity: summary.bySeverity,
            topAlert: summary.topAlert,
          })}
          source={{
            kind: 'Moteur monitoring',
            origin: 'règles métier',
          }}
        />
        <SolKpiCard
          label="Dérive cumulée estimée"
          explainKey="monitoring_cumulative_drift"
          value={summary.totalImpact > 0 ? formatFR(summary.totalImpact, 0) : '—'}
          unit={`${NBSP}€/an`}
          semantic="cost"
          headline={interpretMonitoringDrift({
            totalImpact: summary.totalImpact,
            topContributors: summary.topImpact,
          })}
          source={{
            kind: 'Estimation',
            origin: 'prix moyen × kWh excès',
            freshness: summary.topImpact.length > 0
              ? `${summary.topImpact.length}${NBSP}contributeurs`
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
        title="Consommation patrimoine · 12 mois"
        meta={`${trajectoryData.length}${NBSP}mois · baseline moyenne normalisée DJU`}
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
        <SolTrajectoryChart
          data={trajectoryData}
          dataKey="value"
          targetLine={null}
          userLine={baseline}
          userLabel={baseline != null ? `Baseline ${formatFR(baseline, 0)}${NBSP}MWh/mois` : ''}
          yDomain={yDomain}
          yLabel="MWh"
          showThresholdZones={false}
          caption={
            trajectoryData.length > 0 ? (
              <>
                <strong style={{ color: 'var(--sol-ink-900)' }}>
                  Baseline {formatFR(baseline || 0, 0)}{NBSP}MWh/mois
                </strong>
                {' '}(moyenne 12 mois) · dérives cumulées estimées{' '}
                {formatFREur(summary.totalImpact, 0)}/an.
              </>
            ) : (
              <>Historique de consommation non disponible.</>
            )
          }
          sourceChip={
            <SolSourceChip
              kind="EMS"
              origin="Enedis + GRDF"
              freshness="DJU Météo-France"
            />
          }
        />
      </div>
    </>
  );
}
