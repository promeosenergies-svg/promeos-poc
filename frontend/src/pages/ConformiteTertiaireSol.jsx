/**
 * PROMEOS — ConformiteTertiaireSol (Lot 6 Phase 4, Pattern A hybride)
 *
 * Hero Sol injecté EN HAUT de TertiaireDashboardPage.jsx. Le legacy
 * body (DtProgressMultiSite + Sites à traiter section + EFA list +
 * MutualisationSection + ExportOperatModal + Drawer "Pourquoi ?")
 * reste préservé intégralement dessous.
 *
 * Pattern A hybride compact (~160 L avec KpiRow inline) — pas de
 * composant KpiRow séparé car 3 KPIs standards SolKpiCard suffisent
 * et pas de réutilisation cross-page prévue.
 *
 * Proposition A (7ᵉ remap Lot 6) : lit /api/tertiaire/dashboard
 * (ORG-level existant) au lieu de RegAssessment ORG-level inexistant.
 * 3 KPIs honnêtes : EFA actives / Issues ouvertes / Issues critiques.
 * Audit SMÉ reporté backlog P5.
 */
import React from 'react';
import {
  SolPageHeader,
  SolHeadline,
  SolSubline,
  SolKpiRow,
  SolKpiCard,
} from '../ui/sol';
import {
  hasDashboard,
  formatEfaCount,
  formatIssuesOpen,
  formatDeadlineOperat,
  buildKickerText,
  buildNarrative,
  buildSubNarrative,
  interpretEfaCount,
  interpretIssues,
  interpretDeadlineOperat,
  buildEmptyState,
  NBSP,
} from './conformite-tertiaire/sol_presenters';

const TONE_TO_SEMANTIC = {
  succes: 'score',
  calme: 'neutral',
  attention: 'cost',
  refuse: 'cost',
};

/**
 * @param {Object} props
 * @param {Object} [props.dashboard]    getTertiaireDashboard() result
 * @param {boolean} [props.isLoading]
 * @param {Error|null} [props.error]
 */
export default function ConformiteTertiaireSol({ dashboard, isLoading = false, error = null }) {
  // 1. Loading state
  if (isLoading) {
    return (
      <div
        role="status"
        aria-label="Chargement du tableau de bord conformité"
        style={{
          padding: '24px 28px',
          color: 'var(--sol-ink-500)',
          fontStyle: 'italic',
        }}
      >
        Chargement des agrégats Décret Tertiaire…
      </div>
    );
  }

  // 2. Error state
  if (error) {
    return (
      <div
        role="alert"
        style={{
          padding: '24px 28px',
          background: 'var(--sol-refuse-bg)',
          border: '1px solid var(--sol-refuse-fg)',
          borderRadius: 6,
          color: 'var(--sol-refuse-fg)',
          margin: '24px 28px 0',
        }}
      >
        <strong>Erreur chargement conformité :</strong>{' '}
        {error.message || String(error)}
      </div>
    );
  }

  // 3. Empty state
  const empty = buildEmptyState({ dashboard });
  if (empty && !hasDashboard(dashboard)) {
    return (
      <div
        role="region"
        aria-label="État vide conformité"
        style={{
          padding: '28px',
          margin: '24px 28px 0',
          background: 'var(--sol-attention-bg)',
          border: '1px dashed var(--sol-attention-fg)',
          borderRadius: 6,
          textAlign: 'center',
        }}
      >
        <p
          style={{
            fontFamily: 'var(--sol-font-display)',
            fontSize: 17,
            fontWeight: 600,
            color: 'var(--sol-ink-900)',
            margin: 0,
            marginBottom: 6,
          }}
        >
          {empty.title}
        </p>
        <p
          style={{
            fontFamily: 'var(--sol-font-body)',
            fontSize: 13.5,
            color: 'var(--sol-ink-700)',
            margin: 0,
            lineHeight: 1.45,
          }}
        >
          {empty.message}
        </p>
      </div>
    );
  }

  // 4. Happy path
  const kicker = buildKickerText(dashboard);
  const narrative = buildNarrative(dashboard);
  const subNarrative = buildSubNarrative(dashboard);
  const efaK = formatEfaCount(dashboard);
  const issuesK = formatIssuesOpen(dashboard);
  const deadlineK = formatDeadlineOperat(dashboard);

  return (
    <section
      role="region"
      aria-label="Hero conformité tertiaire"
      style={{ display: 'flex', flexDirection: 'column', gap: 20, padding: '24px 28px 0' }}
    >
      <SolPageHeader
        kicker={kicker}
        title="Conformité · Décret Tertiaire"
        titleEm="· portefeuille"
        narrative={narrative}
        subNarrative={subNarrative}
      />

      <SolKpiRow>
        <SolKpiCard
          label="EFA actives"
          value={efaK.value != null ? String(efaK.value) : '—'}
          unit={efaK.total != null ? `/ ${efaK.total}` : ''}
          semantic={TONE_TO_SEMANTIC[efaK.tone] || 'neutral'}
          explainKey="tertiaire_efa_active_count"
          headline={interpretEfaCount(dashboard)}
          source={{ kind: 'calcul', origin: '/api/tertiaire/dashboard' }}
        />
        <SolKpiCard
          label="Problèmes ouverts"
          value={issuesK.value != null ? String(issuesK.value) : '—'}
          unit="à traiter"
          semantic={TONE_TO_SEMANTIC[issuesK.tone] || 'neutral'}
          explainKey="tertiaire_open_issues"
          headline={interpretIssues(dashboard)}
          source={{ kind: 'calcul', origin: '/api/tertiaire/dashboard' }}
        />
        <SolKpiCard
          label="Échéance OPERAT"
          value={deadlineK.days != null ? deadlineK.label : '—'}
          unit={deadlineK.overdue ? 'régularisation urgente' : 'jours restants'}
          semantic={TONE_TO_SEMANTIC[deadlineK.tone] || 'neutral'}
          explainKey="tertiaire_deadline_operat"
          headline={interpretDeadlineOperat(dashboard)}
          source={{ kind: 'calcul', origin: 'Décret Tertiaire · 30/09/2026' }}
        />
      </SolKpiRow>
    </section>
  );
}
