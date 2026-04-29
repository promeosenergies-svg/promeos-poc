/**
 * useCockpitFacts — Hook léger qui consomme /api/cockpit/_facts (Phase 1.3.a SoT).
 *
 * Phase 3.1 du sprint refonte cockpit dual sol2 (29/04/2026). Wrap le call
 * à l'endpoint atomique unifié et expose le payload sans aucun calcul
 * (doctrine §8.1 zero business logic frontend).
 *
 * Cible : sera consommé par <SolKpiMonthlyVsN1Container> (Phase 3.1) puis
 * progressivement par d'autres composants Cockpit (Phase 3.2 drill-downs,
 * Phase 3.3 push hebdo).
 *
 * Pattern aligné useCockpitData.js (RÈGLE : fetch + normalize, pas de calcul).
 */
import { useState, useEffect, useCallback } from 'react';

import { getCockpitFacts } from '../services/api';
import { logger } from '../services/logger';

const TAG = 'CockpitFacts';

export function useCockpitFacts(period = 'current_week') {
  const [facts, setFacts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getCockpitFacts(period);
      setFacts(data);
    } catch (err) {
      logger.warn(TAG, 'fetch failed', err);
      setError(err);
      setFacts(null);
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { facts, loading, error, reload };
}

export default useCockpitFacts;
