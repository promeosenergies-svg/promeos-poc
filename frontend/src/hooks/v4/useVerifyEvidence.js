/**
 * M2-5.1 — Hook mutation : vérification d'une evidence.
 *
 * Pattern: { execute, loading, error, data, reset }
 * - execute(evidenceId, payload) → renvoie une Promise avec la réponse
 * - data = dernière réponse (evidence verified : verified_at/by/expires_at) | null
 * - error = erreur normalisée { code, message, hint, status } | null
 * - reset() → remet à l'état initial
 */
import { useCallback, useState } from 'react';

import { verifyEvidence } from '../../services/api/v4ActionCenter';

export function useVerifyEvidence() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  const execute = useCallback(async (evidenceId, payload) => {
    setLoading(true);
    setError(null);
    try {
      const response = await verifyEvidence(evidenceId, payload);
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
