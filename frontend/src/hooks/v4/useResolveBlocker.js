/**
 * M2-5.1 — Hook mutation : résolution d'un blocker.
 *
 * Pattern: { execute, loading, error, data, reset }
 * - execute(blockerId, payload) → renvoie une Promise avec la réponse
 * - data = dernière réponse (blocker résolu) | null
 * - error = erreur normalisée { code, message, hint, status } | null
 * - reset() → remet à l'état initial
 */
import { useCallback, useState } from 'react';

import { resolveBlocker } from '../../services/api/v4ActionCenter';

export function useResolveBlocker() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  const execute = useCallback(async (blockerId, payload) => {
    setLoading(true);
    setError(null);
    try {
      const response = await resolveBlocker(blockerId, payload);
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
