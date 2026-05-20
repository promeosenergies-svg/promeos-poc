/**
 * M2-5.1 — Hook mutation : création d'un link sur un item V4.
 *
 * Pattern: { execute, loading, error, data, reset }
 * - execute(itemId, payload) → renvoie une Promise avec la réponse
 * - data = dernière réponse (link créé) | null
 * - error = erreur normalisée { code, message, hint, status } | null
 * - reset() → remet à l'état initial
 */
import { useCallback, useState } from 'react';

import { createLink } from '../../services/api/v4ActionCenter';

export function useCreateLink() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  const execute = useCallback(async (itemId, payload) => {
    setLoading(true);
    setError(null);
    try {
      const response = await createLink(itemId, payload);
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
