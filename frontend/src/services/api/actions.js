/**
 * PROMEOS - API Actions
 * Action Hub, anomalies, copilot, action templates, reports, guidance
 */
import api, { cachedGet } from './core';

// ── Action Hub ──
export const createAction = (data) => api.post('/actions', data).then((r) => r.data);
export const syncActions = (orgId = null) =>
  api.post('/actions/sync', null, { params: orgId ? { org_id: orgId } : {} }).then((r) => r.data);
export const getActionsList = (params = {}) =>
  cachedGet('/actions/list', { params }).then((r) => r.data);
export const getActionsSummary = (orgId = null, siteId = null) => {
  const params = {};
  if (orgId) params.org_id = orgId;
  if (siteId) params.site_id = siteId;
  return cachedGet('/actions/summary', { params }).then((r) => r.data);
};
export const patchAction = (id, data) => api.patch(`/actions/${id}`, data).then((r) => r.data);
export const getActionBatches = (orgId = null) =>
  api.get('/actions/batches', { params: orgId ? { org_id: orgId } : {} }).then((r) => r.data);
export const exportActionsCSV = (params = {}) =>
  api.get('/actions/export.csv', { params, responseType: 'blob' });

// Action Detail + Sub-resources
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

// Action <> Proof persistence
export const getActionProofs = (actionId) =>
  api.get(`/actions/${actionId}/proofs`).then((r) => r.data);
export const linkProofToAction = (actionId, kbDocId) =>
  api.post(`/actions/${actionId}/proofs/${kbDocId}`).then((r) => r.data);

// Anomaly <> Action Link
export const createAnomalyActionLink = (data) =>
  api.post('/actions/anomaly-links', data).then((r) => r.data);
export const dismissAnomaly = (data) =>
  api.post('/actions/anomaly-dismiss', data).then((r) => r.data);
export const getAnomalyStatuses = (anomalies) =>
  api.post('/actions/anomaly-statuses', { anomalies }).then((r) => r.data);

// Action closeability check
export const checkActionCloseability = (actionId) =>
  api.get(`/actions/${actionId}/closeability`).then((r) => r.data);

// ── Action Templates ──
export const getActionTemplates = (category = null) =>
  cachedGet('/action-templates', { params: category ? { category } : {} }).then((r) => r.data);
export const seedActionTemplates = () => api.post('/action-templates/seed').then((r) => r.data);

// ── Energy Copilot ──
export const getCopilotActions = (orgId, params = {}) =>
  cachedGet('/copilot/actions', { params: { org_id: orgId, ...params } }).then((r) => r.data);
export const runCopilot = (orgId) =>
  api.post('/copilot/run', { org_id: orgId }).then((r) => r.data);
export const validateCopilotAction = (actionId) =>
  api.post(`/copilot/actions/${actionId}/validate`).then((r) => r.data);
export const rejectCopilotAction = (actionId, reason = '') =>
  api.post(`/copilot/actions/${actionId}/reject`, { reason }).then((r) => r.data);

// ── Guidance (Action Plan + Readiness) ──
export const getActionPlan = (params = {}) =>
  api.get('/guidance/action-plan', { params }).then((r) => r.data);
export const getReadiness = () => api.get('/guidance/readiness').then((r) => r.data);

// ── Reports ──
export const getAuditReportJSON = (orgId = null) =>
  api.get('/reports/audit.json', { params: orgId ? { org_id: orgId } : {} }).then((r) => r.data);
export const downloadAuditPDF = (orgId = null) =>
  api.get('/reports/audit.pdf', { params: orgId ? { org_id: orgId } : {}, responseType: 'blob' });

// ── Action Center (unified issues) ──
export const getActionCenterIssues = (params = {}) =>
  cachedGet('/action-center/issues', { params }, 30000);
export const getActionCenterSummary = () => cachedGet('/action-center/summary', {}, 30000);

// ── Action Center Workflow ──
export const getActionCenterActions = (params = {}) =>
  cachedGet('/action-center/actions', { params }, 15000);
export const createActionCenterAction = (data) =>
  api.post('/action-center/actions', data).then((r) => r.data);
export const updateActionCenterAction = (id, data) =>
  api.patch(`/action-center/actions/${id}`, data).then((r) => r.data);
export const resolveActionCenterAction = (id, data = {}) =>
  api.post(`/action-center/actions/${id}/resolve`, data).then((r) => r.data);
export const reopenActionCenterAction = (id, data = {}) =>
  api.post(`/action-center/actions/${id}/reopen`, data).then((r) => r.data);

// ── Action Center Summary (persisted actions) ──
export const getActionCenterActionsSummary = () =>
  cachedGet('/action-center/actions/summary', {}, 15000);

// ── Action Center Audit Trail ──
export const getActionCenterHistory = (actionId) =>
  cachedGet(`/action-center/actions/${actionId}/history`, {}, 10000);
