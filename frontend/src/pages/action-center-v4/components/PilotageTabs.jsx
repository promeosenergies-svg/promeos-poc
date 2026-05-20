import { Link, useLocation } from 'react-router-dom';

import { PILOTAGE_COPY } from '../constants';

/**
 * M2-5.10.D — Tabs Pilotage / Référentiel (maquette §8.1 lignes 825-829).
 *
 * Navigation interne au Centre d'Action — 2 routes côte à côte. L'onglet
 * actif est dérivé du path courant (pas un state local : la navigation
 * URL est la source de vérité, cohérent avec le pattern PageShell tabs).
 *
 * Posé sous le masthead Sol des 2 pages (référentiel + pilotage), exposé
 * comme composant partagé.
 */

const TAB_BASE =
  'inline-flex items-center gap-2 px-4 py-2.5 font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--sol-ink-900)]';

function tabStyle(active) {
  return active
    ? {
        fontFamily: 'var(--sol-font-display)',
        fontSize: '15px',
        color: 'var(--sol-ink-900)',
        borderBottom: '3px solid var(--sol-ink-900)',
        fontWeight: 600,
        transform: 'translateY(2px)',
        letterSpacing: '-0.005em',
      }
    : {
        fontFamily: 'var(--sol-font-display)',
        fontSize: '15px',
        color: 'var(--sol-ink-500)',
        borderBottom: '3px solid transparent',
        fontWeight: 500,
        transform: 'translateY(2px)',
        letterSpacing: '-0.005em',
      };
}

export function PilotageTabs() {
  const location = useLocation();
  const isPilotage = location.pathname === '/action-center-v4/pilotage';
  const isReferentiel = location.pathname === '/action-center-v4';

  return (
    <nav
      role="tablist"
      aria-label="Sections du Centre d'action"
      className="mb-4 flex items-center gap-0"
      style={{ borderBottom: '1px solid var(--sol-ink-900)' }}
    >
      <Link
        to="/action-center-v4/pilotage"
        role="tab"
        aria-selected={isPilotage}
        className={TAB_BASE}
        style={tabStyle(isPilotage)}
      >
        {PILOTAGE_COPY.tabPilotage}
      </Link>
      <Link
        to="/action-center-v4"
        role="tab"
        aria-selected={isReferentiel}
        className={TAB_BASE}
        style={tabStyle(isReferentiel)}
      >
        {PILOTAGE_COPY.tabReferentiel}
      </Link>
    </nav>
  );
}
