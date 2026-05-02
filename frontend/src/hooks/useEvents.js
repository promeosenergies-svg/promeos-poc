/**
 * PROMEOS — useEvents (Phase 1.C Sprint α-fin).
 *
 * Hook de consommation du `EventsContext`. Déclenche un refetch ciblé
 * sur changement de pageKey ou persona, et expose une API plate
 * (events / total / nextCursor / loading / error) sans exposer la
 * mécanique interne du Provider (currentParams / refetch).
 *
 * Calque `useNavigationBadges` (P1.2.bis), avec paramétrage dynamique.
 *
 * Usage :
 *   const { events, loading, error, total } = useEvents('cockpit_daily', 'daf');
 */

import { useEffect, useMemo } from 'react';
import { useEventsContext } from '../contexts/EventsContext';

// Mapping role frontend (`AuthContext.role`) → persona endpoint.
// Aligné PERSONA_TO_OWNER_ROLES backend (events_query_service.py).
// Les rôles non listés → null (no filter persona côté endpoint).
const ROLE_TO_PERSONA = {
  ENERGY_MANAGER: 'energy_manager',
  DAF: 'daf',
  DG_OWNER: 'daf', // DG owner = décideur financier, même filtre que DAF
  ADMIN: 'admin',
  OPERATOR: 'operator',
};

/**
 * @param {string|null} pageKey - Literal canonique PageKey backend.
 * @param {string|null} [persona=null] - Persona endpoint OU rôle FE
 *   (auto-mappé via ROLE_TO_PERSONA). Passer `null` pour aucun filtre.
 */
export function useEvents(pageKey = null, persona = null) {
  const ctx = useEventsContext();

  // Auto-map role → persona si l'appelant passe un rôle FE
  const resolvedPersona = useMemo(() => {
    if (!persona) return null;
    return ROLE_TO_PERSONA[persona] ?? persona;
  }, [persona]);

  useEffect(() => {
    ctx.refetch({ pageKey, persona: resolvedPersona });
    // ctx.refetch est stable (useCallback) ; on ne dépend que des params
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pageKey, resolvedPersona]);

  return {
    events: ctx.data?.events ?? [],
    total: ctx.data?.total ?? 0,
    nextCursor: ctx.data?.next_cursor ?? null,
    computedAt: ctx.data?.computed_at ?? null,
    loading: ctx.loading,
    error: ctx.error,
  };
}

export { ROLE_TO_PERSONA };
