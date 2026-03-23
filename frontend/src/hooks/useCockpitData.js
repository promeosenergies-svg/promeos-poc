/**
 * useCockpitData — Agrège les données du cockpit exécutif.
 *
 * RÈGLE : Ce hook ne calcule RIEN. Il fetch, normalise, et expose.
 * Tout calcul métier est fait backend (P0 : /api/cockpit + /api/cockpit/trajectory).
 *
 * Appels parallèles :
 *   1. GET /api/cockpit           → KPIs exécutifs, risque, conformité
 *   2. GET /api/cockpit/trajectory → Trajectoire DT pré-calculée
 *   3. GET /api/actions/summary    → Compteurs actions (total, en cours, urgentes)
 *   4. GET /api/billing/summary    → Anomalies billing (total anomalies, montant)
 *
 * Retourne un objet stable, compatible avec le design validé.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { useScope } from '../contexts/ScopeContext';
import { logger } from '../services/logger';
import {
  getCockpit,
  getCockpitTrajectory,
  getActionsSummary,
  getBillingSummary,
} from '../services/api';

const TAG = 'CockpitData';

/**
 * Normalise la réponse /api/cockpit en shape stable pour le front.
 * Aucun calcul — juste renommage/défense contre null.
 */
function normalizeCockpitKpis(raw) {
  if (!raw?.stats) return null;
  const s = raw.stats;
  return {
    conformiteScore: s.compliance_score ?? null,
    conformiteSource: s.compliance_source ?? null,
    conformiteComputedAt: s.compliance_computed_at ?? null,
    risqueTotal: s.risque_financier_euro ?? 0,
    risqueBreakdown: s.risque_breakdown ?? null,
    totalSites: s.total_sites ?? 0,
    sitesActifs: s.sites_actifs ?? 0,
    avancementDecretPct: s.avancement_decret_pct ?? null,
    orgNom: raw.organisation?.nom ?? null,
  };
}

/**
 * Normalise la réponse /api/cockpit/trajectory.
 * Le front reçoit les séries prêtes — pas de calcul.
 */
function normalizeTrajectory(raw) {
  if (!raw?.annees?.length) return null;
  return {
    refYear: raw.ref_year,
    refKwh: raw.ref_kwh,
    reductionPctActuelle: raw.reduction_pct_actuelle,
    objectif2026Pct: raw.objectif_2026_pct ?? -25.0,
    annees: raw.annees ?? [],
    reelMwh: raw.reel_mwh ?? [],
    objectifMwh: raw.objectif_mwh ?? [],
    projectionMwh: raw.projection_mwh ?? [],
    jalons: raw.jalons ?? [],
    surfaceM2Total: raw.surface_m2_total ?? null,
    computedAt: raw.computed_at ?? null,
  };
}

/**
 * Normalise la réponse /api/actions/summary.
 */
function normalizeActions(raw) {
  if (!raw) return { total: 0, enCours: 0, urgentes: 0, potentielEur: 0 };
  return {
    total: raw.total ?? raw.total_actions ?? 0,
    enCours: raw.en_cours ?? raw.in_progress ?? 0,
    urgentes: raw.urgentes ?? raw.critical ?? 0,
    potentielEur: raw.potentiel_eur ?? raw.savings_eur ?? 0,
  };
}

/**
 * Normalise la réponse /api/billing/summary.
 */
function normalizeBilling(raw) {
  if (!raw) return { anomalies: 0, montantEur: 0 };
  return {
    anomalies: raw.anomalies_count ?? raw.total_anomalies ?? 0,
    montantEur: raw.pertes_estimees_eur ?? raw.amount_eur ?? 0,
  };
}

export function useCockpitData() {
  const { org } = useScope();
  const [state, setState] = useState({
    kpis: null,
    trajectoire: null,
    actions: null,
    billing: null,
    loading: true,
    error: null,
    lastFetchedAt: null,
  });

  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const fetchAll = useCallback(async () => {
    if (!org?.id) return;

    setState((prev) => ({ ...prev, loading: true, error: null }));
    logger.info(TAG, 'Fetching cockpit data', { orgId: org.id });

    try {
      const [cockpitRaw, trajectoireRaw, actionsRaw, billingRaw] = await Promise.all([
        getCockpit().catch((err) => {
          logger.error(TAG, 'getCockpit failed', { err: err.message });
          return null;
        }),
        getCockpitTrajectory().catch((err) => {
          logger.error(TAG, 'getCockpitTrajectory failed', { err: err.message });
          return null;
        }),
        getActionsSummary().catch((err) => {
          logger.error(TAG, 'getActionsSummary failed', { err: err.message });
          return null;
        }),
        getBillingSummary().catch((err) => {
          logger.error(TAG, 'getBillingSummary failed', { err: err.message });
          return null;
        }),
      ]);

      if (!mountedRef.current) return;

      setState({
        kpis: normalizeCockpitKpis(cockpitRaw),
        trajectoire: normalizeTrajectory(trajectoireRaw),
        actions: normalizeActions(actionsRaw),
        billing: normalizeBilling(billingRaw),
        loading: false,
        error: null,
        lastFetchedAt: new Date().toISOString(),
      });

      logger.info(TAG, 'Cockpit data loaded', {
        orgId: org.id,
        conformiteScore: cockpitRaw?.stats?.compliance_score,
        hasTraj: !!trajectoireRaw?.annees?.length,
      });
    } catch (err) {
      if (!mountedRef.current) return;
      logger.error(TAG, 'Cockpit fetch failed', { err: err.message });
      setState((prev) => ({ ...prev, loading: false, error: err.message }));
    }
  }, [org?.id]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  return { ...state, refetch: fetchAll };
}
