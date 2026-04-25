/**
 * PROMEOS — RegOpsSol presenters (Lot 3 Phase 3)
 *
 * Helpers purs pour RegOpsSol (fiche dossier réglementaire par site).
 *
 * API consommée (parent RegOps.jsx) :
 *   getRegOpsAssessment(siteId) → RegAssessment
 *     { site_id, compliance_score (0-100), global_status (RegStatus),
 *       next_deadline, findings: [...], actions: [...], missing_data: [...],
 *       deterministic_version }
 *
 * Un « dossier » RegOps = une évaluation agrégée par SITE, couvrant
 * plusieurs obligations réglementaires (DT/BACS/APER) via la liste
 * `findings`. Chaque finding a un rule_id, legal_deadline, penalty.
 *
 * Source de vérité libellés : domain/compliance/complianceLabels.fr.js
 */
import { NBSP, formatFR, formatFREur } from '../cockpit/sol_presenters';
import {
  REG_LABELS,
  REGOPS_STATUS_LABELS,
  REGOPS_SEVERITY_LABELS,
  RULE_LABELS,
} from '../../domain/compliance/complianceLabels.fr';
import { businessErrorFallback } from '../../i18n/business_errors';

export { NBSP, formatFR, formatFREur };

// ─────────────────────────────────────────────────────────────────────────────
// Date helpers
// ─────────────────────────────────────────────────────────────────────────────

export function daysUntil(dateStr) {
  if (!dateStr) return null;
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return null;
  const diffMs = d.getTime() - Date.now();
  return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
}

export function formatDateFR(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
}

// ─────────────────────────────────────────────────────────────────────────────
// Tone mappings
// ─────────────────────────────────────────────────────────────────────────────

const SEVERITY_TONE = {
  CRITICAL: 'refuse',
  HIGH: 'attention',
  MEDIUM: 'afaire',
  LOW: 'succes',
};

const STATUS_TONE = {
  COMPLIANT: 'succes',
  AT_RISK: 'attention',
  NON_COMPLIANT: 'refuse',
  UNKNOWN: 'afaire',
  OUT_OF_SCOPE: 'calme',
  EXEMPTION_POSSIBLE: 'calme',
};

export function toneFromSeverity(severity) {
  return SEVERITY_TONE[severity] || 'afaire';
}

