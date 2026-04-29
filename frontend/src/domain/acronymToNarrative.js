/**
 * acronymToNarrative — substitution narrative inline des acronymes énergétiques.
 *
 * Phase 1.1 du sprint refonte cockpit dual sol2 (29/04/2026). Couvre les
 * acronymes utilisés dans les 2 maquettes cibles (`docs/maquettes/cockpit-sol2/
 * cockpit-pilotage-briefing-jour.html` + `cockpit-synthese-strategique.html`)
 * et plus largement le périmètre Cockpit/Conformité/Bill-Intel/Achat.
 *
 * Doctrine PROMEOS Sol §5 grammaire éditoriale + §6.3 anti-pattern « acronyme
 * brut en titre » + §430 critère de transformation réussie : « lire la phrase
 * principale d'une page → un non-sachant la comprend-il sans glossaire externe ? ».
 *
 * Différent de `domain/glossary.js` (tooltip 1-clic via `<SolAcronym>`) :
 *   - GLOSSARY → couple acronyme + tooltip pour CORPS de texte (densité préservée)
 *   - ACRONYM_TO_NARRATIVE → SUBSTITUTION inline pour TITRES H1/H2 et intros
 *     narratives (l'acronyme disparaît au profit du récit)
 *
 * Cas d'usage canonique Phase 1+ :
 *   <SolBriefingHead title={`Trajectoire ${narrativeFor('DT')}`} />
 *   → "Trajectoire le décret tertiaire" (à composer grammaticalement par le
 *      composant amont — ce dico fournit la brique narrative, pas la phrase).
 *
 * Audit Marie DAF (28/04/2026) : « Sur Conformité, je relis 2 fois "BACS/
 * APER/Décret Tertiaire" sans gloss, je décroche dès la 3ᵉ ligne ». Ce dico
 * remplit la promesse §5 « non-sachants comprennent sans apprendre les
 * acronymes avant d'utiliser le produit ».
 */

export const ACRONYM_TO_NARRATIVE = Object.freeze({
  // ── Réglementation tertiaire ────────────────────────────────────
  DT: {
    short: 'le décret tertiaire',
    long: "le décret tertiaire (objectif -40 % d'énergie d'ici 2030)",
  },
  BACS: {
    short: 'le décret BACS',
    long: "le décret BACS d'automatisation des bâtiments",
  },
  GTB: {
    short: 'la gestion technique du bâtiment',
    long: 'la gestion technique chauffage/clim/éclairage automatisée',
  },
  APER: {
    short: 'la loi APER',
    long: 'la loi APER de solarisation parkings et toitures',
  },
  OPERAT: {
    short: 'la plateforme OPERAT',
    long: 'la plateforme ADEME de déclaration tertiaire (OPERAT)',
  },

  // ── Tarifs réseaux ──────────────────────────────────────────────
  TURPE: {
    short: "le tarif d'acheminement",
    long: "le tarif d'acheminement TURPE facturé Enedis",
  },
  CTA: {
    short: 'la contribution tarifaire',
    long: "la contribution tarifaire d'acheminement (retraites IEG)",
  },
  ATRD: {
    short: "l'acheminement gaz",
    long: "le tarif d'acheminement gaz (ATRD) facturé GRDF",
  },

  // ── Marché électricité ──────────────────────────────────────────
  ARENH: {
    short: 'le quota nucléaire ARENH',
    long: 'le quota nucléaire historique ARENH (terminé 31/12/2025)',
  },
  VNU: {
    short: 'le versement nucléaire',
    long: 'le versement nucléaire universel (taxe redistributive sur EDF)',
  },
  EPEX: {
    short: 'le prix marché spot',
    long: 'le prix de marché spot EPEX (référence horaire J-1)',
  },
  CEE: {
    short: "les certificats d'économies d'énergie",
    long: "les certificats d'économies d'énergie (obligation fournisseurs P6)",
  },
  NEBCO: {
    short: "l'effacement industriel",
    long: "l'effacement industriel rémunéré par RTE (mécanisme NEBCO)",
  },
  AOFD: {
    short: "l'effacement contractualisé",
    long: "l'effacement contractualisé annuel RTE (AOFD)",
  },

  // ── Conformité européenne ───────────────────────────────────────
  CBAM: {
    short: 'la taxe carbone aux frontières',
    long: 'la taxe carbone européenne aux frontières (CBAM, plein 2034)',
  },
  CSRD: {
    short: 'le reporting extra-financier',
    long: 'le reporting extra-financier européen (CSRD post-Omnibus)',
  },
  ETS2: {
    short: 'le marché carbone bâtiments',
    long: 'le marché carbone européen bâtiments-transports (ETS2 dès 2028)',
  },

  // ── Connecteurs réseau ──────────────────────────────────────────
  RTE: {
    short: 'le gestionnaire de transport',
    long: 'le gestionnaire du réseau de transport électrique (RTE)',
  },
  SGE: {
    short: 'le portail Enedis SGE',
    long: 'le portail tiers Enedis (Système de Gestion des Échanges)',
  },
  GRDF: {
    short: 'le distributeur gaz GRDF',
    long: 'le gestionnaire du réseau de distribution gaz (GRDF)',
  },
  ENEDIS: {
    short: 'le distributeur électrique',
    long: 'le gestionnaire du réseau de distribution électrique (Enedis)',
  },

  // ── Indicateurs technique ───────────────────────────────────────
  CDC: {
    short: 'la courbe de charge',
    long: 'la courbe de charge demi-horaire (relevés Enedis J+1)',
  },
  DJU: {
    short: 'les degrés-jours',
    long: 'les degrés-jours unifiés (référence COSTIC météo)',
  },
  EMS: {
    short: 'le pilotage énergie',
    long: 'le système de pilotage énergétique (Energy Management System)',
  },
  HP: {
    short: 'les heures pleines',
    long: 'les heures pleines (créneau tarif normal)',
  },
  HC: {
    short: 'les heures creuses',
    long: 'les heures creuses (créneau tarif réduit)',
  },

  // ── Fiscalité ──────────────────────────────────────────────────
  TVA: {
    short: 'la TVA',
    long: 'la taxe sur la valeur ajoutée',
  },
});

/**
 * Retourne la forme narrative substituable d'un acronyme.
 *
 * - mode 'short' (défaut) : tournure courte pour titres H1/H2 (≤ 50 chars)
 * - mode 'long' : tournure étendue pour 1ʳᵉ mention en intro narrative (≤ 90 chars)
 *
 * Si l'acronyme est inconnu → retourne le code brut (no-op safe pour
 * éviter de masquer un acronyme manquant — un audit visuel le verra).
 *
 * @param {string} code - Code acronyme (ex: 'DT', 'BACS', 'TURPE')
 * @param {{ mode?: 'short' | 'long' }} options - Mode de substitution
 * @returns {string} Forme narrative ou code brut si inconnu
 */
export function narrativeFor(code, { mode = 'short' } = {}) {
  if (!code) return '';
  const entry = ACRONYM_TO_NARRATIVE[code] || ACRONYM_TO_NARRATIVE[code.toUpperCase()];
  if (!entry) return code;
  return entry[mode] || entry.short || code;
}

/**
 * Liste des acronymes ayant une forme narrative — utile pour tests source-guard
 * et audit doctrinal Vague Q (audit acronymes maquettes vs dico).
 *
 * @returns {string[]} Codes acronymes en MAJUSCULES
 */
export function listNarratableAcronyms() {
  return Object.keys(ACRONYM_TO_NARRATIVE);
}
