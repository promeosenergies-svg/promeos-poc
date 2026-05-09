import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const DemoContext = createContext();

export function DemoProvider({ children }) {
  // Audit Phase 1.7 P2 : useState(null) au lieu de (true) pour éviter
  // le flash visible 1 frame de la card démo en prod avant que le backend
  // ne réponde demoEnabled=false. Les consommateurs (cf ConformitePage)
  // doivent guarder leur rendu sur `demoEnabled === true` strict + loading.
  const [demoEnabled, setDemoEnabled] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/demo/status')
      .then((r) => r.json())
      .then((data) => {
        setDemoEnabled(Boolean(data.demo_enabled));
        setLoading(false);
      })
      .catch(() => {
        // Fallback : si le backend n'a pas répondu, on assume PROD strict
        // (pas de démo affichée) pour éviter toute fuite de chiffres en dur.
        setDemoEnabled(false);
        setLoading(false);
      });
  }, []);

  const [toggling, setToggling] = useState(false);

  const toggleDemo = useCallback(async () => {
    setToggling(true);
    const endpoint = demoEnabled ? '/api/demo/disable' : '/api/demo/enable';
    try {
      const resp = await fetch(endpoint, { method: 'POST' });
      const data = await resp.json();
      setDemoEnabled(data.demo_enabled);
    } catch {
      // toggle failed — user sees stale state
    } finally {
      setToggling(false);
    }
  }, [demoEnabled]);

  return (
    <DemoContext.Provider value={{ demoEnabled, toggleDemo, loading, toggling }}>
      {children}
    </DemoContext.Provider>
  );
}

export function useDemo() {
  const ctx = useContext(DemoContext);
  if (!ctx) throw new Error('useDemo must be used inside DemoProvider');
  return ctx;
}
