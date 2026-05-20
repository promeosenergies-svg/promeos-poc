import { useCallback, useState } from 'react';

import { useToast } from '../../../ui/ToastProvider';

import { useAssignOwner } from '../../../hooks/v4';
import { ASSIGN_OWNER_COPY, UUID_PATTERN } from '../constants';
import { classifyError, toastMessageForError } from '../utils/errorClassifier';
import { SolButton } from './SolButton';
import { SolInlineError } from './SolInlineError';
import { V4Modal } from './V4Modal';

/**
 * M2-5.11.E — Modal d'assignation d'un pilote (PATCH /items/{id}/assign).
 *
 * Deux modes :
 * - Assigner (champ vides) : on saisit `owner_display_name` + `owner_id` UUID.
 * - Réassigner (item déjà assigné) : champs pré-remplis depuis l'item courant,
 *   l'utilisateur ajuste.
 *
 * Le bouton « Désassigner » envoie `{ owner_id: null }` — le BE force aussi
 * `owner_display_name = null` (pas de label fantôme). Validations client-side
 * légères : UUID syntaxique + display_name requis si UUID saisi. La validation
 * stricte (UUID format, longueur 120) est faite par le BE Pydantic.
 *
 * Pattern UI cohérent BlockerResolveModal / EvidenceUploadModal (M2-5.11.A) :
 * V4Modal + SolButton + SolInlineError + textarea/input tokens Sol.
 */
export function AssignOwnerModal({ open, onClose, item, onSuccess }) {
  const isCurrentlyAssigned = Boolean(item?.owner_id);
  const [displayName, setDisplayName] = useState(item?.owner_display_name || '');
  const [ownerId, setOwnerId] = useState(item?.owner_id || '');
  const [clientError, setClientError] = useState(null);

  const { execute, loading, reset } = useAssignOwner();
  const { toast } = useToast();

  const handleClose = useCallback(() => {
    setClientError(null);
    reset();
    onClose();
  }, [onClose, reset]);

  const handleSubmit = useCallback(
    async (mode) => {
      setClientError(null);
      let payload;
      if (mode === 'unassign') {
        // Désassigner : owner_id null, owner_display_name ignoré par le BE.
        payload = { owner_id: null };
      } else {
        const trimmedName = displayName.trim();
        const trimmedId = ownerId.trim();
        // Validation locale : UUID requis ET display_name requis.
        if (!UUID_PATTERN.test(trimmedId)) {
          setClientError({ message: ASSIGN_OWNER_COPY.validationOwnerIdInvalid });
          return;
        }
        if (!trimmedName) {
          setClientError({ message: ASSIGN_OWNER_COPY.validationDisplayNameRequired });
          return;
        }
        payload = { owner_id: trimmedId, owner_display_name: trimmedName };
      }

      try {
        await execute(item.id, payload);
        toast(
          mode === 'unassign'
            ? ASSIGN_OWNER_COPY.successUnassignedToast
            : ASSIGN_OWNER_COPY.successAssignedToast,
          'success'
        );
        onSuccess?.();
        handleClose();
      } catch (err) {
        const normalized = err.promeos || {
          message: err.message,
          status: err.response?.status,
        };
        // M2-5.11.G : si l'erreur est classée « inline » (validation Pydantic
        // 422, conflit récupérable…), on garde la modal ouverte et on rend
        // l'erreur via SolInlineError — l'utilisateur peut corriger le champ.
        // Sinon (5xx, auth, réseau) on ferme + toast — pas de récupération.
        if (classifyError(normalized) === 'inline') {
          setClientError({ message: toastMessageForError(normalized) });
          return;
        }
        toast(toastMessageForError(normalized), 'error');
        handleClose();
      }
    },
    [displayName, ownerId, item, execute, toast, onSuccess, handleClose]
  );

  return (
    <V4Modal
      open={open}
      onClose={handleClose}
      title={ASSIGN_OWNER_COPY.modalTitle}
      footer={
        <>
          <SolButton variant="ghost" onClick={handleClose} disabled={loading}>
            {ASSIGN_OWNER_COPY.cancelButton}
          </SolButton>
          {/* Désassigner : visible uniquement si l'item est déjà assigné — sinon
              c'est un bouton qui ne fait rien (anti UX confusion). */}
          {isCurrentlyAssigned && (
            <SolButton
              variant="danger"
              onClick={() => handleSubmit('unassign')}
              disabled={loading}
              loading={loading}
              title={ASSIGN_OWNER_COPY.unassignConfirmHint}
            >
              {ASSIGN_OWNER_COPY.unassignButton}
            </SolButton>
          )}
          <SolButton onClick={() => handleSubmit('assign')} disabled={loading} loading={loading}>
            {loading
              ? ASSIGN_OWNER_COPY.submitLoading
              : isCurrentlyAssigned
                ? ASSIGN_OWNER_COPY.submitReassignButton
                : ASSIGN_OWNER_COPY.submitButton}
          </SolButton>
        </>
      }
    >
      <div className="space-y-4">
        {clientError && <SolInlineError error={clientError} />}

        <div>
          <label
            htmlFor="assign-owner-display-name"
            className="mb-1 block text-[12px] font-medium"
            style={{ color: 'var(--sol-ink-700)' }}
          >
            {ASSIGN_OWNER_COPY.fieldDisplayName}
          </label>
          {/* M2-5.11.H : `aria-describedby` lie l'input à son hint italique
              en-dessous — les lecteurs d'écran annoncent maintenant la copy
              guidance après le label (WCAG 2.1 AA / AAA bonus). */}
          <input
            id="assign-owner-display-name"
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            maxLength={120}
            aria-describedby="assign-owner-display-name-hint"
            className="w-full rounded-[6px] border p-2 text-[13px] focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--sol-ink-900)]"
            style={{
              background: 'var(--sol-bg-paper)',
              borderColor: 'var(--sol-ink-300)',
              color: 'var(--sol-ink-900)',
              fontFamily: 'var(--sol-font-body)',
            }}
          />
          <p
            id="assign-owner-display-name-hint"
            className="mt-1 text-[11px] italic"
            style={{
              fontFamily: 'var(--sol-font-display)',
              color: 'var(--sol-ink-500)',
            }}
          >
            {ASSIGN_OWNER_COPY.fieldDisplayNameHint}
          </p>
        </div>

        <div>
          <label
            htmlFor="assign-owner-id"
            className="mb-1 block text-[12px] font-medium"
            style={{ color: 'var(--sol-ink-700)' }}
          >
            {ASSIGN_OWNER_COPY.fieldOwnerId}
          </label>
          <input
            id="assign-owner-id"
            type="text"
            value={ownerId}
            onChange={(e) => setOwnerId(e.target.value)}
            placeholder="12345678-1234-1234-1234-123456789012"
            aria-describedby="assign-owner-id-hint"
            className="w-full rounded-[6px] border p-2 font-mono text-[12.5px] focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--sol-ink-900)]"
            style={{
              background: 'var(--sol-bg-paper)',
              borderColor: 'var(--sol-ink-300)',
              color: 'var(--sol-ink-900)',
            }}
          />
          <p
            id="assign-owner-id-hint"
            className="mt-1 text-[11px] italic"
            style={{
              fontFamily: 'var(--sol-font-display)',
              color: 'var(--sol-ink-500)',
            }}
          >
            {ASSIGN_OWNER_COPY.fieldOwnerIdHint}
          </p>
        </div>
      </div>
    </V4Modal>
  );
}
