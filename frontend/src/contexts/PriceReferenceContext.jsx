/**
 * PriceReferenceContext — source unique prix de référence (fallback) pour le frontend.
 *
 * Fetch au mount /api/config/price-references qui lit la section `prix_reference`
 * du YAML tarifs_reglementaires (valeurs non-réglementaires, fallback spot moyen).
 *
 * Doctrine PROMEOS (queue 2 audit QA Guardian 2026-04-15) :
 * - Jamais hardcoder un prix de référence dans un composant frontend
 *   (`EUR_FACTOR = 0.068` supprimé partout).
 * - Toujours passer par `useElecPriceReference()` (avec fallback 0.068 le temps
 *   que l'API charge, puis valeur backend).
 * - ⚠️ Ce fallback N'EST PAS une source réglementaire (is_regulatory: false).
 *   Pour un coût réel, privilégier les contrats réels ou ParameterStore côté backend.
 */
import React, { createContext, useContext, useEffect, useState } from 'react';

// Fallback utilisé avant que l'API réponde (premier render, offline, erreur).
// Valeurs alignées sur backend/config/tarifs_reglementaires.yaml (prix_reference).
const FALLBACK_PRICES = {
  elec_eur_kwh: 0.068,
  gaz_eur_kwh: 0.045,
  source: 'Fallback PROMEOS POC (EPEX Spot 30j moyen, API non chargée)',
  valid_from: '2024-01-01',
  is_regulatory: false,
};

const PriceReferenceContext = createContext(null);

export function PriceReferenceProvider({ children }) {
  const [prices, setPrices] = useState(FALLBACK_PRICES);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    fetch('/api/config/price-references')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        if (cancelled) return;
        if (data && typeof data.elec_eur_kwh === 'number') {
          setPrices(data);
        }
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        // eslint-disable-next-line no-console
        console.warn('[PriceReferenceContext] fallback, fetch failed:', err?.message);
        setError(err?.message || 'fetch failed');
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <PriceReferenceContext.Provider value={{ prices, loading, error }}>
      {children}
    </PriceReferenceContext.Provider>
  );
}

/**
 * Hook shortcut — retourne le prix de référence élec (€/kWh).
 * Usage :
 *   const eurPerKwh = useElecPriceReference();
 *   const totalEur = kwh * eurPerKwh;
 */
export function useElecPriceReference() {
  const ctx = useContext(PriceReferenceContext);
  if (!ctx) {
    // Crash-proof hors provider (fallback).
    return FALLBACK_PRICES.elec_eur_kwh;
  }
  return ctx.prices?.elec_eur_kwh ?? FALLBACK_PRICES.elec_eur_kwh;
}

/**
 * Hook complet : prices + loading + error.
 */
export function usePriceReferences() {
  const ctx = useContext(PriceReferenceContext);
  if (!ctx) {
    return {
      prices: FALLBACK_PRICES,
      loading: false,
      error: null,
    };
  }
  return ctx;
}
