/**
 * PROMEOS - API Enedis
 * Promotion pipeline health, runs, backlog + NAF estimator
 */
import api from './core';

// ── Promotion pipeline ──
export const getPromotionHealth = () => api.get('/enedis/promotion/health').then((r) => r.data);

export const getPromotionRuns = (limit = 20, offset = 0) =>
  api.get(`/enedis/promotion/runs?limit=${limit}&offset=${offset}`).then((r) => r.data);

export const getPromotionRun = (id) => api.get(`/enedis/promotion/runs/${id}`).then((r) => r.data);

export const getPromotionBacklog = (status = 'pending', limit = 50) =>
  api.get(`/enedis/promotion/backlog?status=${status}&limit=${limit}`).then((r) => r.data);

export const triggerPromotion = (mode = 'incremental', dryRun = false) =>
  api.post(`/enedis/promotion/promote?mode=${mode}&dry_run=${dryRun}`).then((r) => r.data);

// ── NAF estimator ──
export const estimateReferenceCurve = (nafCode, powerKva, months = 12) =>
  api
    .get(
      `/usages/estimate/reference-curve?naf_code=${encodeURIComponent(nafCode)}&power_kva=${powerKva}&months=${months}`
    )
    .then((r) => r.data);

// ── ODS freshness ──
export const getOpendataFreshness = () => api.get('/enedis/opendata/freshness').then((r) => r.data);

export const refreshOpendata = (dataset = 'sup36', dateFrom = null, dateTo = null) => {
  const params = new URLSearchParams({ dataset });
  if (dateFrom) params.append('date_from', dateFrom);
  if (dateTo) params.append('date_to', dateTo);
  return api.post(`/enedis/opendata/refresh?${params}`).then((r) => r.data);
};

// ── Site analytics (Sprint A — Cockpit Site360 enrichi) ──
export const getLoadProfile = (siteId, months = 12) =>
  api.get(`/usages/load-profile/${siteId}?months=${months}`).then((r) => r.data);

export const getEnergySignatureAdvanced = (siteId, months = 12, model = 'auto') =>
  api
    .get(`/usages/energy-signature/${siteId}/advanced?months=${months}&model=${model}`)
    .then((r) => r.data);

export const getSiteBenchmark = (siteId, months = 12) =>
  api.get(`/usages/benchmark/${siteId}?months=${months}`).then((r) => r.data);

export const generateRecommendations = (siteId, persist = true) =>
  api.post(`/usages/recommendations/generate/${siteId}?persist=${persist}`).then((r) => r.data);

export const compareSiteVsSector = (siteId, months = 12, persistAlerts = false) =>
  api
    .get(
      `/usages/compare/site-vs-sector/${siteId}?months=${months}&persist_alerts=${persistAlerts}`
    )
    .then((r) => r.data);
