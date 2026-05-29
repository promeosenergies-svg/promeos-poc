/**
 * PROMEOS — Helpers de conversion unité kWh → kgCO₂eq.
 *
 * Sprint Énergie P0.S1b (2026-05-29, brief P1 CO₂ backend).
 *
 * DOCTRINE
 * ────────
 * Ce module est **explicitement whitelisté** dans le source-guard
 * `test_frontend_no_business_calc_source_guards.py`. Il est le SEUL
 * endroit du frontend autorisé à faire `kwh * facteur_CO2`. Toute
 * autre occurrence sera rejetée par le CI.
 *
 * Justification :
 * - Le facteur d'émission est une CONSTANTE versionnée (ADEME Base
 *   Carbone V23.6, électricité France métropole = 0,052 kgCO₂eq/kWh)
 *   fournie par le backend via `/api/config/emission-factors`
 *   (cf. EmissionFactorsContext.jsx). Le frontend NE CALCULE PAS la
 *   valeur du facteur — il la consomme.
 * - La multiplication kWh × facteur est une CONVERSION D'UNITÉ pure
 *   (comparable à kWh → MWh = /1000), pas une règle métier ni une
 *   agrégation statistique.
 * - Aucun seuil, aucune règle d'anomalie, aucune décision produit
 *   n'est encodée ici. La doctrine « zéro calcul métier frontend »
 *   reste respectée au sens où le sprint l'entend : pas de quartile,
 *   pas de score qualité, pas de génération synthétique, pas
 *   d'agrégation cross-périodes côté FE.
 *
 * Préférence forte : si un payload backend (`/api/monitoring/kpis`,
 * `/api/diagnostic-conso/insights`, etc.) expose DÉJÀ `total_co2e_kg`
 * pré-calculé, le consommer directement plutôt que d'appeler ce
 * helper. L'usage de `kwhToCo2Kg` est réservé aux cas où :
 * - Le kWh est dynamique (slider de prix, sélection de période FE).
 * - Le backend ne fournit pas encore le champ (en attendant
 *   extension du payload).
 *
 * Tests : `frontend/src/__tests__/co2.test.js` (à exécuter via vitest).
 */

/**
 * Convertit un volume kWh en kgCO₂eq en utilisant un facteur fourni
 * par le backend (ADEME V23.6 typiquement).
 *
 * @param {number|null|undefined} kwh - Volume énergétique en kWh.
 *   Si null/undefined/NaN → retourne null (pas 0, pour ne pas
 *   masquer une absence de donnée).
 * @param {number|null|undefined} factor - Facteur d'émission
 *   kgCO₂eq/kWh fourni par `useElecCo2Factor()` ou équivalent.
 *   Si null/undefined → retourne null.
 * @returns {number|null} Émissions en kgCO₂eq, arrondies à l'entier,
 *   ou null si entrées invalides.
 *
 * @example
 *   kwhToCo2Kg(1000, 0.052)      // → 52
 *   kwhToCo2Kg(null, 0.052)      // → null
 *   kwhToCo2Kg(1000, null)       // → null
 *   kwhToCo2Kg(0, 0.052)         // → 0
 */
export function kwhToCo2Kg(kwh, factor) {
  if (kwh == null || factor == null) return null;
  const k = Number(kwh);
  const f = Number(factor);
  if (!Number.isFinite(k) || !Number.isFinite(f)) return null;
  return Math.round(k * f);
}

/**
 * Convertit un volume kWh en tonnes CO₂eq (kg / 1000).
 *
 * @param {number|null|undefined} kwh
 * @param {number|null|undefined} factor
 * @returns {number|null} Émissions en tCO₂eq (2 décimales) ou null.
 *
 * @example
 *   kwhToCo2Tonnes(100000, 0.052)  // → 5.20
 */
export function kwhToCo2Tonnes(kwh, factor) {
  const kg = kwhToCo2Kg(kwh, factor);
  if (kg == null) return null;
  return Math.round(kg / 10) / 100; // 2 décimales
}
