import { useCallback } from 'react';

import { useToast } from '../../../ui/ToastProvider';

import { useVerifyEvidence } from '../../../hooks/v4';
import { VERIFY_COPY } from '../constants';
import { classifyError, toastMessageForError } from '../utils/errorClassifier';
import { SolButton } from './SolButton';
import { V4Modal } from './V4Modal';

/**
 * M2-5.5 / M2-5.11.A — Confirm dialog de vérification d'une preuve.
 *
 * Q3 : simple confirmation, aucun champ expires_at (le backend pose le défaut
 * +90 jours). Toujours toast + close : un confirm dialog n'a pas de champ à
 * corriger — `EVIDENCE_ALREADY_VERIFIED` → toast warning (jaune) pour adoucir.
 *
 * M2-5.11.A — passage sur V4Modal + SolButton.
 */
export function EvidenceVerifyDialog({ open, onClose, evidenceId, onSuccess }) {
  const { execute, loading, reset } = useVerifyEvidence();
  const { toast } = useToast();

  const handleClose = useCallback(() => {
    reset();
    onClose();
  }, [onClose, reset]);

  const handleConfirm = useCallback(async () => {
    try {
      await execute(evidenceId, {}); // payload vide → backend pose expires_at +90j
      toast(VERIFY_COPY.successToast, 'success');
      onSuccess?.();
      handleClose();
    } catch (err) {
      const normalized = err.promeos || {
        message: err.message,
        status: err.response?.status,
      };
      // Confirm dialog : aucune correction possible → toast + close dans tous
      // les cas. Le code corrigeable EVIDENCE_ALREADY_VERIFIED est juste
      // adouci en warning.
      const tone = classifyError(normalized) === 'inline' ? 'warning' : 'error';
      toast(toastMessageForError(normalized), tone);
      handleClose();
    }
  }, [evidenceId, execute, toast, onSuccess, handleClose]);

  return (
    <V4Modal
      open={open}
      onClose={handleClose}
      title={VERIFY_COPY.dialogTitle}
      footer={
        <>
          <SolButton variant="ghost" onClick={handleClose} disabled={loading}>
            {VERIFY_COPY.cancelButton}
          </SolButton>
          <SolButton onClick={handleConfirm} disabled={loading} loading={loading}>
            {loading ? VERIFY_COPY.confirmLoading : VERIFY_COPY.confirmButton}
          </SolButton>
        </>
      }
    >
      <p className="text-[13px] leading-[1.5]" style={{ color: 'var(--sol-ink-700)' }}>
        {VERIFY_COPY.dialogMessage}
      </p>
    </V4Modal>
  );
}
