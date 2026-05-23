import { useCallback, useRef, useState } from 'react';

import Input from '../../../../ui/Input';
import { useToast } from '../../../../ui/ToastProvider';

import { useUploadEvidence } from '../../../../hooks/v4';
import { UPLOAD_COPY } from '../../constants';
import { classifyError, toastMessageForError } from '../../utils/errorClassifier';
import { ACCEPTED_MIME_TYPES, validateEvidenceFile } from '../../utils/evidenceValidation';
import { formatFileSize } from '../../utils/fileSize';
import { SolButton } from '../shared/SolButton';
import { SolInlineError } from '../shared/SolInlineError';
import { V4Modal } from './V4Modal';

/**
 * M2-5.5 / M2-5.11.A — Modal d'upload d'une preuve (multipart POST).
 *
 * Réplique le pattern UI write figé M2-5.4 : pessimistic, erreur inline 422
 * corrigeable / toast infra + close, refetch au succès via `onSuccess`.
 *
 * Q1 : validation MIME côté client (defense in depth) — le backend reste
 * l'autorité (magic bytes + 10 Mo). Q2 : loading simple, pas de progress bar.
 *
 * M2-5.11.A — passage sur V4Modal + SolButton + SolInlineError.
 */
export function EvidenceUploadModal({ open, onClose, itemId, onSuccess }) {
  const [file, setFile] = useState(null);
  const [description, setDescription] = useState('');
  const [clientError, setClientError] = useState(null);
  const [inlineError, setInlineError] = useState(null);
  const fileInputRef = useRef(null);

  const { execute, loading, reset } = useUploadEvidence();
  const { toast } = useToast();

  const handleClose = useCallback(() => {
    setFile(null);
    setDescription('');
    setClientError(null);
    setInlineError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    reset();
    onClose();
  }, [onClose, reset]);

  const handleFileChange = useCallback((e) => {
    const selected = e.target.files?.[0] || null;
    setClientError(null);
    setInlineError(null);
    if (selected) {
      const errMsg = validateEvidenceFile(selected);
      if (errMsg) {
        setClientError(errMsg);
        setFile(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
        return;
      }
    }
    setFile(selected);
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!file) return;
    setInlineError(null);

    try {
      await execute(itemId, file, {
        description: description.trim() || undefined,
      });
      toast(UPLOAD_COPY.successToast, 'success');
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
  }, [file, description, itemId, execute, toast, onSuccess, handleClose]);

  const canSubmit = Boolean(file) && !clientError && !loading;

  return (
    <V4Modal
      open={open}
      onClose={handleClose}
      title={UPLOAD_COPY.modalTitle}
      footer={
        <>
          <SolButton variant="ghost" onClick={handleClose} disabled={loading}>
            {UPLOAD_COPY.cancelButton}
          </SolButton>
          <SolButton onClick={handleSubmit} disabled={!canSubmit} loading={loading}>
            {loading ? UPLOAD_COPY.submitLoading : UPLOAD_COPY.submitButton}
          </SolButton>
        </>
      }
    >
      <div className="space-y-4">
        <div>
          <label
            htmlFor="evidence-file-input"
            className="mb-1 block text-[12px] font-medium"
            style={{ color: 'var(--sol-ink-700)' }}
          >
            {UPLOAD_COPY.fieldFile}
          </label>
          <input
            id="evidence-file-input"
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_MIME_TYPES.join(',')}
            onChange={handleFileChange}
            // Styles natifs file input — tokens Sol via inline pour `file:*` :
            className="block w-full text-[12.5px] file:mr-3 file:cursor-pointer file:rounded-[4px] file:border-0 file:px-4 file:py-2 file:font-medium"
            style={{
              color: 'var(--sol-ink-700)',
              // file:* pseudo nécessite Tailwind ; tokens via background-attribute
              // composite : on garde la classe Tailwind file:bg-* mais via vars Sol
              // l'effet est plus pragmatique avec un wrapper.
            }}
          />
          <p
            className="mt-1 text-[11px] italic"
            style={{
              fontFamily: 'var(--sol-font-display)',
              color: 'var(--sol-ink-500)',
            }}
          >
            {UPLOAD_COPY.fieldFileHint}
          </p>
          {file && !clientError && (
            <p className="mt-1 font-mono text-[10.5px]" style={{ color: 'var(--sol-ink-700)' }}>
              {file.name} · {formatFileSize(file.size)}
            </p>
          )}
        </div>

        <Input
          label={UPLOAD_COPY.fieldDescription}
          aria-label={UPLOAD_COPY.fieldDescription}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          maxLength={500}
        />

        {/* Validation client MIME — couleur attention (warning, pas erreur). */}
        {clientError && (
          <div
            role="alert"
            className="rounded-[6px] border p-3 text-[12.5px]"
            style={{
              background: 'var(--sol-attention-bg)',
              borderColor: 'var(--sol-attention-line)',
              color: 'var(--sol-attention-fg)',
            }}
          >
            {clientError}
          </div>
        )}

        <SolInlineError error={inlineError} />
      </div>
    </V4Modal>
  );
}
