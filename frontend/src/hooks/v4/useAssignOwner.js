/**
 * M2-5.11.E — Hook mutation : assignation du pilote.
 *
 * Pattern: { execute, loading, error, data, reset } (cohérent autres write
 * hooks V4 — useTransitionLifecycle, useResolveBlocker, …).
 *
 * `execute(itemId, payload)` :
 * - assigner   → `{ owner_id: UUID, owner_display_name: 'J. Martin' }`
 * - désassigner → `{ owner_id: null }` (le BE force `owner_display_name = null`)
 *
 * Le BE écrit un event `owner_changed` dans la même transaction (atomicité).
 * Pas d'optimistic update — pessimiste : on attend 200 puis on refetch.
 */
import { useCallback, useState } from 'react';

import { assignOwner } from '../../services/api/v4ActionCenter';

export function useAssignOwner() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  const execute = useCallback(async (itemId, payload) => {
    setLoading(true);
    setError(null);
    try {
      const response = await assignOwner(itemId, payload);
      setData(response.data);
      return response.data;
    } catch (err) {
      const normalized = err.promeos || { code: 'UNKNOWN', message: err.message };
      setError(normalized);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
  }, []);

  return { execute, loading, error, data, reset };
}
