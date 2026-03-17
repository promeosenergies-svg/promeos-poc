/**
 * PROMEOS - API Purchase
 * Purchase, market prices, offer pricing
 */
import api, { cachedGet } from './core';

// ── Achat Energie ──
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
  cachedGet('/purchase/assistant', { params: orgId ? { org_id: orgId } : {} }).then((r) => r.data);

// Brique 3: WOW multi-site datasets
export const seedWowHappy = () => api.post('/purchase/seed-wow-happy').then((r) => r.data);
export const seedWowDirty = () => api.post('/purchase/seed-wow-dirty').then((r) => r.data);

// Portfolio, Renewals, History, Actions
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

// ── Marche Energie ──
export const getMarketPrices = (params = {}) =>
  cachedGet('/market/prices', { params }).then((r) => r.data);
export const getMarketContext = (energyType = 'ELEC') =>
  cachedGet('/market/context', { params: { energy_type: energyType } }).then((r) => r.data);

// ── V100: Offer Pricing V1 + Reconciliation ──
export const quoteOffer = (params) => api.post('/purchase/quote-offer', params).then((r) => r.data);
export const quoteMultiStrategy = (params) =>
  api.post('/purchase/quote-multi', params).then((r) => r.data);
export const reconcileOfferVsInvoice = (params) =>
  api.post('/purchase/reconcile', params).then((r) => r.data);
