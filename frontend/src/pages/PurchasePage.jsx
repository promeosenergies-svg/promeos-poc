/**
 * PROMEOS — Achat Energie V2 (V72 UX)
 * Simulateur de scenarios d'achat: Fixe / Indexe / Spot / ReFlex Solar
 * V1.1: + Portfolio roll-up, Echeances, Historique tabs.
 * Brique 3: + Energy Gate, WOW datasets, A4 exports.
 * V71: + Scénarios cockpit, actions CTAs.
 * V72: + Scope lock, autosave, volume toggle, confidence badges.
 * V73: + Scope unlock fix, skipSiteHeader, tab deep-link, assistant CTA, renewals re-fetch.
 * V74: + ReFlex Solar card, blocs horaires badges, effort score, cross-brique CTAs.
 * V75: + ReFlex report toggle/slider, portfolio ReFlex table, top-lists, campaign CTA.
 * V76: + Rename ReFlex → Budget Securise (user-facing labels only), scenario_label in prefills.
 * V77: + Rename Budget Securise → Tarif Heures Solaires, bloc explicability, assistant offer, deep-link CTA.
 * V78: + Audit THS — sous-titre grand public, creneaux ete/hiver sur carte, CTAs enrichis.
 * V79: + Cross-brique Performance, CTA Voir performance, toMonitoring, dejargon.
 * V80: + Badge Sans penalite, nettoyage tooltip jargon, tests audit final.
 * V81: + Header dynamique strategies, CTA Tester dans l'Assistant, deep-link assistant.
 * V82: + Composant "Option THS" structure (titre, 2 bullets, badge Sans penalite prominent).
 */
import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useScope } from '../contexts/ScopeContext';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { PageShell, Badge } from '../ui';
import { SkeletonCard } from '../ui/Skeleton';
import Tooltip from '../ui/Tooltip';
import { useToast } from '../ui/ToastProvider';
import useDataReadiness from '../hooks/useDataReadiness';
import { computeDataConfidence } from '../models/dataReadinessModel';
import ExportNoteDecision from '../components/ExportNoteDecision';
import ExportPackRFP from '../components/ExportPackRFP';
import PurchaseErrorBoundary from '../components/PurchaseErrorBoundary';
import PurchaseDebugDrawer from '../components/PurchaseDebugDrawer';
import {
  getPurchaseEstimate,
  getPurchaseAssumptions,
  putPurchaseAssumptions,
  getPurchasePreferences,
  putPurchasePreferences,
  computePurchaseScenarios,
  getPurchaseResults,
  acceptPurchaseResult,
  computePortfolio,
  getPortfolioResults,
  getPurchaseRenewals,
  getPurchaseHistory,
  seedWowHappy,
  seedWowDirty,
} from '../services/api';
import { toActionNew, toActionsList, toPurchaseAssistant, toPurchase, toConsoExplorer, toBillIntel, toConsoDiag, toMonitoring } from '../services/routes';
import {
  ShoppingCart,
  Calculator,
  Settings2,
  CheckCircle2,
  TrendingDown,
  Shield,
  Zap,
  Leaf,
  AlertTriangle,
  Building2,
  Clock,
  History,
  Lock,
  Info,
  Database,
  AlertOctagon,
  Printer,
  FileText,
  Plus,
  ExternalLink,
  HelpCircle,
  Target,
  ToggleLeft,
  ToggleRight,
  RefreshCw,
  BadgeCheck,
  Sun,
  BarChart3,
  FileSearch,
  Sliders,
  Award,
  Flame,
  ArrowUpDown,
  Activity,
  Rocket,
} from 'lucide-react';

const STRATEGY_META = {
  fixe: {
    label: 'Prix Fixe',
    icon: Shield,
    bgClass: 'bg-blue-50',
    textClass: 'text-blue-600',
    desc: 'Prix garanti sur toute la duree du contrat',
  },
  indexe: {
    label: 'Indexe',
    icon: TrendingDown,
    bgClass: 'bg-green-50',
    textClass: 'text-green-600',
    desc: 'Prix suit un indice marche avec plafond',
  },
  spot: {
    label: 'Spot',
    icon: Zap,
    bgClass: 'bg-orange-50',
    textClass: 'text-orange-600',
    desc: 'Prix marche temps reel, economies max',
  },
  reflex_solar: {
    label: 'Tarif Heures Solaires',
    icon: Sun,
    bgClass: 'bg-amber-50',
    textClass: 'text-amber-600',
    desc: "Payez moins quand le soleil brille — sans surcoût si vous ne changez rien.",
    dynamic: true,
  },
};

const RISK_COLORS = {
  low: 'text-green-600 bg-green-50',
  medium: 'text-yellow-600 bg-yellow-50',
  high: 'text-red-600 bg-red-50',
};

const URGENCY_STYLES = {
  red: 'bg-red-100 text-red-700 border-red-200',
  orange: 'bg-orange-100 text-orange-700 border-orange-200',
  yellow: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  gray: 'bg-gray-100 text-gray-600 border-gray-200',
};

function round1(n) { return Math.round(n * 10) / 10; }

function riskLevel(score) {
  if (score <= 30) return 'low';
  if (score <= 60) return 'medium';
  return 'high';
}

const TABS = [
  { key: 'simulation', label: 'Simulation', icon: Calculator },
  { key: 'portefeuille', label: 'Portefeuille', icon: Building2 },
  { key: 'echeances', label: 'Échéances', icon: Clock },
  { key: 'historique', label: 'Historique', icon: History },
];

/** Map deep-link ?filter= values to the corresponding tab key. */
const FILTER_TO_TAB = {
  renewal: 'echeances',
  missing: 'portefeuille',
};

const VALID_TABS = new Set(TABS.map((t) => t.key));

/** Hypothèses clés derrière chaque stratégie (affichées dans "Pourquoi ?"). */
const STRATEGY_WHY = {
  fixe: 'Budget prévisible à 100 %. Aucune exposition marché. Idéal si la visibilité budgétaire prime.',
  indexe: "Suit un indice marché avec plafond. Potentiel d'économie ~5-10 % vs Fixe, mais légère exposition à la volatilité.",
  spot: "Prix temps réel sans marge intermédiaire. Économie potentielle maximale, mais forte volatilité. Réservé aux profils avertis.",
  reflex_solar: "• Été : prix bas de 13h à 16h (sem.) et 10h–17h (WE) grâce à la surproduction solaire.\n• Hiver : créneaux réduits 8h–10h et 17h–20h — restez gagnant toute l'année.\n• Aucune pénalité si vous ne décalez rien. Report optionnel en mode Expert pour maximiser.",
};

