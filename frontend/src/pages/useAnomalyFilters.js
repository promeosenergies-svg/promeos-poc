/**
 * useAnomalyFilters — V114b
 * Bidirectional URL + localStorage sync for the Anomalies Centre d'actions.
 * Priority: URL params > localStorage > defaults (empty).
 *
 * URL params: fw, sev, site, q, tab
 * localStorage key: promeos_anomaly_filters
 */
import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';

const LS_KEY = 'promeos_anomaly_filters';
const FILTER_KEYS = ['fw', 'sev', 'site', 'q'];

function readLocalStorage() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export default function useAnomalyFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const saved = useMemo(() => readLocalStorage(), []); // read once on mount

  // Resolve each filter: URL > localStorage > ''
  const filters = useMemo(() => {
    const result = {};
    for (const key of FILTER_KEYS) {
      result[key] = searchParams.get(key) || saved[key] || '';
    }
    result.tab = searchParams.get('tab') || 'anomalies';
    return result;
  }, [searchParams, saved]);

  const hasFilters = useMemo(
    () => FILTER_KEYS.some((k) => !!filters[k]),
    [filters]
  );

  /**
   * Merge-update filters → URL (replace) + localStorage.
   */
  const setFilters = useCallback(
    (updates) => {
      // Persist non-tab filters to localStorage
      const lsData = readLocalStorage();
      for (const [key, value] of Object.entries(updates)) {
        if (key !== 'tab') {
          if (value) lsData[key] = value;
          else delete lsData[key];
        }
      }
      localStorage.setItem(LS_KEY, JSON.stringify(lsData));

      // Update URL
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          for (const [key, value] of Object.entries(updates)) {
            if (value === null || value === undefined || value === '') {
              next.delete(key);
            } else {
              next.set(key, String(value));
            }
          }
          return next;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );

  /**
   * Reset all filters — clear URL params + localStorage.
   */
  const resetFilters = useCallback(() => {
    localStorage.removeItem(LS_KEY);
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        for (const key of FILTER_KEYS) next.delete(key);
        return next;
      },
      { replace: true }
    );
  }, [setSearchParams]);

  return { filters, hasFilters, setFilters, resetFilters };
}
