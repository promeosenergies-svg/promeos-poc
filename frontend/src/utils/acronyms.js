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
