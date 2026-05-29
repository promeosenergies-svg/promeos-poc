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

// ── Audit Energetique / SME (Loi 2025-391) ──
export const getAuditSmeAssessment = (orgId) =>
  api.get(`/regops/organisations/${orgId}/audit-sme`).then((r) => r.data);
export const getAuditSmeScope = () => api.get('/regops/audit-sme/scope').then((r) => r.data);
export const updateAuditSme = (orgId, payload) =>
  api.patch(`/regops/organisations/${orgId}/audit-sme`, payload).then((r) => r.data);
export const getAuditDeadlineStatus = (orgId) =>
  cachedGet('/regops/audit-deadline-status', { params: { org_id: orgId } }).then((r) => r.data);

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

/**
 * Score conformité portefeuille (org-scoped via intercepteur axios X-Org-Id).
 * Remplace le fetch() natif dans Cockpit.jsx — X-Org-Id injecté automatiquement.
 * Shape : { avg_score, high_confidence_count, total_sites, ... }
 */
export const getCompliancePortfolioScore = () =>
  api.get('/compliance/portfolio/score').then((r) => r.data);
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

// ── Mutualisation & Modulation DT (Phase 3) ──
export const getMutualisation = (orgId, jalon = 2030) =>
  api.get(`${TERT_BASE}/mutualisation`, { params: { org_id: orgId, jalon } }).then((r) => r.data);
export const simulateModulation = (body) =>
  api.post(`${TERT_BASE}/modulation-simulation`, body).then((r) => r.data);

// ── Sprint S3 — Groupes de structures (Article 14 arrêté 10/04/2020 modifié) ──
const MUTU_BASE = `${TERT_BASE}/mutualisation`;

/**
 * Liste les groupes de structures de l'organisation (actifs par défaut).
 * @param {number} orgId
 * @param {boolean} includeArchived
 */
export const listGroupeStructures = (orgId, includeArchived = false) =>
  api
    .get(`${MUTU_BASE}/groups`, {
      params: { org_id: orgId, include_archived: includeArchived },
    })
    .then((r) => r.data);

export const createGroupeStructures = (payload) =>
  api.post(`${MUTU_BASE}/groups`, payload).then((r) => r.data);

export const getGroupeStructures = (groupId, orgId) =>
  api.get(`${MUTU_BASE}/groups/${groupId}`, { params: { org_id: orgId } }).then((r) => r.data);

export const addGroupeStructuresMember = (groupId, orgId, payload) =>
  api
    .post(`${MUTU_BASE}/groups/${groupId}/members`, payload, { params: { org_id: orgId } })
    .then((r) => r.data);

export const removeGroupeStructuresMember = (groupId, efaId, orgId) =>
  api.delete(`${MUTU_BASE}/groups/${groupId}/members/${efaId}`, { params: { org_id: orgId } });

export const updateRepresentantLegal = (groupId, efaId, orgId, payload) =>
  api
    .patch(`${MUTU_BASE}/groups/${groupId}/members/${efaId}/rl`, payload, {
      params: { org_id: orgId },
    })
    .then((r) => r.data);

export const archiveGroupeStructures = (groupId, orgId) =>
  api
    .post(`${MUTU_BASE}/groups/${groupId}/archive`, null, { params: { org_id: orgId } })
    .then((r) => r.data);

/**
 * URL canonique de l'export Table 1B Annexe IV (CSV).
 * Le composant rend un lien `<a>` direct pour permettre le download natif
 * (axios + blob = friction inutile pour un fichier minimal).
 */
export const buildExportTable1bUrl = (groupId, orgId) =>
  `/api${TERT_BASE}/mutualisation/groups/${groupId}/export-table-1b?org_id=${orgId}`;

// Sprint S4 (2026-05-29) — endpoints avancés mutualisation.

/**
 * URL de l'export Table 1B Annexe IV au format PDF.
 * Le PDF inclut un hash SHA256 d'opposabilité (recalculable au contrôle ADEME).
 */
export const buildExportTable1bPdfUrl = (groupId, orgId) =>
  `/api${TERT_BASE}/mutualisation/groups/${groupId}/export-table-1b.pdf?org_id=${orgId}`;

/**
 * Crée (ou retourne l'existante) une action « Demander validation RL »
 * dans le Centre d'Action V4, signée par `external_ref` idempotent.
 */
export const requestRlValidation = (groupId, efaId, orgId) =>
  api
    .post(`${MUTU_BASE}/groups/${groupId}/members/${efaId}/request-validation`, null, {
      params: { org_id: orgId },
    })
    .then((r) => r.data);

/**
 * Renvoie la prochaine échéance ADEME + statut opposabilité du groupe
 * + action recommandée FR. Source : Art. R.174-31 CCH (vérification au
 * 31/12/2031, 2041, 2051 au plus tard).
 */
export const getMutualisationDeadlineStatus = (groupId, orgId) =>
  api
    .get(`${MUTU_BASE}/groups/${groupId}/deadline-status`, {
      params: { org_id: orgId },
    })
    .then((r) => r.data);

// ── DT Progress — Progression Décret Tertiaire ──
export const getSiteDtProgress = (siteId, annee = null) =>
  api
    .get(`${TERT_BASE}/sites/${siteId}/dt-progress`, { params: annee ? { annee } : {} })
    .then((r) => r.data);
export const getPortfolioDtProgress = (orgId, annee = null) =>
  api
    .get(`${TERT_BASE}/portfolio/${orgId}/dt-progress`, { params: annee ? { annee } : {} })
    .then((r) => r.data);

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

// BACS Derogation (Art. R.175-6)
export const listBacsExemptions = (siteId) =>
  api.get(`/regops/bacs/site/${siteId}/exemptions`).then((r) => r.data);
export const createBacsExemption = (siteId, data) =>
  api.post(`/regops/bacs/site/${siteId}/exemption`, data).then((r) => r.data);
export const getBacsExemption = (exemptionId) =>
  api.get(`/regops/bacs/exemption/${exemptionId}`).then((r) => r.data);
export const updateBacsExemption = (exemptionId, data) =>
  api.patch(`/regops/bacs/exemption/${exemptionId}`, data).then((r) => r.data);
export const submitBacsExemption = (exemptionId) =>
  api.post(`/regops/bacs/exemption/${exemptionId}/submit`).then((r) => r.data);
export const approveBacsExemption = (exemptionId, data = {}) =>
  api.post(`/regops/bacs/exemption/${exemptionId}/approve`, data).then((r) => r.data);
export const rejectBacsExemption = (exemptionId, data = {}) =>
  api.post(`/regops/bacs/exemption/${exemptionId}/reject`, data).then((r) => r.data);
export const deleteBacsExemption = (exemptionId) =>
  api.delete(`/regops/bacs/exemption/${exemptionId}`).then((r) => r.data);

// ── Regulatory Applicability (ADR-024) ─────────────────────────────────────
// P0-B 2026-05-23 : consommé par Patrimoine.jsx pour filtrer `?incomplete=<RULE>`.
export const getRegulatoryApplicability = (params = {}) =>
  api.get('/regulatory/applicability', { params }).then((r) => r.data);

// ── Contract Coverage (P0-C 2026-05-23) ────────────────────────────────────
// Couverture contractuelle d'un site (points de livraison ↔ contrats).
// Consommé par SiteContractsSummary.jsx + drawer Site360.
export const getSiteContractCoverage = (siteId) =>
  api.get(`/patrimoine/sites/${siteId}/contract-coverage`).then((r) => r.data);
