/**
 * RegulatoryConstantsContext — source unique seuils réglementaires (VNU/APER/TURPE/OPERAT).
 *
 * Fetch au mount /api/config/regulatory-constants qui lit doctrine/constants.py
 * et referentials/market_tariffs_2026.yaml côté backend.
 *
 * Doctrine PROMEOS §8.1 :
 * - Jamais hardcoder un seuil réglementaire dans un composant frontend.
 * - Toujours passer par useRegulatoryConstants() avec fallback jusqu'au chargement.
 * - Fix P0-5 Vague2 EPIC #274 — CockpitDecision.jsx seuils 78/110 €/MWh, 20 €/m²/an.
 */
import React, { createContext, useContext, useEffect, useState } from 'react';

// Fallback utilisé avant que l'API réponde (premier render, offline, erreur).
// Valeurs alignées sur backend/doctrine/constants.py + referentials/market_tariffs_2026.yaml.
const FALLBACK_CONSTANTS = {
  vnu: {
    seuil_bas_eur_mwh: 78.0,
    seuil_haut_eur_mwh: 110.0,
    source: 'Fallback LF 2025 art. 17 (API non chargée)',
    label: 'Versement Nucléaire Universel',
    activation: '2027 si EPEX dépasse seuil',
  },
  aper: {
    penalite_eur_m2_an: 20,
    surface_min_m2: 1500,
    deadline_iso: '2028-01-01',
    source: 'Fallback Loi 2023-175 (API non chargée)',
    label: 'APER — solarisation parkings',
  },
  turpe7_hc: {
    plage_meridienne: '11h-17h',
    source: 'Fallback CRE 2025-78 (API non chargée)',
    label: 'TURPE 7 reprogrammation HC méridiennes',
  },
  operat: {
    penalite_eur: 1500,
    deadline_declaration_iso: '2026-09-30',
    source: 'Fallback Arrêté Tertiaire 2024-DGEC (API non chargée)',
    label: 'OPERAT — déclaration consommations 2025',
  },
};

const RegulatoryConstantsContext = createContext(null);

export function RegulatoryConstantsProvider({ children }) {
  const [constants, setConstants] = useState(FALLBACK_CONSTANTS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    fetch('/api/config/regulatory-constants')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        if (cancelled) return;
        // Merge backend data sur les clés connues — ignore la clé "doctrine"
        const merged = { ...FALLBACK_CONSTANTS };
        if (data?.vnu) merged.vnu = { ...FALLBACK_CONSTANTS.vnu, ...data.vnu };
        if (data?.aper) merged.aper = { ...FALLBACK_CONSTANTS.aper, ...data.aper };
        if (data?.turpe7_hc)
          merged.turpe7_hc = { ...FALLBACK_CONSTANTS.turpe7_hc, ...data.turpe7_hc };
        if (data?.operat) merged.operat = { ...FALLBACK_CONSTANTS.operat, ...data.operat };
        setConstants(merged);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        // Fallback silencieux : on garde FALLBACK_CONSTANTS, log l'erreur.
        // eslint-disable-next-line no-console
        console.warn('[RegulatoryConstantsContext] fallback, fetch failed:', err?.message);
        setError(err?.message || 'fetch failed');
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <RegulatoryConstantsContext.Provider value={{ constants, loading, error }}>
      {children}
    </RegulatoryConstantsContext.Provider>
  );
}

/**
 * Hook principal. Retourne toutes les constantes réglementaires.
 *
 * Usage :
 *   const { constants } = useRegulatoryConstants();
 *   const vnuSeuil = constants.vnu.seuil_bas_eur_mwh; // 78.0
 */
export function useRegulatoryConstants() {
  const ctx = useContext(RegulatoryConstantsContext);
  if (!ctx) {
    // Hors provider : fallback pour que les composants ne crashent pas.
    return {
      constants: FALLBACK_CONSTANTS,
      loading: false,
      error: null,
    };
  }
  return ctx;
}
