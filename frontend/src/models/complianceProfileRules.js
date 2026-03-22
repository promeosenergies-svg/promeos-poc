/**
 * PROMEOS — V1.5 Compliance x Profile rules
 * Logique pure : calcule les tags et priorités des obligations
 * selon le profil de segmentation (réponses questionnaire).
 *
 * Garde-fous :
 * - Le boost profil ne casse JAMAIS le tri par urgence/statut
 * - "Déclaré" uniquement si l'obligation dépend d'une réponse utilisateur pertinente
 * - Pertinence affichée uniquement en cas de correspondance forte
 * - Jamais trop affirmatif juridiquement
 * - Ne JAMAIS masquer une obligation, seulement déprioriser/qualifier/contextualiser
 */

// Typologies où le Décret Tertiaire est fortement pertinent
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

// Typologies où BACS est fortement pertinent
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
 * R1 — Décret Tertiaire x q_surface_seuil
 * Libellés sobres et prudents.
 */
const DT_SURFACE_RULES = {
  oui_majorite: {
    boost: 2,
    tag: 'Prioritaire selon votre profil',
    color: 'green',
    reliability: 'declared',
    tooltip: 'Surface > 1 000 m² déclarée sur la majorité des bâtiments',
  },
  oui_certains: {
    boost: 1,
    tag: 'Applicable sur une partie du périmètre',
    color: 'blue',
    reliability: 'declared',
    tooltip: 'Surface > 1 000 m² déclarée sur certains bâtiments',
  },
  non: {
    boost: -2,
    tag: 'Moins prioritaire selon votre profil',
    color: 'gray',
    reliability: 'declared',
    tooltip: 'Surface < 1 000 m² déclarée — vérification recommandée',
  },
  ne_sait_pas: {
    boost: 0,
    tag: 'À qualifier',
    color: 'amber',
    reliability: 'to_confirm',
    tooltip: 'Surface non confirmée — qualification nécessaire',
  },
};

/**
 * R4 — BACS x q_gtb
 * La GTB est l'infrastructure de base pour la conformité BACS.
 * Sans GTB = mise en conformité à planifier (boost positif = attention requise).
 * Avec GTB = conformité BACS facilitée.
 */
const BACS_GTB_RULES = {
  oui_centralisee: {
    boost: 1,
    tag: 'GTB centralisée — BACS facilité',
    color: 'green',
    reliability: 'declared',
    tooltip: 'GTB centralisée déclarée — conformité BACS plus accessible',
  },
  oui_partielle: {
    boost: 0,
    tag: 'GTB partielle — BACS à vérifier par site',
    color: 'blue',
    reliability: 'declared',
    tooltip: 'GTB présente sur certains sites — vérification site par site recommandée',
  },
  non: {
    boost: 1,
    tag: 'Sans GTB — mise en conformité BACS à planifier',
    color: 'amber',
    reliability: 'declared',
    tooltip: 'Absence de GTB déclarée — planification BACS recommandée',
  },
  ne_sait_pas: {
    boost: 0,
    tag: 'À qualifier',
    color: 'amber',
    reliability: 'to_confirm',
    tooltip: 'Équipement GTB non confirmé — qualification nécessaire',
  },
};

/**
 * R5 — Décret Tertiaire x q_operat
 * OPERAT est la plateforme de déclaration pour le Décret Tertiaire.
 * En retard ou non déclaré = attention requise (boost positif).
 * Non concerné = dépriorisé (boost négatif, JAMAIS masqué).
 */
const DT_OPERAT_RULES = {
  oui_a_jour: {
    boost: 0,
    tag: 'Déclaration OPERAT à jour',
    color: 'green',
    reliability: 'declared',
    tooltip: 'Déclarations OPERAT à jour selon votre profil',
  },
  oui_retard: {
    boost: 1,
    tag: 'Déclaration OPERAT en retard',
    color: 'amber',
    reliability: 'declared',
    tooltip: 'Déclarations OPERAT en retard — régularisation recommandée',
  },
  non: {
    boost: 1,
    tag: 'OPERAT non déclaré',
    color: 'amber',
    reliability: 'declared',
    tooltip: 'Aucune déclaration OPERAT — action recommandée si concerné',
  },
  non_concerne: {
    boost: -1,
    tag: 'Non concerné OPERAT selon votre profil',
    color: 'gray',
    reliability: 'declared',
    tooltip: 'Non concerné par OPERAT selon votre déclaration — vérification recommandée',
  },
};

