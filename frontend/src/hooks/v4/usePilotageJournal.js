/**
 * M2-5.10.E — Hook lecture Journal org-wide cross-items (fenêtre N jours).
 *
 * Pattern: { data, loading, error, refetch } (cohérent autres read hooks V4).
 * `data` = { items, total, since_days, limit } | null.
 */
import { useCallback, useEffect, useState } from 'react';

import { fetchPilotageJournal } from '../../services/api/v4ActionCenter';

export function usePilotageJournal({ sinceDays = 7, limit = 100 } = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchPilotageJournal({ sinceDays, limit });
      setData(response.data);
    } catch (err) {
      setError(err.promeos || { code: 'UNKNOWN', message: err.message });
    } finally {
      setLoading(false);
    }
  }, [sinceDays, limit]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, loading, error, refetch };
}
