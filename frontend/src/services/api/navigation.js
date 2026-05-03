/**
 * PROMEOS — API navigation badges (Phase 2.B P1.2.bis).
 *
 * Source de vérité unique des compteurs nav rail/panel — remplace les
 * 3 fetches dispersés Sidebar/AppShell (getNotificationsSummary,
 * getMonitoringAlerts, getActionCenterActionsSummary +
 * getActionCenterNotifications).
 *
 * Backend : GET /api/v1/navigation/badges (Phase 2.A — commit 6c4cc362).
 */

import api from './core';

/**
 * Fetch les compteurs agrégés rail/panel (NavBadgesResponse).
 *
 * Pas de `cachedGet` ici : le NavigationBadgesContext gère son propre
 * polling (stale-while-revalidate) avec un interval piloté par le
 * `cache_ttl_seconds` du payload — un cache GET en plus créerait une
 * double couche de TTL et masquerait les refetch volontaires.
 *
 * @returns {Promise<{
 *   energy_alerts: number,
 *   compliance_alerts: number,
 *   billing_anomalies: number,
 *   purchase_deadlines: number,
 *   action_center: number,
 *   conformite_dt_progress: number,
 *   conformite_bacs_progress: number,
 *   conformite_aper_progress: number,
 *   computed_at: string,
 *   cache_ttl_seconds: number,
 * }>}
 */
// Note : core.js axios baseURL='/api' → ne pas répéter le prefix dans l'URL.
// Bug double-prefix /api/api/v1/... fixé Phase 2 post-merge ccfb6420.
export const getNavigationBadges = () => api.get('/v1/navigation/badges').then((r) => r.data);
