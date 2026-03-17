/**
 * PROMEOS - API Conformite
 * Compliance, RegOps, Tertiaire/OPERAT, BACS
 */
import api, { cachedGet } from './core';

// ── RegOps ──
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

// ── Compliance (Rules-based) ──
export const getComplianceSummary = (params = {}) =>
  api.get('/compliance/summary', { params }).then((r) => r.data);
export const getComplianceSites = (params = {}) =>
  api.get('/compliance/sites', { params }).then((r) => r.data);
export const getComplianceBundle = (params = {}) =>
  cachedGet('/compliance/bundle', { params }).then((r) => r.data);
export const recomputeComplianceRules = (orgId = null) =>
  api.post('/compliance/recompute-rules', null, { params: { org_id: orgId } }).then((r) => r.data);
export const getComplianceRules = () => api.get('/compliance/rules').then((r) => r.data);

// Compliance OPS workflow
export const getComplianceFindings = (params = {}) =>
  api.get('/compliance/findings', { params }).then((r) => r.data);
export const patchComplianceFinding = (id, data) =>
  api.patch(`/compliance/findings/${id}`, data).then((r) => r.data);
export const getComplianceBatches = (orgId = null) =>
  api.get('/compliance/batches', { params: { org_id: orgId } }).then((r) => r.data);
export const getFindingDetail = (findingId) =>
  api.get(`/compliance/findings/${findingId}`).then((r) => r.data);

// Compliance Pipeline summaries
export const getSiteComplianceSummary = (siteId) =>
  api.get(`/compliance/sites/${siteId}/summary`).then((r) => r.data);
export const getPortfolioComplianceSummary = (params = {}) =>
  api.get('/compliance/portfolio/summary', { params }).then((r) => r.data);
export const getComplianceTimeline = () => api.get('/compliance/timeline').then((r) => r.data);
export const getComplianceScoreTrend = (params = {}) =>
  cachedGet('/compliance/score-trend', { params }).then((r) => r.data);

// CEE Pipeline + M&V
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

// ── Watchers ──
export const listWatchers = () => api.get('/watchers/list').then((r) => r.data);
export const runWatcher = (name) => api.post(`/watchers/${name}/run`).then((r) => r.data);
export const listRegEvents = (source = null, reviewed = null, status = null) =>
  api.get('/watchers/events', { params: { source, reviewed, status } }).then((r) => r.data);
export const reviewRegEvent = (eventId, decision = 'apply', notes = '') =>
  api.patch(`/watchers/events/${eventId}/review`, { decision, notes }).then((r) => r.data);
export const getRegEventDetail = (eventId) =>
  api.get(`/watchers/events/${eventId}`).then((r) => r.data);

// ── Tertiaire / OPERAT ──
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

export const getTertiaireSiteSignals = (params = {}) =>
  api.get(`${TERT_BASE}/site-signals`, { params }).then((r) => r.data);

export const getTertiaireCatalog = (orgId = 1) =>
  api.get(`${TERT_BASE}/catalog`, { params: { org_id: orgId } }).then((r) => r.data);

export const getTertiaireProofCatalog = () =>
  api.get(`${TERT_BASE}/proof-catalog`).then((r) => r.data);

export const getTertiaireEfaProofs = (efaId, year = null) =>
  api.get(`${TERT_BASE}/efa/${efaId}/proofs`, { params: year ? { year } : {} }).then((r) => r.data);

export const linkTertiaireProof = (efaId, body) =>
  api.post(`${TERT_BASE}/efa/${efaId}/proofs/link`, body).then((r) => r.data);

export const getOperatProofCatalogV2 = () =>
  api.get(`${TERT_BASE}/proofs/catalog`).then((r) => r.data);

// OPERAT Trajectory
export const validateEfaTrajectory = (efaId, year) =>
  api.get(`${TERT_BASE}/efa/${efaId}/targets/validate`, { params: { year } }).then((r) => r.data);
export const getEfaProofEvents = (efaId) =>
  api.get(`${TERT_BASE}/efa/${efaId}/proof-events`).then((r) => r.data);

export const getIssueProofs = (issueCode) =>
  api.get(`${TERT_BASE}/issues/${issueCode}/proofs`).then((r) => r.data);

export const createOperatProofTemplates = (efaId, year, body) =>
  api
    .post(`${TERT_BASE}/efa/${efaId}/proofs/templates`, body, { params: { year } })
    .then((r) => r.data);

// V113: OPERAT Export
export const exportOperatCsv = (orgId, year, efaIds = null) =>
  api
    .post('/operat/export', { org_id: orgId, year, efa_ids: efaIds }, { responseType: 'blob' })
    .then((r) => r.data);
export const previewOperatExport = (orgId, year, efaIds = null) =>
  api.post('/operat/export/preview', { org_id: orgId, year, efa_ids: efaIds }).then((r) => r.data);

// Export manifests (chaine de preuve)
export const getExportManifests = (orgId) =>
  api.get('/operat/export-manifests', { params: { org_id: orgId } }).then((r) => r.data);
export const getExportManifest = (manifestId) =>
  api.get(`/operat/export-manifests/${manifestId}`).then((r) => r.data);

// ── BACS Expert ──
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

// BACS Regulatory
export const getBacsRegulatoryAssessment = (siteId) =>
  api.get(`/regops/bacs/site/${siteId}/regulatory-assessment`).then((r) => r.data);
export const getBacsComplianceGate = (siteId) =>
  api.get(`/regops/bacs/site/${siteId}/compliance-gate`).then((r) => r.data);
export const createBacsRemediation = (siteId, data) =>
  api.post(`/regops/bacs/site/${siteId}/remediation`, data).then((r) => r.data);
export const listBacsRemediations = (siteId) =>
  api.get(`/regops/bacs/site/${siteId}/remediation`).then((r) => r.data);
export const attachBacsProof = (actionId, data) =>
  api.post(`/regops/bacs/remediation/${actionId}/attach-proof`, data).then((r) => r.data);
export const reviewBacsProof = (actionId, data) =>
  api.post(`/regops/bacs/remediation/${actionId}/review-proof`, data).then((r) => r.data);
