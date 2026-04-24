import { useState, useEffect, useContext } from 'react';
import { X, ChevronRight } from 'lucide-react';

const ONBOARDING_KEY = 'promeos_onboarding_done';

/**
 * Onboarding désactivé par défaut en mode démo + en production pour éviter
 * de bloquer la première impression à l'accueil. Pour re-activer pour un
 * vrai nouveau user : localStorage.setItem('promeos_onboarding_show', '1')
 * ou via env VITE_ONBOARDING_FORCE=1.
 * Fix M-01 Sprint P0 démo-ready (rapport V2 audit).
 */
function shouldShowOnboarding() {
  try {
    // Désactivé si déjà vu
    if (localStorage.getItem(ONBOARDING_KEY)) return false;
    // Force via env var (pour dev/debug)
    if (import.meta.env?.VITE_ONBOARDING_FORCE === '1') return true;
    // Force via localStorage (opt-in user)
    if (localStorage.getItem('promeos_onboarding_show') === '1') return true;
    // Par défaut : off en démo (cas usage principal PROMEOS)
    return false;
  } catch {
    return false;
  }
}

const STEPS = [
  {
    title: 'Navigation par module',
    text: 'Le rail regroupe 5 modules : Accueil, Conformite, Energie, Patrimoine, Achat. Cliquez sur une icone pour basculer.',
  },
  {
    title: 'Panneau contextuel',
    text: 'Chaque module affiche ses pages. Epinglez vos favoris, retrouvez vos recents.',
  },
  {
    title: 'Recherche rapide (Ctrl+K)',
    text: 'Cherchez pages, sites ou actions instantanement.',
  },
  {
    title: 'Mode Expert',
    text: 'Toggle Expert en haut a droite pour Audit SME, Simulateur achat et plus.',
  },
];

export default function OnboardingOverlay() {
  const [step, setStep] = useState(0);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (shouldShowOnboarding()) setVisible(true);
  }, []);

  const dismiss = () => {
    setVisible(false);
    try {
      localStorage.setItem(ONBOARDING_KEY, 'true');
    } catch {
      /* noop */
    }
  };

  const next = () => {
    if (step < STEPS.length - 1) setStep(step + 1);
    else dismiss();
  };

  if (!visible) return null;

  const s = STEPS[step];

  return (
    <div className="fixed inset-0 z-[280] flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/50 animate-[fadeIn_0.3s_ease-out]"
        onClick={dismiss}
      />
      <div className="relative bg-white rounded-2xl shadow-2xl max-w-md w-full mx-4 p-6 animate-[slideInUp_0.3s_ease-out]">
        <button
          onClick={dismiss}
          className="absolute top-3 right-3 p-1.5 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition"
          aria-label="Fermer"
        >
          <X size={16} />
        </button>

        <div className="flex gap-1.5 mb-4">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-1 flex-1 rounded-full transition-colors ${i <= step ? 'bg-blue-500' : 'bg-gray-200'}`}
            />
          ))}
        </div>

        <h3 className="text-lg font-semibold text-gray-900 mb-2">{s.title}</h3>
        <p className="text-sm text-gray-600 leading-relaxed mb-6">{s.text}</p>

        <div className="flex items-center justify-between">
          <button
            onClick={dismiss}
            className="text-sm text-gray-400 hover:text-gray-600 transition"
          >
            Passer le tour
          </button>
          <button
            onClick={next}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition"
          >
            {step < STEPS.length - 1 ? 'Suivant' : 'Commencer'}
            <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
