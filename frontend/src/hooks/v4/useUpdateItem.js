/**
 * M2-5.1 — Hook mutation : mise à jour cosmétique d'un item V4 (PATCH).
 *
 * Pattern: { execute, loading, error, data, reset }
 * - execute(itemId, payload) → renvoie une Promise avec la réponse
 * - data = dernière réponse (item mis à jour) | null
 * - error = erreur normalisée { code, message, hint, status } | null
 * - reset() → remet à l'état initial
 */
import { useCallback, useState } from 'react';

import { updateItem } from '../../services/api/v4ActionCenter';

export function useUpdateItem() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  const execute = useCallback(async (itemId, payload) => {
    setLoading(true);
    setError(null);
    try {
      const response = await updateItem(itemId, payload);
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
