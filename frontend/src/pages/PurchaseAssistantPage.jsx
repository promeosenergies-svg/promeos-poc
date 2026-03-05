/**
 * PROMEOS — Brique 3 "Achat post-ARENH"
 * Purchase Assistant — 8-step wizard
 *
 * Steps: Portfolio → Consumption → Persona → Horizon → Offers → Results → Scoring → Decision
 * V81: + Deep-link support (step, offer, site_id URL params), offer highlight.
 */
import { useState, useMemo, useCallback, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  PageShell,
  Card,
  CardHeader,
  CardBody,
  Button,
  Badge,
  KpiCard,
  Progress,
  EmptyState,
  Modal,
} from '../ui';
import { useToast } from '../ui/ToastProvider';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { useScope } from '../contexts/ScopeContext';
import { getPurchaseAssistantData } from '../services/api';
import {
  ShoppingCart,
  ChevronLeft,
  ChevronRight,
  Check,
  MapPin,
  Zap,
  BarChart3,
  User,
  Clock,
  FileText,
  Shield,
  TrendingUp,
  Target,
  AlertTriangle,
  Info,
  Plus,
  Trash2,
  Download,
  Eye,
  Lock,
  ArrowRight,
  Flame,
  CheckCircle2,
  Sun,
  Minus,
  Star,
} from 'lucide-react';
import {
  EnergyType,
  OfferStructure,
  BREAKDOWN_LABELS,
  PERSONA_PROFILES,
  SCENARIO_PRESETS,
  DEFAULT_MARKET,
  BRIQUE3_VERSION,
  createDefaultWizardState,
  runEngine,
  clearEngineCache,
  scoreOffer,
  recommend,
  generateDecisionNote,
  generateRfpPack,
  generateComparisonCsv,
  appendDecision,
  getAuditLog,
  downloadAuditFile,
  DEMO_OFFERS,
  DEMO_ORGANIZATIONS,
  aggregateDemoSites,
  getAllDemoSites,
} from '../domain/purchase/index.js';
import { fmtNum, fmtPct } from '../utils/format';

// ── Constants ──────────────────────────────────────────────────────

const STEPS = [
  { key: 'portfolio', label: 'Portefeuille', icon: MapPin, desc: 'Sites & perimetre' },
  { key: 'consumption', label: 'Consommation', icon: BarChart3, desc: 'Volumes & profil' },
  { key: 'persona', label: 'Persona', icon: User, desc: 'Profil decideur' },
  { key: 'horizon', label: 'Horizon & Risque', icon: Clock, desc: 'Scenario marche' },
  { key: 'offers', label: 'Offres', icon: FileText, desc: 'Saisie fournisseurs' },
  { key: 'results', label: 'Resultats', icon: TrendingUp, desc: 'Corridor & TCO' },
  { key: 'scoring', label: 'Scoring', icon: Shield, desc: 'Transparence & risques' },
  { key: 'decision', label: 'Decision', icon: Target, desc: 'Recommandation & export' },
];

const STRUCTURE_LABELS = {
  FIXE: 'Prix Fixe',
  INDEXE: 'Indexe',
  SPOT: 'Spot',
  HYBRIDE: 'Hybride',
  HEURES_SOLAIRES: 'Heures Solaires',
};

const STRUCTURE_COLORS = {
  FIXE: 'bg-blue-100 text-blue-700',
  INDEXE: 'bg-green-100 text-green-700',
  SPOT: 'bg-orange-100 text-orange-700',
  HYBRIDE: 'bg-purple-100 text-purple-700',
  HEURES_SOLAIRES: 'bg-amber-100 text-amber-700',
};

const SCORE_COLORS = {
  GREEN: 'text-green-600 bg-green-50 border-green-200',
  ORANGE: 'text-amber-600 bg-amber-50 border-amber-200',
  RED: 'text-red-600 bg-red-50 border-red-200',
};

const CONFIDENCE_COLORS = {
  HIGH: 'bg-green-100 text-green-700',
  MEDIUM: 'bg-amber-100 text-amber-700',
  LOW: 'bg-red-100 text-red-700',
};

// ── Empty Offer Template ───────────────────────────────────────────

function createEmptyOffer(index) {
  return {
    id: `offer-${Date.now()}-${index}`,
    supplierName: '',
    structure: OfferStructure.FIXE,
    pricing: {
      fixedPriceEurPerMwh: 90,
      indexName: 'EPEX Spot FR',
      spreadEurPerMwh: 5,
      capEurPerMwh: null,
      floorEurPerMwh: null,
      fixedSharePct: 1,
      indexedSharePct: 0,
      spotSharePct: 0,
    },
    breakdown: [],
    contractTerms: {
      durationMonths: 24,
      noticePeriodDays: 90,
      earlyTerminationPenalty: 'MODERATE',
      indexationClause: 'CLEAR',
      slaLevel: 'BASIC',
      greenCertified: false,
      clauseFlags: [],
    },
    intermediation: {
      hasIntermediary: false,
      feeDisclosed: true,
      feeEurPerMwh: 0,
      passThroughPolicy: 'FULL',
    },
    dataTerms: {
      curvesAccess: false,
      dplus1: false,
      csvExport: false,
      apiAccess: false,
    },
  };
}

// ── Main Component ─────────────────────────────────────────────────

