/**
 * PROMEOS - API Admin
 * Admin users, demo, onboarding, import, connectors, KB, AI agents, dev tools
 */
import api from './core';

// ── Admin Users ──
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

// ── Demo Mode ──
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
export const seedDemo = () => api.post('/demo/seed').then((r) => r.data);

// ── Onboarding ──
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

// ── Import Standalone ──
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

// ── Connectors ──
export const listConnectors = () => api.get('/connectors/list').then((r) => r.data);
export const testConnector = (name) => api.post(`/connectors/${name}/test`).then((r) => r.data);
export const syncConnector = (name, objectType, objectId) =>
  api
    .post(`/connectors/${name}/sync`, null, {
      params: { object_type: objectType, object_id: objectId },
    })
    .then((r) => r.data);

// ── KB Usages (Knowledge Base) ──
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
export const getKBMetrics = (sinceDays = 30) =>
  api.get(`${KB_BASE}/metrics`, { params: { since_days: sinceDays } }).then((r) => r.data);

// KB Memobox — Upload + Lifecycle
export const uploadKBDoc = (file, title, domain = null, docType = 'pdf', actionId = null) => {
  const fd = new FormData();
  fd.append('file', file);
  const params = { title };
  if (domain) params.domain = domain;
  if (docType) params.doc_type = docType;
  if (actionId) params.action_id = actionId;
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

// ── AI Agents ──
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

// ── Dev Tools ──
export const resetDb = () => api.post('/dev/reset_db').then((r) => r.data);
