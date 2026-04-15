/**
 * PROMEOS — Onboarding Stepper Page (V113 Chantier 5)
 * Route: /onboarding
 * 6-step guided onboarding with auto-detection and manual progression.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Building2,
  MapPin,
  Zap,
  FileText,
  Users,
  Target,
  CheckCircle,
  Circle,
  Loader2,
  Sparkles,
  X,
  ArrowRight,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useScope } from '../contexts/ScopeContext';
import {
  getOnboardingProgress,
  updateOnboardingStep,
  dismissOnboarding,
  autoDetectOnboarding,
} from '../services/api';
import { PageShell, Card, CardBody, Button } from '../ui';

const STEP_ICONS = {
  Building2,
  MapPin,
  Zap,
  FileText,
  Users,
  Target,
};

const STEP_LINKS = {
  step_org_created: null,
  step_sites_added: '/onboarding/sirene',
  step_meters_connected: '/connectors',
  step_invoices_imported: '/billing',
  step_users_invited: '/admin/users',
  step_first_action: '/actions/new',
};

const STEP_DESCRIPTIONS = {
  step_org_created: "Votre organisation a été créée lors de l'inscription.",
  step_sites_added:
    'Créez votre patrimoine depuis un SIREN (auto-complétion Sirene officielle) ou manuellement.',
  step_meters_connected: "Connectez vos compteurs d'électricité et de gaz.",
  step_invoices_imported: "Importez vos factures pour l'analyse énergétique.",
  step_users_invited: 'Invitez vos collaborateurs sur la plateforme.',
  step_first_action: "Créez votre première action d'économie d'énergie.",
};

function StepCard({ step, index, onManualComplete }) {
  const Icon = STEP_ICONS[step.icon] || Circle;
  const link = STEP_LINKS[step.key];
  const description = STEP_DESCRIPTIONS[step.key];
  const navigate = useNavigate();

  return (
    <div
      className={`flex items-start gap-4 p-4 rounded-lg border transition ${
        step.done
          ? 'bg-emerald-50 border-emerald-200'
          : 'bg-white border-gray-200 hover:border-blue-300'
      }`}
    >
      {/* Step number + icon */}
      <div
        className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
          step.done ? 'bg-emerald-500 text-white' : 'bg-gray-100 text-gray-400'
        }`}
      >
        {step.done ? (
          <CheckCircle size={20} />
        ) : (
          <span className="text-sm font-bold">{index + 1}</span>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <Icon size={16} className={step.done ? 'text-emerald-600' : 'text-gray-500'} />
          <p
            className={`text-sm font-semibold ${step.done ? 'text-emerald-700' : 'text-gray-900'}`}
          >
            {step.label}
          </p>
        </div>
        <p className="text-xs text-gray-500 mt-1">{description}</p>

        {!step.done && (
          <div className="flex gap-2 mt-2">
            {link && (
              <Button size="sm" onClick={() => navigate(link)}>
                <ArrowRight size={14} className="mr-1" /> Configurer
              </Button>
            )}
            <Button size="sm" variant="secondary" onClick={() => onManualComplete(step.key)}>
              <CheckCircle size={14} className="mr-1" /> Marquer terminé
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function OnboardingPage() {
  const { org } = useScope();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [autoLoading, setAutoLoading] = useState(false);
  const navigate = useNavigate();

  const fetchProgress = useCallback(() => {
    if (!org?.id) return;
    setLoading(true);
    getOnboardingProgress(org.id)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [org?.id]);

  useEffect(() => {
    fetchProgress();
  }, [fetchProgress]);

  // Auto-detect completed steps on first load if all steps show 0%
  const autoDetectedRef = useRef(false);
  useEffect(() => {
    if (data && data.completed_count === 0 && !autoDetectedRef.current && org?.id) {
      autoDetectedRef.current = true;
      autoDetectOnboarding(org.id)
        .then(setData)
        .catch(() => {});
    }
  }, [data, org?.id]);

  // Auto-redirect to cockpit when onboarding is 100% complete
  useEffect(() => {
    if (!data?.all_done) return;
    const timer = setTimeout(() => navigate('/'), 3000);
    return () => clearTimeout(timer);
  }, [data?.all_done, navigate]);

  const handleManualComplete = async (stepKey) => {
    if (!org?.id) return;
    try {
      const updated = await updateOnboardingStep(org.id, stepKey, true);
      setData(updated);
    } catch {
      /* ignore */
    }
  };

  const handleAutoDetect = async () => {
    if (!org?.id) return;
    setAutoLoading(true);
    try {
      const updated = await autoDetectOnboarding(org.id);
      setData(updated);
    } finally {
      setAutoLoading(false);
    }
  };

  const handleDismiss = async () => {
    if (!org?.id) return;
    await dismissOnboarding(org.id);
    navigate('/');
  };

  const steps = data?.steps || [];
  const progressPct = data?.progress_pct || 0;

  return (
    <PageShell
      icon={Sparkles}
      title="Démarrage"
      subtitle="Configurez votre plateforme en 6 étapes"
      actions={
        <div className="flex gap-2">
          <Button size="sm" variant="secondary" onClick={handleAutoDetect} disabled={autoLoading}>
            {autoLoading ? (
              <Loader2 size={14} className="animate-spin mr-1" />
            ) : (
              <Sparkles size={14} className="mr-1" />
            )}
            Détection auto
          </Button>
          <Button size="sm" variant="secondary" onClick={handleDismiss}>
            <X size={14} className="mr-1" /> Masquer
          </Button>
        </div>
      }
    >
      {/* Progress bar */}
      <Card>
        <CardBody>
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-semibold text-gray-700">
              Progression : {data?.completed_count || 0} / {data?.total || 6}
            </p>
            <span className="text-sm font-bold text-blue-600">{progressPct}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className="bg-blue-600 h-3 rounded-full transition-all duration-500"
              style={{ width: `${progressPct}%` }}
            />
          </div>
          {data?.all_done && (
            <div className="mt-2">
              <p className="text-sm text-emerald-600 font-medium">
                Félicitations ! Votre plateforme est prête.
              </p>
              <p className="text-xs text-gray-400 mt-1">
                Redirection vers le cockpit dans quelques secondes...
              </p>
            </div>
          )}
        </CardBody>
      </Card>

      {/* Steps */}
      {loading ? (
        <div className="flex items-center justify-center py-12 text-gray-400">
          <Loader2 size={20} className="animate-spin mr-2" /> Chargement...
        </div>
      ) : (
        <div className="space-y-3">
          {steps.map((step, i) => (
            <StepCard
              key={step.key}
              step={step}
              index={i}
              onManualComplete={handleManualComplete}
            />
          ))}
        </div>
      )}
    </PageShell>
  );
}