/**
 * Calcule les tags et priorités pour chaque obligation
 * en fonction du profil de segmentation.
 *
 * Le priorityBoost est un entier petit (ex: -2 à +2) utilisé
 * UNIQUEMENT pour trier au sein d'un même groupe statut/urgence.
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
  const gtbAnswer = answers.q_gtb;
  const operatAnswer = answers.q_operat;

  // Helper: appliquer une règle questionnaire sur une entry
  const applyRule = (entry, rule, state) => {
    entry.priorityBoost += rule.boost;
    entry.tags.push({ label: rule.tag, color: rule.color, tooltip: rule.tooltip });
    if (rule.reliability === 'declared') entry.reliability = 'declared';
    else if (rule.reliability === 'to_confirm' && entry.reliability !== 'declared')
      entry.reliability = 'to_confirm';
    state.usesUserAnswer = true;
  };

  for (const obl of obligations) {
    const code = (obl.code || obl.id || '').toLowerCase();
    const entry = { priorityBoost: 0, tags: [], reliability: 'detected' };
    const state = { usesUserAnswer: false };

    // R1 — Décret Tertiaire x q_surface_seuil
    if (code.includes('tertiaire') && surfaceAnswer && DT_SURFACE_RULES[surfaceAnswer]) {
      applyRule(entry, DT_SURFACE_RULES[surfaceAnswer], state);
    }

    // R4 — BACS x q_gtb
    if (code.includes('bacs') && gtbAnswer && BACS_GTB_RULES[gtbAnswer]) {
      applyRule(entry, BACS_GTB_RULES[gtbAnswer], state);
    }

    // R5 — Décret Tertiaire x q_operat
    if (code.includes('tertiaire') && operatAnswer && DT_OPERAT_RULES[operatAnswer]) {
      applyRule(entry, DT_OPERAT_RULES[operatAnswer], state);
    }

    // R2 — Pertinence par typologie (prudente)
    if (typologie) {
      let relevance = null;
      if (code.includes('tertiaire')) relevance = DT_RELEVANCE[typologie];
      else if (code.includes('bacs')) relevance = BACS_RELEVANCE[typologie];
      // APER: toujours medium (applicable selon parking/toiture, pas liée à typologie)

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

    // R3 — Fiabilité par obligation
    // "declared" UNIQUEMENT si cette obligation utilise une réponse utilisateur
    if (!state.usesUserAnswer) {
      entry.reliability = 'detected';
    }

    // Garde-fou: clamp boost à [-3, +3] pour éviter les extrêmes
    entry.priorityBoost = Math.max(-3, Math.min(3, entry.priorityBoost));

    if (entry.tags.length > 0 || entry.priorityBoost !== 0) {
      result.set(obl.id || obl.code, entry);
    }
  }

  return result;
}

export const RELIABILITY_CONFIG = {
  declared: {
    label: 'Déclaré',
    cls: 'bg-blue-50 text-blue-600',
    tooltip: 'Ajusté selon vos réponses',
  },
  detected: {
    label: 'Détecté',
    cls: 'bg-gray-50 text-gray-400',
    tooltip: 'Calculé depuis vos données patrimoine',
  },
  to_confirm: {
    label: 'À confirmer',
    cls: 'bg-amber-50 text-amber-600',
    tooltip: 'Information insuffisante — qualification recommandée',
  },
};

export const TAG_COLORS = {
  green: 'bg-green-100 text-green-700',
  blue: 'bg-blue-100 text-blue-700',
  amber: 'bg-amber-100 text-amber-700',
  gray: 'bg-gray-100 text-gray-500',
};
