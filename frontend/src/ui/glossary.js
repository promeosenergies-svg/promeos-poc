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
    long: "Un sous-compteur est un compteur secondaire installé en aval du compteur principal. Il permet de ventiler la consommation par zone (étage, local) ou par usage (CVC, éclairage, process). L'écart entre le compteur principal et la somme des sous-compteurs représente les pertes et parties communes.",
  },
  // ── Composantes de facturation ─────────────────────────────────────────────
  turpe: {
    term: 'TURPE',
    short:
      "Tarif d'Utilisation des Réseaux Publics d'Électricité. Coût d'acheminement de l'électricité via le réseau, fixé par la CRE.",
    // Source : CRE délibération n°2025-78 du 23 janvier 2025. TURPE 7 en vigueur depuis 1er août 2025.
    long: 'Le TURPE 7 (depuis 1er août 2025, CRE n°2025-78) comprend une composante énergie (EUR/kWh, variable selon segment C5/C4/C3) et une composante gestion (EUR/mois, fixe). Les segments : C5 BT ≤36 kVA, C4 BT >36 kVA, C3 HTA. Taux chargés depuis le référentiel tarifs_reglementaires.yaml.',
  },
  atrd: {
    term: 'ATRD',
    short:
      'Accès des Tiers aux Réseaux de Distribution de gaz. Équivalent du TURPE pour le gaz naturel.',
  },
  accise: {
    term: 'Accise',
    short:
      "Taxe intérieure sur la consommation d'énergie (ex-TICFE/CSPE pour l'électricité, ex-TICGN pour le gaz).",
  },
  accise_electricite: {
    term: 'Accise électricité (TIEE)',
    short:
      "Taxe intérieure sur l'électricité (ex-CSPE/TICFE), rebaptisée TIEE depuis 2022. Taux 2026 : 26,58 EUR/MWh (C4 pro).",
    // Source : Code des impositions sur les biens et services, arrêté février 2026. Taux C5 ménages : 25,09 EUR/MWh.
    long: "L'accise sur l'électricité (TIEE) est fixée par la Loi de finances. Depuis février 2026 : 26,58 EUR/MWh pour les professionnels C4 (0,02658 EUR/kWh). Elle s'applique sur la consommation totale (kWh). TVA 20 % applicable. Source : LFI 2026, Code des impositions.",
  },
  cspe: {
    term: 'CSPE',
    short:
      "Contribution au Service Public de l'Électricité. Intégrée dans l'accise depuis 2022, finance les obligations de service public.",
  },
  cta: {
    term: 'CTA',
    short:
      "Contribution Tarifaire d'Acheminement. Taxe finançant les retraites des agents des industries électriques et gazières. Assiette : part fixe TURPE (gestion + soutirage).",
    long: "La CTA est calculée comme un pourcentage de la composante gestion du TURPE (part fixe). Coefficients 2026 en vigueur : 21,93 % pour l'électricité (sur part gestion), 10,11 % pour l'abonnement TURPE. Pré-février 2026, les coefficients historiques étaient 15 %/5 %. CTA gaz : formule additive (20,80 % + 4,71 % × coef_transport). La CTA est soumise à une TVA de 5,5 %. Source : Code de la sécurité sociale, arrêté tarifaire CRE, ParameterStore PROMEOS versionné par date d'effet.",
  },
  tva: {
    term: 'TVA',
    short:
      'Taxe sur la Valeur Ajoutée. CTA : 5,5 %. Abonnement et consommation : 20 % (depuis août 2025 pour les ≤36 kVA, toujours 20 % pour les professionnels).',
    long: "La TVA s'applique à 3 taux différents selon la composante : CTA à 5,5 % (taux réduit), abonnement à 20 % (depuis 1er août 2025 pour les ménages ≤36 kVA, sinon toujours 20 % pro), consommation (énergie + accise) à 20 %. Le calcul final : TTC = HT × (1 + taux applicable par composante). Source : LFI 2025, Code général des impôts art. 278-0 bis.",
  },
  car: {
    term: 'CAR',
    short:
      "Consommation Annuelle de Référence. Volume annuel de gaz consommé par un point de livraison, base de calcul de l'option tarifaire ATRD.",
    long: "La CAR conditionne l'option tarifaire ATRD applicable : T1 si < 6 MWh/an, T2 si 6–300 MWh/an, T3 si 300–5 000 MWh/an, T4 si ≥ 5 000 MWh/an. Pour T4, un découpage marginal 2 tranches s'applique (< 500 et ≥ 500 MWh/jour). TP (Tarif à Proximité) réservé aux plus gros volumes avec terme capacité distance. Source : délibération CRE n°2024-17 (ATRD7), mise à jour 2025-122 au 1/07/2025 (+6,06 %).",
  },
  tdn: {
    term: 'TDN',
    short:
      "Tarif Dynamique de Nouveaux usages. Tarif d'achat d'électricité avec signal prix variable, pensé pour les usages pilotables (VE, batteries, ballons ECS).",
    long: "Le TDN est un tarif dynamique horaire indexé sur les prix spot du marché, avec une incitation forte à consommer quand l'électricité est abondante (prix bas/négatifs). Cible : clients résidentiels équipés d'actifs pilotables et pro avec flexibilité fine. Articulation avec le mécanisme Tempo (3 couleurs) et les tarifications dynamiques en cours d'élargissement dans le cadre de la réforme HC TURPE 7 (3 phases nov 2025 → mi-2028). Source : CRE, RTE, réforme HC saisonnalisée.",
  },
  cee: {
    term: 'CEE',
    short:
      "Certificats d'Économies d'Énergie. Dispositif obligeant les fournisseurs d'énergie à financer des travaux d'efficacité énergétique chez leurs clients. P6 depuis 1/1/2026 : 1 050 TWhc/an.",
    long: "Les CEE (dispositif obligation nationale) imposent aux fournisseurs d'atteindre un volume de certificats sur la période P6 2026–2030 (1 050 TWhc/an, +50 % vs P5). Impact facture : ~0,731 €/MWh livré en 2026 (vs 0,478 en P5). Le coût est soit assumé par le fournisseur, soit répercuté au client via la composante CEE de la facture (pass-through activé sur le contrat). Nouvelles fiches 2026 : chaleur fatale, data centers, bornes VE. Source : DGEC, arrêté CEE P6, hebdo énergie 6-12 avril 2026.",
  },
  vnu: {
    term: 'VNU',
    short:
      'Versement Nucléaire Universel. Taxe redistributive sur la rente nucléaire EDF (Décret 2026-55, CRE 2026-52), successeur du cadre ARENH depuis le 01/01/2026.',
    long: "Le VNU (Versement Nucléaire Universel) est une taxe redistributive prélevée sur EDF lorsque le prix de marché dépasse les seuils CRE (78 / 110 €/MWh). Elle n'est PAS une ligne de la facture client final — c'est un transfert EDF → fournisseurs concurrents pour ré-équilibrer la rente nucléaire. Remplace le cadre ARENH (42 €/MWh × 50% quota) supprimé au 31/12/2025. Statut dormant en 2026 tant que les prix forward restent sous 78 €/MWh. PROMEOS expose le statut VNU dans hypotheses pour traçabilité auditeur. Source : Loi 2023-491 souveraineté énergétique, Décret 2026-55, CRE 2026-52.",
  },
  capacite: {
    term: 'Mécanisme de capacité',
    short:
      'Obligation RTE imposant aux fournisseurs de détenir des garanties de capacité proportionnelles à la pointe de leurs clients. Centralisation enchères PL-4/PL-1 prévue nov 2026.',
    long: "Le mécanisme de capacité assure l'adéquation offre/demande lors des pointes hiver (vague de froid, pointes du soir). Chaque fournisseur doit acheter des certificats auprès des producteurs/effaceurs pour couvrir l'obligation de ses clients. Réforme novembre 2026 : centralisation RTE (enchères PL-4 puis PL-1) remplace le système décentralisé actuel. Impact facture : ligne capacité (EUR/kW ou EUR/MWh selon contrat), en hausse attendue sur 2026–2028. Source : RTE, CRE, hebdo énergie avril 2026.",
  },
  ht: {
    term: 'HT',
    short: 'Hors Taxes. Montant avant application de la TVA.',
  },
  ttc: {
    term: 'TTC',
    short: 'Toutes Taxes Comprises. Montant final incluant toutes les taxes (accise, CTA, TVA).',
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
      'Kilowatt. Unité de puissance instantanée. La puissance souscrite détermine le dimensionnement du réseau et le coût TURPE.',
  },
  eur_kwh: {
    term: '€/kWh',
    short: "Prix unitaire de l'énergie. Permet de comparer les offres entre fournisseurs.",
  },
  kwh_m2_an: {
    term: 'kWh/m²/an',
    short:
      "Intensité énergétique. Ratio clé du Décret Tertiaire pour mesurer la performance d'un bâtiment.",
  },

  // ── Concepts PROMEOS ───────────────────────────────────────────────────────
  shadow_billing: {
    term: 'Facturation théorique',
    short:
      'Recalcul attendu de la facture à partir des données réelles (consommation, contrat, catalogue réglementaire). Permet de détecter les écarts avec le montant facturé.',
  },
  // ── APER / Solarisation ────────────────────────────────────────────────
  aper: {
    term: 'Loi APER',
    short:
      "Loi d'Accélération de la Production d'Énergies Renouvelables. Impose la solarisation des parkings extérieurs ≥ 1 500 m² et des toitures ≥ 500 m² avec des échéances échelonnées de 2026 à 2028.",
    long: "La loi APER (n° 2023-175 du 10 mars 2023) impose aux gestionnaires de parkings extérieurs de plus de 1 500 m² et aux propriétaires de toitures de plus de 500 m² d'installer des dispositifs de production d'énergie renouvelable (ombrières, panneaux solaires). Échéances : parkings > 10 000 m² au 01/07/2026, parkings 1 500–10 000 m² au 01/07/2028, toitures au 01/01/2028.",
  },
  production_pv: {
    term: 'Production photovoltaïque estimée',
    short:
      "Estimation de la production d'électricité solaire basée sur la surface disponible, la localisation du site et les données d'irradiance solaire.",
    long: "Le calcul utilise la puissance crête (surface panneaux × 180 Wc/m²), corrigée par un ratio de couverture (60 % parking, 80 % toiture) et les données d'irradiance PVGIS (European Commission) ou une estimation par zone climatique FR (H1/H2/H3). Pertes système : 14 %.",
  },
  shadow_breakdown: {
    term: 'Décomposition shadow',
    short:
      'Comparaison composante par composante entre la facture reçue et le montant recalculé par PROMEOS. Fourniture (énergie), acheminement (TURPE), taxes (accise/CTA) et TVA sont vérifiés séparément.',
    long: "Le shadow breakdown décompose l'écart total en 4 composantes : fourniture d'énergie (kWh × prix contrat), acheminement réseau (TURPE selon segment C5/C4/C3), taxes (accise + CTA), et TVA (5,5 % abo + 20 % conso). Chaque composante a un statut (conforme/attention/alerte) basé sur l'amplitude de l'écart. Source : référentiel TURPE/taxes 2025.",
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
      "Accès Régulé à l'Électricité Nucléaire Historique. Prix fixe 42 €/MWh. Dispositif terminé le 31/12/2025, remplacé par le VNU (Versement Nucléaire Universel, taxe redistributive sur EDF).",
    // Source : Loi Énergie-Climat 2019, fin ARENH confirmée LFI 2023. VNU : PPE3 2026-2035.
  },
  post_arenh: {
    term: 'Nouveau cadre marché électricité 2026',
    short:
      "Depuis le 01/01/2026, les règles de l'électricité ont changé : trois composantes impactent vos factures — coûts réseau (TURPE 7), versement nucléaire universel (VNU) en remplacement de l'ancien quota ARENH, et mécanisme de capacité RTE renforcé en novembre 2026.",
    long: "Le 01/01/2026 a marqué la fin de l'ARENH (100 TWh à 42 €/MWh disparus du marché B2B). Le nouveau cadre comporte 3 composantes que les factures intègrent désormais : (a) TURPE 7 — grille acheminement révisée 2025-2029 par la CRE ; (b) VNU — taxe redistributive sur EDF dormante tant que les prix forward restent < 78 €/MWh ; (c) Mécanisme de capacité RTE — réforme novembre 2026 avec enchères centralisées PL-4/PL-1. Voir aussi : TURPE, VNU, Mécanisme de capacité. Source : Loi 2023-491, Décret 2026-55, CRE 2026-52, RTE Règles Mécanisme Capacité.",
  },

  // ── Pricing achat ────────────────────────────────────────────────────────────
  forward_price: {
    term: 'Prix forward (CAL)',
    short:
      'Prix à terme sur le marché de gros (produit calendaire). Correspond au spot + prime de terme reflétant le risque de livraison future.',
    long: "Le prix forward CAL est calculé à partir du spot EPEX moyen 30 jours + une prime de terme (3 % de base + 0,3 % par mois d'horizon, cap 12 %). S'y ajoute la marge fournisseur B2B (~2,5 EUR/MWh). Convention : EUR/MWh.",
  },
  spread_fournisseur: {
    term: 'Spread fournisseur',
    short:
      "Écart fixe ajouté par le fournisseur au-dessus de l'index de marché (EPEX Spot). Couvre sa marge, ses coûts de gestion et le risque de contrepartie.",
    long: 'En contrat indexé B2B, le spread typique est de 3 à 6 EUR/MWh selon la taille du portefeuille et la solvabilité du client. PROMEOS utilise 4 EUR/MWh par défaut.',
  },

  // ── Score conformité (A.2) ─────────────────────────────────────────────────
  compliance_score: {
    term: 'Score conformité',
    short:
      'Score 0-100 mesurant le respect des 3 obligations réglementaires applicables : Décret Tertiaire, BACS et APER. Les CEE, qui relèvent du financement, ne sont pas inclus.',
    long: 'Formule : Moyenne pondérée (Tertiaire 45% + BACS 30% + APER 25%) − pénalité findings critiques (max −20 pts). Confiance : haute si 3/3 frameworks évalués, moyenne si 2/3, basse si ≤1.',
  },

  // ── KPIs & scoring (C.2b) ──────────────────────────────────────────────────
  risque_financier: {
    term: 'Risque financier',
    short:
      'Somme des risques financiers estimés pour les sites non conformes ou à risque. Formule : Σ(risque_eur) par site.',
  },
  worst_sites: {
    term: 'Sites critiques',
    short:
      'Sites concentrant le plus de risque ou de non-conformité. Priorisez vos actions sur ces sites en premier.',
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
      'Pourcentage de sites ayant transmis leurs données dans les délais. Un taux < 80 % signale un risque de non-conformité.',
  },
  effort_score: {
    term: "Score d'effort",
    short:
      "Indicateur synthétique mesurant l'effort restant pour atteindre la conformité : investissement, complexité, délai.",
  },
  data_confidence: {
    term: 'Confiance données',
    short:
      'Niveau de fiabilité des données utilisées pour les calculs : haute (compteur vérifié), moyenne (facture), basse (estimé).',
  },
  statut_conformite: {
    term: 'Statut conformité',
    short:
      "État réglementaire du site : conforme, à risque, non conforme, ou en cours d'évaluation.",
  },
  distribution_sites: {
    term: 'Distribution sites',
    short: "Répartition des sites par statut, risque ou performance. Vue d'ensemble du patrimoine.",
  },

  // ── Types d'anomalies ──────────────────────────────────────────────────────
  shadow_gap: {
    term: 'Écart facture',
    short:
      'Différence significative entre le montant facturé et le montant attendu recalculé par la facturation théorique.',
  },
  unit_price_high: {
    term: 'Prix unitaire élevé',
    short:
      'Le prix €/kWh de cette facture dépasse le seuil attendu pour ce type de contrat et cette période.',
  },
  duplicate_invoice: {
    term: 'Doublon facture',
    short:
      'Deux factures couvrent la même période pour le même point de livraison. Risque de double paiement.',
  },
  consumption_spike: {
    term: 'Pic de consommation',
    short:
      "Hausse brutale de la consommation par rapport à la tendance historique. Peut indiquer une fuite, un dysfonctionnement ou un changement d'usage.",
  },
  price_drift: {
    term: 'Dérive de prix',
    short: 'Évolution progressive du prix unitaire au-delà des variations contractuelles prévues.',
  },

  // ── Consommation unifiée (A.1) ───────────────────────────────────────────
  conso_metered: {
    term: 'Consommation mesurée',
    short:
      'Consommation calculée à partir des relevés de compteur (télérelève ou index). Source la plus précise quand la couverture dépasse 80 %.',
    long: 'Unité : kWh. Source : Compteur (MeterReading).',
  },
  conso_billed: {
    term: 'Consommation facturée',
    short:
      'Consommation déclarée sur les factures fournisseur. Utilisée en fallback quand les relevés compteur sont insuffisants.',
    long: 'Unité : kWh. Source : Factures énergie (EnergyInvoice).',
  },
  reconciliation_conso: {
    term: 'Réconciliation compteur / facture',
    short:
      'Comparaison automatique entre la consommation mesurée et la consommation facturée. Un écart supérieur à 10 % déclenche une alerte.',
    long: 'Formule : |metered_kwh − billed_kwh| / metered_kwh × 100. Unité : %. Source : Service unifié PROMEOS.',
  },
  reconciliation_auto: {
    term: "Rapprochement automatique à l'import",
    short:
      'Après chaque import de facture (CSV, PDF), PROMEOS compare automatiquement la consommation compteur et facturée. Un écart > 10 % génère une alerte de type reconciliation_mismatch.',
    long: 'Déclenché automatiquement après import-csv, import-pdf et audit-all. Idempotent : pas de doublon pour la même période/site. Seuils : medium > 10 %, high > 20 %.',
  },
  data_quality_score: {
    term: 'Score qualité données',
    short:
      'Indicateur 0-100 mesurant la fiabilité des données du site selon 4 axes : complétude, fraîcheur, précision et cohérence compteur/facture.',
    long: 'Formule : Complétude (35%) + Fraîcheur (25%) + Précision (25%) + Cohérence (15%). Unité : points /100. Source : Service Data Quality PROMEOS.',
  },
  freshness: {
    term: 'Fraîcheur des données',
    short:
      'Indicateur de récence des données de consommation. À jour (< 48h), Récent (2-7j), En retard (7-30j), Périmées (> 30j).',
    long: 'Calculé depuis la date la plus récente entre le dernier relevé compteur et la dernière facture importée. Si > 30 jours, les KPIs sont grisés et un bandeau invite à importer des données.',
  },
  emissions_co2: {
    term: 'Émissions CO₂',
    short:
      "Émissions de gaz à effet de serre calculées à partir de la consommation et du facteur d'émission ADEME par vecteur énergétique (électricité : 0,052 kgCO₂e/kWh, gaz : 0,227 kgCO₂e/kWh).",
    // Source : ADEME Base Empreinte V23.6 (2024). Note : 0,0569 est un tarif TURPE HPH en EUR/kWh, pas un facteur CO₂.
    long: 'Formule : kWh × facteur ADEME (différencié par vecteur). Unité : kgCO₂e ou tCO₂e. Source : ADEME Base Empreinte V23.6 (2024). Électricité mix France ACV : 0,052. Gaz naturel PCI combustion + amont : 0,227.',
  },
  timeline_reglementaire: {
    term: 'Frise réglementaire',
    short:
      'Vue chronologique de toutes les échéances réglementaires applicables au portefeuille (Décret Tertiaire, BACS, APER). Chaque point indique le nombre de sites concernés et le risque financier.',
    long: 'Les échéances proviennent de la configuration réglementaire (regs.yaml) croisée avec les données patrimoniales (surfaces, puissances CVC, parkings). Statuts : échue (rouge), < 12 mois (orange), à planifier (bleu).',
  },
  impact_financier: {
    term: 'Impact financier',
    short:
      'Estimation du risque financier en euros associé à chaque constat de non-conformité. Basé sur les pénalités définies réglementairement (regs.yaml) ou sur des estimations conservatrices.',
    long: 'Chaque finding inclut estimated_penalty_eur (montant), penalty_source (regs.yaml ou estimation) et penalty_basis (base de calcul). Pour le Décret Tertiaire : 7 500 EUR/site (non-déclaration) ou 1 500 EUR/site (non-affichage). BACS : 7 500 EUR/site. APER : estimation ~20 EUR/m² parking, ~15 EUR/m² toiture.',
  },
  prix_marche_epex: {
    term: 'Prix marché EPEX Spot',
    short:
      "Prix de l'électricité sur le marché spot français (EPEX SPOT SE). Reflète l'offre et la demande en temps réel. Utilisé comme référence pour les contrats indexés et spot.",
    long: "L'EPEX SPOT SE est la bourse européenne de l'électricité. Le prix day-ahead France est la référence pour les contrats indexés. Unité : EUR/MWh. Seed PROMEOS basé sur les tendances observées 2024-2025 (post-crise, normalisation progressive).",
  },
  import_incremental: {
    term: 'Import incrémental',
    short:
      "Mode d'import qui met à jour les sites existants au lieu de créer des doublons. Le matching se fait par SIRET (prioritaire), PRM/PCE, ou nom + code postal.",
    long: "Le mode update du pipeline d'import patrimoine compare chaque site du fichier aux sites existants. Priorité de matching : 1) SIRET exact (confiance haute), 2) PRM/PCE du compteur (confiance haute), 3) Nom + code postal (confiance moyenne). Les champs non-null du fichier écrasent les valeurs existantes. Les sites non matchés sont créés normalement.",
  },

  // ── Décret Tertiaire — termes spécifiques ────────────────────────────────
  efa: {
    term: 'EFA',
    short:
      'Entite Fonctionnelle Assujettie. Unite de base du Decret Tertiaire : un batiment ou partie de batiment de meme usage, assujetti aux obligations de reduction.',
    long: "L'EFA est definie par l'arrete du 10 avril 2020 (art. 2). Elle correspond a un perimetre homogene (meme activite, meme assujetti) au sein d'un batiment ou ensemble de batiments. C'est l'entite declaree sur OPERAT.",
  },
  iiu: {
    term: 'IIU',
    short:
      "Indicateur d'Intensite d'Usage. Facteur de correction de l'objectif DT en fonction de l'usage reel (occupants, horaires, intensite d'activite).",
    long: "L'IIU est defini par l'arrete du 10 avril 2020 (annexe II). Il permet d'ajuster les objectifs de reduction si l'usage du batiment a change depuis l'annee de reference. Exemple : un hotel qui augmente son nombre de chambres exploitees.",
  },
  dju: {
    term: 'DJU',
    short:
      'Degres-Jours Unifies. Indicateur climatique pour corriger les consommations des variations meteo. Base 18 C, methode COSTIC.',
    long: "Les DJU mesurent l'ecart entre la temperature exterieure et 18 C sur une periode. Plus les DJU sont eleves, plus le besoin de chauffage est important. La normalisation DJU permet de comparer les consommations entre annees a climat equivalent.",
  },
  crefabs: {
    term: 'CRefAbs',
    short:
      "Consommation de Reference Absolue. Seuil maximal par categorie d'activite. Si le batiment est deja en-dessous, il est conforme sans reduction supplementaire.",
    long: "Les valeurs absolues (Cabs) sont definies par l'arrete du 10 avril 2020 modifie (annexe VI). Elles varient par categorie fonctionnelle et zone climatique (H1a a H3). C'est une alternative a la trajectoire relative (-40%/-50%/-60%).",
  },
  modulation_dt: {
    term: 'Modulation',
    short:
      "Dossier de modulation DT. Demande d'ajustement d'objectif quand celui-ci est techniquement ou economiquement impossible. Depot OPERAT avant le 30/09/2026.",
    long: "La modulation est prevue par le decret n 2019-771 (art. 3). L'assujetti doit justifier de contraintes techniques, architecturales ou de disproportion economique, et documenter les actions envisagees avec leur TRI.",
  },
  mutualisation_dt: {
    term: 'Mutualisation',
    short:
      'Compensation inter-sites DT. Un site performant compense un site en retard au sein du meme portefeuille. Fonctionnalite a venir dans OPERAT.',
    long: "La mutualisation est prevue par le decret n 2019-771 (art. 3). Elle permet d'evaluer la conformite au niveau du portefeuille plutot que site par site, reduisant potentiellement les penalites.",
  },
  operat: {
    term: 'OPERAT',
    short:
      'Observatoire de la Performance Energetique, de la Renovation et des Actions du Tertiaire. Plateforme ADEME pour les declarations DT.',
    long: 'OPERAT (operat.ademe.fr) est la plateforme officielle ou les assujettis au Decret Tertiaire declarent leurs consommations, choisissent leur annee de reference, et suivent leur trajectoire de conformite.',
  },
  tri_investissement: {
    term: 'TRI',
    short:
      "Temps de Retour sur Investissement. Duree necessaire pour que les economies d'energie remboursent le cout d'un investissement. TRI = cout / economie annuelle.",
    long: "Le TRI est un critere essentiel du dossier de modulation DT et de l'exemption BACS. Un TRI > 10 ans (BACS) ou disproportionne (DT) peut justifier un ajustement d'objectif. Norme NF EN 15459.",
  },

  // ── Drivers North-Star CX (Sprint CX 3) ─────────────────────────────────
  t2v: {
    term: 'T2V',
    short:
      "Time-to-Value : délai entre la création d'un compte utilisateur et sa 1ʳᵉ action validée. Cible <7j (vert), 7–14j (amber), >14j (rouge).",
    long: "Le T2V mesure la rapidité avec laquelle un nouvel utilisateur atteint un 1ᵉʳ résultat tangible (une action PROMEOS passée au statut DONE). Signal : event CX_ACTION_FROM_INSIGHT. Rapporté en p50/p90/p95 jours. Un user sans action validée n'est pas dans l'échantillon.",
  },
  iar: {
    term: 'IAR',
    short:
      "Insight-to-Action Rate : ratio entre actions validées et insights consultés sur la période. Un IAR supérieur à 1.0 (capped) signale qu'un insight a généré plusieurs actions (légitime).",
    long: "IAR = actions_validated / insights_consulted sur la fenêtre. Numérateur CX_ACTION_FROM_INSIGHT, dénominateur CX_INSIGHT_CONSULTED. Le ratio est cappé à 1.0 pour une lecture en pourcentage ; iar_raw > 1.0 quand un même insight produit N actions. is_capped signale au front d'afficher une nuance.",
  },
  wau_mau: {
    term: 'WAU/MAU',
    short:
      'Stickiness ratio : WAU (users actifs 7j) / MAU (users actifs 30j). Seuils : ≥40% excellent, 30–40% bon, 20–30% à travailler, <20% faible.',
    long: "Le ratio WAU/MAU mesure la fidélité d'usage : plus il est haut, plus les utilisateurs reviennent fréquemment. Référence marché B2B SaaS : 20-30% normal, 40%+ excellent. Source : events CX_* rattachés à un user_id sur les fenêtres 7j et 30j.",
  },
};
