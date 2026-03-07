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
  // ── Compteurs & sous-compteurs ──────────────────────────────────────────────
  sous_compteur: {
    term: 'Sous-compteur',
    short:
      "Compteur divisionnaire rattaché à un compteur principal. Mesure la consommation d'une zone ou d'un usage spécifique (ex : climatisation, cuisine).",
    long:
      "Un sous-compteur est un compteur secondaire installé en aval du compteur principal. Il permet de ventiler la consommation par zone (étage, local) ou par usage (CVC, éclairage, process). L'écart entre le compteur principal et la somme des sous-compteurs représente les pertes et parties communes.",
  },
  // ── Composantes de facturation ─────────────────────────────────────────────
  turpe: {
    term: 'TURPE',
    short:
      "Tarif d'Utilisation des Réseaux Publics d'Électricité. Coût d'acheminement de l'électricité via le réseau, fixé par la CRE.",
    long:
      "Le TURPE 7 (depuis fév. 2025) comprend une composante énergie (EUR/kWh, variable selon segment C5/C4/C3) et une composante gestion (EUR/mois, fixe). Les segments : C5 BT ≤36 kVA, C4 BT >36 kVA, C3 HTA. Taux chargés depuis le référentiel tarifs_reglementaires.yaml.",
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
  accise_electricite: {
    term: 'Accise électricité (TIEE)',
    short:
      "Taxe intérieure sur l'électricité (ex-CSPE/TICFE), rebaptisée TIEE depuis 2022. Taux 2025 : 22,50 EUR/MWh.",
    long:
      "L'accise sur l'électricité (TIEE) est fixée par la Loi de finances. Depuis 2025 : 0,02250 EUR/kWh. Elle s'applique sur la consommation totale (kWh). TVA 20 % applicable. Source : Loi de finances 2025 art. 92.",
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

  // ── Pricing achat ────────────────────────────────────────────────────────────
  forward_price: {
    term: 'Prix forward (CAL)',
    short:
      "Prix à terme sur le marché de gros (produit calendaire). Correspond au spot + prime de terme reflétant le risque de livraison future.",
    long:
      "Le prix forward CAL est calculé à partir du spot EPEX moyen 30 jours + une prime de terme (3 % de base + 0,3 % par mois d'horizon, cap 12 %). S'y ajoute la marge fournisseur B2B (~2,5 EUR/MWh). Convention : EUR/MWh.",
  },
  spread_fournisseur: {
    term: 'Spread fournisseur',
    short:
      "Écart fixe ajouté par le fournisseur au-dessus de l'index de marché (EPEX Spot). Couvre sa marge, ses coûts de gestion et le risque de contrepartie.",
    long:
      "En contrat indexé B2B, le spread typique est de 3 à 6 EUR/MWh selon la taille du portefeuille et la solvabilité du client. PROMEOS utilise 4 EUR/MWh par défaut.",
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

  // ── Consommation unifiée (A.1) ───────────────────────────────────────────
  conso_metered: {
    term: 'Consommation mesurée',
    short:
      "Consommation calculée à partir des relevés de compteur (télérelève ou index). Source la plus précise quand la couverture dépasse 80 %.",
    long: "Unité : kWh. Source : Compteur (MeterReading).",
  },
  conso_billed: {
    term: 'Consommation facturée',
    short:
      "Consommation déclarée sur les factures fournisseur. Utilisée en fallback quand les relevés compteur sont insuffisants.",
    long: "Unité : kWh. Source : Factures énergie (EnergyInvoice).",
  },
  reconciliation_conso: {
    term: 'Réconciliation compteur / facture',
    short:
      "Comparaison automatique entre la consommation mesurée et la consommation facturée. Un écart supérieur à 10 % déclenche une alerte.",
    long: "Formule : |metered_kwh − billed_kwh| / metered_kwh × 100. Unité : %. Source : Service unifié PROMEOS.",
  },
  reconciliation_auto: {
    term: 'Rapprochement automatique à l\'import',
    short:
      "Après chaque import de facture (CSV, PDF), PROMEOS compare automatiquement la consommation compteur et facturée. Un écart > 10 % génère une alerte de type reconciliation_mismatch.",
    long: "Déclenché automatiquement après import-csv, import-pdf et audit-all. Idempotent : pas de doublon pour la même période/site. Seuils : medium > 10 %, high > 20 %.",
  },
  data_quality_score: {
    term: 'Score qualité données',
    short:
      "Indicateur 0-100 mesurant la fiabilité des données du site selon 4 axes : complétude, fraîcheur, précision et cohérence compteur/facture.",
    long: "Formule : Complétude (35%) + Fraîcheur (25%) + Précision (25%) + Cohérence (15%). Unité : points /100. Source : Service Data Quality PROMEOS.",
  },
  freshness: {
    term: 'Fraîcheur des données',
    short:
      "Indicateur de récence des données de consommation. À jour (< 48h), Récent (2-7j), En retard (7-30j), Périmées (> 30j).",
    long: "Calculé depuis la date la plus récente entre le dernier relevé compteur et la dernière facture importée. Si > 30 jours, les KPIs sont grisés et un bandeau invite à importer des données.",
  },
  emissions_co2: {
    term: 'Émissions CO₂',
    short:
      "Émissions de gaz à effet de serre calculées à partir de la consommation et du facteur d'émission ADEME par vecteur énergétique (électricité : 0,057 kgCO₂e/kWh, gaz : 0,227 kgCO₂e/kWh).",
    long: "Formule : kWh × facteur ADEME (différencié par vecteur). Unité : kgCO₂e ou tCO₂e. Source : ADEME Base Carbone 2024.",
  },
  timeline_reglementaire: {
    term: 'Frise réglementaire',
    short:
      "Vue chronologique de toutes les échéances réglementaires applicables au portefeuille (Décret Tertiaire, BACS, APER). Chaque point indique le nombre de sites concernés et le risque financier.",
    long: "Les échéances proviennent de la configuration réglementaire (regs.yaml) croisée avec les données patrimoniales (surfaces, puissances CVC, parkings). Statuts : échue (rouge), < 12 mois (orange), à planifier (bleu).",
  },
  impact_financier: {
    term: 'Impact financier',
    short:
      "Estimation du risque financier en euros associé à chaque constat de non-conformité. Basé sur les pénalités définies réglementairement (regs.yaml) ou sur des estimations conservatrices.",
    long: "Chaque finding inclut estimated_penalty_eur (montant), penalty_source (regs.yaml ou estimation) et penalty_basis (base de calcul). Pour le Décret Tertiaire : 7 500 EUR/site (non-déclaration) ou 1 500 EUR/site (non-affichage). BACS : 7 500 EUR/site. APER : estimation ~20 EUR/m² parking, ~15 EUR/m² toiture.",
  },
  prix_marche_epex: {
    term: 'Prix marché EPEX Spot',
    short:
      "Prix de l'électricité sur le marché spot français (EPEX SPOT SE). Reflète l'offre et la demande en temps réel. Utilisé comme référence pour les contrats indexés et spot.",
    long: "L'EPEX SPOT SE est la bourse européenne de l'électricité. Le prix day-ahead France est la référence pour les contrats indexés. Unité : EUR/MWh. Seed PROMEOS basé sur les tendances observées 2024-2025 (post-crise, normalisation progressive).",
  },
};
