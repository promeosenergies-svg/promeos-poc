/**
 * PROMEOS - Scope Context
 * Global context switcher: Organisation → Portefeuille → Site (optional).
 * Persisted in localStorage. Filters Dashboard, Patrimoine, Site360.
 *
 * When authenticated: uses org/scopes from AuthContext.
 * When not authenticated (demo mode): falls back to mock data.
 * After seed-pack: applyDemoScope() auto-switches to the seeded org/site.
 */
import { createContext, useContext, useState, useCallback, useMemo } from 'react';
import { mockSites } from '../mocks/sites';
import { useAuth } from './AuthContext';

const STORAGE_KEY = 'promeos_scope';
const DEMO_ORGS_KEY = 'promeos_demo_orgs';

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

function loadDemoOrgs() {
  try {
    const raw = localStorage.getItem(DEMO_ORGS_KEY);
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  return [];
}

function saveDemoOrgs(orgs) {
  localStorage.setItem(DEMO_ORGS_KEY, JSON.stringify(orgs));
}

const ScopeContext = createContext(null);

export function ScopeProvider({ children }) {
  const [scope, setScope] = useState(loadScope);
  const [demoOrgs, setDemoOrgs] = useState(loadDemoOrgs);
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

  const clearScope = useCallback(() => {
    const next = { orgId: null, portefeuilleId: null, siteId: null };
    setScope(next);
    localStorage.removeItem(STORAGE_KEY);
    // Also clear demo orgs on full reset
    setDemoOrgs([]);
    localStorage.removeItem(DEMO_ORGS_KEY);
  }, []);

  /**
   * applyDemoScope — called after seed-pack to auto-switch to the seeded org.
   * Accepts an object: { orgId, orgNom, defaultSiteId?, defaultSiteName? }
   * Always sets siteId=null ("Tous les sites") for a clean multi-site demo context.
   * Registers the org in demoOrgs (persisted) and switches scope atomically.
   */
  const applyDemoScope = useCallback(({ orgId, orgNom, defaultSiteId = null, defaultSiteName = null } = {}) => {
    if (!orgId) return;
    // Register the org dynamically
    setDemoOrgs((prev) => {
      const exists = prev.some((o) => o.id === orgId);
      const next = exists ? prev : [...prev, { id: orgId, nom: orgNom || `Organisation #${orgId}` }];
      saveDemoOrgs(next);
      return next;
    });
    // Switch scope: always siteId=null => "Tous les sites" in demo mode
    const next = { orgId, portefeuilleId: null, siteId: null };
    setScope(next);
    saveScope(next);
    // eslint-disable-next-line no-unused-expressions
    void defaultSiteId; void defaultSiteName; // reserved for future use
  }, []);

  // When authenticated, use auth orgs; otherwise mock + dynamically registered demo orgs
  const orgsData = useMemo(() => {
    if (isAuth && auth.orgs && auth.orgs.length > 0) {
      return auth.orgs.map(o => ({ id: o.id, nom: o.nom }));
    }
    // Merge MOCK_ORGS + demoOrgs (dedup by id)
    const all = [...MOCK_ORGS];
    for (const d of demoOrgs) {
      if (!all.some((o) => o.id === d.id)) all.push(d);
    }
    return all;
  }, [isAuth, auth, demoOrgs]);

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

  /**
   * scopeLabel — human-readable label for the current site selection.
   * "Tous les sites" when no specific site is selected (siteId=null).
   * "Site : <nom>" when a specific site is selected.
   */
  const scopeLabel = useMemo(() => {
    if (!scope.siteId) return 'Tous les sites';
    const site = scopedSites.find(s => s.id === scope.siteId);
    return site ? `Site\u00a0: ${site.nom}` : 'Tous les sites';
  }, [scope.siteId, scopedSites]);

  /** selectedSiteId — convenience alias for scope.siteId */
  const selectedSiteId = scope.siteId;

  const value = {
    scope: { ...scope, orgId: effectiveOrgId },
    org, portefeuille, portefeuilles, scopedSites,
    orgs: orgsData,
    selectedSiteId,
    scopeLabel,
    setOrg, setPortefeuille, setSite, resetScope, clearScope, applyDemoScope,
  };

  return <ScopeContext.Provider value={value}>{children}</ScopeContext.Provider>;
}

export function useScope() {
  const ctx = useContext(ScopeContext);
  if (!ctx) throw new Error('useScope must be used within ScopeProvider');
  return ctx;
}
