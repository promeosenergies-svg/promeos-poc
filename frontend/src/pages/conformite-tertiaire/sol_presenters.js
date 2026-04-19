/**
 * PROMEOS — ConformiteTertiaireSol presenters (Lot 6 Phase 4, Pattern A hybride)
 *
 * Helpers purs pour le hero `/conformite/tertiaire`. Pure functions,
 * zéro import React, zéro calcul métier (pondérations/pénalités/jalons
 * absents de l'API — viennent du backend quand l'endpoint portfolio-summary
 * sera exposé, cf. docs/backlog/BACKLOG_P5_AUDIT_SME_API.md).
 *
 * API consommée (parent TertiaireDashboardPage.jsx) :
 *   getTertiaireDashboard({ site_id? }) → {
 *     total_efa, active, draft, closed,
 *     open_issues, critical_issues
 *   }
 *   getTertiaireEfas({ site_id? }) → { efas: [...] }
 *   getTertiaireSiteSignals({ site_id? }) → { sites: [...], counts, top_missing_fields }
 *
 * IMPORTANT — 7ᵉ remap Lot 6 (discipline honnêteté constante) :
 *   Spec prompt Phase 4 : RegAssessment ORG-level + weights_used +
 *   penalty_risk_eur + operat_trajectory.gap + frameworks_applicable.
 *   API réelle : aucun endpoint RegAssessment ORG-level n'existe.
 *   /api/tertiaire/dashboard expose 6 compteurs ORG agrégés (EFA
 *   active/draft/closed + open/critical issues). Le hero se cale sur
 *   ces 6 compteurs, quitte à laisser certains KPIs spec pour la
 *   Phase 5 backend (endpoints à exposer).
 *
 * Chaque helper accepte null|undefined → empty-state propre (pas de
 * throw). Unit tests Vitest couvrent null + 0 + frameworks manquants.
 */
import { NBSP, formatFR } from '../cockpit/sol_presenters';
import { businessErrorFallback } from '../../i18n/business_errors';

export { NBSP, formatFR };

// ─────────────────────────────────────────────────────────────────────────────
// 1. hasDashboard — empty-state guard
// ─────────────────────────────────────────────────────────────────────────────

export function hasDashboard(dashboard) {
  return Boolean(dashboard && typeof dashboard === 'object' && 'total_efa' in dashboard);
}

// ─────────────────────────────────────────────────────────────────────────────
// 2. formatEfaCount — KPI 1 display
// ─────────────────────────────────────────────────────────────────────────────