export function toneFromStatus(status) {
  return STATUS_TONE[status] || 'afaire';
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI computations
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Complétude obligations : % de findings en statut COMPLIANT.
 * Exclut la catégorie 'incentive' (CEE masqué V1.2, non-obligatoire).
 * Retourne { percent, compliant, total }.
 */
export function computeCompletion(findings = []) {
  const obligations = (findings || []).filter((f) => f?.category !== 'incentive');
  const total = obligations.length;
  if (total === 0) return { percent: null, compliant: 0, total: 0 };
  const compliant = obligations.filter((f) => f.status === 'COMPLIANT').length;
  const percent = Math.round((compliant / total) * 100);
  return { percent, compliant, total };
}

/**
 * Somme des pénalités estimées sur findings non-compliants.
 * Seuls les findings en AT_RISK ou NON_COMPLIANT contribuent.
 */
export function sumPenalties(findings = []) {
  const atRisk = (findings || []).filter(
    (f) => f?.status === 'AT_RISK' || f?.status === 'NON_COMPLIANT'
  );
  return atRisk.reduce((acc, f) => acc + (Number(f.estimated_penalty_eur) || 0), 0);
}

// ─────────────────────────────────────────────────────────────────────────────
// Kicker + narratives
// ─────────────────────────────────────────────────────────────────────────────

export function buildRegOpsKicker({ site, assessment } = {}) {
  const statusFR = REGOPS_STATUS_LABELS[assessment?.global_status] || 'À qualifier';
  const siteName = site?.nom || `#${assessment?.site_id ?? '—'}`;
  return `CONFORMITÉ · DOSSIER ${siteName.toUpperCase()} · ${statusFR.toUpperCase()}`;
}

export function buildRegOpsNarrative({ assessment, site, findings = [] }) {
  if (!assessment) {
    return 'Évaluation en cours. Sol analyse les obligations applicables à ce site.';
  }
  const score =
    assessment.compliance_score != null ? Math.round(assessment.compliance_score) : null;
  const { percent, compliant, total } = computeCompletion(findings);
  const penalty = sumPenalties(findings);
  const days = daysUntil(assessment.next_deadline);
  const siteLabel = site?.nom ? `Votre dossier conformité ${site.nom}` : 'Votre dossier conformité';

  const parts = [];
  if (score != null) {
    parts.push(`${siteLabel} affiche un score de ${score}${NBSP}/${NBSP}100`);
  } else {
    parts.push(`${siteLabel} est en cours d'évaluation`);
  }
  if (percent != null && total > 0) {
    parts.push(
      `${compliant}${NBSP}obligation${compliant > 1 ? 's' : ''} sur ${total} conforme${compliant > 1 ? 's' : ''} (${percent}${NBSP}%)`
    );
  }
  if (penalty > 0) {
    parts.push(`pénalité potentielle ${formatFREur(penalty, 0)} en cas de dépôt manqué`);
  }
  if (days != null) {
    if (days <= 0) {
      parts.push(
        `échéance dépassée de ${Math.abs(days)}${NBSP}jour${Math.abs(days) > 1 ? 's' : ''}`
      );
    } else if (days <= 30) {
      parts.push(`prochaine échéance dans ${days}${NBSP}jour${days > 1 ? 's' : ''}`);
    } else if (days <= 90) {
      parts.push(`prochaine échéance dans ${days}${NBSP}jours, fenêtre de préparation ouverte`);
    }
  }
  return parts.join(' · ') + '.';
}

export function buildRegOpsSubNarrative({ assessment, freshness: freshnessStr }) {
  const src = ['Sources : moteur RegOps déterministe + RULE_LABELS canoniques'];
  if (assessment?.deterministic_version) {
    src.push(`moteur v${assessment.deterministic_version}`);
  }
  if (freshnessStr) src.push(freshnessStr);
  return src.join(' · ') + '.';
}

// ─────────────────────────────────────────────────────────────────────────────
// Status pill (assessment-driven)
// ─────────────────────────────────────────────────────────────────────────────

export function statusPillFromAssessment({ assessment } = {}) {
  if (!assessment?.global_status) return null;
  const label = REGOPS_STATUS_LABELS[assessment.global_status] || assessment.global_status;
  const tone = toneFromStatus(assessment.global_status);
  return { tone, label };
}

// ─────────────────────────────────────────────────────────────────────────────
// Entity card fields
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Fields entity card pour RegOpsSol.
 * Ordre : Site parent · Framework couverts · Score · Prochaine échéance ·
 *         Statut OPERAT · Dernière évaluation.
 */
export function buildRegOpsEntityCardFields({ assessment, site, findings = [] }) {
  if (!assessment) return [];

  // Frameworks couverts (findings distincts regulation)
  const frameworks = new Set();
  for (const f of findings || []) {
    if (f?.regulation && f.category !== 'incentive') {
      frameworks.add(f.regulation);
    }
  }
  const frameworksLabel =
    Array.from(frameworks)
      .map((k) => REG_LABELS[k] || k)
      .join(' · ') || '—';

  // Statut OPERAT : statut du finding dont regulation contient 'decret_tertiaire'
  const operatFinding = (findings || []).find(
    (f) => f?.regulation === 'decret_tertiaire_operat' || f?.rule_id?.includes('operat')
  );
  const operatLabel = operatFinding
    ? REGOPS_STATUS_LABELS[operatFinding.status] || operatFinding.status
    : 'Non applicable';

  const scoreLabel =
    assessment.compliance_score != null
      ? `${Math.round(assessment.compliance_score)}${NBSP}/${NBSP}100`
      : '—';

  return [
    { label: 'Site', value: site?.nom || `#${assessment.site_id || '—'}` },
    { label: 'Obligations', value: frameworksLabel },
    { label: 'Score conformité', value: scoreLabel, mono: true },
    { label: 'Prochaine échéance', value: formatDateFR(assessment.next_deadline), mono: true },
    { label: 'Statut OPERAT', value: operatLabel },
    {
      label: 'Moteur',
      value: assessment.deterministic_version
        ? `v${assessment.deterministic_version}`
        : 'déterministe',
      mono: true,
    },
  ];
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI interpretations
// ─────────────────────────────────────────────────────────────────────────────

export function interpretRegOpsCompletion(findings = []) {
  const { percent, compliant, total } = computeCompletion(findings);
  if (percent == null) {
    return 'Aucune obligation applicable à ce site pour le moment.';
  }
  return `${compliant} sur ${total} obligation${total > 1 ? 's' : ''} conforme${compliant > 1 ? 's' : ''}.`;
}

export function interpretRegOpsPenalty(findings = []) {
  const total = sumPenalties(findings);
  if (total <= 0) {
    return 'Aucune pénalité financière identifiée à ce jour.';
  }
  const atRisk = (findings || []).filter(
    (f) =>
      (f?.status === 'AT_RISK' || f?.status === 'NON_COMPLIANT') &&
      Number(f.estimated_penalty_eur) > 0
  );
  return `${formatFREur(total, 0)} cumulés sur ${atRisk.length}${NBSP}finding${atRisk.length > 1 ? 's' : ''} non conforme${atRisk.length > 1 ? 's' : ''}.`;
}

export function interpretRegOpsDeadline(nextDeadline) {
  const days = daysUntil(nextDeadline);
  if (days == null) return 'Aucune échéance planifiée à ce jour.';
  if (days < 0) {
    return `Échéance dépassée de ${Math.abs(days)}${NBSP}jour${Math.abs(days) > 1 ? 's' : ''} — régularisation urgente.`;
  }
  if (days <= 30) {
    return 'Échéance imminente · préparez le dépôt sans tarder.';
  }
  if (days <= 90) {
    return 'Fenêtre confortable · finalisez les pièces et validez la cohérence.';
  }
  return 'Échéance lointaine · aucune action urgente.';
}

// ─────────────────────────────────────────────────────────────────────────────
// Timeline events (findings ordered by deadline + severity)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Convertit findings + next_deadline → events SolTimeline.
 *
 * Ordre : legal_deadline ASC (plus proche en premier). Findings sans deadline
 * sont triés par severity DESC et placés en fin.
 *
 * Shape SolTimeline : { datetime, type, title, description, tone, deeplink, id }
 */
export function buildRegOpsTimelineEvents({ assessment, findings = [] } = {}) {
  const obligations = (findings || []).filter((f) => f?.category !== 'incentive');

  const withDeadline = obligations
    .filter((f) => f.legal_deadline)
    .sort((a, b) => new Date(a.legal_deadline) - new Date(b.legal_deadline));

  const SEVERITY_RANK = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
  const withoutDeadline = obligations
    .filter((f) => !f.legal_deadline)
    .sort((a, b) => (SEVERITY_RANK[a.severity] ?? 9) - (SEVERITY_RANK[b.severity] ?? 9));

  const events = [];
  for (const f of [...withDeadline, ...withoutDeadline]) {
    const regLabel = REG_LABELS[f.regulation] || f.regulation || 'Obligation';
    const ruleLabel = RULE_LABELS[f.rule_id]?.title_fr || f.rule_id || '';
    const title = ruleLabel ? `${regLabel} · ${ruleLabel}` : regLabel;
    events.push({
      id: `finding-${f.rule_id || Math.random().toString(36).slice(2)}`,
      datetime: f.legal_deadline ? formatDateFR(f.legal_deadline) : 'Sans échéance',
      type: REGOPS_SEVERITY_LABELS[f.severity] || 'Info',
      title,
      description: f.explanation || null,
      tone: toneFromSeverity(f.severity),
    });
  }

  // Jalon « prochaine échéance globale » si différente des findings déjà listés
  if (assessment?.next_deadline) {
    const already = events.some((e) => e.datetime === formatDateFR(assessment.next_deadline));
    if (!already) {
      events.unshift({
        id: 'next-deadline',
        datetime: formatDateFR(assessment.next_deadline),
        type: 'Échéance globale',
        title: 'Prochaine échéance réglementaire',
        description: interpretRegOpsDeadline(assessment.next_deadline),
        tone: (() => {
          const d = daysUntil(assessment.next_deadline);
          if (d != null && d < 0) return 'refuse';
          if (d != null && d <= 30) return 'attention';
          return 'afaire';
        })(),
      });
    }
  }

  return events;
}

// ─────────────────────────────────────────────────────────────────────────────
// Week-cards : variété garantie (1 attention + 1 afaire + 1 succes si possible)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * 3 week-cards RegOps avec variété de tags imposée.
 *   Card 1 'attention' : top action priority_score > 70 OU finding CRITICAL
 *   Card 2 'afaire'    : prochaine action priorité moyenne OU missing_data
 *   Card 3 'succes'    : pièce déposée / finding COMPLIANT récent OU fallback
 */
export function buildRegOpsWeekCards({ assessment, findings = [], onOpenAction } = {}) {
  const actions = (assessment?.actions || []).filter((a) => !a?.is_ai_suggestion);
  const sortedActions = [...actions].sort(
    (a, b) => (b.priority_score || 0) - (a.priority_score || 0)
  );

  const criticalFindings = (findings || []).filter(
    (f) => f?.severity === 'CRITICAL' || f?.severity === 'HIGH'
  );

  const cards = [];

  // Card 1 : attention (CRITICAL finding OU top action)
  if (criticalFindings.length > 0) {
    const f = criticalFindings[0];
    const regLabel = REG_LABELS[f.regulation] || f.regulation || 'Obligation';
    cards.push({
      id: `critical-${f.rule_id || 'top'}`,
      tagKind: 'attention',
      tagLabel: 'À regarder',
      title: RULE_LABELS[f.rule_id]?.title_fr || regLabel,
      body: f.explanation || 'Finding critique à traiter en priorité.',
      footerLeft: regLabel,
      footerRight: '⌘K',
      onClick: () => onOpenAction?.(f),
    });
  } else if (sortedActions[0]) {
    const a = sortedActions[0];
    cards.push({
      id: `action-top-${a.action_code || 'top'}`,
      tagKind: 'attention',
      tagLabel: 'À regarder',
      title: a.label || 'Action prioritaire',
      body: a.urgency_reason || 'Action prioritaire identifiée par le moteur déterministe.',
      footerLeft: `priorité ${a.priority_score || '—'}`,
      footerRight: a.owner_role || '—',
      onClick: () => onOpenAction?.(a),
    });
  } else {
    cards.push(businessErrorFallback('regops.no_findings', cards.length));
  }

  // Card 2 : afaire (action moyenne OU missing_data OU finding AT_RISK)
  const mediumAction = sortedActions.find(
    (a) => (a.priority_score || 0) <= 70 && (a.priority_score || 0) > 30
  );
  const hasMissing = Array.isArray(assessment?.missing_data) && assessment.missing_data.length > 0;
  if (hasMissing) {
    cards.push({
      id: 'missing-data',
      tagKind: 'afaire',
      tagLabel: 'À faire',
      title: `${assessment.missing_data.length}${NBSP}donnée${assessment.missing_data.length > 1 ? 's' : ''} manquante${assessment.missing_data.length > 1 ? 's' : ''}`,
      body: assessment.missing_data.slice(0, 2).join(' · '),
      footerLeft: 'complétez ces champs',
      footerRight: 'saisie requise',
      onClick: () => onOpenAction?.({ type: 'missing_data' }),
    });
  } else if (mediumAction) {
    cards.push({
      id: `action-medium-${mediumAction.action_code || 'mid'}`,
      tagKind: 'afaire',
      tagLabel: 'À faire',
      title: mediumAction.label || 'Action à planifier',
      body: mediumAction.urgency_reason || 'Action à traiter dans les prochaines semaines.',
      footerLeft: `priorité ${mediumAction.priority_score || '—'}`,
      footerRight: mediumAction.effort || 'effort non estimé',
      onClick: () => onOpenAction?.(mediumAction),
    });
  } else {
    // variant du fallback avec tagKind forcé à 'afaire' pour garantir variété
    const fb = businessErrorFallback('regops.evaluation_unavailable', cards.length);
    cards.push({ ...fb, tagKind: 'afaire', tagLabel: 'À faire' });
  }

  // Card 3 : succes (finding COMPLIANT récent OU fallback)
  const compliant = (findings || []).filter((f) => f?.status === 'COMPLIANT');
  if (compliant.length > 0) {
    const f = compliant[0];
    const regLabel = REG_LABELS[f.regulation] || f.regulation;
    cards.push({
      id: `ok-${f.rule_id || 'top'}`,
      tagKind: 'succes',
      tagLabel: 'Bonne nouvelle',
      title: `${regLabel} conforme`,
      body: f.explanation || `Obligation ${regLabel} validée par le moteur déterministe.`,
      footerLeft: 'audit confirmé',
      footerRight: '✓ Clean',
    });
  } else {
    // Variety guard : si on est déjà sur 2 fallbacks, ne pas tomber sur un 3e
    cards.push({
      id: 'no-success-yet',
      tagKind: 'succes',
      tagLabel: 'Bonne nouvelle',
      title: 'Évaluation déterministe active',
      body: "Le moteur RegOps surveille ce dossier en continu et vous alertera dès qu'une obligation est validée.",
      footerLeft: 'surveillance active',
      footerRight: '—',
    });
  }

  return cards.slice(0, 3);
}

// ─────────────────────────────────────────────────────────────────────────────
// Normalize + re-exports
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Normalise la réponse API RegAssessment (shape déjà propre côté backend).
 * Retourne null si input nul.
 */
export function normalizeAssessment(raw) {
  if (!raw) return null;
  return {
    site_id: raw.site_id,
    compliance_score: raw.compliance_score ?? null,
    global_status: raw.global_status || 'UNKNOWN',
    next_deadline: raw.next_deadline || null,
    findings: Array.isArray(raw.findings) ? raw.findings : [],
    actions: Array.isArray(raw.actions) ? raw.actions : [],
    missing_data: Array.isArray(raw.missing_data) ? raw.missing_data : [],
    deterministic_version: raw.deterministic_version || null,
  };
}

export { REG_LABELS, REGOPS_STATUS_LABELS, REGOPS_SEVERITY_LABELS, RULE_LABELS };
