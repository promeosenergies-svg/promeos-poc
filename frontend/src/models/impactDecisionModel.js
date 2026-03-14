/**
 * PROMEOS — Impact & Décision — Modèle pur (aucun import React)
 * Calculs déterministes V1 pour le panneau Impact & Décision du Cockpit.
 *
 * Exports:
 *   computeImpactKpis(kpis, billingSummary)  → { risqueConformite, surcoutFacture, opportuniteOptim }
 *   computeRecommendation(impact, kpis)      → { titre, bullets, cta, ctaPath }
 */

import { fmtEur } from '../utils/format';

// ── Taux heuristique V1 pour l'opportunité optimisation ─────────────────────
const OPTIM_RATE_V1 = 0.01; // 1% du montant facturé total

/**
 * Calcule les 3 KPIs Impact & Décision.
 *
 * @param {object} kpis            — KPIs Cockpit (risqueTotal, nonConformes, aRisque…)
 * @param {object} billingSummary  — résultat de getBillingSummary() ou {}
 * @returns {{ risqueConformite: number, surcoutFacture: number, opportuniteOptim: number,
 *             risqueAvailable: boolean, surcoutAvailable: boolean, optimAvailable: boolean }}
 */
export function computeImpactKpis(kpis = {}, billingSummary = {}) {
  // 1. Risque conformité — directement depuis le scope
  const risqueConformite = kpis.risqueTotal ?? 0;
  // Available dès qu'on a des sites (risque 0 € = bonne nouvelle, pas donnée manquante)
  const risqueAvailable = (kpis.total ?? 0) > 0;

  // 2. Surcoût facture — delta pertes billing (clamp >= 0)
  const totalLoss = billingSummary?.total_loss_eur ?? 0;
  const surcoutFacture = Math.max(0, totalLoss);
  const surcoutAvailable = totalLoss > 0 || (billingSummary?.total_invoices ?? 0) > 0;

  // 3. Opportunité optimisation — heuristique V1: 1% du total facturé
  const totalEur = billingSummary?.total_eur ?? 0;
  const opportuniteOptim = Math.round(totalEur * OPTIM_RATE_V1);
  const optimAvailable = totalEur > 0;

  return {
    risqueConformite,
    surcoutFacture,
    opportuniteOptim,
    risqueAvailable,
    surcoutAvailable,
    optimAvailable,
  };
}

/**
 * Détermine la recommandation prioritaire (rule-based V1).
 *
 * Règle:
 *   max(risqueConformite, surcoutFacture, opportuniteOptim) → thème de la reco.
 *   Si tout à 0 → recommandation par défaut "compléter les données".
 *
 * @param {object} impact  — résultat de computeImpactKpis()
 * @param {object} kpis    — KPIs Cockpit
 * @returns {{ key, titre, bullets: string[], cta, ctaPath }}
 */
export function computeRecommendation(impact = {}, kpis = {}) {
  const { risqueConformite = 0, surcoutFacture = 0, opportuniteOptim = 0 } = impact;
  const { nonConformes = 0, aRisque = 0 } = kpis;

  const maxVal = Math.max(risqueConformite, surcoutFacture, opportuniteOptim);

  // Cas tout à zéro — données manquantes
  if (maxVal === 0) {
    return {
      key: 'no_data',
      titre: 'Compléter les données pour activer les recommandations',
      bullets: [
        'Aucune donnée de risque, facture ou consommation détectée',
        'Importez votre patrimoine et vos factures',
        'Les recommandations apparaîtront automatiquement',
      ],
      cta: 'Importer le patrimoine',
      ctaPath: '/patrimoine',
    };
  }

  // Risque conformité est le plus élevé
  if (risqueConformite >= surcoutFacture && risqueConformite >= opportuniteOptim) {
    const sitesCount = nonConformes + aRisque;
    return {
      key: 'conformite',
      titre: `Priorité : réduire le risque conformité`,
      bullets: [
        `${sitesCount} site${sitesCount > 1 ? 's' : ''} non conforme${sitesCount > 1 ? 's' : ''} ou à risque`,
        `Risque financier estimé : ${_fmtEur0(risqueConformite)}`,
        'Échéance Décret Tertiaire — actions correctives recommandées',
      ],
      cta: 'Voir les sites à risque',
      ctaPath: '/conformite',
    };
  }

  // Surcoût facture est le plus élevé
  if (surcoutFacture >= opportuniteOptim) {
    return {
      key: 'facture',
      titre: `Priorité : corriger les anomalies facture`,
      bullets: [
        `Surcoût détecté : ${_fmtEur0(surcoutFacture)}`,
        'Anomalies identifiées par le moteur de facturation théorique',
        'Vérifiez les écarts prix, volumes et doublons',
      ],
      cta: 'Voir les anomalies',
      ctaPath: '/bill-intel',
    };
  }

  // Opportunité optimisation est le max
  return {
    key: 'optimisation',
    titre: `Priorité : lancer l'optimisation énergétique`,
    bullets: [
      `Économie potentielle estimée : ${_fmtEur0(opportuniteOptim)}`,
      'Basé sur 1 % du montant facturé total (heuristique V1)',
      'Identifiez les sites énergivores et les surconsommations',
    ],
    cta: 'Voir le diagnostic conso',
    ctaPath: '/diagnostic-conso',
  };
}

// ── Helpers internes ─────────────────────────────────────────────────────────

/** fmtEur retourne '—' pour 0 ; ici on veut un texte explicite dans les bullets. */
function _fmtEur0(v) {
  return v ? fmtEur(v) : 'non estimé';
}
