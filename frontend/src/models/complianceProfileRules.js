/**
 * PROMEOS — V1.4 Compliance x Profile rules (version corrigee)
 * Logique pure : calcule les tags et priorites des obligations
 * selon le profil de segmentation (reponses questionnaire).
 *
 * Garde-fous :
 * - Le boost profil ne casse JAMAIS le tri par urgence/statut
 * - "Declare" uniquement si l'obligation depend d'une reponse utilisateur pertinente
 * - Pertinence affichee uniquement en cas de correspondance forte
 * - Jamais trop affirmatif juridiquement
 */

// Typologies ou le Decret Tertiaire est fortement pertinent
const DT_RELEVANCE = {
  tertiaire_prive: 'high',
  tertiaire_public: 'high',
  collectivite: 'high',
  enseignement: 'high',
  sante_medico_social: 'high',
  hotellerie_restauration: 'high',
  commerce_retail: 'medium',
  industrie: 'check_context',
  copropriete_syndic: 'check_context',
  bailleur_social: 'check_context',
  mixte: 'medium',
};

// Typologies ou BACS est fortement pertinent
const BACS_RELEVANCE = {
  tertiaire_prive: 'high',
  tertiaire_public: 'high',
  sante_medico_social: 'high',
  hotellerie_restauration: 'high',
  enseignement: 'medium',
  collectivite: 'medium',
  industrie: 'medium',
  commerce_retail: 'check_context',
  copropriete_syndic: 'check_context',
  bailleur_social: 'check_context',
  mixte: 'medium',
};

/**
 * R1 — Decret Tertiaire x q_surface_seuil
 * Libelles sobres et prudents.
 */
const DT_SURFACE_RULES = {
  oui_majorite: {
    boost: 2,
    tag: 'Prioritaire selon votre profil',
    color: 'green',
    reliability: 'declared',
    tooltip: 'Surface > 1 000 m\u00b2 d\u00e9clar\u00e9e sur la majorit\u00e9 des b\u00e2timents',
  },
  oui_certains: {
    boost: 1,
    tag: 'Applicable sur une partie du p\u00e9rim\u00e8tre',
    color: 'blue',
    reliability: 'declared',
    tooltip: 'Surface > 1 000 m\u00b2 d\u00e9clar\u00e9e sur certains b\u00e2timents',
  },
  non: {
    boost: -2,
    tag: 'Moins prioritaire selon votre profil',
    color: 'gray',
    reliability: 'declared',
    tooltip: 'Surface < 1 000 m\u00b2 d\u00e9clar\u00e9e — v\u00e9rification recommand\u00e9e',
  },
  ne_sait_pas: {
    boost: 0,
    tag: '\u00c0 qualifier',
    color: 'amber',
    reliability: 'to_confirm',
    tooltip: 'Surface non confirm\u00e9e — qualification n\u00e9cessaire',
  },
};

/**
 * Calcule les tags et priorites pour chaque obligation
 * en fonction du profil de segmentation.
 *
 * Le priorityBoost est un entier petit (ex: -2 a +2) utilise
 * UNIQUEMENT pour trier au sein d'un meme groupe statut/urgence.
 * Il ne peut jamais faire remonter une obligation conforme
 * au-dessus d'une obligation non conforme.
 *
 * @param {Array} obligations - liste des obligations (de sitesToObligations)
 * @param {Object|null} segProfile - profil de segmentation (de getSegmentationProfile)
 * @returns {Map<string, {priorityBoost: number, tags: Array, reliability: string}>}
 */
export function computeObligationProfileTags(obligations, segProfile) {
  const result = new Map();
  if (!segProfile?.has_profile || !obligations?.length) return result;

  const answers = segProfile.answers || {};
  const typologie = (segProfile.typologie || '').toLowerCase();
  const surfaceAnswer = answers.q_surface_seuil;

  for (const obl of obligations) {
    const code = (obl.code || obl.id || '').toLowerCase();
    const entry = { priorityBoost: 0, tags: [], reliability: 'detected' };
    let usesUserAnswer = false;

    // R1 — Decret Tertiaire x q_surface_seuil
    if (code.includes('tertiaire') && surfaceAnswer && DT_SURFACE_RULES[surfaceAnswer]) {
      const rule = DT_SURFACE_RULES[surfaceAnswer];
      entry.priorityBoost = rule.boost;
      entry.tags.push({ label: rule.tag, color: rule.color, tooltip: rule.tooltip });
      entry.reliability = rule.reliability;
      usesUserAnswer = true;
    }

    // R2 — Pertinence par typologie (prudente)
    if (typologie) {
      let relevance = null;
      if (code.includes('tertiaire')) relevance = DT_RELEVANCE[typologie];
      else if (code.includes('bacs')) relevance = BACS_RELEVANCE[typologie];
      // APER: toujours medium (applicable selon parking/toiture, pas liee a typologie)

      // Afficher le badge "Pertinent" uniquement en cas de correspondance forte
      if (relevance === 'high') {
        entry.tags.push({
          label: 'Pertinent pour votre profil',
          color: 'blue',
          tooltip: `Typologie : ${segProfile.segment_label || typologie}`,
        });
      }
      // medium et check_context : pas de badge visible, pas d'affirmation
    }

    // R3 — Fiabilite par obligation
    // "declared" UNIQUEMENT si cette obligation utilise une reponse utilisateur
    if (usesUserAnswer) {
      // reliability deja set par DT_SURFACE_RULES
    } else {
      // Pas de reponse utilisateur pertinente pour cette obligation
      entry.reliability = 'detected';
    }

    if (entry.tags.length > 0 || entry.priorityBoost !== 0) {
      result.set(obl.id || obl.code, entry);
    }
  }

  return result;
}

export const RELIABILITY_CONFIG = {
  declared: {
    label: 'D\u00e9clar\u00e9',
    cls: 'bg-blue-50 text-blue-600',
    tooltip: 'Ajust\u00e9 selon vos r\u00e9ponses',
  },
  detected: {
    label: 'D\u00e9tect\u00e9',
    cls: 'bg-gray-50 text-gray-400',
    tooltip: 'Calcul\u00e9 depuis vos donn\u00e9es patrimoine',
  },
  to_confirm: {
    label: '\u00c0 confirmer',
    cls: 'bg-amber-50 text-amber-600',
    tooltip: 'Information insuffisante \u2014 qualification recommand\u00e9e',
  },
};

export const TAG_COLORS = {
  green: 'bg-green-100 text-green-700',
  blue: 'bg-blue-100 text-blue-700',
  amber: 'bg-amber-100 text-amber-700',
  gray: 'bg-gray-100 text-gray-500',
};
