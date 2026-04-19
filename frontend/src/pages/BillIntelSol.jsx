/**
 * PROMEOS — BillIntelSol (Phase 4.2, refonte Sol V1 Pattern A)
 *
 * Rebuild intégral de /bill-intel selon le Pattern A :
 *   SolPageHeader → SolHeadline → SolKpiRow (3 KPIs) → SolWeekGrid (3 cards)
 *   → SolBarChart signature mensuelle (factures année N vs N−1).
 *
 * APIs consommées (inchangées) :
 *   - getBillingSummary({ scope })            → total_eur, total_invoices, total_insights
 *   - getBillingInsights({ limit: 30 })        → anomalies (open/in_review/resolved)
 *   - getBillingCompareMonthly({ months: 12 }) → série mensuelle current vs previous
 *
 * Drawer préservé : InsightDrawer (legacy, components/InsightDrawer.jsx)
 * déclenché via state local drawerInsightId + onClick week-cards.
 *
 * CX compliance :
 *   - Explain wraps KPIs via explainKey=billing_*
 *   - Fallbacks businessErrorFallback() si API vide
 *   - Source chips sur KPIs + SolBarChart
 *   - Pas de duplication CX_DASHBOARD_OPENED (loggé backend-side)
 *
 * Sémantique :
 *   KPI 1 Factures mois     → semantic='cost'  (hausse = mauvais)
 *   KPI 2 Anomalies         → semantic='cost'  (plus d'anomalies = plus de risque)
 *   KPI 3 Récupéré YTD       → semantic='score' (plus récupéré = mieux)
 */
import React, { useEffect, useMemo, useState } from 'react';
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
  getBillingSummary,
  getBillingInsights,
  getBillingCompareMonthly,
} from '../services/api';
import {
  NBSP,
  buildBillKicker,
  buildBillNarrative,
  buildBillSubNarrative,
  buildBillWeekCards,
  interpretTotalFactures,
  interpretAnomalies,
  interpretRecovery,
  adaptCompareToBarChart,
  extractCurrentMonthTotals,
  estimateRecoveredYtd,
  countContestableAnomalies,
  computeDelta,
  formatFR,
  formatFREur,
  freshness,
} from './bill-intel/sol_presenters';
import { SkeletonCard } from '../ui/Skeleton';
import InsightDrawer from '../components/InsightDrawer';

// ──────────────────────────────────────────────────────────────────────────────
// Data hook — 3 APIs en parallèle
// ──────────────────────────────────────────────────────────────────────────────

function useBillIntelSolData({ orgId, siteId } = {}) {
  const [state, setState] = useState({
    status: 'loading',
    summary: null,
    insights: null,
    compare: null,
  });

  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, status: 'loading' }));

    const params = siteId ? { site_id: siteId } : {};

    Promise.allSettled([
      getBillingSummary(params).catch(() => null),
      getBillingInsights({ limit: 30, ...params }).catch(() => null),
      getBillingCompareMonthly({ months: 12, ...params }).catch(() => null),
    ]).then(([summary, insights, compare]) => {
      if (cancelled) return;
      setState({
        status: 'ready',
        summary: summary.status === 'fulfilled' ? summary.value : null,
        insights: insights.status === 'fulfilled' ? insights.value : null,
        compare: compare.status === 'fulfilled' ? compare.value : null,
      });
    });

    return () => { cancelled = true; };
  }, [orgId, siteId]);

  return state;
}

// ──────────────────────────────────────────────────────────────────────────────

