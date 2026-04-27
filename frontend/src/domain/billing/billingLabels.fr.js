/**
 * PROMEOS — Labels centralisés Bill-Intelligence (FR).
 *
 * Source de vérité unique pour les libellés affichés côté facturation
 * (page BillIntelPage + drawer InsightDrawer). Évite la duplication
 * livrée Sprint 2 Vague A ét2 (TYPE_LABELS_TEXT répliqué dans 2 fichiers).
 *
 * Doctrine : labels en français côté frontend uniquement. Le backend
 * retourne des codes types (`shadow_gap`, `reseau_mismatch`...) — la
 * traduction est ici. Pattern aligné sur `complianceLabels.fr.js`.
 *
 * Sprint 2 Vague B ét6' (label_registries cross-vue, 27/04/2026).
 *
 * Note : la version JSX enrichie avec `<Explain>` reste locale à chaque
 * consommateur (BillIntelPage / InsightDrawer) car React doit pouvoir
 * mixer libellé + composants. Le registre canonique porte le PLAIN TEXT
 * — c'est la source de vérité éditoriale, le wrap JSX est cosmétique.
 */

/**
 * 15 codes anomalies billing → phrases narratives non-sachant (Marie/CFO).
 * Vague A ét2 grammaire éditoriale §5 + ADR-004 (acronymes encapsulés Explain
 * côté JSX). Verbe partagé « ne se reconstitue pas » crée la signature
 * éditoriale Bill-Intel reconnaissable.
 */
export const BILLING_INSIGHT_TYPE_LABELS = Object.freeze({
  shadow_gap: 'Cette facture coûte plus que la facturation théorique',
  unit_price_high: 'Le prix au kWh dépasse vos repères',
  duplicate_invoice: 'Cette facture semble facturée deux fois',
  missing_period: "Une période de facturation n'a pas été couverte",
  period_too_long: 'Cette période dépasse la durée habituelle',
  negative_kwh: 'Une consommation négative en kWh est apparue',
  zero_amount: 'Le montant facturé est nul',
  lines_sum_mismatch: 'Le total ne se reconstitue pas à partir des lignes',
  consumption_spike: 'Pic de consommation inhabituel détecté',
  price_drift: 'Le prix unitaire dérive depuis plusieurs mois',
  ttc_coherence: 'Le total TTC ne se reconstitue pas',
  contract_expiry: 'Votre contrat est arrivé à échéance',
  reseau_mismatch: "L'acheminement réseau dépasse le tarif TURPE attendu",
  taxes_mismatch: "Les taxes dépassent l'accise et la CTA en vigueur",
  reconciliation_mismatch: 'Écart compteur / facture détecté',
});

/**
 * Statuts workflow d'une anomalie billing (insight). Cohérent avec
 * complianceLabels.fr.WORKFLOW_LABELS mais formulé pour le contexte
 * facturation : « Pris en charge » plutôt que « En cours ».
 */
export const BILLING_INSIGHT_STATUS_LABELS = Object.freeze({
  open: 'Ouvert',
  ack: 'Pris en charge',
  resolved: 'Résolu',
  false_positive: 'Faux positif',
});

/**
 * Statuts d'une facture importée (côté table d'inventaire).
 */
export const BILLING_INVOICE_STATUS_LABELS = Object.freeze({
  imported: 'Importé',
  validated: 'Validé',
  audited: 'Audité',
  anomaly: 'Anomalie',
  archived: 'Archivé',
});

/**
 * Sévérité d'une anomalie billing — masculin (s'accorde avec "écart" /
 * "doublon" / "pic" qui sont les substantifs sous-jacents).
 *
 * Note : `complianceLabels.fr.js::SEVERITY_LABELS` utilise le féminin
 * ("Élevée" pour s'accorder avec "Sévérité"). Les deux registres
 * coexistent volontairement — la grammaire suit le contexte d'affichage,
 * pas la donnée.
 */
export const BILLING_SEVERITY_LABELS = Object.freeze({
  critical: 'Critique',
  high: 'Élevé',
  medium: 'Moyen',
  low: 'Faible',
});

/**
 * Mapping sévérité → variant Badge UI (cohérent avec le composant Badge
 * du design system).
 */
export const BILLING_SEVERITY_BADGE = Object.freeze({
  critical: 'crit',
  high: 'warn',
  medium: 'info',
  low: 'neutral',
});

/**
 * Helper text fallback : retourne le label canonique si présent,
 * sinon le code brut (pour codes types non encore narrativisés).
 */
export function billingInsightLabel(type) {
  return BILLING_INSIGHT_TYPE_LABELS[type] || type;
}
