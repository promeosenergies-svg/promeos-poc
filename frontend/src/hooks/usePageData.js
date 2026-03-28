/**
 * PROMEOS — usePageData hook (Sprint Front S)
 * Hook générique pour le pattern fetch+loading+error+data.
 * Remplace les 50+ useState/useEffect/catch ad-hoc dans les pages.
 *
 * Usage:
 *   const { data, loading, error, refetch } = usePageData(
 *     () => getComplianceBundle(params),
 *     [params.orgId, params.siteId]
 *   );
 *
 * Retourne:
 *   - data: T | null
 *   - loading: boolean
 *   - error: string | null
 *   - refetch: () => void
 *
 * Garanties:
 *   - Pas d'update après unmount
 *   - Stale response guard (ignore les réponses d'anciens appels)
 *   - Error = message string (pas l'objet Error brut)
 */
import { useState, useEffect, useCallback, useRef } from 'react';

export default function usePageData(fetcher, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const mountedRef = useRef(true);
  const fetchIdRef = useRef(0);

  const doFetch = useCallback(() => {
    const fetchId = ++fetchIdRef.current;
    setLoading(true);
    setError(null);

    fetcher()
      .then((result) => {
        if (!mountedRef.current || fetchIdRef.current !== fetchId) return;
        setData(result);
        setLoading(false);
      })
      .catch((err) => {
        if (!mountedRef.current || fetchIdRef.current !== fetchId) return;
        setError(err?.message || err?.detail || 'Erreur de chargement');
        setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    mountedRef.current = true;
    doFetch();
    return () => {
      mountedRef.current = false;
    };
  }, [doFetch]);

  return { data, loading, error, refetch: doFetch };
}
