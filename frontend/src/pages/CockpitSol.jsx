/**
 * PROMEOS — CockpitSol (Phase 2, refonte Sol V1)
 *
 * Cockpit exécutif branché sur les APIs main réelles (aucun mock, aucun fetch
 * dans les composants Sol).
 *
 * APIs consommées (inchangées) :
 *   - getBillingSummary({ scope })           → KPI facture + delta
 *   - getComplianceScoreTrend({ scope })     → KPI score DT + delta
 *   - getCockpit()                           → KPI conso patrimoine
 *   - getNotificationsSummary(orgId, siteId) → alertes / signaux
 *   - getComplianceTimeline()                → échéances + validations
 *   - getEmsTimeseries({ granularity:'30min'}) → courbe de charge
 *
 * Zéro logique métier ici : seulement des helpers présentation purs
 * (sol_presenters.js + sol_interpreters.jsx).
 *
 * 3 modes : Surface (par défaut) · Inspect (prose éditoriale) · Expert (table dense).
 */
import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  SolPageHeader,
  SolHero,
  SolKpiRow,
  SolKpiCard,
  SolSourceChip,
  SolSectionHead,
  SolWeekGrid,
  SolWeekCard,
  SolLoadCurve,
  SolLayerToggle,
  SolInspectDoc,
  SolExpertGrid,
  SolStatusPill,
} from '../ui/sol';
import { useScope } from '../contexts/ScopeContext';
import {
  getBillingSummary,
  getCockpit,
  getNotificationsList,
  getComplianceScoreTrend,
  getComplianceTimeline,
  getEmsTimeseries,
} from '../services/api';
import {
  buildKicker,
  buildWeekSignals,
  buildFallbackLoadCurve,
  computeDelta,
  computeHPShare,
  findPeak,
  freshness,
  adaptEmsSeriesToLoadCurve,
  formatFR,
  formatFREur,
  formatFRPct,
  NBSP,
} from './cockpit/sol_presenters';
import {
  interpretCompliance,
  buildCockpitNarrative,
  buildCockpitSubNarrative,
} from './cockpit/sol_interpreters';
import { SkeletonCard } from '../ui/Skeleton';
import { businessErrorFallback } from '../i18n/business_errors';

// Sprint P6 S2 — Enrichissement superset MAIN (Batch 2 Vue exécutive)
// Imports composants MAIN standalone pour parité fonctionnelle
import AlertesPrioritaires from './cockpit/AlertesPrioritaires';
import TrajectorySection from './cockpit/TrajectorySection';
import EvenementsRecents from './cockpit/EvenementsRecents';
import HeroImpactBar from './cockpit/HeroImpactBar';
import SanteKpiGrid from './cockpit/SanteKpiGrid';
import PriorityActions from './cockpit/PriorityActions';
import { ChevronDown, ChevronUp } from 'lucide-react';

const SOL_PROPOSAL_EMPTY_STYLE = {
  margin: '16px 0 24px',
  padding: '14px 18px',
  background: 'var(--sol-bg-paper)',
  border: '1px dashed var(--sol-ink-200)',
  borderRadius: 6,
  color: 'var(--sol-ink-500)',
  fontFamily: 'var(--sol-font-body)',
  fontSize: 13,
  lineHeight: 1.5,
};

// ──────────────────────────────────────────────────────────────────────────────
// Async data hook — charge en parallèle les 6 endpoints Cockpit.
// Zero state management framework : useState + useEffect, pattern PROMEOS.
// ──────────────────────────────────────────────────────────────────────────────

