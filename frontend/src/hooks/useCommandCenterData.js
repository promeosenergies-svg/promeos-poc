/**
 * useCommandCenterData — Données vue exploitation (tableau de bord quotidien /).
 *
 * RÈGLE : display-only, zéro calcul métier.
 * Agrège : EMS J-1, EMS 7 jours, EMS profil horaire.
 *
 * Note : NE PAS dupliquer les données du hook useCockpitData (conformité, risque).
 * Ce hook est exclusivement pour les données de monitoring quotidien.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { useScope } from '../contexts/ScopeContext';
import { logger } from '../services/logger';
import { getEmsTimeseries } from '../services/api';

const TAG = 'CommandCenterData';

function isoDate(d) {
  return d.toISOString().split('T')[0];
}

function yesterday() {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d;
}

function daysAgo(n) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d;
}

/**
 * Normalise la réponse EMS pour le graphique 7 jours.
 * Backend fournit { series: [{ key, data: [{t, v}] }] }
 */
function normalizeWeekSeries(raw) {
  if (!raw?.series?.length) return [];
  const serie = raw.series[0];
  return (serie?.data ?? []).map((point) => ({
    date: point.t?.split('T')[0] ?? point.t,
    kwh: point.v ?? null,
  }));
}

/**
 * Normalise le profil journalier horaire J-1.
 * 24 points avec heure + kW.
 */
function normalizeHourlyProfile(raw) {
  if (!raw?.series?.length) return [];
  const serie = raw.series[0];
  return (serie?.data ?? []).map((point) => ({
    heure: new Date(point.t).getHours() + 'h',
    kw: point.v != null ? Math.round(point.v * 4) : null,
    t: point.t,
  }));
}

export function useCommandCenterData() {
  const { org, scopedSites } = useScope();
  const [state, setState] = useState({
    weekSeries: [],
    hourlyProfile: [],
    kpisJ1: null,
    loading: true,
    error: null,
    lastFetchedAt: null,
  });

  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const fetchAll = useCallback(async () => {
    if (!org?.id || !scopedSites?.length) return;

    setState((prev) => ({ ...prev, loading: true, error: null }));
    const siteIds = scopedSites.map((s) => s.id).join(',');
    const today = isoDate(new Date());
    const yest = isoDate(yesterday());
    const week7 = isoDate(daysAgo(7));

    logger.info(TAG, 'Fetching command center data', { orgId: org.id, sites: scopedSites.length });

    try {
      const [weekRaw, profileRaw] = await Promise.all([
        getEmsTimeseries({
          site_ids: siteIds,
          date_from: week7,
          date_to: today,
          granularity: 'daily',
          mode: 'aggregate',
        }).catch((err) => {
          logger.error(TAG, 'weekSeries failed', { err: err.message });
          return null;
        }),
        getEmsTimeseries({
          site_ids: siteIds,
          date_from: yest,
          date_to: today,
          granularity: 'hourly',
          mode: 'aggregate',
        }).catch((err) => {
          logger.error(TAG, 'hourlyProfile failed', { err: err.message });
          return null;
        }),
      ]);

      if (!mountedRef.current) return;

      const weekSeries = normalizeWeekSeries(weekRaw);
      const hourlyProfile = normalizeHourlyProfile(profileRaw);

      const yestData = weekSeries.find((p) => p.date === yest);
      const consoHierKwh = yestData?.kwh ?? null;

      const picKw = hourlyProfile.length ? Math.max(...hourlyProfile.map((p) => p.kw ?? 0)) : null;

      setState({
        weekSeries,
        hourlyProfile,
        kpisJ1: {
          consoHierKwh,
          picKw,
          co2ResKgKwh: null,
        },
        loading: false,
        error: null,
        lastFetchedAt: new Date().toISOString(),
      });

      logger.info(TAG, 'Command center data loaded', {
        weekPoints: weekSeries.length,
        profilePoints: hourlyProfile.length,
      });
    } catch (err) {
      if (!mountedRef.current) return;
      logger.error(TAG, 'Command center fetch failed', { err: err.message });
      setState((prev) => ({ ...prev, loading: false, error: err.message }));
    }
  }, [org?.id, scopedSites]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  return { ...state, refetch: fetchAll };
}
