/**
 * PROMEOS - Scope Context
 * Global context switcher: Organisation → Portefeuille → Site (optional).
 * Persisted in localStorage. Filters Dashboard, Patrimoine, Site360.
 *
 * When authenticated: uses org/scopes from AuthContext.
 * When not authenticated (demo mode): falls back to mock data.
 * After seed-pack: applyDemoScope() auto-switches to the seeded org/site.
 */
import { createContext, useContext, useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { mockSites } from '../mocks/sites';
import { useAuth } from './AuthContext';
import { getSites, setApiScope, getDemoPackStatus, clearApiCache } from '../services/api';

const STORAGE_KEY = 'promeos_scope';
const DEMO_ORGS_KEY = 'promeos_demo_orgs';

const MOCK_ORGS = [
  { id: 1, nom: 'Groupe HELIOS' },
];

const MOCK_PORTEFEUILLES = [
  { id: 1, org_id: 1, nom: 'Siège & Bureaux' },
  { id: 2, org_id: 1, nom: 'Sites Industriels' },
  { id: 3, org_id: 1, nom: 'Patrimoine Tertiaire' },
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
  // Default to null — auto-sync from backend will resolve the correct org
  return { orgId: null, portefeuilleId: null, siteId: null };
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

  // ── Real sites from API (replaces mockSites when available) ───────────
  const [apiSites, setApiSites] = useState([]);
  const [sitesLoading, setSitesLoading] = useState(false); // V18: loading indicator
  const [sitesError, setSitesError] = useState(null); // V19: surface API errors
  const _fetchId = useRef(0); // V18: requestId guard — ignore stale responses
  const _fetchTrigger = useRef(0); // V19: manual refresh trigger

  // ── IMPORTANT: setApiScope MUST be called synchronously during render ──────
  // ── so _apiScope.orgId is set BEFORE any child useEffect runs.            ──
  // ── (React runs child effects before parent effects on mount.)             ──
  // ── setApiScope is idempotent and only mutates a module-level variable     ──
  // ── — no React state, no re-render. Safe to call during render.           ──
  setApiScope({ orgId: effectiveOrgId ?? null, siteId: scope.siteId ?? null });

  // Also keep the useEffect to handle future scope changes (re-renders).
  useEffect(() => {
    setApiScope({ orgId: effectiveOrgId ?? null, siteId: scope.siteId ?? null });
  }, [effectiveOrgId, scope.siteId]);

  // V19: refreshSites — bump trigger to re-run the fetch effect
  const [fetchTrigger, setFetchTrigger] = useState(0);
  const refreshSites = useCallback(() => {
    setFetchTrigger(t => t + 1);
  }, []);

  useEffect(() => {
    // V18-A (RC1+RC3): sitesLoading indicator + requestId guard to reject stale responses
    // V19: also clears error on retry, keeps previous sites during refresh
    if (!effectiveOrgId) {
      setApiSites([]);
      setSitesLoading(false);
      setSitesError(null);
      return;
    }
    setSitesLoading(true);
    setSitesError(null);
    const myId = ++_fetchId.current;
    getSites({ org_id: effectiveOrgId, limit: 2000 })
      .then(data => {
        if (myId !== _fetchId.current) return; // stale response — ignore
        const raw = Array.isArray(data) ? data : (data.sites || data.items || []);
        // Normalize: /api/sites returns statut_decret_tertiaire but frontend uses statut_conformite
        const list = raw.map(s => ({
          ...s,
          statut_conformite: s.statut_conformite ?? s.statut_decret_tertiaire ?? null,
          risque_eur: s.risque_eur ?? s.risque_financier_euro ?? 0,
        }));
        setApiSites(list);
        setSitesLoading(false);
      })
      .catch((err) => {
        if (myId !== _fetchId.current) return;
        const status = err?.response?.status;
        const msg = status === 401 ? 'Session expirée — reconnectez-vous'
          : status === 403 ? 'Accès refusé à cette organisation'
          : 'Impossible de charger les sites';
        setSitesError(msg);
        // V19: keep previous apiSites during transient errors (don't blank the UI)
        setSitesLoading(false);
      });
  }, [effectiveOrgId, fetchTrigger]);

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
    // Invalidate stale GET cache from previous org BEFORE switching scope
    clearApiCache();
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

  // Auto-sync: on mount, if no org is selected, check backend for a seeded demo
  const _autoSynced = useRef(false);
  useEffect(() => {
    if (scope.orgId || _autoSynced.current) return;
    _autoSynced.current = true;
    getDemoPackStatus()
      .then(status => {
        if (status?.org_id) {
          applyDemoScope({ orgId: status.org_id, orgNom: status.org_nom });
        }
      })
      .catch(() => {}); // Silent — no demo loaded on backend
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

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

  const org = effectiveOrgId
    ? (orgsData.find((o) => o.id === effectiveOrgId) || orgsData[0] || null)
    : null;
  const portefeuilles = MOCK_PORTEFEUILLES.filter((p) => p.org_id === effectiveOrgId);
  const portefeuille = scope.portefeuilleId
    ? MOCK_PORTEFEUILLES.find((p) => p.id === scope.portefeuilleId)
    : null;

  // Filter sites by scope — real API sites take priority over mock fallback
  const scopedSites = useMemo(() => {
    let sites;
    if (apiSites.length > 0) {
      // Real API sites are already org-scoped by the server
      sites = apiSites;
    } else if (!effectiveOrgId) {
      // Truly no org configured (offline/pre-demo): show a small mock sample
      sites = mockSites.slice(0, 10).filter((s) => {
        const pfId = sitePortefeuille(s);
        const pf = MOCK_PORTEFEUILLES.find((p) => p.id === pfId);
        return pf && pf.org_id === 1; // offline sample from HELIOS
      });
      if (scope.portefeuilleId) {
        sites = sites.filter((s) => sitePortefeuille(s) === scope.portefeuilleId);
      }
    } else {
      // Real org configured but API still loading → empty list (no stale mock data)
      sites = [];
    }
    if (scope.siteId) {
      // Use String() coercion to handle number/string mismatch (e.g. localStorage → string)
      sites = sites.filter((s) => String(s.id) === String(scope.siteId));
    }
    return sites;
  }, [apiSites, effectiveOrgId, scope.portefeuilleId, scope.siteId]);

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

  /** orgSites — all sites for the current org, without siteId filter (used by site picker) */
  const orgSites = useMemo(() => {
    if (apiSites.length > 0) return apiSites;
    // Only use mock fallback when no real org is configured (offline/pre-demo)
    if (effectiveOrgId) return []; // real org loading → return [] to avoid stale mock count
    return mockSites.slice(0, 10).filter((s) => {
      const pfId = sitePortefeuille(s);
      const pf = MOCK_PORTEFEUILLES.find((p) => p.id === pfId);
      return pf && pf.org_id === 1; // offline sample
    });
  }, [apiSites, effectiveOrgId]);

  /** sitesCount — total sites for current org (from API or mock fallback) */
  const sitesCount = orgSites.length;

  const value = {
    scope: { ...scope, orgId: effectiveOrgId },
    org, portefeuille, portefeuilles, scopedSites, orgSites,
    orgs: orgsData,
    sitesCount,
    sitesLoading, // V18: exposed for pages to show skeleton during fetch
    sitesError,   // V19: error message when getSites fails
    refreshSites, // V19: trigger re-fetch without full page reload
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
