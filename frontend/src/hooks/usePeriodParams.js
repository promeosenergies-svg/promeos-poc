/**
 * PROMEOS — usePeriodParams (Step 11 — F2)
 * Hook unifié pour la gestion de période via URL params.
 * Toutes les pages Analyse utilisent ce hook → période synchronisée.
 *
 * URL params : ?period_start=2024-01-01&period_end=2025-01-01&days=365
 *
 * Priorité : period_start/period_end explicites > days > défaut
 * Backward compat : lit aussi start/end et date_from/date_to
 */
import { useSearchParams } from 'react-router-dom';
import { useMemo, useCallback } from 'react';

export default function usePeriodParams(defaultDays = 365) {
  const [searchParams, setSearchParams] = useSearchParams();

  const period = useMemo(() => {
    // Read with fallback chain: period_start > start > date_from
    const periodStart =
      searchParams.get('period_start') ||
      searchParams.get('start') ||
      searchParams.get('date_from') ||
      null;
    const periodEnd =
      searchParams.get('period_end') ||
      searchParams.get('end') ||
      searchParams.get('date_to') ||
      null;
    const daysParam = searchParams.get('days');

    if (periodStart && periodEnd) {
      const daysComputed = Math.round(
        (new Date(periodEnd) - new Date(periodStart)) / 86400000
      );
      return {
        start: periodStart,
        end: periodEnd,
        days: daysComputed > 0 ? daysComputed : defaultDays,
        source: 'explicit',
      };
    }

    const days = daysParam ? parseInt(daysParam, 10) : defaultDays;
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - days);

    return {
      start: start.toISOString().slice(0, 10),
      end: end.toISOString().slice(0, 10),
      days,
      source: daysParam ? 'days_param' : 'default',
    };
  }, [searchParams, defaultDays]);

  const setPeriod = useCallback(
    ({ start, end, days }) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (start && end) {
            next.set('period_start', start);
            next.set('period_end', end);
            next.delete('days');
          } else if (days) {
            next.set('days', String(days));
            next.delete('period_start');
            next.delete('period_end');
          }
          // Clean up legacy params
          next.delete('start');
          next.delete('end');
          next.delete('date_from');
          next.delete('date_to');
          return next;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );

  // Génère les params URL pour naviguer vers une autre page Analyse
  // en conservant la même période
  const periodQueryString = useMemo(() => {
    if (period.source === 'explicit') {
      return `period_start=${period.start}&period_end=${period.end}`;
    }
    return `days=${period.days}`;
  }, [period]);

  return { period, setPeriod, periodQueryString };
}
