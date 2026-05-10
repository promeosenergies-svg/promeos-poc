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
// Valeurs alignées sur backend/doctrine/constants.py + sources_reglementaires.yaml.
// Phase L29.3 audit fix P1 — enrichi avec dt, primary_energy, readiness_weights
// (exposés par /api/config/regulatory-constants depuis Phase L28.1a) + champs
// vnu.tarif_unitaire_2026_eur_mwh, aper.surface_large_m2/solar_ratio_pct.
const FALLBACK_CONSTANTS = {
  vnu: {
    seuil_bas_eur_mwh: 78.0,
    seuil_haut_eur_mwh: 110.0,
    tarif_unitaire_2026_eur_mwh: 0.0,
    source: 'Fallback LF 2025 art. 17 (API non chargée)',
    label: 'Versement Nucléaire Universel',
    activation: '2027 si EPEX dépasse seuil',
  },
  aper: {
    penalite_eur_m2_an: 20,
    surface_min_m2: 1500,
    surface_large_m2: 10000,
    solar_ratio_pct: 50.0,
    // Phase L30.1 audit fix P1 — deadline_iso drift corrigé (2028-01-01 → 2028-07-01,
    // aligné sur APER_DEADLINE_SMALL_PARKING_DATE doctrine Phase L29.1).
    // deadline_iso = pour parkings 1500-10000 m² (legacy alias = SMALL).
    deadline_iso: '2028-07-01',
    deadline_large_iso: '2026-07-01', // parkings >10000 m² (IMMINENT) — APER_DEADLINE_LARGE_PARKING_DATE
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
  dt: {
    penalty_eur: 7500,
    penalty_at_risk_eur: 3750,
    source: 'Fallback Décret 2019-771 art. 9 + L.173-2 CCH (API non chargée)',
    label: 'Décret Tertiaire — sanctions',
  },
  primary_energy: {
    coef_elec: 1.9,
    coef_gas: 1.0,
    source: 'Fallback Arrêté ministériel 13/04/2023 (API non chargée)',
    label: 'Coefficient énergie primaire RE2020',
  },
  readiness_weights: {
    data: 0.3,
    conformity: 0.4,
    actions: 0.3,
    source: 'Fallback doctrine PROMEOS Sol §15 (API non chargée)',
    label: 'Pondérations Readiness score backend',
  },
  // Phase L31.1 audit fix P1 — exposition price_fallback (était hardcoded 68 €/MWh
  // dans CostSimulationCard.jsx:355 InfoTip). status: internal_fallback (YAML).
  price_fallback: {
    eur_per_kwh: 0.068,
    eur_per_mwh: 68.0,
    source: 'Fallback Observatoire CRE T4 2025 (API non chargée)',
    label: 'Prix fallback PROMEOS',
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
        // Phase L33.4 audit fix P1 simplify (Reviewer #2 audit 3/3) — merge générique
        // qui itère sur les clés FALLBACK_CONSTANTS. Avant : 8 if/spread répétés
        // (fragile à l'extension, copier-coller). Désormais zero maintenance pour
        // une nouvelle clé exposée par /api/config/regulatory-constants — il suffit
        // de l'ajouter dans FALLBACK_CONSTANTS. La clé "doctrine" du backend
        // (string narrative) est ignorée car non dans FALLBACK_CONSTANTS.
        const merged = Object.fromEntries(
          Object.entries(FALLBACK_CONSTANTS).map(([key, fallback]) => [
            key,
            data?.[key] ? { ...fallback, ...data[key] } : fallback,
          ])
        );
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