export function formatEfaCount(dashboard) {
  if (!hasDashboard(dashboard)) {
    return { value: null, total: null, label: '—', tone: 'calme' };
  }
  const total = Number(dashboard.total_efa) || 0;
  const active = Number(dashboard.active) || 0;
  const draft = Number(dashboard.draft) || 0;
  const closed = Number(dashboard.closed) || 0;
  const tone = active === total && total > 0 ? 'succes' : active === 0 ? 'refuse' : 'attention';
  return {
    value: active,
    total,
    draft,
    closed,
    label: `${active} / ${total}`,
    tone,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. formatIssuesOpen — KPI 2 display
// ─────────────────────────────────────────────────────────────────────────────

export function formatIssuesOpen(dashboard) {
  if (!hasDashboard(dashboard)) return { value: null, tone: 'calme' };
  const open = Number(dashboard.open_issues) || 0;
  const critical = Number(dashboard.critical_issues) || 0;
  const tone = critical > 0 ? 'refuse' : open > 0 ? 'attention' : 'succes';
  return { value: open, critical, tone };
}

// ─────────────────────────────────────────────────────────────────────────────
// 4. formatCriticalIssues — KPI 3 display
// ─────────────────────────────────────────────────────────────────────────────

export function formatCriticalIssues(dashboard) {
  if (!hasDashboard(dashboard)) return { value: null, tone: 'calme' };
  const critical = Number(dashboard.critical_issues) || 0;
  return {
    value: critical,
    tone: critical > 0 ? 'refuse' : 'succes',
    urgent: critical > 0,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// 5. buildKickerText
// ─────────────────────────────────────────────────────────────────────────────

export function buildKickerText(dashboard) {
  if (!hasDashboard(dashboard)) return 'CONFORMITÉ · DÉCRET TERTIAIRE';
  const total = Number(dashboard.total_efa) || 0;
  return `CONFORMITÉ · DÉCRET TERTIAIRE · ${total}${NBSP}EFA${total > 1 ? 'S' : ''} ENREGISTRÉE${total > 1 ? 'S' : ''}`;
}

// ─────────────────────────────────────────────────────────────────────────────
// 6. buildNarrative
// ─────────────────────────────────────────────────────────────────────────────

export function buildNarrative(dashboard) {
  if (!hasDashboard(dashboard)) {
    return "Aucune donnée Décret Tertiaire disponible — vérifiez l'import du patrimoine.";
  }
  const total = Number(dashboard.total_efa) || 0;
  const active = Number(dashboard.active) || 0;
  const draft = Number(dashboard.draft) || 0;
  const open = Number(dashboard.open_issues) || 0;
  const critical = Number(dashboard.critical_issues) || 0;

  if (total === 0) {
    return 'Aucune EFA Décret Tertiaire enregistrée pour votre organisation. Créez votre première EFA pour démarrer le suivi obligatoire 2030.';
  }

  const parts = [];
  parts.push(`${active}${NBSP}EFA actives sur ${total}${NBSP}enregistrée${total > 1 ? 's' : ''}`);
  if (draft > 0) parts.push(`${draft}${NBSP}en brouillon`);
  if (open > 0) {
    parts.push(`${open}${NBSP}problème${open > 1 ? 's' : ''} ouvert${open > 1 ? 's' : ''}`);
  }
  if (critical > 0) {
    parts.push(`${critical}${NBSP}critique${critical > 1 ? 's' : ''} à traiter en priorité`);
  }
  return parts.join(' · ') + '.';
}

// ─────────────────────────────────────────────────────────────────────────────
// 7. buildSubNarrative
// ─────────────────────────────────────────────────────────────────────────────

export function buildSubNarrative(dashboard) {
  const base =
    'Sources : moteur RegOps backend + /api/tertiaire/dashboard agrégats ORG · ' +
    'trajectoire 2030 évaluée par site via /api/regops/site/{id}.';
  if (!hasDashboard(dashboard)) return base;
  const closed = Number(dashboard.closed) || 0;
  if (closed > 0) {
    return `${closed}${NBSP}EFA clôturée${closed > 1 ? 's' : ''} (historique préservé). ${base}`;
  }
  return base;
}

// ─────────────────────────────────────────────────────────────────────────────
// 8. interpretEfaCount, interpretIssues, interpretCritical (tooltips KPIs)
// ─────────────────────────────────────────────────────────────────────────────

export function interpretEfaCount(dashboard) {
  const k = formatEfaCount(dashboard);
  if (k.value == null) return 'Statistiques EFA indisponibles.';
  if (k.total === 0) return 'Aucune EFA enregistrée — démarrez la déclaration OPERAT 2030.';
  if (k.value === k.total) return 'Toutes vos EFA sont actives · suivi réglementaire opérationnel.';
  return `${k.draft > 0 ? `${k.draft}${NBSP}brouillons à finaliser · ` : ''}${k.closed > 0 ? `${k.closed}${NBSP}clôturée${k.closed > 1 ? 's' : ''} (historique)` : ''}`.trim() || 'Suivi EFA en cours.';
}

export function interpretIssues(dashboard) {
  const k = formatIssuesOpen(dashboard);
  if (k.value == null) return 'Données problèmes indisponibles.';
  if (k.value === 0) return 'Aucun problème ouvert — conformité sous contrôle.';
  if (k.critical > 0) {
    return `${k.critical}${NBSP}critique${k.critical > 1 ? 's' : ''} parmi ${k.value} problèmes · action urgente requise.`;
  }
  return `${k.value}${NBSP}problème${k.value > 1 ? 's' : ''} à résoudre · surveillance active.`;
}

export function interpretCritical(dashboard) {
  const k = formatCriticalIssues(dashboard);
  if (k.value == null) return 'Données criticité indisponibles.';
  if (k.value === 0) return 'Aucun problème critique actif · portefeuille serein.';
  return `${k.value}${NBSP}problème${k.value > 1 ? 's' : ''} critique${k.value > 1 ? 's' : ''} · priorité absolue sur ces EFA.`;
}

// ─────────────────────────────────────────────────────────────────────────────
// 9. buildEmptyState — fallback si dashboard null
// ─────────────────────────────────────────────────────────────────────────────

export function buildEmptyState({ dashboard } = {}) {
  if (hasDashboard(dashboard)) return null;
  const fb = businessErrorFallback('conformite.no_dashboard');
  return { title: fb.title, message: fb.body };
}

// ─────────────────────────────────────────────────────────────────────────────
// 10. resolveTooltipExplain — router vers l'interpret correct par KPI code
// ─────────────────────────────────────────────────────────────────────────────

export function resolveTooltipExplain(kpiCode, dashboard) {
  switch (kpiCode) {
    case 'efa_count':
      return interpretEfaCount(dashboard);
    case 'open_issues':
      return interpretIssues(dashboard);
    case 'critical_issues':
      return interpretCritical(dashboard);
    default:
      return '';
  }
}
