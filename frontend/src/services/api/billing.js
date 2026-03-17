/**
 * PROMEOS - API Billing
 * Billing, reconciliation, payment rules, invoices
 */
import api from './core';

// ── Bill Intelligence ──
export const getBillingSummary = (params = {}) =>
  api.get('/billing/summary', { params }).then((r) => r.data);
export const getBillingInsights = (params = {}) =>
  api.get('/billing/insights', { params }).then((r) => r.data);
export const getInsightDetail = (insightId) =>
  api.get(`/billing/insights/${insightId}`).then((r) => r.data);
export const getInvoiceShadowBreakdown = (invoiceId) =>
  api.get(`/billing/invoices/${invoiceId}/shadow-breakdown`).then((r) => r.data);

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

// PDF import + action creation + billing anomalies
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

// Timeline & Coverage
export const getBillingPeriods = (params = {}) =>
  api.get('/billing/periods', { params }).then((r) => r.data);
export const getCoverageSummary = (params = {}) =>
  api.get('/billing/coverage-summary', { params }).then((r) => r.data);
export const getMissingPeriods = (params = {}) =>
  api.get('/billing/missing-periods', { params }).then((r) => r.data);
export const getNormalizedInvoices = (params = {}) =>
  api.get('/billing/invoices/normalized', { params }).then((r) => r.data);
export const getBillingCompareMonthly = (params = {}) =>
  api.get('/billing/compare-monthly', { params }).then((r) => r.data);

// Reconciliation
export const getReconciliation = (siteId) =>
  api.get(`/patrimoine/sites/${siteId}/reconciliation`).then((r) => r.data);
export const getPortfolioReconciliation = (params = {}) =>
  api.get('/patrimoine/portfolio/reconciliation', { params }).then((r) => r.data);
export const postBillingReconcileAll = (months = 12) =>
  api.post('/billing/reconcile-all', null, { params: { months } }).then((r) => r.data);

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
