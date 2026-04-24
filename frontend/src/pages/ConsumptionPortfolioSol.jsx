/**
 * PROMEOS — ConsumptionPortfolioSol (Sprint REFONTE-P6 S1 — Wrapper)
 *
 * Wrapper Sol autour de ConsumptionPortfolioPage (980 LOC, 25 features MAIN).
 * Ajoute SolPageHeader narratif + 3 SolWeekCard (Impact / Dérive / Bonne nouvelle).
 * ConsumptionPortfolioPage reste propriétaire : KPIs hero 4 tiles,
 * "Où agir en priorité" 4 cards, tableau 25/page × 10 colonnes,
 * tri 8 options, filtres 6 pills, drill-down navigation.
 */

import React, { useEffect, useState } from 'react';
import { SolPageHeader, SolWeekCard } from '../ui/sol';
import ConsumptionPortfolioPage from './ConsumptionPortfolioPage';
import { getPortfolioSummary } from '../services/api/cockpit';
import { useScope } from '../contexts/ScopeContext';
import {
  buildPortfolioKicker,
  buildPortfolioNarrative,
  interpretPortfolioWeek,
} from './consommations/sol_presenters';

export default function ConsumptionPortfolioSol() {
  const { portefeuille } = useScope();
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

  const week = interpretPortfolioWeek({ portfolioSummary });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <SolPageHeader
        kicker={buildPortfolioKicker({ portfolioSummary })}
        title="Votre portefeuille consommation"
        titleEm="— synthèse 12 mois glissants"
        narrative={buildPortfolioNarrative({
          portfolioSummary,
          topImpact: portfolioSummary?.top_impact || [],
        })}
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

      <ConsumptionPortfolioPage />
    </div>
  );
}
