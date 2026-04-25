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
import RegulatoryCalendarCard from '../components/RegulatoryCalendarCard';
import ImpactProjectionCard from '../components/ImpactProjectionCard';
import BriefCodexCard from '../components/BriefCodexCard';
// WhatIfScenarioCard retiré /cockpit : trop complexe pour vue exec
// (lecture/scan, pas manipulation interactive). Vit sur /achat-energie.
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

// Seuils relatifs au chiffre énergie (audit Jean-Marc COMEX CAC40) :
// - >10% facture annuelle = critique
// - >5% = warning
// - <5% = ok
// Pour un patrimoine 200 sites à 4M€/an, "10k€" n'a aucun sens — il faut
// normaliser par le poids financier réel.
function getRiskStatus(riskEur, factureAnnuelleEur) {
  if (!factureAnnuelleEur || factureAnnuelleEur <= 0) {
    // Fallback absolu si pas de baseline — seuils CAC40 (M€)
    if (riskEur > 200000) return 'crit';
    if (riskEur > 50000) return 'warn';
    return 'ok';
  }
  const ratio = riskEur / factureAnnuelleEur;
  if (ratio > 0.10) return 'crit';
  if (ratio > 0.05) return 'warn';
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
  // Accordéon "Détails benchmark" — fermé par défaut pour réduire scroll exec.
  // Le COMEX expand seulement s'il veut creuser. Gain ~600px en scroll initial.
  const [showBenchmarkDetails, setShowBenchmarkDetails] = useState(false);

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
      risqueStatus: getRiskStatus(risque, data.billing?.total_eur),
    };
  }, [scopedSites, cockpitKpisFull, data.billing]);

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
      parts.push(`plan d'optimisation à valider`);
    } else {
      parts.push(`surveillance continue sur ${rawKpis.total} sites`);
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
      style={{
        padding: '24px 48px 48px',
        background: 'var(--sol-bg-canvas)',
        minHeight: '100vh',
      }}
    >
      {/* Header sobre — le briefing chiffré vit dans le SolHero (chip "BRIEFING
          EXÉCUTIF · SOL" + headline prescriptif + plan 3 leviers). On garde
          ici l'orgname + breakdown sites pour le contexte exec. */}
      <SolPageHeader
        kicker={kicker}
        title="Bonjour"
        titleEm=" — votre patrimoine cette semaine"
        narrative={`${rawKpis.total} sites · ${rawKpis.conformes} OK · ${rawKpis.nonConformes + rawKpis.aRisque} à risque · ${alertsCount} alerte${alertsCount > 1 ? 's' : ''}`}
        subNarrative="Briefing exécutif synthétisé ci-dessous."
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
          {/* 1. BRIEF SOL — version exécutive : narrative état + chiffrage risque.
              Le PLAN détaillé (3 actions chiffrées) vit dans OpportunitiesCard
              plus bas pour éviter le doublon avec /. Cohérence cross-vues :
              même backend /api/sol/proposal, formats adaptés par persona
              (liste action-first sur / · cards 3-col exec-first sur /cockpit). */}
          <SolHero
            chip="Briefing exécutif"
            title={briefTitle}
            description={briefDescription}
            metrics={[
              {
                label: 'Sites à risque',
                value: `${sitesAtRisk}`,
              },
              {
                label: 'Risque cumulé',
                value: rawKpis.risque > 0 ? formatFREur(rawKpis.risque, 0) : '—',
              },
              {
                label: 'Leviers identifiés',
                value: `${data.solProposal?.actions?.length || 0}`,
              },
            ]}
            primaryLabel="Voir le plan complet"
            onPrimary={() => navigate('/')}
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

          {/* Densification — Brief CODIR + Calendrier réglementaire en
              grid 2-col responsive. Sur écran large, comble le vide droit
              que créait le full-width single column. */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))',
              gap: 16,
              marginBottom: 16,
            }}
          >
            <div>
              <SolSectionHead
                title="Brief exécutif — prêt à présenter"
                meta="Copy-paste CODIR · généré par Sol"
              />
              <BriefCodexCard
                orgName={orgName}
                totalSites={rawKpis.total}
                facture={billing.total_eur}
                conformityScore={scoreNow}
                consoMwh={consoMwh}
                co2Tco2={co2Total}
                sitesAtRisk={sitesAtRisk}
                actionsCount={data.solProposal?.actions?.length || 0}
                totalImpactEur={data.solProposal?.total_impact_eur_per_year || 0}
                alertesCount={alertsCount}
                anomaliesCount={billing.total_insights || 0}
              />
            </div>
            <div>
              <SolSectionHead
                title="Calendrier réglementaire"
                meta="3 prochaines échéances tertiaire"
              />
              <RegulatoryCalendarCard limit={3} />
            </div>
          </div>

          {/* 3. Trajectoire Décret Tertiaire 2030 — compact si data absente
              pour ne pas perdre 155px sur un placeholder. Si trajectoire
              chargée, affiche le composant complet (TrajectorySection). */}
          {cockpitStats.trajectoire?.annees?.length > 0 ? (
            <>
              <SolSectionHead
                title="Trajectoire Décret Tertiaire"
                meta="Progression vers objectif 2030 (-40%)"
              />
              <div style={{ marginBottom: 16 }}>
                <TrajectorySection
                  trajectoire={cockpitStats.trajectoire}
                  loading={false}
                  sites={cockpit.sites}
                />
              </div>
            </>
          ) : (
            <div
              style={{
                background: 'var(--sol-bg-paper)',
                border: '1px dashed var(--sol-ink-200)',
                borderRadius: 6,
                padding: '10px 14px',
                marginBottom: 16,
                fontSize: 12,
                color: 'var(--sol-ink-500)',
                fontFamily: 'var(--sol-font-body)',
                display: 'flex',
                alignItems: 'center',
                gap: 10,
              }}
            >
              <span style={{ fontFamily: 'var(--sol-font-mono)', textTransform: 'uppercase', letterSpacing: '0.08em', fontSize: 10, color: 'var(--sol-ink-700)' }}>
                Trajectoire DT
              </span>
              <span>·</span>
              <span>Données pluriannuelles non disponibles — connexion patrimoine à finaliser.</span>
            </div>
          )}

          {/* AJUSTEMENT PERSONA — Plan d'action PROMU avant Pairs/Vecteurs.
              Scan exec top-down : état → KPIs → marché → trajectoire → PLAN
              → projection 3 ans (WOW) → benchmarks → événements. */}
          {(() => {
            const sourceActions = data.solProposal?.actions || [];
            const oppList =
              sourceActions.length > 0
                ? sourceActions.map((a) => ({
                    id: a.id,
                    label: a.title,
                    sub: `+${(a.impact_eur_per_year || 0).toLocaleString('fr-FR')} €/an · ${a.delay} · ${a.source_module}`,
                    cta: 'Voir l\'action',
                    path: a.action_path,
                  }))
                : opportunities;
            const totalImpact = data.solProposal?.total_impact_eur_per_year || 0;
            return (
              oppList.length > 0 && (
                <>
                  <SolSectionHead
                    title="Plan d'action — leviers à activer"
                    meta={
                      totalImpact > 0
                        ? `${oppList.length} levier${oppList.length > 1 ? 's' : ''} · ${formatFREur(totalImpact, 0)}/an`
                        : `${oppList.length} levier${oppList.length > 1 ? 's' : ''} chiffré${oppList.length > 1 ? 's' : ''}`
                    }
                  />
                  <div style={{ marginBottom: 16 }}>
                    <OpportunitiesCard opportunities={oppList} onNavigate={navigate} />
                  </div>
                </>
              )
            );
          })()}

          {/* WOW-2 : Projection 3 ans avec/sans Sol — gap visuel. Différenciateur
              PROMEOS (aucun concurrent B2B énergie n'affiche ce GAP). Sources :
              solProposal.total_impact_eur_per_year × 3 ans. */}
          {data.solProposal?.total_impact_eur_per_year > 0 && (
            <div style={{ marginBottom: 16 }}>
              <ImpactProjectionCard
                annualImpactEur={data.solProposal.total_impact_eur_per_year}
                actionsCount={data.solProposal.actions?.length || 3}
                onPrimary={() => navigate('/actions')}
              />
            </div>
          )}

          {/* WhatIfScenarioCard retiré : trop complexe pour /cockpit (vue
              exec en lecture/scan, pas en manipulation). Le simulateur a
              sa place sur /achat-energie où l'arbitrage budget se pilote. */}

          {/* Densification — Performance OID + Événements récents en
              grid 2-col responsive. Performance OID = argument DAF, Événements
              = timeline 7j monitoring. Comble le vide droit. */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))',
              gap: 16,
              marginBottom: 16,
            }}
          >
            <div>
              <SolSectionHead
                title="Performance vs pairs OID"
                meta="Benchmark · indice OID/CEREN"
              />
              <PerformanceSitesCard fallbackSites={cockpit.sites || scopedSites} />
            </div>
            <div>
              <SolSectionHead title="Événements récents" meta="Timeline monitoring 7j" />
              <EvenementsRecents />
            </div>
          </div>

          {/* Vecteurs CO₂ + ESG → accordéon (secondaire CFO mais utile pour
              reporting CSRD à la demande). Pleine largeur car expandable. */}
          <div style={{ marginBottom: 16 }}>
            <button
              type="button"
              onClick={() => setShowBenchmarkDetails((s) => !s)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                width: '100%',
                padding: '12px 16px',
                background: 'var(--sol-bg-paper)',
                border: '1px solid var(--sol-ink-200)',
                borderRadius: 8,
                cursor: 'pointer',
                fontSize: 13,
                fontWeight: 600,
                color: 'var(--sol-ink-900)',
                fontFamily: 'var(--sol-font-body)',
              }}
            >
              <span>
                {showBenchmarkDetails ? 'Masquer' : 'Voir'} le détail ESG/CSRD
                <span style={{ fontWeight: 400, color: 'var(--sol-ink-500)', marginLeft: 12, fontSize: 12 }}>
                  — Vecteurs énergétiques + CO₂ scopes 1/2 + delta N-1
                </span>
              </span>
              <span style={{ color: 'var(--sol-ink-400)', fontSize: 18 }}>
                {showBenchmarkDetails ? '−' : '+'}
              </span>
            </button>
            {showBenchmarkDetails && (
              <div style={{ marginTop: 16 }}>
                <SolSectionHead
                  title="Vecteurs & empreinte CO₂"
                  meta="Élec/gaz · scopes 1/2 · vs N-1"
                />
                <VecteurEnergetiqueCard />
              </div>
            )}
          </div>

          {/* Brief CODIR remonté en grid 2-col avec Calendrier (position #5). */}
          {/* Événements récents intégré au grid Performance OID (position #6). */}
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
