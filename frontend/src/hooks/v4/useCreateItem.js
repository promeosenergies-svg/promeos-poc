/**
 * M2-5.1 — Hook mutation : création d'un item V4.
 *
 * Pattern: { execute, loading, error, data, reset }
 * - execute(payload, options) → renvoie une Promise avec la réponse
 * - options.idempotencyKey → header Idempotency-Key (déduplication serveur)
 * - data = dernière réponse (item créé) | null
 * - error = erreur normalisée { code, message, hint, status } | null
 * - reset() → remet à l'état initial
 */
import { useCallback, useState } from 'react';

import { createItem } from '../../services/api/v4ActionCenter';

export function useCreateItem() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  const execute = useCallback(async (payload, options) => {
    setLoading(true);
    setError(null);
    try {
      const response = await createItem(payload, options);
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
