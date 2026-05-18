/**
 * M2-5.1 — Hook lecture paginée des links d'un item V4.
 *
 * Pattern: { data, loading, error, refetch }.
 * data = { links, total, offset, limit } | null avant chargement.
 * Ne fetch pas tant que itemId est absent.
 */
import { useCallback, useEffect, useState } from 'react';

import { fetchItemLinks } from '../../services/api/v4ActionCenter';

export function useActionCenterV4Links(itemId, { offset = 0, limit = 50 } = {}) {
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
      const response = await fetchItemLinks(itemId, { offset, limit });
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
