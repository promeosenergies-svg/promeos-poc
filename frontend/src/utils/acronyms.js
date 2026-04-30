/**
 * acronyms.js — Glossaire acronymes énergie/réglementaire (Étape 2.bis · 29/04/2026).
 *
 * Convergence audits 5 personas (Marie DAF · Jean-Marc CFO · Sophie VC ·
 * /frontend-design · /simplify) : les pages Cockpit dual exposent en clair
 * BACS / TURPE / ARENH / VNU / CBAM / CEE / OPERAT / EPEX / DT / NEBCO /
 * AOFD / GTB sans tooltip. Marie 47 ans DAF non-sachante ne peut pas
 * présenter en CODIR sans glossaire ; Sophie VC voit "perte de confiance
 * immédiate" ; Jean-Marc CFO veut formules sourcées.
 *
 * Doctrine §6.4 (acronyme → récit) appliquée frontend en attendant le
 * dictionnaire backend canonique `backend/doctrine/acronyms.py` Phase 1.8.
 *
 * Convention : chaque entrée fournit
 *   - long  : forme développée (titre tooltip)
 *   - meaning : récit court non-sachant (1 phrase, jamais > 120 chars)
 *   - source : référence vérifiable (article loi, mécanisme, organisme)
 */

export const ACRONYM_GLOSSARY = Object.freeze({
  ARENH: {
    long: "Accès Régulé à l'Électricité Nucléaire Historique",
    meaning:
      "Ancien tarif réglementé d'achat d'électricité nucléaire EDF — fin du dispositif au 31/12/2025.",
    source: 'Loi NOME 2010 · fin 31/12/2025',
  },
  VNU: {
    long: 'Versement Nucléaire Universel',
    meaning:
      'Mécanisme post-ARENH qui répartit le bénéfice du parc nucléaire EDF — activation prévue 2027.',
    source: 'Loi de programmation énergie 2024',
  },
  TURPE: {
    long: "Tarif d'Utilisation des Réseaux Publics d'Électricité",
    meaning:
      "Tarif d'acheminement réseau payé au gestionnaire (Enedis) — composante incompressible de la facture.",
    source: 'CRE délibération TURPE 7 (2025-2029)',
  },
  CTA: {
    long: "Contribution Tarifaire d'Acheminement",
    meaning:
      'Taxe affectée au financement du régime spécial des retraites des industries électriques et gazières.',
    source: 'Code des impositions sur les biens et services',
  },
  CSPE: {
    long: "Contribution au Service Public de l'Électricité",
    meaning:
      'Accise électricité finançant les charges de service public — remplacée par TICFE depuis 2016.',
    source: 'Code des impositions',
  },
  CEE: {
    long: "Certificat d'Économie d'Énergie",
    meaning:
      "Mécanisme obligeant les fournisseurs d'énergie à financer des travaux d'économies — référentiel BAT-TH-XXX.",
    source: "Code de l'Énergie L221-1",
  },
  DT: {
    long: 'Décret Tertiaire',
    meaning:
      'Obligation de réduction de consommation énergétique sur tertiaire >1000 m² : −40 %/2030, −50 %/2040, −60 %/2050.',
    source: 'Décret n°2019-771 art. 9',
  },
  BACS: {
    long: 'Building Automation and Control Systems',
    meaning:
      'Décret obligeant à installer un pilotage CVC automatisé classe A/B sur tertiaire >290 kW (échéance 1ᵉʳ janv 2027).',
    source: 'Décret n°2020-887',
  },
  GTB: {
    long: 'Gestion Technique du Bâtiment',
    meaning:
      "Système de pilotage CVC / éclairage / production d'eau chaude avec automate centralisé (classe A = optimal, B = standard).",
    source: 'Norme NF EN 15232',
  },
  APER: {
    long: "Accélération de la production d'Énergies Renouvelables",
    meaning:
      'Loi qui impose le solaire sur les parkings extérieurs >1 500 m² — échéance 1ᵉʳ juillet 2028.',
    source: 'Loi n°2023-175 art. 40',
  },
  OPERAT: {
    long: "OPérateur de la Réduction d'Énergie sur les bâtiments du tertiaire",
    meaning:
      'Plateforme ADEME où les assujettis Décret Tertiaire déclarent annuellement leur consommation (deadline 30 sept).',
    source: 'Décret n°2019-771 art. 6',
  },
  CBAM: {
    long: 'Carbon Border Adjustment Mechanism',
    meaning:
      'Taxe carbone aux frontières UE sur acier/ciment/aluminium/électricité — secteur tertiaire hors périmètre.',
    source: 'Règlement UE 2023/956',
  },
  EPEX: {
    long: 'European Power Exchange',
    meaning:
      "Bourse spot européenne de l'électricité — référence prix horaires day-ahead (J−1 publié 12h45).",
    source: 'EPEX SPOT SE',
  },
  NEBCO: {
    long: 'Nouveau cadre Effacement Bilatéral Compensé',
    meaning:
      "Mécanisme RTE qui rémunère l'effacement de consommation industrielle — seuil 100 kW par bloc.",
    source: 'RTE règles SI 2024',
  },
  AOFD: {
    long: "Appels d'Offres Effacement Diffus",
    meaning:
      "Concours RTE pour l'effacement résidentiel/tertiaire diffus — capacité agrégée par opérateur.",
    source: 'RTE / Ministère',
  },
  CDC: {
    long: 'Courbe De Charge',
    meaning:
      "Mesure de puissance pas par pas (30 min) — base du shadow billing et de l'analyse pic.",
    source: 'Enedis SF1-SF4 (R6X)',
  },
  EMS: {
    long: 'Energy Management System',
    meaning:
      'Système de monitoring temps réel des consommations énergétiques (compteurs, sondes, GTB connectée).',
    source: 'ISO 50001',
  },
  DJU: {
    long: 'Degré Jour Unifié',
    meaning:
      'Indicateur climatique qui mesure les besoins de chauffage/climatisation — permet de normaliser la conso vs météo.',
    source: 'Méthode COSTIC',
  },
  TDN: {
    long: 'Tarif De Nuit',
    meaning:
      "Tarif d'achat d'électricité avec heures pleines / heures creuses (HP/HC) selon plages horaires Enedis.",
    source: 'CRE TURPE 7',
  },
  ETS2: {
    long: 'Emissions Trading System 2',
    meaning: 'Marché carbone UE étendu au bâtiment et au transport routier — application 2027.',
    source: 'Directive UE 2023/959',
  },
  // Phase 15.C — entrées CFO ajoutées pour passer les tooltips title="" non
  // accessibles vers AcronymTooltip (tabIndex + role=button + aria-label).
  CAPEX: {
    long: 'Capital Expenditure',
    meaning:
      'Investissement initial estimé pour engager un levier (équipement + installation + mise en service). Hors charges récurrentes (OpEx).',
    source: 'Référentiels CEE BAT-TH-* + benchmarks ADEME tertiaire',
  },
  PAYBACK: {
    long: 'Délai de retour sur investissement',
    meaning:
      'Durée (en mois) avant que les économies cumulées remboursent le CapEx. Formule simple : CapEx ÷ Économies annuelles. N’intègre pas la pénalité légale évitée par défaut.',
    source: 'Méthodologie indicateur PROMEOS',
  },
  // Phase 17.bis.A — 18 acronymes manquants (audit jargon : 14 routes/16 sans
  // tooltip, hors-glossaire critique). Cible : zéro acronyme métier exposé brut.
  CVC: {
    long: 'Chauffage Ventilation Climatisation',
    meaning:
      "Système thermique d'un bâtiment : production chaud/froid + traitement d'air. Premier poste de consommation tertiaire (~50 % conso annuelle bureau).",
    source: 'Doctrine bâtiment tertiaire ADEME',
  },
  CRE: {
    long: "Commission de Régulation de l'Énergie",
    meaning:
      'Autorité administrative indépendante française (loi 2000-108). Régule TURPE, ATRD, ARENH, capacité, NEBCO, prix repère gaz et électricité.',
    source: 'cre.fr',
  },
  RTE: {
    long: "Réseau de Transport d'Électricité",
    meaning:
      'Gestionnaire du réseau haute tension français. Opère le mécanisme capacité, NEBCO, AOFD, équilibrage.',
    source: 'rte-france.com',
  },
  ATRD: {
    long: 'Accès des Tiers au Réseau de Distribution',
    meaning:
      "Tarif d'acheminement gaz (équivalent TURPE pour l'électricité). Versions ATRD7 GRDF en vigueur depuis 01/07/2026.",
    source: 'CRE 2026-83 ATRD7 GRDF',
  },
  ATRT: {
    long: 'Accès des Tiers au Réseau de Transport',
    meaning:
      "Tarif acheminement gaz haute pression GRTgaz/Teréga. Couvre l'amont du réseau de distribution.",
    source: 'CRE délibérations ATRT',
  },
  ISO: {
    long: "Norme ISO 50001 (Système de Management de l'Énergie)",
    meaning:
      "Norme internationale de management de l'énergie. Certification SMÉ vaut audit énergétique réglementaire — exonère de l'audit obligatoire ETI.",
    source: 'ISO 50001:2018',
  },
  COSTIC: {
    long: 'Comité Scientifique et Technique des Industries Climatiques',
    meaning:
      'Référence française pour le calcul des Degrés Jours Unifiés (DJU). Méthode COSTIC NF EN 16247-2 = base normalisation conso vs météo.',
    source: 'costic.fr / NF EN 16247-2',
  },
  EFA: {
    long: 'Entité Fonctionnelle Assujettie',
    meaning:
      'Unité de déclaration OPERAT (un site ou groupe de bâtiments cohérents > 1 000 m² tertiaire). Doit déclarer conso annuelle + atteindre les jalons -40/-50/-60 %.',
    source: 'Décret Tertiaire 2019-771 art. R131-39',
  },
  CSRD: {
    long: 'Corporate Sustainability Reporting Directive',
    meaning:
      'Directive UE 2022/2464 — reporting durabilité obligatoire grands groupes (>250 ETP, >40M€ CA, >20M€ bilan). Premier exercice 2024.',
    source: 'Directive UE 2022/2464 + Omnibus 2025',
  },
  DPE: {
    long: 'Diagnostic de Performance Énergétique',
    meaning:
      "Étiquette énergie/climat A→G d'un bâtiment, obligatoire location/vente. Pour le tertiaire, méthode 3CL ou conventionnelle CSTB.",
    source: 'CCH art. L126-26 + Décret 2021-872',
  },
  SME: {
    long: "Système de Management de l'Énergie",
    meaning:
      "Démarche ISO 50001 — plan d'action énergétique pluriannuel + revue de direction + amélioration continue. Vaut audit énergétique réglementaire ETI.",
    source: 'ISO 50001 + Code Énergie L233-1',
  },
  GTC: {
    long: 'Gestion Technique Centralisée',
    meaning:
      'Système de pilotage centralisé multi-équipements (CVC + éclairage + IT). Variante de la GTB — Décret BACS exige une classe A ou B.',
    source: 'Décret BACS 2020-887',
  },
  COFRAC: {
    long: "Comité Français d'Accréditation",
    meaning:
      "Organisme officiel d'accréditation des auditeurs énergétiques en France. Tout audit réglementaire ETI doit être réalisé par un auditeur accrédité COFRAC.",
    source: 'cofrac.fr',
  },
  IPE: {
    long: 'Indicateur de Performance Énergétique',
    meaning:
      "Ratio énergie/activité d'un site (ex kWh/m²/an, kWh/jour ouvré, kWh/repas servi). ISO 50001 demande au moins 1 IPE de référence.",
    source: 'ISO 50001 § 6.3',
  },
  ADEME: {
    long: 'Agence de la transition écologique',
    meaning:
      "Établissement public référence transition énergétique. Publie Base Empreinte (CO₂), benchmarks tertiaires OID, méthodes d'audit, fiches CEE.",
    source: 'ademe.fr + Base Empreinte V23.6',
  },
  PRM: {
    long: 'Point de Référence Mesure',
    meaning:
      "Identifiant unique 14 chiffres d'un point de livraison électrique Enedis. Donne accès aux relevés CDC 30 minutes via SGE.",
    source: 'Enedis SGE',
  },
  PCE: {
    long: "Point de Comptage et d'Estimation",
    meaning:
      "Identifiant unique 14 chiffres d'un point de livraison gaz GRDF. Donne accès aux relevés MMR via portail ADICT.",
    source: 'GRDF ADICT',
  },
  OPQIBI: {
    long: "Office Professionnel de Qualification dans l'Ingénierie Bâtiment et Infrastructure",
    meaning:
      "Organisme de qualification des bureaux d'études énergétiques. Qualification OPQIBI 1905 = audit énergétique réglementaire ETI.",
    source: 'opqibi.com',
  },
  // Phase 17.quater — entrées complémentaires (pages billing / achat / APER).
  TVA: {
    long: 'Taxe sur la Valeur Ajoutée',
    meaning:
      'Taxe française 20 % sur tous les composants HT de la facture énergie depuis le 01/08/2025. Avant : taux réduits 5,5 %/20 % selon la composante.',
    source: 'CGI art. 278 + LFI 2025',
  },
  GRDF: {
    long: 'Gaz Réseau Distribution France',
    meaning:
      'Gestionnaire du réseau de distribution gaz français (filiale Engie). Opère ATRD7, MMR, portail ADICT pour les relevés PCE.',
    source: 'grdf.fr',
  },
  HTA: {
    long: 'Haute Tension A',
    meaning:
      'Niveau de tension entre 1 kV et 50 kV (poste de livraison entreprise > 250 kVA). Tarif TURPE 7 dédié, plus avantageux que BT pour gros consommateurs.',
    source: 'CRE TURPE 7 §4',
  },
  HTB: {
    long: 'Haute Tension B',
    meaning:
      'Niveau de tension > 50 kV (transport RTE). Site directement raccordé au réseau de transport — TURPE 7 HTB1/HTB2/HTB3.',
    source: 'RTE / CRE TURPE 7',
  },
  ENR: {
    long: 'Énergies Renouvelables',
    meaning:
      "Sources d'énergie renouvelables : solaire, éolien, hydraulique, géothermie, biomasse. Couverture obligatoire APER >50 % d'ici 2028.",
    source: 'Loi APER 2023-175 + Code Énergie',
  },
});

/** Retourne le tooltip text à mettre dans `title=`/`aria-label`. */
export function acronymTooltip(key) {
  const entry = ACRONYM_GLOSSARY[key?.toUpperCase()];
  if (!entry) return null;
  return `${entry.long} — ${entry.meaning} · Source : ${entry.source}`;
}

/** Boolean : un terme est-il dans le glossaire ? */
export function isKnownAcronym(key) {
  return Object.prototype.hasOwnProperty.call(ACRONYM_GLOSSARY, key?.toUpperCase());
}