function useCockpitSolData({ orgId, siteId } = {}) {
  const [state, setState] = useState({
    status: 'loading',
    billing: null,
    compliance: null,
    cockpit: null,
    notifications: null,
    timeline: null,
    emsSeries: null,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, status: 'loading', error: null }));

    // Fix M-02-bis Sprint P0 : backend /api/ems/timeseries exige site_ids
    // obligatoire + dates YYYY-MM-DD (date-only, pas ISO complet avec T...Z).
    // Si pas de siteId scope, on skip l'appel EMS (pattern "no-site=no-data").
    const dateTo = new Date();
    const dateFrom = new Date();
    dateFrom.setDate(dateFrom.getDate() - 1);
    const isoDate = (d) => d.toISOString().split('T')[0];
    const hasSite = Boolean(siteId);
    const emsParams = hasSite
      ? {
          site_ids: String(siteId),
          date_from: isoDate(dateFrom),
          date_to: isoDate(dateTo),
          granularity: '30min',
          mode: 'aggregate',
          metric: 'kw',
        }
      : null;

    Promise.allSettled([
      getBillingSummary().catch(() => null),
      getComplianceScoreTrend({ months: 6 }).catch(() => null),
      getCockpit().catch(() => null),
      getNotificationsList({ org_id: orgId, limit: 10 }).catch(() => null),
      getComplianceTimeline().catch(() => null),
      emsParams ? getEmsTimeseries(emsParams).catch(() => null) : Promise.resolve(null),
    ]).then(([billing, compliance, cockpit, notifications, timeline, ems]) => {
      if (cancelled) return;
      setState({
        status: 'ready',
        billing: billing.status === 'fulfilled' ? billing.value : null,
        complianceTrend: compliance.status === 'fulfilled' ? compliance.value : null,
        cockpit: cockpit.status === 'fulfilled' ? cockpit.value : null,
        notifications: notifications.status === 'fulfilled' ? notifications.value : null,
        timeline: timeline.status === 'fulfilled' ? timeline.value : null,
        emsSeries: ems.status === 'fulfilled' ? ems.value : null,
        error: null,
      });
    });

    return () => {
      cancelled = true;
    };
  }, [orgId, siteId]);

  return state;
}

// ──────────────────────────────────────────────────────────────────────────────

