/**
 * PROMEOS — Data Activation Model V37 (logique pure, aucun import React)
 *
 * Agrege les 5 dimensions d'activation a partir des donnees deja presentes
 * dans le state du Cockpit (kpis + billingSummary + purchaseSignals).
 * Aucune nouvelle API.
 *
 * Exports:
 *   ACTIVATION_DIMENSIONS             — array des 5 cles de dimension
 *   ACTIVATION_THRESHOLD              — seuil levier (si activatedCount < seuil)
 *   buildActivationChecklist(input)   → ActivationResult
 *   computeActivatedCount(input)      → number (pour leverEngine)
 */

import { isPurchaseAvailable } from './purchaseSignalsContract';
import { toPurchase } from '../services/routes';

// ── Constantes ──────────────────────────────────────────────────────────────

export const ACTIVATION_DIMENSIONS = ['patrimoine', 'conformite', 'consommation', 'facturation', 'achat'];
export const ACTIVATION_THRESHOLD = 3;

/**
 * @typedef {object} ActivationDimension
 * @property {string}  key         — cle technique
 * @property {string}  label       — libelle FR
 * @property {string}  description — description FR courte
 * @property {boolean} available   — true si la brique est active
 * @property {number}  coverage    — couverture 0-100
 * @property {string|null} detail  — detail FR (ex: "12 sites")
 * @property {string}  ctaPath     — route pour completer
 * @property {string}  ctaLabel    — libelle du CTA FR
 */

/**
 * @typedef {object} ActivationResult
 * @property {ActivationDimension[]} dimensions
 * @property {number}  activatedCount   — briques actives (0-5)
 * @property {number}  totalDimensions  — toujours 5
 * @property {number}  overallCoverage  — moyenne ponderee 0-100
 * @property {ActivationDimension|null} nextAction — premiere brique manquante
 */

/**
 * Construit la checklist d'activation a partir des donnees deja en scope.
 *
 * @param {{ kpis?: object, billingSummary?: object, purchaseSignals?: object }} input
 * @returns {ActivationResult}
 */
export function buildActivationChecklist({ kpis = {}, billingSummary = {}, purchaseSignals } = {}) {
  const total = kpis.total ?? 0;
  const conformesSites = (kpis.conformes ?? 0) + (kpis.nonConformes ?? 0) + (kpis.aRisque ?? 0);
  const hasBilling = (billingSummary.total_invoices ?? billingSummary.total_eur ?? 0) > 0;
  const hasPurchase = isPurchaseAvailable(purchaseSignals);

  const dimensions = [
    {
      key: 'patrimoine',
      label: 'Patrimoine',
      description: 'Sites importes dans le referentiel',
      available: total > 0,
      coverage: total > 0 ? 100 : 0,
      detail: total > 0 ? `${total} site${total > 1 ? 's' : ''}` : null,
      ctaPath: '/patrimoine',
      ctaLabel: 'Importer le patrimoine',
    },
    {
      key: 'conformite',
      label: 'Conformite reglementaire',
      description: 'Evaluation du statut conformite par site',
      available: conformesSites > 0,
      coverage: total > 0 ? Math.round((conformesSites / total) * 100) : 0,
      detail: conformesSites > 0 ? `${conformesSites}/${total} evalues` : null,
      ctaPath: '/conformite',
      ctaLabel: 'Evaluer la conformite',
    },
    {
      key: 'consommation',
      label: 'Donnees de consommation',
      description: 'Consommation energetique par site (kWh/an)',
      available: (kpis.couvertureDonnees ?? 0) > 0,
      coverage: kpis.couvertureDonnees ?? 0,
      detail: (kpis.couvertureDonnees ?? 0) > 0 ? `${kpis.couvertureDonnees}% des sites` : null,
      ctaPath: '/consommations/import',
      ctaLabel: 'Importer les consommations',
    },
    {
      key: 'facturation',
      label: 'Audit facturation',
      description: 'Factures analysees par le moteur d\'audit',
      available: hasBilling,
      coverage: hasBilling ? 100 : 0,
      detail: hasBilling ? `${billingSummary.total_invoices ?? '\u2013'} factures` : null,
      ctaPath: '/bill-intel',
      ctaLabel: 'Importer les factures',
    },
    {
      key: 'achat',
      label: 'Contrats energie',
      description: 'Contrats de fourniture renseignes par site',
      available: hasPurchase,
      coverage: purchaseSignals?.coverageContractsPct ?? 0,
      detail: hasPurchase ? `${purchaseSignals.totalContracts} contrat${purchaseSignals.totalContracts > 1 ? 's' : ''}` : null,
      ctaPath: toPurchase(),
      ctaLabel: 'Renseigner les contrats',
    },
  ];

  const activatedCount = dimensions.filter((d) => d.available).length;
  const totalDimensions = dimensions.length;
  const overallCoverage = totalDimensions > 0
    ? Math.round(dimensions.reduce((sum, d) => sum + d.coverage, 0) / totalDimensions)
    : 0;
  const nextAction = dimensions.find((d) => !d.available) || null;

  return { dimensions, activatedCount, totalDimensions, overallCoverage, nextAction };
}

/**
 * Compte rapide des briques actives (pour le leverEngine — evite d'instancier tout le checklist).
 *
 * @param {{ kpis?: object, billingSummary?: object, purchaseSignals?: object }} input
 * @returns {number} 0-5
 */
export function computeActivatedCount(input) {
  if (!input || typeof input !== 'object') return 0;
  const { kpis = {}, billingSummary = {}, purchaseSignals } = input;
  return [
    (kpis.total ?? 0) > 0,
    (kpis.conformes ?? 0) + (kpis.nonConformes ?? 0) + (kpis.aRisque ?? 0) > 0,
    (kpis.couvertureDonnees ?? 0) > 0,
    (billingSummary.total_invoices ?? billingSummary.total_eur ?? 0) > 0,
    isPurchaseAvailable(purchaseSignals),
  ].filter(Boolean).length;
}
