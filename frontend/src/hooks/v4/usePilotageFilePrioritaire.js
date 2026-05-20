/**
 * M2-5.10.D — Hook lecture File prioritaire pilotage (top N items P0/P1 actifs).
 *
 * Pattern: { data, loading, error, refetch } (cohérent autres read hooks V4).
 * `data` = { items, limit } | null.
 */
import { useCallback, useEffect, useState } from 'react';

import { fetchPilotageFilePrioritaire } from '../../services/api/v4ActionCenter';

export function usePilotageFilePrioritaire({ limit = 5 } = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchPilotageFilePrioritaire({ limit });
      setData(response.data);
    } catch (err) {
      setError(err.promeos || { code: 'UNKNOWN', message: err.message });
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, loading, error, refetch };
}
