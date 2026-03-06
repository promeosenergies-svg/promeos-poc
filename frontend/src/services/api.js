/**
 * PROMEOS - Service API
 * Gestion des appels vers le backend FastAPI
 */
import axios from 'axios';
import { logger } from './logger';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ── GET dedup + short-lived cache ────────────────────────────────────────
// Eliminates duplicate concurrent GET requests (React StrictMode double-mount)
// and caches responses for a short TTL (tab switching in Expert mode).
const _getCache = new Map();
const GET_CACHE_TTL_MS = 5000; // 5 seconds

function _cacheKey(url, params) {
  if (!params || Object.keys(params).length === 0) return url;
  const sorted = JSON.stringify(params, Object.keys(params).sort());
  return `${url}|${sorted}`;
}

/**
 * Cached GET — deduplicates in-flight requests and caches responses.
 * - Same request in-flight → returns same Promise (no duplicate network call)
 * - Same request completed within TTL → returns cached data
 * - Otherwise → fresh fetch
 * @param {string} url
 * @param {object} [config] — axios config (params, headers, etc.)
 * @returns {Promise<import('axios').AxiosResponse>}
 */
function _cachedGet(url, config = {}) {
  const key = _cacheKey(url, config.params);
  const now = Date.now();
  const entry = _getCache.get(key);

  if (entry) {
    if (entry.inflight) return entry.promise; // dedup in-flight
    if (now - entry.ts < GET_CACHE_TTL_MS) {
      // cache hit
      return Promise.resolve({ data: entry.data, status: 200, _cached: true });
    }
  }

  const promise = api
    .get(url, config)
    .then((response) => {
      _getCache.set(key, { data: response.data, ts: Date.now(), inflight: false });
      return response;
    })
    .catch((err) => {
      _getCache.delete(key);
      throw err;
    });

  _getCache.set(key, { promise, inflight: true });
  return promise;
}

/** Clear the GET cache (for tests or after mutations). */
export function clearApiCache() {
  _getCache.clear();
}

/** @returns {number} Current cache size (for DevPanel / tests). */
export function getApiCacheSize() {
  return _getCache.size;
}

// Periodic cleanup of expired entries
if (typeof setInterval !== 'undefined') {
  setInterval(() => {
    const now = Date.now();
    for (const [key, entry] of _getCache) {
      if (!entry.inflight && now - entry.ts > GET_CACHE_TTL_MS) _getCache.delete(key);
    }
  }, GET_CACHE_TTL_MS * 2);
}

// ── Request tracing (ring buffer for DevPanel) ──────────────────────────
let _lastRequests = [];
const MAX_REQUESTS = 20;

function genRequestId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}

/** @returns {Array} Last 20 API requests for DevPanel */
export function getLastRequests() {
  return _lastRequests;
}

// ── Scope state (module-level, updated by ScopeContext) ──────────────────
// Holds the current org/site scope for injection into API headers.
let _apiScope = { orgId: null, siteId: null };

/**
 * setApiScope — called by ScopeContext on every scope change (and on boot).
 * Enables all API requests to carry X-Org-Id / X-Site-Id without prop drilling.
 * @param {{ orgId: number|null, siteId: number|null }} scope
 */
export function setApiScope({ orgId = null, siteId = null } = {}) {
  _apiScope = { orgId: orgId ?? null, siteId: siteId ?? null };
}

// Auth + Scope + Request-Id interceptor
// NOTE: demo paths (/demo/*) are scope-exempt — we NEVER inject org/site headers there.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('promeos_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;

  // Request tracing
  config._requestId = genRequestId();
  config._startTime = Date.now();
  config.headers['X-Request-Id'] = config._requestId;

  // Scope injection: skip /demo/* endpoints and skipSiteHeader requests
  if (!isDemoPath(config.url)) {
    if (_apiScope.orgId != null) {
      config.headers['X-Org-Id'] = String(_apiScope.orgId);
    }
    if (_apiScope.siteId != null && !config.skipSiteHeader) {
      config.headers['X-Site-Id'] = String(_apiScope.siteId);
    }
  }
  return config;
});

// Silent URL patterns — passive checks that should never trigger toasts
const SILENT_URLS = ['/demo/status-pack'];

/**
 * Demo-path guard: /demo/* endpoints must NEVER receive scope injection
 * (org_id / site_id headers or query params) from a request interceptor.
 * If a scope interceptor is ever added, it MUST call isDemoPath() first.
 *
 * @param {string} url — raw URL string or path (with or without baseURL prefix)
 * @returns {boolean}
 */
