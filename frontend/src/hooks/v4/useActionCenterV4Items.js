/**
 * M2-5.1 — Hook lecture paginée des items V4.
 *
 * Pattern: { data, loading, error, refetch } — identique à usePageData legacy.
 * data = { items, total, offset, limit } | null avant chargement.
 */
import { useCallback, useEffect, useState } from 'react';

import { fetchItems } from '../../services/api/v4ActionCenter';

export function useActionCenterV4Items({ offset = 0, limit = 50 } = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchItems({ offset, limit });
      setData(response.data);
    } catch (err) {
      setError(err.promeos || { code: 'UNKNOWN', message: err.message });
    } finally {
      setLoading(false);
    }
  }, [offset, limit]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, loading, error, refetch };
}
