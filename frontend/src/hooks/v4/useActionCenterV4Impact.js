/**
 * M2-5.10.C — Hook lecture Impact financier 4 quadrants pour un item V4.
 *
 * Pattern: { data, loading, error, refetch } (cohérent autres read hooks V4).
 * `data` = ItemImpactResponse (cf. schemas/v4/action_center.py) | null.
 * Ne fetch pas tant que itemId est absent.
 */
import { useCallback, useEffect, useState } from 'react';

import { fetchItemImpact } from '../../services/api/v4ActionCenter';

export function useActionCenterV4Impact(itemId) {
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
      const response = await fetchItemImpact(itemId);
      setData(response.data);
    } catch (err) {
      setError(err.promeos || { code: 'UNKNOWN', message: err.message });
    } finally {
      setLoading(false);
    }
  }, [itemId]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, loading, error, refetch };
}
