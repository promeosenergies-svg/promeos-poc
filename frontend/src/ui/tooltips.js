/**
 * PROMEOS — Tooltip content map
 * Centralise les textes d'aide pour éviter les duplications inline.
 *
 * Convention: TOOLTIPS.<page>.<key>
 */

export const TOOLTIPS = {
  executive: {
    risqueConformite:
      "Somme des risques financiers des sites non conformes ou à risque dans le périmètre actif.",
    surcoutFacture:
      "Total des pertes identifiées par le moteur d'audit facture (shadow billing).",
    opportuniteOptim:
      "Heuristique V1 : 1 % du montant facturé total — affiné à mesure que les données s'enrichissent.",
    calculsV1:
      "Calculs V1 — règles déterministes basées sur vos données réelles.",
    achatsEnergie:
      "Signaux dérivés des contrats renseignés — heuristique V1.",
    activationDonnees:
      "Couverture des 5 briques de données nécessaires aux recommandations.",
  },
};