export default function PurchasePage() {
  const { scopedSites, scope, selectedSiteId: scopeSiteId } = useScope();
  const { isExpert } = useExpertMode();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // Data confidence (Step 3.1)
  const purchaseKpis = useMemo(() => ({
    total: scopedSites.length,
    conformes: 0, nonConformes: 0, aRisque: 0,
    couvertureDonnees: scopedSites.length > 0 ? Math.round(scopedSites.filter(s => s.conso_kwh_an > 0).length / scopedSites.length * 100) : 0,
  }), [scopedSites]);
  const { readinessState: purchaseReadiness } = useDataReadiness(purchaseKpis);
  const dataConfidence = useMemo(() => computeDataConfidence(purchaseReadiness), [purchaseReadiness]);

  // Tab state — initialise from ?tab= or ?filter= deep-link if present
  const [activeTab, setActiveTab] = useState(() => {
    const tab = searchParams.get('tab');
    if (tab && VALID_TABS.has(tab)) return tab;
    const filter = searchParams.get('filter');
    return (filter && FILTER_TO_TAB[filter]) || 'simulation';
  });

  // Sync tab ↔ URL: when filter changes externally, update tab
  useEffect(() => {
    const filter = searchParams.get('filter');
    const mapped = filter && FILTER_TO_TAB[filter];
    if (mapped && mapped !== activeTab) setActiveTab(mapped);
  }, [searchParams, activeTab]);

  // When user clicks a tab, update URL to keep it in sync
  const handleTabChange = useCallback(
    (tabKey) => {
      setActiveTab(tabKey);
      const filterEntry = Object.entries(FILTER_TO_TAB).find(([, v]) => v === tabKey);
      if (filterEntry) {
        setSearchParams({ filter: filterEntry[0] }, { replace: true });
      } else {
        // Remove filter param for tabs without a deep-link alias
        setSearchParams({}, { replace: true });
      }
    },
    [setSearchParams]
  );

  // V73: Scope lock — if bandeau has a selected site, lock it (user can unlock via "Changer")
  const [scopeOverride, setScopeOverride] = useState(false);
  const isScopeLocked = !!scopeSiteId && !scopeOverride;

  // Simulation state (V1)
  const [selectedSiteId, setSelectedSiteId] = useState(null);
  const [estimate, setEstimate] = useState(null);
  const [assumptions, setAssumptions] = useState({
    volume_kwh_an: 0,
    horizon_months: 24,
    energy_type: 'elec',
    profile_factor: 1.0,
  });
  const [preferences, setPreferences] = useState({
    risk_tolerance: 'medium',
    budget_priority: 0.5,
    green_preference: false,
  });
  const [scenarios, setScenarios] = useState([]);
  const [loading, setLoading] = useState(false);
  const [computing, setComputing] = useState(false);
  const [acceptedId, setAcceptedId] = useState(null);

  // V72: volume toggle (estimation vs manual)
  const [useEstimation, setUseEstimation] = useState(true);

  // V75: RéFlex report toggle + slider
  const [reportEnabled, setReportEnabled] = useState(false);
  const [reportPct, setReportPct] = useState(0.15);

  // V72: autosave timer
  const autosaveTimer = useRef(null);

  // V1.1 state
  const [portfolioData, setPortfolioData] = useState(null);
  const [portfolioLoading, setPortfolioLoading] = useState(false);
  const [renewals, setRenewals] = useState([]);
  const [renewalsLoading, setRenewalsLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [selectedRun, setSelectedRun] = useState(null);
  const [seedingWow, setSeedingWow] = useState(null); // 'happy' | 'dirty' | null
  const [seedResult, setSeedResult] = useState(null);

  // Brique 3: Export state
  const [showNoteDecision, setShowNoteDecision] = useState(false);
  const [showPackRFP, setShowPackRFP] = useState(false);

  // WOW dataset handlers
  const handleSeedWow = async (mode) => {
    setSeedingWow(mode);
    setSeedResult(null);
    try {
      const result = mode === 'happy' ? await seedWowHappy() : await seedWowDirty();
      setSeedResult(result);
      // Reload portfolio after seeding
      if (result.org_id) {
        const data = await computePortfolio(result.org_id);
        setPortfolioData(data);
      }
    } catch (err) {
      setSeedResult({ error: err.message || 'Erreur lors du chargement' });
    }
    setSeedingWow(null);
  };

  // V73: Scope-aware site selection — locked if scope has a site, reset override on scope change
  useEffect(() => {
    setScopeOverride(false); // reset override when bandeau scope changes
    // V77: URL deep-link site_id takes priority
    const urlSiteId = searchParams.get('site_id');
    if (urlSiteId) {
      const parsed = Number(urlSiteId);
      if (!isNaN(parsed)) { setSelectedSiteId(parsed); return; }
    }
    if (scopeSiteId) {
      setSelectedSiteId(scopeSiteId);
    } else if (scopedSites.length > 0) {
      setSelectedSiteId((prev) => prev ?? scopedSites[0].id);
    }
  }, [scopedSites, scopeSiteId, searchParams]);

  // Load data when site changes
  const loadSiteData = useCallback(async (siteId) => {
    if (!siteId) return;
    setLoading(true);
    try {
      const [est, assump, prefs, results] = await Promise.all([
        getPurchaseEstimate(siteId),
        getPurchaseAssumptions(siteId),
        getPurchasePreferences(),
        getPurchaseResults(siteId),
      ]);
      setEstimate(est);
      setAssumptions({
        volume_kwh_an: assump.volume_kwh_an || est.volume_kwh_an || 0,
        horizon_months: assump.horizon_months || 24,
        energy_type: assump.energy_type || 'elec',
        profile_factor: assump.profile_factor || est.profile_factor || 1.0,
      });
      setPreferences({
        risk_tolerance: prefs.risk_tolerance || 'medium',
        budget_priority: prefs.budget_priority ?? 0.5,
        green_preference: prefs.green_preference || false,
      });
      setScenarios(results.scenarios || []);
      setAcceptedId(null);
    } catch {
      toast('Erreur lors du chargement des données du site', 'error');
    }
    setLoading(false);
  }, [toast]);

  useEffect(() => {
    if (selectedSiteId) loadSiteData(selectedSiteId);
  }, [selectedSiteId, loadSiteData]);

  // V73: Load renewals when tab becomes active — pass orgId + re-fetch on scope change
  const renewalsOrgRef = useRef(null);
  useEffect(() => {
    const orgId = scope.orgId;
    if (activeTab === 'echeances' && (renewals.length === 0 || renewalsOrgRef.current !== orgId)) {
      renewalsOrgRef.current = orgId;
      setRenewalsLoading(true);
      getPurchaseRenewals(orgId)
        .then((data) => {
          setRenewals(data.renewals || []);
        })
        .catch(() => toast('Erreur lors du chargement des echeances', 'error'))
        .finally(() => setRenewalsLoading(false));
    }
  }, [activeTab, renewals.length, scope.orgId, toast]);

  // Load history when tab + site selected
  useEffect(() => {
    if (activeTab === 'historique' && selectedSiteId) {
      setHistoryLoading(true);
      getPurchaseHistory(selectedSiteId)
        .then((data) => {
          setHistory(data.runs || []);
        })
        .catch(() => toast("Erreur lors du chargement de l'historique", 'error'))
        .finally(() => setHistoryLoading(false));
    }
  }, [activeTab, selectedSiteId, toast]);

  // V72: autosave — debounced save on assumption/preference change
  const autosave = useCallback(() => {
    if (!selectedSiteId) return;
    if (autosaveTimer.current) clearTimeout(autosaveTimer.current);
    autosaveTimer.current = setTimeout(async () => {
      try {
        await Promise.all([
          putPurchaseAssumptions(selectedSiteId, assumptions),
          putPurchasePreferences(preferences),
        ]);
      } catch {
        /* silent autosave — errors surfaced on compute */
      }
    }, 1500);
  }, [selectedSiteId, assumptions, preferences]);

  useEffect(() => {
    autosave();
    return () => { if (autosaveTimer.current) clearTimeout(autosaveTimer.current); };
  }, [autosave]);

  // V72: when toggling to estimation, sync volume from estimate
  useEffect(() => {
    if (useEstimation && estimate) {
      setAssumptions((prev) => ({ ...prev, volume_kwh_an: estimate.volume_kwh_an || prev.volume_kwh_an }));
    }
  }, [useEstimation, estimate]);

  const handleCompute = async () => {
    if (!selectedSiteId) return;
    setComputing(true);
    try {
      await putPurchaseAssumptions(selectedSiteId, assumptions);
      await putPurchasePreferences(preferences);
      const result = await computePurchaseScenarios(selectedSiteId, {
        report_pct: reportEnabled ? reportPct : 0,
      });
      setScenarios(result.scenarios || []);
      setAcceptedId(null);
    } catch {
      toast('Erreur lors du calcul des scenarios', 'error');
    }
    setComputing(false);
  };

  const handleAccept = async (resultId) => {
    try {
      await acceptPurchaseResult(resultId);
      setAcceptedId(resultId);
      setScenarios((prev) =>
        prev.map((s) => (s.id === resultId ? { ...s, reco_status: 'accepted' } : s))
      );
    } catch {
      toast("Erreur lors de l'acceptation du scenario", 'error');
    }
  };

  const handleComputePortfolio = async () => {
    setPortfolioLoading(true);
    try {
      const data = await computePortfolio(scope.orgId);
      setPortfolioData(data);
    } catch {
      toast('Erreur lors du calcul du portefeuille', 'error');
    }
    setPortfolioLoading(false);
  };

  const handleLoadPortfolio = async () => {
    setPortfolioLoading(true);
    try {
      const data = await getPortfolioResults(scope.orgId);
      setPortfolioData(data);
    } catch {
      toast('Erreur lors du chargement du portefeuille', 'error');
    }
    setPortfolioLoading(false);
  };

  return (
    <PurchaseErrorBoundary>
      <PageShell
        icon={ShoppingCart}
        title="Achats énergie"
        subtitle={
          <span className="flex items-center gap-2">
            Simuler &amp; arbitrer vos stratégies d'achat
            {dataConfidence && (
              <Tooltip text={dataConfidence.tooltipFR}>
                <span className="inline-flex items-center gap-1" data-testid="purchase-confidence">
                  <Badge status={dataConfidence.badgeStatus}>Confiance : {dataConfidence.label}</Badge>
                </span>
              </Tooltip>
            )}
          </span>
        }
      >
        {/* Tab bar */}
        <div className="flex border-b border-gray-200">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => handleTabChange(tab.key)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition ${
                activeTab === tab.key
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <tab.icon size={16} />
              {tab.label}
            </button>
          ))}
        </div>

        {/* ══ TAB: Simulation (V2 — V72 UX) ══ */}
        {activeTab === 'simulation' && (
          <>
            {/* Section 1: Site selection + Estimation + Confidence badges */}
            <div className="bg-white rounded-lg shadow p-6" data-section="site-estimation">
              <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                <Calculator size={18} /> Sélection du site & Estimation
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Site</label>
                  {isScopeLocked ? (
                    <div data-testid="scope-locked-site" className="w-full border border-blue-200 bg-blue-50 rounded-lg px-3 py-2 text-sm flex items-center gap-2">
                      <Lock size={14} className="text-blue-500" />
                      <span className="font-medium text-blue-900">
                        {scopedSites.find((s) => s.id === selectedSiteId)?.nom || `Site #${selectedSiteId}`}
                      </span>
                      <button
                        data-testid="cta-change-site"
                        onClick={() => {
                          // V73: Unlock scope lock — user can pick another site
                          setScopeOverride(true);
                          setSelectedSiteId(null);
                        }}
                        className="ml-auto text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
                      >
                        <RefreshCw size={10} /> Changer
                      </button>
                    </div>
                  ) : (
                    <select
                      data-testid="site-selector-open"
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                      value={selectedSiteId || ''}
                      onChange={(e) => setSelectedSiteId(e.target.value ? Number(e.target.value) : null)}
                    >
                      <option value="">Choisir un site...</option>
                      {scopedSites.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.nom} — {s.ville}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
                {estimate && (
                  <>
                    <div className="bg-blue-50 rounded-lg p-4">
                      <div className="text-xs text-blue-600 font-medium uppercase">
                        Volume estimé
                      </div>
                      <div className="text-2xl font-bold text-blue-900">
                        {Math.round(estimate.volume_kwh_an).toLocaleString()} kWh/an
                      </div>
                      <div className="text-xs text-blue-500 mt-1">
                        Source: {estimate.source} ({estimate.months_covered} mois)
                      </div>
                      {/* V72: confidence badges */}
                      <div className="flex gap-1.5 mt-2" data-testid="confidence-badges">
                        <span className={`inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full font-medium ${estimate.source === 'compteur' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                          <BadgeCheck size={10} /> {estimate.source === 'compteur' ? 'Relevé réel' : 'Estimé'}
                        </span>
                        <span className={`inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full font-medium ${(estimate.months_covered || 0) >= 12 ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'}`}>
                          {estimate.months_covered || 0} mois
                        </span>
                      </div>
                    </div>
                    <div className="bg-purple-50 rounded-lg p-4">
                      <div className="text-xs text-purple-600 font-medium uppercase">
                        Profil de charge
                      </div>
                      <div className="text-2xl font-bold text-purple-900">
                        {estimate.profile_factor?.toFixed(2)}
                      </div>
                      <div className="text-xs text-purple-500 mt-1">
                        {estimate.profile_factor > 1
                          ? 'Profil pointe'
                          : estimate.profile_factor < 1
                            ? 'Profil plat'
                            : 'Standard'}
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Section 2: Hypothèses + Volume toggle */}
            <div className="bg-white rounded-lg shadow p-6" data-section="hypotheses">
              <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                <Settings2 size={18} /> Hypothèses
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="block text-sm font-medium text-gray-700">
                      Volume (kWh/an)
                    </label>
                    {/* V72: volume toggle */}
                    <button
                      data-testid="volume-toggle"
                      onClick={() => setUseEstimation((v) => !v)}
                      className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-medium"
                    >
                      {useEstimation ? <ToggleRight size={14} /> : <ToggleLeft size={14} />}
                      {useEstimation ? 'Estimation' : 'Manuel'}
                    </button>
                  </div>
                  {useEstimation ? (
                    <div data-testid="volume-estimation" className="w-full border border-blue-200 bg-blue-50 rounded-lg px-3 py-2 text-sm text-blue-900 font-medium flex items-center gap-2">
                      <Zap size={14} className="text-blue-500" />
                      {Math.round(assumptions.volume_kwh_an).toLocaleString()} kWh/an
                      <Lock size={12} className="text-blue-300 ml-auto" />
                    </div>
                  ) : (
                    <input
                      data-testid="volume-manual"
                      type="number"
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                      value={assumptions.volume_kwh_an}
                      onChange={(e) =>
                        setAssumptions((prev) => ({ ...prev, volume_kwh_an: Number(e.target.value) }))
                      }
                    />
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Horizon (mois)
                  </label>
                  <select
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                    value={assumptions.horizon_months}
                    onChange={(e) =>
                      setAssumptions((prev) => ({
                        ...prev,
                        horizon_months: Number(e.target.value),
                      }))
                    }
                  >
                    <option value={12}>12 mois</option>
                    <option value={24}>24 mois</option>
                    <option value={36}>36 mois</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Énergie</label>
                  <div className="w-full border border-gray-200 bg-gray-50 rounded-lg px-3 py-2 text-sm flex items-center gap-2 text-gray-700">
                    <Zap size={14} className="text-blue-500" />
                    <span className="font-medium">Électricité</span>
                    <Lock size={12} className="text-gray-400 ml-auto" />
                  </div>
                  <p className="text-xs text-gray-400 mt-1 flex items-center gap-1">
                    <Info size={10} /> Post-ARENH — élec uniquement
                  </p>
                </div>
              </div>
            </div>

            {/* Section 3: Préférences + CTA unique "Comparer les scénarios" */}
            <div className="bg-white rounded-lg shadow p-6" data-section="preferences">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Préférences</h3>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Tolérance au risque
                  </label>
                  <div className="flex gap-2">
                    {['low', 'medium', 'high'].map((level) => (
                      <button
                        key={level}
                        onClick={() =>
                          setPreferences((prev) => ({ ...prev, risk_tolerance: level }))
                        }
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                          preferences.risk_tolerance === level
                            ? RISK_COLORS[level] + ' ring-2 ring-offset-1 ring-current'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                      >
                        {level === 'low' ? 'Faible' : level === 'medium' ? 'Moyen' : 'Élevé'}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Priorité budget: {Math.round(preferences.budget_priority * 100)}%
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={preferences.budget_priority}
                    onChange={(e) =>
                      setPreferences((prev) => ({
                        ...prev,
                        budget_priority: Number(e.target.value),
                      }))
                    }
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-gray-400">
                    <span>Sécurité</span>
                    <span>Économies</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="green"
                    checked={preferences.green_preference}
                    onChange={(e) =>
                      setPreferences((prev) => ({ ...prev, green_preference: e.target.checked }))
                    }
                    className="rounded"
                  />
                  <label htmlFor="green" className="text-sm text-gray-700 flex items-center gap-1">
                    <Leaf size={14} className="text-green-500" /> Offre verte
                  </label>
                </div>
                {/* V75: RéFlex report toggle + slider (Expert) */}
                <div data-testid="reflex-report-controls" className="bg-amber-50 rounded-lg p-3 border border-amber-200">
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-sm font-medium text-amber-800 flex items-center gap-1.5">
                      <Sun size={14} /> Décalage heures pleines → solaire
                      <span className="ml-1 px-1.5 py-0.5 text-[10px] font-bold bg-amber-200 text-amber-800 rounded">TARIF HEURES SOLAIRES</span>
                    </label>
                    <button
                      data-testid="report-toggle"
                      onClick={() => setReportEnabled((v) => !v)}
                      className="flex items-center gap-1 text-xs text-amber-700 hover:text-amber-900 font-medium"
                    >
                      {reportEnabled ? <ToggleRight size={14} /> : <ToggleLeft size={14} />}
                      {reportEnabled ? 'Avec report' : 'Sans report'}
                    </button>
                  </div>
                  {reportEnabled && isExpert && (
                    <div data-testid="report-slider" className="flex items-center gap-3">
                      <Sliders size={12} className="text-amber-600 shrink-0" />
                      <input
                        type="range"
                        min={0}
                        max={30}
                        value={Math.round(reportPct * 100)}
                        onChange={(e) => setReportPct(Number(e.target.value) / 100)}
                        className="flex-1 h-1.5 rounded-full accent-amber-500"
                      />
                      <span className="text-xs font-mono text-amber-700 w-10 text-right">{Math.round(reportPct * 100)}%</span>
                    </div>
                  )}
                  {reportEnabled && !isExpert && (
                    <p className="text-xs text-amber-600">Report fixé à 15%. Activez le mode Expert pour ajuster.</p>
                  )}
                </div>
                <div>
                  {/* V72: CTA unique — plus de double "Sauvegarder" */}
                  <Tooltip text={selectedSiteId && assumptions.volume_kwh_an === 0 ? 'Données de consommation requises pour la simulation' : ''}>
                    <button
                      data-testid="cta-comparer-scenarios"
                      onClick={handleCompute}
                      disabled={computing || !selectedSiteId || assumptions.volume_kwh_an === 0}
                      className="w-full bg-blue-600 text-white px-4 py-2.5 rounded-lg text-sm font-semibold hover:bg-blue-700 transition disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      {computing ? 'Calcul en cours...' : 'Comparer les scénarios'}
                    </button>
                  </Tooltip>
                </div>
              </div>
            </div>

            {/* Section 4: Scénarios 2026–2030 — Cockpit décisionnel */}
            {scenarios.length > 0 && (
              <div data-section="scenarios-cockpit">
                <h3 className="text-lg font-semibold text-gray-800 mb-2 flex items-center gap-2">
                  <Target size={18} /> Scénarios 2026–2030
                </h3>
                <p className="text-sm text-gray-500 mb-4">
                  {scenarios.length} stratégies comparées · Horizon {assumptions.horizon_months || 24} mois · Volume {Math.round(assumptions.volume_kwh_an).toLocaleString()} kWh/an
                </p>

                {/* KPI strip: Budget / Risque / Recommandation */}
                {(() => {
                  const reco = scenarios.find((s) => s.is_recommended);
                  const cheapest = [...scenarios].sort((a, b) => a.total_annual_eur - b.total_annual_eur)[0];
                  const mostExpensive = [...scenarios].sort((a, b) => b.total_annual_eur - a.total_annual_eur)[0];
                  const recoMeta = reco ? (STRATEGY_META[reco.strategy] || STRATEGY_META.fixe) : null;
                  return (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6" data-testid="scenario-kpi-strip">
                      <div className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500">
                        <div className="text-xs text-gray-500 uppercase font-medium">Budget annuel</div>
                        <div className="text-2xl font-bold text-gray-900 mt-1">
                          {cheapest ? `${Math.round(cheapest.total_annual_eur).toLocaleString()} — ${Math.round(mostExpensive.total_annual_eur).toLocaleString()}` : '—'} EUR
                        </div>
                        <div className="text-xs text-gray-400 mt-1">Fourchette des {scenarios.length} stratégies</div>
                      </div>
                      <div className="bg-white rounded-lg shadow p-4 border-l-4 border-yellow-500">
                        <div className="text-xs text-gray-500 uppercase font-medium">Risque moyen</div>
                        <div className="text-2xl font-bold text-gray-900 mt-1">
                          {reco ? `${reco.risk_score}/100` : '—'}
                        </div>
                        <div className="text-xs text-gray-400 mt-1">Score de la stratégie recommandée</div>
                      </div>
                      <div className="bg-white rounded-lg shadow p-4 border-l-4 border-green-500">
                        <div className="text-xs text-gray-500 uppercase font-medium">Recommandation</div>
                        <div className="text-2xl font-bold text-gray-900 mt-1 flex items-center gap-2">
                          {recoMeta ? recoMeta.label : 'Aucune'}
                          {reco?.savings_vs_current_pct > 0 && (
                            <span className="text-sm font-medium text-green-600">−{reco.savings_vs_current_pct}%</span>
                          )}
                        </div>
                        <div className="text-xs text-gray-400 mt-1">
                          {reco?.reasoning || 'Calculez les scénarios pour obtenir une recommandation'}
                        </div>
                      </div>
                    </div>
                  );
                })()}

                {/* Scenario cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {scenarios.map((s) => {
                    const meta = STRATEGY_META[s.strategy] || STRATEGY_META.fixe;
                    const Icon = meta.icon;
                    const risk = riskLevel(s.risk_score);
                    const isReco = s.is_recommended;
                    const isAccepted = s.reco_status === 'accepted' || acceptedId === s.id;
                    const whyText = STRATEGY_WHY[s.strategy] || '';
                    return (
                      <div
                        key={s.strategy}
                        data-testid={`scenario-card-${s.strategy}`}
                        className={`bg-white rounded-xl shadow-md p-6 border-2 transition ${isReco ? 'border-blue-500 ring-2 ring-blue-100' : 'border-gray-200'}`}
                      >
                        <div className="flex items-center justify-between mb-4">
                          <div className="flex items-center gap-2">
                            <div className={`p-2 rounded-lg ${meta.bgClass}`}>
                              <Icon size={20} className={meta.textClass} />
                            </div>
                            <div>
                              <h4 className="font-semibold text-gray-900 flex items-center gap-1.5">
                                {meta.label}
                                {s.strategy === 'reflex_solar' && isExpert && (
                                  <span data-testid="reflex-expert-tooltip" title="Tarification dynamique par blocs horaires avec optimisation solaire" className="cursor-help"><Info size={10} className="text-gray-400" /></span>
                                )}
                                {meta.dynamic && (
                                  <span data-testid="reflex-dynamic-badge" className="px-1.5 py-0.5 text-[10px] font-bold bg-amber-100 text-amber-700 rounded">DYNAMIQUE</span>
                                )}
                              </h4>
                              <p className="text-xs text-gray-500">{meta.desc}</p>
                            </div>
                          </div>
                          {isReco && (
                            <span className="px-2 py-1 text-xs font-bold bg-blue-100 text-blue-700 rounded-full">
                              Recommande
                            </span>
                          )}
                        </div>
                        <div className="mb-4">
                          <div className="text-3xl font-bold text-gray-900">
                            {s.price_eur_per_kwh?.toFixed(4)}{' '}
                            <span className="text-sm font-normal text-gray-500">EUR/kWh</span>
                          </div>
                          <div className="text-sm text-gray-600 mt-1">
                            {Math.round(s.total_annual_eur).toLocaleString()} EUR/an
                          </div>
                        </div>
                        {s.savings_vs_current_pct != null && (
                          <div
                            className={`text-sm font-medium mb-3 ${s.savings_vs_current_pct > 0 ? 'text-green-600' : 'text-red-600'}`}
                          >
                            {s.savings_vs_current_pct > 0 ? '-' : '+'}
                            {Math.abs(s.savings_vs_current_pct)}% vs prix actuel
                          </div>
                        )}
                        <div className="mb-3">
                          <div className="flex justify-between text-xs text-gray-500 mb-1">
                            <span>Risque</span>
                            <span className={RISK_COLORS[risk]}>{s.risk_score}/100</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full ${risk === 'low' ? 'bg-green-500' : risk === 'medium' ? 'bg-yellow-500' : 'bg-red-500'}`}
                              style={{ width: `${s.risk_score}%` }}
                            />
                          </div>
                        </div>
                        {s.p10_eur != null && s.p90_eur != null && (
                          <div className="text-xs text-gray-500 mb-3">
                            <AlertTriangle size={12} className="inline mr-1" />
                            Fourchette: {Math.round(s.p10_eur).toLocaleString()} —{' '}
                            {Math.round(s.p90_eur).toLocaleString()} EUR/an
                          </div>
                        )}

                        {/* V71: "Pourquoi ?" — explication de la stratégie */}
                        <details className="mb-3 group" data-testid={`scenario-why-${s.strategy}`}>
                          <summary className="flex items-center gap-1 text-xs text-blue-600 cursor-pointer hover:text-blue-800">
                            <HelpCircle size={12} /> Pourquoi cette stratégie ?
                          </summary>
                          <p className="mt-1.5 text-xs text-gray-600 bg-gray-50 rounded p-2 whitespace-pre-line">{whyText}</p>
                        </details>

                        {/* V82: Option Tarif Heures Solaires — composant structuré */}
                        {s.strategy === 'reflex_solar' && (
                          <div data-testid="reflex-solar-detail" className="mb-3 rounded-lg border border-amber-200 bg-amber-50/50 overflow-hidden">
                            {/* Header: titre + badge Sans pénalité */}
                            <div data-testid="option-ths-header" className="flex items-center justify-between px-3 py-2 bg-amber-100/60 border-b border-amber-200">
                              <h5 className="text-sm font-semibold text-amber-900 flex items-center gap-1.5">
                                <Sun size={14} className="text-amber-600" /> Option Tarif Heures Solaires
                              </h5>
                              <span data-testid="reflex-sans-penalite" className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
                                <CheckCircle2 size={12} /> Sans pénalité
                              </span>
                            </div>
                            {/* 2 bullets grand public */}
                            <div data-testid="option-ths-bullets" className="px-3 py-2 space-y-1">
                              <p className="text-xs text-gray-700 flex items-start gap-1.5">
                                <TrendingDown size={12} className="text-green-600 mt-0.5 shrink-0" />
                                Profitez d'un prix réduit pendant les heures de forte production solaire — été comme hiver.
                              </p>
                              <p className="text-xs text-gray-700 flex items-start gap-1.5">
                                <Shield size={12} className="text-blue-600 mt-0.5 shrink-0" />
                                Aucun engagement de décalage : si vous ne changez rien, votre facture reste identique.
                              </p>
                            </div>
                            {/* Badges: Budget / Risque / Effort */}
                            <div className="px-3 pb-2">
                              <div data-testid="reflex-badges" className="flex items-center gap-2 flex-wrap">
                                <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-green-50 text-green-700">
                                  <TrendingDown size={10} /> Budget {s.savings_vs_current_pct > 0 ? `-${s.savings_vs_current_pct}%` : '—'}
                                </span>
                                <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${RISK_COLORS[risk]}`}>
                                  <Shield size={10} /> Risque {s.risk_score}/100
                                </span>
                                {s.effort_score != null && (
                                  <span data-testid="reflex-effort-badge" className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${s.effort_score <= 30 ? 'bg-green-50 text-green-700' : s.effort_score <= 60 ? 'bg-yellow-50 text-yellow-700' : 'bg-red-50 text-red-700'}`}>
                                    <Settings2 size={10} /> Effort {s.effort_score}/100
                                  </span>
                                )}
                              </div>
                            </div>
                            {/* Créneaux + détails (collapsible) */}
                            <div className="px-3 pb-2 space-y-2">
                              {/* Créneaux Heures Solaires */}
                              <div data-testid="reflex-creneaux" className="text-xs bg-white/60 rounded p-2 border border-amber-100">
                                <p className="font-semibold text-amber-800 flex items-center gap-1 mb-1">
                                  <Clock size={12} /> Créneaux Heures Solaires
                                </p>
                                <div className="grid grid-cols-2 gap-2 text-gray-700">
                                  <div><span className="font-medium text-amber-700">Été :</span> 13h–16h (sem.) · 10h–17h (WE)</div>
                                  <div><span className="font-medium text-amber-700">Hiver :</span> 8h–10h & 17h–20h</div>
                                </div>
                              </div>
                              {/* Blocs horaires summary */}
                              {s.blocs && s.blocs.length > 0 && (
                                <details data-testid="reflex-blocs-detail" className="group">
                                  <summary className="flex items-center gap-1 text-xs text-amber-600 cursor-pointer hover:text-amber-800">
                                    <BarChart3 size={12} /> {s.blocs.length} blocs horaires
                                  </summary>
                                  <div className="mt-1.5 text-xs bg-white/60 rounded p-2 space-y-1 border border-amber-100">
                                    {s.blocs.map((b) => (
                                      <div key={b.bloc} className="flex justify-between">
                                        <span className="text-gray-700">{b.bloc.replace(/_/g, ' ')}</span>
                                        <span className="font-mono text-gray-600">{b.weight_pct}% — {b.price_eur_kwh.toFixed(4)} EUR/kWh</span>
                                      </div>
                                    ))}
                                  </div>
                                </details>
                              )}
                              {/* Report info */}
                              {s.report_pct != null && s.report_pct > 0 && (
                                <p data-testid="reflex-report-pct" className="text-xs text-amber-700">
                                  <RefreshCw size={10} className="inline mr-1" />
                                  Décalage heures pleines → solaire: {s.report_pct}%
                                </p>
                              )}
                              {/* Delta vs Prix Fixe standard */}
                              {(() => {
                                const fixeScenario = scenarios.find((sc) => sc.strategy === 'fixe');
                                if (!fixeScenario || !s.total_annual_eur) return null;
                                const deltaEur = Math.round(fixeScenario.total_annual_eur - s.total_annual_eur);
                                const deltaPct = fixeScenario.total_annual_eur > 0 ? round1((deltaEur / fixeScenario.total_annual_eur) * 100) : 0;
                                return (
                                  <div data-testid="reflex-delta-vs-fixe" className="text-xs bg-green-50 rounded p-2 flex items-center gap-1.5">
                                    <TrendingDown size={12} className="text-green-600" />
                                    <span className="text-green-700">
                                      {deltaEur > 0 ? `-${deltaEur.toLocaleString()} EUR/an` : `+${Math.abs(deltaEur).toLocaleString()} EUR/an`}
                                      {' '}({deltaPct > 0 ? '-' : '+'}{Math.abs(deltaPct)}%) vs Prix Fixe standard
                                    </span>
                                  </div>
                                );
                              })()}
                            </div>
                            {/* Cross-brique CTAs */}
                            <div data-testid="reflex-cross-ctas" className="flex items-center gap-2 flex-wrap px-3 pb-3 pt-1 border-t border-amber-200">
                              <button
                                data-testid="cta-conso-explorer-reflex"
                                onClick={() => {
                                  const now = new Date();
                                  const from = new Date(now);
                                  from.setDate(from.getDate() - 90);
                                  navigate(toConsoExplorer({
                                    site_id: selectedSiteId,
                                    date_from: from.toISOString().slice(0, 10),
                                    date_to: now.toISOString().slice(0, 10),
                                  }));
                                }}
                                className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 underline"
                              >
                                <BarChart3 size={12} /> Voir preuves conso
                              </button>
                              <button
                                data-testid="cta-bill-intel-reflex"
                                onClick={() => navigate(toBillIntel({ site_id: selectedSiteId, month: new Date().toISOString().slice(0, 7) }))}
                                className="flex items-center gap-1 text-xs text-purple-600 hover:text-purple-800 underline"
                              >
                                <FileSearch size={12} /> Contrôler facture
                              </button>
                              <button
                                data-testid="cta-perf-monitoring-reflex"
                                onClick={() => navigate(toMonitoring({ site_id: selectedSiteId }))}
                                className="flex items-center gap-1 text-xs text-emerald-600 hover:text-emerald-800 underline"
                              >
                                <Activity size={12} /> Voir performance
                              </button>
                              <button
                                data-testid="cta-create-action-reflex"
                                onClick={() => navigate(toActionNew({
                                  source: 'purchase',
                                  source_type: 'achat',
                                  site_id: selectedSiteId,
                                  title: `Tarif Heures Solaires — ${Math.round(s.total_annual_eur).toLocaleString()} EUR/an`,
                                  scenario_label: 'Tarif Heures Solaires',
                                  impact_eur: s.savings_vs_current_pct > 0 ? Math.round(s.total_annual_eur * s.savings_vs_current_pct / 100) : undefined,
                                }))}
                                className="flex items-center gap-1 text-xs text-green-600 hover:text-green-800 underline"
                              >
                                <Plus size={12} /> Créer action
                              </button>
                              <button
                                data-testid="cta-tester-tarif-solaire"
                                onClick={() => navigate(toPurchase({ tab: 'simulation', site_id: selectedSiteId }))}
                                className="flex items-center gap-1 text-xs text-amber-600 hover:text-amber-800 underline font-medium"
                              >
                                <Sun size={12} /> Tester un Tarif Heures Solaires
                              </button>
                              <button
                                data-testid="cta-assistant-ths"
                                onClick={() => navigate(toPurchaseAssistant({ site_id: selectedSiteId, step: 'offres', offer: 'HEURES_SOLAIRES' }))}
                                className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 underline"
                              >
                                <Rocket size={12} /> Tester dans l'Assistant
                              </button>
                            </div>
                          </div>
                        )}

                        {/* Accept CTA (reco only) */}
                        {isReco && !isAccepted && (
                          <button
                            onClick={() => handleAccept(s.id)}
                            className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 transition flex items-center justify-center gap-2"
                          >
                            <CheckCircle2 size={16} /> Accepter
                          </button>
                        )}
                        {isAccepted && (
                          <div className="w-full bg-green-50 text-green-700 py-2 rounded-lg text-sm font-semibold text-center flex items-center justify-center gap-2">
                            <CheckCircle2 size={16} /> Accepte
                          </div>
                        )}

                        {/* V71: "Créer action" CTA — visible after accepting */}
                        {isAccepted && (
                          <button
                            data-testid={`cta-create-action-${s.strategy}`}
                            onClick={() => navigate(toActionNew({
                              source: 'purchase',
                              source_type: 'achat',
                              site_id: selectedSiteId,
                              title: `Achat énergie — ${meta.label} (${Math.round(s.total_annual_eur).toLocaleString()} EUR/an)`,
                              scenario_label: meta.label,
                              impact_eur: s.savings_vs_current_pct > 0 ? Math.round(s.total_annual_eur * s.savings_vs_current_pct / 100) : undefined,
                            }))}
                            className="w-full mt-2 bg-white border border-green-300 text-green-700 py-2 rounded-lg text-sm font-medium hover:bg-green-50 transition flex items-center justify-center gap-2"
                          >
                            <Plus size={14} /> Créer action
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Reasoning + actions bar */}
                <div className="mt-4 flex flex-col sm:flex-row items-start sm:items-center gap-3">
                  {scenarios.find((s) => s.reasoning) && (
                    <div className="flex-1 bg-blue-50 rounded-lg p-4">
                      <p className="text-sm text-blue-800">
                        <strong>Analyse:</strong> {scenarios.find((s) => s.reasoning)?.reasoning}
                      </p>
                    </div>
                  )}
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      data-testid="cta-voir-actions-purchase"
                      onClick={() => navigate(toActionsList({ source_type: 'achat' }))}
                      className="flex items-center gap-1.5 bg-white border border-gray-200 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition"
                    >
                      <ExternalLink size={14} /> Voir les actions
                    </button>
                    <button
                      onClick={() => setShowNoteDecision(true)}
                      className="flex items-center gap-1.5 bg-white border border-blue-200 text-blue-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-50 transition"
                    >
                      <Printer size={14} /> Exporter Note de Decision (A4)
                    </button>
                  </div>
                </div>
              </div>
            )}
            {/* V71: empty state guidé quand aucun scénario */}
            {!loading && scenarios.length === 0 && selectedSiteId && (
              <div data-testid="empty-state-scenarios" className="bg-white rounded-lg shadow p-8 text-center">
                <Target size={40} className="mx-auto text-gray-300 mb-3" />
                <h4 className="text-lg font-semibold text-gray-700 mb-1">Aucun scénario calculé</h4>
                <p className="text-sm text-gray-500 mb-4">
                  Renseignez vos hypothèses ci-dessus puis cliquez sur «{'\u00a0'}Comparer les scénarios{'\u00a0'}» pour comparer Fixe / Indexé / Spot.
                </p>
                <button
                  data-testid="cta-assistant-achat"
                  onClick={() => navigate(toPurchaseAssistant())}
                  className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 font-medium"
                >
                  <Target size={14} /> Lancer l'Assistant Achat
                </button>
              </div>
            )}
            {loading && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <SkeletonCard />
                <SkeletonCard />
                <SkeletonCard />
              </div>
            )}
          </>
        )}

        {/* ══ TAB: Portefeuille (V1.1) ══ */}
        {activeTab === 'portefeuille' && (
          <div className="space-y-6">
            <div className="flex items-center gap-4 flex-wrap">
              <button
                onClick={handleComputePortfolio}
                disabled={portfolioLoading}
                className="bg-blue-600 text-white px-5 py-2.5 rounded-lg text-sm font-semibold hover:bg-blue-700 transition disabled:opacity-50"
              >
                {portfolioLoading ? 'Calcul...' : 'Calculer le portefeuille'}
              </button>
              <button
                onClick={handleLoadPortfolio}
                disabled={portfolioLoading}
                className="bg-gray-100 text-gray-700 px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-gray-200 transition disabled:opacity-50"
              >
                Charger résultats existants
              </button>
              <div className="ml-auto flex items-center gap-2">
                <span className="text-xs text-gray-400 uppercase font-medium">Datasets demo</span>
                <button
                  onClick={() => handleSeedWow('happy')}
                  disabled={!!seedingWow}
                  className="flex items-center gap-1.5 bg-emerald-50 text-emerald-700 border border-emerald-200 px-3 py-2 rounded-lg text-xs font-medium hover:bg-emerald-100 transition disabled:opacity-50"
                >
                  <Database size={13} />
                  {seedingWow === 'happy' ? 'Chargement...' : '15 sites (happy)'}
                </button>
                <button
                  onClick={() => handleSeedWow('dirty')}
                  disabled={!!seedingWow}
                  className="flex items-center gap-1.5 bg-orange-50 text-orange-700 border border-orange-200 px-3 py-2 rounded-lg text-xs font-medium hover:bg-orange-100 transition disabled:opacity-50"
                >
                  <AlertOctagon size={13} />
                  {seedingWow === 'dirty' ? 'Chargement...' : '15 sites (dirty)'}
                </button>
              </div>
            </div>
            {seedResult && (
              <div
                className={`rounded-lg p-3 text-sm ${seedResult.error ? 'bg-red-50 text-red-700' : 'bg-blue-50 text-blue-700'}`}
              >
                {seedResult.error
                  ? `Erreur: ${seedResult.error}`
                  : `Dataset "${seedResult.mode}" charge: ${seedResult.sites_created} sites, ${seedResult.scenarios_created} scenarios, ${seedResult.contracts_created} contrats (org: ${seedResult.org_nom})`}
              </div>
            )}
            {portfolioData?.portfolio && (
              <>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="bg-white rounded-lg shadow p-5">
                    <div className="text-xs text-gray-500 uppercase font-medium">
                      Sites analyses
                    </div>
                    <div className="text-3xl font-bold text-gray-900 mt-1">
                      {portfolioData.portfolio.sites_count}
                    </div>
                  </div>
                  <div className="bg-white rounded-lg shadow p-5">
                    <div className="text-xs text-gray-500 uppercase font-medium">
                      Cout annuel total
                    </div>
                    <div className="text-3xl font-bold text-blue-700 mt-1">
                      {Math.round(portfolioData.portfolio.total_annual_cost_eur).toLocaleString()}{' '}
                      EUR
                    </div>
                  </div>
                  <div className="bg-white rounded-lg shadow p-5">
                    <div className="text-xs text-gray-500 uppercase font-medium">
                      Risque moyen pondere
                    </div>
                    <div className="text-3xl font-bold text-orange-600 mt-1">
                      {portfolioData.portfolio.weighted_risk_score}/100
                    </div>
                  </div>
                  <div className="bg-white rounded-lg shadow p-5">
                    <div className="text-xs text-gray-500 uppercase font-medium">
                      Economies potentielles
                    </div>
                    <div
                      className={`text-3xl font-bold mt-1 ${portfolioData.portfolio.weighted_savings_pct > 0 ? 'text-green-600' : 'text-red-600'}`}
                    >
                      {portfolioData.portfolio.weighted_savings_pct > 0 ? '-' : ''}
                      {portfolioData.portfolio.weighted_savings_pct}%
                    </div>
                  </div>
                </div>
                {/* V75: RéFlex portfolio table with enhanced columns */}
                {portfolioData.sites?.length > 0 && (() => {
                  const enriched = portfolioData.sites.map((site) => {
                    const reco = site.scenarios?.find((s) => s.is_recommended);
                    const reflex = site.scenarios?.find((s) => s.strategy === 'reflex_solar');
                    const fixe = site.scenarios?.find((s) => s.strategy === 'fixe');
                    const baseline = fixe?.total_annual_eur || reco?.total_annual_eur || 0;
                    const reflexCost = reflex?.total_annual_eur || 0;
                    const gain = baseline > 0 ? round1((1 - reflexCost / baseline) * 100) : 0;
                    return { ...site, reco, reflex, baseline, reflexCost, gain };
                  });
                  const topGains = [...enriched].sort((a, b) => b.gain - a.gain).slice(0, 3);
                  const topRisk = [...enriched].filter((s) => s.reflex).sort((a, b) => (b.reflex?.risk_score || 0) - (a.reflex?.risk_score || 0)).slice(0, 3);
                  const easiest = [...enriched].filter((s) => s.reflex?.effort_score != null).sort((a, b) => (a.reflex.effort_score || 0) - (b.reflex.effort_score || 0)).slice(0, 3);
                  const campaignSites = enriched.filter((s) => s.gain > 0);
                  const campaignGainTotal = campaignSites.reduce((sum, s) => sum + Math.round(s.baseline * s.gain / 100), 0);
                  return (
                    <>
                      {/* V75: Top-lists */}
                      <div data-testid="reflex-top-lists" className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {[
                          { items: topGains, cardClass: 'bg-green-50 border-green-200', titleClass: 'text-green-800', icon: <Award size={14} />, title: 'Meilleurs gains Tarif Heures Solaires',
                            metric: (s) => <span className="font-medium text-green-700">-{s.gain}%</span>,
                            actionTitle: (s) => `Tarif Heures Solaires — gain ${s.gain}%` },
                          { items: topRisk, cardClass: 'bg-red-50 border-red-200', titleClass: 'text-red-800', icon: <Flame size={14} />, title: 'Risque pointe',
                            metric: (s) => <span className="font-medium text-red-700">{s.reflex?.risk_score}/100</span>,
                            actionTitle: (s) => `Risque pointe — ${s.reflex?.risk_score}/100` },
                          { items: easiest, cardClass: 'bg-blue-50 border-blue-200', titleClass: 'text-blue-800', icon: <ArrowUpDown size={14} />, title: 'Faciles à basculer',
                            metric: (s) => <span className="font-medium text-blue-700">Effort {s.reflex?.effort_score}/100</span>,
                            actionTitle: (s) => `Bascule Tarif Heures Solaires — effort ${s.reflex?.effort_score}/100` },
                        ].map(({ items, cardClass, titleClass, icon, title, metric, actionTitle }) => (
                          <div key={title} className={`${cardClass} rounded-lg p-4 border`}>
                            <h4 className={`text-xs font-bold ${titleClass} uppercase flex items-center gap-1.5 mb-2`}>
                              {icon} {title}
                            </h4>
                            {items.map((s) => (
                              <div key={s.site_id} className="flex items-center justify-between text-sm py-1">
                                <span className="text-gray-700">{s.site_nom || `Site ${s.site_id}`}</span>
                                <div className="flex items-center gap-2">
                                  {metric(s)}
                                  <button aria-label="Explorer conso" onClick={() => navigate(toConsoExplorer({ site_id: s.site_id, days: 90 }))} className="text-blue-500 hover:text-blue-700" title="Explorer"><BarChart3 size={12} /></button>
                                  <button aria-label="Diagnostic" onClick={() => navigate(toConsoDiag({ site_id: s.site_id }))} className="text-purple-500 hover:text-purple-700" title="Diagnostic"><Activity size={12} /></button>
                                  <button aria-label="Facture" onClick={() => navigate(toBillIntel({ site_id: s.site_id }))} className="text-indigo-500 hover:text-indigo-700" title="Facture"><FileSearch size={12} /></button>
                                  <button aria-label="Creer action" onClick={() => navigate(toActionNew({ source: 'purchase', source_type: 'achat', site_id: s.site_id, title: actionTitle(s), scenario_label: 'Tarif Heures Solaires' }))} className="text-green-500 hover:text-green-700" title="Action"><Plus size={12} /></button>
                                </div>
                              </div>
                            ))}
                          </div>
                        ))}
                      </div>
                      {/* V75: Enhanced portfolio table */}
                      <div data-testid="reflex-portfolio-table" className="bg-white rounded-lg shadow overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
                            <tr>
                              <th className="px-4 py-3 text-left">Site</th>
                              <th className="px-4 py-3 text-right">Budget baseline</th>
                              <th className="px-4 py-3 text-right">Tarif Heures Solaires</th>
                              <th className="px-4 py-3 text-right">Gain</th>
                              <th className="px-4 py-3 text-right">Risque</th>
                              <th className="px-4 py-3 text-right">Effort</th>
                              <th className="px-4 py-3 text-center">Confiance</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-100">
                            {enriched.map((site) => (
                              <tr key={site.site_id} className="hover:bg-gray-50">
                                <td className="px-4 py-3 font-medium text-gray-900">
                                  {site.site_nom || `Site ${site.site_id}`}
                                </td>
                                <td className="px-4 py-3 text-right text-gray-600">
                                  {Math.round(site.baseline).toLocaleString()} EUR
                                </td>
                                <td className="px-4 py-3 text-right font-medium text-amber-700">
                                  {site.reflex ? `${Math.round(site.reflexCost).toLocaleString()} EUR` : '—'}
                                </td>
                                <td className="px-4 py-3 text-right">
                                  {site.gain > 0 ? (
                                    <span className="text-green-600 font-medium">-{site.gain}%</span>
                                  ) : site.gain < 0 ? (
                                    <span className="text-red-600">+{Math.abs(site.gain)}%</span>
                                  ) : '—'}
                                </td>
                                <td className="px-4 py-3 text-right">
                                  {site.reflex ? `${site.reflex.risk_score}/100` : '—'}
                                </td>
                                <td className="px-4 py-3 text-right">
                                  {site.reflex?.effort_score != null ? (
                                    <span className={site.reflex.effort_score <= 30 ? 'text-green-600' : site.reflex.effort_score <= 60 ? 'text-yellow-600' : 'text-red-600'}>
                                      {site.reflex.effort_score}/100
                                    </span>
                                  ) : '—'}
                                </td>
                                <td className="px-4 py-3 text-center">
                                  {site.volume_kwh_an > 0 ? (
                                    <span className="inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded-full bg-green-50 text-green-700">
                                      <BadgeCheck size={10} /> Données
                                    </span>
                                  ) : (
                                    <span className="inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded-full bg-yellow-50 text-yellow-700">
                                      Estimé
                                    </span>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      {/* V75: Campaign CTA + Export */}
                      <div className="flex items-center justify-between mt-4">
                        {campaignSites.length > 0 && (
                          <button
                            data-testid="cta-campaign-reflex"
                            onClick={() => navigate(toActionNew({
                              source: 'purchase',
                              source_type: 'achat',
                              site_ids: campaignSites.map((s) => s.site_id),
                              title: `Campagne Tarif Heures Solaires — ${campaignSites.length} sites, gain ${campaignGainTotal.toLocaleString()} EUR`,
                              scenario_label: 'Tarif Heures Solaires',
                              impact_eur: campaignGainTotal,
                            }))}
                            className="flex items-center gap-2 bg-amber-500 text-white px-5 py-2.5 rounded-lg text-sm font-semibold hover:bg-amber-600 transition"
                          >
                            <Rocket size={16} /> Lancer campagne Tarif Heures Solaires ({campaignSites.length} sites)
                          </button>
                        )}
                        <button
                          onClick={() => setShowPackRFP(true)}
                          className="flex items-center gap-1.5 bg-white border border-blue-200 text-blue-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-50 transition"
                        >
                          <FileText size={14} /> Exporter Pack RFP (A4)
                        </button>
                      </div>
                    </>
                  );
                })()}
              </>
            )}
            {!portfolioData && !portfolioLoading && (
              <div className="text-center py-12 text-gray-400">
                Cliquez sur "Calculer le portefeuille" pour lancer l'analyse multi-site
              </div>
            )}
          </div>
        )}

        {/* ══ Export modals ══ */}
        {showNoteDecision && (
          <ExportNoteDecision
            data={{
              site_id: selectedSiteId,
              site_nom: scopedSites.find((s) => s.id === selectedSiteId)?.nom,
              volume_kwh_an: assumptions.volume_kwh_an,
              horizon_months: assumptions.horizon_months,
              scenarios,
            }}
            onClose={() => setShowNoteDecision(false)}
          />
        )}
        {showPackRFP && portfolioData && (
          <ExportPackRFP
            portfolio={portfolioData.portfolio}
            sites={portfolioData.sites}
            orgName={scope.org?.nom || 'Organisation'}
            onClose={() => setShowPackRFP(false)}
          />
        )}

        {/* ══ TAB: Echeances (V1.1) ══ */}
        {activeTab === 'echeances' && (
          <div className="space-y-4">
            {renewalsLoading ? (
              <div className="text-center py-12 text-gray-400">Chargement...</div>
            ) : renewals.length === 0 ? (
              <div className="text-center py-12 text-gray-400">
                Aucun contrat avec echeance a venir
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
                    <tr>
                      <th className="px-4 py-3 text-left">Urgence</th>
                      <th className="px-4 py-3 text-left">Site</th>
                      <th className="px-4 py-3 text-left">Fournisseur</th>
                      <th className="px-4 py-3 text-left">Energie</th>
                      <th className="px-4 py-3 text-left">Fin contrat</th>
                      <th className="px-4 py-3 text-left">Deadline preavis</th>
                      <th className="px-4 py-3 text-right">Jours restants</th>
                      <th className="px-4 py-3 text-center">Auto-renew</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {renewals.map((r) => (
                      <tr key={r.contract_id} className="hover:bg-gray-50">
                        <td className="px-4 py-3">
                          <span
                            className={`px-2 py-1 text-xs font-bold rounded ${URGENCY_STYLES[r.urgency] || URGENCY_STYLES.gray}`}
                          >
                            {r.urgency === 'red'
                              ? 'Urgent'
                              : r.urgency === 'orange'
                                ? 'Bientot'
                                : r.urgency === 'yellow'
                                  ? 'A planifier'
                                  : 'OK'}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-medium text-gray-900">
                          {r.site_nom || `Site ${r.site_id}`}
                        </td>
                        <td className="px-4 py-3">{r.supplier_name}</td>
                        <td className="px-4 py-3 capitalize">
                        {r.energy_type}
                        {r.energy_type === 'gaz' && (
                          <span className="ml-1 px-1.5 py-0.5 text-[10px] font-medium bg-gray-200 text-gray-500 rounded" title="Simulation achat non disponible pour le gaz dans cette version">hors-perimetre</span>
                        )}
                      </td>
                        <td className="px-4 py-3">
                          {new Date(r.end_date).toLocaleDateString('fr-FR')}
                        </td>
                        <td className="px-4 py-3">
                          {new Date(r.notice_deadline).toLocaleDateString('fr-FR')}
                        </td>
                        <td className="px-4 py-3 text-right font-semibold">
                          {r.days_until_expiry}j
                        </td>
                        <td className="px-4 py-3 text-center">
                          {r.auto_renew ? (
                            <span className="text-green-600 text-xs font-medium">Oui</span>
                          ) : (
                            <span className="text-gray-400 text-xs">Non</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* ══ TAB: Historique (V1.1) ══ */}
        {activeTab === 'historique' && (
          <div className="space-y-4">
            <div className="bg-white rounded-lg shadow p-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Site</label>
              <select
                className="w-full max-w-sm border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={selectedSiteId || ''}
                onChange={(e) => setSelectedSiteId(e.target.value ? Number(e.target.value) : null)}
              >
                <option value="">Choisir un site...</option>
                {scopedSites.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.nom} — {s.ville}
                  </option>
                ))}
              </select>
            </div>
            {historyLoading ? (
              <div className="text-center py-12 text-gray-400">Chargement...</div>
            ) : history.length === 0 ? (
              <div className="text-center py-12 text-gray-400">
                Aucun historique de calcul pour ce site
              </div>
            ) : (
              <div className="space-y-3">
                {history.map((run, idx) => (
                  <div
                    key={run.run_id || idx}
                    className={`bg-white rounded-lg shadow p-4 cursor-pointer transition border-2 ${selectedRun?.run_id === run.run_id ? 'border-blue-500' : 'border-transparent hover:border-gray-300'}`}
                    onClick={() => setSelectedRun(selectedRun?.run_id === run.run_id ? null : run)}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm font-semibold text-gray-900">
                          {run.computed_at
                            ? new Date(run.computed_at).toLocaleString('fr-FR')
                            : 'Date inconnue'}
                        </div>
                        <div className="text-xs text-gray-500 mt-0.5">
                          {run.run_id ? `Run: ${run.run_id.substring(0, 8)}...` : 'Run legacy'}
                          {run.inputs_hash && ` | Hash: ${run.inputs_hash.substring(0, 8)}...`}
                        </div>
                      </div>
                      <div className="text-right">
                        {run.summary?.recommended_strategy && (
                          <span className="px-2 py-1 text-xs font-semibold bg-blue-50 text-blue-700 rounded capitalize">
                            {run.summary.recommended_strategy}
                          </span>
                        )}
                        {run.summary?.recommended_total_eur && (
                          <div className="text-sm font-medium text-gray-700 mt-1">
                            {Math.round(run.summary.recommended_total_eur).toLocaleString()} EUR/an
                          </div>
                        )}
                      </div>
                    </div>
                    {selectedRun?.run_id === run.run_id && run.scenarios && (
                      <div className="mt-4 pt-4 border-t border-gray-100 grid grid-cols-3 gap-3">
                        {run.scenarios.map((s) => (
                          <div
                            key={s.id}
                            className={`p-3 rounded-lg border ${s.is_recommended ? 'border-blue-300 bg-blue-50' : 'border-gray-200'}`}
                          >
                            <div className="text-xs font-semibold uppercase text-gray-500 capitalize">
                              {s.strategy}
                            </div>
                            <div className="text-lg font-bold text-gray-900 mt-1">
                              {s.price_eur_per_kwh?.toFixed(4)} EUR/kWh
                            </div>
                            <div className="text-xs text-gray-500">
                              {Math.round(s.total_annual_eur).toLocaleString()} EUR/an | Risque:{' '}
                              {s.risk_score}
                            </div>
                            {s.is_recommended && (
                              <span className="inline-block mt-1 px-2 py-0.5 text-xs font-bold bg-blue-100 text-blue-700 rounded-full">
                                Recommande
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
        <PurchaseDebugDrawer
          assumptions={assumptions}
          preferences={preferences}
          scenarios={scenarios}
          portfolioData={portfolioData}
          selectedSiteId={selectedSiteId}
          seedResult={seedResult}
        />
      </PageShell>
    </PurchaseErrorBoundary>
  );
}