export function isDemoPath(url) {
  if (!url) return false;
  // Strip protocol + host + query string to get bare path
  let path = url;
  try {
    if (/^https?:\/\//i.test(url)) path = new URL(url).pathname;
  } catch {
    /* keep as-is */
  }
  path = path.split('?')[0].split('#')[0];
  // Match /demo/* or /api/demo/*
  return /\/demo\//.test(path);
}

/**
 * Normalize an Axios config into a clean pathname for matching.
 * Handles: baseURL+url join, absolute URLs, querystring/hash, missing slash.
 */
export function normalizePathFromAxiosConfig(config) {
  if (!config) return '';
  let raw = config.url || '';
  // Join baseURL + url if url is relative
  if (raw && !/^https?:\/\//i.test(raw) && config.baseURL) {
    const base = config.baseURL.replace(/\/+$/, '');
    raw = base + (raw.startsWith('/') ? raw : '/' + raw);
  }
  // Strip protocol + host for absolute URLs
  try {
    if (/^https?:\/\//i.test(raw)) {
      raw = new URL(raw).pathname;
    }
  } catch {
    /* keep raw as-is */
  }
  // Strip querystring and hash
  raw = raw.split('?')[0].split('#')[0];
  // Ensure leading slash
  if (raw && !raw.startsWith('/')) raw = '/' + raw;
  return raw;
}

export const isSilentUrl = (urlOrConfig) => {
  // Accept either a string (legacy) or an axios config object
  const path =
    typeof urlOrConfig === 'object' && urlOrConfig !== null
      ? normalizePathFromAxiosConfig(urlOrConfig)
      : String(urlOrConfig || '');
  return SILENT_URLS.some(
    (u) => path.endsWith(u) || path.includes(u + '?') || path.includes(u + '#') || path === u
  );
};

api.interceptors.response.use(
  (response) => {
    // Guard: detect non-JSON responses (HTML from missing proxy / wrong prefix)
    const ct = response.headers?.['content-type'] || '';
    if (
      ct &&
      !ct.includes('application/json') &&
      !ct.includes('text/plain') &&
      response.config.responseType !== 'blob'
    ) {
      const msg = `[PROMEOS] API returned non-JSON (content-type: ${ct}). Vérifiez le proxy Vite ou le préfixe /api.`;
      console.error(msg, { url: response.config.url, status: response.status });
      return Promise.reject(new Error(msg));
    }

    // Track successful request
    const duration = Date.now() - (response.config._startTime || Date.now());
    const entry = {
      id: response.config._requestId,
      url: response.config.url,
      method: response.config.method?.toUpperCase(),
      status: response.status,
      duration,
      ts: Date.now(),
    };
    _lastRequests = [..._lastRequests, entry].slice(-MAX_REQUESTS);

    // Structured DEV logging: page, orgId, endpoint, ms
    if (import.meta.env.DEV) {
      console.log(
        `%c[API] %c${entry.method} %c${entry.url} %c${entry.status} %c${duration}ms`,
        'color:#6b7280',
        'color:#2563eb',
        'color:#059669',
        'color:#6b7280',
        duration > 300 ? 'color:#ef4444;font-weight:bold' : 'color:#6b7280',
        {
          page: window.location.pathname,
          orgId: _apiScope.orgId,
          endpoint: entry.url,
          ms: duration,
          requestId: entry.id,
        }
      );
    }

    return response;
  },
  (error) => {
    const cfg = error.config || {};
    const isSilent = cfg.silent || isSilentUrl(cfg);

    // Track failed request
    const duration = Date.now() - (cfg._startTime || Date.now());
    const errEntry = {
      id: cfg._requestId,
      url: cfg.url,
      method: cfg.method?.toUpperCase(),
      status: error.response?.status || 0,
      duration,
      ts: Date.now(),
      error: true,
    };
    _lastRequests = [..._lastRequests, errEntry].slice(-MAX_REQUESTS);

    if (!isSilent) {
      logger.warn('API', `${cfg.method?.toUpperCase() || '?'} ${cfg.url || '?'} failed`, {
        page: window.location.pathname,
        orgId: _apiScope.orgId,
        endpoint: cfg.url,
        ms: duration,
        status: error.response?.status,
        requestId: cfg._requestId,
      });
    }

    if (!isSilent && error.response?.status === 401 && !cfg.url?.includes('/auth/')) {
      localStorage.removeItem('promeos_token');
      if (window.location.pathname !== '/login') {
        window.location.assign('/login');
      }
    }
    // Mark error as silent so downstream handlers can skip toasting
    if (isSilent) error._silent = true;
    return Promise.reject(error);
  }
);

// ========================================
// SITES
// ========================================

export const getSites = async (params = {}) => {
  const response = await _cachedGet('/sites', { params });
  return response.data;
};

export const getSite = async (id) => {
  const response = await api.get(`/sites/${id}`);
  return response.data;
};

export const getSiteStats = async (id) => {
  const response = await api.get(`/sites/${id}/stats`);
  return response.data;
};

// ========================================
// COMPTEURS
// ========================================

export const getCompteurs = async (params = {}) => {
  const response = await api.get('/compteurs', { params });
  return response.data;
};

export const getCompteur = async (id) => {
  const response = await api.get(`/compteurs/${id}`);
  return response.data;
};

// ========================================
// CONSOMMATIONS
// ========================================

export const getConsommations = async (params = {}) => {
  const response = await api.get('/consommations', { params });
  return response.data;
};

// ========================================
// ALERTES
// ========================================

export const getAlertes = async (params = {}) => {
  const response = await api.get('/alertes', { params });
  return response.data;
};

export const getAlerte = async (id) => {
  const response = await api.get(`/alertes/${id}`);
  return response.data;
};

export const resolveAlerte = async (id) => {
  const response = await api.patch(`/alertes/${id}/resolve`);
  return response.data;
};

// ========================================
// DEMO MODE
// ========================================

export const getDemoStatus = () => api.get('/demo/status').then((r) => r.data);
export const enableDemo = () => api.post('/demo/enable').then((r) => r.data);
export const disableDemo = () => api.post('/demo/disable').then((r) => r.data);
export const getDemoTemplates = () => api.get('/demo/templates').then((r) => r.data);
export const getDemoPacks = () => api.get('/demo/packs').then((r) => r.data);
export const seedDemoPack = (pack, size, reset = false) =>
  api.post('/demo/seed-pack', { pack, size, reset, rng_seed: 42 }).then((r) => r.data);
export const getDemoPackStatus = () =>
  api.get('/demo/status-pack', { silent: true }).then((r) => r.data);
export const resetDemoPack = (mode = 'soft', confirm = false) =>
  api.post('/demo/reset-pack', { mode, confirm }).then((r) => r.data);
export const getDemoManifest = () =>
  api.get('/demo/manifest', { silent: true }).then((r) => r.data);

// ========================================
// GUIDANCE (Action Plan + Readiness)
// ========================================

export const getActionPlan = (params = {}) =>
  api.get('/guidance/action-plan', { params }).then((r) => r.data);
export const getReadiness = () => api.get('/guidance/readiness').then((r) => r.data);

// ========================================
// GUARDRAILS
// ========================================

export const getSiteGuardrails = (id) => api.get(`/sites/${id}/guardrails`).then((r) => r.data);

// ========================================
// REGOPS
// ========================================

export const getRegOpsAssessment = (siteId) =>
  api.get(`/regops/site/${siteId}`).then((r) => r.data);
export const getRegOpsCached = (siteId) =>
  api.get(`/regops/site/${siteId}/cached`).then((r) => r.data);
export const recomputeRegOps = (params = {}) =>
  api.post('/regops/recompute', null, { params }).then((r) => r.data);
export const getRegOpsDashboard = () => api.get('/regops/dashboard').then((r) => r.data);
export const getScoreExplain = (scopeType, scopeId) =>
  api
    .get('/regops/score_explain', { params: { scope_type: scopeType, scope_id: scopeId } })
    .then((r) => r.data);
export const getDataQuality = (scopeType, scopeId) =>
  api
    .get('/regops/data_quality', { params: { scope_type: scopeType, scope_id: scopeId } })
    .then((r) => r.data);
export const getDataQualitySpecs = () => api.get('/regops/data_quality/specs').then((r) => r.data);

// ========================================
// CONNECTORS
// ========================================

export const listConnectors = () => api.get('/connectors/list').then((r) => r.data);
export const testConnector = (name) => api.post(`/connectors/${name}/test`).then((r) => r.data);
export const syncConnector = (name, objectType, objectId) =>
  api
    .post(`/connectors/${name}/sync`, null, {
      params: { object_type: objectType, object_id: objectId },
    })
    .then((r) => r.data);

// ========================================
// WATCHERS
// ========================================

export const listWatchers = () => api.get('/watchers/list').then((r) => r.data);
export const runWatcher = (name) => api.post(`/watchers/${name}/run`).then((r) => r.data);
export const listRegEvents = (source = null, reviewed = null, status = null) =>
  api.get('/watchers/events', { params: { source, reviewed, status } }).then((r) => r.data);
export const reviewRegEvent = (eventId, decision = 'apply', notes = '') =>
  api.patch(`/watchers/events/${eventId}/review`, { decision, notes }).then((r) => r.data);
export const getRegEventDetail = (eventId) =>
  api.get(`/watchers/events/${eventId}`).then((r) => r.data);

// ========================================
// AI AGENTS
// ========================================

export const getAiExplanation = (siteId) =>
  api.get(`/ai/site/${siteId}/explain`).then((r) => r.data);
export const getAiRecommendations = (siteId) =>
  api.get(`/ai/site/${siteId}/recommend`).then((r) => r.data);
export const getAiDataQuality = (siteId) =>
  api.get(`/ai/site/${siteId}/data-quality`).then((r) => r.data);
export const getAiExecBrief = (orgId = null) =>
  api.get('/ai/org/brief', { params: orgId ? { org_id: orgId } : {} }).then((r) => r.data);
export const listAiInsights = (params = {}) =>
  api.get('/ai/insights', { params }).then((r) => r.data);

// ========================================
// KB USAGES (Knowledge Base)
// ========================================

const KB_BASE = '/kb';

export const pingKB = () => api.get(`${KB_BASE}/ping`).then((r) => r.data);
export const getKBArchetypes = () => api.get(`${KB_BASE}/archetypes`).then((r) => r.data);
export const getKBArchetype = (code) =>
  api.get(`${KB_BASE}/archetypes/${code}`).then((r) => r.data);
export const getKBArchetypeByNaf = (naf) =>
  api.get(`${KB_BASE}/archetypes/by-naf/${naf}`).then((r) => r.data);
export const getKBRules = () => api.get(`${KB_BASE}/rules`).then((r) => r.data);
export const getKBRecommendations = () => api.get(`${KB_BASE}/recommendations`).then((r) => r.data);
export const searchKB = (q, type = null) =>
  api.get(`${KB_BASE}/search`, { params: { q, type } }).then((r) => r.data);
export const getKBProvenance = (itemType, code) =>
  api.get(`${KB_BASE}/provenance/${itemType}/${code}`).then((r) => r.data);
export const getKBStats = () => api.get(`${KB_BASE}/usages-stats`).then((r) => r.data);
export const reloadKB = () => api.post(`${KB_BASE}/reload`).then((r) => r.data);
export const seedDemoKB = () => api.post(`${KB_BASE}/seed_demo`).then((r) => r.data);

// KB Explorer (structured KB system - FTS5 search + apply engine)
export const getKBItemsList = (params = {}) =>
  api.get(`${KB_BASE}/items`, { params }).then((r) => r.data);
export const getKBItemDetail = (itemId) =>
  api.get(`${KB_BASE}/items/${itemId}`).then((r) => r.data);
export const searchKBItems = (body) => api.post(`${KB_BASE}/search`, body).then((r) => r.data);
export const applyKB = (body) => api.post(`${KB_BASE}/apply`, body).then((r) => r.data);
export const getKBFullStats = () =>
  api.get(`${KB_BASE}/stats`).then((r) => {
    const d = r.data;
    // app/kb/router.py returns { kb: { total_items, by_status, by_domain, ... }, index: {...} }
    // Normalize to flat shape expected by KBExplorerPage (stats.total_items, stats.by_status, ...)
    return d && d.kb ? { ...d.kb } : d;
  });

// KB Memobox V38 — Upload + Lifecycle
export const uploadKBDoc = (file, title, domain = null, docType = 'pdf', actionId = null) => {
  const fd = new FormData();
  fd.append('file', file);
  const params = { title };
  if (domain) params.domain = domain;
  if (docType) params.doc_type = docType;
  if (actionId) params.action_id = actionId; // V48: auto-link to action
  return api
    .post(`${KB_BASE}/upload`, fd, {
      params,
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data);
};
export const changeKBDocStatus = (docId, status) =>
  api.post(`${KB_BASE}/docs/${docId}/status`, { status }).then((r) => r.data);
export const getKBDocs = (params = {}) =>
  api.get(`${KB_BASE}/docs`, { params }).then((r) => r.data);

// ========================================
// ENERGY (Import & Analysis)
// ========================================

export const getMeters = (siteId = null) =>
  api.get('/energy/meters', { params: { site_id: siteId } }).then((r) => r.data);
export const createMeter = (data) => api.post('/energy/meters', data).then((r) => r.data);
export const uploadConsumptionData = (file, meterId, frequency = 'hourly') => {
  const formData = new FormData();
  formData.append('file', file);
  return api
    .post('/energy/import/upload', formData, {
      params: { meter_id: meterId, frequency },
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data);
};
export const getImportJobs = (meterId = null) =>
  api.get('/energy/import/jobs', { params: { meter_id: meterId } }).then((r) => r.data);
export const runAnalysis = (meterId) =>
  api.post('/energy/analysis/run', null, { params: { meter_id: meterId } }).then((r) => r.data);
export const getAnalysisSummary = (meterId) =>
  api.get('/energy/analysis/summary', { params: { meter_id: meterId } }).then((r) => r.data);
export const generateDemoEnergy = (data) =>
  api.post('/energy/demo/generate', data).then((r) => r.data);

// ========================================
// ONBOARDING
// ========================================

export const createOnboarding = (data) => api.post('/onboarding', data).then((r) => r.data);
export const importSitesCsv = (file) => {
  const fd = new FormData();
  fd.append('file', file);
  return api
    .post('/onboarding/import-csv', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data);
};
export const getOnboardingStatus = () => api.get('/onboarding/status').then((r) => r.data);

// ========================================
// IMPORT STANDALONE
// ========================================

export const importSitesStandalone = (file) => {
  const fd = new FormData();
  fd.append('file', file);
  return api
    .post('/import/sites', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data);
};
export const getImportTemplate = () => api.get('/import/template').then((r) => r.data);

// ========================================
// DEMO SEED
// ========================================

export const seedDemo = () => api.post('/demo/seed').then((r) => r.data);

// ========================================
// CRUD (Sites + Compteurs)
// ========================================

export const createSite = (data) => api.post('/sites', data).then((r) => r.data);
export const createCompteur = (data) => api.post('/compteurs', data).then((r) => r.data);

// ========================================
// DASHBOARD 2 MINUTES
// ========================================

export const getDashboard2min = () => api.get('/dashboard/2min').then((r) => r.data);

// ========================================
// SEGMENTATION
// ========================================

export const getSegmentationQuestions = () =>
  api.get('/segmentation/questions').then((r) => r.data);
export const submitSegmentationAnswers = (answers) =>
  api.post('/segmentation/answers', { answers }).then((r) => r.data);
export const getSegmentationProfile = () => api.get('/segmentation/profile').then((r) => r.data);
export const recomputeSegmentation = () => api.post('/segmentation/recompute').then((r) => r.data);

// V101: Next Best Step + Action Creation
export const getSegmentationNextStep = (portfolioId) =>
  api.get('/segmentation/next-step', { params: { portfolio_id: portfolioId } }).then((r) => r.data);
export const createActionFromRecommendation = (recommendationKey, portfolioId) =>
  api
    .post('/segmentation/actions/from-recommendation', {
      recommendation_key: recommendationKey,
      portfolio_id: portfolioId,
    })
    .then((r) => r.data);
export const createActionFromNextStep = (portfolioId) =>
  api
    .post('/segmentation/actions/from-next-step', { portfolio_id: portfolioId })
    .then((r) => r.data);

// ========================================
// COMPLIANCE (Rules-based)
// ========================================

export const getComplianceSummary = (params = {}) =>
  api.get('/compliance/summary', { params }).then((r) => r.data);
export const getComplianceSites = (params = {}) =>
  api.get('/compliance/sites', { params }).then((r) => r.data);
export const getComplianceBundle = (params = {}) =>
  _cachedGet('/compliance/bundle', { params }).then((r) => r.data);
export const recomputeComplianceRules = (orgId = null) =>
  api.post('/compliance/recompute-rules', null, { params: { org_id: orgId } }).then((r) => r.data);
export const getComplianceRules = () => api.get('/compliance/rules').then((r) => r.data);

// Sprint 9: Compliance OPS workflow
export const getComplianceFindings = (params = {}) =>
  api.get('/compliance/findings', { params }).then((r) => r.data);
export const patchComplianceFinding = (id, data) =>
  api.patch(`/compliance/findings/${id}`, data).then((r) => r.data);
export const getComplianceBatches = (orgId = null) =>
  api.get('/compliance/batches', { params: { org_id: orgId } }).then((r) => r.data);
export const getFindingDetail = (findingId) =>
  api.get(`/compliance/findings/${findingId}`).then((r) => r.data);

// V68: Compliance Pipeline summaries
export const getSiteComplianceSummary = (siteId) =>
  api.get(`/compliance/sites/${siteId}/summary`).then((r) => r.data);
export const getPortfolioComplianceSummary = (params = {}) =>
  api.get('/compliance/portfolio/summary', { params }).then((r) => r.data);

// V69: CEE Pipeline + M&V
export const getSiteWorkPackages = (siteId) =>
  api.get(`/compliance/sites/${siteId}/packages`).then((r) => r.data);
export const createWorkPackage = (siteId, data) =>
  api.post(`/compliance/sites/${siteId}/packages`, data).then((r) => r.data);
export const createCeeDossier = (siteId, workPackageId) =>
  api
    .post(`/compliance/sites/${siteId}/cee/dossier`, null, {
      params: { work_package_id: workPackageId },
    })
    .then((r) => r.data);
export const advanceCeeStep = (dossierId, step) =>
  api.patch(`/compliance/cee/dossier/${dossierId}/step`, { step }).then((r) => r.data);
export const getMvSummary = (siteId) =>
  api.get(`/compliance/sites/${siteId}/mv/summary`).then((r) => r.data);

// Dev Tools
export const resetDb = () => api.post('/dev/reset_db').then((r) => r.data);

// Health
export const getApiHealth = () => api.get('/health').then((r) => r.data);

// ========================================
// CONSUMPTION DIAGNOSTIC
// ========================================

export const getConsumptionInsights = (orgId = null) =>
  api.get('/consumption/insights', { params: { org_id: orgId } }).then((r) => r.data);
export const getConsumptionSite = (siteId) =>
  api.get(`/consumption/site/${siteId}`).then((r) => r.data);
export const runConsumptionDiagnose = (orgId = null, days = 30) =>
  api.post('/consumption/diagnose', null, { params: { org_id: orgId, days } }).then((r) => r.data);
export const seedDemoConsumption = (siteId = null, days = 30) =>
  api
    .post('/consumption/seed-demo', null, { params: { site_id: siteId, days } })
    .then((r) => r.data);
export const patchConsumptionInsight = (insightId, data) =>
  api.patch(`/consumption/insights/${insightId}`, data).then((r) => r.data);

// ========================================
// FLEX MINI
// ========================================
export const getFlexMini = (siteId, start, end) =>
  api.get(`/sites/${siteId}/flex/mini`, { params: { start, end } }).then((r) => r.data);

// ========================================
// CONSUMPTION EXPLORER (V10 World-Class)
// ========================================

// Availability check (V10.1 handshake)
export const getConsumptionAvailability = (siteId, energyType = 'electricity') =>
  _cachedGet('/consumption/availability', {
    params: { site_id: siteId, energy_type: energyType },
  }).then((r) => r.data);

// Tunnel (envelope P10-P90)
export const getConsumptionTunnel = (siteId, days = 90, energyType = 'electricity') =>
  api
    .get('/consumption/tunnel', { params: { site_id: siteId, days, energy_type: energyType } })
    .then((r) => r.data);
export const getConsumptionTunnelV2 = (
  siteId,
  days = 90,
  energyType = 'electricity',
  mode = 'energy'
) =>
  _cachedGet('/consumption/tunnel_v2', {
    params: { site_id: siteId, days, energy_type: energyType, mode },
  }).then((r) => r.data);

// Targets (objectifs & budgets)
export const getConsumptionTargets = (siteId, energyType = 'electricity', year = null) =>
  _cachedGet('/consumption/targets', {
    params: { site_id: siteId, energy_type: energyType, year },
  }).then((r) => r.data);
export const createConsumptionTarget = (data) =>
  api.post('/consumption/targets', data).then((r) => r.data);
export const patchConsumptionTarget = (id, data) =>
  api.patch(`/consumption/targets/${id}`, data).then((r) => r.data);
export const deleteConsumptionTarget = (id) =>
  api.delete(`/consumption/targets/${id}`).then((r) => r.data);
export const getTargetsProgression = (siteId, energyType = 'electricity', year = null) =>
  api
    .get('/consumption/targets/progression', {
      params: { site_id: siteId, energy_type: energyType, year },
    })
    .then((r) => r.data);
export const getTargetsProgressionV2 = (siteId, energyType = 'electricity', year = null) =>
  _cachedGet('/consumption/targets/progress_v2', {
    params: { site_id: siteId, energy_type: energyType, year },
  }).then((r) => r.data);

// TOU Schedules (grilles HP/HC)
export const getTOUSchedules = (siteId, meterId = null, activeOnly = true) =>
  api
    .get('/consumption/tou_schedules', {
      params: { site_id: siteId, meter_id: meterId, active_only: activeOnly },
    })
    .then((r) => r.data);
export const getActiveTOUSchedule = (siteId, meterId = null, refDate = null) =>
  api
    .get('/consumption/tou_schedules/active', {
      params: { site_id: siteId, meter_id: meterId, ref_date: refDate },
    })
    .then((r) => r.data);
export const createTOUSchedule = (data) =>
  api.post('/consumption/tou_schedules', data).then((r) => r.data);
export const patchTOUSchedule = (id, data) =>
  api.patch(`/consumption/tou_schedules/${id}`, data).then((r) => r.data);
export const deleteTOUSchedule = (id) =>
  api.delete(`/consumption/tou_schedules/${id}`).then((r) => r.data);

// HP/HC Ratio
export const getHPHCRatio = (siteId, meterId = null, days = 30) =>
  api
    .get('/consumption/hp_hc', { params: { site_id: siteId, meter_id: meterId, days } })
    .then((r) => r.data);
export const getHPHCBreakdownV2 = (siteId, days = 30, calendarId = null, simulate = false) =>
  _cachedGet('/consumption/hphc_breakdown_v2', {
    params: { site_id: siteId, days, calendar_id: calendarId, simulate },
  }).then((r) => r.data);

// Gas Summary (beta)
export const getGasSummary = (siteId, days = 90) =>
  _cachedGet('/consumption/gas/summary', { params: { site_id: siteId, days } }).then((r) => r.data);
export const getGasWeatherNormalized = (siteId, days = 90) =>
  _cachedGet('/consumption/gas/weather_normalized', { params: { site_id: siteId, days } }).then(
    (r) => r.data
  );

// ========================================
// SITE CONFIG (Schedule + Tariff)
// ========================================

export const getSiteSchedule = (siteId) => api.get(`/site/${siteId}/schedule`).then((r) => r.data);
export const putSiteSchedule = (siteId, data) =>
  api.put(`/site/${siteId}/schedule`, data).then((r) => r.data);
export const getSiteTariff = (siteId) => api.get(`/site/${siteId}/tariff`).then((r) => r.data);
export const putSiteTariff = (siteId, data) =>
  api.put(`/site/${siteId}/tariff`, data).then((r) => r.data);

// ========================================
// BILL INTELLIGENCE
// ========================================

export const getBillingSummary = () => api.get('/billing/summary').then((r) => r.data);
export const getBillingInsights = (params = {}) =>
  api.get('/billing/insights', { params }).then((r) => r.data);
export const getInsightDetail = (insightId) =>
  api.get(`/billing/insights/${insightId}`).then((r) => r.data);
export const getBillingInvoices = (params = {}) =>
  api.get('/billing/invoices', { params }).then((r) => r.data);
export const getSiteBilling = (siteId) => api.get(`/billing/site/${siteId}`).then((r) => r.data);
export const getBillingRules = () => api.get('/billing/rules').then((r) => r.data);
export const auditInvoice = (invoiceId) =>
  api.post(`/billing/audit/${invoiceId}`).then((r) => r.data);
export const auditAllInvoices = () => api.post('/billing/audit-all').then((r) => r.data);
export const seedBillingDemo = () => api.post('/billing/seed-demo').then((r) => r.data);
export const importInvoicesCsv = (file) => {
  const fd = new FormData();
  fd.append('file', file);
  return api
    .post('/billing/import-csv', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data);
};
export const patchBillingInsight = (insightId, data) =>
  api.patch(`/billing/insights/${insightId}`, data).then((r) => r.data);
export const resolveBillingInsight = (insightId, notes = null) =>
  api
    .post(`/billing/insights/${insightId}/resolve`, null, { params: notes ? { notes } : {} })
    .then((r) => r.data);
export const getImportBatches = (params = {}) =>
  api.get('/billing/import/batches', { params }).then((r) => r.data);

// V66 — PDF import + action creation + billing anomalies
export const importInvoicesPdf = (siteId, file) => {
  const fd = new FormData();
  fd.append('file', file);
  return api
    .post('/billing/import-pdf', fd, {
      params: { site_id: siteId },
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data);
};

export const createActionFromBillingInsight = (insightId, title, siteId) =>
  api
    .post('/actions', {
      source_type: 'manual',
      source_id: String(insightId),
      source_key: `billing-insight:${insightId}`,
      idempotency_key: `billing-insight:${insightId}`,
      title,
      site_id: siteId,
    })
    .then((r) => r.data);

export const getBillingAnomaliesScoped = () =>
  api.get('/billing/anomalies-scoped').then((r) => r.data);

/* ── V67 — Timeline & Coverage ── */
export const getBillingPeriods = (params = {}) =>
  api.get('/billing/periods', { params }).then((r) => r.data);

export const getCoverageSummary = (params = {}) =>
  api.get('/billing/coverage-summary', { params }).then((r) => r.data);

export const getMissingPeriods = (params = {}) =>
  api.get('/billing/missing-periods', { params }).then((r) => r.data);

export const getNormalizedInvoices = (params = {}) =>
  api.get('/billing/invoices/normalized', { params }).then((r) => r.data);

// ========================================
// ACHAT ENERGIE
// ========================================

export const getPurchaseEstimate = (siteId) =>
  api.get(`/purchase/estimate/${siteId}`).then((r) => r.data);
export const getPurchaseAssumptions = (siteId) =>
  api.get(`/purchase/assumptions/${siteId}`).then((r) => r.data);
export const putPurchaseAssumptions = (siteId, data) =>
  api.put(`/purchase/assumptions/${siteId}`, data).then((r) => r.data);
export const getPurchasePreferences = (params = {}) =>
  api.get('/purchase/preferences', { params }).then((r) => r.data);
export const putPurchasePreferences = (data) =>
  api.put('/purchase/preferences', data).then((r) => r.data);
export const computePurchaseScenarios = (siteId, { report_pct } = {}) =>
  api
    .post(`/purchase/compute/${siteId}`, null, { params: report_pct != null ? { report_pct } : {} })
    .then((r) => r.data);
export const getPurchaseResults = (siteId) =>
  api.get(`/purchase/results/${siteId}`).then((r) => r.data);
export const acceptPurchaseResult = (resultId) =>
  api.patch(`/purchase/results/${resultId}/accept`).then((r) => r.data);
export const seedPurchaseDemo = () => api.post('/purchase/seed-demo').then((r) => r.data);

// Brique 3: Assistant wizard data
export const getPurchaseAssistantData = (orgId = null) =>
  _cachedGet('/purchase/assistant', { params: orgId ? { org_id: orgId } : {} }).then((r) => r.data);

// Brique 3: WOW multi-site datasets
export const seedWowHappy = () => api.post('/purchase/seed-wow-happy').then((r) => r.data);
export const seedWowDirty = () => api.post('/purchase/seed-wow-dirty').then((r) => r.data);

// Sprint 8.1: Portfolio, Renewals, History, Actions
// skipSiteHeader: portfolio = multi-sites, never filter by single site scope
export const computePortfolio = (orgId) =>
  api
    .post('/purchase/compute', null, {
      params: { org_id: orgId, scope: 'org' },
      skipSiteHeader: true,
    })
    .then((r) => r.data);
export const getPortfolioResults = (orgId) =>
  api
    .get('/purchase/results', { params: { org_id: orgId }, skipSiteHeader: true })
    .then((r) => r.data);
export const getPurchaseRenewals = (orgId = null) =>
  api
    .get('/purchase/renewals', { params: orgId ? { org_id: orgId } : {}, skipSiteHeader: true })
    .then((r) => r.data);
export const getPurchaseHistory = (siteId) =>
  api.get(`/purchase/history/${siteId}`).then((r) => r.data);
export const getPurchaseActions = (orgId = null) =>
  api.get('/purchase/actions', { params: orgId ? { org_id: orgId } : {} }).then((r) => r.data);

// ========================================
// ACTION HUB (Sprint 10)
// ========================================

export const createAction = (data) => api.post('/actions', data).then((r) => r.data);
export const syncActions = (orgId = null) =>
  api.post('/actions/sync', null, { params: orgId ? { org_id: orgId } : {} }).then((r) => r.data);
export const getActionsList = (params = {}) =>
  _cachedGet('/actions/list', { params }).then((r) => r.data);
export const getActionsSummary = (orgId = null, siteId = null) => {
  const params = {};
  if (orgId) params.org_id = orgId;
  if (siteId) params.site_id = siteId;
  return _cachedGet('/actions/summary', { params }).then((r) => r.data);
};
export const patchAction = (id, data) => api.patch(`/actions/${id}`, data).then((r) => r.data);
export const getActionBatches = (orgId = null) =>
  api.get('/actions/batches', { params: orgId ? { org_id: orgId } : {} }).then((r) => r.data);
export const exportActionsCSV = (params = {}) =>
  api.get('/actions/export.csv', { params, responseType: 'blob' });

// Action Detail + Sub-resources (V5.0)
export const getActionDetail = (id) => api.get(`/actions/${id}`).then((r) => r.data);
export const getActionComments = (id) => api.get(`/actions/${id}/comments`).then((r) => r.data);
export const addActionComment = (id, data) =>
  api.post(`/actions/${id}/comments`, data).then((r) => r.data);
export const getActionEvidence = (id) => api.get(`/actions/${id}/evidence`).then((r) => r.data);
export const addActionEvidence = (id, data) =>
  api.post(`/actions/${id}/evidence`, data).then((r) => r.data);
export const getActionEvents = (id) => api.get(`/actions/${id}/events`).then((r) => r.data);
export const getROISummary = (orgId) =>
  api.get('/actions/roi_summary', { params: orgId ? { org_id: orgId } : {} }).then((r) => r.data);

// V48: Action ↔ Proof persistence
export const getActionProofs = (actionId) =>
  api.get(`/actions/${actionId}/proofs`).then((r) => r.data);
export const linkProofToAction = (actionId, kbDocId) =>
  api.post(`/actions/${actionId}/proofs/${kbDocId}`).then((r) => r.data);

// V117: Anomaly ↔ Action Link
export const createAnomalyActionLink = (data) =>
  api.post('/actions/anomaly-links', data).then((r) => r.data);
export const dismissAnomaly = (data) =>
  api.post('/actions/anomaly-dismiss', data).then((r) => r.data);
export const getAnomalyStatuses = (anomalies) =>
  api.post('/actions/anomaly-statuses', { anomalies }).then((r) => r.data);

// V49: Action closeability check
export const checkActionCloseability = (actionId) =>
  api.get(`/actions/${actionId}/closeability`).then((r) => r.data);

// ========================================
// REPORTS (Sprint 10.1)
// ========================================

export const getAuditReportJSON = (orgId = null) =>
  api.get('/reports/audit.json', { params: orgId ? { org_id: orgId } : {} }).then((r) => r.data);
export const downloadAuditPDF = (orgId = null) =>
  api.get('/reports/audit.pdf', { params: orgId ? { org_id: orgId } : {}, responseType: 'blob' });

// ========================================
// NOTIFICATIONS (Sprint 10.2)
// ========================================

export const syncNotifications = (orgId = null) =>
  api
    .post('/notifications/sync', null, { params: orgId ? { org_id: orgId } : {} })
    .then((r) => r.data);
export const getNotificationsList = (params = {}) =>
  api.get('/notifications/list', { params }).then((r) => r.data);
export const getNotificationsSummary = (orgId = null, siteId = null) => {
  const params = {};
  if (orgId) params.org_id = orgId;
  if (siteId) params.site_id = siteId;
  return _cachedGet('/notifications/summary', { params }).then((r) => r.data);
};
export const patchNotification = (id, data) =>
  api.patch(`/notifications/${id}`, data).then((r) => r.data);
export const getNotificationPreferences = (orgId = null) =>
  api
    .get('/notifications/preferences', { params: orgId ? { org_id: orgId } : {} })
    .then((r) => r.data);
export const putNotificationPreferences = (data, orgId = null) =>
  api
    .put('/notifications/preferences', data, { params: orgId ? { org_id: orgId } : {} })
    .then((r) => r.data);

// ========================================
// IAM — Auth (Sprint 11)
// ========================================

export const loginAuth = (email, password) =>
  api.post('/auth/login', { email, password }).then((r) => r.data);
export const refreshAuth = () => api.post('/auth/refresh').then((r) => r.data);
export const getAuthMe = () => api.get('/auth/me').then((r) => r.data);
export const logoutAuth = () => api.post('/auth/logout').then((r) => r.data);
export const changePassword = (currentPassword, newPassword) =>
  api
    .put('/auth/password', { current_password: currentPassword, new_password: newPassword })
    .then((r) => r.data);
export const switchOrg = (orgId) =>
  api.post('/auth/switch-org', { org_id: orgId }).then((r) => r.data);

// ========================================
// IAM — Admin Users (Sprint 11)
// ========================================

export const getAdminUsers = () => api.get('/admin/users').then((r) => r.data);
export const createAdminUser = (data) => api.post('/admin/users', data).then((r) => r.data);
export const getAdminUser = (id) => api.get(`/admin/users/${id}`).then((r) => r.data);
export const patchAdminUser = (id, data) =>
  api.patch(`/admin/users/${id}`, data).then((r) => r.data);
export const changeAdminRole = (id, role) =>
  api.put(`/admin/users/${id}/role`, { role }).then((r) => r.data);
export const setAdminScopes = (id, scopes) =>
  api.put(`/admin/users/${id}/scopes`, { scopes }).then((r) => r.data);
export const deleteAdminUser = (id) => api.delete(`/admin/users/${id}`).then((r) => r.data);
export const getAdminRoles = () => api.get('/admin/roles').then((r) => r.data);
export const getEffectiveAccess = (id) =>
  api.get(`/admin/users/${id}/effective-access`).then((r) => r.data);

// ========================================
// IAM — Audit Log (Sprint 11)
// ========================================

export const getAuditLogs = (params = {}) => api.get('/auth/audit', { params }).then((r) => r.data);

// ========================================
// IAM — Demo Mode (Sprint 11)
// ========================================

export const impersonateUser = (email) =>
  api.post('/auth/impersonate', { email }).then((r) => r.data);

// ========================================
// PATRIMOINE STAGING (DIAMANT)
// ========================================

export const stagingImport = (file, mode = 'import') => {
  const fd = new FormData();
  fd.append('file', file);
  return api
    .post('/patrimoine/staging/import', fd, {
      params: { mode },
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data);
};
export const stagingImportInvoices = (invoices) =>
  api.post('/patrimoine/staging/import-invoices', { invoices }).then((r) => r.data);
export const stagingSummary = (batchId) =>
  api.get(`/patrimoine/staging/${batchId}/summary`).then((r) => r.data);
export const stagingRows = (batchId, params = {}) =>
  api.get(`/patrimoine/staging/${batchId}/rows`, { params }).then((r) => r.data);
export const stagingIssues = (batchId, params = {}) =>
  api.get(`/patrimoine/staging/${batchId}/issues`, { params }).then((r) => r.data);
export const stagingValidate = (batchId) =>
  api.post(`/patrimoine/staging/${batchId}/validate`).then((r) => r.data);
export const stagingFix = (batchId, fixType, params) =>
  api.put(`/patrimoine/staging/${batchId}/fix`, { fix_type: fixType, params }).then((r) => r.data);
export const stagingFixBulk = (batchId, fixes) =>
  api.put(`/patrimoine/staging/${batchId}/fix/bulk`, { fixes }).then((r) => r.data);
export const stagingAutofix = (batchId) =>
  api.post(`/patrimoine/staging/${batchId}/autofix`).then((r) => r.data);
export const stagingActivate = (batchId, portefeuilleId) =>
  api
    .post(`/patrimoine/staging/${batchId}/activate`, { portefeuille_id: portefeuilleId })
    .then((r) => r.data);
export const stagingResult = (batchId) =>
  api.get(`/patrimoine/staging/${batchId}/result`).then((r) => r.data);
export const stagingAbandon = (batchId) =>
  api.delete(`/patrimoine/staging/${batchId}`).then((r) => r.data);
export const loadPatrimoineDemo = () => api.post('/patrimoine/demo/load').then((r) => r.data);
export const getImportTemplateColumns = () =>
  api.get('/patrimoine/import/template/columns').then((r) => r.data);
export const portfolioSync = (portfolioId, file, dryRun = true) => {
  const fd = new FormData();
  fd.append('file', file);
  return api
    .post(`/patrimoine/${portfolioId}/sync`, fd, {
      params: { dry_run: dryRun },
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data);
};
export const mappingPreview = (headers) =>
  api.post('/patrimoine/mapping/preview', { headers }).then((r) => r.data);

// PATRIMOINE CRUD (WORLD CLASS)
export const patrimoineSites = (params = {}) =>
  api.get('/patrimoine/sites', { params }).then((r) => r.data);
export const patrimoineSiteDetail = (id) => api.get(`/patrimoine/sites/${id}`).then((r) => r.data);
export const patrimoineSiteUpdate = (id, data) =>
  api.patch(`/patrimoine/sites/${id}`, data).then((r) => r.data);
export const patrimoineSiteArchive = (id) =>
  api.post(`/patrimoine/sites/${id}/archive`).then((r) => r.data);
export const patrimoineSiteRestore = (id) =>
  api.post(`/patrimoine/sites/${id}/restore`).then((r) => r.data);
export const patrimoineSiteMerge = (sourceId, targetId) =>
  api
    .post('/patrimoine/sites/merge', { source_site_id: sourceId, target_site_id: targetId })
    .then((r) => r.data);
export const patrimoineCompteurs = (params = {}) =>
  api.get('/patrimoine/compteurs', { params }).then((r) => r.data);
export const patrimoineCompteurUpdate = (id, data) =>
  api.patch(`/patrimoine/compteurs/${id}`, data).then((r) => r.data);
export const patrimoineCompteurMove = (id, targetSiteId) =>
  api
    .post(`/patrimoine/compteurs/${id}/move`, { target_site_id: targetSiteId })
    .then((r) => r.data);
export const patrimoineCompteurDetach = (id) =>
  api.post(`/patrimoine/compteurs/${id}/detach`).then((r) => r.data);
export const patrimoineContracts = (params = {}) =>
  api.get('/patrimoine/contracts', { params }).then((r) => r.data);
export const patrimoineContractCreate = (data) =>
  api.post('/patrimoine/contracts', data).then((r) => r.data);
export const patrimoineContractUpdate = (id, data) =>
  api.patch(`/patrimoine/contracts/${id}`, data).then((r) => r.data);
export const patrimoineContractDelete = (id) =>
  api.delete(`/patrimoine/contracts/${id}`).then((r) => r.data);

// Patrimoine — compléments audit V51
export const stagingExportReport = (batchId) =>
  api.get(`/patrimoine/staging/${batchId}/export/report.csv`, { responseType: 'blob' });
export const patrimoineDeliveryPoints = (siteId) =>
  api.get(`/patrimoine/sites/${siteId}/delivery-points`).then((r) => r.data);
export const patrimoineKpis = (params = {}) =>
  api.get('/patrimoine/kpis', { params }).then((r) => r.data);
export const patrimoineSitesExport = (params = {}) =>
  api.get('/patrimoine/sites/export.csv', { params, responseType: 'blob' });

// Patrimoine — V58 Snapshot & Anomalies (V59: enriched with impact)
export const getPatrimoineSnapshot = (siteId) =>
  api.get(`/patrimoine/sites/${siteId}/snapshot`).then((r) => r.data);
export const getPatrimoineAnomalies = (siteId) =>
  api.get(`/patrimoine/sites/${siteId}/anomalies`).then((r) => r.data);
export const listPatrimoineAnomalies = (params = {}) =>
  api.get('/patrimoine/anomalies', { params }).then((r) => r.data);
// V59: hypothèses de calcul en lecture seule
export const getPatrimoineAssumptions = () =>
  api.get('/patrimoine/assumptions').then((r) => r.data);
// V60: résumé portfolio — risque global, framework breakdown, top sites
export const getPatrimoinePortfolioSummary = (params = {}) =>
  _cachedGet('/patrimoine/portfolio-summary', { params }).then((r) => r.data);

// ========================================
// SMART INTAKE (DIAMANT)
// ========================================

export const getIntakeQuestions = (siteId) =>
  api.get(`/intake/${siteId}/questions`).then((r) => r.data);
export const submitIntakeAnswer = (siteId, fieldPath, value, source = 'user') =>
  api
    .post(`/intake/${siteId}/answers`, { field_path: fieldPath, value, source })
    .then((r) => r.data);
export const applyIntakeSuggestions = (siteId, fieldPaths) =>
  api.post(`/intake/${siteId}/apply-suggestions`, { field_paths: fieldPaths }).then((r) => r.data);
export const intakeDemoAutofill = (siteId) =>
  api.post(`/intake/${siteId}/demo-autofill`).then((r) => r.data);
export const completeIntake = (siteId) =>
  api.post(`/intake/${siteId}/complete`).then((r) => r.data);
export const getIntakeSession = (sessionId) =>
  api.get(`/intake/session/${sessionId}`).then((r) => r.data);
export const purgeIntakeDemo = () => api.delete('/intake/demo/purge').then((r) => r.data);

// ========================================
// MONITORING (Electric Performance)
// ========================================

export const getMonitoringKpis = (siteId) =>
  api.get('/monitoring/kpis', { params: { site_id: siteId } }).then((r) => r.data);
export const runMonitoring = (siteId, days = 90) =>
  api.post('/monitoring/run', { site_id: siteId, days }).then((r) => r.data);
export const getMonitoringSnapshots = (siteId, limit = 10) =>
  api.get('/monitoring/snapshots', { params: { site_id: siteId, limit } }).then((r) => r.data);
export const getMonitoringAlerts = (siteId, status = null, limit = 50) =>
  api.get('/monitoring/alerts', { params: { site_id: siteId, status, limit } }).then((r) => r.data);
export const ackMonitoringAlert = (id) =>
  api.post(`/monitoring/alerts/${id}/ack`, { acknowledged_by: 'user' }).then((r) => r.data);
export const resolveMonitoringAlert = (id, note = null) =>
  api
    .post(`/monitoring/alerts/${id}/resolve`, { resolved_by: 'user', resolution_note: note })
    .then((r) => r.data);
export const generateMonitoringDemo = (siteId, days = 90, profile = 'office') =>
  api.post('/monitoring/demo/generate', { site_id: siteId, days, profile }).then((r) => r.data);
export const getMonitoringKpisCompare = (
  siteId,
  mode = 'previous',
  customStart = null,
  customEnd = null
) =>
  api
    .get('/monitoring/kpis/compare', {
      params: { site_id: siteId, mode, custom_start: customStart, custom_end: customEnd },
    })
    .then((r) => r.data);

// ========================================
// Emissions / CO2e (Sprint V9 Decarbonation)
// ========================================

export const getEmissions = (siteId) =>
  api.get('/monitoring/emissions', { params: { site_id: siteId } }).then((r) => r.data);
export const getEmissionFactors = () => api.get('/monitoring/emission-factors').then((r) => r.data);
export const seedEmissionFactors = () =>
  api.post('/monitoring/emission-factors/seed').then((r) => r.data);

// ========================================
// BACS Expert (Decret n°2020-887)
// ========================================

export const getBacsAssessment = (siteId) =>
  api.get(`/regops/bacs/site/${siteId}`).then((r) => r.data);
export const recomputeBacs = (siteId) =>
  api.post(`/regops/bacs/recompute/${siteId}`).then((r) => r.data);
export const getBacsScoreExplain = (siteId) =>
  api.get(`/regops/bacs/score_explain/${siteId}`).then((r) => r.data);
export const getBacsDataQuality = (siteId) =>
  api.get(`/regops/bacs/data_quality/${siteId}`).then((r) => r.data);
export const createBacsAsset = (siteId, isTertiary = true, pcDate = null) =>
  api
    .post('/regops/bacs/asset', null, {
      params: { site_id: siteId, is_tertiary: isTertiary, pc_date: pcDate },
    })
    .then((r) => r.data);
export const addCvcSystem = (assetId, systemType, architecture, unitsJson = '[]') =>
  api
    .post(`/regops/bacs/asset/${assetId}/system`, null, {
      params: { system_type: systemType, architecture, units_json: unitsJson },
    })
    .then((r) => r.data);
export const updateCvcSystem = (systemId, unitsJson = null, architecture = null) =>
  api
    .put(`/regops/bacs/system/${systemId}`, null, {
      params: { units_json: unitsJson, architecture },
    })
    .then((r) => r.data);
export const deleteCvcSystem = (systemId) =>
  api.delete(`/regops/bacs/system/${systemId}`).then((r) => r.data);
export const seedBacsDemo = () => api.post('/regops/bacs/seed_demo').then((r) => r.data);
export const getBacsOpsPanel = (siteId) =>
  api.get(`/regops/bacs/site/${siteId}/ops`).then((r) => r.data);

// ========================================
// EMS Consumption Explorer
// ========================================

export const getEmsTimeseries = (params) =>
  _cachedGet('/ems/timeseries', { params }).then((r) => r.data);
export const getEmsTimeseriesSuggest = (dateFrom, dateTo) =>
  _cachedGet('/ems/timeseries/suggest', { params: { date_from: dateFrom, date_to: dateTo } }).then(
    (r) => r.data
  );
export const getEmsCompareSummary = (params) =>
  _cachedGet('/ems/timeseries/compare-summary', { params }).then((r) => r.data);
export const getEmsWeather = (siteId, dateFrom, dateTo) =>
  api
    .get('/ems/weather', { params: { site_id: siteId, date_from: dateFrom, date_to: dateTo } })
    .then((r) => r.data);
export const getEmsWeatherMulti = (siteIds, dateFrom, dateTo) =>
  api
    .get('/ems/weather', {
      params: { site_ids: siteIds.join(','), date_from: dateFrom, date_to: dateTo },
    })
    .then((r) => r.data);
export const getEmsReferenceProfile = (
  siteId,
  dateFrom,
  dateTo,
  famille,
  puissance,
  granularity = 'daily'
) =>
  api
    .get('/ems/reference_profile', {
      params: {
        site_id: siteId,
        date_from: dateFrom,
        date_to: dateTo,
        famille,
        puissance,
        granularity,
      },
    })
    .then((r) => r.data);
export const getEmsWeatherHourly = (siteId, dateFrom, dateTo) =>
  api
    .get('/ems/weather_hourly', {
      params: { site_id: siteId, date_from: dateFrom, date_to: dateTo },
    })
    .then((r) => r.data);
export const runEmsSignature = (siteId, dateFrom, dateTo, meterIds = null) =>
  api
    .post('/ems/signature/run', null, {
      params: { site_id: siteId, date_from: dateFrom, date_to: dateTo, meter_ids: meterIds },
    })
    .then((r) => r.data);
export const runEmsSignaturePortfolio = (siteIds, dateFrom, dateTo) =>
  api
    .post('/ems/signature/portfolio', null, {
      params: { site_ids: siteIds.join(','), date_from: dateFrom, date_to: dateTo },
    })
    .then((r) => r.data);
export const getEmsViews = (userId = null) =>
  api.get('/ems/views', { params: userId ? { user_id: userId } : {} }).then((r) => r.data);
export const createEmsView = (name, configJson, userId = null) =>
  api
    .post('/ems/views', null, { params: { name, config_json: configJson, user_id: userId } })
    .then((r) => r.data);
export const updateEmsView = (id, params) =>
  api.put(`/ems/views/${id}`, null, { params }).then((r) => r.data);
export const deleteEmsView = (id) => api.delete(`/ems/views/${id}`).then((r) => r.data);

// Collections (paniers de sites)
export const getEmsCollections = () => api.get('/ems/collections').then((r) => r.data);
export const createEmsCollection = (name, siteIds, scopeType = 'custom', isFavorite = false) =>
  api
    .post('/ems/collections', null, {
      params: { name, site_ids: siteIds.join(','), scope_type: scopeType, is_favorite: isFavorite },
    })
    .then((r) => r.data);
export const updateEmsCollection = (id, params) =>
  api.put(`/ems/collections/${id}`, null, { params }).then((r) => r.data);
export const deleteEmsCollection = (id) => api.delete(`/ems/collections/${id}`).then((r) => r.data);

// Usage suggest & benchmark
export const getUsageSuggest = (siteId) =>
  api.get('/ems/usage_suggest', { params: { site_id: siteId } }).then((r) => r.data);
export const getEmsBenchmark = (siteId) =>
  api.get('/ems/benchmark', { params: { site_id: siteId } }).then((r) => r.data);
export const getScheduleSuggest = (siteId, days = 90) =>
  api.get('/ems/schedule_suggest', { params: { site_id: siteId, days } }).then((r) => r.data);

// Demo data
export const generateEmsDemo = (portfolioSize = 12, days = 365, seed = 123, force = false) =>
  api
    .post('/ems/demo/generate', null, {
      params: { portfolio_size: portfolioSize, days, seed, force },
    })
    .then((r) => r.data);
export const purgeEmsDemo = () => api.post('/ems/demo/purge').then((r) => r.data);

// ═══════════════════════════════════════════════════════════════════════════
// Tertiaire / OPERAT V39
// ═══════════════════════════════════════════════════════════════════════════
const TERT_BASE = '/tertiaire';

export const getTertiaireEfas = (params = {}) =>
  api.get(`${TERT_BASE}/efa`, { params }).then((r) => r.data);
export const createTertiaireEfa = (body) => api.post(`${TERT_BASE}/efa`, body).then((r) => r.data);
export const getTertiaireEfa = (efaId) => api.get(`${TERT_BASE}/efa/${efaId}`).then((r) => r.data);
export const updateTertiaireEfa = (efaId, body) =>
  api.patch(`${TERT_BASE}/efa/${efaId}`, body).then((r) => r.data);
export const deleteTertiaireEfa = (efaId) =>
  api.delete(`${TERT_BASE}/efa/${efaId}`).then((r) => r.data);

export const addTertiaireBuilding = (efaId, body) =>
  api.post(`${TERT_BASE}/efa/${efaId}/buildings`, body).then((r) => r.data);
export const addTertiaireResponsibility = (efaId, body) =>
  api.post(`${TERT_BASE}/efa/${efaId}/responsibilities`, body).then((r) => r.data);
export const addTertiaireEvent = (efaId, body) =>
  api.post(`${TERT_BASE}/efa/${efaId}/events`, body).then((r) => r.data);
export const addTertiaireEfaLink = (efaId, body) =>
  api.post(`${TERT_BASE}/efa/${efaId}/links`, body).then((r) => r.data);

export const runTertiaireControls = (efaId, year = null) =>
  api
    .post(`${TERT_BASE}/efa/${efaId}/controls`, null, { params: year ? { year } : {} })
    .then((r) => r.data);
export const precheckTertiaireDeclaration = (efaId, year) =>
  api.post(`${TERT_BASE}/efa/${efaId}/precheck`, null, { params: { year } }).then((r) => r.data);
export const exportTertiairePack = (efaId, year) =>
  api.post(`${TERT_BASE}/efa/${efaId}/export-pack`, null, { params: { year } }).then((r) => r.data);

export const getTertiaireIssues = (params = {}) =>
  api.get(`${TERT_BASE}/issues`, { params }).then((r) => r.data);
export const updateTertiaireIssue = (issueId, body) =>
  api.patch(`${TERT_BASE}/issues/${issueId}`, body).then((r) => r.data);

export const getTertiaireDashboard = (params = {}) =>
  api.get(`${TERT_BASE}/dashboard`, { params }).then((r) => r.data);

// V42: Site signals for auto-qualification
export const getTertiaireSiteSignals = (params = {}) =>
  api.get(`${TERT_BASE}/site-signals`, { params }).then((r) => r.data);

// V41: Patrimoine building catalog for wizard
export const getTertiaireCatalog = (orgId = 1) =>
  api.get(`${TERT_BASE}/catalog`, { params: { org_id: orgId } }).then((r) => r.data);

// V45 — Proof catalog + status
export const getTertiaireProofCatalog = () =>
  api.get(`${TERT_BASE}/proof-catalog`).then((r) => r.data);

export const getTertiaireEfaProofs = (efaId, year = null) =>
  api.get(`${TERT_BASE}/efa/${efaId}/proofs`, { params: year ? { year } : {} }).then((r) => r.data);

export const linkTertiaireProof = (efaId, body) =>
  api.post(`${TERT_BASE}/efa/${efaId}/proofs/link`, body).then((r) => r.data);

// V50: Proof Catalog V2 + Issue mapping + Template generation
export const getOperatProofCatalogV2 = () =>
  api.get(`${TERT_BASE}/proofs/catalog`).then((r) => r.data);

export const getIssueProofs = (issueCode) =>
  api.get(`${TERT_BASE}/issues/${issueCode}/proofs`).then((r) => r.data);

export const createOperatProofTemplates = (efaId, year, body) =>
  api
    .post(`${TERT_BASE}/efa/${efaId}/proofs/templates`, body, { params: { year } })
    .then((r) => r.data);

// ========================================
// PORTFOLIO CONSUMPTION (V1)
// ========================================

// skipSiteHeader: portfolio = multi-sites, never filter by single site scope
export const getPortfolioSummary = (params = {}) =>
  _cachedGet('/portfolio/consumption/summary', { params, skipSiteHeader: true }).then(
    (r) => r.data
  );
export const getPortfolioSites = (params = {}) =>
  _cachedGet('/portfolio/consumption/sites', { params, skipSiteHeader: true }).then((r) => r.data);

// CONSUMPTION CONTEXT V0 (Usages & Horaires)
// ========================================

export const getConsumptionContext = (siteId, days = 30) =>
  _cachedGet(`/consumption-context/site/${siteId}`, { params: { days } }).then((r) => r.data);
export const getConsumptionProfile = (siteId, days = 30) =>
  _cachedGet(`/consumption-context/site/${siteId}/profile`, { params: { days } }).then(
    (r) => r.data
  );
export const getConsumptionActivity = (siteId) =>
  _cachedGet(`/consumption-context/site/${siteId}/activity`).then((r) => r.data);
export const getConsumptionAnomalies = (siteId, days = 30) =>
  _cachedGet(`/consumption-context/site/${siteId}/anomalies`, { params: { days } }).then(
    (r) => r.data
  );
export const refreshConsumptionDiagnose = (siteId, days = 30) =>
  api
    .post(`/consumption-context/site/${siteId}/diagnose`, null, { params: { days } })
    .then((r) => r.data);
export const suggestSchedule = (siteId) =>
  api.get(`/consumption-context/site/${siteId}/suggest-schedule`).then((r) => r.data);
export const getDetectedSchedule = (siteId, windowDays = 56) =>
  api
    .get(`/consumption-context/site/${siteId}/activity/detected`, {
      params: { window_days: windowDays },
    })
    .then((r) => r.data);
export const compareSchedules = (siteId, windowDays = 56) =>
  api
    .get(`/consumption-context/site/${siteId}/activity/compare`, {
      params: { window_days: windowDays },
    })
    .then((r) => r.data);
export const applyDetectedSchedule = (siteId, windowDays = 56) =>
  api
    .post(`/consumption-context/site/${siteId}/activity/apply_detected`, null, {
      params: { window_days: windowDays },
    })
    .then((r) => r.data);
export const getPortfolioBehaviorSummary = (days = 30) =>
  _cachedGet('/consumption-context/portfolio/summary', { params: { days } }).then((r) => r.data);

// A.1: Unified Consumption
export const getConsumptionUnifiedSite = (siteId, start, end, source = 'reconciled') =>
  api.get(`/consumption-unified/site/${siteId}`, { params: { start, end, source } }).then((r) => r.data);
export const getConsumptionUnifiedPortfolio = (start, end, source = 'reconciled') =>
  api.get('/consumption-unified/portfolio', { params: { start, end, source } }).then((r) => r.data);
export const getConsumptionReconcile = (siteId, start, end) =>
  api.get(`/consumption-unified/reconcile/${siteId}`, { params: { start, end } }).then((r) => r.data);

// Step 9 B3: Reconcile-all (compteur/facture tous sites)
export const postBillingReconcileAll = (months = 12) =>
  api.post('/billing/reconcile-all', null, { params: { months } }).then((r) => r.data);

// V69: Meta version (sha + branch) — Expert mode display
export const getMetaVersion = () =>
  api
    .get('/meta/version')
    .then((r) => r.data)
    .catch(() => null);

// ========================================
// V96: Payment Rules
// ========================================
export const getPaymentRules = (params = {}) =>
  api.get('/patrimoine/payment-rules', { params }).then((r) => r.data);
export const createPaymentRule = (data) =>
  api.post('/patrimoine/payment-rules', data).then((r) => r.data);
export const updatePaymentRule = (id, data) =>
  api.put(`/patrimoine/payment-rules/${id}`, data).then((r) => r.data);
export const deletePaymentRule = (id) =>
  api.delete(`/patrimoine/payment-rules/${id}`).then((r) => r.data);
export const applyPaymentRulesBulk = (data) =>
  api.post('/patrimoine/payment-rules/apply-bulk', data).then((r) => r.data);
export const getSitePaymentInfo = (siteId) =>
  api.get(`/patrimoine/sites/${siteId}/payment-info`).then((r) => r.data);

// V96: Reconciliation
export const getReconciliation = (siteId) =>
  api.get(`/patrimoine/sites/${siteId}/reconciliation`).then((r) => r.data);
export const getPortfolioReconciliation = (params = {}) =>
  api.get('/patrimoine/portfolio/reconciliation', { params }).then((r) => r.data);

// V96: Contracts (if not already exported above)
export const getPatrimoineContracts = (params = {}) =>
  api.get('/patrimoine/contracts', { params }).then((r) => r.data);

// V97: Resolution Engine
export const applyReconciliationFix = (siteId, data) =>
  api.post(`/patrimoine/sites/${siteId}/reconciliation/fix`, data).then((r) => r.data);
export const getReconciliationHistory = (siteId) =>
  api.get(`/patrimoine/sites/${siteId}/reconciliation/history`).then((r) => r.data);
export const getReconciliationEvidence = (siteId) =>
  api.get(`/patrimoine/sites/${siteId}/reconciliation/evidence`).then((r) => r.data);
export const getReconciliationEvidenceCsv = (siteId) =>
  api
    .get(`/patrimoine/sites/${siteId}/reconciliation/evidence/csv`, { responseType: 'blob' })
    .then((r) => r.data);
export const getPortfolioReconciliationCsv = (params = {}) =>
  api
    .get('/patrimoine/portfolio/reconciliation/evidence/csv', { params, responseType: 'blob' })
    .then((r) => r.data);

// V98: Guidance Layer
export const getReconciliationEvidenceSummary = (siteId) =>
  api.get(`/patrimoine/sites/${siteId}/reconciliation/evidence/summary`).then((r) => r.data);

// V99: Contract Renewal Radar
export const getContractRadar = (params = {}) =>
  api.get('/contracts/radar', { params, skipSiteHeader: true }).then((r) => r.data);
export const getContractPurchaseScenarios = (contractId) =>
  api.get(`/contracts/${contractId}/purchase-scenarios`).then((r) => r.data);
export const createActionsFromScenario = (contractId, scenario) =>
  api.post(`/contracts/${contractId}/actions/from-scenario`, { scenario }).then((r) => r.data);
export const getContractScenarioSummary = (contractId) =>
  api.get(`/contracts/${contractId}/scenario-summary`).then((r) => r.data);

// V100: Offer Pricing V1 + Reconciliation
export const quoteOffer = (params) => api.post('/purchase/quote-offer', params).then((r) => r.data);
export const quoteMultiStrategy = (params) =>
  api.post('/purchase/quote-multi', params).then((r) => r.data);
export const reconcileOfferVsInvoice = (params) =>
  api.post('/purchase/reconcile', params).then((r) => r.data);

// V113: Action Templates
export const getActionTemplates = (category = null) =>
  _cachedGet('/action-templates', { params: category ? { category } : {} }).then((r) => r.data);
export const seedActionTemplates = () => api.post('/action-templates/seed').then((r) => r.data);

// V113: Energy Copilot
export const getCopilotActions = (orgId, params = {}) =>
  _cachedGet('/copilot/actions', { params: { org_id: orgId, ...params } }).then((r) => r.data);
export const runCopilot = (orgId) =>
  api.post('/copilot/run', { org_id: orgId }).then((r) => r.data);
export const validateCopilotAction = (actionId) =>
  api.post(`/copilot/actions/${actionId}/validate`).then((r) => r.data);
export const rejectCopilotAction = (actionId, reason = '') =>
  api.post(`/copilot/actions/${actionId}/reject`, { reason }).then((r) => r.data);

// V113: OPERAT Export
export const exportOperatCsv = (orgId, year, efaIds = null) =>
  api
    .post('/operat/export', { org_id: orgId, year, efa_ids: efaIds }, { responseType: 'blob' })
    .then((r) => r.data);
export const previewOperatExport = (orgId, year, efaIds = null) =>
  api.post('/operat/export/preview', { org_id: orgId, year, efa_ids: efaIds }).then((r) => r.data);

// V113: Data Quality Dashboard
export const getDataQualityCompleteness = (orgId) =>
  _cachedGet('/data-quality/completeness', { params: { org_id: orgId } }).then((r) => r.data);
export const getDataQualitySite = (siteId) =>
  _cachedGet(`/data-quality/completeness/${siteId}`).then((r) => r.data);

// D.1: Data Quality Score (4 dimensions)
export const getDataQualityScore = (siteId) =>
  _cachedGet(`/data-quality/site/${siteId}`).then((r) => r.data);
export const getDataQualityPortfolio = (orgId) =>
  _cachedGet('/data-quality/portfolio', { params: { org_id: orgId } }).then((r) => r.data);

// D.2: Data Freshness
export const getSiteFreshness = (siteId) =>
  _cachedGet(`/data-quality/freshness/${siteId}`).then((r) => r.data);

// V113: Onboarding Stepper
export const getOnboardingProgress = (orgId) =>
  _cachedGet('/onboarding-progress', { params: { org_id: orgId } }).then((r) => r.data);
export const updateOnboardingStep = (orgId, step, done = true) =>
  api
    .patch('/onboarding-progress/step', { step, done }, { params: { org_id: orgId } })
    .then((r) => r.data);
export const dismissOnboarding = (orgId) =>
  api.post('/onboarding-progress/dismiss', null, { params: { org_id: orgId } }).then((r) => r.data);
export const autoDetectOnboarding = (orgId) =>
  api.post('/onboarding-progress/auto', null, { params: { org_id: orgId } }).then((r) => r.data);

export default api;
