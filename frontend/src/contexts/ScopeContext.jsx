/**
 * PROMEOS - Scope Context
 * Global context switcher: Organisation → Portefeuille → Site (optional).
 * Persisted in localStorage. Filters Dashboard, Patrimoine, Site360.
 */
import { createContext, useContext, useState, useCallback, useMemo } from 'react';
import { mockSites } from '../mocks/sites';

const STORAGE_KEY = 'promeos_scope';

const MOCK_ORGS = [
  { id: 1, nom: 'Nexity Immobilier' },
  { id: 2, nom: 'Groupe Casino' },
];

const MOCK_PORTEFEUILLES = [
  { id: 1, org_id: 1, nom: 'IDF' },
  { id: 2, org_id: 1, nom: 'PACA' },
  { id: 3, org_id: 1, nom: 'National' },
  { id: 4, org_id: 2, nom: 'Hypermarches' },
  { id: 5, org_id: 2, nom: 'Proximite' },
];

// Assign sites to portefeuilles deterministically
function sitePortefeuille(site) {
  return ((site.id - 1) % 5) + 1;
}

function loadScope() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  return { orgId: 1, portefeuilleId: null, siteId: null };
}

function saveScope(scope) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(scope));
}

const ScopeContext = createContext(null);

export function ScopeProvider({ children }) {
  const [scope, setScope] = useState(loadScope);

  const setOrg = useCallback((orgId) => {
    const next = { orgId, portefeuilleId: null, siteId: null };
    setScope(next);
    saveScope(next);
  }, []);

  const setPortefeuille = useCallback((portefeuilleId) => {
    setScope((prev) => {
      const next = { ...prev, portefeuilleId, siteId: null };
      saveScope(next);
      return next;
    });
  }, []);

  const setSite = useCallback((siteId) => {
    setScope((prev) => {
      const next = { ...prev, siteId };
      saveScope(next);
      return next;
    });
  }, []);

  const resetScope = useCallback(() => {
    const next = { orgId: scope.orgId, portefeuilleId: null, siteId: null };
    setScope(next);
    saveScope(next);
  }, [scope.orgId]);

  const org = MOCK_ORGS.find((o) => o.id === scope.orgId) || MOCK_ORGS[0];
  const portefeuilles = MOCK_PORTEFEUILLES.filter((p) => p.org_id === scope.orgId);
  const portefeuille = scope.portefeuilleId
    ? MOCK_PORTEFEUILLES.find((p) => p.id === scope.portefeuilleId)
    : null;

  // Filter sites by scope
  const scopedSites = useMemo(() => {
    let sites = mockSites.filter((s) => {
      const pfId = sitePortefeuille(s);
      const pf = MOCK_PORTEFEUILLES.find((p) => p.id === pfId);
      return pf && pf.org_id === scope.orgId;
    });
    if (scope.portefeuilleId) {
      sites = sites.filter((s) => sitePortefeuille(s) === scope.portefeuilleId);
    }
    if (scope.siteId) {
      sites = sites.filter((s) => s.id === scope.siteId);
    }
    return sites;
  }, [scope.orgId, scope.portefeuilleId, scope.siteId]);

  const value = {
    scope, org, portefeuille, portefeuilles, scopedSites,
    orgs: MOCK_ORGS,
    setOrg, setPortefeuille, setSite, resetScope,
  };

  return <ScopeContext.Provider value={value}>{children}</ScopeContext.Provider>;
}

export function useScope() {
  const ctx = useContext(ScopeContext);
  if (!ctx) throw new Error('useScope must be used within ScopeProvider');
  return ctx;
}
