/**
 * EmissionFactorsContext — source unique facteurs CO₂ (ADEME) pour le frontend.
 *
 * Fetch au mount /api/config/emission-factors qui lit
 * `backend/config/emission_factors.py` (ADEME Base Empreinte V23.6).
 *
 * Doctrine PROMEOS (fix P0 #1-5 audit QA Guardian 2026-04-15) :
 * - Jamais hardcoder un facteur CO₂ dans un composant frontend.
 * - Toujours passer par `useEmissionFactors()` (avec fallback aux constants.js
 *   le temps que l'API charge, puis valeurs backend).
 * - Pour persistence en DB : envoyer `estimated_savings_kwh_year`, laisser
 *   le backend calculer via `_resolve_co2e_kg` (routes/actions.py).
 */
import React, { createContext, useContext, useEffect, useState } from 'react';

import { CO2E_FACTOR_KG_PER_KWH } from '../pages/consumption/constants';

// Fallback utilisé avant que l'API réponde (premier render, offline, erreur).
// Valeurs alignées sur backend/config/emission_factors.py.
const FALLBACK_FACTORS = {
  elec: {
    kgco2e_per_kwh: CO2E_FACTOR_KG_PER_KWH, // 0.052 ADEME V23.6
    source: 'Fallback ADEME V23.6 (API non chargée)',
    year: 2024,
  },
  gaz: {
    kgco2e_per_kwh: 0.227,
    source: 'Fallback ADEME V23.6 (API non chargée)',
    year: 2024,
  },
};

const EmissionFactorsContext = createContext(null);

export function EmissionFactorsProvider({ children }) {
  const [factors, setFactors] = useState(FALLBACK_FACTORS);
  const [sourceVersion, setSourceVersion] = useState('Fallback');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    fetch('/api/config/emission-factors')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        if (cancelled) return;
        if (data && data.factors) {
          setFactors(data.factors);
          setSourceVersion(data.source_version || 'ADEME (backend)');
        }
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        // Fallback silencieux : on garde FALLBACK_FACTORS, on log l'erreur.
        // Les composants continuent à fonctionner avec 0.052 ADEME.
        // eslint-disable-next-line no-console
        console.warn('[EmissionFactorsContext] fallback, fetch failed:', err?.message);
        setError(err?.message || 'fetch failed');
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <EmissionFactorsContext.Provider value={{ factors, sourceVersion, loading, error }}>
      {children}
    </EmissionFactorsContext.Provider>
  );
}

/**
 * Hook principal. Retourne le facteur ELEC (kgCO₂e/kWh) — cas d'usage le
 * plus fréquent dans les pages de consommation.
 *
 * Usage :
 *   const co2Factor = useElecCo2Factor();
 *   const co2Kg = kwh * co2Factor;
 */
export function useElecCo2Factor() {
  const ctx = useContext(EmissionFactorsContext);
  if (!ctx) {
    // Hors provider : on retourne le fallback pour que les composants ne crashent pas.
    // (Useful pour les tests unitaires qui ne wrappent pas le Provider.)
    return FALLBACK_FACTORS.elec.kgco2e_per_kwh;
  }
  return ctx.factors?.elec?.kgco2e_per_kwh ?? FALLBACK_FACTORS.elec.kgco2e_per_kwh;
}

/**
 * Hook complet : retourne tous les facteurs + métadonnées.
 * Usage :
 *   const { factors, sourceVersion, loading, error } = useEmissionFactors();
 */
export function useEmissionFactors() {
  const ctx = useContext(EmissionFactorsContext);
  if (!ctx) {
    return {
      factors: FALLBACK_FACTORS,
      sourceVersion: 'Fallback (no provider)',
      loading: false,
      error: null,
    };
  }
  return ctx;
}
