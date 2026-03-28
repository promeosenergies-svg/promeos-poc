/**
 * useCockpitSignals — Signaux marché + CO₂ + alertes pour le header cockpit.
 * Display-only. Échecs partiels tolérés (chaque signal indépendant).
 */
import { useState, useEffect } from 'react';
import { getMarketPrices, getNotificationsList, getCockpitCo2 } from '../services/api';
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
      const [marketRaw, alertesRaw, co2Raw] = await Promise.all([
        getMarketPrices().catch((err) => {
          logger.error(TAG, 'market fetch failed', { err: err.message });
          return null;
        }),
        getNotificationsList({ status: 'new' }).catch((err) => {
          logger.error(TAG, 'alertes fetch failed', { err: err.message });
          return null;
        }),
        getCockpitCo2().catch((err) => {
          logger.error(TAG, 'co2 fetch failed', { err: err.message });
          return null;
        }),
      ]);

      if (!mounted) return;

      // Prix EPEX : stats.current ou dernier prix du tableau
      const epex =
        marketRaw?.stats?.current_eur_mwh ??
        (marketRaw?.prices?.length
          ? marketRaw.prices[marketRaw.prices.length - 1].price_eur_mwh
          : null);

      // CO₂ intensité réseau : facteur élec ADEME depuis le endpoint cockpit/co2
      // (g/kWh = kg/kWh × 1000)
      const elecFactor = co2Raw?.emission_factors?.elec;
      const co2 = elecFactor != null ? Math.round(elecFactor * 1000) : null;

      setSignals({
        epexEurMwh: epex,
        co2GKwh: co2,
        alertesCount: Array.isArray(alertesRaw) ? alertesRaw.length : null,
        loading: false,
      });

      logger.info(TAG, 'signals loaded', {
        epex,
        co2,
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
