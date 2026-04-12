/**
 * PROMEOS - Expert Mode Context
 * Global toggle: Simple (default) / Expert.
 * Persisted in localStorage. Pages use useExpertMode() to conditionally render advanced content.
 */
import { createContext, useContext, useState, useCallback } from 'react';

const STORAGE_KEY = 'promeos_expert';
const ONBOARDING_KEY = 'promeos_expert_seen';

function loadExpert() {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'true';
  } catch {
    return false;
  }
}

const ExpertModeContext = createContext(null);

export function ExpertModeProvider({ children }) {
  const [isExpert, setIsExpert] = useState(loadExpert);

  const [showOnboarding, setShowOnboarding] = useState(false);

  const toggleExpert = useCallback(() => {
    setIsExpert((prev) => {
      const next = !prev;
      localStorage.setItem(STORAGE_KEY, String(next));
      if (next && !localStorage.getItem(ONBOARDING_KEY)) {
        localStorage.setItem(ONBOARDING_KEY, 'true');
        setShowOnboarding(true);
        setTimeout(() => setShowOnboarding(false), 5000);
      }
      return next;
    });
  }, []);

  return (
    <ExpertModeContext.Provider value={{ isExpert, toggleExpert, showOnboarding }}>
      {children}
    </ExpertModeContext.Provider>
  );
}

export function useExpertMode() {
  const ctx = useContext(ExpertModeContext);
  if (!ctx) throw new Error('useExpertMode must be used within ExpertModeProvider');
  return ctx;
}
