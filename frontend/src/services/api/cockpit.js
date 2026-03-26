/**
 * PROMEOS - API Cockpit
 * Dashboard, data quality, segmentation, portfolio, notifications, alerts
 */
import api, { cachedGet } from './core';

// ── Alertes ──
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

// ── Dashboard 2 Minutes ──
export const getDashboard2min = () => api.get('/dashboard/2min').then((r) => r.data);

// ── Segmentation ──
export const getSegmentationQuestions = () =>
  api.get('/segmentation/questions').then((r) => r.data);
export const submitSegmentationAnswers = (answers) =>
  api.post('/segmentation/answers', { answers }).then((r) => r.data);
export const getSegmentationProfile = () => api.get('/segmentation/profile').then((r) => r.data);
export const recomputeSegmentation = () => api.post('/segmentation/recompute').then((r) => r.data);

// Next Best Step + Action Creation
export const getSegmentationNextStep = (portfolioId) =>
  api.get('/segmentation/next-step', { params: { portfolio_id: portfolioId } }).then((r) => r.data);
export const createActionFromRecommendation = (recommendationKey, portfolioId) =>
  api
    .post('/segmentation/actions/from-recommendation', {
      recommendation_key: recommendationKey,
      portfolio_id: portfolioId,
    })
    .then((r) => r.data);
export const createActionFromNextStep = (portfolioId) =>
  api
    .post('/segmentation/actions/from-next-step', { portfolio_id: portfolioId })
    .then((r) => r.data);

// ── Portfolio Consumption ──
// skipSiteHeader: portfolio = multi-sites, never filter by single site scope
export const getPortfolioSummary = (params = {}) =>
  cachedGet('/portfolio/consumption/summary', { params, skipSiteHeader: true }).then((r) => r.data);
export const getPortfolioSites = (params = {}) =>
  cachedGet('/portfolio/consumption/sites', { params, skipSiteHeader: true }).then((r) => r.data);

// ── Notifications ──
export const syncNotifications = (orgId = null) =>
  api
    .post('/notifications/sync', null, { params: orgId ? { org_id: orgId } : {} })
    .then((r) => r.data);
export const getNotificationsList = (params = {}) =>
  api.get('/notifications/list', { params }).then((r) => r.data);
export const getNotificationsSummary = (orgId = null, siteId = null) => {
  const params = {};
  if (orgId) params.org_id = orgId;
  if (siteId) params.site_id = siteId;
  return cachedGet('/notifications/summary', { params }).then((r) => r.data);
};
export const patchNotification = (id, data) =>
  api.patch(`/notifications/${id}`, data).then((r) => r.data);
export const getNotificationPreferences = (orgId = null) =>
  api
    .get('/notifications/preferences', { params: orgId ? { org_id: orgId } : {} })
    .then((r) => r.data);
export const putNotificationPreferences = (data, orgId = null) =>
  api
    .put('/notifications/preferences', data, { params: orgId ? { org_id: orgId } : {} })
    .then((r) => r.data);

// ── Data Quality Dashboard ──
export const getDataQualityCompleteness = (orgId) =>
  cachedGet('/data-quality/completeness', { params: { org_id: orgId } }).then((r) => r.data);
export const getDataQualitySite = (siteId) =>
  cachedGet(`/data-quality/completeness/${siteId}`).then((r) => r.data);

// Data Quality Score (4 dimensions)
export const getDataQualityScore = (siteId) =>
  cachedGet(`/data-quality/site/${siteId}`).then((r) => r.data);
export const getDataQualityPortfolio = (orgId) =>
  cachedGet('/data-quality/portfolio', { params: { org_id: orgId } }).then((r) => r.data);

// Data Freshness
export const getSiteFreshness = (siteId) =>
  cachedGet(`/data-quality/freshness/${siteId}`).then((r) => r.data);

// ── Onboarding Stepper ──
export const getOnboardingProgress = (orgId) =>
  cachedGet('/onboarding-progress', { params: { org_id: orgId } }).then((r) => r.data);
export const updateOnboardingStep = (orgId, step, done = true) =>
  api
    .patch('/onboarding-progress/step', { step, done }, { params: { org_id: orgId } })
    .then((r) => r.data);
export const dismissOnboarding = (orgId) =>
  api.post('/onboarding-progress/dismiss', null, { params: { org_id: orgId } }).then((r) => r.data);
export const autoDetectOnboarding = (orgId) =>
  api.post('/onboarding-progress/auto', null, { params: { org_id: orgId } }).then((r) => r.data);

// ── Cockpit Executive ──
export const getCockpit = () => cachedGet('/cockpit').then((r) => r.data);
export const getCockpitTrajectory = () => cachedGet('/cockpit/trajectory').then((r) => r.data);
export const getCockpitBenchmark = () => cachedGet('/cockpit/benchmark').then((r) => r.data);
export const getCockpitCo2 = () => cachedGet('/cockpit/co2').then((r) => r.data);
export const getCockpitConsoMonth = () => cachedGet('/cockpit/conso-month').then((r) => r.data);

// ── Health + Meta ──
export const getApiHealth = () => api.get('/health').then((r) => r.data);
export const getMetaVersion = () =>
  api
    .get('/meta/version')
    .then((r) => r.data)
    .catch(() => null);
