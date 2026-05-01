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
 *
 * Phase 26 (sprint retro Cockpit Dual Sol2 — audit prod 2026-05-01) :
 *   Ajout d'un cache in-flight (`_inflight` Map keyé sur period) pour éviter
 *   les fetches dupliqués quand plusieurs composants montent simultanément
 *   avec la même period (ex: page Cockpit + DataReadinessBadge AppShell).
 *   Avant Phase 26 : 2 appels /api/cockpit/_facts au mount /cockpit/strategique.
 *   Après : 1 seul appel partagé.
 */
import { useState, useEffect, useRef, useCallback } from 'react';

import { getCockpitFacts } from '../services/api';
import { logger } from '../services/logger';

const TAG = 'CockpitFacts';

// Phase 26 : cache in-flight pour dédup multi-mount (cf useActivationData
// pattern). La promise est partagée entre tous les hooks qui demandent la
// même period au même moment. Supprimée du cache une fois résolue.
const _inflight = new Map();

function _fetchOnce(period) {
  if (_inflight.has(period)) return _inflight.get(period);
  const p = getCockpitFacts(period).finally(() => {
    _inflight.delete(period);
  });
  _inflight.set(period, p);
  return p;
}

export function useCockpitFacts(period = 'current_week') {
  const [facts, setFacts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  // Race-safe : si period change ou unmount avant fin du fetch, on évite
  // setState sur composant démonté ou écrasement d'une réponse plus récente
  // par une plus ancienne (P1 fix /simplify Phase 3 efficiency F3).
  const cancelRef = useRef(false);

  const reload = useCallback(() => {
    cancelRef.current = false;
    setLoading(true);
    setError(null);
    return _fetchOnce(period)
      .then((data) => {
        if (cancelRef.current) return;
        setFacts(data);
      })
      .catch((err) => {
        if (cancelRef.current) return;
        logger.warn(TAG, 'fetch failed', err);
        setError(err);
        setFacts(null);
      })
      .finally(() => {
        if (!cancelRef.current) setLoading(false);
      });
  }, [period]);

  useEffect(() => {
    cancelRef.current = false;
    reload();
    return () => {
      cancelRef.current = true;
    };
  }, [reload]);

  return { facts, loading, error, reload };
}

export default useCockpitFacts;
