/**
 * PROMEOS - API CX Dashboard (usage interne admin plateforme)
 * Consomme /api/admin/cx-dashboard/* — endpoints strict `require_platform_admin`
 * (DG_OWNER / DSI_ADMIN uniquement, pas de bypass DEMO_MODE).
 *
 * 3 drivers North-Star :
 *   - T2V  : Time-to-Value (p50/p90/p95 jours)
 *   - IAR  : Insight-to-Action Rate (actions validées / insights consultés)
 *   - WAU/MAU : Stickiness ratio
 */
import api from './core';

// Vue générale : events par org + inactive_orgs
export const getCxDashboard = (days = 30) =>
  api.get('/admin/cx-dashboard', { params: { days } }).then((r) => r.data);

// Time-to-Value — p50 / p90 / p95 en jours, par org
export const getT2V = (days = 180) =>
  api.get('/admin/cx-dashboard/t2v', { params: { days } }).then((r) => r.data);

// Insight-to-Action Rate — iar / iar_raw / is_capped, par org
export const getIAR = (days = 30) =>
  api.get('/admin/cx-dashboard/iar', { params: { days } }).then((r) => r.data);

// WAU / MAU — stickiness_ratio + interpretation
export const getWauMau = () => api.get('/admin/cx-dashboard/wau-mau').then((r) => r.data);
