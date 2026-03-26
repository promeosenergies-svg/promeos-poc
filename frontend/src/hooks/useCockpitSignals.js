/**
 * useCockpitSignals — Signaux marché + CO₂ + alertes pour le header cockpit.
 * Display-only. Échecs partiels tolérés (chaque signal indépendant).
 */
import { useState, useEffect } from 'react';
import { getMarketPrices, getNotificationsList } from '../services/api';
import { logger } from '../services/logger';

const TAG = 'CockpitSignals';

export function useCockpitSignals() {
  const [signals, setSignals] = useState({
    epexEurMwh: null,
    co2GKwh: null,
    alertesCount: null,
    loading: true,
  });

  useEffect(() => {
    let mounted = true;

    async function fetchSignals() {
      const [marketRaw, alertesRaw] = await Promise.all([
        getMarketPrices({ limit: 731 }).catch((err) => {
          logger.error(TAG, 'market fetch failed', { err: err.message });
          return null;
        }),
        getNotificationsList({ status: 'new' }).catch((err) => {
          logger.error(TAG, 'alertes fetch failed', { err: err.message });
          return null;
        }),
      ]);

      if (!mounted) return;

      // Dernier prix EPEX = dernier élément du array prices
      const prices = marketRaw?.prices ?? [];
      const lastPrice = prices.length > 0 ? prices[prices.length - 1] : null;

      setSignals({
        epexEurMwh: lastPrice?.price_eur_mwh ?? null,
        co2GKwh: null, // connecteur RTE absent — affiche '—'
        alertesCount: Array.isArray(alertesRaw) ? alertesRaw.length : null,
        loading: false,
      });

      logger.info(TAG, 'signals loaded', {
        epex: lastPrice?.price_eur_mwh,
        alertes: Array.isArray(alertesRaw) ? alertesRaw.length : 0,
      });
    }

    fetchSignals();
    return () => {
      mounted = false;
    };
  }, []);

  return signals;
}
