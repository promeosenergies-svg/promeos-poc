/**
 * PROMEOS — useDataReadiness
 * Composed hook: activation + readiness gate.
 * Combines useActivationData + buildActivationChecklist + computeDataReadinessState.
 */
import { useMemo } from 'react';
import useActivationData from './useActivationData';
import { buildActivationChecklist } from '../models/dataActivationModel';
import { computeDataReadinessState } from '../models/dataReadinessModel';

/**
 * @param {object} kpis — { total, conformes, nonConformes, aRisque, couvertureDonnees }
 * @param {{ operatModuleActive?: boolean }} options
 * @returns {{ readinessState: ReadinessState|null, activation: ActivationResult, loading: boolean }}
 */
export default function useDataReadiness(kpis, { operatModuleActive = false } = {}) {
  const { billingSummary, purchaseSignals, efaDashboard, connectors, loading } = useActivationData(kpis?.total);

  const activation = useMemo(
    () => buildActivationChecklist({ kpis, billingSummary: billingSummary || {}, purchaseSignals }),
    [kpis, billingSummary, purchaseSignals],
  );

  const readinessState = useMemo(() => {
    if (loading) return null;
    return computeDataReadinessState(activation, {
      billingMonthCount: billingSummary?.distinct_months ?? 0,
      efaDashboard,
      connectors: Array.isArray(connectors) ? connectors : [],
      operatModuleActive,
      hasManualImport: (activation?.activatedCount ?? 0) > 1,
    });
  }, [activation, billingSummary, efaDashboard, connectors, operatModuleActive, loading]);

  return { readinessState, activation, loading };
}
