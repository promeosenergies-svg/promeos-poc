/**
 * Hook Market Data — alimente le widget cockpit.
 * Appelle 4 endpoints en parallèle, gère loading/error/empty.
 * Refresh toutes les 5 minutes (prix spot changent chaque heure).
 */
import { useState, useEffect, useCallback } from 'react';
import {
  getMarketSpotStats,
  getMarketSpotHistory,
  getMarketDecomposition,
  getMarketForwards,
} from '../services/api/market';

const REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes

export function useMarketData(profile = 'C4') {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [spotStats, history, decomposition, forwards] = await Promise.allSettled([
        getMarketSpotStats(7),
        getMarketSpotHistory(7),
        getMarketDecomposition(profile),
        getMarketForwards(),
      ]);

      setData({
        spot: spotStats.status === 'fulfilled' ? spotStats.value : null,
        history: history.status === 'fulfilled' ? history.value : null,
        decomposition: decomposition.status === 'fulfilled' ? decomposition.value : null,
        forwards: forwards.status === 'fulfilled' ? forwards.value : null,
        fetchedAt: new Date().toISOString(),
      });
    } catch (err) {
      setError(err.message || 'Erreur chargement données marché');
    } finally {
      setLoading(false);
    }
  }, [profile]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchData]);

  return { data, loading, error, refresh: fetchData };
}
