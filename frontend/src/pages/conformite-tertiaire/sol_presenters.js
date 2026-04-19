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
// 4. formatCriticalIssues — KPI legacy (kept pour backward-compat tests
//    + potentielle réutilisation future par drawer "Pourquoi ?")
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
// 4 bis. formatDeadlineOperat — NEW KPI 3 (swap CRITIQUES → DEADLINE)
//
// L'API /api/tertiaire/dashboard n'expose ni `days_until_operat` ni
// `next_deadline` côté ORG. Le legacy TertiaireDashboardPage.jsx calcule
// `new Date('2026-09-30') - new Date()` — la date 2026-09-30 est
// l'échéance réglementaire OPERAT publique et stable (décret tertiaire).
// C'est une DATE RÉGLEMENTAIRE, pas une formule métier → pas de violation
// source-guard.
//
// Signature : accepte `deadlineDate` ISO optionnel (default fallback
// à la date OPERAT 2026). Quand un endpoint `/api/audit-sme/status`
// exposera un `deadline` dynamique (cf. backlog P5), la valeur sera
// passée explicitement au presenter.
//
// Tone 4 quadrants (cf. règle user D4 micro-alerte 2) :
//   ≥ 180 j : neutral/calme (pas d'urgence)
//   < 180 j : attention (amber, fenêtre de préparation)
//   < 60 j  : refuse (red, urgence dépôt)
//   ≤ 0 j   : refuse + label "échue" (dépassement)
// ─────────────────────────────────────────────────────────────────────────────

const DEFAULT_OPERAT_DEADLINE_ISO = '2026-09-30';

export function formatDeadlineOperat(dashboard, deadlineDate = DEFAULT_OPERAT_DEADLINE_ISO) {
  if (!hasDashboard(dashboard)) {
    return { days: null, tone: 'calme', label: '—', overdue: false };
  }
  if (!deadlineDate) {
    return { days: null, tone: 'calme', label: '—', overdue: false };
  }
  const target = new Date(deadlineDate);
  if (isNaN(target.getTime())) {
    return { days: null, tone: 'calme', label: '—', overdue: false };
  }
  const days = Math.ceil((target.getTime() - Date.now()) / 86_400_000);
  if (days <= 0) {
    return { days, tone: 'refuse', label: `échue${days < 0 ? ` (J+${Math.abs(days)})` : ''}`, overdue: true };
  }
  let tone = 'calme';
  if (days < 60) tone = 'refuse';
  else if (days < 180) tone = 'attention';
  return { days, tone, label: `J-${days}`, overdue: false };
}

export function interpretDeadlineOperat(dashboard, deadlineDate = DEFAULT_OPERAT_DEADLINE_ISO) {
  const k = formatDeadlineOperat(dashboard, deadlineDate);
  if (k.days == null) return 'Date d\'échéance OPERAT indisponible.';
  if (k.overdue) {
    return `Échéance OPERAT dépassée (${Math.abs(k.days)}${NBSP}jour${Math.abs(k.days) > 1 ? 's' : ''}) · régularisation urgente.`;
  }
  if (k.days < 60) return 'Échéance imminente · préparez le dépôt sans tarder.';
  if (k.days < 180) return 'Fenêtre de préparation ouverte · centralisez les données avant septembre.';
  return 'Délai confortable · prochaine action après consolidation 2026.';
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

export function buildNarrative(dashboard, deadlineDate) {
  if (!hasDashboard(dashboard)) {
    return "Aucune donnée Décret Tertiaire disponible — vérifiez l'import du patrimoine.";
  }
  const total = Number(dashboard.total_efa) || 0;
  const active = Number(dashboard.active) || 0;
  const open = Number(dashboard.open_issues) || 0;

  if (total === 0) {
    return 'Aucune EFA Décret Tertiaire enregistrée · créez la première pour démarrer le suivi 2030.';
  }

  // 1 phrase compact ≤ 120 car (directive P1 micro-sprint polish)
  const deadline = formatDeadlineOperat(dashboard, deadlineDate);
  const bits = [`${active}${NBSP}EFA actives`];
  if (open > 0) {
    bits.push(`${open}${NBSP}problème${open > 1 ? 's' : ''} ouvert${open > 1 ? 's' : ''}`);
  }
  if (deadline.days != null) {
    if (deadline.overdue) {
      bits.push(`OPERAT échue`);
    } else {
      bits.push(`OPERAT dans ${deadline.days}${NBSP}jours`);
    }
  }
  return bits.join(' · ') + '.';
}

// ─────────────────────────────────────────────────────────────────────────────
// 7. buildSubNarrative
// ─────────────────────────────────────────────────────────────────────────────

export function buildSubNarrative(dashboard) {
  // Version métier (directive P2 micro-sprint polish) : zéro mention
  // d'endpoints API. Transparence dev préservée via source chips sous
  // chaque SolKpiCard.
  if (!hasDashboard(dashboard)) return 'Trajectoire 2030 évaluée site par site.';
  const closed = Number(dashboard.closed) || 0;
  if (closed > 0) {
    return `${closed}${NBSP}EFA clôturée${closed > 1 ? 's' : ''} (historique préservé) · trajectoire 2030 évaluée site par site.`;
  }
  return 'Trajectoire 2030 évaluée site par site.';
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

export function resolveTooltipExplain(kpiCode, dashboard, deadlineDate) {
  switch (kpiCode) {
    case 'efa_count':
      return interpretEfaCount(dashboard);
    case 'open_issues':
      return interpretIssues(dashboard);
    case 'critical_issues':
      return interpretCritical(dashboard);
    case 'deadline_operat':
      return interpretDeadlineOperat(dashboard, deadlineDate);
    default:
      return '';
  }
}
