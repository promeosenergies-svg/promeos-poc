/**
 * RegulatoryRatesContext — SoT runtime sources réglementaires PROMEOS (Sprint C-3 Phase 3.3).
 *
 * Consomme l'endpoint backend GET /api/regulatory/rates qui lit le YAML
 * versionné git `backend/config/sources_reglementaires.yaml` (~68 termes / 9 domaines).
 *
 * Doctrine Sprint C-3 :
 * - Migre `frontend/src/domain/regulatory_rates.js` (hardcoded 184L FE) vers fetch API.
 * - Cache module-level partagé entre tous les consumers (évite N fetches simultanés).
 * - Pattern aligné avec `EmissionFactorsContext.jsx` (Phase 4.4 Sprint C-2) :
 *   - fetch au mount du Provider
 *   - fallback silencieux sur erreur (pas de throw qui casse le render)
 *   - hooks ciblés `useRegulatoryRates()` + `useRegulatorySource(termId)`
 *
 * Cas d'usage Phase 3.5 — TraceTooltip composant FE (R10 différenciateur) :
 *   const trace = useRegulatorySource('CO2_FACTOR_ELEC_KGCO2_PER_KWH');
 *   <TraceTooltip term={trace}>0.052 kgCO2/kWh</TraceTooltip>
 */
import React, { createContext, useContext, useEffect, useState } from 'react';

const RegulatoryRatesContext = createContext(null);

// Cache module-level partagé (évite N fetches simultanés cf. risque R2 Phase 3.1).
// Réinitialisable pour tests via `resetRegulatoryRatesCache()`.
let _ratesCache = null;
let _fetchPromise = null;

export function resetRegulatoryRatesCache() {
  _ratesCache = null;
  _fetchPromise = null;
}

export function RegulatoryRatesProvider({ children }) {
  const [rates, setRates] = useState(_ratesCache);
  const [loading, setLoading] = useState(!_ratesCache);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (_ratesCache) {
      // Hit cache : déjà chargé par un autre consumer
      setRates(_ratesCache);
      setLoading(false);
      return;
    }

    let cancelled = false;

    if (!_fetchPromise) {
      _fetchPromise = fetch('/api/regulatory/rates')
        .then((r) => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json();
        })
        .then((data) => {
          _ratesCache = data;
          return data;
        })
        .catch((err) => {
          // Reset promise pour permettre retry au prochain mount
          _fetchPromise = null;
          throw err;
        });
    }

    _fetchPromise
      .then((data) => {
        if (cancelled) return;
        setRates(data);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        // eslint-disable-next-line no-console
        console.warn('[RegulatoryRatesContext] fallback, fetch failed:', err?.message);
        setError(err?.message || 'fetch failed');
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <RegulatoryRatesContext.Provider value={{ rates, loading, error }}>
      {children}
    </RegulatoryRatesContext.Provider>
  );
}

/**
 * Hook principal — retourne l'état complet du context.
 *
 * Hors Provider : retourne fallback `{ rates: null, loading: false, error: null }`
 * pour éviter de casser les tests unitaires qui ne wrappent pas le Provider.
 */
export function useRegulatoryRates() {
  const ctx = useContext(RegulatoryRatesContext);
  if (!ctx) {
    return { rates: null, loading: false, error: null };
  }
  return ctx;
}

/**
 * Hook ciblé — retourne un terme spécifique par ID.
 *
 * Usage typique TraceTooltip Phase 3.5 :
 *   const trace = useRegulatorySource('CO2_FACTOR_ELEC_KGCO2_PER_KWH');
 *   if (!trace) return null; // loading ou inconnu
 *   return <span title={trace.source.label}>{trace.value} {trace.unit}</span>;
 */
export function useRegulatorySource(termId) {
  const { rates, loading, error } = useRegulatoryRates();
  if (loading || error || !rates?.terms || !termId) return null;
  return rates.terms[termId] || null;
}
