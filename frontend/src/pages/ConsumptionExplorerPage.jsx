/**
 * PROMEOS - ConsumptionExplorerPage (/consommations/explorer)
 * Sprint V11 WoW: Motor + Layers architecture
 * Motor: useExplorerMotor (data engine) + useExplorerURL (URL state sync)
 * Panels: Tunnel (P10-P90), Objectifs/Budgets, HP/HC, Gaz (beta)
 */
import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  Target,
  Clock,
  Flame,
  BarChart3,
  AlertTriangle,
  X,
  Zap,
  Database,
  Wifi,
  Info,
  Grid3x3,
  Cloud,
  Lightbulb,
} from 'lucide-react';
import { Badge, Button, EmptyState, EvidenceDrawer as GenericEvidenceDrawer } from '../ui';
import { useToast } from '../ui/ToastProvider';
import { useScope } from '../contexts/ScopeContext';
import { track } from '../services/tracker';
import StickyFilterBar from './consumption/StickyFilterBar';
import ContextBanner from './consumption/ContextBanner';
import InsightsStrip from './consumption/InsightsStrip';
import { computeAutoRange } from './consumption/helpers';
import { computeInsights } from './consumption/insightRules';
import useExplorerMotor from './consumption/useExplorerMotor';
import useExplorerURL from './consumption/useExplorerURL';
import useExplorerPresets from './consumption/useExplorerPresets';
import useExplorerMode from './consumption/useExplorerMode';
import PortfolioPanel from './consumption/PortfolioPanel';
import OverviewRow, { computeOverviewData } from './consumption/OverviewRow';
import { MAX_SITES, nonApplicableTabs } from './consumption/types';
import TimeseriesPanel from './consumption/TimeseriesPanel';
import SignaturePanel from './consumption/SignaturePanel';
import MeteoPanel from './consumption/MeteoPanel';
import InsightsPanel from './consumption/InsightsPanel';
import ConsoKpiHeader from '../components/ConsoKpiHeader';
import BenchmarkPanel from './consumption/BenchmarkPanel';
import TunnelPanel from './consumption/TunnelPanel';
import TargetsPanel from './consumption/TargetsPanel';
import HPHCPanel from './consumption/HPHCPanel';
import GasPanel from './consumption/GasPanel';
import { evidenceKwhTotal, evidenceCO2e } from '../ui/evidence.fixtures';

// ========================================
// Constants
// ========================================

const TAB_CONFIG = [
  { key: 'timeseries', label: 'Consommation', icon: BarChart3, desc: 'Série temporelle' },
  { key: 'insights', label: 'Insights', icon: Lightbulb, desc: 'P05 / P95 / anomalies' },
  { key: 'signature', label: 'Signature', icon: Grid3x3, desc: 'Empreinte horaire-hebdo' },
  { key: 'meteo', label: 'Météo', icon: Cloud, desc: 'Influence climatique' },
  { key: 'tunnel', label: 'Tunnel', icon: Activity, desc: 'Enveloppe P10-P90' },
  { key: 'targets', label: 'Objectifs', icon: Target, desc: 'Budgets & progression' },
  { key: 'hphc', label: 'HP/HC', icon: Clock, desc: 'Grille tarifaire' },
  { key: 'gas', label: 'Gaz', icon: Flame, desc: 'Beta' },
];

// ENERGY_OPTIONS + PERIOD_OPTIONS moved to StickyFilterBar

const REASON_CONFIG = {
  no_site: {
    icon: AlertTriangle,
    title: 'Site introuvable',
    text: "Le site sélectionné n'existe pas ou a été supprimé. Vérifiez votre sélection.",
    ctaLabel: null,
  },
  no_meter: {
    icon: Wifi,
    title: 'Aucun compteur configure',
    text: "Ce site n'a pas encore de compteur rattache. Connectez Enedis / GRDF ou ajoutez un compteur manuellement.",
    ctaLabel: 'Connecter un compteur',
    ctaPath: '/connectors',
  },
  no_readings: {
    icon: Database,
    title: 'Compteur present, aucun releve',
    text: "Un compteur est configure mais aucune donnee de consommation n'a ete importee.",
    ctaLabel: 'Importer des données',
    ctaPath: '/consommations/import',
  },
  insufficient_readings: {
    icon: BarChart3,
    title: 'Données insuffisantes',
    text: "Moins de 48 relevés disponibles. L'analyse nécessite davantage de données pour être fiable.",
    ctaLabel: 'Importer des données',
    ctaPath: '/consommations/import',
  },
  wrong_energy_type: {
    icon: Zap,
    title: "Pas de données pour ce type d'énergie",
    text: null, // dynamic
    ctaLabel: null,
  },
};

