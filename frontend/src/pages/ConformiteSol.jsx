/**
 * PROMEOS — ConformiteSol (Phase 4.1, refonte Sol V1 Pattern A)
 *
 * Rebuild intégral de /conformite selon le Pattern A :
 *   SolPageHeader → SolHeadline → SolKpiRow (3 KPIs) → SolWeekGrid (3 cards)
 *   → SolTrajectoryChart signature DT.
 *
 * APIs consommées (inchangées) :
 *   - getComplianceSummary({ scope })       → KPIs + findings_by_regulation
 *   - getComplianceScoreTrend({ months: 6 }) → trajectoire 6 mois pour chart
 *   - getComplianceTimeline()                → events upcoming/passed/future
 *   - getComplianceFindings({ scope })       → drift + anomalies détectées
 *   - getAuditSmeAssessment(orgId)           → option (404 gracieux)
 *
 * Drawer préservé : FindingAuditDrawer existant (legacy), ouvert via state
 * local + ActionDrawerProvider (déjà monté dans SolAppShell Phase 3).
 *
 * CX compliance : Explain wraps sur les 3 KPIs (explainKey='compliance_score_*'),
 * fallbacks businessErrors narratifs si API down, source chips sur KPIs+chart.
 * CX_DASHBOARD_OPENED loggé backend-side (pas de duplication frontend).
 */
import React, { useEffect, useMemo, useState } from 'react';
import {
  SolPageHeader,
  SolHeadline,
  SolSubline,
  SolKpiRow,
  SolKpiCard,
  SolSourceChip,
  SolStatusPill,
  SolSectionHead,
  SolWeekGrid,
  SolWeekCard,
  SolTrajectoryChart,
} from '../ui/sol';
import { useScope } from '../contexts/ScopeContext';
import {
  getComplianceSummary,
  getComplianceScoreTrend,
  getComplianceTimeline,
  getComplianceFindings,
  getAuditSmeAssessment,
} from '../services/api';
import {
  NBSP,
  buildConformiteKicker,
  buildConformiteNarrative,
  buildConformiteSubNarrative,
  buildConformiteWeekCards,
  computeScoreDelta,
  deriveScoreFromFindings,
  freshness,
  interpretScoreAPER,
  interpretScoreBACS,
  interpretScoreDT,
} from './conformite/sol_presenters';
import { SkeletonCard } from '../ui/Skeleton';
import FindingAuditDrawer from '../components/conformite/FindingAuditDrawer';

// ──────────────────────────────────────────────────────────────────────────────
// Data hook — 5 APIs en parallèle via Promise.allSettled
// ──────────────────────────────────────────────────────────────────────────────

function useConformiteSolData({ orgId } = {}) {
  const [state, setState] = useState({
    status: 'loading',
    summary: null,
    trend: null,
    timeline: null,
    findings: null,
    auditSme: null,
  });

  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, status: 'loading' }));

    Promise.allSettled([
      getComplianceSummary().catch(() => null),
      getComplianceScoreTrend({ months: 6 }).catch(() => null),
      getComplianceTimeline().catch(() => null),
      getComplianceFindings({ limit: 20 }).catch(() => null),
      orgId ? getAuditSmeAssessment(orgId).catch(() => null) : Promise.resolve(null),
    ]).then(([summary, trend, timeline, findings, auditSme]) => {
      if (cancelled) return;
      setState({
        status: 'ready',
        summary: summary.status === 'fulfilled' ? summary.value : null,
        trend: trend.status === 'fulfilled' ? trend.value : null,
        timeline: timeline.status === 'fulfilled' ? timeline.value : null,
        findings: findings.status === 'fulfilled' ? findings.value : null,
        auditSme: auditSme.status === 'fulfilled' ? auditSme.value : null,
      });
    });

    return () => { cancelled = true; };
  }, [orgId]);

  return state;
}

// ──────────────────────────────────────────────────────────────────────────────

