/**
 * M2-5.11.C — Hook lecture du summary org (5 compteurs NarrativeBar).
 *
 * Pattern: { data, loading, error, refetch } (cohérent autres read hooks V4).
 * `data` = { count_p0, count_p1, count_without_owner, count_at_risk, count_secured } | null.
 *
 * Pas de paramètre : le scope est implicite (JWT → middleware org_context côté
 * BE). 5 compteurs entiers ≥ 0 garantis par le schema Pydantic.
 */
import { useCallback, useEffect, useState } from 'react';

import { fetchActionCenterSummary } from '../../services/api/v4ActionCenter';

export function useActionCenterV4Summary() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchActionCenterSummary();
      setData(response.data);
    } catch (err) {
      setError(err.promeos || { code: 'UNKNOWN', message: err.message });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, loading, error, refetch };
}
