/**
 * SolKpiMonthlyVsN1Container — wrapper data-fetching pour SolKpiMonthlyVsN1.
 *
 * Phase 3.1 du sprint refonte cockpit dual sol2 (29/04/2026). Connecte le
 * composant pur display Sol (Phase 2.1bis) à l'endpoint /api/cockpit/_facts
 * (Phase 1.3.a) via useCockpitFacts hook.
 *
 * Doctrine §8.1 : aucune logique métier ici — juste fetch + extraction.
 * Le KPI mensuel vs N-1 DJU-ajusté est calculé backend
 * (cockpit_facts_service.py + monthly_comparison_service.py).
 *
 * Cible : page Pilotage (CommandCenter / route /cockpit/jour) Phase 3.1
 * du triptyque KPI hero.
 */
import SolKpiMonthlyVsN1 from '../../ui/sol/SolKpiMonthlyVsN1';
import useCockpitFacts from '../../hooks/useCockpitFacts';

export default function SolKpiMonthlyVsN1Container({ className = '' }) {
  const { facts, loading } = useCockpitFacts('current_month');

  if (loading || !facts) return null;

  const monthlyData = facts?.consumption?.monthly_vs_n1;
  if (!monthlyData) return null;

  return <SolKpiMonthlyVsN1 data={monthlyData} className={className} />;
}
