/**
 * PROMEOS — API events upcoming (Phase 1.C Sprint α-fin).
 *
 * Wrapper du nouvel endpoint REST `GET /api/v1/events/upcoming`
 * (Phase 1.A backend, commit a3b48f07). Consommé via EventsContext +
 * useEvents hook — jamais directement par les pages (cf SG_EVENTS_FE_01).
 *
 * Backend : event_bus.compute_events → events_query_service
 * (filtres persona / page_key / horizon_days / pagination cursor).
 *
 * Pas de cachedGet : EventsContext gère son propre polling
 * (stale-while-revalidate + TTL backend-driven cache_ttl_seconds).
 */

import api from './core';

/**
 * Fetch la page courante des événements en attente, scope org.
 *
 * @param {object} params
 * @param {string|null} [params.pageKey] - Clé page (cockpit_daily, conformite, ...).
 * @param {string|null} [params.persona] - Persona (energy_manager, daf, ...).
 * @param {number}      [params.horizonDays=30]
 * @param {string|null} [params.cursor] - Pagination cursor base64 opaque.
 * @param {number}      [params.limit=20]
 * @param {AbortSignal|null} [params.signal] - AbortController.signal pour cancel race.
 * @returns {Promise<{
 *   events: Array,
 *   next_cursor: string|null,
 *   total: number,
 *   computed_at: string,
 *   cache_ttl_seconds: number,
 * }>}
 */
export const getUpcomingEvents = ({
  pageKey = null,
  persona = null,
  horizonDays = 30,
  cursor = null,
  limit = 20,
  signal = null,
} = {}) => {
  const qs = new URLSearchParams();
  if (pageKey) qs.set('page_key', pageKey);
  if (persona) qs.set('persona', persona);
  qs.set('horizon_days', String(horizonDays));
  if (cursor) qs.set('cursor', cursor);
  qs.set('limit', String(limit));
  // Note : `core.js` configure axios `baseURL='/api'` → ne pas répéter le prefix
  // dans l'URL ici. Bug surfaced par smoke Playwright post-merge ccfb6420
  // (double prefix `/api/api/v1/...` → 404). Aligné convention autres wrappers.
  return api
    .get(`/v1/events/upcoming?${qs.toString()}`, signal ? { signal } : undefined)
    .then((r) => r.data);
};
