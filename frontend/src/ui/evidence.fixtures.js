/**
 * PROMEOS — Evidence V0 fixtures
 * Mock evidence objects for Cockpit + Explorer integration.
 */
import { buildEvidence } from './evidence';

export function evidenceConformite(scopeLabel) {
  return buildEvidence({
    id: 'exec-conformite',
    title: 'Score de conformité',
    scopeLabel,
    sources: [
      {
        kind: 'calc',
        label: 'Moteur RegOps — 4 réglementations',
        confidence: 'high',
        details: 'Évaluation déterministe Tertiaire, BACS, APER, CEE P6.',
        freshness: 'Recalculé à chaque chargement du cockpit',
        links: [{ label: 'Voir RegOps', href: '/regops' }],
      },
      {
        kind: 'manual',
        label: 'Données patrimoniales',
        confidence: 'medium',
        details: 'Surface, usage, puissance CVC — importées via HELIOS.',
        links: [{ label: 'Patrimoine', href: '/patrimoine' }],
      },
    ],
    method: [
      'Score = sites conformes / total sites × 100.',
      'Statut par site : conforme si 0 finding critique, sinon à risque ou non conforme.',
      'Chaque réglementation évaluée indépendamment (Tertiaire, BACS, APER, CEE P6).',
    ],
    assumptions: [
      'Les données patrimoniales (surface, usage) sont à jour.',
      'Aucun audit externe n\'est intégré — évaluation interne uniquement.',
    ],
  });
}

export function evidenceRisque(scopeLabel, risqueEur) {
  return buildEvidence({
    id: 'exec-risque',
    title: 'Risque financier estimé',
    valueLabel: risqueEur != null ? `${(risqueEur / 1000).toFixed(0)}k€` : null,
    scopeLabel,
    sources: [
      {
        kind: 'calc',
        label: 'Estimation heuristique V1',
        confidence: 'medium',
        details: 'Risque = somme des risque_eur par site non conforme.',
        freshness: 'Calculé dynamiquement',
      },
      {
        kind: 'calc',
        label: 'Findings réglementaires',
        confidence: 'high',
        details: 'Chaque finding porte un risque unitaire basé sur la sévérité et l\'urgence.',
        links: [{ label: 'Plan d\'action', href: '/action-plan' }],
      },
    ],
    method: [
      'Somme des champs risque_eur de chaque site (heuristique V1).',
      'Risque unitaire par finding = sévérité × urgence × barème réglementaire.',
      'Pondération : non conforme = 100%, à risque = 50%.',
    ],
    assumptions: [
      'Barèmes basés sur les sanctions théoriques maximales (Décret Tertiaire, BACS).',
      'Le risque réel dépend de l\'application effective des sanctions par les autorités.',
    ],
  });
}

export function evidenceKwhTotal(scopeLabel, periodLabel, kwhValue) {
  return buildEvidence({
    id: 'conso-kwh-total',
    title: `kWh total${periodLabel ? ` — ${periodLabel}` : ''}`,
    valueLabel: kwhValue,
    scopeLabel,
    periodLabel,
    sources: [
      {
        kind: 'enedis',
        label: 'Courbe de charge Enedis',
        confidence: 'high',
        details: 'Index horaires ou 15 min (selon disponibilité compteur).',
        freshness: 'Données seed HELIOS — 730 jours horaires',
        links: [{ label: 'Voir les compteurs', href: '/connectors' }],
      },
      {
        kind: 'calc',
        label: 'Agrégation PROMEOS',
        confidence: 'high',
        details: 'Somme des relevés filtrés par période et fréquence.',
      },
    ],
    method: [
      'Somme des mesures horaires (ou 15 min) sur la période sélectionnée.',
      'Filtrage par fréquence compatible (exclusion des lectures MONTHLY dans l\'agrégation horaire).',
      'Multi-site : somme des totaux par site sélectionné.',
    ],
    assumptions: [
      'Données Enedis considérées comme source de vérité (compteur certifié).',
      'En cas de trou de données, aucune interpolation — le total peut être sous-estimé.',
    ],
  });
}

export function evidenceCO2e(scopeLabel, periodLabel, co2Value) {
  return buildEvidence({
    id: 'conso-co2e',
    title: `Émissions CO2e${periodLabel ? ` — ${periodLabel}` : ''}`,
    valueLabel: co2Value,
    scopeLabel,
    periodLabel,
    sources: [
      {
        kind: 'enedis',
        label: 'Consommation kWh (Enedis)',
        confidence: 'high',
        details: 'Base de calcul : kWh total sur la période.',
      },
      {
        kind: 'calc',
        label: 'Facteur d\'émission ADEME 2024',
        confidence: 'high',
        details: 'Mix électrique France : 0,052 kgCO2e/kWh.',
        links: [{ label: 'Référentiel ADEME', href: '/kb' }],
      },
    ],
    method: [
      'CO2e = kWh total × facteur ADEME (0,052 kgCO2e/kWh).',
      'Facteur unique pour le mix électrique français moyen.',
      'Pas de distinction heure creuse / heure pleine (facteur moyen).',
    ],
    assumptions: [
      'Facteur ADEME 2024 constant sur toute la période.',
      'Ne tient pas compte de l\'autoconsommation PV éventuelle.',
    ],
  });
}