export default function CockpitSol() {
  const scopeCtx = useScope();
  const navigate = useNavigate();
  const scope = scopeCtx?.scope || {};
  const org = scopeCtx?.org;
  const scopeLabel = scopeCtx?.scopeLabel;
  const sitesCount = scopeCtx?.sitesCount;
  const orgName = org?.name || org?.label || scopeLabel || 'votre patrimoine';
  const [mode, setMode] = useState('surface');
  // Sprint P6 S2 Batch 2 : accordion Zone 4 détail (MAIN-parity)
  const [showDetailZone, setShowDetailZone] = useState(false);

  const data = useCockpitSolData({
    orgId: scope.orgId,
    siteId: scope.siteId,
  });

  // ─── Dérivations présentation ──────────────────────────────────────────────

  // Phase 4.6 branchera GET /api/sol/pending ici.
  const solProposal = null;

  const kicker = buildKicker({
    module: 'Cockpit',
    scope: { orgName, sitesCount },
  });

  // KPI 1 : facture énergie (shape réelle : billing.total_eur, total_kwh, total_invoices)
  const billing = data.billing ?? {};
  const kpiCostValue = billing.total_eur;
  // Pas de previous_cost dans /billing/summary → delta non calculable ici,
  // nécessite getBillingCompareMonthly() qu'on ajoutera dans une mini-phase suivante.
  const kpiCostDelta = null;

  // KPI 2 : conformité DT — /cockpit.stats.compliance_score en priorité,
  // fallback sur /compliance/score-trend dernier point (l'endpoint /cockpit
  // peut retourner 500 dans certaines configs scope — fallback mandatoire).
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

  // KPI 3 : conso patrimoine — /cockpit.stats.conso_kwh_total en priorité,
  // fallback sur billing.total_kwh (facturation = proxy consommation).
  const consoKwhPrimary = cockpitStats.conso_kwh_total;
  const consoKwhFallback = billing.total_kwh;
  const consoKwh = consoKwhPrimary ?? consoKwhFallback ?? null;
  const consoMwh = consoKwh != null ? consoKwh / 1000 : null;
  const consoSource = consoKwhPrimary != null ? 'Enedis + GRDF' : 'Factures (estimation)';
  const consoDelta = null;

  // Narratives — alertes : compteur stats en priorité, sinon longueur liste notifications.
  const notifList = Array.isArray(data.notifications)
    ? data.notifications
    : data.notifications?.items || data.notifications?.events || [];
  const alertsCount =
    cockpitStats.alertes_actives ??
    cockpit?.action_center?.total_issues ??
    notifList.filter((n) => n?.severity === 'critical' || n?.severity === 'high').length;
  const topAlertTitle = notifList[0]?.title;

  // Week signals — notifications (array) + timeline /compliance/timeline.events[]
  // Backend shapes :
  //   notifications = array directe avec {severity, title, message, deeplink_path, ...}
  //   timeline = { events: [{status: 'passed'|'upcoming'|'future', label, deadline, ...}] }
  // Backend utilise 'passed' pour les échéances validées (pas 'validated'/'completed').
  const weekCards = useMemo(() => {
    const notifs = Array.isArray(data.notifications)
      ? data.notifications
      : data.notifications?.items || data.notifications?.events || [];
    const timelineRaw = data.timeline;
    const timelineItems = Array.isArray(timelineRaw)
      ? timelineRaw
      : timelineRaw?.events || timelineRaw?.items || [];
    // Filtrer critical en priorité pour l'alerte "à regarder"
    const sortedAlerts = [...notifs].sort((a, b) => {
      const rank = { critical: 0, high: 1, warn: 2, info: 3 };
      return (rank[a?.severity] ?? 9) - (rank[b?.severity] ?? 9);
    });
    const upcoming = timelineItems
      .filter((t) => t?.status === 'upcoming')
      .sort((a, b) => new Date(a.deadline) - new Date(b.deadline));
    const validated = timelineItems.filter((t) => t?.status === 'passed');
    return buildWeekSignals({
      alerts: sortedAlerts,
      upcomingItems: upcoming,
      validatedItems: validated,
      scope: { sitesCount: cockpitStats.total_sites },
      onNavigate: (path) => navigate(path),
    });
  }, [data.notifications, data.timeline, cockpitStats.total_sites, navigate]);

  // Load curve — EMS réel si dispo, sinon fallback courbe 24h type bureau
  // (la signature visuelle de la maquette doit toujours être présente).
  const loadCurveData = useMemo(() => {
    const raw = data.emsSeries?.series?.[0]?.data || data.emsSeries?.data || [];
    const adapted = adaptEmsSeriesToLoadCurve(raw);
    return adapted.length > 0 ? adapted : buildFallbackLoadCurve();
  }, [data.emsSeries]);
  const loadCurveIsMock = !(
    data.emsSeries?.series?.[0]?.data?.length || data.emsSeries?.data?.length
  );

  const peak = useMemo(() => findPeak(loadCurveData, 'kW'), [loadCurveData]);
  const hpShare = useMemo(() => computeHPShare(loadCurveData), [loadCurveData]);

  // Freshness — timestamp dominant pour la section "Cette semaine"
  const dataFreshness = useMemo(() => {
    const ts =
      data.cockpit?.stats?.compliance_computed_at || data.notifications?.[0]?.created_at || null;
    return freshness(ts);
  }, [data.cockpit, data.notifications]);

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
      <SolPageHeader
        kicker={kicker}
        title="Bonjour "
        titleEm="— voici votre semaine"
        narrative={buildCockpitNarrative({ alertsCount, topAlertTitle })}
        subNarrative={buildCockpitSubNarrative({
          sitesCount: cockpit.total_sites ?? cockpit.sites_count,
          nextComexDays: cockpit.next_comex_days,
        })}
        rightSlot={<SolLayerToggle value={mode} onChange={setMode} />}
      />

      {/* User request : "Cette semaine chez vous" juste après header sur les 2 vues */}
      <SolSectionHead
        title="Cette semaine chez vous"
        meta={`${weekCards.length} points · actualisé ${dataFreshness}`}
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

      {/* Sol Hero "proposition agentique" — affiché uniquement si disponible (pas d'empty state verbeux) */}
      {mode === 'surface' && solProposal && (
        <SolHero
          chip="Sol propose · action agentique"
          title={solProposal.title_fr}
          description={solProposal.summary_fr}
        />
      )}
      {mode === 'surface' && (
        <>
          <SolKpiRow>
            <SolKpiCard
              label="Facture énergie · période"
              explainKey="billing_total_current_month"
              value={kpiCostValue != null ? formatFR(kpiCostValue, 0) : '—'}
              unit={`${NBSP}€${NBSP}HT`}
              delta={kpiCostDelta}
              semantic="cost"
              headline={
                billing.total_invoices
                  ? `${billing.total_invoices} factures analysées · ${billing.total_insights ?? 0} anomalie${(billing.total_insights ?? 0) > 1 ? 's' : ''}.`
                  : "Importez vos factures pour déclencher l'analyse."
              }
              source={{
                kind: 'Factures',
                origin: billing.engine_version ? `shadow ${billing.engine_version}` : undefined,
                freshness:
                  billing.last_updated || billing.coverage_months
                    ? `${billing.coverage_months ?? '—'}${NBSP}mois couverts`
                    : undefined,
              }}
            />
            <SolKpiCard
              label="Conformité Décret tertiaire"
              explainKey="compliance_score_dt"
              value={scoreNow != null ? `${scoreNow}` : '—'}
              unit="/100"
              delta={scoreDelta}
              semantic="score"
              headline={interpretCompliance({
                score: scoreNow,
                sitesAtRisk: cockpitStats.sites_tertiaire_ko,
              })}
              source={{
                kind: 'RegOps',
                origin: cockpitStats.compliance_source || 'canonique',
                freshness: cockpitStats.sites_evaluated
                  ? `${cockpitStats.sites_evaluated}${NBSP}sites évalués`
                  : undefined,
              }}
            />
            <SolKpiCard
              label="Consommation · patrimoine"
              explainKey="usage_total_mwh"
              value={consoMwh != null ? formatFR(consoMwh, 0) : '—'}
              unit={`${NBSP}MWh`}
              delta={consoDelta}
              semantic="conso"
              headline={
                cockpitStats.conso_sites_with_data
                  ? `${cockpitStats.conso_sites_with_data}${NBSP}sites avec données · période glissante.`
                  : billing.total_invoices
                    ? `Estimée depuis ${billing.total_invoices}${NBSP}factures analysées.`
                    : 'Données de consommation en cours de collecte.'
              }
              source={{
                kind: consoSource,
                freshness:
                  cockpitStats.conso_confidence && cockpitStats.conso_confidence !== 'none'
                    ? `confiance ${cockpitStats.conso_confidence}`
                    : undefined,
              }}
            />
          </SolKpiRow>

          {/* Sprint P6 S2 — Section MAIN-parity : Alertes prioritaires top 3 (exception-first) */}
          <SolSectionHead
            title="À traiter cette semaine — top 3"
            meta="Priorités par impact business (Rule of 3)"
          />
          <div style={{ marginBottom: 24 }}>
            <AlertesPrioritaires />
          </div>

          {/* Sprint P6 S2 — Section MAIN-parity : Trajectoire Décret Tertiaire */}
          <SolSectionHead
            title="Trajectoire Décret Tertiaire"
            meta="Progression vers objectif 2030 (-40%)"
          />
          <div style={{ marginBottom: 24 }}>
            <TrajectorySection
              trajectoire={cockpitStats.trajectoire}
              loading={data.status === 'loading'}
              sites={cockpit.sites}
            />
          </div>

          {/* Sprint P6 S2 — Section MAIN-parity : Événements récents (timeline) */}
          <SolSectionHead title="Événements récents" meta="Timeline monitoring 7j" />
          <div style={{ marginBottom: 24 }}>
            <EvenementsRecents />
          </div>

          <SolSectionHead
            title={`Courbe de charge · ${loadCurveIsMock ? `aperçu 24${NBSP}h` : 'hier'}`}
            meta={`pas ${loadCurveIsMock ? `1${NBSP}h` : `30${NBSP}min`} · HP / HC tarifaires`}
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
            <SolLoadCurve
              data={loadCurveData}
              peakPoint={peak}
              hpStart="06:00"
              hpEnd="22:00"
              caption={
                <>
                  <strong style={{ color: 'var(--sol-ink-900)' }}>
                    {formatFRPct(Math.round(hpShare * 100))} de votre consommation
                  </strong>{' '}
                  tombe en heures pleines — attendu pour un bureau.
                  {loadCurveIsMock && (
                    <span style={{ color: 'var(--sol-ink-400)', marginLeft: 8 }}>
                      (aperçu estimé, courbe réelle en cours de branchement)
                    </span>
                  )}
                </>
              }
              sourceChip={
                <SolSourceChip
                  kind={loadCurveIsMock ? 'Estimé' : 'Enedis'}
                  origin={loadCurveIsMock ? 'profil bureau' : 'M023'}
                  freshness={loadCurveIsMock ? undefined : 'complète'}
                />
              }
            />
          </div>

          {/* Sprint P6 S2 — Zone 4 accordion : détail complet MAIN-parity */}
          <div style={{ marginTop: 24 }}>
            <button
              type="button"
              onClick={() => setShowDetailZone((s) => !s)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                width: '100%',
                padding: '14px 18px',
                background: 'var(--sol-bg-paper)',
                border: '1px solid var(--sol-ink-200)',
                borderRadius: 8,
                cursor: 'pointer',
                fontSize: 14,
                fontWeight: 600,
                color: 'var(--sol-ink-900)',
                fontFamily: 'var(--sol-font-body)',
              }}
            >
              <span>
                {showDetailZone ? 'Masquer' : 'Voir'} le détail exécutif complet
                <span style={{ fontWeight: 400, color: 'var(--sol-ink-500)', marginLeft: 12 }}>
                  — Impact financier · KPIs santé · Actions prioritaires
                </span>
              </span>
              {showDetailZone ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
            </button>
            {showDetailZone && (
              <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
                {/* HeroImpactBar — impact 4 colonnes */}
                <HeroImpactBar
                  totalEur={cockpitStats.impact_financier_total_eur}
                  conformiteEur={cockpitStats.impact_conformite_eur}
                  facturesEur={cockpitStats.impact_factures_eur}
                  optimisationEur={cockpitStats.impact_optimisation_eur}
                  sitesConcernes={cockpitStats.sites_concernes || []}
                />
                {/* SanteKpiGrid — 4 KPIs santé */}
                <SanteKpiGrid
                  sante={{
                    conformite_score: scoreNow,
                    risque_eur: cockpitStats.risque_eur,
                    conso_kwh: consoKwh,
                    alertes_count: alertsCount,
                    ...(cockpitStats.sante || {}),
                  }}
                />
                {/* PriorityActions — top actions V1+ executive */}
                <PriorityActions actions={cockpit.top_actions || cockpit.priority_actions || []} />
              </div>
            )}
          </div>
        </>
      )}

      {/* ─── Mode INSPECT : lecture éditoriale de la semaine ─── */}
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
              <strong>{kpiCostValue != null ? formatFREur(kpiCostValue, 0) : '—'}</strong> sur la
              période analysée.{' '}
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
              Sources : shadow billing v4.2 · Enedis DataConnect · RegOps canonique · GRDF.
            </div>
          </SolInspectDoc>
        </>
      )}

      {/* ─── Mode EXPERT : table dense anomalies factures ─── */}
      {mode === 'expert' && (
        <>
          <SolSectionHead
            title="Expert · KPIs détaillés"
            meta={`${formatFR(loadCurveData.length)} points · source Enedis`}
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
                  value: kpiCostValue != null ? formatFREur(kpiCostValue, 0) : '—',
                  delta: kpiCostDelta?.text || '—',
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
                  delta: consoDelta?.text || '—',
                  source: cockpitStats.conso_source || 'Enedis + GRDF',
                  status: (
                    <SolStatusPill kind={cockpitStats.conso_confidence === 'high' ? 'ok' : 'att'}>
                      {cockpitStats.conso_confidence || 'n/d'}
                    </SolStatusPill>
                  ),
                },
              },
              {
                key: 'peak',
                cells: {
                  metric: 'Pic J-1',
                  value: peak ? `${peak.value}${NBSP}kW` : '—',
                  delta: peak ? `à ${peak.time}` : '—',
                  source: 'Enedis M023',
                  status: <SolStatusPill kind="ok">Observé</SolStatusPill>,
                },
              },
              {
                key: 'hp',
                cells: {
                  metric: 'Part HP',
                  value: hpShare ? formatFRPct(Math.round(hpShare * 100)) : '—',
                  delta: '—',
                  source: 'Enedis M023',
                  status: <SolStatusPill kind="ok">Calculé</SolStatusPill>,
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
                    <SolStatusPill
                      kind={alertsCount === 0 ? 'ok' : alertsCount <= 2 ? 'att' : 'risk'}
                    >
                      {alertsCount === 0 ? 'RAS' : alertsCount <= 2 ? 'À voir' : 'Vigilance'}
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
