/**
 * PROMEOS - Scope Context
 * Global context switcher: Organisation → Portefeuille → Site (optional).
 * Persisted in localStorage. Filters Dashboard, Patrimoine, Site360.
 *
 * When authenticated: uses org/scopes from AuthContext.
 * When not authenticated (demo mode): falls back to mock data.
 */
import { createContext, useContext, useState, useCallback, useMemo } from 'react';
import { mockSites } from '../mocks/sites';
import { useAuth } from './AuthContext';

const STORAGE_KEY = 'promeos_scope';

const MOCK_ORGS = [
  { id: 1, nom: 'Groupe Casino' },
  { id: 2, nom: 'Nexity Immobilier' },
];

const MOCK_PORTEFEUILLES = [
  { id: 1, org_id: 1, nom: 'Hypermarches' },
  { id: 2, org_id: 1, nom: 'Proximite' },
  { id: 3, org_id: 1, nom: 'Logistique' },
  { id: 4, org_id: 2, nom: 'IDF' },
  { id: 5, org_id: 2, nom: 'PACA' },
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
  const auth = useAuth();

  const isAuth = auth && auth.isAuthenticated;

  // When authenticated, override orgId from auth context
  const effectiveOrgId = isAuth && auth.org ? auth.org.id : scope.orgId;

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
    const next = { orgId: effectiveOrgId, portefeuilleId: null, siteId: null };
    setScope(next);
    saveScope(next);
  }, [effectiveOrgId]);

  // When authenticated, use auth orgs; otherwise mock
  const orgsData = isAuth && auth.orgs && auth.orgs.length > 0
    ? auth.orgs.map(o => ({ id: o.id, nom: o.nom }))
    : MOCK_ORGS;

  const org = orgsData.find((o) => o.id === effectiveOrgId) || orgsData[0];
  const portefeuilles = MOCK_PORTEFEUILLES.filter((p) => p.org_id === effectiveOrgId);
  const portefeuille = scope.portefeuilleId
    ? MOCK_PORTEFEUILLES.find((p) => p.id === scope.portefeuilleId)
    : null;

  // Filter sites by scope
  const scopedSites = useMemo(() => {
    let sites = mockSites.filter((s) => {
      const pfId = sitePortefeuille(s);
      const pf = MOCK_PORTEFEUILLES.find((p) => p.id === pfId);
      return pf && pf.org_id === effectiveOrgId;
    });
    if (scope.portefeuilleId) {
      sites = sites.filter((s) => sitePortefeuille(s) === scope.portefeuilleId);
    }
    if (scope.siteId) {
      sites = sites.filter((s) => s.id === scope.siteId);
    }
    return sites;
  }, [effectiveOrgId, scope.portefeuilleId, scope.siteId]);

  const value = {
    scope: { ...scope, orgId: effectiveOrgId },
    org, portefeuille, portefeuilles, scopedSites,
    orgs: orgsData,
    setOrg, setPortefeuille, setSite, resetScope,
  };

  return <ScopeContext.Provider value={value}>{children}</ScopeContext.Provider>;
}

export function useScope() {
  const ctx = useContext(ScopeContext);
  if (!ctx) throw new Error('useScope must be used within ScopeProvider');
  return ctx;
}
