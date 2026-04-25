/**
 * PROMEOS — CockpitSol (refonte from-scratch, route /cockpit)
 *
 * Persona : COMEX / Directeur énergie / DG / CFO.
 * Question répondue : « Où on en est, qu'est-ce qui menace budget/trajectoire ? »
 *
 * Doctrine appliquée :
 *   - Briefing exécutif : Sol résume en 1 phrase narrative.
 *   - Multi-stream : KPIs Facture · Conformité · Conso · CO₂ (4 streams).
 *   - Livrable concret : export Rapport COMEX (PDF via window.print).
 *   - 3 modes Surface/Inspect/Expert : densité ajustable.
 *
 * Structure (mode Surface) :
 *   1. Header + LayerToggle + BoutonRapportCOMEX
 *   2. DeadlineBanner
 *   3. SolHero — briefing exécutif Sol
 *   4. SolKpiRow × 4 — Facture / Conformité / Conso / CO₂
 *   5. Trajectoire DT 2030
 *   6. Performance vs pairs OID
 *   7. Vecteurs énergétiques + CO₂ scopes
 *   8. Opportunités (top 3)
 *   9. Événements récents (timeline 7j)
 */
import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  SolPageHeader,
  SolHero,
  SolKpiRow,
  SolKpiCard,
  SolSectionHead,
  SolLayerToggle,
  SolInspectDoc,
  SolExpertGrid,
  SolStatusPill,
} from '../ui/sol';
import { useScope } from '../contexts/ScopeContext';
import {
  getBillingSummary,
  getCockpit,
  getCockpitCo2,
  getNotificationsList,
  getComplianceScoreTrend,
  getComplianceTimeline,
  getSolProposal,
} from '../services/api';
import {
  buildKicker,
  computeDelta,
  freshness,
  formatFR,
  formatFREur,
  formatFRPct,
  NBSP,
} from './cockpit/sol_presenters';
import { SkeletonCard } from '../ui/Skeleton';

// Refonte from-scratch : composants MAIN-récup pour incarner la doctrine
import TrajectorySection from './cockpit/TrajectorySection';
import EvenementsRecents from './cockpit/EvenementsRecents';
import PerformanceSitesCard from './cockpit/PerformanceSitesCard';
import VecteurEnergetiqueCard from './cockpit/VecteurEnergetiqueCard';
import OpportunitiesCard from './cockpit/OpportunitiesCard';
import BoutonRapportCOMEX from './cockpit/BoutonRapportCOMEX';
import DeadlineBanner from '../components/DeadlineBanner';
import { useCockpitData } from '../hooks/useCockpitData';
import {
  buildBriefing,
  buildWatchlist,
  buildOpportunities,
} from '../models/dashboardEssentials';

// ──────────────────────────────────────────────────────────────────────────────

function useCockpitSolData({ orgId } = {}) {
  const [state, setState] = useState({
    status: 'loading',
    billing: null,
    complianceTrend: null,
    cockpit: null,
    notifications: null,
    timeline: null,
    co2: null,
    solProposal: null,
  });

  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, status: 'loading' }));

    Promise.allSettled([
      getBillingSummary().catch(() => null),
      getComplianceScoreTrend({ months: 6 }).catch(() => null),
      getCockpit().catch(() => null),
      getNotificationsList({ org_id: orgId, limit: 10 }).catch(() => null),
      getComplianceTimeline().catch(() => null),
      getCockpitCo2().catch(() => null),
      getSolProposal().catch(() => null),
    ]).then(([billing, compliance, cockpit, notifications, timeline, co2, solProposal]) => {
      if (cancelled) return;
      setState({
        status: 'ready',
        billing: billing.status === 'fulfilled' ? billing.value : null,
        complianceTrend: compliance.status === 'fulfilled' ? compliance.value : null,
        cockpit: cockpit.status === 'fulfilled' ? cockpit.value : null,
        notifications: notifications.status === 'fulfilled' ? notifications.value : null,
        timeline: timeline.status === 'fulfilled' ? timeline.value : null,
        co2: co2.status === 'fulfilled' ? co2.value : null,
        solProposal: solProposal.status === 'fulfilled' ? solProposal.value : null,
      });
    });

    return () => {
      cancelled = true;
    };
  }, [orgId]);

  return state;
}

