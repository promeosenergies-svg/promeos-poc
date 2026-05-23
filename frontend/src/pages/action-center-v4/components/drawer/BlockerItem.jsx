import { useCallback, useState } from 'react';

import {
  BLOCKERS_SINCE_COPY,
  BLOCKER_RESOLVE_COPY,
  BLOCKER_STATUS_LABELS,
  BLOCKER_TYPE_LABELS,
  TAB_COPY,
} from '../../constants';
import { daysSince, formatDateTimeFR } from '../../utils/date';
import { BlockerResolveModal } from '../modals/BlockerResolveModal';

/**
 * M2-5.3.B / M2-5.6 / M2-5.10.B — Card d'un blocker (restyle Sol).
 *
 * Chip blocker style maquette §8.4 lignes 463-478 : préfixe ⊘ + label MONO
 * + bg/border afaire (dashed) + « depuis X jours » dérivé client-side de
 * `added_at`. Le bouton « Résoudre » est rendu en chip Sol attention.
 *
 * Status dérivé de `resolved_at` (jamais d'enum backend).
 */

export function BlockerItem({ blocker, onResolveSuccess }) {
  const [modalOpen, setModalOpen] = useState(false);
  const handleOpenModal = useCallback(() => setModalOpen(true), []);
  const handleCloseModal = useCallback(() => setModalOpen(false), []);

  const isActive = !blocker.resolved_at;
  const statusLabel = BLOCKER_STATUS_LABELS[isActive ? 'active' : 'resolved'];
  const typeLabel = BLOCKER_TYPE_LABELS[blocker.blocker_type] || blocker.blocker_type;
  const days = daysSince(blocker.added_at);
  const daysText =
    days != null
      ? days === 1
        ? BLOCKERS_SINCE_COPY.sinceDaysSingular(days)
        : BLOCKERS_SINCE_COPY.sinceDaysPlural(days)
      : null;

  const palette = isActive
    ? {
        bg: 'var(--sol-afaire-bg)',
        color: 'var(--sol-afaire-fg)',
        border: 'var(--sol-afaire-line)',
      }
    : {
        bg: 'var(--sol-succes-bg)',
        color: 'var(--sol-succes-fg)',
        border: 'var(--sol-succes-line)',
      };

  return (
    <article
      className="rounded-[6px] border p-3"
      style={{
        background: 'var(--sol-bg-paper)',
        borderColor: 'var(--sol-rule)',
      }}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
          <span
            className="inline-flex items-center gap-1.5 rounded-[3px] border px-2.5 py-1 font-mono text-[10.5px] font-medium"
            style={{
              background: palette.bg,
              color: palette.color,
              borderColor: palette.border,
              borderStyle: 'dashed',
            }}
          >
            <span aria-hidden="true" className="opacity-85">
              ⊘
            </span>
            {typeLabel}
          </span>
          <span
            className="rounded-[2px] px-1.5 py-px font-mono text-[9.5px] font-semibold uppercase tracking-[0.14em]"
            style={{
              background: palette.bg,
              color: palette.color,
            }}
          >
            {statusLabel}
          </span>
        </div>
        {isActive && (
          <button
            type="button"
            onClick={handleOpenModal}
            className="inline-flex items-center rounded-[4px] border px-2.5 py-1 font-sans text-[11.5px] font-semibold cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--sol-ink-900)]"
            style={{
              background: 'var(--sol-bg-paper)',
              color: 'var(--sol-afaire-fg)',
              borderColor: 'var(--sol-afaire-line)',
            }}
          >
            {BLOCKER_RESOLVE_COPY.buttonResolve}
          </button>
        )}
      </div>

      {blocker.justification && (
        <p
          className="mt-2 text-[12.5px] leading-[1.5]"
          style={{
            fontFamily: 'var(--sol-font-body)',
            color: 'var(--sol-ink-700)',
          }}
        >
          {blocker.justification}
        </p>
      )}

      <div
        className="mt-2 flex flex-wrap items-baseline gap-x-2 font-mono text-[10px] tracking-[0.02em]"
        style={{ color: 'var(--sol-ink-500)' }}
      >
        {blocker.added_at && (
          <span>
            {TAB_COPY.reportedAtLabel} {formatDateTimeFR(blocker.added_at)}
          </span>
        )}
        {daysText && isActive && (
          <span aria-hidden={false}>
            ·{' '}
            <span style={{ fontStyle: 'italic', fontFamily: 'var(--sol-font-display)' }}>
              {BLOCKERS_SINCE_COPY.prefix} {daysText}
            </span>
          </span>
        )}
        {blocker.resolved_at && (
          <span>
            · {TAB_COPY.resolvedAtLabel} {formatDateTimeFR(blocker.resolved_at)}
          </span>
        )}
      </div>

      {modalOpen && (
        <BlockerResolveModal
          open
          onClose={handleCloseModal}
          blockerId={blocker.id}
          onSuccess={onResolveSuccess}
        />
      )}
    </article>
  );
}
