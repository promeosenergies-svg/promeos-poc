/**
 * PROMEOS — Page Usages Énergétiques V3
 * Layout 2 colonnes + scope switcher + 3 onglets.
 * Orchestrateur : fetch centralisé, composants dans components/usages/.
 */
import React, { useEffect, useState } from 'react';
import { useScope } from '../contexts/ScopeContext';
import { getUsagesDashboard, getUsageTimeline, getPortfolioUsageComparison } from '../services/api';

import ScopeBar from '../components/usages/ScopeBar';
import KpiStrip from '../components/usages/KpiStrip';
import TabBar from '../components/usages/TabBar';
import TimelineTab from '../components/usages/TimelineTab';
import BaselineTab from '../components/usages/BaselineTab';
import ComptageTab from '../components/usages/ComptageTab';
import HeatmapCard from '../components/usages/HeatmapCard';
import ComplianceCard from '../components/usages/ComplianceCard';
import CostCard from '../components/usages/CostCard';
import FooterLinks from '../components/usages/FooterLinks';

const TABS = [
  { id: 'timeline', label: '📈 Évolution' },
  { id: 'baseline', label: '📊 Baseline' },
  { id: 'comptage', label: '🔌 Comptage' },
];

export default function UsagesDashboardPage() {
  const { selectedSiteId, scopedSites, scope } = useScope();
  const [data, setData] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('timeline');
  const [scopeLevel, setScopeLevel] = useState(selectedSiteId ? 'site' : 'org');

  const siteId = selectedSiteId;
  const siteName = scopedSites?.find((s) => s.id === siteId)?.nom;
  const totalSurface = scopedSites?.reduce((s, site) => s + (site.surface_m2 || 0), 0) || 0;

  // Fetch dashboard data
  useEffect(() => {
    if (!siteId) {
      setData(null);
      setTimeline(null);
      setLoading(false);
      return;
    }
    // Fetch per-site dashboard
    if (siteId) {
      setLoading(true);
      setError(null);
      getUsagesDashboard(siteId)
        .then(setData)
        .catch((err) => setError(err?.response?.data?.detail || err.message))
        .finally(() => setLoading(false));
      getUsageTimeline(siteId)
        .then(setTimeline)
        .catch(() => {});
    }
  }, [siteId, scopeLevel]);

  // Portfolio comparison
  useEffect(() => {
    const orgId = scope?.orgId;
    if (orgId && scopedSites?.length >= 2) {
      getPortfolioUsageComparison(orgId)
        .then(setPortfolio)
        .catch(() => {});
    }
  }, [scope?.orgId, scopedSites?.length]);

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
    XLSX.writeFile(
      wb,
      `PROMEOS_Usages_${siteName || siteId}_${new Date().toISOString().slice(0, 10)}.xlsx`
    );
  };

  // No site selected
  if (!siteId && !loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header score={null} />
        <ScopeBar scopeLevel={scopeLevel} onLevelChange={setScopeLevel} />
        <KpiStrip
          dashboard={null}
          scopeLevel={scopeLevel}
          sitesCount={scopedSites?.length || 0}
          totalSurface={totalSurface}
        />
        <div className="px-7 pb-4 grid grid-cols-1 lg:grid-cols-[5fr_3fr] gap-3.5">
          <div className="bg-white border border-gray-200 rounded-xl p-8 text-center text-gray-400 text-sm">
            Sélectionnez un site pour afficher les usages détaillés.
          </div>
          <div className="flex flex-col gap-3.5">
            <HeatmapCard data={portfolio} currentSiteId={null} />
          </div>
        </div>
        <FooterLinks />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header score={null} />
        <ScopeBar scopeLevel={scopeLevel} onLevelChange={setScopeLevel} />
        <div className="p-8 text-center text-gray-400 text-sm">Chargement des usages...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header score={null} />
        <ScopeBar scopeLevel={scopeLevel} onLevelChange={setScopeLevel} />
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
      <ScopeBar scopeLevel={scopeLevel} onLevelChange={setScopeLevel} />

      {/* KPI Strip — 4 cartes */}
      <KpiStrip
        dashboard={data}
        scopeLevel={scopeLevel}
        sitesCount={scopedSites?.length || 1}
        totalSurface={
          scopeLevel === 'site'
            ? scopedSites?.find((s) => s.id === siteId)?.surface_m2 || 0
            : totalSurface
        }
      />

      {/* Main 2 colonnes */}
      <div className="px-7 pb-4 grid grid-cols-1 lg:grid-cols-[5fr_3fr] gap-3.5">
        {/* Colonne gauche : onglets */}
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <TabBar active={activeTab} onChange={setActiveTab} tabs={TABS} />
          {activeTab === 'timeline' && <TimelineTab data={timeline} />}
          {activeTab === 'baseline' && (
            <BaselineTab baselines={data?.baselines} meteringPlan={data?.metering_plan} />
          )}
          {activeTab === 'comptage' && <ComptageTab data={data?.metering_plan} />}
        </div>

        {/* Colonne droite : contexte permanent */}
        <div className="flex flex-col gap-3.5">
          <HeatmapCard data={portfolio} currentSiteId={siteId} />
          <ComplianceCard data={data?.compliance} />
          <CostCard data={data?.cost_breakdown} />
        </div>
      </div>

      {/* Footer links */}
      <FooterLinks />
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
      <h1 className="text-lg font-bold tracking-tight">Usages Énergétiques</h1>
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
          className="px-3 py-1.5 rounded-lg border border-gray-200 bg-white text-xs font-medium hover:border-blue-400 hover:text-blue-600 transition print:hidden"
        >
          📊 Excel
        </button>
        <button
          onClick={() => window.print()}
          className="px-3 py-1.5 rounded-lg border border-gray-200 bg-white text-xs font-medium hover:border-blue-400 hover:text-blue-600 transition print:hidden"
        >
          🖨 PDF
        </button>
      </div>
    </div>
  );
}