export default function BillIntelSol() {
  const scopeCtx = useScope();
  const scope = scopeCtx?.scope || {};
  const org = scopeCtx?.org;
  const scopeLabel = scopeCtx?.scopeLabel;
  const sitesCount = scopeCtx?.sitesCount;
  const orgName = org?.name || org?.label || scopeLabel || 'votre patrimoine';

  const data = useBillIntelSolData({ orgId: scope.orgId, siteId: scope.siteId });
  const [drawerInsightId, setDrawerInsightId] = useState(null);

  // ─── Dérivations présentation ──────────────────────────────────────────────

  const kicker = buildBillKicker({ scope: { orgName, sitesCount } });

  const summary = data.summary ?? {};
  const insightsList = Array.isArray(data.insights?.insights)
    ? data.insights.insights
    : Array.isArray(data.insights)
      ? data.insights
      : [];
  const compare = data.compare;

  // KPI 1 — Factures mois en cours + delta vs mois précédent
  const { currentEur: currentMonthEur, previousMonthEur } = useMemo(
    () => extractCurrentMonthTotals(compare),
    [compare]
  );
  const kpiCostDelta = useMemo(() => {
    if (currentMonthEur == null || previousMonthEur == null) return null;
    return computeDelta({
      current: currentMonthEur,
      previous: previousMonthEur,
      unit: '%',
      context: 'vs mois précédent',
    });
  }, [currentMonthEur, previousMonthEur]);

  // KPI 2 — Anomalies actives
  const anomaliesOpen = insightsList.filter((i) => i?.insight_status === 'open').length;
  const potentialRecovery = summary.total_estimated_loss_eur ?? 0;
  const contestableCount = useMemo(() => countContestableAnomalies(insightsList), [insightsList]);

  // KPI 3 — Récupéré YTD
  const recoveredYtd = useMemo(() => estimateRecoveredYtd(insightsList), [insightsList]);
  const contestationsValidated = insightsList.filter((i) => i?.insight_status === 'resolved').length;

  // Narrative
  const narrative = buildBillNarrative({
    summary,
    anomaliesCount: anomaliesOpen,
    recoveredYtd,
  });
  const subNarrative = buildBillSubNarrative({ summary });

  // Week-cards
  const weekCards = useMemo(
    () =>
      buildBillWeekCards({
        insights: insightsList,
        onOpenInsight: (insight) => setDrawerInsightId(insight?.id || null),
      }),
    [insightsList]
  );

  // Graphe signature
  const barChartData = useMemo(() => adaptCompareToBarChart(compare), [compare]);

  const dataFreshness = useMemo(
    () => freshness(summary.last_updated),
    [summary.last_updated]
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
        title="Votre facturation "
        titleEm="— shadow billing et contestations"
        narrative={narrative}
        subNarrative={subNarrative}
      />

      <SolKpiRow>
        <SolKpiCard
          label="Factures · mois en cours"
          explainKey="billing_total_current_month"
          value={currentMonthEur != null ? formatFR(currentMonthEur, 0) : '—'}
          unit={`${NBSP}€${NBSP}HT`}
          delta={kpiCostDelta}
          semantic="cost"
          headline={interpretTotalFactures({
            summary,
            currentMonthEur,
            previousMonthEur,
          })}
          source={{
            kind: 'Factures',
            origin: summary.total_invoices
              ? `${summary.total_invoices}${NBSP}factures`
              : undefined,
            freshness: summary.coverage_months
              ? `${summary.coverage_months}${NBSP}mois`
              : undefined,
          }}
        />
        <SolKpiCard
          label="Anomalies · à contester"
          explainKey="billing_anomalies_count"
          value={anomaliesOpen != null ? formatFR(anomaliesOpen, 0) : '—'}
          unit={anomaliesOpen > 1 ? 'anomalies' : 'anomalie'}
          semantic="cost"
          headline={interpretAnomalies({
            anomaliesCount: anomaliesOpen,
            potentialRecovery,
            contestableCount,
          })}
          source={{
            kind: 'Shadow billing',
            origin: summary.engine_version || 'rules_v2',
            freshness: `mis à jour ${dataFreshness}`,
          }}
        />
        <SolKpiCard
          label="Récupéré · depuis janvier"
          explainKey="billing_recovery_ytd"
          value={recoveredYtd != null ? formatFR(recoveredYtd, 0) : '—'}
          unit={`${NBSP}€${NBSP}HT`}
          semantic="score"
          headline={interpretRecovery({
            recoveredYtd,
            contestationsValidated,
          })}
          source={{
            kind: 'Contestations',
            origin: 'validées',
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
        title="Facturation mensuelle"
        meta={`12${NBSP}mois · ${compare?.current_year || ''} vs ${compare?.previous_year || ''}`}
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
          metric="euros"
          showDeltaPct
          highlightCurrent
          caption={
            summary.total_eur ? (
              <>
                <strong style={{ color: 'var(--sol-ink-900)' }}>
                  {formatFREur(summary.total_eur, 0)}
                </strong>{' '}
                cumulés sur {summary.coverage_months ?? '—'}{NBSP}mois
                {potentialRecovery > 0 && (
                  <>
                    {' '}· potentiel récupération {formatFREur(potentialRecovery, 0)}
                  </>
                )}
                .
              </>
            ) : null
          }
          sourceChip={
            <SolSourceChip
              kind="Factures"
              origin="agrégées"
              freshness={dataFreshness}
            />
          }
        />
      </div>

      <InsightDrawer
        insightId={drawerInsightId}
        open={drawerInsightId != null}
        onClose={() => setDrawerInsightId(null)}
      />
    </>
  );
}
