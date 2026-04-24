/**
 * PROMEOS — BillingSol (Sprint REFONTE-P6 S1 — Pilot wrapper)
 *
 * Wrapper Sol autour de BillingPage (intact). Préserve les 34 features MAIN :
 * BillingTimeline, BillingCompareChart, CoverageBar, import CSV/PDF, filtres,
 * pagination, navigation croisée bill-intel/conso-diag/purchase.
 * Ajoute SolPageHeader narratif + 3 SolWeekCard sémantiques.
 */

import React, { useEffect, useState } from 'react';
import { SolPageHeader, SolWeekCard } from '../ui/sol';
import BillingPage from './BillingPage';
import {
  getCoverageSummary,
  getMissingPeriods,
} from '../services/api/billing';
import { useScope } from '../contexts/ScopeContext';
import {
  buildBillingKicker,
  buildBillingNarrative,
  interpretWeek,
} from './billing/sol_presenters';

function useBillingHeaderData() {
  const { selectedSiteId } = useScope();
  const [summary, setSummary] = useState(null);
  const [missingPeriods, setMissingPeriods] = useState([]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const params = {};
        if (selectedSiteId) params.site_id = selectedSiteId;
        const [s, m] = await Promise.all([
          getCoverageSummary(params).catch(() => null),
          getMissingPeriods({ ...params, limit: 5 }).catch(() => ({ items: [] })),
        ]);
        if (cancelled) return;
        setSummary(s || null);
        setMissingPeriods(Array.isArray(m?.items) ? m.items : []);
      } catch (_err) {
        // silent
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [selectedSiteId]);

  return { summary, missingPeriods };
}

export default function BillingSol() {
  const { summary, missingPeriods } = useBillingHeaderData();
  const week = interpretWeek({ summary, missingPeriods });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <SolPageHeader
        kicker={buildBillingKicker({ summary })}
        title="Votre facturation"
        titleEm="— shadow billing & couverture"
        narrative={buildBillingNarrative({ summary })}
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

      {/* BillingPage MAIN intact — 34 features préservées */}
      <BillingPage />
    </div>
  );
}
