/**
 * PROMEOS - API Energy
 * Consumption, EMS, monitoring, emissions, usages, consumption context
 */
import api, { cachedGet } from './core';

// ── Consommations ──
export const getConsommations = async (params = {}) => {
  const response = await api.get('/consommations', { params });
  return response.data;
};

// ── Energy (Import & Analysis) ──
export const getMeters = (siteId = null) =>
  api.get('/energy/meters', { params: { site_id: siteId } }).then((r) => r.data);
export const createMeter = (data) => api.post('/energy/meters', data).then((r) => r.data);
export const uploadConsumptionData = (file, meterId, frequency = 'hourly') => {
  const formData = new FormData();
  formData.append('file', file);
  return api
    .post('/energy/import/upload', formData, {
      params: { meter_id: meterId, frequency },
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data);
};
export const getImportJobs = (meterId = null) =>
  api.get('/energy/import/jobs', { params: { meter_id: meterId } }).then((r) => r.data);
export const runAnalysis = (meterId) =>
  api.post('/energy/analysis/run', null, { params: { meter_id: meterId } }).then((r) => r.data);
export const getAnalysisSummary = (meterId) =>
  api.get('/energy/analysis/summary', { params: { meter_id: meterId } }).then((r) => r.data);
export const generateDemoEnergy = (data) =>
  api.post('/energy/demo/generate', data).then((r) => r.data);

// ── Consumption Diagnostic ──
export const getConsumptionInsights = (orgId = null) =>
  api.get('/consumption/insights', { params: { org_id: orgId } }).then((r) => r.data);
export const getConsumptionSite = (siteId) =>
  api.get(`/consumption/site/${siteId}`).then((r) => r.data);
export const runConsumptionDiagnose = (orgId = null, days = 30) =>
  api.post('/consumption/diagnose', null, { params: { org_id: orgId, days } }).then((r) => r.data);
export const seedDemoConsumption = (siteId = null, days = 30) =>
  api
    .post('/consumption/seed-demo', null, { params: { site_id: siteId, days } })
    .then((r) => r.data);
export const patchConsumptionInsight = (insightId, data) =>
  api.patch(`/consumption/insights/${insightId}`, data).then((r) => r.data);

// ── Consumption Explorer ──
export const getConsumptionAvailability = (siteId, energyType = 'electricity') =>
  cachedGet('/consumption/availability', {
    params: { site_id: siteId, energy_type: energyType },
  }).then((r) => r.data);

// Tunnel (envelope P10-P90)
export const getConsumptionTunnel = (siteId, days = 90, energyType = 'electricity') =>
  api
    .get('/consumption/tunnel', { params: { site_id: siteId, days, energy_type: energyType } })
    .then((r) => r.data);
export const getConsumptionTunnelV2 = (
  siteId,
  days = 90,
  energyType = 'electricity',
  mode = 'energy',
  { startDate, endDate } = {}
) =>
  cachedGet('/consumption/tunnel_v2', {
    params: {
      site_id: siteId,
      days,
      energy_type: energyType,
      mode,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    },
  }).then((r) => r.data);

// Targets (objectifs & budgets)
export const getConsumptionTargets = (siteId, energyType = 'electricity', year = null) =>
  cachedGet('/consumption/targets', {
    params: { site_id: siteId, energy_type: energyType, year },
  }).then((r) => r.data);
export const createConsumptionTarget = (data) =>
  api.post('/consumption/targets', data).then((r) => r.data);
export const patchConsumptionTarget = (id, data) =>
  api.patch(`/consumption/targets/${id}`, data).then((r) => r.data);
export const deleteConsumptionTarget = (id) =>
  api.delete(`/consumption/targets/${id}`).then((r) => r.data);
export const getTargetsProgression = (siteId, energyType = 'electricity', year = null) =>
  api
    .get('/consumption/targets/progression', {
      params: { site_id: siteId, energy_type: energyType, year },
    })
    .then((r) => r.data);
export const getTargetsProgressionV2 = (siteId, energyType = 'electricity', year = null) =>
  cachedGet('/consumption/targets/progress_v2', {
    params: { site_id: siteId, energy_type: energyType, year },
  }).then((r) => r.data);

// TOU Schedules (grilles HP/HC)
export const getTOUSchedules = (siteId, meterId = null, activeOnly = true) =>
  api
    .get('/consumption/tou_schedules', {
      params: { site_id: siteId, meter_id: meterId, active_only: activeOnly },
    })
    .then((r) => r.data);
export const getActiveTOUSchedule = (siteId, meterId = null, refDate = null) =>
  api
    .get('/consumption/tou_schedules/active', {
      params: { site_id: siteId, meter_id: meterId, ref_date: refDate },
    })
    .then((r) => r.data);
export const createTOUSchedule = (data) =>
  api.post('/consumption/tou_schedules', data).then((r) => r.data);
export const patchTOUSchedule = (id, data) =>
  api.patch(`/consumption/tou_schedules/${id}`, data).then((r) => r.data);
export const deleteTOUSchedule = (id) =>
  api.delete(`/consumption/tou_schedules/${id}`).then((r) => r.data);

// HP/HC Ratio
export const getHPHCRatio = (siteId, meterId = null, days = 30) =>
  api
    .get('/consumption/hp_hc', { params: { site_id: siteId, meter_id: meterId, days } })
    .then((r) => r.data);
export const getHPHCBreakdownV2 = (
  siteId,
  days = 30,
  calendarId = null,
  simulate = false,
  { startDate, endDate } = {}
) =>
  cachedGet('/consumption/hphc_breakdown_v2', {
    params: {
      site_id: siteId,
      days,
      calendar_id: calendarId,
      simulate,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    },
  }).then((r) => r.data);

// Gas Summary
export const getGasSummary = (siteId, days = 90, { startDate, endDate } = {}) =>
  cachedGet('/consumption/gas/summary', {
    params: {
      site_id: siteId,
      days,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    },
  }).then((r) => r.data);
export const getGasWeatherNormalized = (siteId, days = 90, { startDate, endDate } = {}) =>
  cachedGet('/consumption/gas/weather_normalized', {
    params: {
      site_id: siteId,
      days,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    },
  }).then((r) => r.data);

// ── EMS Consumption Explorer ──
export const getEmsTimeseries = (params) =>
  cachedGet('/ems/timeseries', { params }).then((r) => r.data);
export const getEmsTimeseriesSuggest = (dateFrom, dateTo) =>
  cachedGet('/ems/timeseries/suggest', { params: { date_from: dateFrom, date_to: dateTo } }).then(
    (r) => r.data
  );
export const getEmsCompareSummary = (params) =>
  cachedGet('/ems/timeseries/compare-summary', { params }).then((r) => r.data);
export const getEmsWeather = (siteId, dateFrom, dateTo) =>
  api
    .get('/ems/weather', { params: { site_id: siteId, date_from: dateFrom, date_to: dateTo } })
    .then((r) => r.data);
export const getEmsWeatherMulti = (siteIds, dateFrom, dateTo) =>
  api
    .get('/ems/weather', {
      params: { site_ids: siteIds.join(','), date_from: dateFrom, date_to: dateTo },
    })
    .then((r) => r.data);
export const getEmsReferenceProfile = (
  siteId,
  dateFrom,
  dateTo,
  famille,
  puissance,
  granularity = 'daily'
) =>
  api
    .get('/ems/reference_profile', {
      params: {
        site_id: siteId,
        date_from: dateFrom,
        date_to: dateTo,
        famille,
        puissance,
        granularity,
      },
    })
    .then((r) => r.data);
export const getEmsWeatherHourly = (siteId, dateFrom, dateTo) =>
  api
    .get('/ems/weather_hourly', {
      params: { site_id: siteId, date_from: dateFrom, date_to: dateTo },
    })
    .then((r) => r.data);
export const runEmsSignature = (siteId, dateFrom, dateTo, meterIds = null) =>
  api
    .post('/ems/signature/run', null, {
      params: { site_id: siteId, date_from: dateFrom, date_to: dateTo, meter_ids: meterIds },
    })
    .then((r) => r.data);
export const runEmsSignaturePortfolio = (siteIds, dateFrom, dateTo) =>
  api
    .post('/ems/signature/portfolio', null, {
      params: { site_ids: siteIds.join(','), date_from: dateFrom, date_to: dateTo },
    })
    .then((r) => r.data);
export const getEmsViews = (userId = null) =>
  api.get('/ems/views', { params: userId ? { user_id: userId } : {} }).then((r) => r.data);
export const createEmsView = (name, configJson, userId = null) =>
  api
    .post('/ems/views', null, { params: { name, config_json: configJson, user_id: userId } })
    .then((r) => r.data);
export const updateEmsView = (id, params) =>
  api.put(`/ems/views/${id}`, null, { params }).then((r) => r.data);
export const deleteEmsView = (id) => api.delete(`/ems/views/${id}`).then((r) => r.data);

// Collections (paniers de sites)
export const getEmsCollections = () => api.get('/ems/collections').then((r) => r.data);
export const createEmsCollection = (name, siteIds, scopeType = 'custom', isFavorite = false) =>
  api
    .post('/ems/collections', null, {
      params: { name, site_ids: siteIds.join(','), scope_type: scopeType, is_favorite: isFavorite },
    })
    .then((r) => r.data);
export const updateEmsCollection = (id, params) =>
  api.put(`/ems/collections/${id}`, null, { params }).then((r) => r.data);
export const deleteEmsCollection = (id) => api.delete(`/ems/collections/${id}`).then((r) => r.data);

// Usage suggest & benchmark
export const getUsageSuggest = (siteId) =>
  api.get('/ems/usage_suggest', { params: { site_id: siteId } }).then((r) => r.data);
export const getEmsBenchmark = (siteId) =>
  api.get('/ems/benchmark', { params: { site_id: siteId } }).then((r) => r.data);
export const getScheduleSuggest = (siteId, days = 90) =>
  api.get('/ems/schedule_suggest', { params: { site_id: siteId, days } }).then((r) => r.data);

// Demo data
export const generateEmsDemo = (portfolioSize = 12, days = 365, seed = 123, force = false) =>
  api
    .post('/ems/demo/generate', null, {
      params: { portfolio_size: portfolioSize, days, seed, force },
    })
    .then((r) => r.data);
export const purgeEmsDemo = () => api.post('/ems/demo/purge').then((r) => r.data);

// ── Monitoring (Electric Performance) ──
export const getMonitoringKpis = (siteId) =>
  api.get('/monitoring/kpis', { params: { site_id: siteId } }).then((r) => r.data);
export const runMonitoring = (siteId, days = 90) =>
  api.post('/monitoring/run', { site_id: siteId, days }).then((r) => r.data);
export const getMonitoringSnapshots = (siteId, limit = 10) =>
  api.get('/monitoring/snapshots', { params: { site_id: siteId, limit } }).then((r) => r.data);
export const getMonitoringAlerts = (siteId, status = null, limit = 50) =>
  api.get('/monitoring/alerts', { params: { site_id: siteId, status, limit } }).then((r) => r.data);
export const ackMonitoringAlert = (id) =>
  api.post(`/monitoring/alerts/${id}/ack`, { acknowledged_by: 'user' }).then((r) => r.data);
export const resolveMonitoringAlert = (id, note = null) =>
  api
    .post(`/monitoring/alerts/${id}/resolve`, { resolved_by: 'user', resolution_note: note })
    .then((r) => r.data);
export const generateMonitoringDemo = (siteId, days = 90, profile = 'office') =>
  api.post('/monitoring/demo/generate', { site_id: siteId, days, profile }).then((r) => r.data);
export const getMonitoringKpisCompare = (
  siteId,
  mode = 'previous',
  customStart = null,
  customEnd = null
) =>
  api
    .get('/monitoring/kpis/compare', {
      params: { site_id: siteId, mode, custom_start: customStart, custom_end: customEnd },
    })
    .then((r) => r.data);

// ── Emissions / CO2e ──
export const getEmissions = (siteId) =>
  api.get('/monitoring/emissions', { params: { site_id: siteId } }).then((r) => r.data);
export const getEmissionFactors = () => api.get('/monitoring/emission-factors').then((r) => r.data);
export const seedEmissionFactors = () =>
  api.post('/monitoring/emission-factors/seed').then((r) => r.data);

// ── Consumption Context (Usages & Horaires) ──
export const getConsumptionContext = (siteId, days = 30) =>
  cachedGet(`/consumption-context/site/${siteId}`, { params: { days } }).then((r) => r.data);
export const getConsumptionProfile = (siteId, days = 30) =>
  cachedGet(`/consumption-context/site/${siteId}/profile`, { params: { days } }).then(
    (r) => r.data
  );
export const getConsumptionActivity = (siteId) =>
  cachedGet(`/consumption-context/site/${siteId}/activity`).then((r) => r.data);
export const getConsumptionAnomalies = (siteId, days = 30) =>
  cachedGet(`/consumption-context/site/${siteId}/anomalies`, { params: { days } }).then(
    (r) => r.data
  );
export const refreshConsumptionDiagnose = (siteId, days = 30) =>
  api
    .post(`/consumption-context/site/${siteId}/diagnose`, null, { params: { days } })
    .then((r) => r.data);
export const suggestSchedule = (siteId) =>
  api.get(`/consumption-context/site/${siteId}/suggest-schedule`).then((r) => r.data);
export const getDetectedSchedule = (siteId, windowDays = 56) =>
  api
    .get(`/consumption-context/site/${siteId}/activity/detected`, {
      params: { window_days: windowDays },
    })
    .then((r) => r.data);
export const compareSchedules = (siteId, windowDays = 56) =>
  api
    .get(`/consumption-context/site/${siteId}/activity/compare`, {
      params: { window_days: windowDays },
    })
    .then((r) => r.data);
export const applyDetectedSchedule = (siteId, windowDays = 56) =>
  api
    .post(`/consumption-context/site/${siteId}/activity/apply_detected`, null, {
      params: { window_days: windowDays },
    })
    .then((r) => r.data);
export const getPortfolioBehaviorSummary = (days = 30) =>
  cachedGet('/consumption-context/portfolio/summary', { params: { days } }).then((r) => r.data);

// Unified Consumption
export const getConsumptionUnifiedSite = (siteId, start, end, source = 'reconciled') =>
  api
    .get(`/consumption-unified/site/${siteId}`, { params: { start, end, source } })
    .then((r) => r.data);
export const getConsumptionUnifiedPortfolio = (start, end, source = 'reconciled') =>
  api.get('/consumption-unified/portfolio', { params: { start, end, source } }).then((r) => r.data);
export const getConsumptionReconcile = (siteId, start, end) =>
  api
    .get(`/consumption-unified/reconcile/${siteId}`, { params: { start, end } })
    .then((r) => r.data);

// ── Usages Energetiques ──
export const getUsagesDashboard = (siteId) =>
  cachedGet(`/usages/dashboard/${siteId}`).then((r) => r.data);
export const getUsageReadiness = (siteId) =>
  cachedGet(`/usages/readiness/${siteId}`).then((r) => r.data);
export const getMeteringPlan = (siteId) =>
  cachedGet(`/usages/metering-plan/${siteId}`).then((r) => r.data);
export const getTopUES = (siteId, limit = 5) =>
  cachedGet(`/usages/top-ues/${siteId}`, { params: { limit } }).then((r) => r.data);
export const getUsageCostBreakdown = (siteId, days = 365) =>
  cachedGet(`/usages/cost-breakdown/${siteId}`, { params: { days } }).then((r) => r.data);
export const getUsageTaxonomy = () => cachedGet('/usages/taxonomy').then((r) => r.data);
export const getSiteUsages = (siteId) => cachedGet(`/usages/site/${siteId}`).then((r) => r.data);
export const getUsageTimeline = (siteId, months = 12) =>
  cachedGet(`/usages/timeline/${siteId}`, { params: { months } }).then((r) => r.data);
export const getPortfolioUsageComparison = (orgId) =>
  cachedGet('/usages/portfolio-compare', { params: { org_id: orgId } }).then((r) => r.data);
export const getMeterReadingsPreview = (meterId, days = 7) =>
  cachedGet(`/usages/meter-readings/${meterId}`, { params: { days } }).then((r) => r.data);

// ── Usages scoped (multi-niveaux) ──
export const getScopedUsagesDashboard = ({
  entityId,
  portefeuilleId,
  siteId,
  archetypeCode,
} = {}) =>
  cachedGet('/usages/scoped-dashboard', {
    params: {
      entity_id: entityId || undefined,
      portefeuille_id: portefeuilleId || undefined,
      site_id: siteId || undefined,
      archetype_code: archetypeCode || undefined,
    },
  }).then((r) => r.data);

export const getScopedUsageTimeline = ({
  entityId,
  portefeuilleId,
  siteId,
  archetypeCode,
  months = 12,
} = {}) =>
  cachedGet('/usages/scoped-timeline', {
    params: {
      entity_id: entityId || undefined,
      portefeuille_id: portefeuilleId || undefined,
      site_id: siteId || undefined,
      archetype_code: archetypeCode || undefined,
      months,
    },
  }).then((r) => r.data);

export const getScopeTree = () => cachedGet('/patrimoine/scope-tree').then((r) => r.data);

// ── SIRENE Lookup ──
export const lookupSiret = (siret) =>
  api.get(`/patrimoine/lookup-siret/${siret}`).then((r) => r.data);

// ── Usages archetypes in scope ──
export const getArchetypesInScope = ({ entityId, portefeuilleId, siteId } = {}) =>
  cachedGet('/usages/archetypes-in-scope', {
    params: {
      entity_id: entityId || undefined,
      portefeuille_id: portefeuilleId || undefined,
      site_id: siteId || undefined,
    },
  }).then((r) => r.data);

// ── Energy Intensity (Yannick #146) ──
export const getEnergyIntensity = (siteId, year = null) =>
  cachedGet('/energy/intensity', {
    params: { site_id: siteId, year: year || undefined },
  }).then((r) => r.data);

// ── Coût par période tarifaire ──
export const getCostByPeriod = (siteId, months = 12) =>
  cachedGet(`/usages/cost-by-period/${siteId}`, { params: { months } }).then((r) => r.data);

// ── Flex NEBEF ──
export const getFlexNebef = (siteId) =>
  cachedGet(`/usages/flex-potential/${siteId}`).then((r) => r.data);

export const getFlexNebefPortfolio = ({ entityId, portefeuilleId } = {}) =>
  cachedGet('/usages/flex-portfolio', {
    params: {
      entity_id: entityId || undefined,
      portefeuille_id: portefeuilleId || undefined,
    },
  }).then((r) => r.data);

// ── Signature énergétique (corrélation DJU) ──
export const getEnergySignature = (siteId, months = 12) =>
  cachedGet(`/usages/energy-signature/${siteId}`, { params: { months } }).then((r) => r.data);

// ── Optimisation puissance souscrite ──
export const getPowerOptimization = (siteId) =>
  cachedGet(`/usages/power-optimization/${siteId}`).then((r) => r.data);

// ── Site Intelligence (KB-driven) ──
export const getSiteIntelligence = (siteId) =>
  api.get(`/sites/${siteId}/intelligence`).then((r) => r.data);
export const getTopRecommendation = (siteId) =>
  api.get(`/sites/${siteId}/top-recommendation`).then((r) => r.data);
