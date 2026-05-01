/**
 * PROMEOS — useDataReadiness
 * Composed hook: activation + readiness gate.
 * Combines useActivationData + buildActivationChecklist + computeDataReadinessState.
 *
 * Phase 26 (sprint retro Cockpit Dual Sol2 — audit prod 2026-05-01) :
 *   Accepte un nouveau param `cockpitFactsBilling` qui, si fourni, est
 *   propagé à useActivationData pour skipper l'appel /api/billing/summary.
 *   Permet à DataReadinessBadge de réutiliser le payload `_facts` quand il
 *   est déjà chargé par la page Cockpit hôte (single source).
 */
import { useMemo } from 'react';
import useActivationData from './useActivationData';
import { buildActivationChecklist } from '../models/dataActivationModel';
import { computeDataReadinessState } from '../models/dataReadinessModel';

/**
 * @param {object} kpis — { total, conformes, nonConformes, aRisque, couvertureDonnees }
 * @param {object} [options]
 * @param {boolean} [options.operatModuleActive]
 * @param {boolean} [options.demoEnabled]
 * @param {object} [options.cockpitFactsBilling] — `_facts.billing` si dispo (Phase 26).
 * @returns {{ readinessState: ReadinessState|null, activation: ActivationResult, loading: boolean }}
 */
export default function useDataReadiness(
  kpis,
  {
    operatModuleActive = false,
    demoEnabled = false,
    cockpitFactsBilling = null,
    waitForFacts = false,
  } = {}
) {
  const { billingSummary, purchaseSignals, efaDashboard, connectors, loading } = useActivationData(
    kpis?.total,
    { cockpitFactsBilling, waitForFacts }
  );

  const activation = useMemo(
    () => buildActivationChecklist({ kpis, billingSummary: billingSummary || {}, purchaseSignals }),
    [kpis, billingSummary, purchaseSignals]
  );

  const readinessState = useMemo(() => {
    if (loading) return null;
    return computeDataReadinessState(activation, {
      billingMonthCount: billingSummary?.coverage_months ?? billingSummary?.distinct_months ?? 0,
      efaDashboard,
      connectors: Array.isArray(connectors) ? connectors : [],
      operatModuleActive,
      hasManualImport: (activation?.activatedCount ?? 0) > 1,
      demoEnabled,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activation, billingSummary, efaDashboard, connectors, operatModuleActive, loading]);

  return { readinessState, activation, loading };
}
