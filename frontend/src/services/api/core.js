/**
 * PROMEOS - API Core
 * Axios instance, interceptors, cache, and utility functions
 */
import axios from 'axios';
import { logger } from '../logger';

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
const GET_CACHE_TTL_MS = 60_000; // 60 seconds — historical consumption data changes rarely

function _cacheKey(url, params) {
  // C1 FIX: inclure orgId dans la clé pour éviter le cross-tenant
  const scopePrefix = _apiScope.orgId != null ? `org:${_apiScope.orgId}|` : '';
  if (!params || Object.keys(params).length === 0) return `${scopePrefix}${url}`;
  const sorted = JSON.stringify(params, Object.keys(params).sort());
  return `${scopePrefix}${url}|${sorted}`;
}

/**
 * Cached GET — deduplicates in-flight requests and caches responses.
 * - Same request in-flight -> returns same Promise (no duplicate network call)
 * - Same request completed within TTL -> returns cached data
 * - Otherwise -> fresh fetch
 * @param {string} url
 * @param {object} [config] — axios config (params, headers, etc.)
 * @returns {Promise<import('axios').AxiosResponse>}
 */
export function cachedGet(url, config = {}) {
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

export default api;
