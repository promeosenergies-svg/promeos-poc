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
import { LayoutDashboard, ShieldCheck, Receipt, Building2, ShoppingCart } from 'lucide-react';

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

    return () => { cancelled = true; };
  }, [orgId]);

  return state;
}

// ──────────────────────────────────────────────────────────────────────────────

const MODULE_TILES = [
  { to: '/cockpit', label: 'Cockpit exécutif', desc: 'Synthèse portefeuille, KPIs 3 modes', Icon: LayoutDashboard },
  { to: '/conformite', label: 'Conformité', desc: 'Décret tertiaire · BACS · APER', Icon: ShieldCheck },
  { to: '/bill-intel', label: 'Facturation', desc: 'Shadow billing + anomalies', Icon: Receipt },
  { to: '/patrimoine', label: 'Patrimoine', desc: 'Sites · contrats · EUI', Icon: Building2 },
  { to: '/achat-energie', label: 'Achat énergie', desc: 'Arbitrage · scénarios · radar', Icon: ShoppingCart },
];

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
    notifSummary.total
    ?? notifSummary.counts?.total
    ?? (notifList.filter((n) => n?.severity === 'critical' || n?.severity === 'high').length);
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

  const narrative = buildCommandNarrative({
    stateIndex,
    alertsCount,
    solActionsCount,
    totalGain,
  });
  const subNarrative = buildCommandSubNarrative({ summary: actions });

  const dataFreshness = useMemo(
    () => freshness(data.cockpit?.stats?.compliance_computed_at),
    [data.cockpit]
  );

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
        title="Bonjour "
        titleEm="— bienvenue sur votre cockpit énergétique"
        narrative={narrative}
        subNarrative={subNarrative}
      />

      <SolKpiRow>
        <SolKpiCard
          label="Indice d'état patrimoine"
          explainKey="command_state_index"
          value={stateIndex != null ? stateIndex.toFixed(1).replace('.', ',') : '—'}
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
                </strong>
                {' '}à date · gain cumulé {formatFREur(totalGain, 0)}.
              </>
            ) : null
          }
          sourceChip={
            <SolSourceChip
              kind="Sol V1"
              origin="journal actions"
              freshness={dataFreshness}
            />
          }
        />
      </div>

      {/* Tuiles de navigation modules — complément Pattern A pour page racine */}
      <SolSectionHead title="Accès rapide aux modules" meta={`${MODULE_TILES.length}${NBSP}modules`} />
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: 12,
          marginTop: 8,
        }}
      >
        {MODULE_TILES.map(({ to, label, desc, Icon }) => (
          <button
            key={to}
            type="button"
            onClick={() => navigate(to)}
            style={{
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
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'var(--sol-calme-fg)';
              e.currentTarget.style.boxShadow = '0 2px 6px rgba(15, 23, 42, 0.06)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--sol-ink-200)';
              e.currentTarget.style.boxShadow = '0 1px 2px rgba(15, 23, 42, 0.03)';
            }}
          >
            <Icon size={20} style={{ color: 'var(--sol-calme-fg)', flexShrink: 0, marginTop: 2 }} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  fontFamily: 'var(--sol-font-body)',
                  fontSize: 14,
                  fontWeight: 600,
                  color: 'var(--sol-ink-900)',
                  marginBottom: 3,
                }}
              >
                {label}
              </div>
              <div style={{ fontSize: 12, color: 'var(--sol-ink-500)', lineHeight: 1.4 }}>
                {desc}
              </div>
            </div>
          </button>
        ))}
      </div>
    </>
  );
}
