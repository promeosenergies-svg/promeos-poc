/**
 * useRouteTracker — push la route courante dans `navRecent` localStorage.
 *
 * Appelé au top de SolAppShell (mount unique global). À chaque changement
 * de pathname, push dans navRecent (dédup + FIFO drop gérés par l'util).
 * Exclut les routes techniques (`/`, `/login`, `/_sol_showcase`).
 */
import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { addRecent } from '../utils/navRecent';

const EXCLUDED_PATHS = new Set(['/', '/login', '/_sol_showcase']);

export default function useRouteTracker() {
  const { pathname } = useLocation();
  useEffect(() => {
    if (EXCLUDED_PATHS.has(pathname)) return;
    addRecent(pathname);
  }, [pathname]);
}
