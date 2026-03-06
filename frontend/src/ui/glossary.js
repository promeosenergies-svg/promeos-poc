/**
 * PROMEOS — Glossaire énergie & facturation
 * Définitions centralisées pour le composant <Explain>.
 *
 * Convention : GLOSSARY[clé] = { term, short, long? }
 *   - term  : terme affiché (label FR)
 *   - short : définition courte (1-2 phrases, tooltip)
 *   - long  : explication détaillée optionnelle (panel/drawer)
 */

export const GLOSSARY = {
  // ── Composantes de facturation ─────────────────────────────────────────────
  turpe: {
    term: 'TURPE',
    short:
      "Tarif d'Utilisation des Réseaux Publics d'Électricité. Coût d'acheminement de l'électricité via le réseau, fixé par la CRE.",
  },
  atrd: {
    term: 'ATRD',
    short:
      "Accès des Tiers aux Réseaux de Distribution de gaz. Équivalent du TURPE pour le gaz naturel.",
  },
  accise: {
    term: 'Accise',
    short:
      "Taxe intérieure sur la consommation d'énergie (ex-TICFE/CSPE pour l'électricité, ex-TICGN pour le gaz).",
  },
  cspe: {
    term: 'CSPE',
    short:
      "Contribution au Service Public de l'Électricité. Intégrée dans l'accise depuis 2022, finance les obligations de service public.",
  },
  cta: {
    term: 'CTA',
    short:
      "Contribution Tarifaire d'Acheminement. Taxe finançant les retraites des agents des industries électriques et gazières.",
  },
  tva: {
    term: 'TVA',
    short:
      "Taxe sur la Valeur Ajoutée. Appliquée à 5,5 % sur l'abonnement et la CTA, et 20 % sur la consommation et les taxes.",
  },
  ht: {
    term: 'HT',
    short:
      'Hors Taxes. Montant avant application de la TVA.',
  },
  ttc: {
    term: 'TTC',
    short:
      'Toutes Taxes Comprises. Montant final incluant toutes les taxes (accise, CTA, TVA).',
  },

  // ── Unités & métriques ─────────────────────────────────────────────────────
  kwh: {
    term: 'kWh',
    short:
      "Kilowattheure. Unité de mesure d'énergie consommée. 1 kWh = énergie consommée par un appareil de 1 000 W pendant 1 heure.",
  },
  mwh: {
    term: 'MWh',
    short:
      'Mégawattheure = 1 000 kWh. Unité courante pour les gros consommateurs et les prix de marché.',
  },
  kw: {
    term: 'kW',
    short:
      "Kilowatt. Unité de puissance instantanée. La puissance souscrite détermine le dimensionnement du réseau et le coût TURPE.",
  },
  eur_kwh: {
    term: '€/kWh',
    short:
      "Prix unitaire de l'énergie. Permet de comparer les offres entre fournisseurs.",
  },
  kwh_m2_an: {
    term: 'kWh/m²/an',
    short:
      "Intensité énergétique. Ratio clé du Décret Tertiaire pour mesurer la performance d'un bâtiment.",
  },

  // ── Concepts PROMEOS ───────────────────────────────────────────────────────
  shadow_billing: {
    term: 'Shadow billing',
    short:
      "Recalcul attendu de la facture à partir des données réelles (consommation, contrat, catalogue réglementaire). Permet de détecter les écarts avec le montant facturé.",
  },
  anomalie: {
    term: 'Anomalie',
    short:
      "Signal détecté automatiquement par le moteur d'audit : écart facture, doublon, prix hors norme, période manquante, etc.",
  },
  insight: {
    term: 'Insight',
    short:
      "Recommandation actionnable générée par PROMEOS à partir d'une ou plusieurs anomalies. Chaque insight a un impact estimé et un niveau de confiance.",
  },
  confiance: {
    term: 'Confiance',
    short:
      "Niveau de fiabilité d'un calcul ou d'une recommandation. Dépend de la complétude des données (contrat, consommation, lignes de facture).",
  },
  patrimoine: {
    term: 'Patrimoine',
    short:
      "Ensemble des sites et bâtiments gérés par l'organisation. Base du périmètre d'analyse PROMEOS.",
  },

  // ── Réglementaire ──────────────────────────────────────────────────────────
  decret_tertiaire: {
    term: 'Décret Tertiaire',
    short:
      "Obligation réglementaire de réduire la consommation énergétique des bâtiments tertiaires de -40 % d'ici 2030 (vs. année de référence).",
  },
  decret_bacs: {
    term: 'Décret BACS',
    short:
      "Building Automation & Control Systems. Obligation d'équiper les bâtiments tertiaires de systèmes d'automatisation et de contrôle d'ici 2025.",
  },
  cre: {
    term: 'CRE',
    short:
      "Commission de Régulation de l'Énergie. Autorité indépendante fixant les tarifs réglementés (TURPE, ATRD).",
  },
  arenh: {
    term: 'ARENH',
    short:
      "Accès Régulé à l'Électricité Nucléaire Historique. Mécanisme permettant aux fournisseurs alternatifs d'acheter de l'électricité nucléaire à prix fixe (42 €/MWh).",
  },

  // ── Score conformité (A.2) ─────────────────────────────────────────────────
  compliance_score: {
    term: 'Score conformité',
    short:
      "Score 0-100 mesurant le respect des 3 obligations réglementaires applicables : Décret Tertiaire, BACS et APER. Les CEE, qui relèvent du financement, ne sont pas inclus.",
    long:
      "Formule : Moyenne pondérée (Tertiaire 45% + BACS 30% + APER 25%) − pénalité findings critiques (max −20 pts). Confiance : haute si 3/3 frameworks évalués, moyenne si 2/3, basse si ≤1.",
  },

  // ── KPIs & scoring (C.2b) ──────────────────────────────────────────────────
  risque_financier: {
    term: 'Risque financier',
    short:
      "Somme des risques financiers estimés pour les sites non conformes ou à risque. Formule : Σ(risque_eur) par site.",
  },
  worst_sites: {
    term: 'Sites critiques',
    short:
      "Sites concentrant le plus de risque ou de non-conformité. Priorisez vos actions sur ces sites en premier.",
  },
  off_hours_ratio: {
    term: 'Ratio hors horaires',
    short:
      "Part de la consommation électrique en dehors des heures d'occupation (nuit, week-end). Formule : kWh hors-horaires / kWh total.",
  },
  gaspillage_estime: {
    term: 'Gaspillage estimé',
    short:
      "Coût annuel estimé de la consommation hors horaires d'occupation. Formule : kWh hors-horaires × prix moyen €/kWh.",
  },
  ths_adoption: {
    term: 'Adoption THS',
    short:
      "Taux d'adoption des Tarifs Heures Supplémentaires ou tarifs à pointe. Mesure le pourcentage de sites bénéficiant d'un tarif optimisé.",
  },
  severite: {
    term: 'Sévérité',
    short:
      "Niveau de criticité d'une anomalie ou d'un finding : critique, élevé, moyen, faible. Détermine la priorité de traitement.",
  },
  finding: {
    term: 'Finding',
    short:
      "Constat issu d'un audit réglementaire ou technique. Chaque finding a une sévérité et une recommandation associée.",
  },
  report_pct: {
    term: 'Taux de reporting',
    short:
      "Pourcentage de sites ayant transmis leurs données dans les délais. Un taux < 80 % signale un risque de non-conformité.",
  },
  effort_score: {
    term: "Score d'effort",
    short:
      "Indicateur synthétique mesurant l'effort restant pour atteindre la conformité : investissement, complexité, délai.",
  },
  data_confidence: {
    term: 'Confiance données',
    short:
      "Niveau de fiabilité des données utilisées pour les calculs : haute (compteur vérifié), moyenne (facture), basse (estimé).",
  },
  statut_conformite: {
    term: 'Statut conformité',
    short:
      "État réglementaire du site : conforme, à risque, non conforme, ou en cours d'évaluation.",
  },
  distribution_sites: {
    term: 'Distribution sites',
    short:
      "Répartition des sites par statut, risque ou performance. Vue d'ensemble du patrimoine.",
  },

  // ── Types d'anomalies ──────────────────────────────────────────────────────
  shadow_gap: {
    term: 'Écart facture',
    short:
      "Différence significative entre le montant facturé et le montant attendu recalculé par le shadow billing.",
  },
  unit_price_high: {
    term: 'Prix unitaire élevé',
    short:
      "Le prix €/kWh de cette facture dépasse le seuil attendu pour ce type de contrat et cette période.",
  },
  duplicate_invoice: {
    term: 'Doublon facture',
    short:
      "Deux factures couvrent la même période pour le même point de livraison. Risque de double paiement.",
  },
  consumption_spike: {
    term: 'Pic de consommation',
    short:
      "Hausse brutale de la consommation par rapport à la tendance historique. Peut indiquer une fuite, un dysfonctionnement ou un changement d'usage.",
  },
  price_drift: {
    term: 'Dérive de prix',
    short:
      "Évolution progressive du prix unitaire au-delà des variations contractuelles prévues.",
  },
};
