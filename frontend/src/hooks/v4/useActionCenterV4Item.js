/**
 * M2-5.1 — Hook lecture du détail d'un item V4 (objet unique, pas de pagination).
 *
 * Pattern: { data, loading, error, refetch }.
 * data = item | null avant chargement (ou si itemId absent).
 */
import { useCallback, useEffect, useState } from 'react';

import { fetchItem } from '../../services/api/v4ActionCenter';

export function useActionCenterV4Item(itemId) {
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
      const response = await fetchItem(itemId);
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
