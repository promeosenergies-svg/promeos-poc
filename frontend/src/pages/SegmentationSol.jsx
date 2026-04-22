/**
 * PROMEOS — SegmentationSol (Lot 6 Phase 3, Pattern A compact)
 *
 * Injection Sol compacte en haut de SegmentationPage. Le legacy body
 * (profile card blue gradient + progress + questions Cards + submit
 * button) reste préservé intégralement dessous pour préserver le flow
 * questionnaire et la logique submitSegmentationAnswers du parent.
 *
 * Pattern A compact (identique à UsagesHorairesSol Phase 6 Lot 2) :
 * pas de SolBarChart, pas de SolWeekGrid, juste header + 3 KPIs.
 */
import React from 'react';
import { SolPageHeader, SolHeadline, SolKpiRow, SolKpiCard } from '../ui/sol';
import {
  buildSegmentationKicker,
  buildSegmentationNarrative,
  buildSegmentationSubNarrative,
  interpretTypology,
  interpretConfidence,
  interpretQuestionnaireProgress,
  profilePill,
  TYPO_LABELS,
} from './segmentation/sol_presenters';

/**
 * @param {Object} props
 * @param {Object} [props.profile]        getSegmentationProfile() result
 * @param {Array} [props.questions]       getSegmentationQuestions().questions
 * @param {Object} [props.answers]        answer map
 */
export default function SegmentationSol({ profile, questions = [], answers = {} }) {
  const totalQuestions = questions.length;
  const answeredCount = Object.values(answers).filter((v) => v).length;

  const kicker = buildSegmentationKicker({ profile });
  const narrative = buildSegmentationNarrative({ profile, answeredCount, totalQuestions });
  const subNarrative = buildSegmentationSubNarrative({ profile });
  const pill = profilePill({ profile });

  const confidenceValue = Number(profile?.confidence_score);
  const progressPct =
    totalQuestions > 0 ? Math.round((answeredCount / totalQuestions) * 100) : null;

  const typoLabel = profile?.has_profile
    ? profile.segment_label || TYPO_LABELS[profile.typologie] || profile.typologie || '—'
    : '—';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, padding: '24px 28px 0' }}>
      <SolPageHeader
        kicker={kicker}
        title="Segmentation B2B"
        titleEm="· moteur NAF × métier"
        narrative={narrative}
        subNarrative={subNarrative}
      />

      <SolHeadline>
        <em>Votre organisation</em>{' '}
        {profile?.has_profile
          ? `est segmentée comme ${typoLabel} (${pill.label.toLowerCase()}).`
          : "n'a pas encore de profil — questionnaire à compléter ci-dessous."}
      </SolHeadline>

      <SolKpiRow>
        <SolKpiCard
          label="Profil détecté"
          value={typoLabel}
          unit={profile?.derived_from ? `source : ${profile.derived_from}` : ''}
          semantic="neutral"
          explainKey="segmentation_profile_typology"
          headline={interpretTypology({ profile })}
          source={{ kind: 'calcul', origin: 'NAF + questionnaire + patrimoine' }}
        />
        <SolKpiCard
          label="Confiance"
          value={Number.isFinite(confidenceValue) ? String(Math.round(confidenceValue)) : '—'}
          unit="/100"
          semantic="score"
          explainKey="segmentation_confidence_score"
          headline={interpretConfidence({ profile })}
          source={{ kind: 'calcul', origin: 'moteur segmentation' }}
        />
        <SolKpiCard
          label="Questionnaire"
          value={progressPct != null ? `${progressPct}` : '—'}
          unit={`% · ${answeredCount}/${totalQuestions}`}
          semantic="score"
          explainKey="segmentation_questionnaire_progress"
          headline={interpretQuestionnaireProgress({ answeredCount, totalQuestions })}
          source={{ kind: 'calcul', origin: 'réponses / questions totales' }}
        />
      </SolKpiRow>
    </div>
  );
}
