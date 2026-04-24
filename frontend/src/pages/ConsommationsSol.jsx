/**
 * PROMEOS — ConsommationsSol (Sprint REFONTE-P6 S1 — Hub wrapper)
 *
 * Wrapper Sol hub autour de ConsommationsPage (intact). Ajoute SolPageHeader
 * narratif au-dessus des 4 tabs (Portfolio / Explorer / Import / Memobox).
 */

import React, { useEffect, useState } from 'react';
import { SolPageHeader } from '../ui/sol';
import ConsommationsPage from './ConsommationsPage';
import { getPortfolioSummary } from '../services/api/cockpit';
import { useScope } from '../contexts/ScopeContext';
import {
  buildConsoHubKicker,
  buildConsoHubNarrative,
} from './consommations/sol_presenters';

export default function ConsommationsSol() {
  const { portefeuille, orgSites } = useScope();
  const [portfolioSummary, setPortfolioSummary] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const params = {};
        if (portefeuille?.id) params.portefeuille_id = portefeuille.id;
        const data = await getPortfolioSummary(params).catch(() => null);
        if (!cancelled) setPortfolioSummary(data);
      } catch (_) {
        // silent
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [portefeuille?.id]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <SolPageHeader
        kicker={buildConsoHubKicker({ portfolioSummary })}
        title="Consommations"
        titleEm="— portefeuille, explorateur & usages"
        narrative={buildConsoHubNarrative({
          portfolioSummary,
          sitesCount: orgSites?.length || 0,
        })}
      />
      <ConsommationsPage />
    </div>
  );
}
