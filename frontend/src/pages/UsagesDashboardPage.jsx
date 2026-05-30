/**
 * PROMEOS — Page Usages Énergétiques V4
 * Layout 2 colonnes + scope switcher multi-niveaux + 3 onglets.
 * Orchestrateur : fetch centralisé via scoped endpoints.
 */
import React, { useEffect, useState, useMemo, useRef, useCallback } from 'react';
// Énergie P0b visual credibility (2026-05-27, brief C5) — icônes lucide
// remplacent les emojis 📈 📊 🔌 🖨 dans les labels onglets + boutons
// export (ne respectaient pas la charte corporate Sol § Premium Night).
// Usage Steering P1 (2026-05-27) — icône Sliders pour onglet « Pilotage
// des usages » (4ᵉ tab interne, brief C1).
// Sprint Énergie P1.S4 (2026-05-29) — icône CalendarDays pour onglet
// « Semaine type » (5ᵉ tab interne, branché sur /api/energy/week-profile).
import {
  TrendingUp,
  BarChart2,
  Plug,
  Printer,
  FileSpreadsheet,
  Sliders,
  CalendarDays,
} from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { useScope } from '../contexts/ScopeContext';
import {
  getScopedUsagesDashboard,
  getScopedUsageTimeline,
  getPortfolioUsageComparison,
  getCostByPeriod,
  getFlexNebco,
  getPowerOptimization,
  getCdcSimulation,
  getFlexNebcoPortfolio,
} from '../services/api';

import ScopeBar from '../components/usages/ScopeBar';
import KpiStrip from '../components/usages/KpiStrip';
import TabBar from '../components/usages/TabBar';
import TimelineTab from '../components/usages/TimelineTab';
import BaselineTab from '../components/usages/BaselineTab';
import ComptageTab from '../components/usages/ComptageTab';
import HeatmapCard from '../components/usages/HeatmapCard';
import ComplianceCard from '../components/usages/ComplianceCard';
import FlexNebcoCard from '../components/usages/FlexNebcoCard';
import CostCard from '../components/usages/CostCard';
import PowerOptimizationCard from '../components/usages/PowerOptimizationCard';
import CdcSimulationCard from '../components/usages/CdcSimulationCard';
import FlexBubbleChart from '../components/usages/FlexBubbleChart';
import FooterLinks from '../components/usages/FooterLinks';
// Usage Steering P1 (2026-05-27, brief C1) — 4ᵉ onglet « Pilotage des
// usages » dans /usages. PAS de nouveau menu, PAS de /usage-steering.
import PilotageTab from '../components/usages/PilotageTab';
// Sprint Énergie P1.S4 (2026-05-29) — 5ᵉ onglet interne « Semaine type »
// branché sur /api/energy/week-profile (livré S2b). Heatmap 7×24 + 4 KPI
// canoniques (highest_day/hour, night_baseload_kw, weekend_consumption_pct).
import WeekProfileTab from './usages/WeekProfileTab';

const ALL_TABS = [
  { id: 'timeline', label: 'Évolution', icon: TrendingUp },
  { id: 'baseline', label: 'Baseline', icon: BarChart2 },
  { id: 'comptage', label: 'Comptage', icon: Plug },
  // Usage Steering P1 — onglet pilotage interne (brief C1) ; consomme
  // /api/usages/pilotage-summary + sync vers Centre d'Action V4.
  { id: 'pilotage', label: 'Pilotage des usages', icon: Sliders },
  // Sprint Énergie P1.S4 — onglet Semaine type ; consomme
  // /api/energy/week-profile (zéro calcul métier FE).
  { id: 'semaine-type', label: 'Semaine type', icon: CalendarDays },
];

