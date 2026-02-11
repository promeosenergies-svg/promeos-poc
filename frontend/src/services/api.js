/**
 * PROMEOS - Service API
 * Gestion des appels vers le backend FastAPI
 */
import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ========================================
// SITES
// ========================================

export const getSites = async (params = {}) => {
  const response = await api.get('/sites', { params });
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

export const getDemoStatus = () => api.get('/demo/status').then(r => r.data);
export const enableDemo = () => api.post('/demo/enable').then(r => r.data);
export const disableDemo = () => api.post('/demo/disable').then(r => r.data);
export const getDemoTemplates = () => api.get('/demo/templates').then(r => r.data);

// ========================================
// GUIDANCE (Action Plan + Readiness)
// ========================================

export const getActionPlan = (params = {}) => api.get('/guidance/action-plan', { params }).then(r => r.data);
export const getReadiness = () => api.get('/guidance/readiness').then(r => r.data);

// ========================================
// GUARDRAILS
// ========================================

export const getSiteGuardrails = (id) => api.get(`/sites/${id}/guardrails`).then(r => r.data);

// ========================================
// REGOPS
// ========================================

export const getRegOpsAssessment = (siteId) => api.get(`/regops/site/${siteId}`).then(r => r.data);
export const getRegOpsCached = (siteId) => api.get(`/regops/site/${siteId}/cached`).then(r => r.data);
export const recomputeRegOps = (params = {}) => api.post('/regops/recompute', null, { params }).then(r => r.data);
export const getRegOpsDashboard = () => api.get('/regops/dashboard').then(r => r.data);

// ========================================
// CONNECTORS
// ========================================

export const listConnectors = () => api.get('/connectors/list').then(r => r.data);
export const testConnector = (name) => api.post(`/connectors/${name}/test`).then(r => r.data);
export const syncConnector = (name, objectType, objectId) =>
  api.post(`/connectors/${name}/sync`, null, { params: { object_type: objectType, object_id: objectId } }).then(r => r.data);

// ========================================
// WATCHERS
// ========================================

export const listWatchers = () => api.get('/watchers/list').then(r => r.data);
export const runWatcher = (name) => api.post(`/watchers/${name}/run`).then(r => r.data);
export const listRegEvents = (source = null, reviewed = null) =>
  api.get('/watchers/events', { params: { source, reviewed } }).then(r => r.data);
export const reviewRegEvent = (eventId, reviewNote = '') =>
  api.patch(`/watchers/events/${eventId}/review`, null, { params: { review_note: reviewNote } }).then(r => r.data);

// ========================================
// AI AGENTS
// ========================================

export const getAiExplanation = (siteId) => api.get(`/ai/site/${siteId}/explain`).then(r => r.data);
export const getAiRecommendations = (siteId) => api.get(`/ai/site/${siteId}/recommend`).then(r => r.data);
export const getAiDataQuality = (siteId) => api.get(`/ai/site/${siteId}/data-quality`).then(r => r.data);
export const getAiExecBrief = (orgId = 1) => api.get('/ai/org/brief', { params: { org_id: orgId } }).then(r => r.data);
export const listAiInsights = (params = {}) => api.get('/ai/insights', { params }).then(r => r.data);

// ========================================
// KB USAGES (Knowledge Base)
// ========================================

export const getKBArchetypes = () => api.get('/kb/archetypes').then(r => r.data);
export const getKBArchetype = (code) => api.get(`/kb/archetypes/${code}`).then(r => r.data);
export const getKBArchetypeByNaf = (naf) => api.get(`/kb/archetypes/by-naf/${naf}`).then(r => r.data);
export const getKBRules = () => api.get('/kb/rules').then(r => r.data);
export const getKBRecommendations = () => api.get('/kb/recommendations').then(r => r.data);
export const searchKB = (q, type = null) => api.get('/kb/search', { params: { q, type } }).then(r => r.data);
export const getKBProvenance = (itemType, code) => api.get(`/kb/provenance/${itemType}/${code}`).then(r => r.data);
export const getKBStats = () => api.get('/kb/stats').then(r => r.data);
export const reloadKB = () => api.post('/kb/reload').then(r => r.data);

// ========================================
// ENERGY (Import & Analysis)
// ========================================

export const getMeters = (siteId = null) => api.get('/energy/meters', { params: { site_id: siteId } }).then(r => r.data);
export const createMeter = (data) => api.post('/energy/meters', data).then(r => r.data);
export const uploadConsumptionData = (file, meterId, frequency = 'hourly') => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/energy/import/upload', formData, {
    params: { meter_id: meterId, frequency },
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(r => r.data);
};
export const getImportJobs = (meterId = null) => api.get('/energy/import/jobs', { params: { meter_id: meterId } }).then(r => r.data);
export const runAnalysis = (meterId) => api.post('/energy/analysis/run', null, { params: { meter_id: meterId } }).then(r => r.data);
export const getAnalysisSummary = (meterId) => api.get('/energy/analysis/summary', { params: { meter_id: meterId } }).then(r => r.data);
export const generateDemoEnergy = (data) => api.post('/energy/demo/generate', data).then(r => r.data);

// ========================================
// ONBOARDING
// ========================================

export const createOnboarding = (data) => api.post('/onboarding', data).then(r => r.data);
export const importSitesCsv = (file) => {
  const fd = new FormData();
  fd.append('file', file);
  return api.post('/onboarding/import-csv', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data);
};
export const getOnboardingStatus = () => api.get('/onboarding/status').then(r => r.data);

// ========================================
// IMPORT STANDALONE
// ========================================

export const importSitesStandalone = (file) => {
  const fd = new FormData();
  fd.append('file', file);
  return api.post('/import/sites', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data);
};
export const getImportTemplate = () => api.get('/import/template').then(r => r.data);

// ========================================
// DEMO SEED
// ========================================

export const seedDemo = () => api.post('/demo/seed').then(r => r.data);

// ========================================
// CRUD (Sites + Compteurs)
// ========================================

export const createSite = (data) => api.post('/sites', data).then(r => r.data);
export const createCompteur = (data) => api.post('/compteurs', data).then(r => r.data);

// ========================================
// DASHBOARD 2 MINUTES
// ========================================

export const getDashboard2min = () => api.get('/dashboard/2min').then(r => r.data);

// ========================================
// SEGMENTATION
// ========================================

export const getSegmentationQuestions = () => api.get('/segmentation/questions').then(r => r.data);
export const submitSegmentationAnswers = (answers) => api.post('/segmentation/answers', { answers }).then(r => r.data);
export const getSegmentationProfile = () => api.get('/segmentation/profile').then(r => r.data);

export default api;
