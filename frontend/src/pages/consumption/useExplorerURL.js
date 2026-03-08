/**
 * PROMEOS — useExplorerURL v2
 * Bidirectional URL state sync for the Consumption Explorer.
 * Uses react-router-dom's useSearchParams.
 *
 * URL params:
 *   sites  — comma-separated site IDs   e.g. "12,34"
 *   energy — 'electricity' | 'gas'
 *   days   — period in days             e.g. "90"
 *   start  — ISO8601 start date         e.g. "2025-01-01"  (custom range)
 *   end    — ISO8601 end date           e.g. "2025-03-31"  (custom range)
 *   mode   — 'agrege' | 'superpose' | 'empile' | 'separe'
 *   unit   — 'kwh' | 'kw' | 'eur'
 *   tab    — active panel tab key
 *   layers — comma-separated active layers e.g. "tunnel,signature"
 */
import { useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';

const DEFAULTS = {
  energy: 'electricity',
  days: 90,
  mode: 'agrege',
  unit: 'kwh',
  tab: 'timeseries', // V19: timeseries is the primary chart view
};

export default function useExplorerURL() {
  const [searchParams, setSearchParams] = useSearchParams();

  /**
   * Read current URL state (falls back to DEFAULTS when params absent).
   */
  const urlState = {
    siteIds: searchParams.get('sites')
      ? searchParams.get('sites').split(',').map(Number).filter(Boolean)
      : [],
    energy: searchParams.get('energy') || DEFAULTS.energy,
    days: searchParams.has('days') ? Number(searchParams.get('days')) : DEFAULTS.days,
    // Custom date range (overrides days when present)
    // Step 11: also read period_start/period_end and date_from/date_to for cross-page compat
    startDate:
      searchParams.get('start') ||
      searchParams.get('period_start') ||
      searchParams.get('date_from') ||
      null,
    endDate:
      searchParams.get('end') ||
      searchParams.get('period_end') ||
      searchParams.get('date_to') ||
      null,
    mode: searchParams.get('mode') || DEFAULTS.mode,
    unit: searchParams.get('unit') || DEFAULTS.unit,
    tab: searchParams.get('tab') || DEFAULTS.tab,
    // Layers — null means "use DEFAULT_LAYERS"; array means explicit user choice
    layers: searchParams.get('layers')
      ? searchParams.get('layers').split(',').filter(Boolean)
      : null,
  };

  /**
   * Update one or more URL params without losing the rest.
   * @param {Record<string, string|number|number[]|null>} updates
   */
  const setUrlParams = useCallback(
    (updates) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          for (const [key, value] of Object.entries(updates)) {
            if (value === null || value === undefined) {
              next.delete(key);
            } else if (Array.isArray(value)) {
              if (value.length === 0) {
                next.delete(key);
              } else {
                next.set(key, value.join(','));
              }
            } else {
              next.set(key, String(value));
            }
          }
          return next;
        },
        { replace: true }
      ); // replace to avoid polluting browser history on every filter change
    },
    [setSearchParams]
  );

  return { urlState, setUrlParams };
}
