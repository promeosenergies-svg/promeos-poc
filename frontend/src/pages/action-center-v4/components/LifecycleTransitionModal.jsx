import { useCallback, useMemo, useState } from 'react';

import Input from '../../../ui/Input';
import Select from '../../../ui/Select';
import { useToast } from '../../../ui/ToastProvider';

import { useTransitionLifecycle } from '../../../hooks/v4';
import { CLOSURE_REASON_LABELS, LIFECYCLE_LABELS, TRANSITION_COPY } from '../constants';
import { classifyError, toastMessageForError } from '../utils/errorClassifier';
import {
  USER_FACING_CLOSURE_REASONS,
  getAvailableTransitions,
  transitionRequiresReason,
} from '../utils/lifecycleTransitions';
import { SolButton } from './SolButton';
import { SolInlineError } from './SolInlineError';
import { V4Modal } from './V4Modal';

/**
 * M2-5.4 / M2-5.11.A — Modal de transition lifecycle (premier write V4).
 *
 * Validation client : options new_state filtrées selon la matrice de
 * transitions depuis currentState, closure_reason affiché si requis. Le
 * backend reste l'autorité finale (re-validation). Pessimistic : on attend
 * la réponse serveur, le parent refetch au succès via `onSuccess`.
 *
 * Erreurs : 422 corrigeable → inline (modal reste ouverte) ; sinon → toast
 * + fermeture (cf. utils/errorClassifier).
 *
 * M2-5.11.A — passage sur V4Modal + SolButton + SolInlineError (audit UI
 * Sol cross-pages P1 : modal Tailwind dans drawer Sol = anti-pattern §6.1).
 */
export function LifecycleTransitionModal({ open, onClose, itemId, currentState, onSuccess }) {
  const [newState, setNewState] = useState('');
  const [closureReason, setClosureReason] = useState('');
  const [comment, setComment] = useState('');
  const [inlineError, setInlineError] = useState(null);

  const { execute, loading, reset } = useTransitionLifecycle();
  const { toast } = useToast();

  const availableTransitions = useMemo(() => getAvailableTransitions(currentState), [currentState]);

  const requiresReason = newState ? transitionRequiresReason(currentState, newState) : false;

  const handleClose = useCallback(() => {
    setNewState('');
    setClosureReason('');
    setComment('');
    setInlineError(null);
    reset();
    onClose();
  }, [onClose, reset]);

  const handleSubmit = useCallback(async () => {
    if (!newState) return;
    setInlineError(null);

    const payload = { new_state: newState };
    if (requiresReason) payload.closure_reason = closureReason;
    if (comment.trim()) payload.comment = comment.trim();

    try {
      await execute(itemId, payload);
      toast(TRANSITION_COPY.successToast, 'success');
      onSuccess?.();
      handleClose();
    } catch (err) {
      const normalized = err.promeos || {
        message: err.message,
        status: err.response?.status,
      };
      if (classifyError(normalized) === 'inline') {
        setInlineError(normalized);
      } else {
        toast(toastMessageForError(normalized), 'error');
        handleClose();
      }
    }
  }, [
    newState,
    closureReason,
    comment,
    requiresReason,
    itemId,
    execute,
    toast,
    onSuccess,
    handleClose,
  ]);

  const canSubmit = Boolean(newState) && (!requiresReason || Boolean(closureReason)) && !loading;

  if (availableTransitions.length === 0) {
    return (
      <V4Modal
        open={open}
        onClose={handleClose}
        title={TRANSITION_COPY.modalTitle}
        footer={
          <SolButton variant="ghost" onClick={handleClose}>
            {TRANSITION_COPY.cancelButton}
          </SolButton>
        }
      >
        <p className="text-[13px]" style={{ color: 'var(--sol-ink-700)' }}>
          {TRANSITION_COPY.noTransitionsAvailable}
        </p>
      </V4Modal>
    );
  }

  return (
    <V4Modal
      open={open}
      onClose={handleClose}
      title={TRANSITION_COPY.modalTitle}
      footer={
        <>
          <SolButton variant="ghost" onClick={handleClose} disabled={loading}>
            {TRANSITION_COPY.cancelButton}
          </SolButton>
          <SolButton onClick={handleSubmit} disabled={!canSubmit} loading={loading}>
            {loading ? TRANSITION_COPY.submitLoading : TRANSITION_COPY.submitButton}
          </SolButton>
        </>
      }
    >
      <div className="space-y-4">
        <Select
          label={TRANSITION_COPY.fieldNewState}
          aria-label={TRANSITION_COPY.fieldNewState}
          value={newState}
          onChange={(e) => setNewState(e.target.value)}
          options={[
            { value: '', label: TRANSITION_COPY.selectPlaceholder },
            ...availableTransitions.map(({ to }) => ({
              value: to,
              label: LIFECYCLE_LABELS[to],
            })),
          ]}
        />

        {requiresReason && (
          <Select
            label={TRANSITION_COPY.fieldClosureReason}
            aria-label={TRANSITION_COPY.fieldClosureReason}
            value={closureReason}
            onChange={(e) => setClosureReason(e.target.value)}
            options={[
              { value: '', label: TRANSITION_COPY.closurePlaceholder },
              ...USER_FACING_CLOSURE_REASONS.map((r) => ({
                value: r,
                label: CLOSURE_REASON_LABELS[r],
              })),
            ]}
          />
        )}

        <Input
          label={TRANSITION_COPY.fieldComment}
          aria-label={TRANSITION_COPY.fieldComment}
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          maxLength={500}
        />

        <SolInlineError error={inlineError} />
      </div>
    </V4Modal>
  );
}
