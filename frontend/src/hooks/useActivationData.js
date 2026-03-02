/**
 * PROMEOS — useActivationData
 * Shared hook for activation data (billing + purchase + contracts).
 * Deduplicates the triple-fetch used by DataActivationPanel, ImpactDecisionPanel, ActivationPage.
 *
 * Features:
 *   - In-flight promise deduplication (same scope key → same request)
 *   - Cancelled flag for unmount safety
 *   - Normalizes purchase signals via normalizePurchaseSignals()
 */
import { useState, useEffect, useRef } from 'react';
import { getBillingSummary, getPurchaseRenewals, patrimoineContracts, getTertiaireDashboard, listConnectors } from '../services/api';
import { normalizePurchaseSignals } from '../models/purchaseSignalsContract';

// In-flight promise cache — avoids duplicate network requests when multiple
// components mount simultaneously with the same totalSites value.
const _inflight = new Map();

function _fetchAll(totalSites) {
  const key = `activation-${totalSites}`;
  if (_inflight.has(key)) return _inflight.get(key);

  const promise = Promise.all([
    getBillingSummary().catch(() => ({})),
    getPurchaseRenewals().catch(() => ({ total: 0, renewals: [] })),
    patrimoineContracts().catch(() => ({ total: 0, contracts: [] })),
    getTertiaireDashboard().catch(() => null),
    listConnectors().catch(() => []),
  ]).then(([billing, renewals, contracts, efaDashboard, connectors]) => {
    const signals = normalizePurchaseSignals({ renewals, contracts, totalSites });

    // Extract contract site IDs
    const rawContracts = contracts?.contracts ?? contracts?.data ?? [];
    const contractSiteIds = new Set(
      (Array.isArray(rawContracts) ? rawContracts : [])
        .map((c) => c?.site_id)
        .filter(Boolean),
    );

    return { billingSummary: billing, purchaseSignals: signals, contractSiteIds, efaDashboard, connectors };
  }).finally(() => {
    _inflight.delete(key);
  });

  _inflight.set(key, promise);
  return promise;
}

/**
 * @param {number} totalSites — number of sites in scope (triggers re-fetch when changed)
 * @returns {{ billingSummary, purchaseSignals, contractSiteIds, loading, error, refetch }}
 */
export default function useActivationData(totalSites) {
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
    setLoading(true);
    setError(null);
    _fetchAll(totalSites ?? 0)
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
    return () => { mountRef.current = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [totalSites]);

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
