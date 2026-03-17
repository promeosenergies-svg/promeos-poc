/**
 * PROMEOS - API Patrimoine
 * Sites, compteurs, contracts, delivery points, geocoding, CRUD, intake, staging
 */
import api, { cachedGet } from './core';

// ── Sites ──
export const getSites = async (params = {}) => {
  const response = await cachedGet('/sites', { params });
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
export const createSite = (data) => api.post('/sites', data).then((r) => r.data);
export const quickCreateSite = (data) => api.post('/sites/quick-create', data).then((r) => r.data);

// ── Geocoding ──
export const geocodeOneSite = async (siteId, force = false) => {
  const response = await api.post(`/geocode/site/${siteId}`, null, { params: { force } });
  return response.data;
};
export const geocodeOrgSites = async (orgId, force = false) => {
  const response = await api.post('/geocode/org', null, { params: { org_id: orgId, force } });
  return response.data;
};
export const searchAddress = async (query) => {
  const response = await api.get('/geocode/search', { params: { q: query } });
  return response.data;
};

// ── Compteurs ──
export const getCompteurs = async (params = {}) => {
  const response = await api.get('/compteurs', { params });
  return response.data;
};
export const getCompteur = async (id) => {
  const response = await api.get(`/compteurs/${id}`);
  return response.data;
};
export const createCompteur = (data) => api.post('/compteurs', data).then((r) => r.data);

// ── Guardrails ──
export const getSiteGuardrails = (id) => api.get(`/sites/${id}/guardrails`).then((r) => r.data);

// ── Site Config (Schedule + Tariff) ──
export const getSiteSchedule = (siteId) => api.get(`/site/${siteId}/schedule`).then((r) => r.data);
export const putSiteSchedule = (siteId, data) =>
  api.put(`/site/${siteId}/schedule`, data).then((r) => r.data);
export const getSiteTariff = (siteId) => api.get(`/site/${siteId}/tariff`).then((r) => r.data);
export const putSiteTariff = (siteId, data) =>
  api.put(`/site/${siteId}/tariff`, data).then((r) => r.data);

// ── Referentiel Tarifs ──
export const getReferentielTarifs = () => cachedGet('/referentiel/tarifs').then((r) => r.data);

// ── Patrimoine CRUD ──
export const crudListOrganisations = () =>
  api.get('/patrimoine/crud/organisations').then((r) => r.data);
export const crudCreateOrganisation = (data) =>
  api.post('/patrimoine/crud/organisations', data).then((r) => r.data);
export const crudUpdateOrganisation = (id, data) =>
  api.patch(`/patrimoine/crud/organisations/${id}`, data).then((r) => r.data);
export const crudDeleteOrganisation = (id) =>
  api.delete(`/patrimoine/crud/organisations/${id}`).then((r) => r.data);

export const crudListEntites = (params = {}) =>
  api.get('/patrimoine/crud/entites', { params }).then((r) => r.data);
export const crudCreateEntite = (data) =>
  api.post('/patrimoine/crud/entites', data).then((r) => r.data);
export const crudUpdateEntite = (id, data) =>
  api.patch(`/patrimoine/crud/entites/${id}`, data).then((r) => r.data);
export const crudDeleteEntite = (id) =>
  api.delete(`/patrimoine/crud/entites/${id}`).then((r) => r.data);

export const crudListPortefeuilles = (params = {}) =>
  api.get('/patrimoine/crud/portefeuilles', { params }).then((r) => r.data);
export const crudCreatePortefeuille = (data) =>
  api.post('/patrimoine/crud/portefeuilles', data).then((r) => r.data);
export const crudUpdatePortefeuille = (id, data) =>
  api.patch(`/patrimoine/crud/portefeuilles/${id}`, data).then((r) => r.data);
export const crudDeletePortefeuille = (id) =>
  api.delete(`/patrimoine/crud/portefeuilles/${id}`).then((r) => r.data);

export const crudListSites = (params = {}) =>
  api.get('/patrimoine/crud/sites', { params }).then((r) => r.data);
export const crudCreateSite = (data) =>
  api.post('/patrimoine/crud/sites', data).then((r) => r.data);
export const crudUpdateSite = (id, data) =>
  api.patch(`/patrimoine/crud/sites/${id}`, data).then((r) => r.data);
export const crudDeleteSite = (id) =>
  api.delete(`/patrimoine/crud/sites/${id}`).then((r) => r.data);

export const crudCreateBatiment = (data) =>
  api.post('/patrimoine/crud/batiments', data).then((r) => r.data);

// ── Patrimoine World-Class CRUD ──
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
export const patrimoineSiteMeters = (siteId) =>
  api.get(`/patrimoine/sites/${siteId}/meters`).then((r) => r.data);
export const getSiteMetersTree = (siteId) =>
  api.get(`/patrimoine/sites/${siteId}/meters/tree`).then((r) => r.data);
export const createSubMeter = (meterId, data) =>
  api.post(`/patrimoine/meters/${meterId}/sub-meters`, data).then((r) => r.data);
export const getMeterBreakdown = (meterId, params = {}) =>
  api.get(`/patrimoine/meters/${meterId}/breakdown`, { params }).then((r) => r.data);
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

// ── Patrimoine Audit V51 ──
export const patrimoineDeliveryPoints = (siteId) =>
  api.get(`/patrimoine/sites/${siteId}/delivery-points`).then((r) => r.data);
export const patrimoineKpis = (params = {}) =>
  api.get('/patrimoine/kpis', { params }).then((r) => r.data);
export const patrimoineSitesExport = (params = {}) =>
  api.get('/patrimoine/sites/export.csv', { params, responseType: 'blob' });

// ── Patrimoine Snapshot & Anomalies ──
export const getPatrimoineSnapshot = (siteId) =>
  api.get(`/patrimoine/sites/${siteId}/snapshot`).then((r) => r.data);
export const getPatrimoineAnomalies = (siteId) =>
  api.get(`/patrimoine/sites/${siteId}/anomalies`).then((r) => r.data);
export const listPatrimoineAnomalies = (params = {}) =>
  api.get('/patrimoine/anomalies', { params }).then((r) => r.data);
export const getPatrimoineAssumptions = () =>
  api.get('/patrimoine/assumptions').then((r) => r.data);
export const getPatrimoinePortfolioSummary = (params = {}) =>
  cachedGet('/patrimoine/portfolio-summary', { params }).then((r) => r.data);

// ── Patrimoine Staging (DIAMANT) ──
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
export const getStagingMatching = (batchId) =>
  api.get(`/patrimoine/staging/${batchId}/matching`).then((r) => r.data);
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
export const stagingExportReport = (batchId) =>
  api.get(`/patrimoine/staging/${batchId}/export/report.csv`, { responseType: 'blob' });

// ── Smart Intake (DIAMANT) ──
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

// ── V96: Payment Rules ──
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

// ── V96: Contracts ──
export const getPatrimoineContracts = (params = {}) =>
  api.get('/patrimoine/contracts', { params }).then((r) => r.data);

// ── V-registre: KPIs patrimoine + completude ──
export const getPatrimoineKpis = (params = {}) =>
  api.get('/patrimoine/kpis', { params }).then((r) => r.data);
export const getSiteCompleteness = (siteId) =>
  api.get(`/patrimoine/sites/${siteId}/completeness`).then((r) => r.data);

// ── V99: Contract Renewal Radar ──
export const getContractRadar = (params = {}) =>
  api.get('/contracts/radar', { params, skipSiteHeader: true }).then((r) => r.data);
export const getContractPurchaseScenarios = (contractId) =>
  api.get(`/contracts/${contractId}/purchase-scenarios`).then((r) => r.data);
export const createActionsFromScenario = (contractId, scenario) =>
  api.post(`/contracts/${contractId}/actions/from-scenario`, { scenario }).then((r) => r.data);
export const getContractScenarioSummary = (contractId) =>
  api.get(`/contracts/${contractId}/scenario-summary`).then((r) => r.data);

// ── Flex Mini ──
export const getFlexMini = (siteId, start, end) =>
  api.get(`/sites/${siteId}/flex/mini`, { params: { start, end } }).then((r) => r.data);

// ── APER (solarisation) ──
export const getAperDashboard = () => cachedGet('/aper/dashboard').then((r) => r.data);
export const getAperEstimate = (siteId, params = {}) =>
  cachedGet(`/aper/site/${siteId}/estimate`, { params }).then((r) => r.data);
