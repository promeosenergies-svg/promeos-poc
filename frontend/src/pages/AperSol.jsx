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
import { useNavigate, useSearchParams } from 'react-router-dom';
import { X } from 'lucide-react';
import { track } from '../services/tracker';
import { FOCUS_RING_SOL } from '../ui/sol/focusRing';
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
  applyAperFilter,
  normalizeAperFilter,
} from './aper/sol_presenters';
import { SkeletonCard } from '../ui/Skeleton';

const FILTER_LABELS = {
  parking: 'Parkings > 1 500 m²',
  toiture: 'Toitures > 500 m²',
};

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
  const [searchParams] = useSearchParams();

  // Deep-link `?filter=parking|toiture` depuis panel nav (Vague 1).
  // Autre valeur ou absence → pas de filtre.
  const activeFilter = normalizeAperFilter(searchParams.get('filter'));

  // Tracker A10 : filter_applied au mount + à chaque changement URL.
  // Source = 'deep_link' quand l'URL contient `?filter=…` au mount, sinon
  // non tracké (pas de filtre manuel dans AperSol pour l'instant — les
  // week-cards drillent directement vers /sites/:id sans filtrage).
  React.useEffect(() => {
    if (!activeFilter) return;
    track('aper_filter_applied', {
      filter_type: activeFilter,
      source: 'deep_link',
    });
  }, [activeFilter]);

  const data = useAperData();

  // ─── Dérivations présentation ──────────────────────────────────────────────

  const kicker = buildAperKicker({ scope: { orgName, sitesCount } });

  // Dashboard filtré : propage automatiquement sur KPIs, week-cards, bar chart.
  const dashboard = useMemo(
    () => applyAperFilter(data.dashboard, activeFilter),
    [data.dashboard, activeFilter]
  );
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

      {activeFilter && (
        <div
          data-testid="aper-active-filter"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 10,
            padding: '6px 10px',
            marginBottom: 24,
            background: 'var(--sol-calme-bg)',
            color: 'var(--sol-calme-fg)',
            border: '1px solid var(--sol-ink-200)',
            borderRadius: 4,
            fontSize: 12,
            fontFamily: 'var(--sol-font-body)',
          }}
        >
          {/* Live region scopée au texte (pas au bouton Reset) pour
              éviter la ré-annonce SR à chaque click. */}
          <span
            role="status"
            aria-live="polite"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 10,
            }}
          >
            <span
              style={{
                fontFamily: 'var(--sol-font-mono)',
                fontSize: 10,
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
                color: 'var(--sol-ink-500)',
              }}
            >
              Filtre actif
            </span>
            <span style={{ fontWeight: 500 }}>{FILTER_LABELS[activeFilter]}</span>
          </span>
          {/* Hit area ≥ 44×44 (WCAG 2.5.5). */}
          <button
            type="button"
            onClick={() => navigate('/conformite/aper')}
            aria-label="Réinitialiser le filtre"
            className={FOCUS_RING_SOL}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '10px 12px',
              minHeight: 44,
              minWidth: 44,
              background: 'transparent',
              border: '1px solid var(--sol-ink-300)',
              borderRadius: 4,
              color: 'var(--sol-ink-700)',
              fontSize: 12,
              cursor: 'pointer',
            }}
          >
            <X size={14} aria-hidden="true" />
            Réinitialiser
          </button>
        </div>
      )}

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
