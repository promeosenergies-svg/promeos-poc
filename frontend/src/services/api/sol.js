/**
 * PROMEOS Sol V1 API client.
 *
 * Endpoints côté backend : `backend/routes/sol.py`, `sol_audit.py`, `sol_policy.py`.
 * Les tokens HMAC et correlation_id sont gérés côté backend — le client
 * envoie juste les payloads JSON.
 */
import api from './core';

// ── Propose / Preview / Confirm / Cancel cycle ──

/**
 * Propose une action agentique. Retourne { type: 'plan', plan } ou
 * { type: 'refused', refused }.
 */
export const proposeAction = (intent, params = {}, scopeSiteId = null) =>
  api
    .post('/sol/propose', {
      intent,
      params,
      scope_site_id: scopeSiteId,
    })
    .then((r) => r.data);

/**
 * Preview un plan et obtient un confirmation_token HMAC TTL 5 min.
 */
export const previewAction = (correlationId, intent, params = {}) =>
  api
    .post('/sol/preview', {
      correlation_id: correlationId,
      intent,
      params,
    })
    .then((r) => r.data);

/**
 * Confirm et schedule un plan (202 Accepted avec pending_action_id +
 * cancellation_token).
 */
export const confirmAction = (correlationId, confirmationToken, intent, params = {}, secondValidatorUserId = null) =>
  api
    .post('/sol/confirm', {
      correlation_id: correlationId,
      confirmation_token: confirmationToken,
      intent,
      params,
      second_validator_user_id: secondValidatorUserId,
    })
    .then((r) => r.data);

/**
 * Annule via cancellation_token URL-safe (accepté sans JWT — one-click
 * depuis email). Si l'utilisateur est authentifié, son id est tracé
 * dans cancelled_by côté serveur.
 */
export const cancelAction = (cancellationToken) =>
  api.post('/sol/cancel', { cancellation_token: cancellationToken }).then((r) => r.data);

// ── Pending queue ──

export const listPendingActions = (status = null) => {
  const params = status ? { status } : {};
  return api.get('/sol/pending', { params }).then((r) => r.data);
};

// ── Audit trail ──

export const listAuditTrail = (params = {}) =>
  api.get('/sol/audit', { params }).then((r) => r.data);

export const exportAuditCSV = (params = {}) =>
  api.get('/sol/audit/export', { params, responseType: 'blob' });

// ── Org policy (admin) ──

export const getSolPolicy = () => api.get('/sol/policy').then((r) => r.data);

export const updateSolPolicy = (payload) => api.put('/sol/policy', payload).then((r) => r.data);

// ── Constantes réutilisées par les composants Sol ──

export const SOL_INTENT_KINDS = Object.freeze({
  INVOICE_DISPUTE: 'invoice_dispute',
  EXEC_REPORT: 'exec_report',
  DT_ACTION_PLAN: 'dt_action_plan',
  AO_BUILDER: 'ao_builder',
  OPERAT_BUILDER: 'operat_builder',
  CONSULTATIVE_ONLY: 'consultative_only',
  DUMMY_NOOP: 'dummy_noop',
});

export const SOL_ACTION_PHASES = Object.freeze({
  PROPOSED: 'proposed',
  PREVIEWED: 'previewed',
  CONFIRMED: 'confirmed',
  SCHEDULED: 'scheduled',
  EXECUTED: 'executed',
  CANCELLED: 'cancelled',
  REVERTED: 'reverted',
  REFUSED: 'refused',
});