// ========================================
// Smart Empty State
// ========================================

function SmartEmptyState({
  reasons,
  energyTypes,
  onNavigate,
  onSwitchEnergy,
  isExpert,
  onGenerateDemo,
}) {
  if (!reasons?.length) {
    return (
      <EmptyState
        icon={BarChart3}
        title="Aucune donnee disponible"
        text="Vérifiez la configuration du site ou importez des données."
      />
    );
  }

  const primary = reasons[0];
  const config = REASON_CONFIG[primary] || REASON_CONFIG.no_readings;
  const Icon = config.icon;

  // Dynamic text for wrong_energy_type
  let text = config.text;
  if (primary === 'wrong_energy_type' && energyTypes?.length > 0) {
    text = `Aucune donnée pour ce vecteur énergétique. Types disponibles : ${energyTypes.join(', ')}.`;
  }

  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mb-4">
        <Icon size={32} className="text-gray-400" />
      </div>
      <h3 className="text-lg font-semibold text-gray-700 mb-1">{config.title}</h3>
      <p className="text-sm text-gray-500 mb-6 max-w-md">{text}</p>
      <div className="flex items-center gap-3">
        {config.ctaLabel && config.ctaPath && (
          <Button onClick={() => onNavigate(config.ctaPath)}>{config.ctaLabel}</Button>
        )}
        {primary === 'wrong_energy_type' && energyTypes?.length > 0 && (
          <Button onClick={() => onSwitchEnergy(energyTypes[0])}>
            Basculer vers {energyTypes[0]}
          </Button>
        )}
        {onGenerateDemo && (
          <Button variant="outline" onClick={onGenerateDemo}>
            Generer demo
          </Button>
        )}
      </div>
      {reasons.length > 1 && (
        <p className="text-xs text-gray-400 mt-4">Diagnostics : {reasons.join(', ')}</p>
      )}
      {isExpert && reasons?.length > 0 && (
        <div className="mt-4 bg-gray-50 rounded-lg p-3 text-left text-xs max-w-md">
          <p className="font-semibold text-gray-500">Debug</p>
          <p className="text-gray-400 mt-1">Reasons: {reasons.join(', ')}</p>
          {energyTypes?.length > 0 && (
            <p className="text-gray-400">Energy types: {energyTypes.join(', ')}</p>
          )}
        </div>
      )}
    </div>
  );
}

// ========================================
// Availability Skeleton
// ========================================

function AvailabilitySkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-10 bg-gray-200 rounded-lg w-full" />
      <div className="grid grid-cols-3 gap-3">
        <div className="h-20 bg-gray-200 rounded-lg" />
        <div className="h-20 bg-gray-200 rounded-lg" />
        <div className="h-20 bg-gray-200 rounded-lg" />
      </div>
      <div className="h-64 bg-gray-200 rounded-lg" />
    </div>
  );
}

// FilterBar + ContextBanner extracted to consumption/StickyFilterBar + consumption/ContextBanner
// TunnelPanel, TargetsPanel, HPHCPanel, GasPanel extracted to consumption/ (V23-H)

// Main Page
// ========================================

