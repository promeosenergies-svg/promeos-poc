/**
 * PROMEOS — SegmentationSol presenters (Lot 6 Phase 3, Pattern A compact)
 *
 * API consommée (parent SegmentationPage.jsx) :
 *   getSegmentationQuestions() → { questions: [{ id, text, options }] }
 *   getSegmentationProfile() → {
 *     has_profile, typologie (enum), segment_label, confidence_score,
 *     derived_from ('naf'|'questionnaire'|'patrimoine'|'mixte'),
 *     reasons: [], answers?: {}
 *   }
 *   submitSegmentationAnswers(answers) → { typologie, confidence_score, reasons }
 *
 * IMPORTANT — divergences spec user → API réelle (6ᵉ remap Lot 6) :
 *   - Spec parlait de KPIs agrégés patrimoine ("topArchetype.count sites",
 *     "avg_confidence_pct", "naf_coverage_pct" par site).
 *   - API expose un **profil ORGANISATION unique** (pas breakdown par
 *     site). L'organisation entière = 1 profil + 1 confidence + 1 source.
 *   - 3 KPIs remappés honnête : profil détecté · confiance · progression
 *     questionnaire.
 */
import { NBSP } from '../cockpit/sol_presenters';
import { businessErrorFallback } from '../../i18n/business_errors';

export { NBSP };

// ─────────────────────────────────────────────────────────────────────────────
// Labels
// ─────────────────────────────────────────────────────────────────────────────

export const TYPO_LABELS = {
  tertiaire_prive: 'Tertiaire Privé',
  tertiaire_public: 'Tertiaire Public',
  industrie: 'Industrie',
  commerce_retail: 'Commerce / Retail',
  copropriete_syndic: 'Copropriété / Syndic',
  bailleur_social: 'Bailleur Social',
  collectivite: 'Collectivité',
  hotellerie_restauration: 'Hôtellerie / Restauration',
  sante_medico_social: 'Santé / Médico-social',
  enseignement: 'Enseignement',
  mixte: 'Mixte (multi-activités)',
};

export const SOURCE_LABELS = {
  naf: 'Code NAF',
  questionnaire: 'Questionnaire',
  patrimoine: 'Patrimoine',
  mixte: 'Détection mixte',
};

// ─────────────────────────────────────────────────────────────────────────────
// Kicker + narratives
// ─────────────────────────────────────────────────────────────────────────────

export function buildSegmentationKicker({ profile } = {}) {
  if (!profile?.has_profile) return 'SEGMENTATION · PROFIL · EN COURS';
  const typo = profile.segment_label || TYPO_LABELS[profile.typologie] || 'PROFIL';
  return `SEGMENTATION · ${typo.toUpperCase()}`;
}

export function buildSegmentationNarrative({ profile, answeredCount = 0, totalQuestions = 0 } = {}) {
  if (!profile?.has_profile) {
    return 'Aucun profil détecté pour votre organisation. Répondez au questionnaire ci-dessous pour activer la segmentation et affiner les recommandations PROMEOS.';
  }
  const typo = profile.segment_label || TYPO_LABELS[profile.typologie] || 'Profil inconnu';
  const conf = Math.round(Number(profile.confidence_score) || 0);
  const source = SOURCE_LABELS[profile.derived_from] || profile.derived_from || '—';
  const parts = [`Votre organisation est segmentée comme ${typo}`];
  parts.push(`confiance ${conf}${NBSP}%`);
  parts.push(`source : ${source}`);
  if (totalQuestions > 0 && answeredCount < totalQuestions) {
    const remaining = totalQuestions - answeredCount;
    parts.push(`${remaining}${NBSP}question${remaining > 1 ? 's' : ''} à compléter pour affiner`);
  }
  return parts.join(' · ') + '.';
}

export function buildSegmentationSubNarrative({ profile } = {}) {
  const reasons = Array.isArray(profile?.reasons) ? profile.reasons : [];
  const reasonsBit = reasons.length > 0 ? `Signaux détectés : ${reasons.slice(0, 3).join(' · ')}. ` : '';
  return (
    reasonsBit +
    'Méthodologie : code NAF + questionnaire métier + analyse patrimoine · 11 typologies référence PROMEOS.'
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI interpretations
// ─────────────────────────────────────────────────────────────────────────────

export function interpretTypology({ profile } = {}) {
  if (!profile?.has_profile) return 'Profil en cours d\'établissement — complétez le questionnaire.';
  const source = SOURCE_LABELS[profile.derived_from] || profile.derived_from;
  return `Source : ${source}. Raffinez via questionnaire pour confiance supérieure.`;
}

export function interpretConfidence({ profile } = {}) {
  const c = Number(profile?.confidence_score);
  if (!Number.isFinite(c)) return 'Confiance indisponible — aucun profil actif.';
  if (c >= 70) return 'Haute confiance · recommandations personnalisées fiables.';
  if (c >= 40) return 'Confiance moyenne · questionnaire complémentaire recommandé.';
  return 'Faible confiance · compléter le questionnaire prioritairement.';
}

export function interpretQuestionnaireProgress({ answeredCount = 0, totalQuestions = 0 } = {}) {
  if (totalQuestions === 0) return 'Questionnaire en cours d\'initialisation.';
  if (answeredCount === 0) return 'Répondez aux questions pour activer la segmentation.';
  if (answeredCount === totalQuestions) return 'Questionnaire complet · profil à jour.';
  const pct = Math.round((answeredCount / totalQuestions) * 100);
  return `${pct}${NBSP}% des questions répondues · ${totalQuestions - answeredCount} restante${totalQuestions - answeredCount > 1 ? 's' : ''}.`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Status pill builder
// ─────────────────────────────────────────────────────────────────────────────

export function profilePill({ profile } = {}) {
  if (!profile?.has_profile) return { tone: 'afaire', label: 'En attente' };
  const c = Number(profile.confidence_score) || 0;
  if (c >= 70) return { tone: 'succes', label: 'Haute confiance' };
  if (c >= 40) return { tone: 'attention', label: 'Moyenne' };
  return { tone: 'refuse', label: 'Faible' };
}

// ─────────────────────────────────────────────────────────────────────────────
// Low-confidence fallback
// ─────────────────────────────────────────────────────────────────────────────

export function buildLowConfidenceNote({ profile } = {}) {
  const c = Number(profile?.confidence_score) || 0;
  if (!profile?.has_profile || c < 50) {
    const fb = businessErrorFallback('segmentation.low_confidence');
    return { title: fb.title, message: fb.body };
  }
  return null;
}