export default function UsagesDashboardPage() {
  const { selectedSiteId, scopedSites, scope, setSite } = useScope();
  // Usage Steering P1 (2026-05-27, brief C1) — état URL pour deep-link
  // /usages?tab=pilotage (depuis Centre d'Action V4 source_url).
  // Usage Steering P1.5 (2026-05-27, brief C3) — `?site=X` mis en évidence
  // au retour depuis le drawer V4 PilotageSourceBackLink. ScopeBar
  // bascule automatiquement sur le site cible.
  const [searchParams, setSearchParams] = useSearchParams();
  const tabFromUrl = searchParams.get('tab');
  const siteFromUrl = searchParams.get('site');
  const validInitialTab = ['timeline', 'baseline', 'comptage', 'pilotage', 'semaine-type'].includes(
    tabFromUrl
  )
    ? tabFromUrl
    : 'timeline';

  // Usage Steering P1.5 brief C3 — au mount (ou changement param), si un
  // site est passé en URL et diffère du scope courant, on bascule. Évite
  // une boucle : check stricte avant setSite (pas de re-render infini).
  useEffect(() => {
    if (!siteFromUrl) return;
    const targetSiteId = Number(siteFromUrl);
    if (Number.isFinite(targetSiteId) && targetSiteId !== selectedSiteId) {
      setSite(targetSiteId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteFromUrl]);
  const [data, setData] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [portfolio, setPortfolio] = useState(null);
  const [costByPeriod, setCostByPeriod] = useState(null);
  const [flexData, setFlexData] = useState(null);
  const [powerOpt, setPowerOpt] = useState(null);
  const [cdcSim, setCdcSim] = useState(null);
  const [flexPortfolio, setFlexPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState(validInitialTab);
  const [scopeLevel, setScopeLevel] = useState(selectedSiteId ? 'site' : 'org');
  const [archetypeFilter, setArchetypeFilter] = useState(null);

  // Usage Steering P1 — sync activeTab → URL (sans replace si même valeur).
  const handleTabChange = useCallback(
    (nextTab) => {
      setActiveTab(nextTab);
      const params = new URLSearchParams(searchParams);
      if (nextTab === 'timeline') {
        params.delete('tab');
      } else {
        params.set('tab', nextTab);
      }
      setSearchParams(params, { replace: true });
    },
    [searchParams, setSearchParams]
  );

  const _fetchId = useRef(0);
  const siteId = selectedSiteId;
  const siteName = scopedSites?.find((s) => s.id === siteId)?.nom;
  const totalSurface = scopedSites?.reduce((s, site) => s + (site.surface_m2 || 0), 0) || 0;
  const isMultiSite = scopeLevel !== 'site';

  // Tabs : masquer Comptage en mode multi-site
  const visibleTabs = useMemo(
    () => (isMultiSite ? ALL_TABS.filter((t) => t.id !== 'comptage') : ALL_TABS),
    [isMultiSite]
  );

  // Reset active tab if it's hidden
  useEffect(() => {
    if (activeTab === 'comptage' && isMultiSite) setActiveTab('timeline');
  }, [isMultiSite, activeTab]);

  // Fetch scoped dashboard data (with requestId guard to reject stale responses)
  useEffect(() => {
    const myId = ++_fetchId.current;
    setLoading(true);
    setError(null);
    setTimeline(null);

    const params = {};
    if (scopeLevel === 'site' && siteId) params.siteId = siteId;
    else if (scopeLevel === 'portfolio' && scope.portefeuilleId)
      params.portefeuilleId = scope.portefeuilleId;
    else if (scopeLevel === 'entite' && scope.entiteId) params.entityId = scope.entiteId;
    if (archetypeFilter) params.archetypeCode = archetypeFilter;

    getScopedUsagesDashboard(params)
      .then((d) => {
        if (myId === _fetchId.current) setData(d);
      })
      .catch((err) => {
        if (myId === _fetchId.current) setError(err?.response?.data?.detail || err.message);
      })
      .finally(() => {
        if (myId === _fetchId.current) setLoading(false);
      });

    getScopedUsageTimeline(params)
      .then((t) => {
        if (myId === _fetchId.current) setTimeline(t);
      })
      .catch(() => {});
  }, [siteId, scopeLevel, scope.portefeuilleId, scope.entiteId, archetypeFilter]);

  // Portfolio comparison (heatmap sidebar) + flex portfolio (bubble chart)
  // Re-fetch when archetypeFilter changes to show only filtered sites
  useEffect(() => {
    const orgId = scope?.orgId;
    if (orgId && scopedSites?.length >= 1) {
      getPortfolioUsageComparison(orgId, { archetypeCode: archetypeFilter })
        .then(setPortfolio)
        .catch(() => {});
      getFlexNebcoPortfolio({
        entityId: scope.entiteId,
        portefeuilleId: scope.portefeuilleId,
        archetypeCode: archetypeFilter,
      })
        .then(setFlexPortfolio)
        .catch(() => setFlexPortfolio(null));
    } else {
      setFlexPortfolio(null);
    }
  }, [scope?.orgId, scope?.entiteId, scope?.portefeuilleId, scopedSites?.length, archetypeFilter]);

  // Cost by period + flex NEBCO + power optimization (site mode only)
  useEffect(() => {
    if (scopeLevel === 'site' && siteId) {
      getCostByPeriod(siteId)
        .then(setCostByPeriod)
        .catch(() => setCostByPeriod(null));
      getFlexNebco(siteId)
        .then(setFlexData)
        .catch(() => setFlexData(null));
      getPowerOptimization(siteId)
        .then(setPowerOpt)
        .catch(() => setPowerOpt(null));
      getCdcSimulation(siteId)
        .then(setCdcSim)
        .catch(() => setCdcSim(null));
    } else {
      setCostByPeriod(null);
      setFlexData(null);
      setPowerOpt(null);
      setCdcSim(null);
    }
  }, [siteId, scopeLevel]);

  // Export Excel (dynamic import)
  const handleExportExcel = async () => {
    if (!data) return;
    const XLSX = await import('xlsx');
    const { summary, top_ues, baselines } = data;
    const wb = XLSX.utils.book_new();
    const kpiData = [
      ['Métrique', 'Valeur', 'Unité'],
      ['Conso totale', summary?.total_kwh, 'kWh/an'],
      ['Coût total', summary?.total_eur, 'EUR/an'],
      ['Score readiness', data.readiness?.score, '/100'],
    ];
    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(kpiData), 'KPIs');
    if (top_ues?.length) {
      const uesData = [
        ['Usage', 'kWh/an', 'Part %', 'IPE', 'Source', 'UES'],
        ...top_ues.map((u) => [
          u.label,
          u.kwh,
          u.pct_of_total,
          u.ipe_kwh_m2,
          u.data_source,
          u.is_significant ? 'Oui' : 'Non',
        ]),
      ];
      XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(uesData), 'UES');
    }
    if (baselines?.length) {
      const blData = [
        ['Usage', 'Baseline kWh', 'Actuel kWh', 'Écart kWh', 'Écart %', 'Tendance'],
        ...baselines.map((b) => [
          b.label,
          b.kwh_baseline,
          b.kwh_current,
          b.ecart_kwh,
          b.ecart_pct,
          b.trend,
        ]),
      ];
      XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(blData), 'Baseline');
    }
    const scopeLabel = archetypeFilter
      ? `${siteName || siteId || 'portfolio'}_${archetypeFilter}`
      : siteName || siteId || 'portfolio';
    XLSX.writeFile(
      wb,
      `PROMEOS_Usages_${scopeLabel}_${new Date().toISOString().slice(0, 10)}.xlsx`
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header score={null} />
        <ScopeBar
          scopeLevel={scopeLevel}
          onLevelChange={setScopeLevel}
          archetypeFilter={archetypeFilter}
          onArchetypeFilter={setArchetypeFilter}
        />
        <div className="p-8 text-center text-gray-400 text-sm">Chargement des usages...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header score={null} />
        <ScopeBar
          scopeLevel={scopeLevel}
          onLevelChange={setScopeLevel}
          archetypeFilter={archetypeFilter}
          onArchetypeFilter={setArchetypeFilter}
        />
        <div className="p-8">
          <div className="p-4 bg-red-50 rounded-xl text-red-700 text-sm">Erreur : {error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <Header
        score={data?.readiness?.score}
        level={data?.readiness?.level}
        details={data?.readiness?.details}
        recommendations={data?.readiness?.recommendations}
        onExportExcel={handleExportExcel}
      />

      {/* Scope Bar */}
      <ScopeBar
        scopeLevel={scopeLevel}
        onLevelChange={setScopeLevel}
        archetypeFilter={archetypeFilter}
        onArchetypeFilter={setArchetypeFilter}
      />

      {/* KPI Strip — 4 cartes */}
      <KpiStrip
        dashboard={data}
        scopeLevel={scopeLevel}
        sitesCount={data?.sites_count ?? scopedSites?.length ?? 1}
        totalSurface={
          scopeLevel === 'site'
            ? (scopedSites?.find((s) => s.id === siteId)?.surface_m2 ?? 0)
            : (data?.summary?.total_surface_m2 ?? totalSurface)
        }
      />

      {/* Top 2 colonnes : onglets + heatmap */}
      <div className="px-7 pb-4 grid grid-cols-1 lg:grid-cols-[5fr_3fr] gap-3.5">
        {/* Colonne gauche : onglets */}
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <TabBar active={activeTab} onChange={handleTabChange} tabs={visibleTabs} />
          {activeTab === 'timeline' && (
            <TimelineTab data={timeline} siteId={scopeLevel === 'site' ? siteId : null} />
          )}
          {activeTab === 'baseline' && (
            <BaselineTab
              baselines={data?.baselines}
              meteringPlan={isMultiSite ? null : data?.metering_plan}
            />
          )}
          {activeTab === 'comptage' && !isMultiSite && <ComptageTab data={data?.metering_plan} />}
          {/* Usage Steering P1 (2026-05-27, brief C2) — 4ᵉ onglet interne.
              Consomme /api/usages/pilotage-summary + sync vers ActionCenter V4. */}
          {activeTab === 'pilotage' && (
            <PilotageTab
              scope={{
                entityId: scope?.entityId,
                portefeuilleId: scope?.portefeuilleId,
                siteId: scopeLevel === 'site' ? siteId : null,
                archetypeCode: archetypeFilter,
              }}
            />
          )}
          {/* Sprint Énergie P1.S4 (2026-05-29) — onglet Semaine type
              branché sur /api/energy/week-profile. Composant autonome,
              consomme `useScope()` directement. Doctrine zéro calcul FE. */}
          {activeTab === 'semaine-type' && <WeekProfileTab />}
        </div>

        {/* Colonne droite : heatmap IPE */}
        <div className="flex flex-col gap-3.5">
          <HeatmapCard data={portfolio} currentSiteId={siteId} />
        </div>
      </div>

      {/* Grille 3 colonnes pleine largeur : Conformité + Coût + Flexibilité */}
      <div className="px-7 pb-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
        {data?.compliance && (
          <ComplianceCard data={data.compliance} archetypeFilter={archetypeFilter} />
        )}
        <CostCard data={data?.cost_breakdown} costByPeriod={costByPeriod} />
        {isMultiSite ? <FlexBubbleChart data={flexPortfolio} /> : <FlexNebcoCard data={flexData} />}
      </div>

      {/* Widgets additionnels site-level */}
      {(powerOpt || cdcSim) && (
        <div className="px-7 pb-4 grid grid-cols-1 md:grid-cols-2 gap-3.5">
          <PowerOptimizationCard data={powerOpt} />
          <CdcSimulationCard data={cdcSim} />
        </div>
      )}

      {/* Footer links contextuels */}
      <FooterLinks archetypeFilter={archetypeFilter} dashboard={data} />
    </div>
  );
}

// ── Header component (inline, minimal) ──────────────────────────────────

const LEVEL_BADGE = {
  GREEN: { bg: '#F0FDF4', color: '#16A34A', border: '#BBF7D0' },
  AMBER: { bg: '#FFFBEB', color: '#D97706', border: '#FDE68A' },
  RED: { bg: '#FEF2F2', color: '#DC2626', border: '#FECACA' },
};

const READINESS_LABELS = {
  usages_declared: 'Usages déclarés',
  sub_metering_coverage: 'Couverture comptage',
  data_quality: 'Qualité données',
  data_depth: 'Ancienneté données',
};

function Header({ score, level, details, recommendations, onExportExcel }) {
  const [showTooltip, setShowTooltip] = useState(false);
  const badge = LEVEL_BADGE[level] || LEVEL_BADGE.GREEN;

  return (
    <div className="px-7 py-5 flex justify-between items-center border-b border-gray-200 bg-white">
      <h1 className="text-lg font-bold tracking-tight">Usages énergétiques</h1>
      <div className="flex items-center gap-2">
        {score != null && (
          <div className="relative">
            <div
              onMouseEnter={() => setShowTooltip(true)}
              onMouseLeave={() => setShowTooltip(false)}
              className="px-3 py-1.5 rounded-full text-[13px] font-bold cursor-help"
              style={{
                background: badge.bg,
                color: badge.color,
                border: `1px solid ${badge.border}`,
              }}
            >
              {score}/100
            </div>
            {showTooltip && details && (
              <div className="absolute z-50 top-full right-0 mt-2 bg-white border border-gray-200 rounded-xl shadow-lg p-4 w-72 text-xs">
                <div className="font-semibold mb-2">Décomposition du score</div>
                {Object.entries(details).map(([key, d]) => (
                  <div key={key} className="flex justify-between py-1 border-b border-gray-100">
                    <span className="text-gray-500">{READINESS_LABELS[key] || key}</span>
                    <span className="font-semibold">
                      {d.score}/{d.max}
                    </span>
                  </div>
                ))}
                {recommendations?.length > 0 && (
                  <div className="mt-2 text-amber-600">
                    {recommendations.map((r, i) => (
                      <p key={i} className="py-0.5">
                        ▸ {r}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
        <button
          onClick={onExportExcel}
          className="px-3 py-1.5 rounded-lg border border-gray-200 bg-white text-xs font-medium hover:border-blue-400 hover:text-blue-600 transition print:hidden inline-flex items-center gap-1.5"
        >
          <FileSpreadsheet size={13} aria-hidden="true" />
          Excel
        </button>
        <button
          onClick={() => window.print()}
          className="px-3 py-1.5 rounded-lg border border-gray-200 bg-white text-xs font-medium hover:border-blue-400 hover:text-blue-600 transition print:hidden inline-flex items-center gap-1.5"
        >
          <Printer size={13} aria-hidden="true" />
          PDF
        </button>
      </div>
    </div>
  );
}
