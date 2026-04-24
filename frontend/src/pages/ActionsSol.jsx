/**
 * PROMEOS — ActionsSol (Sprint REFONTE-P6 S1 — Pilot wrapper)
 *
 * Wrapper Sol autour d'ActionsPage (intact). Préserve les 50 features MAIN
 * incluant ActionDetailDrawer 1327 LOC + 3 vues Table/Kanban/Week + bulk ops.
 * Ajoute SolPageHeader narratif + 3 SolWeekCard sémantiques.
 */

import React, { useEffect, useState } from 'react';
import { SolPageHeader, SolWeekCard } from '../ui/sol';
import ActionsPage from './ActionsPage';
import { getActionsList } from '../services/api/actions';
import { useScope } from '../contexts/ScopeContext';
import {
  buildActionsKicker,
  buildActionsNarrative,
  interpretWeek,
  isOverdue,
} from './actions/sol_presenters';

function useActionsHeaderData() {
  const { selectedSiteId } = useScope();
  const [actions, setActions] = useState([]);
  const [stats, setStats] = useState({});

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const params = {};
        if (selectedSiteId) params.site_id = selectedSiteId;
        const data = await getActionsList(params);
        if (cancelled) return;
        const list = Array.isArray(data) ? data : data?.actions || [];
        setActions(list);
        setStats({
          total: list.length,
          overdue: list.filter((a) => isOverdue(a)).length,
          in_progress: list.filter((a) => a.statut === 'in_progress').length,
          done: list.filter((a) => a.statut === 'done').length,
          total_impact: list.reduce((s, a) => s + (a.impact_eur || 0), 0),
        });
      } catch (_err) {
        // silent — ActionsPage gère son état
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [selectedSiteId]);

  return { actions, stats };
}

export default function ActionsSol(props) {
  const { actions, stats } = useActionsHeaderData();
  const week = interpretWeek({ actions });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <SolPageHeader
        kicker={buildActionsKicker({ stats })}
        title="Votre plan d'action"
        titleEm="— management by exception"
        narrative={buildActionsNarrative({ stats, total: actions.length })}
      />

      <section
        aria-label="Cette semaine chez vous"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: 16,
        }}
      >
        <SolWeekCard {...week.aRegarder} />
        <SolWeekCard {...week.deriveDetectee} />
        <SolWeekCard {...week.bonneNouvelle} />
      </section>

      {/* ActionsPage MAIN intact — 50 features préservées */}
      <ActionsPage {...props} />
    </div>
  );
}
