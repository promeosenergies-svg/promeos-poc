/**
 * PROMEOS — UsagesSol (Lot 2 Phase 5, Pattern A hybride)
 *
 * Injection Sol Pattern A en haut de UsagesDashboardPage. Le legacy
 * body (ScopeBar + KpiStrip + 3 onglets Timeline/Baseline/Comptage
 * + HeatmapCard + ComplianceCard + FlexNebcoCard + cards power/cdc/
 * flex bubble + footer) reste préservé intégralement en dessous.
 * Zéro rewrite des onglets — asset lourd qui mérite sa propre refonte
 * dédiée future.
 */
import React from 'react';
import {
  SolPageHeader,
  SolHeadline,
  SolSubline,
  SolKpiRow,
  SolKpiCard,
  SolSourceChip,
  SolSectionHead,
  SolBarChart,
  SolWeekGrid,
  SolWeekCard,
} from '../ui/sol';
import {
  buildUsagesKicker,
  buildUsagesNarrative,
  buildUsagesSubNarrative,
  interpretUsageDominant,
  interpretUsageTotal,
  interpretReadinessScore,
  adaptUsagesToBar,
  buildUsagesWeekCards,
  formatFR,
  NBSP,
} from './usages/sol_presenters';

/**
 * @param {Object} props
 * @param {Object} props.dashboard  getScopedUsagesDashboard() result
 * @param {string} [props.scopeLabel]
 * @param {(item)=>void} [props.onOpenDetail]  drill-down optionnel
 */
export default function UsagesSol({ dashboard, scopeLabel, onOpenDetail }) {
  const topUes = Array.isArray(dashboard?.top_ues) ? dashboard.top_ues : [];
  const baselines = Array.isArray(dashboard?.baselines) ? dashboard.baselines : [];
  const nbUsages = topUes.length;

  const kicker = buildUsagesKicker({ scopeLabel, nbUsages });
  const narrative = buildUsagesNarrative({ dashboard });
  const subNarrative = buildUsagesSubNarrative({ dashboard });

  const barData = adaptUsagesToBar(dashboard);
  const weekCards = buildUsagesWeekCards({ dashboard, onOpenDetail });

  const totalKwh = Number(dashboard?.summary?.total_kwh) || 0;
  const totalMwh = totalKwh > 0 ? Math.round(totalKwh / 1000) : null;
  const top = topUes[0] || null;
  const topPct = top ? Math.round(Number(top.pct_of_total) || 0) : null;
  const readiness = Number(dashboard?.readiness?.score);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, padding: '24px 28px 0' }}>
      <SolPageHeader
        kicker={kicker}
        title="Usages énergétiques"
        titleEm={`· 12${NBSP}mois glissants`}
        narrative={narrative}
        subNarrative={subNarrative}
      />

      <SolHeadline>
        <em>Votre patrimoine</em>{' '}
        {top
          ? `est dominé par ${top.label} (${topPct}${NBSP}%) sur la période analysée.`
          : 'est en cours de segmentation — données à consolider.'}
      </SolHeadline>
      {totalMwh != null && (
        <SolSubline>
          Consommation totale {formatFR(totalMwh, 0)}
          {NBSP}MWh sur 12 mois · {baselines.length}
          {NBSP}baselines calculées.
        </SolSubline>
      )}

      <SolKpiRow>
        <SolKpiCard
          label="Usage dominant"
          value={top ? `${top.label}` : '—'}
          unit={topPct != null ? `${topPct}${NBSP}%` : ''}
          semantic="neutral"
          explainKey="usage_dominant"
          headline={interpretUsageDominant({ dashboard })}
          source={{ kind: 'calcul', origin: 'compteurs + segmentation NAF' }}
        />
        <SolKpiCard
          label="Consommation totale"
          value={totalMwh != null ? formatFR(totalMwh, 0) : '—'}
          unit="MWh"
          semantic="neutral"
          explainKey="usage_total_mwh"
          headline={interpretUsageTotal({ dashboard })}
          source={{ kind: 'calcul', origin: '12 mois glissants toutes énergies' }}
        />
        <SolKpiCard
          label="Qualité segmentation"
          value={Number.isFinite(readiness) ? String(Math.round(readiness)) : '—'}
          unit="/100"
          semantic="score"
          explainKey="usage_readiness_score"
          headline={interpretReadinessScore({ dashboard })}
          source={{ kind: 'calcul', origin: 'moteur readiness usages' }}
        />
      </SolKpiRow>

      <SolSectionHead
        title="Top usages par consommation"
        meta={`${barData.length}${NBSP}usage${barData.length > 1 ? 's' : ''} · 12${NBSP}mois`}
      />
      {barData.length > 0 ? (
        <SolBarChart
          data={barData}
          xAxisKey="name"
          xAxisType="category"
          yLabel="MWh/an"
          sourceChip={<SolSourceChip kind="calcul" origin="top_ues · baseline" />}
        />
      ) : (
        <p
          style={{
            color: 'var(--sol-ink-500)',
            fontStyle: 'italic',
            margin: 0,
            padding: '16px 0',
          }}
        >
          Aucun usage suffisamment instrumenté pour graphique — ajouter des sous-compteurs.
        </p>
      )}

      <SolSectionHead title="Cette semaine sur vos usages" meta="3 signaux prioritaires" />
      <SolWeekGrid>
        {weekCards.map((c) => (
          <SolWeekCard
            key={c.id}
            tagLabel={c.tagLabel}
            tagKind={c.tagKind}
            title={c.title}
            body={c.body}
            footerLeft={c.footerLeft}
            footerRight={c.footerRight}
            onClick={c.onClick}
          />
        ))}
      </SolWeekGrid>
    </div>
  );
}
