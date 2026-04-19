/**
 * PROMEOS — RegOpsSol (Lot 3 Phase 3, refonte Sol Pattern C)
 *
 * Fiche dossier réglementaire par site en Pattern C :
 *   SolBreadcrumb → SolDetailPage(entityCard + kpiRow + mainContent)
 *   mainContent = 3 KPIs + SolTimeline findings + SolWeekGrid 3 signaux.
 *
 * Architecture :
 *   - RegOps.jsx (parent) gère data fetch + useParams + useScope.
 *   - RegOpsSol.jsx (ici) reçoit en props `assessment` (normalisé),
 *     `site` (depuis scopedSites), `aiExplanation`, `aiRecommendations`.
 *     Pur composant de présentation.
 *
 * La section « Synthèse IA » est rendue en bas comme section optionnelle
 * si aiExplanation.brief est présent — pas d'onglet parallèle, pas de
 * mode « dual panel » legacy.
 */
import React from 'react';
import {
  SolDetailPage,
  SolEntityCard,
  SolKpiRow,
  SolKpiCard,
  SolSourceChip,
  SolSectionHead,
  SolTimeline,
  SolWeekGrid,
  SolWeekCard,
  SolInspectDoc,
  SolButton,
} from '../ui/sol';
import {
  buildRegOpsKicker,
  buildRegOpsNarrative,
  buildRegOpsSubNarrative,
  statusPillFromAssessment,
  buildRegOpsEntityCardFields,
  computeCompletion,
  sumPenalties,
  daysUntil,
  interpretRegOpsCompletion,
  interpretRegOpsPenalty,
  interpretRegOpsDeadline,
  buildRegOpsTimelineEvents,
  buildRegOpsWeekCards,
  formatFR,
  formatFREur,
  NBSP,
} from './regops/sol_presenters';

/**
 * @param {Object} props
 * @param {Object} props.assessment      - RegAssessment normalisé
 * @param {Object} [props.site]          - Site depuis scopedSites (optionnel)
 * @param {Object} [props.aiExplanation] - { brief, needs_human_review }
 * @param {Object} [props.aiRecommendations] - { suggestions: [...] }
 * @param {(fOrA:Object)=>void} [props.onOpenAction]
 * @param {()=>void} [props.onBackToSite]
 */
