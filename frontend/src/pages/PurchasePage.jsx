/**
 * PROMEOS — Achat Energie V1.1
 * Simulateur de scenarios d'achat: Fixe / Indexe / Spot
 * V1.1: + Portfolio roll-up, Echeances, Historique tabs.
 */
import { useState, useEffect, useCallback } from 'react';
import { useScope } from '../contexts/ScopeContext';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { PageShell } from '../ui';
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
} from '../services/api';
import {
  ShoppingCart, Calculator, Settings2, CheckCircle2,
  TrendingDown, Shield, Zap, Leaf, AlertTriangle,
  Building2, Clock, History,
} from 'lucide-react';

const STRATEGY_META = {
  fixe:   { label: 'Prix Fixe',  icon: Shield,       color: 'blue',   desc: 'Prix garanti sur toute la duree du contrat' },
  indexe: { label: 'Indexe',     icon: TrendingDown,  color: 'green',  desc: 'Prix suit un indice marche avec plafond' },
  spot:   { label: 'Spot',       icon: Zap,           color: 'orange', desc: 'Prix marche temps reel, economies max' },
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

function riskLevel(score) {
  if (score <= 30) return 'low';
  if (score <= 60) return 'medium';
  return 'high';
}

const TABS = [
  { key: 'simulation', label: 'Simulation', icon: Calculator },
  { key: 'portefeuille', label: 'Portefeuille', icon: Building2 },
  { key: 'echeances', label: 'Echeances', icon: Clock },
  { key: 'historique', label: 'Historique', icon: History },
];

export default function PurchasePage() {
  const { scopedSites } = useScope();
  const { isExpert } = useExpertMode();

  // Tab state
  const [activeTab, setActiveTab] = useState('simulation');

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
  const [savingAssumptions, setSavingAssumptions] = useState(false);
  const [savingPrefs, setSavingPrefs] = useState(false);
  const [acceptedId, setAcceptedId] = useState(null);

  // V1.1 state
  const [portfolioData, setPortfolioData] = useState(null);
  const [portfolioLoading, setPortfolioLoading] = useState(false);
  const [renewals, setRenewals] = useState([]);
  const [renewalsLoading, setRenewalsLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [selectedRun, setSelectedRun] = useState(null);

  // Auto-select first site
  useEffect(() => {
    if (scopedSites.length > 0 && !selectedSiteId) {
      setSelectedSiteId(scopedSites[0].id);
    }
  }, [scopedSites, selectedSiteId]);

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
      // Silent — mock mode may not have backend
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (selectedSiteId) loadSiteData(selectedSiteId);
  }, [selectedSiteId, loadSiteData]);

  // Load renewals when tab becomes active
  useEffect(() => {
    if (activeTab === 'echeances' && renewals.length === 0) {
      setRenewalsLoading(true);
      getPurchaseRenewals().then(data => {
        setRenewals(data.renewals || []);
      }).catch(() => {}).finally(() => setRenewalsLoading(false));
    }
  }, [activeTab, renewals.length]);

  // Load history when tab + site selected
  useEffect(() => {
    if (activeTab === 'historique' && selectedSiteId) {
      setHistoryLoading(true);
      getPurchaseHistory(selectedSiteId).then(data => {
        setHistory(data.runs || []);
      }).catch(() => {}).finally(() => setHistoryLoading(false));
    }
  }, [activeTab, selectedSiteId]);

  const handleSaveAssumptions = async () => {
    if (!selectedSiteId) return;
    setSavingAssumptions(true);
    try { await putPurchaseAssumptions(selectedSiteId, assumptions); } catch { /* silent */ }
    setSavingAssumptions(false);
  };

  const handleSavePreferences = async () => {
    setSavingPrefs(true);
    try { await putPurchasePreferences(preferences); } catch { /* silent */ }
    setSavingPrefs(false);
  };

  const handleCompute = async () => {
    if (!selectedSiteId) return;
    setComputing(true);
    try {
      await putPurchaseAssumptions(selectedSiteId, assumptions);
      await putPurchasePreferences(preferences);
      const result = await computePurchaseScenarios(selectedSiteId);
      setScenarios(result.scenarios || []);
      setAcceptedId(null);
    } catch { /* silent */ }
    setComputing(false);
  };

  const handleAccept = async (resultId) => {
    try {
      await acceptPurchaseResult(resultId);
      setAcceptedId(resultId);
      setScenarios(prev => prev.map(s =>
        s.id === resultId ? { ...s, reco_status: 'accepted' } : s
      ));
    } catch { /* silent */ }
  };

  const handleComputePortfolio = async () => {
    setPortfolioLoading(true);
    try {
      const data = await computePortfolio(1);
      setPortfolioData(data);
    } catch { /* silent */ }
    setPortfolioLoading(false);
  };

  const handleLoadPortfolio = async () => {
    setPortfolioLoading(true);
    try {
      const data = await getPortfolioResults(1);
      setPortfolioData(data);
    } catch { /* silent */ }
    setPortfolioLoading(false);
  };

  return (
    <PageShell
      icon={ShoppingCart}
      title="Achats energie"
      subtitle="Simuler & arbitrer vos strategies d'achat"
    >
      {/* Tab bar */}
      <div className="flex border-b border-gray-200">
        {TABS.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
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

      {/* ══ TAB: Simulation (V1) ══ */}
      {activeTab === 'simulation' && (
        <>
          {/* Section 1: Site selection + Estimation */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <Calculator size={18} /> Selection du site & Estimation
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Site</label>
                <select
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={selectedSiteId || ''}
                  onChange={(e) => setSelectedSiteId(Number(e.target.value))}
                >
                  <option value="">Choisir un site...</option>
                  {scopedSites.map(s => (
                    <option key={s.id} value={s.id}>{s.nom} — {s.ville}</option>
                  ))}
                </select>
              </div>
              {estimate && (
                <>
                  <div className="bg-blue-50 rounded-lg p-4">
                    <div className="text-xs text-blue-600 font-medium uppercase">Volume estime</div>
                    <div className="text-2xl font-bold text-blue-900">
                      {Math.round(estimate.volume_kwh_an).toLocaleString()} kWh/an
                    </div>
                    <div className="text-xs text-blue-500 mt-1">
                      Source: {estimate.source} ({estimate.months_covered} mois)
                    </div>
                  </div>
                  <div className="bg-purple-50 rounded-lg p-4">
                    <div className="text-xs text-purple-600 font-medium uppercase">Profil de charge</div>
                    <div className="text-2xl font-bold text-purple-900">
                      {estimate.profile_factor?.toFixed(2)}
                    </div>
                    <div className="text-xs text-purple-500 mt-1">
                      {estimate.profile_factor > 1 ? 'Profil pointe' : estimate.profile_factor < 1 ? 'Profil plat' : 'Standard'}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Section 2: Hypotheses */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <Settings2 size={18} /> Hypotheses
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Volume (kWh/an)</label>
                <input
                  type="number"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={assumptions.volume_kwh_an}
                  onChange={(e) => setAssumptions(prev => ({ ...prev, volume_kwh_an: Number(e.target.value) }))}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Horizon (mois)</label>
                <select
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={assumptions.horizon_months}
                  onChange={(e) => setAssumptions(prev => ({ ...prev, horizon_months: Number(e.target.value) }))}
                >
                  <option value={12}>12 mois</option>
                  <option value={24}>24 mois</option>
                  <option value={36}>36 mois</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Energie</label>
                <select
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={assumptions.energy_type}
                  onChange={(e) => setAssumptions(prev => ({ ...prev, energy_type: e.target.value }))}
                >
                  <option value="elec">Electricite</option>
                  <option value="gaz">Gaz</option>
                </select>
              </div>
              <div className="flex items-end">
                <button
                  onClick={handleSaveAssumptions}
                  disabled={savingAssumptions}
                  className="w-full bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200 transition disabled:opacity-50"
                >
                  {savingAssumptions ? 'Sauvegarde...' : 'Sauvegarder'}
                </button>
              </div>
            </div>
          </div>

          {/* Section 3: Preferences */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Preferences</h3>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Tolerance au risque</label>
                <div className="flex gap-2">
                  {['low', 'medium', 'high'].map(level => (
                    <button
                      key={level}
                      onClick={() => setPreferences(prev => ({ ...prev, risk_tolerance: level }))}
                      className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
                        preferences.risk_tolerance === level
                          ? RISK_COLORS[level] + ' ring-2 ring-offset-1 ring-current'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {level === 'low' ? 'Faible' : level === 'medium' ? 'Moyen' : 'Eleve'}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Priorite budget: {Math.round(preferences.budget_priority * 100)}%
                </label>
                <input
                  type="range" min="0" max="1" step="0.1"
                  value={preferences.budget_priority}
                  onChange={(e) => setPreferences(prev => ({ ...prev, budget_priority: Number(e.target.value) }))}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-400">
                  <span>Securite</span>
                  <span>Economies</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="green" checked={preferences.green_preference}
                  onChange={(e) => setPreferences(prev => ({ ...prev, green_preference: e.target.checked }))}
                  className="rounded" />
                <label htmlFor="green" className="text-sm text-gray-700 flex items-center gap-1">
                  <Leaf size={14} className="text-green-500" /> Offre verte
                </label>
              </div>
              <div className="flex gap-2">
                <button onClick={handleSavePreferences} disabled={savingPrefs}
                  className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200 transition disabled:opacity-50">
                  {savingPrefs ? '...' : 'Sauvegarder'}
                </button>
                <button onClick={handleCompute} disabled={computing || !selectedSiteId}
                  className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 transition disabled:opacity-50 flex items-center justify-center gap-2">
                  {computing ? 'Calcul...' : 'Calculer les scenarios'}
                </button>
              </div>
            </div>
          </div>

          {/* Section 4: Scenario Results */}
          {scenarios.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Resultats des scenarios</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {scenarios.map((s) => {
                  const meta = STRATEGY_META[s.strategy] || STRATEGY_META.fixe;
                  const Icon = meta.icon;
                  const risk = riskLevel(s.risk_score);
                  const isReco = s.is_recommended;
                  const isAccepted = s.reco_status === 'accepted' || acceptedId === s.id;
                  return (
                    <div key={s.strategy}
                      className={`bg-white rounded-xl shadow-md p-6 border-2 transition ${isReco ? 'border-blue-500 ring-2 ring-blue-100' : 'border-gray-200'}`}>
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                          <div className={`p-2 rounded-lg bg-${meta.color}-50`}>
                            <Icon size={20} className={`text-${meta.color}-600`} />
                          </div>
                          <div>
                            <h4 className="font-semibold text-gray-900">{meta.label}</h4>
                            <p className="text-xs text-gray-500">{meta.desc}</p>
                          </div>
                        </div>
                        {isReco && <span className="px-2 py-1 text-xs font-bold bg-blue-100 text-blue-700 rounded-full">Recommande</span>}
                      </div>
                      <div className="mb-4">
                        <div className="text-3xl font-bold text-gray-900">
                          {s.price_eur_per_kwh?.toFixed(4)} <span className="text-sm font-normal text-gray-500">EUR/kWh</span>
                        </div>
                        <div className="text-sm text-gray-600 mt-1">{Math.round(s.total_annual_eur).toLocaleString()} EUR/an</div>
                      </div>
                      {s.savings_vs_current_pct != null && (
                        <div className={`text-sm font-medium mb-3 ${s.savings_vs_current_pct > 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {s.savings_vs_current_pct > 0 ? '-' : '+'}{Math.abs(s.savings_vs_current_pct)}% vs prix actuel
                        </div>
                      )}
                      <div className="mb-3">
                        <div className="flex justify-between text-xs text-gray-500 mb-1">
                          <span>Risque</span>
                          <span className={RISK_COLORS[risk]}>{s.risk_score}/100</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div className={`h-2 rounded-full ${risk === 'low' ? 'bg-green-500' : risk === 'medium' ? 'bg-yellow-500' : 'bg-red-500'}`}
                            style={{ width: `${s.risk_score}%` }} />
                        </div>
                      </div>
                      {s.p10_eur != null && s.p90_eur != null && (
                        <div className="text-xs text-gray-500 mb-4">
                          <AlertTriangle size={12} className="inline mr-1" />
                          Fourchette: {Math.round(s.p10_eur).toLocaleString()} — {Math.round(s.p90_eur).toLocaleString()} EUR/an
                        </div>
                      )}
                      {isReco && !isAccepted && (
                        <button onClick={() => handleAccept(s.id)}
                          className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 transition flex items-center justify-center gap-2">
                          <CheckCircle2 size={16} /> Accepter
                        </button>
                      )}
                      {isAccepted && (
                        <div className="w-full bg-green-50 text-green-700 py-2 rounded-lg text-sm font-semibold text-center flex items-center justify-center gap-2">
                          <CheckCircle2 size={16} /> Accepte
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
              {scenarios.find(s => s.reasoning) && (
                <div className="mt-4 bg-blue-50 rounded-lg p-4">
                  <p className="text-sm text-blue-800">
                    <strong>Analyse:</strong> {scenarios.find(s => s.reasoning)?.reasoning}
                  </p>
                </div>
              )}
            </div>
          )}
          {loading && <div className="text-center py-12 text-gray-400">Chargement...</div>}
        </>
      )}

      {/* ══ TAB: Portefeuille (V1.1) ══ */}
      {activeTab === 'portefeuille' && (
        <div className="space-y-6">
          <div className="flex items-center gap-4">
            <button onClick={handleComputePortfolio} disabled={portfolioLoading}
              className="bg-blue-600 text-white px-5 py-2.5 rounded-lg text-sm font-semibold hover:bg-blue-700 transition disabled:opacity-50">
              {portfolioLoading ? 'Calcul...' : 'Calculer le portefeuille'}
            </button>
            <button onClick={handleLoadPortfolio} disabled={portfolioLoading}
              className="bg-gray-100 text-gray-700 px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-gray-200 transition disabled:opacity-50">
              Charger resultats existants
            </button>
          </div>
          {portfolioData?.portfolio && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-white rounded-lg shadow p-5">
                  <div className="text-xs text-gray-500 uppercase font-medium">Sites analyses</div>
                  <div className="text-3xl font-bold text-gray-900 mt-1">{portfolioData.portfolio.sites_count}</div>
                </div>
                <div className="bg-white rounded-lg shadow p-5">
                  <div className="text-xs text-gray-500 uppercase font-medium">Cout annuel total</div>
                  <div className="text-3xl font-bold text-blue-700 mt-1">
                    {Math.round(portfolioData.portfolio.total_annual_cost_eur).toLocaleString()} EUR
                  </div>
                </div>
                <div className="bg-white rounded-lg shadow p-5">
                  <div className="text-xs text-gray-500 uppercase font-medium">Risque moyen pondere</div>
                  <div className="text-3xl font-bold text-orange-600 mt-1">{portfolioData.portfolio.weighted_risk_score}/100</div>
                </div>
                <div className="bg-white rounded-lg shadow p-5">
                  <div className="text-xs text-gray-500 uppercase font-medium">Economies potentielles</div>
                  <div className={`text-3xl font-bold mt-1 ${portfolioData.portfolio.weighted_savings_pct > 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {portfolioData.portfolio.weighted_savings_pct > 0 ? '-' : ''}{portfolioData.portfolio.weighted_savings_pct}%
                  </div>
                </div>
              </div>
              {portfolioData.sites?.length > 0 && (
                <div className="bg-white rounded-lg shadow overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
                      <tr>
                        <th className="px-4 py-3 text-left">Site</th>
                        <th className="px-4 py-3 text-left">Strategie</th>
                        <th className="px-4 py-3 text-right">Cout annuel</th>
                        <th className="px-4 py-3 text-right">Risque</th>
                        <th className="px-4 py-3 text-right">Economies</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {portfolioData.sites.map(site => {
                        const reco = site.scenarios?.find(s => s.is_recommended);
                        return (
                          <tr key={site.site_id} className="hover:bg-gray-50">
                            <td className="px-4 py-3 font-medium text-gray-900">Site {site.site_id}</td>
                            <td className="px-4 py-3">{reco ? <span className="px-2 py-1 text-xs font-semibold bg-blue-50 text-blue-700 rounded capitalize">{reco.strategy}</span> : '—'}</td>
                            <td className="px-4 py-3 text-right">{reco ? `${Math.round(reco.total_annual_eur).toLocaleString()} EUR` : '—'}</td>
                            <td className="px-4 py-3 text-right">{reco ? `${reco.risk_score}/100` : '—'}</td>
                            <td className="px-4 py-3 text-right">{reco?.savings_vs_current_pct != null ? <span className={reco.savings_vs_current_pct > 0 ? 'text-green-600 font-medium' : 'text-red-600'}>{reco.savings_vs_current_pct > 0 ? '-' : '+'}{Math.abs(reco.savings_vs_current_pct)}%</span> : '—'}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
          {!portfolioData && !portfolioLoading && (
            <div className="text-center py-12 text-gray-400">Cliquez sur "Calculer le portefeuille" pour lancer l'analyse multi-site</div>
          )}
        </div>
      )}

      {/* ══ TAB: Echeances (V1.1) ══ */}
      {activeTab === 'echeances' && (
        <div className="space-y-4">
          {renewalsLoading ? (
            <div className="text-center py-12 text-gray-400">Chargement...</div>
          ) : renewals.length === 0 ? (
            <div className="text-center py-12 text-gray-400">Aucun contrat avec echeance a venir</div>
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
                  {renewals.map(r => (
                    <tr key={r.contract_id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 text-xs font-bold rounded ${URGENCY_STYLES[r.urgency] || URGENCY_STYLES.gray}`}>
                          {r.urgency === 'red' ? 'Urgent' : r.urgency === 'orange' ? 'Bientot' : r.urgency === 'yellow' ? 'A planifier' : 'OK'}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-medium text-gray-900">{r.site_nom || `Site ${r.site_id}`}</td>
                      <td className="px-4 py-3">{r.supplier_name}</td>
                      <td className="px-4 py-3 capitalize">{r.energy_type}</td>
                      <td className="px-4 py-3">{new Date(r.end_date).toLocaleDateString('fr-FR')}</td>
                      <td className="px-4 py-3">{new Date(r.notice_deadline).toLocaleDateString('fr-FR')}</td>
                      <td className="px-4 py-3 text-right font-semibold">{r.days_until_expiry}j</td>
                      <td className="px-4 py-3 text-center">{r.auto_renew ? <span className="text-green-600 text-xs font-medium">Oui</span> : <span className="text-gray-400 text-xs">Non</span>}</td>
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
            <select className="w-full max-w-sm border border-gray-300 rounded-lg px-3 py-2 text-sm"
              value={selectedSiteId || ''} onChange={(e) => setSelectedSiteId(Number(e.target.value))}>
              <option value="">Choisir un site...</option>
              {scopedSites.map(s => <option key={s.id} value={s.id}>{s.nom} — {s.ville}</option>)}
            </select>
          </div>
          {historyLoading ? (
            <div className="text-center py-12 text-gray-400">Chargement...</div>
          ) : history.length === 0 ? (
            <div className="text-center py-12 text-gray-400">Aucun historique de calcul pour ce site</div>
          ) : (
            <div className="space-y-3">
              {history.map((run, idx) => (
                <div key={run.run_id || idx}
                  className={`bg-white rounded-lg shadow p-4 cursor-pointer transition border-2 ${selectedRun?.run_id === run.run_id ? 'border-blue-500' : 'border-transparent hover:border-gray-300'}`}
                  onClick={() => setSelectedRun(selectedRun?.run_id === run.run_id ? null : run)}>
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-semibold text-gray-900">
                        {run.computed_at ? new Date(run.computed_at).toLocaleString('fr-FR') : 'Date inconnue'}
                      </div>
                      <div className="text-xs text-gray-500 mt-0.5">
                        {run.run_id ? `Run: ${run.run_id.substring(0, 8)}...` : 'Run legacy'}
                        {run.inputs_hash && ` | Hash: ${run.inputs_hash.substring(0, 8)}...`}
                      </div>
                    </div>
                    <div className="text-right">
                      {run.summary?.recommended_strategy && (
                        <span className="px-2 py-1 text-xs font-semibold bg-blue-50 text-blue-700 rounded capitalize">{run.summary.recommended_strategy}</span>
                      )}
                      {run.summary?.recommended_total_eur && (
                        <div className="text-sm font-medium text-gray-700 mt-1">{Math.round(run.summary.recommended_total_eur).toLocaleString()} EUR/an</div>
                      )}
                    </div>
                  </div>
                  {selectedRun?.run_id === run.run_id && run.scenarios && (
                    <div className="mt-4 pt-4 border-t border-gray-100 grid grid-cols-3 gap-3">
                      {run.scenarios.map(s => (
                        <div key={s.id} className={`p-3 rounded-lg border ${s.is_recommended ? 'border-blue-300 bg-blue-50' : 'border-gray-200'}`}>
                          <div className="text-xs font-semibold uppercase text-gray-500 capitalize">{s.strategy}</div>
                          <div className="text-lg font-bold text-gray-900 mt-1">{s.price_eur_per_kwh?.toFixed(4)} EUR/kWh</div>
                          <div className="text-xs text-gray-500">{Math.round(s.total_annual_eur).toLocaleString()} EUR/an | Risque: {s.risk_score}</div>
                          {s.is_recommended && <span className="inline-block mt-1 px-2 py-0.5 text-xs font-bold bg-blue-100 text-blue-700 rounded-full">Recommande</span>}
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
    </PageShell>
  );
}
