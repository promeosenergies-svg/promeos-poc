/**
 * PROMEOS — useActivationData
 * Shared hook for activation data (billing + purchase + contracts).
 * Deduplicates the triple-fetch used by DataActivationPanel, ImpactDecisionPanel, ActivationPage.
 *
 * Features:
 *   - In-flight promise deduplication (same scope key → same request)
 *   - Cancelled flag for unmount safety
 *   - Normalizes purchase signals via normalizePurchaseSignals()
 *
 * Phase 26 (sprint retro Cockpit Dual Sol2 — audit prod 2026-05-01) :
 *   - Accepte un nouveau param `cockpitFactsBilling` (objet `_facts.billing`).
 *     Si fourni, le hook NE refait PAS l'appel `getBillingSummary()` et
 *     utilise directement les valeurs du payload `_facts` (single source).
 *     Élimine 2× /api/billing/summary au mount /cockpit/* (mesure preview
 *     prod : 2 appels redondants détectés).
 *   - Cohérence règle d'or "_facts source unique" du sprint Cockpit Dual.
 */
import { useState, useEffect, useRef } from 'react';
import {
  getBillingSummary,
  getPurchaseRenewals,
  patrimoineContracts,
  getTertiaireDashboard,
  listConnectors,
} from '../services/api';
import { normalizePurchaseSignals } from '../models/purchaseSignalsContract';

// In-flight promise cache — avoids duplicate network requests when multiple
// components mount simultaneously with the same totalSites value.
const _inflight = new Map();

function _fetchAll(totalSites, cockpitFactsBilling) {
  // Phase 26 : si _facts.billing est fourni, on skippe le call billing/summary.
  // Le cache key inclut donc la présence de cockpitFactsBilling.
  const cacheKey = cockpitFactsBilling
    ? `activation-${totalSites}-with-facts`
    : `activation-${totalSites}`;
  if (_inflight.has(cacheKey)) return _inflight.get(cacheKey);

  // Si on a déjà les données billing dans _facts, on évite l'appel REST.
  const billingPromise = cockpitFactsBilling
    ? Promise.resolve({
        total_invoices: cockpitFactsBilling.total_invoices ?? 0,
        total_eur: cockpitFactsBilling.total_eur ?? 0,
        total_kwh: cockpitFactsBilling.total_kwh ?? 0,
        coverage_months: cockpitFactsBilling.coverage_months ?? 0,
      })
    : getBillingSummary().catch(() => ({}));

  const promise = Promise.all([
    billingPromise,
    getPurchaseRenewals().catch(() => ({ total: 0, renewals: [] })),
    patrimoineContracts().catch(() => ({ total: 0, contracts: [] })),
    getTertiaireDashboard().catch(() => null),
    listConnectors().catch(() => []),
  ])
    .then(([billing, renewals, contracts, efaDashboard, connectors]) => {
      const signals = normalizePurchaseSignals({ renewals, contracts, totalSites });

      // Extract contract site IDs
      const rawContracts = contracts?.contracts ?? contracts?.data ?? [];
      const contractSiteIds = new Set(
        (Array.isArray(rawContracts) ? rawContracts : []).map((c) => c?.site_id).filter(Boolean)
      );

      return {
        billingSummary: billing,
        purchaseSignals: signals,
        contractSiteIds,
        efaDashboard,
        connectors,
      };
    })
    .finally(() => {
      _inflight.delete(cacheKey);
    });

  _inflight.set(cacheKey, promise);
  return promise;
}

/**
 * @param {number} totalSites — number of sites in scope (triggers re-fetch when changed)
 * @param {object} [opts] — optional config
 * @param {object} [opts.cockpitFactsBilling] — `_facts.billing` payload (Phase 26).
 *   Si fourni, le hook NE call PAS `/api/billing/summary` (single source).
 * @param {boolean} [opts.waitForFacts] — Phase 26 : si true, le hook diffère
 *   le fetch tant que `cockpitFactsBilling` n'est pas résolu (évite le call
 *   billing/summary parasite pendant le 1er render avant que useCockpitFacts
 *   ait répondu). À utiliser quand le caller possède un useCockpitFacts en
 *   cours.
 * @returns {{ billingSummary, purchaseSignals, contractSiteIds, loading, error, refetch }}
 */
export default function useActivationData(totalSites, opts = {}) {
  const { cockpitFactsBilling = null, waitForFacts = false } = opts;
  const [data, setData] = useState({
    billingSummary: {},
    purchaseSignals: null,
    contractSiteIds: new Set(),
    efaDashboard: null,
    connectors: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const mountRef = useRef(true);

  const fetchData = () => {
    // Phase 26 timing fix : si waitForFacts=true et facts pas encore résolus,
    // on ne déclenche pas le fetch (évite call billing/summary parasite).
    if (waitForFacts && !cockpitFactsBilling) return;
    setLoading(true);
    setError(null);
    _fetchAll(totalSites ?? 0, cockpitFactsBilling)
      .then((result) => {
        if (mountRef.current) {
          setData(result);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (mountRef.current) {
          setError(err);
          setLoading(false);
        }
      });
  };

  useEffect(() => {
    mountRef.current = true;
    fetchData();
    return () => {
      mountRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [totalSites, cockpitFactsBilling, waitForFacts]);

  return {
    billingSummary: data.billingSummary,
    purchaseSignals: data.purchaseSignals,
    contractSiteIds: data.contractSiteIds,
    efaDashboard: data.efaDashboard,
    connectors: data.connectors,
    loading,
    error,
    refetch: fetchData,
  };
}