// ──────────────────────────────────────────────────────────────────────────────

function getRiskStatus(eur) {
  if (eur > 50000) return 'crit';
  if (eur > 10000) return 'warn';
  return 'ok';
}

// ──────────────────────────────────────────────────────────────────────────────

export default function CockpitSol() {
  const scopeCtx = useScope();
  const navigate = useNavigate();
  const scope = scopeCtx?.scope || {};
  const scopedSites = scopeCtx?.scopedSites || [];
  const org = scopeCtx?.org;
  const scopeLabel = scopeCtx?.scopeLabel;
  const sitesCount = scopeCtx?.sitesCount;
  const orgName = org?.name || org?.label || scopeLabel || 'votre patrimoine';
  const [mode, setMode] = useState('surface');

  const data = useCockpitSolData({ orgId: scope.orgId });
  const { kpis: cockpitKpisFull } = useCockpitData();

  // ─── KPIs builder-ready (shape attendue par dashboardEssentials) ──────────

  const rawKpis = useMemo(() => {
    const total = scopedSites.length;
    const conformes = scopedSites.filter((s) => s.statut_conformite === 'conforme').length;
    const nonConformes = scopedSites.filter((s) => s.statut_conformite === 'non_conforme').length;
    const aRisque = scopedSites.filter((s) => s.statut_conformite === 'a_risque').length;
    const risque = scopedSites.reduce((sum, s) => sum + (s.risque_eur || 0), 0);
    const pctConf =
      cockpitKpisFull?.conformiteScore != null
        ? Math.round(cockpitKpisFull.conformiteScore)
        : 0;
    const couvertureDonnees =
      total > 0
        ? Math.round((scopedSites.filter((s) => s.conso_kwh_an > 0).length / total) * 100)
        : 0;
    const compStatus =
      nonConformes > 0 ? 'crit' : aRisque > 0 ? 'warn' : total > 0 ? 'ok' : 'neutral';
    return {
      total,
      conformes,
      nonConformes,
      aRisque,
      risque,
      pctConf,
      couvertureDonnees,
      compStatus,
      risqueStatus: getRiskStatus(risque),
    };
  }, [scopedSites, cockpitKpisFull]);

  // ─── Données existantes pour KPIs ─────────────────────────────────────────

  const billing = data.billing ?? {};
  const cockpit = data.cockpit ?? {};
  const cockpitStats = cockpit.stats ?? {};

  const trendArr = Array.isArray(data.complianceTrend?.trend) ? data.complianceTrend.trend : [];
  const trendLast = trendArr[trendArr.length - 1];
  const scoreNow =
    cockpitStats.compliance_score ??
    (trendLast?.score != null ? Math.round(trendLast.score * 10) / 10 : null);
  const scorePrev = trendArr.length >= 2 ? trendArr[0]?.score : null;
  const scoreDelta =
    scorePrev != null && scoreNow != null
      ? computeDelta({
          current: scoreNow,
          previous: scorePrev,
          unit: 'pts',
          context: `sur${NBSP}${trendArr.length}${NBSP}mois`,
        })
      : null;

  const consoKwh = cockpitStats.conso_kwh_total ?? billing.total_kwh ?? null;
  const consoMwh = consoKwh != null ? consoKwh / 1000 : null;

  // CO₂ : source canonique = endpoint /api/cockpit/co2 (même que VecteurEnergetiqueCard
  // plus bas → garantit cohérence des chiffres entre KPI haut et card détail).
  // Backend retourne total_co2_tonnes mais peut être 0 même quand sites[] a des t_co2.
  // On somme depuis sites[].t_co2 en fallback (somme défensive, pas du calcul métier).
  const co2Total = useMemo(() => {
    const direct = data.co2?.total_co2_tonnes ?? data.co2?.total_t_co2 ?? null;
    if (direct != null && direct > 0) return direct;
    const sites = Array.isArray(data.co2?.sites) ? data.co2.sites : [];
    if (sites.length === 0) return null;
    const sum = sites.reduce((s, site) => s + (Number(site.t_co2) || 0), 0);
    return sum > 0 ? Math.round(sum * 10) / 10 : null;
  }, [data.co2]);
  const co2DeltaPct = data.co2?.delta_total_pct ?? null;
  const co2Year = data.co2?.year ?? data.co2?.annee_ref ?? new Date().getFullYear();

  // Notifications + alertes
  const notifList = Array.isArray(data.notifications)
    ? data.notifications
    : data.notifications?.items || data.notifications?.events || [];
  const alertsCount =
    cockpitStats.alertes_actives ??
    cockpit?.action_center?.total_issues ??
    notifList.filter((n) => n?.severity === 'critical' || n?.severity === 'high').length;

  // ─── Builders pour Briefing exécutif + Opportunités ───────────────────────

  const watchlist = useMemo(
    () => buildWatchlist(rawKpis, scopedSites),
    [rawKpis, scopedSites]
  );
  const opportunities = useMemo(
    () => buildOpportunities(rawKpis, scopedSites, { isExpert: mode === 'expert' }),
    [rawKpis, scopedSites, mode]
  );
  const briefing = useMemo(
    () => buildBriefing(rawKpis, watchlist, alertsCount),
    [rawKpis, watchlist, alertsCount]
  );

  // Brief Sol — narration 1 phrase + 3 métriques horizontales (SolHero metrics).
  const briefMetrics = useMemo(() => {
    const m = [];
    if (billing.total_eur != null)
      m.push({ label: 'Facture', value: formatFREur(billing.total_eur, 0) });
    if (scoreNow != null) m.push({ label: 'Conformité', value: `${scoreNow}/100` });
    if (consoMwh != null) m.push({ label: 'Consommation', value: `${formatFR(consoMwh, 0)} MWh` });
    return m.slice(0, 3);
  }, [billing, scoreNow, consoMwh]);

  // Brief prescriptif : titre = menace ou opportunité concrète,
  // description = chiffrage du risque + nombre de leviers proposés.
  const sitesAtRisk = rawKpis.aRisque + rawKpis.nonConformes;
  const briefTitle = useMemo(() => {
    if (sitesAtRisk > 0) {
      return `${sitesAtRisk} site${sitesAtRisk > 1 ? 's' : ''} ${sitesAtRisk > 1 ? 'menacent' : 'menace'} votre trajectoire 2030`;
    }
    if (rawKpis.risque > 50000) {
      return `Risque budgétaire ${formatFREur(rawKpis.risque, 0)} à arbitrer cette semaine`;
    }
    if (alertsCount > 0) {
      return `${alertsCount} signal${alertsCount > 1 ? 'aux' : ''} fort${alertsCount > 1 ? 's' : ''} demandent votre arbitrage`;
    }
    if (opportunities.length > 0) {
      return `${opportunities.length} levier${opportunities.length > 1 ? 's' : ''} d'optimisation activable${opportunities.length > 1 ? 's' : ''}`;
    }
    return 'Patrimoine sous contrôle cette semaine';
  }, [sitesAtRisk, rawKpis.risque, alertsCount, opportunities.length]);

  const briefDescription = useMemo(() => {
    const parts = [];
    if (rawKpis.risque > 0) {
      parts.push(`Risque cumulé ${formatFREur(rawKpis.risque, 0)}`);
    }
    if (opportunities.length > 0) {
      parts.push(
        `${opportunities.length} levier${opportunities.length > 1 ? 's' : ''} identifié${opportunities.length > 1 ? 's' : ''} par Sol`
      );
    } else if (sitesAtRisk > 0) {
      parts.push(`Sol prépare un plan d'optimisation`);
    } else {
      parts.push(`Sol surveille en continu vos ${rawKpis.total} sites`);
    }
    if (billing.total_insights > 0) {
      parts.push(
        `${billing.total_insights} anomalie${billing.total_insights > 1 ? 's' : ''} facture détectée${billing.total_insights > 1 ? 's' : ''}`
      );
    }
    return parts.join(' · ') + '.';
  }, [rawKpis.risque, rawKpis.total, sitesAtRisk, opportunities.length, billing.total_insights]);

  // Freshness pour SolKpiCard sources
  const dataFreshness = useMemo(() => {
    const ts =
      data.cockpit?.stats?.compliance_computed_at || data.notifications?.[0]?.created_at || null;
    return freshness(ts);
  }, [data.cockpit, data.notifications]);

  // Header
  const kicker = buildKicker({
    module: 'Cockpit',
    scope: { orgName, sitesCount },
  });

  // ─── Rendu ───────────────────────────────────────────────────────────────

  if (data.status === 'loading') {
    return (
      <div style={{ padding: '32px 48px' }}>
        <SkeletonCard lines={1} />
        <SkeletonCard lines={3} />
        <SkeletonCard lines={5} />
      </div>
    );
  }

  return (
    <div
      style={{ padding: '32px 48px 60px', background: 'var(--sol-bg-canvas)', minHeight: '100vh' }}
    >
      {/* Header sobre — le briefing chiffré vit dans le SolHero (chip "BRIEFING
          EXÉCUTIF · SOL" + headline prescriptif + plan 3 leviers). On garde
          ici l'orgname + breakdown sites pour le contexte exec. */}
      <SolPageHeader
        kicker={kicker}
        title="Bonjour "
        titleEm="— votre patrimoine cette semaine"
        narrative={`${rawKpis.total} sites · ${rawKpis.conformes} OK · ${rawKpis.nonConformes + rawKpis.aRisque} à risque · ${alertsCount} alerte${alertsCount > 1 ? 's' : ''}`}
        subNarrative="Sol prépare le briefing exécutif ci-dessous."
        rightSlot={
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <BoutonRapportCOMEX />
            <SolLayerToggle value={mode} onChange={setMode} />
          </div>
        }
      />

      {/* Urgence régulatoire (cross-vues canonique) */}
      <DeadlineBanner />

      {/* Mode SURFACE — Briefing exécutif Sol → KPIs → Trajectoire → benchmark → CO₂ → opportunités → événements */}
      {mode === 'surface' && (
        <>
          {/* 1. BRIEF SOL — alimenté par /api/sol/proposal (même source que /).
              Headline prescriptif chiffré + 3 metrics KPIs exécutifs + plan
              d'action structuré (3 leviers chiffrés) + CTAs export brief. */}
          <SolHero
            chip="Briefing exécutif · Sol"
            title={data.solProposal?.headline || briefTitle}
            description={
              data.solProposal
                ? `${briefDescription} Sources : ${(data.solProposal.sources || []).join(' · ')}.`
                : briefDescription
            }
            metrics={briefMetrics}
            actions={data.solProposal?.actions || []}
            onAction={(path) => path && navigate(path)}
            primaryLabel="Voir les actions prioritaires"
            onPrimary={() => navigate('/actions')}
            secondaryLabel="Exporter le brief"
            onSecondary={() => window.print()}
          />

          {/* 2. SolKpiRow × 4 — Facture · Conformité · Consommation · CO₂ */}
          <SolKpiRow columns={4}>
            <SolKpiCard
              label="Facture énergie · période"
              explainKey="billing_total_current_month"
              value={billing.total_eur != null ? formatFR(billing.total_eur, 0) : '—'}
              unit={`${NBSP}€${NBSP}HT`}
              semantic="cost"
              headline={
                billing.total_invoices
                  ? `${billing.total_invoices} factures · ${billing.total_insights ?? 0} anomalie${(billing.total_insights ?? 0) > 1 ? 's' : ''}`
                  : "Importez vos factures pour déclencher l'analyse."
              }
              source={{
                kind: 'Factures',
                origin: billing.engine_version ? `shadow ${billing.engine_version}` : 'shadow billing',
                freshness: billing.coverage_months ? `${billing.coverage_months}${NBSP}mois couverts` : dataFreshness,
              }}
            />
            <SolKpiCard
              label="Conformité Décret tertiaire"
              explainKey="compliance_score_dt"
              value={scoreNow != null ? `${scoreNow}` : '—'}
              unit="/100"
              delta={scoreDelta}
              semantic="score"
              headline={
                scoreNow == null
                  ? 'Score en cours de calcul.'
                  : scoreNow >= 75
                    ? 'Trajectoire solide vers 2030.'
                    : scoreNow >= 60
                      ? 'Vigilance — quelques sites en retard.'
                      : 'Risque — plan d\'action prioritaire.'
              }
              source={{
                kind: 'RegOps',
                origin: cockpitStats.compliance_source || 'canonique',
                freshness: cockpitStats.sites_evaluated ? `${cockpitStats.sites_evaluated}${NBSP}sites` : dataFreshness,
              }}
            />
            <SolKpiCard
              label="Consommation · patrimoine"
              explainKey="usage_total_mwh"
              value={consoMwh != null ? formatFR(consoMwh, 0) : '—'}
              unit={`${NBSP}MWh`}
              semantic="conso"
              headline={
                cockpitStats.conso_sites_with_data
                  ? `${cockpitStats.conso_sites_with_data}${NBSP}sites avec données`
                  : 'Cumul Enedis + GRDF agrégé.'
              }
              source={{
                kind: cockpitStats.conso_source || 'Enedis + GRDF',
                freshness:
                  cockpitStats.conso_confidence && cockpitStats.conso_confidence !== 'none'
                    ? `confiance ${cockpitStats.conso_confidence}`
                    : dataFreshness,
              }}
            />
            <SolKpiCard
              label="Empreinte CO₂"
              explainKey="co2_total_tco2eq"
              value={co2Total != null ? formatFR(co2Total, 0) : '—'}
              unit={`${NBSP}tCO₂eq`}
              delta={
                co2DeltaPct != null
                  ? {
                      text: `${co2DeltaPct > 0 ? '+' : ''}${co2DeltaPct.toFixed(1)}% vs ${co2Year - 1}`,
                      kind: co2DeltaPct < 0 ? 'good' : co2DeltaPct > 0 ? 'bad' : 'neutral',
                    }
                  : null
              }
              semantic="conso"
              headline={
                co2Total != null
                  ? `Scopes 1+2 cumulés ${co2Year} · facteurs ADEME V23.6.`
                  : 'Données CO₂ en cours de calcul.'
              }
              source={{
                kind: 'ADEME V23.6',
                origin: 'facteurs canoniques',
                freshness: dataFreshness,
              }}
            />
          </SolKpiRow>

          {/* 3. Trajectoire Décret Tertiaire 2030 */}
          <SolSectionHead
            title="Trajectoire Décret Tertiaire"
            meta="Progression vers objectif 2030 (-40%)"
          />
          <div style={{ marginBottom: 24 }}>
            <TrajectorySection
              trajectoire={cockpitStats.trajectoire}
              loading={false}
              sites={cockpit.sites}
            />
          </div>

          {/* 4 + 5 — Performance OID & Vecteurs CO₂ pairés en grid 2-col
              (densités similaires, évite le vide horizontal sur écran large).
              align-items stretch + flex column wrappers → cards parfaitement alignées. */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
              gap: 16,
              marginBottom: 24,
              alignItems: 'stretch',
            }}
          >
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <SolSectionHead
                title="Performance vs pairs OID"
                meta="Benchmark par usage · top 5 sites"
              />
              <div style={{ flex: 1, display: 'flex' }}>
                <div style={{ width: '100%' }}>
                  <PerformanceSitesCard fallbackSites={cockpit.sites || scopedSites} />
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <SolSectionHead
                title="Vecteurs & empreinte CO₂"
                meta="Élec/gaz · scopes 1/2 · vs N-1"
              />
              <div style={{ flex: 1, display: 'flex' }}>
                <div style={{ width: '100%' }}>
                  <VecteurEnergetiqueCard />
                </div>
              </div>
            </div>
          </div>

          {/* 6. Opportunités économiques (top 3) */}
          {opportunities.length > 0 && (
            <>
              <SolSectionHead
                title="Opportunités à activer"
                meta={`${opportunities.length} levier${opportunities.length > 1 ? 's' : ''} identifié${opportunities.length > 1 ? 's' : ''}`}
              />
              <div style={{ marginBottom: 24 }}>
                <OpportunitiesCard opportunities={opportunities} onNavigate={navigate} />
              </div>
            </>
          )}

          {/* 7. Événements récents (timeline 7j) */}
          <SolSectionHead title="Événements récents" meta="Timeline monitoring 7j" />
          <div style={{ marginBottom: 24 }}>
            <EvenementsRecents />
          </div>
        </>
      )}

      {/* Mode INSPECT — lecture éditoriale prose */}
      {mode === 'inspect' && (
        <>
          <SolSectionHead
            title="Pourquoi ces chiffres méritent votre attention"
            meta="lecture approfondie"
          />
          <SolInspectDoc>
            <p
              style={{
                fontSize: 18,
                color: 'var(--sol-ink-900)',
                fontWeight: 500,
                marginBottom: 24,
              }}
            >
              Votre patrimoine a été facturé{' '}
              <strong>{billing.total_eur != null ? formatFREur(billing.total_eur, 0) : '—'}</strong>
              {' '}sur la période analysée.{' '}
              {billing.total_insights
                ? `${billing.total_insights} anomalie${billing.total_insights > 1 ? 's' : ''} détectée${billing.total_insights > 1 ? 's' : ''} par le moteur shadow billing.`
                : 'Aucune anomalie détectée.'}
            </p>
            <h3 style={{ fontSize: 20, fontWeight: 600, margin: '24px 0 10px' }}>
              §1. Ce que Sol voit
            </h3>
            <p>
              {billing.total_invoices
                ? `${billing.total_invoices} factures ont été analysées, couvrant ${billing.coverage_months ?? '—'}${NBSP}mois. Le moteur ${billing.engine_version ?? 'shadow billing'} compare chaque ligne aux barèmes réglementaires en vigueur.`
                : "Le moteur shadow billing est prêt. Importez vos factures pour commencer l'analyse."}
            </p>
            <h3 style={{ fontSize: 20, fontWeight: 600, margin: '24px 0 10px' }}>
              §2. Votre conformité
            </h3>
            <p>
              Votre score Décret tertiaire est de <strong>{scoreNow ?? '—'}/100</strong>
              {scoreDelta ? ` (${scoreDelta.text})` : ''}. Le seuil d'alerte se situe à 60/100 ;
              en-dessous, une réaction rapide est nécessaire pour tenir la trajectoire −25 % à 2030.
            </p>
            <h3 style={{ fontSize: 20, fontWeight: 600, margin: '24px 0 10px' }}>
              §3. Ce que Sol observe
            </h3>
            <p>
              {alertsCount === 0
                ? 'Aucun signal fort cette semaine. Votre patrimoine tourne au rythme attendu.'
                : `${alertsCount} point${alertsCount > 1 ? 's' : ''} nécessite${alertsCount > 1 ? 'nt' : ''} votre attention. Les signaux sont détaillés dans le mode Surface.`}
            </p>
            <div
              style={{
                fontSize: 12,
                color: 'var(--sol-ink-500)',
                fontFamily: 'var(--sol-font-body)',
                borderTop: '1px solid var(--sol-rule)',
                paddingTop: 12,
                marginTop: 24,
              }}
            >
              Sources : shadow billing v4.2 · Enedis DataConnect · RegOps canonique · GRDF · ADEME V23.6.
            </div>
          </SolInspectDoc>
        </>
      )}

      {/* Mode EXPERT — table dense KPIs détaillés */}
      {mode === 'expert' && (
        <>
          <SolSectionHead
            title="Expert · KPIs détaillés"
            meta={`${rawKpis.total} sites scoped`}
          />
          <SolExpertGrid
            columns={[
              { key: 'metric', label: 'Indicateur', align: 'left' },
              { key: 'value', label: 'Valeur', align: 'right', num: true },
              { key: 'delta', label: 'Évolution', align: 'right', num: false },
              { key: 'source', label: 'Source', align: 'left' },
              { key: 'status', label: 'État', align: 'right' },
            ]}
            rows={[
              {
                key: 'cost',
                cells: {
                  metric: 'Facture énergie',
                  value: billing.total_eur != null ? formatFREur(billing.total_eur, 0) : '—',
                  delta: '—',
                  source: 'Factures fournisseur',
                  status: (
                    <SolStatusPill kind="ok">
                      {billing.total_invoices ? `${billing.total_invoices}${NBSP}fact.` : 'Aucune'}
                    </SolStatusPill>
                  ),
                },
              },
              {
                key: 'score',
                cells: {
                  metric: 'Conformité DT',
                  value: scoreNow != null ? `${scoreNow}/100` : '—',
                  delta: scoreDelta?.text || '—',
                  source: 'RegOps canonique',
                  status: (
                    <SolStatusPill kind={scoreNow >= 75 ? 'ok' : scoreNow >= 60 ? 'att' : 'risk'}>
                      {scoreNow >= 75 ? 'Solide' : scoreNow >= 60 ? 'Vigilance' : 'Risque'}
                    </SolStatusPill>
                  ),
                },
              },
              {
                key: 'conso',
                cells: {
                  metric: 'Consommation',
                  value: consoMwh != null ? `${formatFR(consoMwh, 0)}${NBSP}MWh` : '—',
                  delta: '—',
                  source: cockpitStats.conso_source || 'Enedis + GRDF',
                  status: (
                    <SolStatusPill kind={cockpitStats.conso_confidence === 'high' ? 'ok' : 'att'}>
                      {cockpitStats.conso_confidence || 'n/d'}
                    </SolStatusPill>
                  ),
                },
              },
              {
                key: 'co2',
                cells: {
                  metric: 'CO₂eq cumulé',
                  value: co2Total != null ? `${formatFR(co2Total, 0)}${NBSP}tCO₂` : '—',
                  delta: co2DeltaPct != null ? `${co2DeltaPct > 0 ? '+' : ''}${co2DeltaPct.toFixed(1)}%` : '—',
                  source: 'ADEME V23.6',
                  status: (
                    <SolStatusPill kind={co2Total != null ? 'ok' : 'att'}>
                      {co2Total != null ? 'Calculé' : 'En attente'}
                    </SolStatusPill>
                  ),
                },
              },
              {
                key: 'alerts',
                cells: {
                  metric: 'Signaux semaine',
                  value: `${alertsCount}`,
                  delta: '—',
                  source: 'Notifications',
                  status: (
                    <SolStatusPill kind={alertsCount === 0 ? 'ok' : alertsCount <= 2 ? 'att' : 'risk'}>
                      {alertsCount === 0 ? 'RAS' : alertsCount <= 2 ? 'À voir' : 'Vigilance'}
                    </SolStatusPill>
                  ),
                },
              },
              {
                key: 'risque',
                cells: {
                  metric: 'Risque cumulé',
                  value: `${formatFR(rawKpis.risque, 0)}${NBSP}€`,
                  delta: '—',
                  source: 'Scoring sites',
                  status: (
                    <SolStatusPill kind={rawKpis.risqueStatus === 'crit' ? 'risk' : rawKpis.risqueStatus === 'warn' ? 'att' : 'ok'}>
                      {rawKpis.risqueStatus === 'crit' ? 'Élevé' : rawKpis.risqueStatus === 'warn' ? 'Modéré' : 'Faible'}
                    </SolStatusPill>
                  ),
                },
              },
            ]}
          />
        </>
      )}
    </div>
  );
}
