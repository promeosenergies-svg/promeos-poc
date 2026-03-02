import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const DemoContext = createContext();

const API = 'http://127.0.0.1:8001';

export function DemoProvider({ children }) {
  const [demoEnabled, setDemoEnabled] = useState(true);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/demo/status`)
      .then(r => r.json())
      .then(data => {
        setDemoEnabled(data.demo_enabled);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const toggleDemo = useCallback(async () => {
    const endpoint = demoEnabled ? '/api/demo/disable' : '/api/demo/enable';
    try {
      const resp = await fetch(`${API}${endpoint}`, { method: 'POST' });
      const data = await resp.json();
      setDemoEnabled(data.demo_enabled);
    } catch (err) {
      console.error('Erreur toggle demo:', err);
    }
  }, [demoEnabled]);

  return (
    <DemoContext.Provider value={{ demoEnabled, toggleDemo, loading }}>
      {children}
    </DemoContext.Provider>
  );
}

export function useDemo() {
  const ctx = useContext(DemoContext);
  if (!ctx) throw new Error('useDemo must be used inside DemoProvider');
  return ctx;
}
