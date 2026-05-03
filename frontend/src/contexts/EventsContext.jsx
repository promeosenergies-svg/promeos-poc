/**
 * PROMEOS — EventsContext (Phase 1.C Sprint α-fin).
 *
 * Source de vérité unique côté FE pour les événements `SolEventCard`
 * exposés par `GET /api/v1/events/upcoming` (Phase 1.A backend, commit
 * a3b48f07). Consommé via le hook `useEvents(pageKey, persona)`.
 *
 * Calque NavigationBadgesContext (P1.2.bis commit f036a99e) avec deux
 * différences imposées par le contexte events :
 *
 * 1. **Paramètres dynamiques** (pageKey, persona, horizonDays) : un
 *    changement déclenche un refetch ciblé. État interne `currentParams`
 *    + méthode `refetch(params)`.
 * 2. **AbortController** : si refetch lancé pendant un fetch en cours,
 *    le précédent est annulé pour éviter les races (page A → page B
 *    rapide, le 1ᵉʳ fetch retournerait après le 2ᵉ et écraserait l'état).
 *
 * Stratégie partagée avec NavigationBadges :
 *   - Stale-while-revalidate : on garde la dernière valeur valide
 *     pendant un refetch.
 *   - Refetch interval piloté par `cache_ttl_seconds` (default 300 s).
 *   - Retry 3× — au-delà bascule mode dégradé sans toast.
 *   - Aucune dépendance externe (KISS).
 *
 * Doctrine §6.2 anti-pattern "menus muets" : on expose toujours
 * `events: []` côté consommateurs (pas de undefined).
 */

import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { getUpcomingEvents } from '../services/api';

const EventsContext = createContext(null);

const DEFAULT_TTL_SECONDS = 300;
const MAX_RETRY_BEFORE_DEGRADED = 3;

const INITIAL_STATE = {
  data: null, // null = pas encore fetched (premier mount)
  loading: false,
  error: null, // Error | null — uniquement après MAX_RETRY_BEFORE_DEGRADED échecs
};

const INITIAL_PARAMS = {
  pageKey: null,
  persona: null,
  horizonDays: 30,
};

function paramsEqual(a, b) {
  return a.pageKey === b.pageKey && a.persona === b.persona && a.horizonDays === b.horizonDays;
}

export function EventsProvider({ children }) {
  const [state, setState] = useState(INITIAL_STATE);
  const [currentParams, setCurrentParams] = useState(INITIAL_PARAMS);
  const failureCountRef = useRef(0);
  const intervalRef = useRef(null);
  const ttlRef = useRef(DEFAULT_TTL_SECONDS);
  const cancelledRef = useRef(false);
  const abortRef = useRef(null);

  const fetchEvents = useCallback(async (params) => {
    // Cancel toute requête en vol — anti-race lors d'un refetch params changés
    if (abortRef.current) {
      abortRef.current.abort();
    }
    const controller = new AbortController();
    abortRef.current = controller;

    setState((prev) => ({ ...prev, loading: true }));
    try {
      const data = await getUpcomingEvents({
        pageKey: params.pageKey,
        persona: params.persona,
        horizonDays: params.horizonDays,
        signal: controller.signal,
      });
      if (cancelledRef.current || controller.signal.aborted) return null;
      failureCountRef.current = 0;
      if (typeof data?.cache_ttl_seconds === 'number' && data.cache_ttl_seconds > 0) {
        ttlRef.current = data.cache_ttl_seconds;
      }
      setState({ data, loading: false, error: null });
      return data;
    } catch (err) {
      if (cancelledRef.current || controller.signal.aborted) return null;
      // Axios cancel : pas un vrai échec, on n'incrémente pas le retry
      if (err?.name === 'CanceledError' || err?.code === 'ERR_CANCELED') {
        return null;
      }
      failureCountRef.current += 1;
      // Stale-while-revalidate : garde prev.data, expose error seulement
      // après MAX_RETRY_BEFORE_DEGRADED échecs consécutifs.
      setState((prev) => ({
        data: prev.data,
        loading: false,
        error: failureCountRef.current >= MAX_RETRY_BEFORE_DEGRADED ? err : null,
      }));
      return null;
    }
  }, []);

  /**
   * Refetch avec nouveaux paramètres. Si params identiques aux courants
   * → no-op pour éviter les fetches redondants (cf SG_EVENTS_FE_01).
   */
  const refetch = useCallback(
    (nextParams = {}) => {
      const merged = { ...currentParams, ...nextParams };
      if (!paramsEqual(merged, currentParams)) {
        setCurrentParams(merged);
      }
      return fetchEvents(merged);
    },
    [currentParams, fetchEvents]
  );

  useEffect(() => {
    cancelledRef.current = false;
    fetchEvents(currentParams);

    const tick = () => {
      if (cancelledRef.current) return;
      fetchEvents(currentParams);
      if (cancelledRef.current) return;
      intervalRef.current = setTimeout(tick, ttlRef.current * 1000);
    };
    intervalRef.current = setTimeout(tick, ttlRef.current * 1000);

    return () => {
      cancelledRef.current = true;
      if (intervalRef.current) clearTimeout(intervalRef.current);
      if (abortRef.current) abortRef.current.abort();
    };
  }, [currentParams.pageKey, currentParams.persona, currentParams.horizonDays, fetchEvents]);

  const value = { ...state, currentParams, refetch };

  return <EventsContext.Provider value={value}>{children}</EventsContext.Provider>;
}

/**
 * Hook bas-niveau d'accès au context. Lève une erreur hors Provider —
 * garde-fou contre une régression d'arbre. Le hook canonique consommé
 * par les pages reste `useEvents(pageKey, persona)` exporté depuis
 * `hooks/useEvents.js`.
 */
export function useEventsContext() {
  const ctx = useContext(EventsContext);
  if (ctx === null) {
    throw new Error('useEvents must be used within EventsProvider');
  }
  return ctx;
}
