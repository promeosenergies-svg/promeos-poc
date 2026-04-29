/**
 * PROMEOS - API Cockpit
 * Dashboard, data quality, segmentation, portfolio, notifications, alerts
 */
import api, { cachedGet } from './core';

// ── Cockpit Facts (Phase 1.3.a SoT unifié — endpoint atomique) ──
// P0 fix /simplify Phase 3 : `.then(r => r.data)` aligné aux autres exports
// du fichier — sans cela, `facts` recevrait l'AxiosResponse complète et
// `facts?.consumption?.monthly_vs_n1` retournait undefined silencieusement.
export const getCockpitFacts = (period = 'current_week') =>
  cachedGet(`/cockpit/_facts?period=${encodeURIComponent(period)}`).then((r) => r.data);

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

// ── Top contributeurs Pareto (audit Jean-Marc 26/04 — drill-down "où sont mes 386 k€ ?") ──
// Shape : { contributors: [{ site_id, site_nom, total_eur, conformite_eur,
//   factures_eur, optimisation_eur, certainty }], total_eur, site_count, pareto_share_pct }
export const getTopContributors = (limit = 5) =>
  api.get(`/cockpit/top-contributors?limit=${limit}`).then((r) => r.data);

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
// Phase Refonte WOW : décisions Top 3 narrées (page Décision)
export const getCockpitDecisionsTop3 = () =>
  cachedGet('/cockpit/decisions/top3').then((r) => r.data);
// Phase Refonte WOW : facture portefeuille agrégée 5 sites (page Décision)
export const getPurchasePortfolioCostSimulation = (orgId) =>
  cachedGet(`/purchase/cost-simulation/portfolio/${orgId}`).then((r) => r.data);
// Phase Refonte WOW : priorités opérationnelles P1-P5 (page Pilotage file)
export const getCockpitPriorities = () => cachedGet('/cockpit/priorities').then((r) => r.data);
export const getCockpitBenchmark = () => cachedGet('/cockpit/benchmark').then((r) => r.data);
export const getCockpitCo2 = () => cachedGet('/cockpit/co2').then((r) => r.data);
export const getCockpitConsoMonth = () => cachedGet('/cockpit/conso-month').then((r) => r.data);

// ── Value Summary (CX Gap #6) ──
export const getValueSummary = (orgId) =>
  cachedGet('/value-summary', { params: { org_id: orgId } }).then((r) => r.data);

// ── Health + Meta ──
export const getApiHealth = () => api.get('/health').then((r) => r.data);
export const getMetaVersion = () =>
  api
    .get('/meta/version')
    .then((r) => r.data)
    .catch(() => null);
