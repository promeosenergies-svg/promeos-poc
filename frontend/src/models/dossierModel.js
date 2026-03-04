/**
 * PROMEOS — dossierModel.js (Étape 5)
 * Pure functions for building a "Dossier" data contract from a source + its linked actions.
 * No React imports — fully testable.
 *
 * Exports:
 *   buildDossier        → (source, actions, evidence) → DossierData
 *   groupActionsByWeek  → (actions) → { today, week, later, overdue }
 *   computeCloseabilityBadge → (action) → { label, status }
 *   DOSSIER_SECTION_LABELS → { [key]: string }
 */

import { SOURCE_LABELS_FR, buildSourceDeepLink } from './evidenceRules';

// ── Labels ──────────────────────────────────────────────────────────────────

export const DOSSIER_SECTION_LABELS = {
  header: 'En-tête du dossier',
  actions: 'Actions liées',
  evidence: 'Pièces justificatives',
  missing: 'À compléter',
  summary: 'Synthèse',
};

// ── buildDossier ────────────────────────────────────────────────────────────

/**
 * Build a structured dossier from a source and its linked actions.
 *
 * @param {{ sourceType: string, sourceId: string, label?: string, siteLabel?: string, orgLabel?: string, period?: string, severity?: string }} source
 * @param {Array} actions — backend-serialized actions (with evidence_required, source_label, etc.)
 * @param {Map<number, Array>} evidenceMap — actionId → evidence[] (from getActionEvidence)
 * @returns {{ header, actions, evidence, missing, stats }}
 */
export function buildDossier(source, actions = [], evidenceMap = new Map()) {
  if (!source || !source.sourceType) {
    return {
      header: null,
      actions: [],
      evidence: [],
      missing: [],
      stats: { total: 0, done: 0, open: 0, evidenceCount: 0, missingCount: 0 },
    };
  }

  const sourceLabel = source.label || SOURCE_LABELS_FR[source.sourceType] || source.sourceType;
  const deepLink = buildSourceDeepLink(source.sourceType, source.sourceId);

  // Filter actions linked to this source
  const linked = actions.filter(
    (a) => a.source_type === source.sourceType && a.source_id === source.sourceId
  );

  // Build evidence flat list + missing list
  const allEvidence = [];
  const missingItems = [];

  for (const action of linked) {
    const ev = evidenceMap.get(action.id) || [];
    for (const e of ev) {
      allEvidence.push({ ...e, actionId: action.id, actionTitle: action.title });
    }
    // Check if evidence is required but missing
    if (action.evidence_required && ev.length === 0) {
      missingItems.push({
        actionId: action.id,
        actionTitle: action.title,
        type: 'evidence_missing',
        labelFR: 'Preuve requise — aucune pièce jointe',
      });
    }
    // Check if action has no owner
    if (!action.owner) {
      missingItems.push({
        actionId: action.id,
        actionTitle: action.title,
        type: 'owner_missing',
        labelFR: 'Responsable non assigné',
      });
    }
  }

  const doneCount = linked.filter((a) => a.status === 'done').length;

  return {
    header: {
      sourceType: source.sourceType,
      sourceId: source.sourceId,
      sourceLabel,
      deepLink,
      orgLabel: source.orgLabel || '',
      siteLabel: source.siteLabel || '',
      period: source.period || '',
      generatedAt: new Date().toISOString(),
    },
    actions: linked.map((a) => ({
      id: a.id,
      title: a.title,
      status: a.status,
      priority: a.priority,
      severity: a.severity,
      owner: a.owner,
      dueDate: a.due_date,
      evidenceRequired: a.evidence_required,
      evidenceCount: (evidenceMap.get(a.id) || []).length,
      sourceLabel: a.source_label,
    })),
    evidence: allEvidence,
    missing: missingItems,
    stats: {
      total: linked.length,
      done: doneCount,
      open: linked.length - doneCount,
      evidenceCount: allEvidence.length,
      missingCount: missingItems.length,
    },
  };
}

// ── Week grouping for Runbook ───────────────────────────────────────────────

/**
 * Group actions into time buckets for the runbook view.
 *
 * @param {Array} actions — frontend-mapped actions with due_date and statut
 * @returns {{ overdue: Action[], today: Action[], week: Action[], later: Action[] }}
 */
export function groupActionsByWeek(actions) {
  const now = new Date();
  const todayStr = now.toISOString().slice(0, 10);
  const weekEnd = new Date(now);
  weekEnd.setDate(weekEnd.getDate() + 7);
  const weekEndStr = weekEnd.toISOString().slice(0, 10);

  const overdue = [];
  const today = [];
  const week = [];
  const later = [];

  for (const a of actions) {
    if (a.statut === 'done') continue; // skip closed actions

    const due = a.due_date || '';
    if (due && due < todayStr) {
      overdue.push(a);
    } else if (due === todayStr) {
      today.push(a);
    } else if (due && due <= weekEndStr) {
      week.push(a);
    } else {
      later.push(a);
    }
  }

  return { overdue, today, week, later };
}

// ── Closeability badge logic ────────────────────────────────────────────────

/**
 * Compute a closeability badge for a single action (client-side heuristic).
 * For the real closeability, use the backend endpoint.
 *
 * @param {{ statut: string, due_date?: string, evidence_required?: boolean, evidenceCount?: number, _backend?: object }} action
 * @returns {{ label: string, status: 'ok'|'warn'|'crit'|'neutral' }}
 */
export function computeCloseabilityBadge(action) {
  if (action.statut === 'done') {
    return { label: 'Clôturée', status: 'ok' };
  }

  const ba = action._backend || action;
  const evidenceRequired = ba.evidence_required || false;
  const evidenceCount = ba.evidence_count ?? action.evidenceCount ?? 0;

  // Overdue check
  const now = new Date().toISOString().slice(0, 10);
  const isOverdue = action.due_date && action.due_date < now;

  if (evidenceRequired && evidenceCount === 0) {
    return { label: 'Bloqué (preuve manquante)', status: 'crit' };
  }

  if (isOverdue) {
    return { label: 'En retard', status: 'warn' };
  }

  if (evidenceRequired && evidenceCount > 0) {
    return { label: 'Preuve requise ✓', status: 'ok' };
  }

  return { label: '', status: 'neutral' };
}

// ── Status labels (FR) ──────────────────────────────────────────────────────

export const STATUS_LABELS_FR = {
  open: 'Ouverte',
  in_progress: 'En cours',
  done: 'Terminée',
  blocked: 'Bloquée',
  false_positive: 'Faux positif',
};

export const PRIORITY_LABELS_FR = {
  1: 'Critique',
  2: 'Haute',
  3: 'Moyenne',
  4: 'Faible',
};
