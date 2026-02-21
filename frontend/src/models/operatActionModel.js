/**
 * PROMEOS V46 — OPERAT Issue → Action PROMEOS (logique pure, aucun import React)
 *
 * Transforme une issue OPERAT (controles V2) en payload ActionCreate
 * compatible avec POST /api/actions + deep-link fallback.
 *
 * Dedup via idempotency_key: operat-{efa_id}-{year}-{issue_code}
 *
 * Exports:
 *   buildOperatActionKey(params)     → cle de dedup stable
 *   buildOperatActionPayload(params) → ActionCreate-compatible payload
 *   buildOperatActionDeepLink(payload) → URL string pour navigation
 *   OPERAT_DUE_DAYS                  → mapping severity → delai jours
 */

// ── Delai par severite ──────────────────────────────────────────────────────

export const OPERAT_DUE_DAYS = {
  critical: 14,
  high: 30,
  medium: 60,
  low: 90,
};

// ── Priority mapping (1=critique, 5=faible) ─────────────────────────────────

const SEVERITY_TO_PRIORITY = {
  critical: 1,
  high: 2,
  medium: 3,
  low: 4,
};

// ── Action key builder ──────────────────────────────────────────────────────

/**
 * Construit une cle de dedup stable pour une issue OPERAT.
 *
 * @param {{ efa_id: number|string, year: number|string, issue_code: string }} params
 * @returns {string} ex: "operat:42:2026:TERTIAIRE_NO_BUILDING"
 */
export function buildOperatActionKey({ efa_id, year, issue_code }) {
  const y = year || new Date().getFullYear();
  const code = issue_code || 'UNKNOWN';
  return `operat:${efa_id}:${y}:${code}`;
}

// ── Payload builder ─────────────────────────────────────────────────────────

/**
 * Construit un payload ActionCreate a partir d'une issue OPERAT.
 *
 * @param {{
 *   efa: { id: number, nom: string, site_id?: number },
 *   issue: { code: string, title_fr?: string, message_fr?: string, severity?: string,
 *            impact_fr?: string, action_fr?: string,
 *            proof_required?: { type?: string, label_fr?: string, owner_role?: string, deadline_hint?: string },
 *            proof_links?: string[] },
 *   year?: number,
 *   kb_open_url?: string,
 *   proof_type?: string,
 * }} params
 * @returns {object} ActionCreate-compatible payload (ou payload degradé si données manquantes)
 */
export function buildOperatActionPayload({ efa, issue, year, kb_open_url, proof_type }) {
  const y = year || new Date().getFullYear();

  // Gardes: payload degradé si données manquantes
  if (!efa || !issue) {
    return {
      title: 'OPERAT — Action à clarifier',
      source_type: 'insight',
      source_id: 'operat:unknown',
      severity: 'medium',
      rationale: 'Données insuffisantes pour qualifier cette action.',
      priority: 3,
      idempotency_key: `operat-unknown-${y}-unknown`,
    };
  }

  const severity = issue.severity || 'medium';
  const dueDays = OPERAT_DUE_DAYS[severity] || 60;
  const dueDate = new Date();
  dueDate.setDate(dueDate.getDate() + dueDays);
  const dueDateStr = dueDate.toISOString().slice(0, 10);

  const actionKey = buildOperatActionKey({ efa_id: efa.id, year: y, issue_code: issue.code });
  const titleFr = `OPERAT — ${issue.title_fr || issue.code}`;

  // Description FR: 3 bullets (constat, impact, prochaine etape)
  const bullets = [];
  bullets.push(`Constat : ${issue.message_fr || issue.code}`);
  if (issue.impact_fr) {
    bullets.push(`Impact : ${issue.impact_fr}`);
  } else {
    bullets.push(`Impact : Non-conformité OPERAT détectée sur l'EFA ${efa.nom || `#${efa.id}`}`);
  }
  if (issue.action_fr) {
    bullets.push(`Prochaine étape : ${issue.action_fr}`);
  } else if (issue.proof_required) {
    bullets.push(`Prochaine étape : Déposer la preuve "${issue.proof_required.label_fr || 'requise'}" dans la Mémobox`);
  } else {
    bullets.push('Prochaine étape : Corriger les données EFA et relancer les contrôles');
  }

  const efaUrl = `/conformite/tertiaire/efa/${efa.id}`;
  const anomaliesUrl = '/conformite/tertiaire/anomalies';

  // Build rationale with links
  const rationale = [
    ...bullets,
    '',
    `Fiche EFA : ${efaUrl}`,
    kb_open_url ? `Preuve Mémobox : ${kb_open_url}` : null,
    `Anomalies : ${anomaliesUrl}`,
  ].filter(Boolean).join('\n');

  return {
    title: titleFr,
    source_type: 'insight',
    source_id: actionKey,
    severity,
    rationale,
    due_date: dueDateStr,
    priority: SEVERITY_TO_PRIORITY[severity] || 3,
    idempotency_key: `operat-${efa.id}-${y}-${issue.code}`,
    site_id: efa.site_id || undefined,
    notes: issue.proof_required
      ? `Preuve attendue : ${issue.proof_required.label_fr || proof_type || '—'} (${issue.proof_required.owner_role || '—'})`
      : undefined,
    _meta: {
      domain: 'conformite/tertiaire-operat',
      efa_id: efa.id,
      year: y,
      issue_code: issue.code,
      proof_type: proof_type || issue.proof_required?.type || null,
      proof_required: issue.proof_required || null,
      kb_open_url: kb_open_url || null,
      efa_url: efaUrl,
      anomalies_url: anomaliesUrl,
    },
  };
}

// ── Deep-link fallback ──────────────────────────────────────────────────────

/**
 * Construit un deep-link vers la page Plan d'actions avec pre-filtre OPERAT.
 *
 * @param {object} payload — Payload issu de buildOperatActionPayload()
 * @returns {string} URL string pour navigation
 */
export function buildOperatActionDeepLink(payload) {
  if (!payload) return '/actions';

  const params = new URLSearchParams();
  params.set('source', 'operat');

  if (payload._meta?.efa_id) params.set('efa_id', String(payload._meta.efa_id));
  if (payload._meta?.issue_code) params.set('issue_code', payload._meta.issue_code);
  if (payload.severity) params.set('severity', payload.severity);

  return `/actions?${params.toString()}`;
}