export default function ConsumptionExplorerPage() {
  const navigate = useNavigate();
  const { selectedSiteId, orgSites, sitesLoading, scopeLabel } = useScope();
  const { toast } = useToast();

  // ── UI mode (Classic / Expert) — localStorage only, never in URL ───────
  const { uiMode, isClassic, toggleUiMode } = useExplorerMode();

  // ── URL state (bidirectional sync) ─────────────────────────────────────
  const { urlState, setUrlParams } = useExplorerURL();

  // ── Site list for picker: use full org list (orgSites), not filtered scopedSites ──
  // scopedSites is filtered by scope.siteId, which limits the picker to 1 site when a
  // site is selected. orgSites always returns all sites for the org.
  const sites = orgSites || [];

  // Stable key for org-sites set (changes when org switches or sites load)
  const orgSiteIdsKey = useMemo(
    () =>
      sites
        .map((s) => s.id)
        .sort()
        .join(','),
    [sites]
  );

  // ── Resolve initial site IDs from URL or scope ─────────────────────────
  // Note: motor.state.siteIds is only initialized once (useState in useExplorerMotor).
  // The org-change effect below (using orgSiteIdsKey) handles subsequent updates.
  const initialSiteIds = (() => {
    if (urlState.siteIds.length) return urlState.siteIds;
    if (selectedSiteId) return [selectedSiteId];
    if (sites.length) return [sites[0].id];
    return [];
  })();

  // ── Motor (data engine) ────────────────────────────────────────────────
  const motor = useExplorerMotor({
    initialSiteIds,
    initialEnergy: urlState.energy,
    initialDays: urlState.days,
  });

  const {
    state: { siteIds, energyType, days, mode, unit, layers },
    setSiteIds,
    setEnergyType,
    setDays,
    setMode,
    setUnit,
    mergedAvailability,
    primarySiteId,
    primaryAvailability,
    loading,
  } = motor;

  // ── Portfolio mode (V12-A): all sites, aggregated view ────────────────
  const [isPortfolioMode, setIsPortfolioMode] = useState(false);
  const [portfolioBannerDismissed, setPortfolioBannerDismissed] = useState(false);

  const handleTogglePortfolio = useCallback(() => {
    setPortfolioBannerDismissed(false); // show banner again on each entry
    const next = !isPortfolioMode;
    setIsPortfolioMode(next);
    if (next) {
      // Select all available sites when entering portfolio mode
      const allIds = sites.map((s) => s.id);
      setSiteIds(allIds);
      setMode('agrege'); // only agrege is valid in portfolio
    } else {
      // Return to single/first site when leaving portfolio
      const firstSiteId = selectedSiteId || (sites.length ? sites[0].id : null);
      setSiteIds(firstSiteId ? [firstSiteId] : []);
    }
  }, [isPortfolioMode, sites, selectedSiteId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Custom date range (V11.1-A) ────────────────────────────────────────
  // ── Evidence Drawer ("Pourquoi ce chiffre ?") ─────────────────────────
  const [evidenceKpiOpen, setEvidenceKpiOpen] = useState(null);
  const consoEvidenceMap = useMemo(() => {
    const periodStr = `${days} jours`;
    const hphc = motor.primaryHphc;
    const totalKwh = hphc?.total_kwh ?? motor.primaryTunnel?.total_kwh ?? null;
    const kwhStr = totalKwh != null ? `${Math.round(totalKwh).toLocaleString('fr-FR')} kWh` : null;
    const co2Kg = totalKwh != null ? Math.round(totalKwh * 0.052) : null;
    const co2Str = co2Kg != null ? `${co2Kg.toLocaleString('fr-FR')} kg CO2e` : null;
    return {
      'conso-kwh-total': evidenceKwhTotal(scopeLabel, periodStr, kwhStr),
      'conso-co2e': evidenceCO2e(scopeLabel, periodStr, co2Str),
    };
  }, [scopeLabel, days, motor.primaryHphc, motor.primaryTunnel]); // eslint-disable-line react-hooks/exhaustive-deps

  const [startDate, setStartDate] = useState(urlState.startDate || null);
  const [endDate, setEndDate] = useState(urlState.endDate || null);

  // Sync custom dates → URL
  useEffect(() => {
    setUrlParams({
      start: startDate || null,
      end: endDate || null,
    });
  }, [startDate, endDate]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Sync Motor state → URL ─────────────────────────────────────────────
  useEffect(() => {
    setUrlParams({ sites: siteIds, energy: energyType, days, mode, unit });
  }, [siteIds, energyType, days, mode, unit]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Tab state (persisted in URL) ───────────────────────────────────────
  const [activeTab, setActiveTab] = useState(urlState.tab || 'timeseries');
  const switchTab = (tab) => {
    setActiveTab(tab);
    setUrlParams({ tab });
    track('explorer_tab', { tab });
  };

  // ── Auto-calibrate period from availability ────────────────────────────
  useEffect(() => {
    const avail = primaryAvailability;
    if (avail?.has_data && avail.first_ts && avail.last_ts) {
      const autoDays = computeAutoRange(avail.first_ts, avail.last_ts);
      if (autoDays !== days) setDays(autoDays);
    }
    // Auto-switch tab for gas-only
    if (avail?.has_data && energyType === 'gas' && activeTab === 'tunnel') {
      setActiveTab('gas');
    }
  }, [primaryAvailability]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Track previous selectedSiteId to detect explicit scope changes ────────
  const prevSelectedSiteIdRef = useRef(selectedSiteId);

  // ── Validate + reset siteIds on org change or initial site load ─────────
  // Fires when: (a) org changes → orgSiteIdsKey changes → stale IDs detected
  //             (b) sites load from empty → auto-select fires
  //             (c) selectedSiteId changes → force-sync to new selection
  useEffect(() => {
    if (!orgSites.length) return; // Sites not yet loaded — wait
    const orgSiteIdsSet = new Set(orgSites.map((s) => s.id));

    // Detect explicit scope switch: user changed site in scope switcher
    const scopeChanged = selectedSiteId !== prevSelectedSiteIdRef.current;
    prevSelectedSiteIdRef.current = selectedSiteId;

    if (scopeChanged && selectedSiteId && orgSiteIdsSet.has(Number(selectedSiteId))) {
      // User explicitly switched scope → force-sync to the new site
      setSiteIds([Number(selectedSiteId)]);
      return;
    }

    setSiteIds((prev) => {
      // Keep IDs that exist in the current org
      const valid = prev.filter((id) => orgSiteIdsSet.has(Number(id)));
      if (valid.length > 0) {
        // Already valid — return prev ref if no IDs were dropped (avoids re-render)
        return valid.length === prev.length ? prev : valid;
      }
      // No valid IDs → auto-select
      if (selectedSiteId && orgSiteIdsSet.has(Number(selectedSiteId))) {
        return [Number(selectedSiteId)];
      }
      // "Tous les sites": select all if N ≤ 5, else just first
      return orgSites.length <= 5 ? orgSites.map((s) => s.id) : [orgSites[0].id];
    });
  }, [orgSiteIdsKey, selectedSiteId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Reset to defaults (V11.1-A) ────────────────────────────────────────
  const handleReset = useCallback(() => {
    const firstSiteId = selectedSiteId || (sites.length ? sites[0].id : null);
    setSiteIds(firstSiteId ? [firstSiteId] : []);
    setEnergyType('electricity');
    setDays(30);
    setMode('agrege');
    setUnit('kwh');
    setStartDate(null);
    setEndDate(null);
    setUrlParams({
      sites: firstSiteId ? [firstSiteId] : [],
      energy: 'electricity',
      days: 30,
      mode: 'agrege',
      unit: 'kwh',
      start: null,
      end: null,
    });
  }, [selectedSiteId, sites]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── V21-C: Granularity override (user-selectable pills) ─────────────────
  const [granularity, setGranularity] = useState('auto');
  // ── V22-B: Sampling minutes from backend meta (for data-frequency intersection) ──
  const [samplingMinutes, setSamplingMinutes] = useState(null);
  const handleMeta = useCallback((m) => {
    if (m?.sampling_minutes != null) setSamplingMinutes(m.sampling_minutes);
  }, []);

  // ── V20-D / V21-F: Demo generation — generates MeterReading data for site, then forces refetch ──
  // Supports energy_vector param (V21-F: gas demo CTA)
  const [refreshKey, setRefreshKey] = useState(0);
  const handleGenerateDemo = useCallback(async () => {
    if (!siteIds.length) return;
    try {
      const ev = energyType === 'gas' ? 'gas' : 'electricity';
      await fetch(
        `/api/ems/demo/generate_timeseries?site_id=${siteIds[0]}&days=90&energy_vector=${ev}`,
        { method: 'POST' }
      );
      setRefreshKey((k) => k + 1); // force TimeseriesPanel to remount → fresh fetch
    } catch (e) {
      toast('Erreur generation demo', 'error');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteIds, energyType]);

  // ── Presets (V11.1-C) ──────────────────────────────────────────────────
  const { presets, savePreset, loadPreset, deletePreset } = useExplorerPresets();

  const handleSavePreset = useCallback(
    (name) => {
      savePreset(name, {
        siteIds,
        energy: energyType,
        days,
        mode,
        unit,
        startDate,
        endDate,
      });
    },
    [siteIds, energyType, days, mode, unit, startDate, endDate]
  ); // eslint-disable-line react-hooks/exhaustive-deps

  const handleLoadPreset = useCallback((name) => {
    const state = loadPreset(name);
    if (!state) return;
    if (state.siteIds) setSiteIds(state.siteIds);
    if (state.energy) setEnergyType(state.energy);
    if (state.days) setDays(state.days);
    if (state.mode) setMode(state.mode);
    if (state.unit) setUnit(state.unit);
    if (state.startDate !== undefined) setStartDate(state.startDate);
    if (state.endDate !== undefined) setEndDate(state.endDate);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Navigation helpers ─────────────────────────────────────────────────
  const handleNavigate = useCallback(
    (path) => {
      navigate(path);
    },
    [navigate]
  );
  const handleSwitchEnergy = useCallback(
    (type) => {
      setEnergyType(type);
      if (type === 'gas') switchTab('gas');
      else if (activeTab === 'gas') switchTab('timeseries'); // V19: only leave gas tab when on it
    },
    [activeTab]
  ); // eslint-disable-line react-hooks/exhaustive-deps

  const availability = mergedAvailability || primaryAvailability;
  const hasData = availability?.has_data === true;
  const showContent = hasData && !loading;
  const siteId = primarySiteId; // backward compat for panels

  return (
    <div className="space-y-5">
      {/* V1.3: Scope coherence banner — single site indicator */}
      {selectedSiteId && siteIds.length === 1 && (
        <div className="flex items-center gap-2 bg-blue-50 border border-blue-200 rounded-lg px-4 py-2.5 text-sm">
          <Info size={14} className="text-blue-500 shrink-0" />
          <span className="text-blue-700">
            Vous explorez <strong>{scopeLabel}</strong>. La multi-selection est disponible via le
            selecteur de sites ci-dessous.
          </span>
        </div>
      )}

      {/* UI Mode toggle — persisted in localStorage, never in URL */}
      <div className="flex justify-end">
        <button
          onClick={toggleUiMode}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition text-gray-600 border-gray-200 bg-white hover:bg-gray-50"
          title={
            isClassic
              ? 'Passer en mode Expert (contrôles avancés)'
              : 'Passer en mode Classique (vue standard)'
          }
        >
          {isClassic ? '⚙ Mode Expert' : '← Mode Classique'}
        </button>
      </div>

      {/* Unified sticky filter bar */}
      <StickyFilterBar
        uiMode={uiMode}
        siteIds={siteIds}
        setSiteIds={setSiteIds}
        siteId={siteId}
        setSiteId={(id) => setSiteIds([id])}
        sites={sites}
        energyType={energyType}
        setEnergyType={setEnergyType}
        availableTypes={availability?.energy_types}
        days={days}
        setDays={setDays}
        startDate={startDate}
        setStartDate={setStartDate}
        endDate={endDate}
        setEndDate={setEndDate}
        mode={mode}
        setMode={setMode}
        unit={unit}
        setUnit={setUnit}
        availability={availability}
        isPortfolioMode={isPortfolioMode}
        onTogglePortfolio={sites.length > 1 ? handleTogglePortfolio : undefined}
        onReset={handleReset}
        onCopyLink={() => {
          try {
            navigator.clipboard.writeText(window.location.href);
          } catch {}
        }}
        onSave={handleSavePreset}
        savedPresets={presets}
        onLoadPreset={handleLoadPreset}
        onDeletePreset={deletePreset}
        sitesLoading={sitesLoading}
        granularity={granularity}
        setGranularity={setGranularity}
        samplingMinutes={samplingMinutes}
      />

      {/* Portfolio info banner — non-blocking, dismissible */}
      {isPortfolioMode && !portfolioBannerDismissed && (
        <div className="flex items-start gap-2 px-3 py-2 bg-indigo-50 border border-indigo-200 rounded-lg text-xs text-indigo-700">
          <Info size={14} className="shrink-0 mt-0.5 text-indigo-500" />
          <span className="flex-1">
            <strong>Mode Portfolio</strong> — vue agrégée multi-sites (mode Agrégé uniquement).
            Chaque site contribue à l&apos;enveloppe globale. Pour comparer des sites
            individuellement, quittez le Portfolio.
          </span>
          <button
            onClick={() => setPortfolioBannerDismissed(true)}
            className="shrink-0 text-indigo-400 hover:text-indigo-600"
            aria-label="Fermer la bannière Portfolio"
          >
            <X size={13} />
          </button>
        </div>
      )}

      {/* Context banner (site info + date range) */}
      <ContextBanner availability={availability} />

      {/* KPI Header — 6 KPIs respecting scope global */}
      {showContent && (
        <ConsoKpiHeader
          tunnel={motor.primaryTunnel}
          hphc={motor.primaryHphc}
          progression={motor.primaryProgression}
          confidence={availability?.confidence}
          onEvidence={setEvidenceKpiOpen}
        />
      )}

      {/* Loading skeleton */}
      {loading && <AvailabilitySkeleton />}

      {/* Smart empty state — only for non-timeseries Expert tabs (Classic + timeseries tab use TimeseriesPanel's own states) */}
      {!loading && availability && !hasData && !isClassic && activeTab !== 'timeseries' && (
        <SmartEmptyState
          reasons={availability.reasons}
          energyTypes={availability.energy_types}
          onNavigate={handleNavigate}
          onSwitchEnergy={handleSwitchEnergy}
          isExpert={!isClassic}
          onGenerateDemo={siteIds.length ? handleGenerateDemo : undefined}
        />
      )}

      {/* Portfolio mode — shown instead of tab panels */}
      {isPortfolioMode && (loading || (availability && hasData) || !loading) && (
        <>
          {/* OverviewRow (aggregate) */}
          {motor.primaryTunnel && (
            <OverviewRow data={computeOverviewData(motor.primaryTunnel)} unit={unit} />
          )}
          <PortfolioPanel motor={motor} sites={sites} unit={unit} />
        </>
      )}

      {/* Main content — non-portfolio, within site limit */}
      {!isPortfolioMode && siteIds.length <= MAX_SITES && (
        <>
          {/* OverviewRow — only when real data is ready */}
          {showContent && motor.primaryTunnel && (
            <OverviewRow data={computeOverviewData(motor.primaryTunnel)} unit={unit} />
          )}

          {isClassic ? (
            /* ── Classic mode: TimeseriesPanel ALWAYS rendered (handles own loading/empty/error) ── */
            <>
              <TimeseriesPanel
                key={refreshKey}
                siteIds={siteIds}
                energyType={energyType}
                days={days}
                startDate={startDate}
                endDate={endDate}
                unit={unit}
                mode={mode}
                sites={sites}
                availability={availability}
                granularityOverride={granularity === 'auto' ? null : granularity}
                onNavigate={handleNavigate}
                onExtendPeriod={() => setDays(365)}
                onSelectAll={sites.length ? () => setSiteIds(sites.map((s) => s.id)) : undefined}
                onGenerateDemo={siteIds.length ? handleGenerateDemo : undefined}
                onMeta={handleMeta}
              />
              {/* Benchmark: reference profile comparison (Classic mode) */}
              {showContent && (
                <BenchmarkPanel
                  siteId={siteId}
                  days={days}
                  startDate={startDate}
                  endDate={endDate}
                  seriesData={null}
                  toast={toast}
                />
              )}
            </>
          ) : (
            /* ── Expert mode: tab bar always visible + panel routing ── */
            <>
              {/* Tab bar — always visible regardless of data state */}
              <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
                {TAB_CONFIG.map((tab) => {
                  const Icon = tab.icon;
                  const active = activeTab === tab.key;
                  if (nonApplicableTabs(energyType).has(tab.key)) return null;
                  return (
                    <button
                      key={tab.key}
                      onClick={() => switchTab(tab.key)}
                      className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition flex-1 justify-center ${
                        active
                          ? 'bg-white text-blue-700 shadow-sm'
                          : 'text-gray-600 hover:text-gray-900'
                      }`}
                    >
                      <Icon size={16} />
                      <span>{tab.label}</span>
                      {tab.key === 'gas' && (
                        <Badge variant="warn" className="text-[10px] px-1 py-0">
                          Beta
                        </Badge>
                      )}
                    </button>
                  );
                })}
              </div>

              {/* InsightsStrip — only when data ready */}
              {showContent && (
                <InsightsStrip
                  insights={computeInsights(
                    {
                      primaryTunnel: motor.primaryTunnel,
                      primaryHphc: motor.primaryHphc,
                      primaryGas: motor.primaryGas,
                      primaryWeather: motor.primaryWeather,
                      primaryProgression: motor.primaryProgression,
                    },
                    mode,
                    unit
                  )}
                />
              )}

              {/* Panel content */}
              <div>
                {/* TimeseriesPanel: ALWAYS rendered on timeseries tab — handles own loading/empty/error */}
                {activeTab === 'timeseries' && (
                  <TimeseriesPanel
                    key={refreshKey}
                    siteIds={siteIds}
                    energyType={energyType}
                    days={days}
                    startDate={startDate}
                    endDate={endDate}
                    unit={unit}
                    mode={mode}
                    sites={sites}
                    availability={availability}
                    granularityOverride={granularity === 'auto' ? null : granularity}
                    onNavigate={handleNavigate}
                    onExtendPeriod={() => setDays(365)}
                    onSelectAll={
                      sites.length ? () => setSiteIds(sites.map((s) => s.id)) : undefined
                    }
                    onGenerateDemo={siteIds.length ? handleGenerateDemo : undefined}
                    onMeta={handleMeta}
                  />
                )}
                {/* Benchmark: reference profile comparison — below timeseries */}
                {activeTab === 'timeseries' && showContent && (
                  <BenchmarkPanel
                    siteId={siteId}
                    days={days}
                    startDate={startDate}
                    endDate={endDate}
                    seriesData={null}
                    toast={toast}
                  />
                )}
                {/* Insights: statistical analysis — own data fetch, no Motor dependency */}
                {activeTab === 'insights' && (
                  <InsightsPanel siteIds={siteIds} energyType={energyType} days={days} />
                )}
                {/* Signature + Météo: use own data fetch, no Motor dependency */}
                {activeTab === 'signature' && (
                  <SignaturePanel siteIds={siteIds} energyType={energyType} days={days} />
                )}
                {activeTab === 'meteo' && (
                  <MeteoPanel siteIds={siteIds} energyType={energyType} days={days} />
                )}
                {/* Other panels: require showContent (depend on Motor availability data) */}
                {activeTab === 'tunnel' && showContent && (
                  <TunnelPanel
                    siteId={siteId}
                    days={days}
                    energyType={energyType}
                    showSignature={layers.signature}
                    toast={toast}
                    initialTunnel={motor.primaryTunnel}
                  />
                )}
                {activeTab === 'targets' && showContent && (
                  <TargetsPanel
                    siteId={siteId}
                    energyType={energyType}
                    toast={toast}
                    initialTargets={motor.primaryTargets}
                    initialProgression={motor.primaryProgression}
                    onRefreshMotor={motor.refresh}
                  />
                )}
                {activeTab === 'hphc' && showContent && (
                  <HPHCPanel
                    siteId={siteId}
                    days={days}
                    toast={toast}
                    initialBreakdown={motor.primaryHphc}
                  />
                )}
                {activeTab === 'gas' && showContent && (
                  <GasPanel
                    siteId={siteId}
                    days={days}
                    onGenerateDemo={siteIds.length ? handleGenerateDemo : undefined}
                    toast={toast}
                    initialGas={motor.primaryGas}
                    initialWeather={motor.primaryWeather}
                  />
                )}
              </div>
            </>
          )}
        </>
      )}

      {/* Blocked state: too many sites in comparatif (guard) */}
      {!isPortfolioMode && !loading && siteIds.length > MAX_SITES && (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="w-14 h-14 rounded-full bg-amber-50 flex items-center justify-center mb-4">
            <BarChart3 size={28} className="text-amber-500" />
          </div>
          <h3 className="text-base font-semibold text-gray-700 mb-1">Trop de sites sélectionnés</h3>
          <p className="text-sm text-gray-500 mb-4 max-w-sm">
            Le mode comparatif supporte jusqu'à {MAX_SITES} sites simultanément. Passez en mode
            Portfolio pour visualiser tous vos sites.
          </p>
          <button
            onClick={handleTogglePortfolio}
            className="px-4 py-2 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
          >
            Passer en mode Portfolio
          </button>
        </div>
      )}

      {/* ── Evidence Drawer ("Pourquoi ce chiffre ?") ── */}
      <GenericEvidenceDrawer
        open={!!evidenceKpiOpen}
        onClose={() => setEvidenceKpiOpen(null)}
        evidence={evidenceKpiOpen ? consoEvidenceMap[evidenceKpiOpen] : null}
      />
    </div>
  );
}
