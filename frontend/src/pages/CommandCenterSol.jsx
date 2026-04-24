/**
 * PROMEOS — CommandCenterSol (Lot 1.1, route racine /)
 *
 * Page d'accueil PROMEOS. Pattern A adapté avec tuiles de navigation
 * modules en complément des 3 KPIs + 3 week-cards + graphe signature.
 *
 * APIs consommées (inchangées) :
 *   - getActionsSummary(orgId)      → counts + by_source + total_gain + top5
 *   - getNotificationsSummary(orgId) → counts + top alertes
 *   - getNotificationsList({limit}) → items détaillés pour week-cards
 *   - getComplianceBundle({scope})  → score conformité + findings
 *   - getCockpit()                   → stats patrimoine (fallback issue #257)
 *   - getPatrimoineKpis()            → total_sites + surface (contexte narrative)
 *
 * Zéro drawer Sol custom — les navigations vers modules ouvrent les
 * pages dédiées via Router (SPA, pas de flash).
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
  SolBarChart,
} from '../ui/sol';
import { useScope } from '../contexts/ScopeContext';
import {
  getActionsSummary,
  getNotificationsSummary,
  getNotificationsList,
  getComplianceBundle,
  getCockpit,
  getPatrimoineKpis,
} from '../services/api';
import {
  NBSP,
  buildCommandKicker,
  buildCommandNarrative,
  buildCommandSubNarrative,
  buildCommandWeekCards,
  buildSolWeeklyActivity,
  computeStateIndex,
  interpretStateIndex,
  interpretCommandAlerts,
  interpretSolActions,
  formatFR,
  formatFREur,
  freshness,
} from './command-center/sol_presenters';
import { SkeletonCard } from '../ui/Skeleton';
import { fmtNum } from '../utils/format';
import { LayoutDashboard, ShieldCheck, Receipt, Building2, ShoppingCart } from 'lucide-react';

// Sprint P6 S2 — Enrichissement superset MAIN (Batch 1 Tableau de bord)
// Imports composants MAIN standalone (pas de PageShell wrapping)
import DeadlineBanner from '../components/DeadlineBanner';
import MorningBriefCard from '../components/MorningBriefCard';
import TodayActionsCard from './cockpit/TodayActionsCard';
import SitesBaselineCard from './cockpit/SitesBaselineCard';
import { useCommandCenterData } from '../hooks/useCommandCenterData';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ComposedChart,
  Line,
  ReferenceLine,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

// ──────────────────────────────────────────────────────────────────────────────

function useCommandData({ orgId } = {}) {
  const [state, setState] = useState({
    status: 'loading',
    actions: null,
    notifSummary: null,
    notifList: null,
    compliance: null,
    cockpit: null,
    patrimoine: null,
  });

  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, status: 'loading' }));

    Promise.allSettled([
      getActionsSummary(orgId).catch(() => null),
      getNotificationsSummary(orgId).catch(() => null),
      getNotificationsList({ org_id: orgId, limit: 10 }).catch(() => null),
      getComplianceBundle().catch(() => null),
      getCockpit().catch(() => null),
      getPatrimoineKpis().catch(() => null),
    ]).then(([actions, notifSummary, notifList, compliance, cockpit, patrimoine]) => {
      if (cancelled) return;
      setState({
        status: 'ready',
        actions: actions.status === 'fulfilled' ? actions.value : null,
        notifSummary: notifSummary.status === 'fulfilled' ? notifSummary.value : null,
        notifList: notifList.status === 'fulfilled' ? notifList.value : null,
        compliance: compliance.status === 'fulfilled' ? compliance.value : null,
        cockpit: cockpit.status === 'fulfilled' ? cockpit.value : null,
        patrimoine: patrimoine.status === 'fulfilled' ? patrimoine.value : null,
      });
    });

    return () => {
      cancelled = true;
    };
  }, [orgId]);

  return state;
}

// ──────────────────────────────────────────────────────────────────────────────

const MODULE_TILES = [
  {
    to: '/cockpit',
    label: 'Cockpit exécutif',
    desc: 'Synthèse portefeuille, KPIs 3 modes',
    Icon: LayoutDashboard,
  },
  {
    to: '/conformite',
    label: 'Conformité',
    desc: 'Décret tertiaire · BACS · APER',
    Icon: ShieldCheck,
  },
  { to: '/bill-intel', label: 'Facturation', desc: 'Shadow billing + anomalies', Icon: Receipt },
  { to: '/patrimoine', label: 'Patrimoine', desc: 'Sites · contrats · EUI', Icon: Building2 },
  {
    to: '/achat-energie',
    label: 'Achat énergie',
    desc: 'Arbitrage · scénarios · radar',
    Icon: ShoppingCart,
  },
];

const TILE_STYLE = {
  background: 'var(--sol-bg-paper)',
  border: '1px solid var(--sol-ink-200)',
  borderRadius: 8,
  padding: '16px 18px',
  cursor: 'pointer',
  textAlign: 'left',
  display: 'flex',
  alignItems: 'flex-start',
  gap: 12,
  transition: 'border-color 120ms, box-shadow 120ms',
};
const TILE_ICON_STYLE = { color: 'var(--sol-calme-fg)', flexShrink: 0, marginTop: 2 };
const TILE_BODY_STYLE = { flex: 1, minWidth: 0 };
const TILE_LABEL_STYLE = {
  fontFamily: 'var(--sol-font-body)',
  fontSize: 14,
  fontWeight: 600,
  color: 'var(--sol-ink-900)',
  marginBottom: 3,
};
const TILE_DESC_STYLE = { fontSize: 12, color: 'var(--sol-ink-500)', lineHeight: 1.4 };
const TILE_GRID_STYLE = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
  gap: 12,
  marginTop: 8,
};
const tileHoverEnter = (e) => {
  e.currentTarget.style.borderColor = 'var(--sol-calme-fg)';
  e.currentTarget.style.boxShadow = '0 2px 6px rgba(15, 23, 42, 0.06)';
};
const tileHoverLeave = (e) => {
  e.currentTarget.style.borderColor = 'var(--sol-ink-200)';
  e.currentTarget.style.boxShadow = '0 1px 2px rgba(15, 23, 42, 0.03)';
};

// ──────────────────────────────────────────────────────────────────────────────

export default function CommandCenterSol() {
  const scopeCtx = useScope();
  const scope = scopeCtx?.scope || {};
  const org = scopeCtx?.org;
  const scopeLabel = scopeCtx?.scopeLabel;
  const sitesCount = scopeCtx?.sitesCount;
  const orgName = org?.name || org?.label || scopeLabel || 'votre patrimoine';
  const navigate = useNavigate();

  const data = useCommandData({ orgId: scope.orgId });
  // Sprint P6 S2 — données EMS J-1 + 7 jours + profil 24h pour enrichissement superset MAIN
  const cmd = useCommandCenterData();
  const kpisJ1 = cmd.kpisJ1 || {};
  const weekSeries = cmd.weekSeries || [];
  const hourlyProfile = cmd.hourlyProfile || [];

  // ─── Dérivations présentation ──────────────────────────────────────────────

  const kicker = buildCommandKicker({ scope: { orgName, sitesCount } });

  const actions = data.actions ?? {};
  const notifSummary = data.notifSummary ?? {};
  const notifList = Array.isArray(data.notifList)
    ? data.notifList
    : Array.isArray(data.notifList?.items)
      ? data.notifList.items
      : [];
  const cockpitStats = data.cockpit?.stats ?? {};
  const patrimoine = data.patrimoine ?? {};
  const compliance = data.compliance ?? {};

  // KPI 1 State index composite
  const complianceScore = cockpitStats.compliance_score ?? compliance.compliance_score;
  const stateIndex = useMemo(
    () =>
      computeStateIndex({
        complianceScore,
        totalInvoices: data.cockpit?.billing?.total_invoices ?? 36,
        anomaliesCount: cockpitStats.alertes_actives ?? 0,
        activeSites: patrimoine.nb_sites ?? patrimoine.total ?? sitesCount,
        totalSites: patrimoine.nb_sites ?? patrimoine.total ?? sitesCount,
      }),
    [complianceScore, cockpitStats, patrimoine, sitesCount, data.cockpit]
  );

  // KPI 2 alerts
  const alertsCount =
    notifSummary.total ??
    notifSummary.counts?.total ??
    notifList.filter((n) => n?.severity === 'critical' || n?.severity === 'high').length;
  const topAlert = notifList.find((n) => n?.severity === 'critical') || notifList[0];

  // KPI 3 Sol actions
  const solActionsCount = actions.counts?.open ?? 0;
  const totalGain = actions.total_gain_eur ?? 0;

  // Week-cards
  const weekCards = useMemo(
    () =>
      buildCommandWeekCards({
        notifications: notifList,
        actions: actions.top5 || [],
        topFindings: compliance.findings || [],
        onNavigate: (path) => navigate(path),
      }),
    [notifList, actions.top5, compliance.findings, navigate]
  );

  // Graphe activité Sol hebdo
  const barChartData = useMemo(() => buildSolWeeklyActivity(actions), [actions]);

  const narrative = useMemo(
    () => buildCommandNarrative({ stateIndex, alertsCount, solActionsCount, totalGain }),
    [stateIndex, alertsCount, solActionsCount, totalGain]
  );
  const subNarrative = useMemo(() => buildCommandSubNarrative({ summary: actions }), [actions]);

  const dataFreshness = useMemo(
    () => freshness(data.cockpit?.stats?.compliance_computed_at),
    [data.cockpit]
  );

  // ─── Rendu ───────────────────────────────────────────────────────────────

  // Sprint P6 S2 — derivations pour sections MAIN enrichies (avant early return)
  const topActions = actions.top5 || actions.items || [];
  const fmtKwhCompact = (v) => {
    if (v == null || !Number.isFinite(v)) return '—';
    if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1).replace('.', ',')} GWh`;
    if (v >= 1_000) return `${(v / 1_000).toFixed(1).replace('.', ',')} MWh`;
    return `${Math.round(v).toLocaleString('fr-FR')} kWh`;
  };
  // Trajectoire DT 2030 (cible -40% vs baseline) — useMemo AVANT early return
  const dtProgress = useMemo(() => {
    const score = complianceScore;
    if (score == null) return null;
    const objectif = 60;
    const pct = Math.min(100, Math.max(0, (score / objectif) * 100));
    return { score, objectif, pct };
  }, [complianceScore]);

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
        title="Bonjour "
        titleEm="— bienvenue sur votre cockpit énergétique"
        narrative={narrative}
        subNarrative={subNarrative}
      />

      {/* Ordre stratégie produit : urgence réglementaire → priorités semaine → briefing → KPIs */}

      {/* 1. Urgence réglementaire (contextuel du header) */}
      <DeadlineBanner />

      {/* 2. Priorités narratives (juste après contexte header) */}
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

      {/* 3. Briefing d'arrivée (contextualise les compteurs) */}
      <div style={{ marginTop: 8 }}>
        <MorningBriefCard
          alerts={alertsCount || 0}
          invoices={data.cockpit?.billing?.anomalies_count || 0}
          actionsClosed={actions.counts?.done || 0}
        />
      </div>

      {/* 4. État patrimoine 360° */}
      <SolKpiRow>
        <SolKpiCard
          label="Indice d'état patrimoine"
          explainKey="command_state_index"
          value={stateIndex != null ? fmtNum(stateIndex, 1) : '—'}
          unit="/100"
          semantic="score"
          headline={interpretStateIndex(stateIndex)}
          source={{
            kind: 'Composite',
            origin: 'conformité + facture + monitoring',
            freshness: dataFreshness,
          }}
        />
        <SolKpiCard
          label="Alertes actives"
          explainKey="command_alerts_count"
          value={alertsCount != null ? formatFR(alertsCount, 0) : '—'}
          unit={alertsCount > 1 ? 'alertes' : 'alerte'}
          semantic="cost"
          headline={interpretCommandAlerts({
            alertsCount,
            topAlertTitle: topAlert?.title,
            topAlertImpact: topAlert?.estimated_impact_eur,
          })}
          source={{
            kind: 'Notifications',
            origin: 'tous modules',
          }}
        />
        <SolKpiCard
          label="Actions Sol à valider"
          explainKey="command_sol_actions_count"
          value={solActionsCount != null ? formatFR(solActionsCount, 0) : '—'}
          unit={solActionsCount > 1 ? 'actions' : 'action'}
          semantic="score"
          headline={interpretSolActions({
            count: solActionsCount,
            totalGain,
            bySource: actions.by_source,
          })}
          source={{
            kind: 'Sol V1',
            origin: 'journal actions',
            freshness: totalGain > 0 ? `potentiel ${formatFREur(totalGain, 0)}` : undefined,
          }}
        />
      </SolKpiRow>

      {/* Sprint P6 S2 — Section MAIN-parity : KPIs J-1 opérationnels */}
      {kpisJ1 && (kpisJ1.conso_hier_kwh != null || kpisJ1.pic_puissance_kw != null) && (
        <>
          <SolSectionHead
            title="Hier — opérationnel J-1"
            meta="Consommation, pic puissance et intensité CO₂"
          />
          <SolKpiRow>
            <SolKpiCard
              label="Conso hier"
              value={fmtKwhCompact(kpisJ1.conso_hier_kwh)}
              unit=""
              semantic="conso"
              headline={kpisJ1.delta_j7_pct != null ? `${kpisJ1.delta_j7_pct > 0 ? '+' : ''}${kpisJ1.delta_j7_pct.toFixed(1)}% vs J-7` : null}
              source={{ kind: 'Enedis CDC', origin: 'EMS timeseries', freshness: 'J-1' }}
            />
            <SolKpiCard
              label="Conso mois"
              value={fmtKwhCompact(kpisJ1.conso_mois_kwh)}
              unit=""
              semantic="conso"
              headline={kpisJ1.delta_mom_pct != null ? `${kpisJ1.delta_mom_pct > 0 ? '+' : ''}${kpisJ1.delta_mom_pct.toFixed(1)}% vs mois préc.` : null}
              source={{ kind: 'Enedis CDC', origin: 'cumul mensuel', freshness: 'temps réel' }}
            />
            <SolKpiCard
              label="Pic puissance"
              value={kpisJ1.pic_puissance_kw != null ? fmtNum(kpisJ1.pic_puissance_kw, 0) : '—'}
              unit="kW"
              semantic="neutral"
              headline={kpisJ1.pic_heure ? `à ${kpisJ1.pic_heure}` : null}
              source={{ kind: 'Enedis CDC', origin: 'max 15min', freshness: 'J-1' }}
            />
            <SolKpiCard
              label="Intensité CO₂"
              value={kpisJ1.co2_intensity != null ? fmtNum(kpisJ1.co2_intensity, 0) : '—'}
              unit="gCO₂/kWh"
              semantic="cost"
              headline="Mix RTE France temps réel"
              source={{ kind: 'RTE eco2mix', origin: 'moyenne J-1', freshness: 'J-1' }}
            />
          </SolKpiRow>
        </>
      )}

      {/* Sprint P6 S2 — Section MAIN-parity : graphiques conso 7j + profil 24h */}
      {(weekSeries.length > 0 || hourlyProfile.length > 0) && (
        <>
          <SolSectionHead
            title="Signature énergétique récente"
            meta="7 derniers jours · profil horaire J-1"
          />
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
              gap: 16,
            }}
          >
            {weekSeries.length > 0 && (
              <div
                style={{
                  background: 'var(--sol-bg-paper)',
                  border: '1px solid var(--sol-ink-200)',
                  borderRadius: 8,
                  padding: 16,
                }}
              >
                <div
                  style={{
                    fontSize: 12,
                    color: 'var(--sol-ink-500)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    marginBottom: 8,
                  }}
                >
                  Consommation 7 jours · MWh/jour
                </div>
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={weekSeries.map((d) => ({ ...d, mwh: d.kwh != null ? d.kwh / 1000 : null }))}>
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 11, fill: 'var(--sol-ink-500)' }}
                      tickFormatter={(v) => v?.slice(5) || ''}
                    />
                    <YAxis tick={{ fontSize: 11, fill: 'var(--sol-ink-500)' }} />
                    <RechartsTooltip
                      contentStyle={{
                        background: 'var(--sol-bg-paper)',
                        border: '1px solid var(--sol-ink-200)',
                        borderRadius: 6,
                        fontSize: 12,
                      }}
                      formatter={(v) => [`${Number(v).toFixed(1)} MWh`, 'Conso']}
                    />
                    <Bar dataKey="mwh" fill="var(--sol-calme-fg)" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
                <SolSourceChip kind="Enedis CDC" origin="agrégation journalière" freshness="temps réel" />
              </div>
            )}
            {hourlyProfile.length > 0 && (
              <div
                style={{
                  background: 'var(--sol-bg-paper)',
                  border: '1px solid var(--sol-ink-200)',
                  borderRadius: 8,
                  padding: 16,
                }}
              >
                <div
                  style={{
                    fontSize: 12,
                    color: 'var(--sol-ink-500)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    marginBottom: 8,
                  }}
                >
                  Profil horaire J-1 · kW
                </div>
                <ResponsiveContainer width="100%" height={180}>
                  <ComposedChart data={hourlyProfile}>
                    <XAxis dataKey="heure" tick={{ fontSize: 11, fill: 'var(--sol-ink-500)' }} />
                    <YAxis tick={{ fontSize: 11, fill: 'var(--sol-ink-500)' }} />
                    <RechartsTooltip
                      contentStyle={{
                        background: 'var(--sol-bg-paper)',
                        border: '1px solid var(--sol-ink-200)',
                        borderRadius: 6,
                        fontSize: 12,
                      }}
                      formatter={(v) => [`${Math.round(v)} kW`, 'Puissance']}
                    />
                    {kpisJ1.pic_puissance_kw != null && (
                      <ReferenceLine
                        y={kpisJ1.pic_puissance_kw * 0.8}
                        stroke="var(--sol-attention-fg)"
                        strokeDasharray="3 3"
                        label={{ value: '80% pic', fill: 'var(--sol-attention-fg)', fontSize: 10 }}
                      />
                    )}
                    <Line
                      type="monotone"
                      dataKey="kw"
                      stroke="var(--sol-calme-fg)"
                      strokeWidth={2}
                      dot={{ fill: 'var(--sol-calme-fg)', r: 2 }}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
                <SolSourceChip kind="Enedis CDC" origin="profil horaire 15min agrégé" freshness="J-1" />
              </div>
            )}
          </div>
        </>
      )}

      {/* Sprint P6 S2 — Section MAIN-parity : Trajectoire DT 2030 + Actions du jour */}
      {(dtProgress || topActions.length > 0) && (
        <>
          <SolSectionHead
            title="Trajectoire 2030 & priorités du jour"
            meta="Objectif Décret Tertiaire -40%"
          />
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
              gap: 16,
            }}
          >
            {dtProgress && (
              <div
                style={{
                  background: 'var(--sol-bg-paper)',
                  border: '1px solid var(--sol-ink-200)',
                  borderRadius: 8,
                  padding: 16,
                }}
              >
                <div
                  style={{
                    fontSize: 12,
                    color: 'var(--sol-ink-500)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    marginBottom: 12,
                  }}
                >
                  Trajectoire Décret Tertiaire 2030
                </div>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'baseline',
                    marginBottom: 8,
                  }}
                >
                  <span
                    style={{
                      fontFamily: 'var(--sol-font-display)',
                      fontSize: 28,
                      color: 'var(--sol-ink-900)',
                    }}
                  >
                    {fmtNum(dtProgress.score, 0)}
                    <span style={{ fontSize: 14, color: 'var(--sol-ink-500)' }}>/100</span>
                  </span>
                  <span style={{ fontSize: 12, color: 'var(--sol-ink-500)' }}>
                    Objectif ≥ {dtProgress.objectif}
                  </span>
                </div>
                <div
                  style={{
                    height: 8,
                    background: 'var(--sol-ink-100)',
                    borderRadius: 4,
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      width: `${dtProgress.pct}%`,
                      height: '100%',
                      background:
                        dtProgress.pct >= 100
                          ? 'var(--sol-succes-fg)'
                          : dtProgress.pct >= 70
                            ? 'var(--sol-attention-fg)'
                            : 'var(--sol-afaire-fg)',
                      transition: 'width 300ms ease',
                    }}
                  />
                </div>
                <div style={{ marginTop: 8, fontSize: 12, color: 'var(--sol-ink-500)' }}>
                  {dtProgress.pct >= 100
                    ? '✓ Sur la trajectoire pour 2030'
                    : dtProgress.pct >= 70
                      ? 'Rythme soutenu, vigilance sur les écarts'
                      : 'Retard — plan d\'action prioritaire requis'}
                </div>
                <div style={{ marginTop: 12 }}>
                  <SolSourceChip kind="RegOps" origin="score compliance_score_service" freshness={dataFreshness} />
                </div>
              </div>
            )}
            {topActions.length > 0 && (
              <TodayActionsCard
                actions={topActions.slice(0, 5)}
                onNavigate={(path) => navigate(path)}
                title="À traiter aujourd'hui"
              />
            )}
          </div>
        </>
      )}

      {/* Sprint P6 S2 — Section MAIN-parity : Sites J-1 vs baseline */}
      {kpisJ1.consoJ1BySite && Array.isArray(kpisJ1.consoJ1BySite) && kpisJ1.consoJ1BySite.length > 0 && (
        <>
          <SolSectionHead
            title="Sites — performance J-1"
            meta="Consommation hier vs baseline historique"
          />
          <SitesBaselineCard
            consoJ1BySite={kpisJ1.consoJ1BySite}
            consoHierTotal={kpisJ1.conso_hier_kwh}
          />
        </>
      )}

      <SolSectionHead
        title="Activité Sol · 12 semaines"
        meta={`${barChartData.length}${NBSP}semaines · actions validées vs en attente`}
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
          metric="count"
          xAxisType="category"
          xAxisKey="month"
          showDeltaPct={false}
          highlightCurrent
          caption={
            actions.counts ? (
              <>
                <strong style={{ color: 'var(--sol-ink-900)' }}>
                  {actions.counts.done}/{actions.counts.total} actions validées
                </strong>{' '}
                à date · gain cumulé {formatFREur(totalGain, 0)}.
              </>
            ) : null
          }
          sourceChip={
            <SolSourceChip kind="Sol V1" origin="journal actions" freshness={dataFreshness} />
          }
        />
      </div>

      {/* Tuiles de navigation modules — complément Pattern A pour page racine */}
      <SolSectionHead
        title="Accès rapide aux modules"
        meta={`${MODULE_TILES.length}${NBSP}modules`}
      />
      <div style={TILE_GRID_STYLE}>
        {MODULE_TILES.map(({ to, label, desc, Icon }) => (
          <button
            key={to}
            type="button"
            onClick={() => navigate(to)}
            style={TILE_STYLE}
            onMouseEnter={tileHoverEnter}
            onMouseLeave={tileHoverLeave}
          >
            <Icon size={20} style={TILE_ICON_STYLE} />
            <div style={TILE_BODY_STYLE}>
              <div style={TILE_LABEL_STYLE}>{label}</div>
              <div style={TILE_DESC_STYLE}>{desc}</div>
            </div>
          </button>
        ))}
      </div>
    </>
  );
}
