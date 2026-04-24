/**
 * useRouteTracker — Tracks la route courante dans navRecent localStorage.
 *
 * Sprint 1 Vague B · B2.1
 * Appelé au top de SolAppShell (mount unique global).
 *
 * Comportement :
 *   - à chaque changement de pathname, push dans navRecent via `addRecent`
 *   - `getLabel(pathname)` optional → label humain pour le badge recent
 *   - exclut les routes techniques (`/`, `/login`, `/_sol_showcase`)
 *
 * navRecent gère dédup + FIFO drop + corruption-safe (existing util).
 */
import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { addRecent } from '../utils/navRecent';

const EXCLUDED_PATHS = new Set(['/', '/login', '/_sol_showcase']);

export default function useRouteTracker(getLabel) {
  const { pathname } = useLocation();
  useEffect(() => {
    if (EXCLUDED_PATHS.has(pathname)) return;
    const label = getLabel?.(pathname);
    addRecent(pathname, label ? { label } : undefined);
  }, [pathname, getLabel]);
}
