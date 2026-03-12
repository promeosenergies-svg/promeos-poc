/**
 * PROMEOS — DemoSpotlight (C.2b)
 * Onboarding spotlight overlay: 3 steps on Cockpit.
 * Persists "seen" state in localStorage.
 *
 * Usage:
 *   <DemoSpotlight />   // placed inside Cockpit
 *
 * Requires data-tour="step-1", data-tour="step-2", data-tour="step-3"
 * on the 3 target zones in Cockpit.jsx.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';

const LS_KEY = 'promeos_spotlight_seen';

const STEPS = [
  {
    target: 'step-1',
    title: 'KPIs exécutifs',
    body: 'Vue synthétique des 4 indicateurs clés : conformité, risque, maturité, couverture données.',
  },
  {
    target: 'step-2',
    title: 'Briefing du jour',
    body: 'Résumé quotidien automatique : alertes, actions prioritaires, tendances.',
  },
  {
    target: 'step-3',
    title: 'Watchlist',
    body: 'Sites et obligations à surveiller en priorité, classés par criticité.',
  },
];

export default function DemoSpotlight() {
  const [step, setStep] = useState(-1); // -1 = not started or dismissed
  const overlayRef = useRef(null);
  const [rect, setRect] = useState(null);

  // Auto-show is disabled: the spotlight blocks the cockpit on fresh sessions
  // (demo, Playwright, new browser). Users can trigger onboarding from settings
  // if needed. This fixes P0-1 from the UX audit 2026-03-11.
  // Check localStorage on mount — only show if explicitly requested
  useEffect(() => {
    const requested = localStorage.getItem('promeos_spotlight_requested');
    if (requested) {
      localStorage.removeItem('promeos_spotlight_requested');
      const timer = setTimeout(() => setStep(0), 600);
      return () => clearTimeout(timer);
    }
  }, []);

  // Update target rect when step changes
  useEffect(() => {
    if (step < 0 || step >= STEPS.length) {
      setRect(null);
      return;
    }
    const el = document.querySelector(`[data-tour="${STEPS[step].target}"]`);
    if (el) {
      const r = el.getBoundingClientRect();
      setRect({ top: r.top, left: r.left, width: r.width, height: r.height });
    } else {
      setRect(null);
    }
  }, [step]);

  const dismiss = useCallback(() => {
    localStorage.setItem(LS_KEY, '1');
    setStep(-1);
  }, []);

  const next = useCallback(() => {
    if (step + 1 >= STEPS.length) {
      dismiss();
    } else {
      setStep((s) => s + 1);
    }
  }, [step, dismiss]);

  if (step < 0 || step >= STEPS.length) return null;

  const current = STEPS[step];
  const pad = 8;

  return createPortal(
    <div
      ref={overlayRef}
      className="fixed inset-0 z-[9999]"
      data-testid="demo-spotlight"
      onClick={dismiss}
    >
      {/* Semi-transparent overlay */}
      <div className="absolute inset-0 bg-black/40" />

      {/* Highlight cutout */}
      {rect && (
        <div
          className="absolute bg-white/10 rounded-lg ring-2 ring-blue-400 ring-offset-2"
          style={{
            top: rect.top - pad,
            left: rect.left - pad,
            width: rect.width + pad * 2,
            height: rect.height + pad * 2,
          }}
        />
      )}

      {/* Tooltip card */}
      <div
        className="absolute bg-white rounded-xl shadow-2xl p-5 w-80 z-[10000]"
        style={{
          top: rect ? rect.top + rect.height + 16 : '50%',
          left: rect ? Math.min(rect.left, window.innerWidth - 340) : '50%',
          transform: rect ? undefined : 'translate(-50%, -50%)',
        }}
        onClick={(e) => e.stopPropagation()}
        data-testid="spotlight-card"
      >
        <p className="text-xs text-gray-400 mb-1">
          Étape {step + 1} / {STEPS.length}
        </p>
        <h3 className="text-sm font-semibold text-gray-900 mb-1">{current.title}</h3>
        <p className="text-sm text-gray-600 mb-4">{current.body}</p>

        <div className="flex items-center justify-between">
          <button
            onClick={dismiss}
            className="text-xs text-gray-400 hover:text-gray-600 transition"
            data-testid="spotlight-skip"
          >
            Passer
          </button>
          <button
            onClick={next}
            className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition"
            data-testid="spotlight-next"
          >
            {step + 1 < STEPS.length ? 'Suivant' : 'Terminer'}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}
