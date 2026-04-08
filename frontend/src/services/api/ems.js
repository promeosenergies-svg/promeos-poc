/**
 * PROMEOS — API EMS Tier 1
 * Hiérarchie, courbe de charge, qualité données, rapports.
 */
import api, { cachedGet } from './core';

// ── Hiérarchie Org → Portefeuille → Site → Meter ──
export const getEmsHierarchy = (orgId) =>
  cachedGet('/ems/hierarchy', { params: { org_id: orgId } }).then((r) => r.data);

// ── Courbe de charge (CDC) par compteur ──
export const getEmsCdc = (meterId, start, end, granularity = '30min') =>
  cachedGet(`/ems/cdc/${meterId}`, { params: { start, end, granularity } }).then((r) => r.data);

// ── Qualité données par site ──
export const getEmsDataQuality = (siteId) =>
  cachedGet(`/ems/data-quality/${siteId}`).then((r) => r.data);

// ── Génération rapport PDF ──
export const generateEmsReport = (siteId, periodStart, periodEnd, format = 'pdf') =>
  api.post(
    '/ems/reports/generate',
    { site_id: siteId, period_start: periodStart, period_end: periodEnd, format },
    { responseType: 'blob' }
  );