export default function ConformiteSol() {
  const scopeCtx = useScope();
  const scope = scopeCtx?.scope || {};
  const org = scopeCtx?.org;
  const scopeLabel = scopeCtx?.scopeLabel;
  const sitesCount = scopeCtx?.sitesCount;
  const orgName = org?.name || org?.label || scopeLabel || 'votre patrimoine';

  const data = useConformiteSolData({ orgId: scope.orgId });
  const [auditFindingId, setAuditFindingId] = useState(null);

  // ─── Dérivations présentation ──────────────────────────────────────────────

  const kicker = buildConformiteKicker({ scope: { orgName, sitesCount } });

  // Scores : DT depuis summary.compliance_score (canonique),
  //          BACS + APER dérivés depuis findings_by_regulation.
  // Fix P4.1.1 : deriveScoreFromFindings distingue 'not_applicable' (aucun
  // site assujetti, out_of_scope only) vs null (en attente d'évaluation).
  const summary = data.summary ?? {};
  const findingsByReg = summary.findings_by_regulation ?? {};
  const scoreDT = summary.compliance_score;
  const rawBACS = deriveScoreFromFindings(findingsByReg.bacs);
  const rawAPER = deriveScoreFromFindings(findingsByReg.aper);
  const scoreBACS = typeof rawBACS === 'number' ? rawBACS : null;
  const scoreBACSNotApplicable = rawBACS === 'not_applicable';
  const scoreAPER = typeof rawAPER === 'number' ? rawAPER : null;
  const scoreAPERNotApplicable = rawAPER === 'not_applicable';

  // Delta DT via trend
  const trendArr = Array.isArray(data.trend?.trend) ? data.trend.trend : [];
  const scoreDTDelta = computeScoreDelta(trendArr);

  // Timeline split
  const events = Array.isArray(data.timeline?.events) ? data.timeline.events : [];
  const timelineUpcoming = events.filter((e) => e?.status === 'upcoming');
  const timelineValidated = events.filter((e) => e?.status === 'passed');

  // Findings list
  const findingsList = Array.isArray(data.findings?.findings)
    ? data.findings.findings
    : Array.isArray(data.findings)
      ? data.findings
      : summary?.top_actions || [];

  // Week-cards
  const weekCards = useMemo(
    () =>
      buildConformiteWeekCards({
        findings: findingsList,
        timelineUpcoming,
        timelineValidated,
        onOpenEvidence: (entity) => {
          const id = entity?.id || entity?.rule_id || null;
          if (id != null) setAuditFindingId(id);
        },
      }),
    [findingsList, timelineUpcoming, timelineValidated]
  );

  const upcomingCount = timelineUpcoming.length;
  const narrative = buildConformiteNarrative({ summary, upcomingCount });
  const subNarrative = buildConformiteSubNarrative({ summary });

  const computedAt = summary?.compliance_computed_at;
  const dataFreshness = useMemo(() => freshness(computedAt), [computedAt]);

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
        title="Votre conformité "
        titleEm="— décret tertiaire et obligations"
        narrative={narrative}
        subNarrative={subNarrative}
      />

      <SolKpiRow>
        <SolKpiCard
          label="Conformité DT"
          explainKey="compliance_score_dt"
          value={scoreDT != null ? scoreDT.toFixed(1).replace('.', ',') : '—'}
          unit="/100"
          delta={scoreDTDelta}
          semantic="score"
          headline={interpretScoreDT({
            score: scoreDT,
            sitesOk: summary.sites_ok,
            sitesTotal: summary.total_sites,
            deadline: data.timeline?.next_deadline?.deadline,
          })}
          source={{
            kind: 'RegOps',
            origin: summary.compliance_source || 'canonique',
            freshness: `mis à jour ${dataFreshness}`,
          }}
        />
        <SolKpiCard
          label="Conformité BACS"
          explainKey="compliance_score_bacs"
          value={scoreBACS != null ? scoreBACS.toFixed(0) : '—'}
          unit="/100"
          semantic="score"
          notApplicable={scoreBACSNotApplicable}
          headline={interpretScoreBACS({ findingsByReg, notApplicable: scoreBACSNotApplicable })}
          source={{
            kind: 'RegOps',
            origin: 'bacs_v2.0',
            freshness: findingsByReg.bacs
              ? `${(findingsByReg.bacs.ok || 0) + (findingsByReg.bacs.nok || 0)}${NBSP}sites évalués`
              : undefined,
          }}
        />
        <SolKpiCard
          label="Conformité APER & SMÉ"
          explainKey="compliance_score_aper"
          value={scoreAPER != null ? scoreAPER.toFixed(0) : '—'}
          unit="/100"
          semantic="score"
          notApplicable={scoreAPERNotApplicable}
          headline={interpretScoreAPER({ findingsByReg, notApplicable: scoreAPERNotApplicable })}
          source={{
            kind: 'RegOps',
            origin: 'aper + audit SMÉ',
            freshness: data.auditSme?.computed_at
              ? freshness(data.auditSme.computed_at)
              : undefined,
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
        title="Trajectoire Décret Tertiaire"
        meta={`${trendArr.length}${NBSP}mois · cible${NBSP}−25${NBSP}% à 2030`}
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
          data={trendArr}
          targetLine={75}
          targetLabel={`Cible${NBSP}DT${NBSP}2030`}
          yLabel="score /100"
          caption={
            <>
              <SolStatusPill
                kind={scoreDT >= 75 ? 'ok' : scoreDT >= 60 ? 'att' : 'risk'}
              >
                {scoreDT >= 75 ? 'Solide' : scoreDT >= 60 ? 'Vigilance' : 'Risque'}
              </SolStatusPill>{' '}
              <span style={{ color: 'var(--sol-ink-700)', fontWeight: 500 }}>
                Votre score progresse
              </span>{' '}
              au rythme attendu pour tenir l'objectif 2030.
            </>
          }
          sourceChip={
            <SolSourceChip
              kind="RegOps"
              origin="services/compliance_engine.py"
              freshness={dataFreshness}
            />
          }
        />
      </div>

      <FindingAuditDrawer
        findingId={auditFindingId}
        onClose={() => setAuditFindingId(null)}
      />
    </>
  );
}