export default function PurchaseAssistantPage() {
  const { toast } = useToast();
  const { isExpert } = useExpertMode();
  const { scope } = useScope();
  const [searchParams] = useSearchParams();

  // V81: Deep-link params (step, offer, site_id)
  const deepLinkStep = searchParams.get('step');
  const deepLinkOffer = searchParams.get('offer');
  const _deepLinkSiteId = searchParams.get('site_id');

  // Wizard state
  const [step, setStep] = useState(0);
  const [isDemo, setIsDemo] = useState(true);
  const [wizard, setWizard] = useState(createDefaultWizardState);

  // Computed results
  const [engineOutput, setEngineOutput] = useState(null);
  const [recommendation, setRecommendation] = useState(null);
  const [scoredOffers, setScoredOffers] = useState([]);
  const [computing, setComputing] = useState(false);
  const [showAuditModal, setShowAuditModal] = useState(false);

  // API data for assistant
  const [apiAssistantData, setApiAssistantData] = useState(null);

  // Fetch assistant data from API on mount / org change
  useEffect(() => {
    let cancelled = false;
    getPurchaseAssistantData(scope?.orgId ?? null)
      .then((data) => {
        if (!cancelled) {
          setApiAssistantData(data);
          setIsDemo(data.is_demo);
        }
      })
      .catch(() => {
        // Fallback to local demo data on error
        if (!cancelled) setApiAssistantData(null);
      });
    return () => {
      cancelled = true;
    };
  }, [scope?.orgId]);

  // V81: Deep-link — jump to step + highlight offer on mount
  useEffect(() => {
    if (!deepLinkStep) return;
    const stepIndex = STEPS.findIndex((s) => s.key === deepLinkStep);
    if (stepIndex >= 0) setStep(stepIndex);
  }, [deepLinkStep]);

  // Demo sites — prefer API data, fall back to local demo
  const demoSites = useMemo(() => {
    if (apiAssistantData?.sites?.length) {
      return apiAssistantData.sites.map((s) => ({
        id: s.id,
        name: s.name,
        city: s.city,
        usage: s.usage,
        surfaceM2: s.surface_m2,
        energyType: s.energy_type === 'elec' ? EnergyType.ELEC : EnergyType.GAZ,
        consumption: {
          annualKwh: s.annual_kwh,
          granularity: 'monthly',
          profileFactor: 1,
          source: s.source,
        },
        organizationName: apiAssistantData.is_demo ? 'Demo' : `Org #${apiAssistantData.org_id}`,
        entityName: '',
      }));
    }
    return getAllDemoSites();
  }, [apiAssistantData]);

  // Selected sites data
  const selectedSitesData = useMemo(() => {
    if (isDemo) {
      return aggregateDemoSites(wizard.selectedSiteIds);
    }
    return {
      annualKwh: wizard.totalAnnualKwh,
      energyType: wizard.energyType,
      consumption: null,
      billing: null,
      anomalies: [],
    };
  }, [isDemo, wizard.selectedSiteIds, wizard.totalAnnualKwh, wizard.energyType]);

  // Current offers
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const offers = useMemo(
    () => (wizard.offers.length > 0 ? wizard.offers : isDemo ? DEMO_OFFERS : []),
    [wizard.offers, isDemo]
  );

  // ── Navigation ───────────────────────────────────────────────────

  const canAdvance = useMemo(() => {
    switch (step) {
      case 0:
        return wizard.selectedSiteIds.length > 0 || !isDemo;
      case 1:
        return selectedSitesData.annualKwh > 0;
      case 2:
        return !!wizard.persona;
      case 3:
        return wizard.horizonMonths > 0;
      case 4:
        return offers.length > 0;
      default:
        return true;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, wizard, isDemo, selectedSitesData, offers]);

  // ── Computation (must be declared before goNext which references it) ──

  const handleCompute = useCallback(() => {
    setComputing(true);
    try {
      clearEngineCache();
      const annualKwh = selectedSitesData.annualKwh || wizard.totalAnnualKwh || 1000000;
      const params = {
        offers,
        annualKwh,
        energyType: selectedSitesData.energyType || wizard.energyType,
        horizonMonths: wizard.horizonMonths,
        scenarioPreset: wizard.scenarioPreset,
        mcIterations: wizard.mcIterations,
        mcSeed: wizard.mcSeed,
        budgetEur: wizard.budgetEur,
      };

      const output = runEngine(params);
      setEngineOutput(output);

      // Score each offer
      const scored = output.results
        .map((result) => {
          const offer = offers.find((o) => o.id === result.offerId);
          if (!offer) return null;
          const scores = scoreOffer({
            offerResult: result,
            offer,
            budgetEur: wizard.budgetEur,
            anomalies: selectedSitesData.anomalies || [],
            consumption: selectedSitesData.consumption || {
              source: isDemo ? 'DEMO' : 'USER',
              granularity: 'monthly',
            },
            billing: selectedSitesData.billing,
          });
          return { ...result, offer, scores };
        })
        .filter(Boolean);
      setScoredOffers(scored);

      // Recommendation
      const rec = recommend({
        offerResults: output.results,
        offers,
        persona: wizard.persona,
        budgetEur: wizard.budgetEur,
        consumption: selectedSitesData.consumption || {
          source: isDemo ? 'DEMO' : 'USER',
          granularity: 'monthly',
        },
        billing: selectedSitesData.billing,
        anomalies: selectedSitesData.anomalies || [],
      });
      setRecommendation(rec);

      // Audit
      appendDecision({
        inputs: { siteIds: wizard.selectedSiteIds, annualKwh, persona: wizard.persona, isDemo },
        params,
        offerResults: output.results,
        scores: scored.reduce((acc, s) => ({ ...acc, [s.offerId]: s.scores }), {}),
        recommendation: rec,
        action: 'COMPUTE',
      });
    } catch (err) {
      toast('Erreur lors du calcul: ' + (err.message || 'erreur inconnue'), 'error');
    }
    setComputing(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [offers, wizard, selectedSitesData, isDemo, toast]);

  const goNext = useCallback(() => {
    if (step < STEPS.length - 1 && canAdvance) {
      // Auto-compute when reaching results step
      if (step === 4) {
        handleCompute();
      }
      setStep((s) => s + 1);
    }
  }, [step, canAdvance, handleCompute]);

  const goBack = useCallback(() => {
    if (step > 0) setStep((s) => s - 1);
  }, [step]);

  // ── Render Step Content ──────────────────────────────────────────

  const renderStep = () => {
    switch (step) {
      case 0:
        return (
          <StepPortfolio
            wizard={wizard}
            setWizard={setWizard}
            isDemo={isDemo}
            setIsDemo={setIsDemo}
            demoSites={demoSites}
          />
        );
      case 1:
        return (
          <StepConsumption
            wizard={wizard}
            setWizard={setWizard}
            sitesData={selectedSitesData}
            isDemo={isDemo}
          />
        );
      case 2:
        return <StepPersona wizard={wizard} setWizard={setWizard} />;
      case 3:
        return <StepHorizon wizard={wizard} setWizard={setWizard} isExpert={isExpert} />;
      case 4:
        return (
          <StepOffers
            wizard={wizard}
            setWizard={setWizard}
            isDemo={isDemo}
            highlightOffer={deepLinkOffer}
          />
        );
      case 5:
        return (
          <StepResults
            engineOutput={engineOutput}
            scoredOffers={scoredOffers}
            recommendation={recommendation}
            computing={computing}
            onRecompute={handleCompute}
          />
        );
      case 6:
        return <StepScoring scoredOffers={scoredOffers} recommendation={recommendation} />;
      case 7:
        return (
          <StepDecision
            recommendation={recommendation}
            scoredOffers={scoredOffers}
            engineOutput={engineOutput}
            offers={offers}
            wizard={wizard}
            selectedSitesData={selectedSitesData}
            isDemo={isDemo}
            onShowAudit={() => setShowAuditModal(true)}
            toast={toast}
          />
        );
      default:
        return null;
    }
  };

  return (
    <PageShell
      icon={ShoppingCart}
      title="Assistant Achat Energie"
      subtitle={`Brique 3 — Post-ARENH v${BRIQUE3_VERSION}`}
    >
      {/* Step indicator */}
      <div className="flex items-center gap-1 overflow-x-auto pb-2">
        {STEPS.map((s, i) => {
          const Icon = s.icon;
          const isActive = i === step;
          const isDone = i < step;
          return (
            <button
              key={s.key}
              onClick={() => i <= step && setStep(i)}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition
                ${isActive ? 'bg-blue-600 text-white shadow-sm' : isDone ? 'bg-blue-50 text-blue-700 hover:bg-blue-100' : 'bg-gray-50 text-gray-400 cursor-default'}`}
            >
              {isDone ? <Check size={14} /> : <Icon size={14} />}
              <span className="hidden sm:inline">{s.label}</span>
              <span className="sm:hidden">{i + 1}</span>
            </button>
          );
        })}
      </div>

      {/* Step content */}
      <div className="min-h-[400px]">{renderStep()}</div>

      {/* Navigation */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-200">
        <button
          onClick={goBack}
          disabled={step === 0}
          className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 hover:text-gray-900 disabled:opacity-30 disabled:cursor-default transition"
        >
          <ChevronLeft size={16} /> Precedent
        </button>
        <div className="text-xs text-gray-400">
          Etape {step + 1} / {STEPS.length}
          {isDemo && (
            <span className="ml-2 px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full font-medium">
              MODE DEMO
            </span>
          )}
        </div>
        {step < STEPS.length - 1 ? (
          <button
            onClick={goNext}
            disabled={!canAdvance}
            className="flex items-center gap-2 px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-40 disabled:cursor-default transition"
          >
            Suivant <ChevronRight size={16} />
          </button>
        ) : (
          <div className="text-sm text-green-600 font-medium flex items-center gap-1">
            <CheckCircle2 size={16} /> Analyse terminée
          </div>
        )}
      </div>

      {/* Audit Modal */}
      {showAuditModal && (
        <Modal title="Piste d'audit" onClose={() => setShowAuditModal(false)}>
          <AuditTrailView />
        </Modal>
      )}
    </PageShell>
  );
}

// ═══════════════════════════════════════════════════════════════════
// STEP 1: Portfolio
// ═══════════════════════════════════════════════════════════════════

function StepPortfolio({ wizard, setWizard, isDemo, setIsDemo, demoSites }) {
  const toggleSite = (id) => {
    setWizard((prev) => ({
      ...prev,
      selectedSiteIds: prev.selectedSiteIds.includes(id)
        ? prev.selectedSiteIds.filter((x) => x !== id)
        : [...prev.selectedSiteIds, id],
    }));
  };

  const selectAll = () => {
    setWizard((prev) => ({ ...prev, selectedSiteIds: demoSites.map((s) => s.id) }));
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-800">Selection du perimetre</h3>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={isDemo}
              onChange={(e) => setIsDemo(e.target.checked)}
              className="rounded border-gray-300"
            />
            Mode demo
          </label>
          {demoSites.length > 0 && (
            <button onClick={selectAll} className="text-xs text-blue-600 hover:underline">
              Tout selectionner
            </button>
          )}
        </div>
      </div>

      {isDemo ? (
        <div className="space-y-3">
          {DEMO_ORGANIZATIONS.map((org) => (
            <div key={org.id} className="bg-white rounded-lg border border-gray-200 p-4">
              <h4 className="font-medium text-gray-900 mb-3">{org.name}</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {org.entities
                  .flatMap((e) => e.sites)
                  .map((site) => {
                    const selected = wizard.selectedSiteIds.includes(site.id);
                    return (
                      <button
                        key={site.id}
                        onClick={() => toggleSite(site.id)}
                        className={`text-left p-3 rounded-lg border-2 transition
                        ${selected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-medium text-sm text-gray-900">{site.name}</span>
                          <Badge variant={site.energyType === 'ELEC' ? 'blue' : 'orange'}>
                            {site.energyType === 'ELEC' ? <Zap size={12} /> : <Flame size={12} />}
                            {site.energyType}
                          </Badge>
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          {site.city} — {site.usage}
                        </div>
                        <div className="text-xs text-gray-400 mt-1">
                          {fmtNum((site.consumption?.annualKwh || 0) / 1000, 0)} MWh/an —{' '}
                          {site.surfaceM2.toLocaleString('fr-FR')} m2
                        </div>
                      </button>
                    );
                  })}
              </div>
            </div>
          ))}
        </div>
      ) : demoSites.length > 0 ? (
        <div className="space-y-3">
          <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-2 text-sm text-green-700">
            {demoSites.length} site(s) charge(s) depuis votre patrimoine.
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {demoSites.map((site) => {
              const selected = wizard.selectedSiteIds.includes(site.id);
              return (
                <button
                  key={site.id}
                  onClick={() => toggleSite(site.id)}
                  className={`text-left p-3 rounded-lg border-2 transition
                  ${selected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-sm text-gray-900">{site.name}</span>
                    <Badge variant={site.energyType === 'ELEC' ? 'blue' : 'orange'}>
                      {site.energyType === 'ELEC' ? <Zap size={12} /> : <Flame size={12} />}
                      {site.energyType}
                    </Badge>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {site.city} — {site.usage}
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    {fmtNum((site.consumption?.annualKwh || 0) / 1000, 0)} MWh/an —{' '}
                    {(site.surfaceM2 || 0).toLocaleString('fr-FR')} m2
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      ) : (
        <Card>
          <CardBody>
            <p className="text-sm text-gray-500">
              Connectez-vous a votre patrimoine (Brique 1) pour charger les sites reels. En
              attendant, activez le mode demo pour tester l'assistant.
            </p>
          </CardBody>
        </Card>
      )}

      {wizard.selectedSiteIds.length > 0 && (
        <div className="bg-blue-50 rounded-lg p-3 text-sm text-blue-700">
          <strong>{wizard.selectedSiteIds.length}</strong> site(s) selectionne(s)
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// STEP 2: Consumption
// ═══════════════════════════════════════════════════════════════════

function StepConsumption({ wizard, setWizard, sitesData, isDemo }) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-800">Consommation & Profil</h3>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KpiCard
          label="Volume annuel"
          value={`${fmtNum((sitesData.annualKwh || 0) / 1000, 0)} MWh`}
          sublabel={isDemo ? 'Source: demo' : 'Source: patrimoine'}
          icon={<BarChart3 size={18} />}
        />
        <KpiCard
          label="Type d'energie"
          value={sitesData.energyType || wizard.energyType}
          sublabel={sitesData.energyType === 'GAZ' ? 'Gaz naturel' : 'Electricite'}
          icon={sitesData.energyType === 'GAZ' ? <Flame size={18} /> : <Zap size={18} />}
        />
        <KpiCard
          label="Factures disponibles"
          value={sitesData.billing?.invoiceCount || 0}
          sublabel={`${sitesData.anomalies?.length || 0} anomalie(s) B2`}
          icon={<FileText size={18} />}
        />
      </div>

      {!isDemo && (
        <Card>
          <CardBody>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Volume annuel (kWh)
                </label>
                <input
                  type="number"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={wizard.totalAnnualKwh}
                  onChange={(e) =>
                    setWizard((prev) => ({ ...prev, totalAnnualKwh: Number(e.target.value) }))
                  }
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Type d'energie
                </label>
                <select
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={wizard.energyType}
                  onChange={(e) => setWizard((prev) => ({ ...prev, energyType: e.target.value }))}
                >
                  <option value={EnergyType.ELEC}>Electricite</option>
                  <option value={EnergyType.GAZ}>Gaz</option>
                </select>
              </div>
            </div>
          </CardBody>
        </Card>
      )}

      {isDemo && sitesData.annualKwh > 0 && (
        <Card>
          <CardHeader>Profil de consommation</CardHeader>
          <CardBody>
            <div className="flex items-end gap-1 h-24">
              {(sitesData.consumption?.seasonality || []).map((coeff, i) => (
                <div key={i} className="flex-1 flex flex-col items-center gap-1">
                  <div
                    className="w-full bg-blue-200 rounded-t"
                    style={{ height: `${coeff * 60}px` }}
                  />
                  <span className="text-[10px] text-gray-400">
                    {['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'][i]}
                  </span>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-400 mt-2">
              Saisonnalite mensuelle (coefficient normalisé)
            </p>
          </CardBody>
        </Card>
      )}

      {sitesData.anomalies?.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
          <div className="flex items-center gap-2 text-sm font-medium text-amber-700 mb-2">
            <AlertTriangle size={16} /> {sitesData.anomalies.length} anomalie(s) de facturation
            détectée(s)
          </div>
          <ul className="space-y-1">
            {sitesData.anomalies.slice(0, 3).map((a, i) => (
              <li key={i} className="text-xs text-amber-600">
                {a.message}{' '}
                {a.estimatedLossEur > 0 && `(~${a.estimatedLossEur.toLocaleString('fr-FR')} EUR)`}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// STEP 3: Persona
// ═══════════════════════════════════════════════════════════════════

function StepPersona({ wizard, setWizard }) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-800">Profil decideur</h3>
      <p className="text-sm text-gray-500">
        Choisissez le persona qui correspond au destinataire de l'analyse. Les poids de scoring
        seront adaptes.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Object.entries(PERSONA_PROFILES).map(([key, profile]) => {
          const selected = wizard.persona === key;
          return (
            <button
              key={key}
              onClick={() => setWizard((prev) => ({ ...prev, persona: key }))}
              className={`text-left p-4 rounded-lg border-2 transition
                ${selected ? 'border-blue-500 bg-blue-50 shadow-sm' : 'border-gray-200 hover:border-gray-300'}`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-gray-900">{profile.label}</span>
                {selected && <Check size={18} className="text-blue-600" />}
              </div>
              <p className="text-xs text-gray-500 mb-3">{profile.description}</p>
              <div className="grid grid-cols-4 gap-2 text-[10px]">
                {Object.entries(profile.weights).map(([axis, w]) => (
                  <div key={axis} className="text-center">
                    <div className="font-medium text-gray-700">{Math.round(w * 100)}%</div>
                    <div className="text-gray-400">
                      {axis === 'budgetRisk'
                        ? 'Budget'
                        : axis === 'transparency'
                          ? 'Transp.'
                          : axis === 'contractRisk'
                            ? 'Contrat'
                            : 'Data'}
                    </div>
                  </div>
                ))}
              </div>
            </button>
          );
        })}
      </div>

      <Card>
        <CardBody>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Budget plafond annuel (EUR){' '}
            <span className="text-gray-400 font-normal">— optionnel</span>
          </label>
          <input
            type="number"
            placeholder="Ex: 500000"
            className="w-full max-w-xs border border-gray-300 rounded-lg px-3 py-2 text-sm"
            value={wizard.budgetEur || ''}
            onChange={(e) =>
              setWizard((prev) => ({
                ...prev,
                budgetEur: e.target.value ? Number(e.target.value) : null,
              }))
            }
          />
          <p className="text-xs text-gray-400 mt-1">
            Si renseigne, le moteur calculera la probabilite de depassement.
          </p>
        </CardBody>
      </Card>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// STEP 4: Horizon & Risk
// ═══════════════════════════════════════════════════════════════════

function StepHorizon({ wizard, setWizard, isExpert }) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-800">Horizon & Parametres de risque</h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>Horizon contractuel</CardHeader>
          <CardBody>
            <div className="flex gap-3">
              {[12, 24, 36].map((m) => (
                <button
                  key={m}
                  onClick={() => setWizard((prev) => ({ ...prev, horizonMonths: m }))}
                  className={`flex-1 py-3 rounded-lg text-sm font-medium transition border-2
                    ${wizard.horizonMonths === m ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}
                >
                  {m} mois
                </button>
              ))}
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>Scenario de marche</CardHeader>
          <CardBody>
            <div className="space-y-2">
              {Object.entries(SCENARIO_PRESETS).map(([key, preset]) => (
                <button
                  key={key}
                  onClick={() => setWizard((prev) => ({ ...prev, scenarioPreset: key }))}
                  className={`w-full text-left p-3 rounded-lg border-2 transition
                    ${wizard.scenarioPreset === key ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-sm text-gray-900">{preset.label}</span>
                    {wizard.scenarioPreset === key && <Check size={16} className="text-blue-600" />}
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">{preset.description}</p>
                </button>
              ))}
            </div>
          </CardBody>
        </Card>
      </div>

      {isExpert && (
        <Card>
          <CardHeader>Parametres avances (Expert)</CardHeader>
          <CardBody>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Iterations MC (max 200)
                </label>
                <input
                  type="number"
                  min={10}
                  max={200}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={wizard.mcIterations}
                  onChange={(e) =>
                    setWizard((prev) => ({
                      ...prev,
                      mcIterations: Math.min(200, Math.max(10, Number(e.target.value))),
                    }))
                  }
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Seed aleatoire
                </label>
                <input
                  type="number"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={wizard.mcSeed}
                  onChange={(e) =>
                    setWizard((prev) => ({ ...prev, mcSeed: Number(e.target.value) }))
                  }
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Prix base spot (EUR/MWh)
                </label>
                <input
                  type="number"
                  disabled
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-gray-50"
                  value={DEFAULT_MARKET.baseSpotEurPerMwh}
                />
                <p className="text-[10px] text-gray-400 mt-0.5">
                  Non modifiable en v{BRIQUE3_VERSION}
                </p>
              </div>
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// STEP 5: Offers
// ═══════════════════════════════════════════════════════════════════

function StepOffers({ wizard, setWizard, isDemo, highlightOffer }) {
  const offers = wizard.offers;

  const addOffer = () => {
    setWizard((prev) => ({
      ...prev,
      offers: [...prev.offers, createEmptyOffer(prev.offers.length)],
    }));
  };

  const removeOffer = (id) => {
    setWizard((prev) => ({ ...prev, offers: prev.offers.filter((o) => o.id !== id) }));
  };

  const updateOffer = (id, patch) => {
    setWizard((prev) => ({
      ...prev,
      offers: prev.offers.map((o) => (o.id === id ? { ...o, ...patch } : o)),
    }));
  };

  const updatePricing = (id, pricingPatch) => {
    setWizard((prev) => ({
      ...prev,
      offers: prev.offers.map((o) =>
        o.id === id ? { ...o, pricing: { ...o.pricing, ...pricingPatch } } : o
      ),
    }));
  };

  const loadDemoOffers = () => {
    setWizard((prev) => ({ ...prev, offers: [...DEMO_OFFERS] }));
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-800">Offres fournisseurs</h3>
        <div className="flex items-center gap-2">
          {isDemo && (
            <button onClick={loadDemoOffers} className="text-xs text-blue-600 hover:underline">
              Charger les {DEMO_OFFERS.length} offres demo
            </button>
          )}
          <Button size="sm" onClick={addOffer}>
            <Plus size={14} /> Ajouter une offre
          </Button>
        </div>
      </div>

      {isDemo && offers.length === 0 && wizard.offers.length === 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-blue-700">
          <Info size={16} className="inline mr-1" />
          En mode demo, {DEMO_OFFERS.length} offres sont pre-chargees automatiquement. Vous pouvez
          aussi en creer manuellement.
        </div>
      )}

      {offers.length > 0 && (
        <div className="space-y-3">
          {offers.map((offer) => (
            <OfferCard
              key={offer.id}
              offer={offer}
              onUpdate={updateOffer}
              onUpdatePricing={updatePricing}
              onRemove={removeOffer}
              readOnly={isDemo && DEMO_OFFERS.some((d) => d.id === offer.id)}
              highlighted={highlightOffer && offer.structure === highlightOffer}
            />
          ))}
        </div>
      )}

      {wizard.offers.length > 0 && (
        <p className="text-xs text-gray-400">
          {wizard.offers.length} offre(s) saisie(s) manuellement
        </p>
      )}
    </div>
  );
}

function OfferCard({ offer, onUpdate, onUpdatePricing, onRemove, readOnly, highlighted }) {
  const [expanded, setExpanded] = useState(!!highlighted);

  return (
    <div
      data-testid={highlighted ? 'offer-highlighted' : undefined}
      className={`bg-white rounded-lg border overflow-hidden ${highlighted ? 'border-amber-400 ring-2 ring-amber-200' : 'border-gray-200'}`}
    >
      <div className="flex items-center justify-between p-4">
        <div className="flex items-center gap-3">
          <span
            className={`px-2 py-1 text-xs font-semibold rounded-full ${STRUCTURE_COLORS[offer.structure] || 'bg-gray-100 text-gray-600'}`}
          >
            {STRUCTURE_LABELS[offer.structure] || offer.structure}
          </span>
          {readOnly ? (
            <span className="font-medium text-gray-900">{offer.supplierName}</span>
          ) : (
            <input
              type="text"
              placeholder="Nom du fournisseur"
              className="font-medium text-gray-900 border-b border-transparent hover:border-gray-300 focus:border-blue-500 outline-none px-1"
              value={offer.supplierName}
              onChange={(e) => onUpdate(offer.id, { supplierName: e.target.value })}
            />
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-gray-400 hover:text-gray-600"
          >
            <Eye size={16} />
          </button>
          {!readOnly && (
            <button onClick={() => onRemove(offer.id)} className="text-gray-400 hover:text-red-500">
              <Trash2 size={16} />
            </button>
          )}
        </div>
      </div>

      {!readOnly && (
        <div className="px-4 pb-3 flex items-center gap-4">
          <div>
            <label className="text-xs text-gray-500">Structure</label>
            <select
              className="block border border-gray-300 rounded px-2 py-1 text-sm mt-0.5"
              value={offer.structure}
              onChange={(e) => {
                const s = e.target.value;
                const pricingPatch =
                  s === OfferStructure.FIXE
                    ? { fixedSharePct: 1, indexedSharePct: 0, spotSharePct: 0 }
                    : s === OfferStructure.INDEXE
                      ? { fixedSharePct: 0, indexedSharePct: 1, spotSharePct: 0 }
                      : s === OfferStructure.SPOT
                        ? { fixedSharePct: 0, indexedSharePct: 0, spotSharePct: 1 }
                        : {};
                onUpdate(offer.id, { structure: s });
                if (Object.keys(pricingPatch).length) onUpdatePricing(offer.id, pricingPatch);
              }}
            >
              {Object.entries(STRUCTURE_LABELS).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </div>
          {(offer.structure === OfferStructure.FIXE ||
            offer.structure === OfferStructure.HYBRIDE) && (
            <div>
              <label className="text-xs text-gray-500">Prix fixe (EUR/MWh)</label>
              <input
                type="number"
                className="block w-24 border border-gray-300 rounded px-2 py-1 text-sm mt-0.5"
                value={offer.pricing.fixedPriceEurPerMwh}
                onChange={(e) =>
                  onUpdatePricing(offer.id, { fixedPriceEurPerMwh: Number(e.target.value) })
                }
              />
            </div>
          )}
          {(offer.structure === OfferStructure.INDEXE ||
            offer.structure === OfferStructure.HYBRIDE) && (
            <>
              <div>
                <label className="text-xs text-gray-500">Spread (EUR/MWh)</label>
                <input
                  type="number"
                  className="block w-20 border border-gray-300 rounded px-2 py-1 text-sm mt-0.5"
                  value={offer.pricing.spreadEurPerMwh || 0}
                  onChange={(e) =>
                    onUpdatePricing(offer.id, { spreadEurPerMwh: Number(e.target.value) })
                  }
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">Cap (EUR/MWh)</label>
                <input
                  type="number"
                  placeholder="—"
                  className="block w-20 border border-gray-300 rounded px-2 py-1 text-sm mt-0.5"
                  value={offer.pricing.capEurPerMwh ?? ''}
                  onChange={(e) =>
                    onUpdatePricing(offer.id, {
                      capEurPerMwh: e.target.value ? Number(e.target.value) : null,
                    })
                  }
                />
              </div>
            </>
          )}
          {offer.structure === OfferStructure.HYBRIDE && (
            <>
              <div>
                <label className="text-xs text-gray-500">% Fixe</label>
                <input
                  type="number"
                  min={0}
                  max={100}
                  className="block w-16 border border-gray-300 rounded px-2 py-1 text-sm mt-0.5"
                  value={Math.round((offer.pricing.fixedSharePct || 0) * 100)}
                  onChange={(e) =>
                    onUpdatePricing(offer.id, { fixedSharePct: Number(e.target.value) / 100 })
                  }
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">% Indexe</label>
                <input
                  type="number"
                  min={0}
                  max={100}
                  className="block w-16 border border-gray-300 rounded px-2 py-1 text-sm mt-0.5"
                  value={Math.round((offer.pricing.indexedSharePct || 0) * 100)}
                  onChange={(e) =>
                    onUpdatePricing(offer.id, { indexedSharePct: Number(e.target.value) / 100 })
                  }
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">% Spot</label>
                <input
                  type="number"
                  min={0}
                  max={100}
                  className="block w-16 border border-gray-300 rounded px-2 py-1 text-sm mt-0.5"
                  value={Math.round((offer.pricing.spotSharePct || 0) * 100)}
                  onChange={(e) =>
                    onUpdatePricing(offer.id, { spotSharePct: Number(e.target.value) / 100 })
                  }
                />
              </div>
            </>
          )}
        </div>
      )}

      {expanded && (
        <div className="px-4 pb-4 pt-2 border-t border-gray-100 text-xs text-gray-500 space-y-2">
          <div>
            <strong>Contrat:</strong> {offer.contractTerms?.durationMonths}m, preavis{' '}
            {offer.contractTerms?.noticePeriodDays}j, resiliation:{' '}
            {offer.contractTerms?.earlyTerminationPenalty}
          </div>
          <div>
            <strong>SLA:</strong> {offer.contractTerms?.slaLevel} | Indexation:{' '}
            {offer.contractTerms?.indexationClause} | Vert:{' '}
            {offer.contractTerms?.greenCertified ? 'Oui' : 'Non'}
          </div>
          <div>
            <strong>Intermediation:</strong>{' '}
            {offer.intermediation?.hasIntermediary
              ? `Oui (${offer.intermediation.feeDisclosed ? offer.intermediation.feeEurPerMwh + ' EUR/MWh' : 'Non divulgue'})`
              : 'Non'}
          </div>
          <div>
            <strong>Data:</strong> Courbes: {offer.dataTerms?.curvesAccess ? 'Oui' : 'Non'} | J+1:{' '}
            {offer.dataTerms?.dplus1 ? 'Oui' : 'Non'} | CSV:{' '}
            {offer.dataTerms?.csvExport ? 'Oui' : 'Non'} | API:{' '}
            {offer.dataTerms?.apiAccess ? 'Oui' : 'Non'}
          </div>
          <div>
            <strong>Decomposition:</strong> {offer.breakdown?.length || 0} composante(s) (
            {offer.breakdown?.filter((b) => b.status === 'KNOWN').length || 0} connue(s))
          </div>
          {offer.contractTerms?.clauseFlags?.length > 0 && (
            <div className="text-red-500">
              <strong>Alertes clauses:</strong> {offer.contractTerms.clauseFlags.join(', ')}
            </div>
          )}
          {offer.solarSlots && (
            <div
              data-testid="offer-solar-slots"
              className="bg-amber-50 border border-amber-200 rounded-lg p-3 mt-1"
            >
              <h5 className="text-xs font-semibold text-amber-800 flex items-center gap-1.5 mb-2">
                <Sun size={12} /> Créneaux Heures Solaires
              </h5>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <span className="font-medium text-amber-700">Été :</span>{' '}
                  <span className="text-gray-700">
                    {offer.solarSlots.summer.start}–{offer.solarSlots.summer.end} (
                    {offer.solarSlots.summer.days})
                  </span>
                  <br />
                  <span className="text-gray-500">
                    WE : {offer.solarSlots.summer.weekendStart}–{offer.solarSlots.summer.weekendEnd}
                  </span>
                </div>
                <div>
                  <span className="font-medium text-amber-700">Hiver :</span>{' '}
                  <span className="text-gray-700">
                    {offer.solarSlots.winter.start}–{offer.solarSlots.winter.end} (
                    {offer.solarSlots.winter.days})
                  </span>
                  <br />
                  <span className="text-gray-500">
                    WE : {offer.solarSlots.winter.weekendStart}–{offer.solarSlots.winter.weekendEnd}
                  </span>
                </div>
              </div>
              <p
                data-testid="offer-no-penalty"
                className="text-green-700 mt-2 flex items-center gap-1"
              >
                <CheckCircle2 size={10} /> Pas de pénalité si vous ne décalez pas votre
                consommation.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// STEP 6: Results
// ═══════════════════════════════════════════════════════════════════

function StepResults({ engineOutput, scoredOffers, recommendation, computing, onRecompute }) {
  if (computing) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto mb-4" />
          <p className="text-sm text-gray-500">Calcul Monte Carlo en cours...</p>
        </div>
      </div>
    );
  }

  if (!engineOutput || scoredOffers.length === 0) {
    return (
      <EmptyState
        icon={BarChart3}
        title="Aucun résultat"
        description="Revenez à l'étape Offres et avancez pour lancer le calcul."
      />
    );
  }

  const bestId = recommendation?.bestOfferId;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-800">Résultats — Corridor de prix & TCO</h3>
        <button onClick={onRecompute} className="text-xs text-blue-600 hover:underline">
          Recalculer
        </button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard
          label="Offres evaluees"
          value={scoredOffers.length}
          icon={<FileText size={18} />}
        />
        <KpiCard
          label="Meilleur P50"
          value={
            scoredOffers.length > 0 && scoredOffers.some((s) => s.corridor?.p50 != null)
              ? `${fmtNum(Math.min(...scoredOffers.filter((s) => s.corridor?.p50 != null).map((s) => s.corridor.p50)), 1)} EUR/MWh`
              : '—'
          }
          icon={<TrendingUp size={18} />}
        />
        <KpiCard
          label="Horizon"
          value={`${engineOutput?.params?.horizonMonths ?? '—'} mois`}
          icon={<Clock size={18} />}
        />
        <KpiCard
          label="Iterations MC"
          value={engineOutput?.params?.mcIterations ?? '—'}
          icon={<BarChart3 size={18} />}
        />
      </div>

      {/* Offer comparison table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
            <tr>
              <th className="px-4 py-3 text-left">Fournisseur</th>
              <th className="px-4 py-3 text-left">Structure</th>
              <th className="px-4 py-3 text-right">P10</th>
              <th className="px-4 py-3 text-right">P50</th>
              <th className="px-4 py-3 text-right">P90</th>
              <th className="px-4 py-3 text-right">TCO P50</th>
              <th className="px-4 py-3 text-right">Cout/an</th>
              <th className="px-4 py-3 text-right">Volatilité</th>
              <th className="px-4 py-3 text-right">CVaR90</th>
              <th className="px-4 py-3 text-right">P(Budget)</th>
              <th className="px-4 py-3 text-center">Score</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {scoredOffers.map((s) => {
              const isBest = s.offerId === bestId;
              return (
                <tr key={s.offerId} className={isBest ? 'bg-blue-50' : 'hover:bg-gray-50'}>
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {isBest && <Star size={14} className="inline mr-1 text-blue-600" />}
                    {s.supplierName}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-0.5 text-xs font-medium rounded-full ${STRUCTURE_COLORS[s.structure]}`}
                    >
                      {STRUCTURE_LABELS[s.structure]}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums">
                    {fmtNum(s.corridor?.p10, 1)}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums font-semibold">
                    {fmtNum(s.corridor?.p50, 1)}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums">
                    {fmtNum(s.corridor?.p90, 1)}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums">
                    {s.corridor?.tcoP50 != null
                      ? Math.round(s.corridor.tcoP50).toLocaleString('fr-FR')
                      : '—'}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums">
                    {s.annualCostP50 != null ? Math.round(s.annualCostP50).toLocaleString('fr-FR') : '—'}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums">
                    {s.volatility != null ? Math.round(s.volatility).toLocaleString('fr-FR') : '—'}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums">
                    {s.cvar90 != null ? Math.round(s.cvar90).toLocaleString('fr-FR') : '—'}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums">
                    {s.probExceedBudget != null ? fmtPct(s.probExceedBudget, true, 0) : '—'}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`inline-block w-10 text-center font-bold text-xs py-0.5 rounded ${
                        s.scores.overall >= 70
                          ? 'bg-green-100 text-green-700'
                          : s.scores.overall >= 40
                            ? 'bg-amber-100 text-amber-700'
                            : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {s.scores.overall}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Hybrid normalization warnings */}
      {scoredOffers
        .filter((s) => s.hybridNormalized)
        .map((s) => (
          <div key={s.offerId} className="bg-amber-50 rounded-lg p-2 text-xs text-amber-700">
            <AlertTriangle size={12} className="inline mr-1" />
            {s.supplierName}: {s.hybridNormMessage}
          </div>
        ))}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// STEP 7: Scoring
// ═══════════════════════════════════════════════════════════════════

function StepScoring({ scoredOffers, recommendation }) {
  const [selectedOfferId, setSelectedOfferId] = useState(null);
  const selected = scoredOffers.find((s) => s.offerId === selectedOfferId) || scoredOffers[0];

  if (scoredOffers.length === 0) {
    return (
      <EmptyState
        icon={Shield}
        title="Pas de scores"
        description="Lancez d'abord le calcul a l'etape Resultats."
      />
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-800">Scoring detaille & Transparence</h3>

      {/* Offer selector */}
      <div className="flex gap-2 flex-wrap">
        {scoredOffers.map((s) => (
          <button
            key={s.offerId}
            onClick={() => setSelectedOfferId(s.offerId)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition border
              ${selected?.offerId === s.offerId ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}
          >
            {s.supplierName}
            {s.offerId === recommendation?.bestOfferId && (
              <Star size={12} className="inline ml-1 text-blue-500" />
            )}
          </button>
        ))}
      </div>

      {selected && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* 4 scoring axes */}
          {[
            { key: 'budgetRisk', label: 'Risque Budgetaire', icon: AlertTriangle },
            { key: 'transparency', label: 'Transparence', icon: Eye },
            { key: 'contractRisk', label: 'Risque Contractuel', icon: Lock },
            { key: 'dataReadiness', label: 'Donnees & Readiness', icon: BarChart3 },
          ].map((axis) => {
            const score = selected.scores[axis.key];
            if (!score) return null;
            const Icon = axis.icon;
            return (
              <div key={axis.key} className={`rounded-lg border p-4 ${SCORE_COLORS[score.level]}`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Icon size={16} />
                    <span className="font-medium text-sm">{axis.label}</span>
                  </div>
                  <span className="text-lg font-bold">{score.score0to100}/100</span>
                </div>
                <Progress value={score.score0to100} max={100} className="mb-2" />
                {score.reasons.length > 0 && (
                  <ul className="space-y-1 mt-2">
                    {score.reasons.map((r, i) => (
                      <li key={i} className="text-xs flex items-start gap-1">
                        <Minus size={10} className="mt-0.5 flex-shrink-0" /> {r}
                      </li>
                    ))}
                  </ul>
                )}
                {score.evidence.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-current/10">
                    <p className="text-[10px] font-medium mb-1">Evidence:</p>
                    {score.evidence.map((e, i) => (
                      <span
                        key={i}
                        className="inline-block mr-1 mb-1 px-1.5 py-0.5 bg-white/50 rounded text-[10px]"
                      >
                        {e.ruleId}: {e.field}={JSON.stringify(e.value)?.slice(0, 30)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Breakdown table */}
      {selected?.offer?.breakdown?.length > 0 && (
        <Card>
          <CardHeader>Decomposition tarifaire — {selected.supplierName}</CardHeader>
          <CardBody>
            <div className="space-y-1">
              {selected.offer.breakdown.map((b, i) => (
                <div key={i} className="flex items-center justify-between text-sm py-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-2 h-2 rounded-full ${b.status === 'KNOWN' ? 'bg-green-500' : b.status === 'ESTIMATED' ? 'bg-amber-500' : 'bg-red-500'}`}
                    />
                    <span className="text-gray-700">
                      {BREAKDOWN_LABELS[b.component] || b.component}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-xs">
                    <span className="text-gray-500">{fmtPct(b.sharePct, true, 1)}</span>
                    <span className="text-gray-700 font-medium w-20 text-right">
                      {b.eurPerMwh != null ? `${fmtNum(b.eurPerMwh, 2)} EUR/MWh` : 'est.'}
                    </span>
                    <Badge
                      variant={
                        b.status === 'KNOWN' ? 'green' : b.status === 'ESTIMATED' ? 'yellow' : 'red'
                      }
                    >
                      {b.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// STEP 8: Decision
// ═══════════════════════════════════════════════════════════════════

function StepDecision({
  recommendation,
  scoredOffers,
  engineOutput,
  offers,
  wizard,
  selectedSitesData,
  _isDemo,
  onShowAudit,
  toast,
}) {
  if (!recommendation || !recommendation.bestOfferId) {
    return (
      <EmptyState
        icon={Target}
        title="Pas de recommandation"
        description="Lancez le calcul a l'etape Resultats."
      />
    );
  }

  const bestScored = scoredOffers.find((s) => s.offerId === recommendation.bestOfferId);

  const handleExportCsv = () => {
    const csv = generateComparisonCsv(
      recommendation._scoredOffers || scoredOffers,
      engineOutput?.results || []
    );
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `promeos_b3_comparaison_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast('Export CSV telecharge', 'success');
  };

  const handleExportDecisionNote = () => {
    const note = generateDecisionNote({
      recommendation,
      scoredOffers: recommendation._scoredOffers || scoredOffers,
      offerResults: engineOutput?.results || [],
      offers,
      persona: wizard.persona,
      annualKwh: selectedSitesData.annualKwh || wizard.totalAnnualKwh,
      energyType: selectedSitesData.energyType || wizard.energyType,
      horizonMonths: wizard.horizonMonths,
      scenarioPreset: wizard.scenarioPreset,
      budgetEur: wizard.budgetEur,
    });
    const blob = new Blob([JSON.stringify(note, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `promeos_b3_note_decision_${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast('Note de decision exportee', 'success');
  };

  const handleExportRfp = () => {
    const rfp = generateRfpPack({
      offerResults: engineOutput?.results || [],
      offers,
      scoredOffers: recommendation._scoredOffers || scoredOffers,
      annualKwh: selectedSitesData.annualKwh || wizard.totalAnnualKwh,
      energyType: selectedSitesData.energyType || wizard.energyType,
      horizonMonths: wizard.horizonMonths,
      scenarioPreset: wizard.scenarioPreset,
      budgetEur: wizard.budgetEur,
    });
    const blob = new Blob([JSON.stringify(rfp, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `promeos_b3_pack_rfp_${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast('Pack RFP exporte', 'success');
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-800">Recommandation & Decision</h3>

      {/* Confidence badge */}
      <div className="flex items-center gap-3">
        <span
          className={`px-3 py-1 rounded-full text-sm font-semibold ${CONFIDENCE_COLORS[recommendation.confidence]}`}
        >
          Confiance: {recommendation.confidence}
        </span>
        <span className="text-sm text-gray-500">{recommendation.confidenceReason}</span>
      </div>

      {/* Best offer card */}
      {bestScored && (
        <div className="bg-white rounded-xl border-2 border-blue-500 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                <Star size={20} className="text-blue-600" />
              </div>
              <div>
                <h4 className="font-bold text-gray-900 text-lg">{bestScored.supplierName}</h4>
                <span
                  className={`px-2 py-0.5 text-xs font-medium rounded-full ${STRUCTURE_COLORS[bestScored.structure]}`}
                >
                  {STRUCTURE_LABELS[bestScored.structure]}
                </span>
              </div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-gray-900">
                {fmtNum(bestScored.corridor.p50, 1)}{' '}
                <span className="text-sm font-normal text-gray-500">EUR/MWh</span>
              </div>
              <div className="text-sm text-gray-500">
                {Math.round(bestScored.annualCostP50).toLocaleString('fr-FR')} EUR/an
              </div>
            </div>
          </div>

          {/* Rationale */}
          <div className="mb-4">
            <h5 className="text-sm font-semibold text-gray-700 mb-2">Pourquoi cette offre:</h5>
            <ul className="space-y-1">
              {recommendation.rationaleBullets.map((b, i) => (
                <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                  <CheckCircle2 size={14} className="text-green-500 mt-0.5 flex-shrink-0" /> {b}
                </li>
              ))}
            </ul>
          </div>

          {/* Tradeoffs */}
          {recommendation.tradeoffs.length > 0 && (
            <div className="mb-4">
              <h5 className="text-sm font-semibold text-gray-700 mb-2">Points d'attention:</h5>
              <ul className="space-y-1">
                {recommendation.tradeoffs.map((t, i) => (
                  <li key={i} className="text-sm text-amber-600 flex items-start gap-2">
                    <AlertTriangle size={14} className="mt-0.5 flex-shrink-0" /> {t}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Why not others */}
      {Object.keys(recommendation.whyNotOthers).length > 0 && (
        <Card>
          <CardHeader>Pourquoi pas les autres offres</CardHeader>
          <CardBody>
            <div className="space-y-2">
              {Object.entries(recommendation.whyNotOthers).map(([offerId, reason]) => {
                const other = scoredOffers.find((s) => s.offerId === offerId);
                return (
                  <div key={offerId} className="flex items-center justify-between py-1">
                    <span className="text-sm text-gray-700">{other?.supplierName || offerId}</span>
                    <span className="text-xs text-gray-500">{reason}</span>
                  </div>
                );
              })}
            </div>
          </CardBody>
        </Card>
      )}

      {/* Missing data */}
      {recommendation.missingDataToImproveConfidence.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h5 className="text-sm font-semibold text-blue-700 mb-2">Pour ameliorer la confiance:</h5>
          <ul className="space-y-1">
            {recommendation.missingDataToImproveConfidence.map((d, i) => (
              <li key={i} className="text-xs text-blue-600 flex items-start gap-2">
                <ArrowRight size={12} className="mt-0.5 flex-shrink-0" /> {d}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Export actions */}
      <div className="flex flex-wrap gap-3 pt-2">
        <Button onClick={handleExportDecisionNote}>
          <Download size={14} /> Note de Decision (JSON)
        </Button>
        <Button onClick={handleExportRfp} variant="secondary">
          <Download size={14} /> Pack RFP (JSON)
        </Button>
        <Button onClick={handleExportCsv} variant="secondary">
          <Download size={14} /> Comparaison (CSV)
        </Button>
        <Button onClick={() => downloadAuditFile('jsonl')} variant="secondary">
          <Lock size={14} /> Audit Trail (JSONL)
        </Button>
        <Button onClick={onShowAudit} variant="secondary">
          <Eye size={14} /> Voir l'audit trail
        </Button>
      </div>

      {/* Limits */}
      <div className="text-[10px] text-gray-400 pt-2 border-t border-gray-100">
        <p className="font-medium mb-1">Limites:</p>
        <ul className="space-y-0.5">
          <li>Simulation Monte Carlo (max 200 iterations) — valeur indicative</li>
          <li>Prix base sur hypotheses de marche (voir parametres)</li>
          <li>Scoring automatise — validation humaine recommandee</li>
          <li>Version moteur: {BRIQUE3_VERSION}</li>
        </ul>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// Audit Trail View
// ═══════════════════════════════════════════════════════════════════

function AuditTrailView() {
  const log = getAuditLog();

  if (log.length === 0) {
    return <p className="text-sm text-gray-400 py-4">Aucune decision enregistree.</p>;
  }

  return (
    <div className="space-y-3 max-h-96 overflow-y-auto">
      {[...log].reverse().map((record, i) => (
        <div key={record.decisionId || i} className="border border-gray-200 rounded-lg p-3 text-xs">
          <div className="flex items-center justify-between mb-1">
            <span className="font-mono text-gray-400">{record.decisionId}</span>
            <Badge
              variant={
                record.action === 'COMPUTE' ? 'blue' : record.action === 'ACCEPT' ? 'green' : 'gray'
              }
            >
              {record.action}
            </Badge>
          </div>
          <div className="text-gray-500">{new Date(record.timestamp).toLocaleString('fr-FR')}</div>
          <div className="text-gray-600 mt-1">
            {record.outputs?.bestOfferId && `Best: ${record.outputs.bestOfferId}`}
            {record.recommendation?.confidence &&
              ` | Confidence: ${record.recommendation.confidence}`}
            {record.outputs?.offerCount && ` | ${record.outputs.offerCount} offres`}
          </div>
        </div>
      ))}
    </div>
  );
}
