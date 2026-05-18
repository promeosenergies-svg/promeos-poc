/**
 * M2-5.1 — Hook lecture paginée des events (timeline) d'un item V4.
 *
 * Pattern: { data, loading, error, refetch }.
 * data = { events, total, offset, limit } | null avant chargement.
 * Ne fetch pas tant que itemId est absent.
 */
import { useCallback, useEffect, useState } from 'react';

import { fetchItemEvents } from '../../services/api/v4ActionCenter';

export function useActionCenterV4Events(itemId, { offset = 0, limit = 50 } = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refetch = useCallback(async () => {
    if (!itemId) {
      setData(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await fetchItemEvents(itemId, { offset, limit });
      setData(response.data);
    } catch (err) {
      setError(err.promeos || { code: 'UNKNOWN', message: err.message });
    } finally {
      setLoading(false);
    }
  }, [itemId, offset, limit]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, loading, error, refetch };
}
