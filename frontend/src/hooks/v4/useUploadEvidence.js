/**
 * M2-5.1 — Hook mutation : upload d'une evidence (multipart).
 *
 * Pattern: { execute, loading, error, data, reset }
 * - execute(itemId, file, options) → renvoie une Promise avec la réponse
 * - options.description → champ texte facultatif joint au FormData
 * - data = dernière réponse (evidence créée, statut pending) | null
 * - error = erreur normalisée { code, message, hint, status } | null
 * - reset() → remet à l'état initial
 */
import { useCallback, useState } from 'react';

import { uploadEvidence } from '../../services/api/v4ActionCenter';

export function useUploadEvidence() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  const execute = useCallback(async (itemId, file, options) => {
    setLoading(true);
    setError(null);
    try {
      const response = await uploadEvidence(itemId, file, options);
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
