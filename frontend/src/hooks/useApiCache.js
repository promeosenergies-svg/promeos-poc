/**
 * PROMEOS — useApiCache hook (stale-while-revalidate)
 * In-memory cache with TTL. Returns cached data immediately + re-fetches in background.
 *
 * Usage:
 *   const { data, loading, error, invalidate } = useApiCache('cockpit-kpis', getCockpit, 60);
 */
import { useState, useEffect, useCallback, useRef } from 'react';

const _cache = new Map();

export default function useApiCache(key, fetcher, ttlSeconds = 60) {
  const [data, setData] = useState(() => _cache.get(key)?.data ?? null);
  const [loading, setLoading] = useState(!_cache.has(key));
  const [error, setError] = useState(null);
  const mountedRef = useRef(true);

  const doFetch = useCallback(async () => {
    try {
      const result = await fetcher();
      if (!mountedRef.current) return;
      _cache.set(key, { data: result, ts: Date.now() });
      setData(result);
      setError(null);
    } catch (err) {
      if (!mountedRef.current) return;
      setError(err);
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [key, fetcher]);

  useEffect(() => {
    mountedRef.current = true;
    const cached = _cache.get(key);
    const now = Date.now();

    if (cached && now - cached.ts < ttlSeconds * 1000) {
      setData(cached.data);
      setLoading(false);
      return;
    }

    if (cached) {
      // Stale — show cached data, re-fetch in background
      setData(cached.data);
      setLoading(false);
    }

    doFetch();

    return () => {
      mountedRef.current = false;
    };
  }, [key, ttlSeconds, doFetch]);

  const invalidate = useCallback(() => {
    _cache.delete(key);
    setLoading(true);
    doFetch();
  }, [key, doFetch]);

  return { data, loading, error, invalidate };
}

/** Clear all cached entries. Useful for logout/scope change. */
export function clearApiCache() {
  _cache.clear();
}
