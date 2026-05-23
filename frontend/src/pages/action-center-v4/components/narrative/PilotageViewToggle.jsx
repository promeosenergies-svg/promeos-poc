import { Check, Clock } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

import { JOURNAL_COPY } from '../../constants';

/**
 * M2-5.10.E — Toggle Décisions / Journal (maquette §8.2 lignes 601-611).
 *
 * Posé sous la barre `PilotageTabs` sur les 2 pages Pilotage (Décisions =
 * file prioritaire ; Journal = flux d'activité 7j). Navigation URL-driven
 * (cohérent PilotageTabs) — la source de vérité est `location.pathname`.
 */

function isActive(pathname, target) {
  return pathname === target;
}

function ToggleOption({ to, label, active, icon: Icon }) {
  return (
    <Link
      to={to}
      role="tab"
      aria-selected={active}
      className="inline-flex items-center gap-1.5 rounded-[6px] px-3 py-1.5 font-sans text-[12px] font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--sol-ink-900)]"
      style={
        active
          ? {
              background: 'var(--sol-ink-900)',
              color: 'var(--sol-bg-paper)',
            }
          : {
              background: 'transparent',
              color: 'var(--sol-ink-700)',
            }
      }
    >
      <Icon size={11} aria-hidden="true" />
      {label}
    </Link>
  );
}

export function PilotageViewToggle() {
  const location = useLocation();

  return (
    <div
      role="tablist"
      aria-label="Vue Pilotage"
      className="mb-4 inline-flex items-center gap-1 rounded-[8px] border p-1"
      style={{
        background: 'var(--sol-bg-paper)',
        borderColor: 'var(--sol-rule)',
      }}
    >
      <ToggleOption
        to="/action-center-v4/pilotage"
        label={JOURNAL_COPY.viewToggleDecisions}
        active={isActive(location.pathname, '/action-center-v4/pilotage')}
        icon={Check}
      />
      <ToggleOption
        to="/action-center-v4/pilotage/journal"
        label={JOURNAL_COPY.viewToggleJournal}
        active={isActive(location.pathname, '/action-center-v4/pilotage/journal')}
        icon={Clock}
      />
    </div>
  );
}