export const getActionCenterEvidence = (actionId) =>
  cachedGet(`/action-center/actions/${actionId}/evidence`, {}, 10000);
export const addActionCenterEvidence = (actionId, data) =>
  api.post(`/action-center/actions/${actionId}/evidence`, data).then((r) => r.data);
export const exportActionCenterDossier = (actionId) =>
  cachedGet(`/action-center/actions/${actionId}/export`, {}, 5000);

// ── Action Center Notifications ──
export const getActionCenterNotifications = (params = {}) =>
  cachedGet('/action-center/notifications', { params }, 10000);
export const markNotificationRead = (id) =>
  api.post(`/action-center/notifications/${id}/read`).then((r) => r.data);

// ── Action Center Saved Views ──
export const getActionCenterViews = () => cachedGet('/action-center/views', {}, 60000);

// ── Action Center Bulk ──
export const bulkAssignOwner = (actionIds, owner) =>
  api
    .post('/action-center/actions/bulk/assign-owner', { action_ids: actionIds, owner })
    .then((r) => r.data);
export const bulkUpdateDueDate = (actionIds, dueDate) =>
  api
    .post('/action-center/actions/bulk/update-due-date', {
      action_ids: actionIds,
      due_date: dueDate,
    })
    .then((r) => r.data);
export const bulkUpdateStatus = (actionIds, status) =>
  api
    .post('/action-center/actions/bulk/update-status', { action_ids: actionIds, status })
    .then((r) => r.data);

// ── Action Center Management ──
export const getActionCenterManagementSummary = () =>
  cachedGet('/action-center/management-summary', {}, 15000);

// ── Action Center Executive ──
export const getActionCenterExecutiveSummary = (period = 30) =>
  cachedGet('/action-center/executive-summary', { params: { period } }, 15000);
export const getActionCenterTrends = (window = 30) =>
  cachedGet('/action-center/trends', { params: { window } }, 15000);

// ── Action Center Recommendations ──
export const getActionCenterRecommendations = (params = {}) =>
  cachedGet('/action-center/recommendations', { params }, 15000);
export const getActionCenterRecommendationsSummary = () =>
  cachedGet('/action-center/recommendations/summary', {}, 15000);

// ── Recommendation Decisions ──
export const acceptRecommendation = (recId, data = {}) =>
  api.post(`/action-center/recommendations/${recId}/accept`, data).then((r) => r.data);
export const dismissRecommendation = (recId, data) =>
  api.post(`/action-center/recommendations/${recId}/dismiss`, data).then((r) => r.data);
export const deferRecommendation = (recId, data = {}) =>
  api.post(`/action-center/recommendations/${recId}/defer`, data).then((r) => r.data);
export const convertRecommendationToAction = (recId, data) =>
  api.post(`/action-center/recommendations/${recId}/create-action`, data).then((r) => r.data);
export const getRecommendationDecisionStats = () =>
  cachedGet('/action-center/recommendations/decisions', {}, 15000);

// ── Recommendation Quality & Calibration ──
export const getRecommendationQualitySummary = (period = 30) =>
  cachedGet('/action-center/recommendations/quality-summary', { params: { period } }, 15000);
export const getRecommendationCalibration = () =>
  cachedGet('/action-center/recommendations/calibration', {}, 60000);

// ── Calibration Governance ──
export const getCalibrationHistory = () =>
  cachedGet('/action-center/recommendations/calibration/history', {}, 30000);
export const compareCalibrations = (v1, v2) =>
  cachedGet('/action-center/recommendations/calibration/compare', { params: { v1, v2 } }, 15000);
export const createCalibration = (data) =>
  api.post('/action-center/recommendations/calibration', data).then((r) => r.data);
export const activateCalibration = (version) =>
  api.post('/action-center/recommendations/calibration/activate', { version }).then((r) => r.data);
export const rollbackCalibration = () =>
  api.post('/action-center/recommendations/calibration/rollback').then((r) => r.data);

// ── Recommendation Outcomes ──
export const getRecommendationOutcomes = (limit = 50) =>
  cachedGet('/action-center/recommendations/outcomes', { params: { limit } }, 15000);
export const recordRecommendationOutcome = (data) =>
  api.post('/action-center/recommendations/outcomes', data).then((r) => r.data);

// ── Flex Foundation (Sprint 21) ──
export const getFlexAssets = (params = {}) => cachedGet('/flex/assets', { params }, 15000);
export const createFlexAsset = (data) => api.post('/flex/assets', data).then((r) => r.data);
export const updateFlexAsset = (id, data) =>
  api.patch(`/flex/assets/${id}`, data).then((r) => r.data);
export const syncBacsToFlexAssets = (siteId) =>
  cachedGet('/flex/assets/sync-from-bacs', { params: { site_id: siteId } }, 5000);
export const getFlexAssessment = (siteId) =>
  cachedGet('/flex/assessment', { params: { site_id: siteId } }, 15000);
