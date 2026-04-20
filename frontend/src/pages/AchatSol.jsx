/**
 * PROMEOS — AchatSol (Phase 4.4, refonte Sol V1 Pattern A)
 *
 * Rebuild intégral de /achat-energie selon le Pattern A :
 *   SolPageHeader → SolHeadline → SolKpiRow (cost / neutral / neutral)
 *   → SolWeekGrid (3 cards urgence+opportunité+succès)
 *   → SolTrajectoryChart étendu (prix spot 12 mois + userLine prix contracté).
 *
 * APIs consommées (inchangées) :
 *   - getPurchaseRenewals(orgId)      → radar contrats expirant
 *   - getPurchaseAssistantData(orgId) → sites + consommations annuelles
 *   - getMarketContext('ELEC')         → spot EPEX + volatilité + tendance
 *
 * Drawers : pas de wrapper dédié — renouvellements naviguent via
 * /achat-energie?tab=assistant (l'AchatPage legacy gère ses propres drawers
 * ScenarioDrawer via la route).
 *
 * Sémantique :
 *   KPI 1 Prix pondéré contracté   → semantic='cost'     (hausse = mauvais)
 *   KPI 2 Échéance prochain contrat → semantic='neutral'  (date = neutre)
 *                                    tone adapté via interpretEcheance
 *   KPI 3 Scénarios validés         → semantic='neutral'  (compteur d'activité)
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
  getPurchaseRenewals,
  getPurchaseAssistantData,
  getMarketContext,
} from '../services/api';
import {
  NBSP,
  buildAchatKicker,
  buildAchatNarrative,
  buildAchatSubNarrative,
  buildAchatWeekCards,
  detectOpportunityArea,
  estimateWeightedPrice,
  interpretEcheance,
  interpretPrixPondere,
  interpretScenarios,
  synthesizeMarketTrend,
  formatFR,
  formatFREur,
  freshness,
} from './achat/sol_presenters';
import { SkeletonCard } from '../ui/Skeleton';
import { fmtNum } from '../utils/format';

// ──────────────────────────────────────────────────────────────────────────────

function useAchatSolData({ orgId } = {}) {
  const [state, setState] = useState({
    status: 'loading',
    renewals: null,
    assistant: null,
    market: null,
  });

  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, status: 'loading' }));

    Promise.allSettled([
      orgId ? getPurchaseRenewals(orgId).catch(() => null) : Promise.resolve(null),
      orgId ? getPurchaseAssistantData(orgId).catch(() => null) : Promise.resolve(null),
      getMarketContext('ELEC').catch(() => null),
    ]).then(([renewals, assistant, market]) => {
      if (cancelled) return;
      setState({
        status: 'ready',
        renewals: renewals.status === 'fulfilled' ? renewals.value : null,
        assistant: assistant.status === 'fulfilled' ? assistant.value : null,
        market: market.status === 'fulfilled' ? market.value : null,
      });
    });

    return () => { cancelled = true; };
  }, [orgId]);

  return state;
}

// ──────────────────────────────────────────────────────────────────────────────

export default function AchatSol() {
  const scopeCtx = useScope();
  const scope = scopeCtx?.scope || {};
  const org = scopeCtx?.org;
  const scopeLabel = scopeCtx?.scopeLabel;
  const sitesCount = scopeCtx?.sitesCount;
  const orgName = org?.name || org?.label || scopeLabel || 'votre patrimoine';

  const navigate = useNavigate();
  const data = useAchatSolData({ orgId: scope.orgId });

  // ─── Dérivations présentation ──────────────────────────────────────────────

  const kicker = buildAchatKicker({ scope: { orgName, sitesCount } });

  const renewalsList = Array.isArray(data.renewals?.renewals)
    ? data.renewals.renewals
    : Array.isArray(data.renewals)
      ? data.renewals
      : [];
  const assistantSites = Array.isArray(data.assistant?.sites) ? data.assistant.sites : [];
  const market = data.market;
  const marketSpot = market?.spot_current_eur_mwh;

  // KPI 1 Prix pondéré — estimation (backend manque endpoint dédié)
  const weightedPrice = useMemo(
    () => estimateWeightedPrice({ marketSpot, assistantSites }),
    [marketSpot, assistantSites]
  );

  // KPI 2 Échéance — premier renouvellement trié par days_until_expiry asc
  const nextRenewal = useMemo(() => {
    return [...renewalsList]
      .filter((r) => r?.days_until_expiry != null)
      .sort((a, b) => a.days_until_expiry - b.days_until_expiry)[0];
  }, [renewalsList]);
  const echeance = useMemo(() => interpretEcheance(nextRenewal), [nextRenewal]);

  // KPI 3 Scénarios — pas d'API exposée en V2, affiche compteur synthèse
  // Backend future : getPurchaseScenarios() avec {validated, simulated, potential_savings}
  const scenarios = []; // V2 : empty, week-card fallback sur all_stable
  const scenariosSummary = {
    validatedCount: 0,
    simulatedCount: 0,
    potentialSavings: 0,
  };

  // Week-cards
  const weekCards = useMemo(
    () =>
      buildAchatWeekCards({
        renewals: renewalsList,
        marketContext: market,
        scenarios,
        onOpenRenewal: (renewal) => {
          const siteId = renewal?.site_id;
          if (siteId) {
            navigate(`/achat-energie?tab=assistant&site_id=${siteId}`);
          } else {
            navigate('/achat-energie?tab=assistant');
          }
        },
      }),
    [renewalsList, market, navigate]
  );

  // Graphe : trend 12 mois EPEX Spot (synthétisé)
  const marketTrend = useMemo(() => synthesizeMarketTrend(market), [market]);
  const opportunityArea = useMemo(
    () => detectOpportunityArea(marketTrend, weightedPrice),
    [marketTrend, weightedPrice]
  );

  // Narratives
  const renewalsSoonCount = renewalsList.filter(
    (r) => r?.days_until_expiry != null && r.days_until_expiry < 180
  ).length;
  const narrative = buildAchatNarrative({
    weightedPrice,
    marketSpot,
    nextRenewal,
    renewalsCount: renewalsSoonCount,
  });
  const subNarrative = buildAchatSubNarrative({
    marketContext: market,
    renewals: renewalsList,
  });

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

  // Classes CSS tone pour KPI Échéance headline (afaire / attention / calme)
  const echeanceToneColor = {
    afaire: 'var(--sol-afaire-fg)',
    attention: 'var(--sol-attention-fg)',
    calme: 'var(--sol-calme-fg)',
  }[echeance.tone] || 'var(--sol-ink-700)';

  return (
    <>
      <SolPageHeader
        kicker={kicker}
        title="Votre achat énergie "
        titleEm="— prix pondéré, échéances et scénarios"
        narrative={narrative}
        subNarrative={subNarrative}
      />

      <SolKpiRow>
        <SolKpiCard
          label="Prix pondéré contracté"
          explainKey="achat_prix_pondere"
          value={weightedPrice != null ? formatFR(weightedPrice, 1) : '—'}
          unit={`${NBSP}€/MWh HT`}
          semantic="cost"
          headline={interpretPrixPondere({ weightedPrice, marketSpot })}
          source={{
            kind: 'Contrats',
            origin: 'pondéré volumes',
            freshness: marketSpot != null
              ? `spot EPEX ${formatFR(marketSpot, 1)}${NBSP}€/MWh`
              : undefined,
          }}
        />
        <SolKpiCard
          label="Échéance prochain contrat"
          explainKey="achat_echeance_contrat"
          value={echeance.value}
          unit={echeance.unit}
          semantic="neutral"
          headline={
            <span style={{ color: echeanceToneColor }}>
              {echeance.headline}
            </span>
          }
          source={{
            kind: 'Radar renouvellements',
            origin: nextRenewal?.energy_type || 'portefeuille',
            freshness: nextRenewal?.end_date
              ? `fin ${nextRenewal.end_date}`
              : undefined,
          }}
        />
        <SolKpiCard
          label="Scénarios validés"
          explainKey="achat_scenarios_valides"
          value={formatFR(scenariosSummary.validatedCount, 0)}
          unit={scenariosSummary.validatedCount > 1 ? 'scénarios' : 'scénario'}
          semantic="neutral"
          headline={interpretScenarios(scenariosSummary)}
          source={{
            kind: 'Assistant achat',
            origin: 'simulations archivées',
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
        title="Prix marché spot EPEX"
        meta={`12${NBSP}mois · source ${market?.source || '—'}`}
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
          data={marketTrend}
          dataKey="spot"
          targetLine={null}
          userLine={weightedPrice}
          userLabel={weightedPrice != null ? `Votre prix ${formatFR(weightedPrice, 0)}${NBSP}€/MWh` : ''}
          yDomain={[30, 100]}
          yLabel="€/MWh"
          showThresholdZones={false}
          opportunityArea={opportunityArea}
          caption={
            market?.spot_current_eur_mwh != null ? (
              <>
                <strong style={{ color: 'var(--sol-ink-900)' }}>
                  Spot {formatFR(market.spot_current_eur_mwh, 1)}{NBSP}€/MWh
                </strong>
                {' '}actuellement · tendance 30j{' '}
                {market.trend_30d_vs_12m_pct != null && (
                  <span
                    style={{
                      color:
                        market.trend_30d_vs_12m_pct < 0
                          ? 'var(--sol-succes-fg)'
                          : 'var(--sol-afaire-fg)',
                    }}
                  >
                    {market.trend_30d_vs_12m_pct > 0 ? '+' : ''}
                    {fmtNum(market.trend_30d_vs_12m_pct, 1)}{NBSP}%
                  </span>
                )}
                {' '}vs moyenne 12 mois.
              </>
            ) : (
              <>Données marché en cours de rafraîchissement.</>
            )
          }
          sourceChip={
            <SolSourceChip
              kind="EPEX Spot"
              origin={market?.source || 'MANUAL'}
              freshness={market?.is_demo ? 'démo' : 'temps réel'}
            />
          }
        />
      </div>
    </>
  );
}
