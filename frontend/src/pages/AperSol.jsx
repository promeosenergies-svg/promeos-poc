/**
 * PROMEOS — AperSol (Lot 1.2, route /conformite/aper)
 *
 * Solarisation APER Pattern A : 3 KPIs éligibles/conformes/potentiel
 * + 3 week-cards + SolBarChart catégoriel sites × kWc (roof stacked parking).
 *
 * API consommée :
 *   - getAperDashboard() → parking + roof + total_eligible + next_deadline
 *
 * Drawer : navigation vers /sites/:id pour drill-down (pas de drawer Sol dédié).
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
import { getAperDashboard } from '../services/api';
import {
  NBSP,
  buildAperKicker,
  buildAperNarrative,
  buildAperSubNarrative,
  buildAperWeekCards,
  adaptAperToBarChart,
  computeAperPotentialKwc,
  computeAperAnnualGain,
  interpretAperEligible,
  interpretAperConforming,
  interpretAperPotential,
  mergeSitesForBarChart,
  formatFR,
  formatFREur,
} from './aper/sol_presenters';
import { SkeletonCard } from '../ui/Skeleton';

// ──────────────────────────────────────────────────────────────────────────────

function useAperData() {
  const [state, setState] = useState({ status: 'loading', dashboard: null });
  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, status: 'loading' }));
    getAperDashboard()
      .then((dashboard) => {
        if (!cancelled) setState({ status: 'ready', dashboard });
      })
      .catch(() => {
        if (!cancelled) setState({ status: 'ready', dashboard: null });
      });
    return () => {
      cancelled = true;
    };
  }, []);
  return state;
}

// ──────────────────────────────────────────────────────────────────────────────

export default function AperSol() {
  const scopeCtx = useScope();
  const _scope = scopeCtx?.scope || {};
  const org = scopeCtx?.org;
  const scopeLabel = scopeCtx?.scopeLabel;
  const sitesCount = scopeCtx?.sitesCount;
  const orgName = org?.name || org?.label || scopeLabel || 'votre patrimoine';
  const navigate = useNavigate();

  const data = useAperData();

  // ─── Dérivations présentation ──────────────────────────────────────────────

  const kicker = buildAperKicker({ scope: { orgName, sitesCount } });

  const dashboard = data.dashboard;
  const totalEligible = dashboard?.total_eligible_sites ?? 0;
  const potentialKwc = useMemo(() => computeAperPotentialKwc(dashboard), [dashboard]);
  const annualGain = useMemo(() => computeAperAnnualGain(potentialKwc), [potentialKwc]);
  // V2 : pas de distinction "site conforme" dans l'API — sites éligibles = à étudier
  // Placeholder : 0 conforme tant que le flag n'est pas remonté par le backend.
  const conformingCount = 0;

  const mergedSites = useMemo(() => mergeSitesForBarChart(dashboard), [dashboard]);
  const barChartData = useMemo(() => adaptAperToBarChart(mergedSites), [mergedSites]);

  const weekCards = useMemo(
    () =>
      buildAperWeekCards({
        sites: mergedSites,
        onNavigateSite: (siteId) => navigate(`/sites/${siteId}`),
      }),
    [mergedSites, navigate]
  );

  const narrative = buildAperNarrative({ dashboard });
  const subNarrative = buildAperSubNarrative({ dashboard });

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
        title="Solarisation APER "
        titleEm="— parkings et toitures éligibles"
        narrative={narrative}
        subNarrative={subNarrative}
      />

      <SolKpiRow>
        <SolKpiCard
          label="Sites éligibles APER"
          explainKey="aper_eligible_sites"
          value={formatFR(totalEligible, 0)}
          unit={totalEligible > 1 ? 'sites' : 'site'}
          semantic="neutral"
          headline={interpretAperEligible({ dashboard })}
          source={{
            kind: 'Cartographie',
            origin: 'cadastre + patrimoine',
          }}
        />
        <SolKpiCard
          label="Sites conformes APER"
          explainKey="aper_conforming_sites"
          value={totalEligible > 0 ? `${conformingCount}/${totalEligible}` : '—'}
          unit={totalEligible > 0 ? 'sites' : ''}
          semantic="score"
          headline={interpretAperConforming({ conformingCount, totalEligible })}
          source={{
            kind: 'Projets PV',
            origin: 'études en cours',
          }}
        />
        <SolKpiCard
          label="Potentiel solaire cumulé"
          explainKey="aper_potential_capacity"
          value={potentialKwc > 0 ? formatFR(potentialKwc, 0) : '—'}
          unit={`${NBSP}kWc`}
          semantic="score"
          headline={interpretAperPotential({ potentialKwc, annualGainEur: annualGain, dashboard })}
          source={{
            kind: 'Estimation',
            origin: 'ADEME + tarif achat',
            freshness: annualGain > 0 ? `gain ${formatFREur(annualGain, 0)}/an` : undefined,
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
        title="Potentiel PV par site"
        meta={`${barChartData.length}${NBSP}sites · toiture + parking en kWc`}
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
          xAxisKey="site"
          xAxisAngle={-20}
          highlightCurrent={false}
          caption={
            potentialKwc > 0 ? (
              <>
                <strong style={{ color: 'var(--sol-ink-900)' }}>
                  {formatFR(potentialKwc, 0)}
                  {NBSP}kWc
                </strong>{' '}
                installables cumulés · gain annuel potentiel {formatFREur(annualGain, 0)} (tarif
                achat ≈ 0,10{NBSP}€/kWh, productible 1{NBSP}100{NBSP}kWh/kWc).
              </>
            ) : (
              <>Potentiel PV non disponible.</>
            )
          }
          sourceChip={
            <SolSourceChip
              kind="ADEME"
              origin="coefficients d'emprise"
              freshness="référentiel 2024"
            />
          }
        />
      </div>
    </>
  );
}
