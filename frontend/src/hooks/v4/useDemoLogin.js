/**
 * M2-5.8.A — Hook du bouton « Se connecter (démo) ».
 *
 * Pattern write V4 (cohérent M2-5.4→.6) : `{ execute, loading, error, reset }`.
 * `execute()` déclenche le demo-login ; un 404 backend (DEMO_MODE inactif) est
 * traduit en message explicite plutôt qu'une erreur axios brute.
 */
import { useCallback, useState } from 'react';

import { demoLogin } from '../../services/api/v4Auth';

export function useDemoLogin() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const execute = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      return await demoLogin();
    } catch (err) {
      const normalized = err.promeos || {
        message:
          err.response?.status === 404
            ? "Le mode démo n'est pas activé sur ce serveur"
            : err.message || 'Erreur de connexion',
        status: err.response?.status,
      };
      setError(normalized);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => setError(null), []);

  return { execute, loading, error, reset };
}
