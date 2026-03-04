import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const DemoContext = createContext();

export function DemoProvider({ children }) {
  const [demoEnabled, setDemoEnabled] = useState(true);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/demo/status')
      .then(r => r.json())
      .then(data => {
        setDemoEnabled(data.demo_enabled);
        setLoading(false);
      })
      .catch(() => setLoading(false));
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
