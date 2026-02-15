/**
 * PROMEOS - Service API
 * Gestion des appels vers le backend FastAPI
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Auth interceptors
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('promeos_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Silent URL patterns — passive checks that should never trigger toasts
const SILENT_URLS = ['/demo/status-pack'];
export const isSilentUrl = (url) => SILENT_URLS.some(u => url?.includes(u));

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const cfg = error.config || {};
    const isSilent = cfg.silent || isSilentUrl(cfg.url);

    if (!isSilent && error.response?.status === 401 && !cfg.url?.includes('/auth/')) {
      localStorage.removeItem('promeos_token');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
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
export const getDemoPacks = () => api.get('/demo/packs').then(r => r.data);
export const seedDemoPack = (pack, size, reset = false) =>
  api.post('/demo/seed-pack', { pack, size, reset, rng_seed: 42 }).then(r => r.data);
export const getDemoPackStatus = () => api.get('/demo/status-pack').then(r => r.data);
export const resetDemoPack = (mode = 'soft', confirm = false) =>
  api.post('/demo/reset-pack', { mode, confirm }).then(r => r.data);

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
export const getScoreExplain = (scopeType, scopeId) => api.get('/regops/score_explain', { params: { scope_type: scopeType, scope_id: scopeId } }).then(r => r.data);
export const getDataQuality = (scopeType, scopeId) => api.get('/regops/data_quality', { params: { scope_type: scopeType, scope_id: scopeId } }).then(r => r.data);
export const getDataQualitySpecs = () => api.get('/regops/data_quality/specs').then(r => r.data);

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
export const listRegEvents = (source = null, reviewed = null, status = null) =>
  api.get('/watchers/events', { params: { source, reviewed, status } }).then(r => r.data);
export const reviewRegEvent = (eventId, decision = 'apply', notes = '') =>
  api.patch(`/watchers/events/${eventId}/review`, { decision, notes }).then(r => r.data);
export const getRegEventDetail = (eventId) => api.get(`/watchers/events/${eventId}`).then(r => r.data);

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

const KB_BASE = '/kb';

export const pingKB = () => api.get(`${KB_BASE}/ping`).then(r => r.data);
export const getKBArchetypes = () => api.get(`${KB_BASE}/archetypes`).then(r => r.data);
export const getKBArchetype = (code) => api.get(`${KB_BASE}/archetypes/${code}`).then(r => r.data);
export const getKBArchetypeByNaf = (naf) => api.get(`${KB_BASE}/archetypes/by-naf/${naf}`).then(r => r.data);
export const getKBRules = () => api.get(`${KB_BASE}/rules`).then(r => r.data);
export const getKBRecommendations = () => api.get(`${KB_BASE}/recommendations`).then(r => r.data);
export const searchKB = (q, type = null) => api.get(`${KB_BASE}/search`, { params: { q, type } }).then(r => r.data);
export const getKBProvenance = (itemType, code) => api.get(`${KB_BASE}/provenance/${itemType}/${code}`).then(r => r.data);
export const getKBStats = () => api.get(`${KB_BASE}/usages-stats`).then(r => r.data);
export const reloadKB = () => api.post(`${KB_BASE}/reload`).then(r => r.data);
export const seedDemoKB = () => api.post(`${KB_BASE}/seed_demo`).then(r => r.data);

// KB Explorer (structured KB system - FTS5 search + apply engine)
export const getKBItemsList = (params = {}) => api.get(`${KB_BASE}/items`, { params }).then(r => r.data);
export const getKBItemDetail = (itemId) => api.get(`${KB_BASE}/items/${itemId}`).then(r => r.data);
export const searchKBItems = (body) => api.post(`${KB_BASE}/search`, body).then(r => r.data);
export const applyKB = (body) => api.post(`${KB_BASE}/apply`, body).then(r => r.data);
export const getKBFullStats = () => api.get(`${KB_BASE}/stats`).then(r => r.data);

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

// ========================================
// COMPLIANCE (Rules-based)
// ========================================

export const getComplianceSummary = (params = {}) => api.get('/compliance/summary', { params }).then(r => r.data);
export const getComplianceSites = (params = {}) => api.get('/compliance/sites', { params }).then(r => r.data);
export const getComplianceBundle = (params = {}) => api.get('/compliance/bundle', { params }).then(r => r.data);
export const recomputeComplianceRules = (orgId = null) => api.post('/compliance/recompute-rules', null, { params: { org_id: orgId } }).then(r => r.data);
export const getComplianceRules = () => api.get('/compliance/rules').then(r => r.data);

// Sprint 9: Compliance OPS workflow
export const getComplianceFindings = (params = {}) => api.get('/compliance/findings', { params }).then(r => r.data);
export const patchComplianceFinding = (id, data) => api.patch(`/compliance/findings/${id}`, data).then(r => r.data);
export const getComplianceBatches = (orgId = null) => api.get('/compliance/batches', { params: { org_id: orgId } }).then(r => r.data);
export const getFindingDetail = (findingId) => api.get(`/compliance/findings/${findingId}`).then(r => r.data);

// Dev Tools
export const resetDb = () => api.post('/dev/reset_db').then(r => r.data);

// Health
export const getApiHealth = () => api.get('/health').then(r => r.data);

// ========================================
// CONSUMPTION DIAGNOSTIC
// ========================================

export const getConsumptionInsights = (orgId = null) => api.get('/consumption/insights', { params: { org_id: orgId } }).then(r => r.data);
export const getConsumptionSite = (siteId) => api.get(`/consumption/site/${siteId}`).then(r => r.data);
export const runConsumptionDiagnose = (orgId = null, days = 30) => api.post('/consumption/diagnose', null, { params: { org_id: orgId, days } }).then(r => r.data);
export const seedDemoConsumption = (siteId = null, days = 30) => api.post('/consumption/seed-demo', null, { params: { site_id: siteId, days } }).then(r => r.data);
export const patchConsumptionInsight = (insightId, data) => api.patch(`/consumption/insights/${insightId}`, data).then(r => r.data);

// ========================================
// FLEX MINI
// ========================================
export const getFlexMini = (siteId, start, end) =>
  api.get(`/sites/${siteId}/flex/mini`, { params: { start, end } }).then(r => r.data);

// ========================================
// SITE CONFIG (Schedule + Tariff)
// ========================================

export const getSiteSchedule = (siteId) => api.get(`/site/${siteId}/schedule`).then(r => r.data);
export const putSiteSchedule = (siteId, data) => api.put(`/site/${siteId}/schedule`, data).then(r => r.data);
export const getSiteTariff = (siteId) => api.get(`/site/${siteId}/tariff`).then(r => r.data);
export const putSiteTariff = (siteId, data) => api.put(`/site/${siteId}/tariff`, data).then(r => r.data);

// ========================================
// BILL INTELLIGENCE
// ========================================

export const getBillingSummary = () => api.get('/billing/summary').then(r => r.data);
export const getBillingInsights = (params = {}) => api.get('/billing/insights', { params }).then(r => r.data);
export const getBillingInvoices = (params = {}) => api.get('/billing/invoices', { params }).then(r => r.data);
export const getSiteBilling = (siteId) => api.get(`/billing/site/${siteId}`).then(r => r.data);
export const getBillingRules = () => api.get('/billing/rules').then(r => r.data);
export const auditInvoice = (invoiceId) => api.post(`/billing/audit/${invoiceId}`).then(r => r.data);
export const auditAllInvoices = () => api.post('/billing/audit-all').then(r => r.data);
export const seedBillingDemo = () => api.post('/billing/seed-demo').then(r => r.data);
export const importInvoicesCsv = (file) => {
  const fd = new FormData();
  fd.append('file', file);
  return api.post('/billing/import-csv', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data);
};
export const patchBillingInsight = (insightId, data) => api.patch(`/billing/insights/${insightId}`, data).then(r => r.data);
export const resolveBillingInsight = (insightId, notes = null) => api.post(`/billing/insights/${insightId}/resolve`, null, { params: notes ? { notes } : {} }).then(r => r.data);
export const getImportBatches = (params = {}) => api.get('/billing/import/batches', { params }).then(r => r.data);

// ========================================
// ACHAT ENERGIE
// ========================================

export const getPurchaseEstimate = (siteId) => api.get(`/purchase/estimate/${siteId}`).then(r => r.data);
export const getPurchaseAssumptions = (siteId) => api.get(`/purchase/assumptions/${siteId}`).then(r => r.data);
export const putPurchaseAssumptions = (siteId, data) => api.put(`/purchase/assumptions/${siteId}`, data).then(r => r.data);
export const getPurchasePreferences = (params = {}) => api.get('/purchase/preferences', { params }).then(r => r.data);
export const putPurchasePreferences = (data) => api.put('/purchase/preferences', data).then(r => r.data);
export const computePurchaseScenarios = (siteId) => api.post(`/purchase/compute/${siteId}`).then(r => r.data);
export const getPurchaseResults = (siteId) => api.get(`/purchase/results/${siteId}`).then(r => r.data);
export const acceptPurchaseResult = (resultId) => api.patch(`/purchase/results/${resultId}/accept`).then(r => r.data);
export const seedPurchaseDemo = () => api.post('/purchase/seed-demo').then(r => r.data);

// Sprint 8.1: Portfolio, Renewals, History, Actions
export const computePortfolio = (orgId) => api.post('/purchase/compute', null, { params: { org_id: orgId, scope: 'org' } }).then(r => r.data);
export const getPortfolioResults = (orgId) => api.get('/purchase/results', { params: { org_id: orgId } }).then(r => r.data);
export const getPurchaseRenewals = (orgId = null) => api.get('/purchase/renewals', { params: orgId ? { org_id: orgId } : {} }).then(r => r.data);
export const getPurchaseHistory = (siteId) => api.get(`/purchase/history/${siteId}`).then(r => r.data);
export const getPurchaseActions = (orgId = null) => api.get('/purchase/actions', { params: orgId ? { org_id: orgId } : {} }).then(r => r.data);

// ========================================
// ACTION HUB (Sprint 10)
// ========================================

export const createAction = (data) => api.post('/actions', data).then(r => r.data);
export const syncActions = (orgId = null) => api.post('/actions/sync', null, { params: orgId ? { org_id: orgId } : {} }).then(r => r.data);
export const getActionsList = (params = {}) => api.get('/actions/list', { params }).then(r => r.data);
export const getActionsSummary = (orgId = null) => api.get('/actions/summary', { params: orgId ? { org_id: orgId } : {} }).then(r => r.data);
export const patchAction = (id, data) => api.patch(`/actions/${id}`, data).then(r => r.data);
export const getActionBatches = (orgId = null) => api.get('/actions/batches', { params: orgId ? { org_id: orgId } : {} }).then(r => r.data);
export const exportActionsCSV = (params = {}) => api.get('/actions/export.csv', { params, responseType: 'blob' });

// ========================================
// REPORTS (Sprint 10.1)
// ========================================

export const getAuditReportJSON = (orgId = null) => api.get('/reports/audit.json', { params: orgId ? { org_id: orgId } : {} }).then(r => r.data);
export const downloadAuditPDF = (orgId = null) => api.get('/reports/audit.pdf', { params: orgId ? { org_id: orgId } : {}, responseType: 'blob' });

// ========================================
// NOTIFICATIONS (Sprint 10.2)
// ========================================

export const syncNotifications = (orgId = null) => api.post('/notifications/sync', null, { params: orgId ? { org_id: orgId } : {} }).then(r => r.data);
export const getNotificationsList = (params = {}) => api.get('/notifications/list', { params }).then(r => r.data);
export const getNotificationsSummary = (orgId = null) => api.get('/notifications/summary', { params: orgId ? { org_id: orgId } : {} }).then(r => r.data);
export const patchNotification = (id, data) => api.patch(`/notifications/${id}`, data).then(r => r.data);
export const getNotificationPreferences = (orgId = null) => api.get('/notifications/preferences', { params: orgId ? { org_id: orgId } : {} }).then(r => r.data);
export const putNotificationPreferences = (data, orgId = null) => api.put('/notifications/preferences', data, { params: orgId ? { org_id: orgId } : {} }).then(r => r.data);

// ========================================
// IAM — Auth (Sprint 11)
// ========================================

export const loginAuth = (email, password) => api.post('/auth/login', { email, password }).then(r => r.data);
export const refreshAuth = () => api.post('/auth/refresh').then(r => r.data);
export const getAuthMe = () => api.get('/auth/me').then(r => r.data);
export const logoutAuth = () => api.post('/auth/logout').then(r => r.data);
export const changePassword = (currentPassword, newPassword) => api.put('/auth/password', { current_password: currentPassword, new_password: newPassword }).then(r => r.data);
export const switchOrg = (orgId) => api.post('/auth/switch-org', { org_id: orgId }).then(r => r.data);

// ========================================
// IAM — Admin Users (Sprint 11)
// ========================================

export const getAdminUsers = () => api.get('/admin/users').then(r => r.data);
export const createAdminUser = (data) => api.post('/admin/users', data).then(r => r.data);
export const getAdminUser = (id) => api.get(`/admin/users/${id}`).then(r => r.data);
export const patchAdminUser = (id, data) => api.patch(`/admin/users/${id}`, data).then(r => r.data);
export const changeAdminRole = (id, role) => api.put(`/admin/users/${id}/role`, { role }).then(r => r.data);
export const setAdminScopes = (id, scopes) => api.put(`/admin/users/${id}/scopes`, { scopes }).then(r => r.data);
export const deleteAdminUser = (id) => api.delete(`/admin/users/${id}`).then(r => r.data);
export const getAdminRoles = () => api.get('/admin/roles').then(r => r.data);
export const getEffectiveAccess = (id) => api.get(`/admin/users/${id}/effective-access`).then(r => r.data);

// ========================================
// IAM — Audit Log (Sprint 11)
// ========================================

export const getAuditLogs = (params = {}) => api.get('/auth/audit', { params }).then(r => r.data);

// ========================================
// IAM — Demo Mode (Sprint 11)
// ========================================

export const impersonateUser = (email) => api.post('/auth/impersonate', { email }).then(r => r.data);

// ========================================
// PATRIMOINE STAGING (DIAMANT)
// ========================================

export const stagingImport = (file, mode = 'import') => {
  const fd = new FormData();
  fd.append('file', file);
  return api.post('/patrimoine/staging/import', fd, {
    params: { mode },
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data);
};
export const stagingImportInvoices = (invoices) => api.post('/patrimoine/staging/import-invoices', { invoices }).then(r => r.data);
export const stagingSummary = (batchId) => api.get(`/patrimoine/staging/${batchId}/summary`).then(r => r.data);
export const stagingRows = (batchId, params = {}) => api.get(`/patrimoine/staging/${batchId}/rows`, { params }).then(r => r.data);
export const stagingIssues = (batchId, params = {}) => api.get(`/patrimoine/staging/${batchId}/issues`, { params }).then(r => r.data);
export const stagingValidate = (batchId) => api.post(`/patrimoine/staging/${batchId}/validate`).then(r => r.data);
export const stagingFix = (batchId, fixType, params) => api.put(`/patrimoine/staging/${batchId}/fix`, { fix_type: fixType, params }).then(r => r.data);
export const stagingFixBulk = (batchId, fixes) => api.put(`/patrimoine/staging/${batchId}/fix/bulk`, { fixes }).then(r => r.data);
export const stagingAutofix = (batchId) => api.post(`/patrimoine/staging/${batchId}/autofix`).then(r => r.data);
export const stagingActivate = (batchId, portefeuilleId) => api.post(`/patrimoine/staging/${batchId}/activate`, { portefeuille_id: portefeuilleId }).then(r => r.data);
export const stagingResult = (batchId) => api.get(`/patrimoine/staging/${batchId}/result`).then(r => r.data);
export const stagingAbandon = (batchId) => api.delete(`/patrimoine/staging/${batchId}`).then(r => r.data);
export const loadPatrimoineDemo = () => api.post('/patrimoine/demo/load').then(r => r.data);
export const getImportTemplateColumns = () => api.get('/patrimoine/import/template/columns').then(r => r.data);
export const portfolioSync = (portfolioId, file, dryRun = true) => {
  const fd = new FormData();
  fd.append('file', file);
  return api.post(`/patrimoine/${portfolioId}/sync`, fd, {
    params: { dry_run: dryRun },
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data);
};

// ========================================
// SMART INTAKE (DIAMANT)
// ========================================

export const getIntakeQuestions = (siteId) => api.get(`/intake/${siteId}/questions`).then(r => r.data);
export const submitIntakeAnswer = (siteId, fieldPath, value, source = 'user') =>
  api.post(`/intake/${siteId}/answers`, { field_path: fieldPath, value, source }).then(r => r.data);
export const applyIntakeSuggestions = (siteId, fieldPaths) =>
  api.post(`/intake/${siteId}/apply-suggestions`, { field_paths: fieldPaths }).then(r => r.data);
export const intakeDemoAutofill = (siteId) => api.post(`/intake/${siteId}/demo-autofill`).then(r => r.data);
export const completeIntake = (siteId) => api.post(`/intake/${siteId}/complete`).then(r => r.data);
export const getIntakeSession = (sessionId) => api.get(`/intake/session/${sessionId}`).then(r => r.data);
export const purgeIntakeDemo = () => api.delete('/intake/demo/purge').then(r => r.data);

// ========================================
// MONITORING (Electric Performance)
// ========================================

export const getMonitoringKpis = (siteId) => api.get('/monitoring/kpis', { params: { site_id: siteId } }).then(r => r.data);
export const runMonitoring = (siteId, days = 90) => api.post('/monitoring/run', { site_id: siteId, days }).then(r => r.data);
export const getMonitoringSnapshots = (siteId, limit = 10) => api.get('/monitoring/snapshots', { params: { site_id: siteId, limit } }).then(r => r.data);
export const getMonitoringAlerts = (siteId, status = null, limit = 50) => api.get('/monitoring/alerts', { params: { site_id: siteId, status, limit } }).then(r => r.data);
export const ackMonitoringAlert = (id) => api.post(`/monitoring/alerts/${id}/ack`, { acknowledged_by: 'user' }).then(r => r.data);
export const resolveMonitoringAlert = (id, note = null) => api.post(`/monitoring/alerts/${id}/resolve`, { resolved_by: 'user', resolution_note: note }).then(r => r.data);
export const generateMonitoringDemo = (siteId, days = 90, profile = 'office') => api.post('/monitoring/demo/generate', { site_id: siteId, days, profile }).then(r => r.data);
export const getMonitoringKpisCompare = (siteId, mode = 'previous', customStart = null, customEnd = null) =>
  api.get('/monitoring/kpis/compare', { params: { site_id: siteId, mode, custom_start: customStart, custom_end: customEnd } }).then(r => r.data);

// ========================================
// BACS Expert (Decret n°2020-887)
// ========================================

export const getBacsAssessment = (siteId) => api.get(`/regops/bacs/site/${siteId}`).then(r => r.data);
export const recomputeBacs = (siteId) => api.post(`/regops/bacs/recompute/${siteId}`).then(r => r.data);
export const getBacsScoreExplain = (siteId) => api.get(`/regops/bacs/score_explain/${siteId}`).then(r => r.data);
export const getBacsDataQuality = (siteId) => api.get(`/regops/bacs/data_quality/${siteId}`).then(r => r.data);
export const createBacsAsset = (siteId, isTertiary = true, pcDate = null) =>
  api.post('/regops/bacs/asset', null, { params: { site_id: siteId, is_tertiary: isTertiary, pc_date: pcDate } }).then(r => r.data);
export const addCvcSystem = (assetId, systemType, architecture, unitsJson = '[]') =>
  api.post(`/regops/bacs/asset/${assetId}/system`, null, { params: { system_type: systemType, architecture, units_json: unitsJson } }).then(r => r.data);
export const updateCvcSystem = (systemId, unitsJson = null, architecture = null) =>
  api.put(`/regops/bacs/system/${systemId}`, null, { params: { units_json: unitsJson, architecture } }).then(r => r.data);
export const deleteCvcSystem = (systemId) => api.delete(`/regops/bacs/system/${systemId}`).then(r => r.data);
export const seedBacsDemo = () => api.post('/regops/bacs/seed_demo').then(r => r.data);
export const getBacsOpsPanel = (siteId) => api.get(`/regops/bacs/site/${siteId}/ops`).then(r => r.data);

// ========================================
// EMS Consumption Explorer
// ========================================

export const getEmsTimeseries = (params) => api.get('/ems/timeseries', { params }).then(r => r.data);
export const getEmsTimeseriesSuggest = (dateFrom, dateTo) => api.get('/ems/timeseries/suggest', { params: { date_from: dateFrom, date_to: dateTo } }).then(r => r.data);
export const getEmsWeather = (siteId, dateFrom, dateTo) => api.get('/ems/weather', { params: { site_id: siteId, date_from: dateFrom, date_to: dateTo } }).then(r => r.data);
export const getEmsWeatherMulti = (siteIds, dateFrom, dateTo) => api.get('/ems/weather', { params: { site_ids: siteIds.join(','), date_from: dateFrom, date_to: dateTo } }).then(r => r.data);
export const runEmsSignature = (siteId, dateFrom, dateTo, meterIds = null) => api.post('/ems/signature/run', null, { params: { site_id: siteId, date_from: dateFrom, date_to: dateTo, meter_ids: meterIds } }).then(r => r.data);
export const runEmsSignaturePortfolio = (siteIds, dateFrom, dateTo) => api.post('/ems/signature/portfolio', null, { params: { site_ids: siteIds.join(','), date_from: dateFrom, date_to: dateTo } }).then(r => r.data);
export const getEmsViews = (userId = null) => api.get('/ems/views', { params: userId ? { user_id: userId } : {} }).then(r => r.data);
export const createEmsView = (name, configJson, userId = null) => api.post('/ems/views', null, { params: { name, config_json: configJson, user_id: userId } }).then(r => r.data);
export const updateEmsView = (id, params) => api.put(`/ems/views/${id}`, null, { params }).then(r => r.data);
export const deleteEmsView = (id) => api.delete(`/ems/views/${id}`).then(r => r.data);

// Collections (paniers de sites)
export const getEmsCollections = () => api.get('/ems/collections').then(r => r.data);
export const createEmsCollection = (name, siteIds, scopeType = 'custom', isFavorite = false) =>
  api.post('/ems/collections', null, { params: { name, site_ids: siteIds.join(','), scope_type: scopeType, is_favorite: isFavorite } }).then(r => r.data);
export const updateEmsCollection = (id, params) => api.put(`/ems/collections/${id}`, null, { params }).then(r => r.data);
export const deleteEmsCollection = (id) => api.delete(`/ems/collections/${id}`).then(r => r.data);

// Usage suggest & benchmark
export const getUsageSuggest = (siteId) => api.get('/ems/usage_suggest', { params: { site_id: siteId } }).then(r => r.data);
export const getEmsBenchmark = (siteId) => api.get('/ems/benchmark', { params: { site_id: siteId } }).then(r => r.data);
export const getScheduleSuggest = (siteId, days = 90) => api.get('/ems/schedule_suggest', { params: { site_id: siteId, days } }).then(r => r.data);

// Demo data
export const generateEmsDemo = (portfolioSize = 12, days = 365, seed = 123, force = false) =>
  api.post('/ems/demo/generate', null, { params: { portfolio_size: portfolioSize, days, seed, force } }).then(r => r.data);
export const purgeEmsDemo = () => api.post('/ems/demo/purge').then(r => r.data);

export default api;