export default function RegOpsSol({
  assessment,
  site = null,
  aiExplanation = null,
  aiRecommendations = null,
  onOpenAction,
  onBackToSite,
}) {
  if (!assessment) {
    return (
      <div style={{ padding: 24, color: 'var(--sol-ink-500)', fontStyle: 'italic' }}>
        Évaluation réglementaire indisponible pour ce site.
      </div>
    );
  }

  const findings = assessment.findings || [];
  const kicker = buildRegOpsKicker({ site, assessment });
  const narrative = buildRegOpsNarrative({ assessment, site, findings });
  const subNarrative = buildRegOpsSubNarrative({ assessment });
  const pill = statusPillFromAssessment({ assessment });
  const fields = buildRegOpsEntityCardFields({ assessment, site, findings });

  const completion = computeCompletion(findings);
  const penalty = sumPenalties(findings);
  const days = daysUntil(assessment.next_deadline);

  const timelineEvents = buildRegOpsTimelineEvents({ assessment, findings });
  const weekCards = buildRegOpsWeekCards({
    assessment,
    findings,
    onOpenAction,
  });

  const siteName = site?.nom || `Site #${assessment.site_id}`;
  const title = `Dossier conformité`;
  const titleEm = `· ${siteName}`;

  const breadcrumbSegments = [{ label: 'Conformité', to: '/conformite' }];
  if (site?.nom) {
    breadcrumbSegments.push({ label: site.nom, to: `/sites/${assessment.site_id}` });
  }
  breadcrumbSegments.push({ label: 'RegOps' });

  const entityCardActions = (
    <>
      {site?.id && (
        <SolButton variant="secondary" onClick={() => onBackToSite?.(site.id)}>
          Fiche site
        </SolButton>
      )}
      <SolButton variant="ghost" onClick={() => window.location.reload()}>
        Réévaluer
      </SolButton>
    </>
  );

  const entityCard = (
    <SolEntityCard
      title={siteName}
      subtitle={`Dossier RegOps · moteur déterministe${assessment.deterministic_version ? ' v' + assessment.deterministic_version : ''}`}
      status={pill}
      fields={fields}
      actions={entityCardActions}
    />
  );

  const kpiRow = (
    <SolKpiRow>
      <SolKpiCard
        label="Complétude obligations"
        value={completion.percent != null ? String(completion.percent) : '—'}
        unit="%"
        semantic="score"
        explainKey="regops_completion"
        headline={interpretRegOpsCompletion(findings)}
        source={{ kind: 'calcul', origin: 'moteur RegOps' }}
      />
      <SolKpiCard
        label="Pénalité potentielle"
        value={penalty > 0 ? formatFREur(penalty, 0) : '—'}
        unit=""
        semantic="cost"
        explainKey="regops_penalty_eur"
        headline={interpretRegOpsPenalty(findings)}
        source={{ kind: 'calcul', origin: 'barèmes réglementaires' }}
      />
      <SolKpiCard
        label="Jours restants"
        value={days != null ? String(days) : '—'}
        unit={days != null ? (Math.abs(days) > 1 ? 'jours' : 'jour') : ''}
        semantic="cost"
        explainKey="regops_days_remaining"
        headline={interpretRegOpsDeadline(assessment.next_deadline)}
        source={{ kind: 'calcul', origin: 'échéances légales' }}
      />
    </SolKpiRow>
  );

  const mainContent = (
    <>
      <SolSectionHead
        title="Timeline du dossier"
        meta={`${findings.length}${NBSP}finding${findings.length > 1 ? 's' : ''} · ordre chronologique`}
      />
      <SolTimeline
        events={timelineEvents}
        emptyLabel="Aucun finding actif — le moteur RegOps surveille ce dossier en continu."
        onNavigate={(dl) => onOpenAction?.({ deeplink: dl })}
      />

      <SolSectionHead title="Cette semaine sur ce dossier" meta="3 signaux" />
      <SolWeekGrid>
        {weekCards.map((c) => (
          <SolWeekCard
            key={c.id}
            tagLabel={c.tagLabel}
            tagKind={c.tagKind}
            title={c.title}
            body={c.body}
            footerLeft={c.footerLeft}
            footerRight={c.footerRight}
            onClick={c.onClick}
          />
        ))}
      </SolWeekGrid>

      {aiExplanation?.brief && (
        <>
          <SolSectionHead
            title="Synthèse IA"
            meta={
              aiExplanation.needs_human_review
                ? 'nécessite une révision humaine'
                : 'suggestions non-déterministes'
            }
          />
          <SolInspectDoc>
            <p style={{ whiteSpace: 'pre-wrap' }}>{aiExplanation.brief}</p>
            {Array.isArray(aiRecommendations?.suggestions) && aiRecommendations.suggestions.length > 0 && (
              <>
                <p style={{ marginTop: 12, fontWeight: 600 }}>Recommandations :</p>
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  {aiRecommendations.suggestions.slice(0, 5).map((s, i) => (
                    <li key={i} style={{ marginBottom: 4 }}>
                      {typeof s === 'string' ? s : s.label || s.suggestion || '—'}
                    </li>
                  ))}
                </ul>
              </>
            )}
            <p style={{ fontSize: 12, color: 'var(--sol-ink-500)', marginTop: 12, fontStyle: 'italic' }}>
              Les suggestions IA ne modifient jamais le statut de conformité déterministe.
            </p>
          </SolInspectDoc>
        </>
      )}
    </>
  );

  return (
    <SolDetailPage
      breadcrumb={{
        segments: breadcrumbSegments,
        backTo: site?.id ? `/sites/${site.id}` : '/conformite',
      }}
      kicker={kicker}
      title={title}
      titleEm={titleEm}
      narrative={narrative}
      subNarrative={subNarrative}
      entityCard={entityCard}
      kpiRow={kpiRow}
      mainContent={mainContent}
    />
  );
}
