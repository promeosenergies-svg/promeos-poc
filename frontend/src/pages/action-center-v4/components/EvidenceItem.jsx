import Badge from '../../../ui/Badge';
import { fmtNum } from '../../../utils/format';

import { EVIDENCE_STATUS_BADGE_VARIANTS, EVIDENCE_STATUS_LABELS, TAB_COPY } from '../constants';
import { formatDateTimeFR } from '../utils/date';
import { deriveEvidenceStatus } from '../utils/evidenceStatus';

/**
 * Taille de fichier formatée en unités FR via le formateur central `fmtNum`
 * (doctrine « formatters centralisés » — aucun arrondi inline en composant).
 */
function formatSize(bytes) {
  if (bytes < 1024) return fmtNum(bytes, 0, 'o');
  if (bytes < 1024 * 1024) return fmtNum(bytes / 1024, 0, 'Ko');
  return fmtNum(bytes / (1024 * 1024), 1, 'Mo');
}

/**
 * M2-5.3.B — Affichage d'une evidence (read-only).
 *
 * Status dérivé de verified_at + expires_at (jamais d'enum backend).
 * `storage_uri` / `validation_payload` ne sont pas exposés par l'API V4 —
 * ce composant ne lit aucun champ sensible (cf. test dédié).
 */
export function EvidenceItem({ evidence }) {
  const status = deriveEvidenceStatus(evidence);
  const label = EVIDENCE_STATUS_LABELS[status];
  const variant = EVIDENCE_STATUS_BADGE_VARIANTS[status];

  return (
    <article className="rounded border border-gray-200 p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-medium text-gray-900">
            {evidence.original_filename || '—'}
          </div>
          {evidence.description && (
            <div className="mt-0.5 text-xs text-gray-600">{evidence.description}</div>
          )}
        </div>
        <Badge status={variant}>{label}</Badge>
      </div>

      <div className="mt-2 space-y-0.5 text-xs text-gray-500">
        <div>
          {TAB_COPY.uploadedAtLabel} {formatDateTimeFR(evidence.uploaded_at)}
          {evidence.file_size_bytes != null && (
            <span> · {formatSize(evidence.file_size_bytes)}</span>
          )}
        </div>

        {status === 'verified' && evidence.verified_at && (
          <div>
            {TAB_COPY.verifiedAtLabel} {formatDateTimeFR(evidence.verified_at)}
            {evidence.expires_at && (
              <span>
                {' · '}
                {TAB_COPY.expiresAtLabel} {formatDateTimeFR(evidence.expires_at)}
              </span>
            )}
          </div>
        )}

        {status === 'expired' && evidence.expires_at && (
          <div>
            {TAB_COPY.expiresAtLabel} {formatDateTimeFR(evidence.expires_at)}
          </div>
        )}
      </div>
    </article>
  );
}
