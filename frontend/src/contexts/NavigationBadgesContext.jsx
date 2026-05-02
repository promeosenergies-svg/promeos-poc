/**
 * PROMEOS — NavigationBadgesContext (Phase 2.B — P1.2.bis).
 *
 * Source de vérité unique côté FE pour les compteurs nav rail/panel +
 * cloche action center. Remplace les 3 fetches dispersés
 * (Sidebar.getNotificationsSummary + Sidebar.getMonitoringAlerts +
 * AppShell.getActionCenter*Summary) par un seul appel canonique
 * `GET /api/v1/navigation/badges` (P1.2 backend, commit 6c4cc362).
 *
 * Stratégie :
 *   - Stale-while-revalidate : on garde la dernière valeur valide
 *     pendant un refetch. Le UI ne flash pas un état vide.
 *   - Refetch interval piloté par `cache_ttl_seconds` du payload
 *     backend (default 60 s) — la SoT TTL est côté serveur.
 *   - Retry 3× en cas d'échec (compteur monotone). Au-delà, on bascule
 *     en mode dégradé (badges masqués) sans toast utilisateur.
 *   - Aucune dépendance externe (React Query / SWR) — KISS.
 *
 * Audit nav §3.3 + §5 P1.2 + dette TECH-badge-context-dedup.
 * Doctrine §6.2 anti-pattern "menus muets" : on expose toujours des
 * compteurs concrets (0 par défaut côté consommateurs).
 */

import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { getNavigationBadges } from '../services/api';

const NavigationBadgesContext = createContext(null);

const DEFAULT_TTL_SECONDS = 60;
const MAX_RETRY_BEFORE_DEGRADED = 3;

const INITIAL_STATE = {
  data: null, // null = pas encore fetched (premier mount)
  loading: true,
  error: null, // Error | null — uniquement après MAX_RETRY_BEFORE_DEGRADED échecs
};

export function NavigationBadgesProvider({ children }) {
  const [state, setState] = useState(INITIAL_STATE);
  const failureCountRef = useRef(0);
  const intervalRef = useRef(null);
  const ttlRef = useRef(DEFAULT_TTL_SECONDS);
  const cancelledRef = useRef(false);

  const fetchBadges = useCallback(async () => {
    try {
      const data = await getNavigationBadges();
      if (cancelledRef.current) return null;
      failureCountRef.current = 0;
      // TTL piloté par backend si fourni, fallback 60 s.
      if (typeof data?.cache_ttl_seconds === 'number' && data.cache_ttl_seconds > 0) {
        ttlRef.current = data.cache_ttl_seconds;
      }
      setState({ data, loading: false, error: null });
      return data;
    } catch (err) {
      if (cancelledRef.current) return null;
      failureCountRef.current += 1;
      // Stale-while-revalidate : garde la dernière valeur (prev.data).
      // Erreur exposée seulement après le seuil — évite le flicker en
      // cas de hiccup réseau ponctuel.
      setState((prev) => ({
        data: prev.data,
        loading: false,
        error: failureCountRef.current >= MAX_RETRY_BEFORE_DEGRADED ? err : null,
      }));
      return null;
    }
  }, []);

  useEffect(() => {
    cancelledRef.current = false;
    fetchBadges();

    // Reschedule via setTimeout récursif pour adopter le TTL courant
    // (le payload backend pilote ttlRef.current). Le guard cancelledRef
    // est vérifié AVANT chaque setTimeout — sinon un tick exécuté
    // pendant l'unmount planifierait un nouveau handle qui échapperait
    // au cleanup (fuite vers double polling au remount rapide).
    const tick = () => {
      if (cancelledRef.current) return;
      fetchBadges();
      if (cancelledRef.current) return;
      intervalRef.current = setTimeout(tick, ttlRef.current * 1000);
    };
    intervalRef.current = setTimeout(tick, ttlRef.current * 1000);

    return () => {
      cancelledRef.current = true;
      if (intervalRef.current) clearTimeout(intervalRef.current);
    };
  }, [fetchBadges]);

  const value = { ...state, refetch: fetchBadges };

  return (
    <NavigationBadgesContext.Provider value={value}>{children}</NavigationBadgesContext.Provider>
  );
}

/**
 * Hook de consommation. Lève une erreur si appelé hors Provider —
 * garde-fou contre une régression d'arbre de composants.
 */
export function useNavigationBadges() {
  const ctx = useContext(NavigationBadgesContext);
  if (ctx === null) {
    throw new Error('useNavigationBadges must be used within NavigationBadgesProvider');
  }
  return ctx;
}
