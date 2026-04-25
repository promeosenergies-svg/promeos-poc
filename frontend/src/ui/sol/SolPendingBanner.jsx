/**
 * PROMEOS — SolPendingBanner
 * Bannière "Sol enverra le courrier dans 23 h 59 min" avec CTAs Annuler / Éditer.
 * Présentation pure. Le compte à rebours est calculé par le parent.
 */
import React from 'react';

export default function SolPendingBanner({
  message = 'Sol enverra le courrier',
  countdown,
  onCancel,
  onEdit,
  className = '',
}) {
  return (
    <div
      className={`sol-pending-banner ${className}`.trim()}
      style={{
        background: 'var(--sol-calme-bg)',
        border: '1px solid var(--sol-calme-fg)',
        borderRadius: 6,
        padding: '12px 16px',
        display: 'flex',
        alignItems: 'center',
        gap: 14,
        margin: '14px 0',
      }}
    >
      <span
        className="sol-pending-banner-msg"
        style={{ flex: 1, fontSize: 13, color: 'var(--sol-calme-fg)', lineHeight: 1.4 }}
      >
        {message}
        {countdown && (
          <>
            {' '}
            dans{' '}
            <span
              className="sol-pending-banner-countdown"
              style={{ fontFamily: 'var(--sol-font-mono)', fontWeight: 600 }}
            >
              {countdown}
            </span>
          </>
        )}
      </span>
      {onEdit && (
        <button
          type="button"
          onClick={onEdit}
          className="sol-btn sol-btn--secondary"
          style={{ fontSize: 12, padding: '5px 10px' }}
        >
          Éditer
        </button>
      )}
      {onCancel && (
        <button
          type="button"
          onClick={onCancel}
          className="sol-btn sol-btn--ghost"
          style={{ fontSize: 12, padding: '5px 10px', color: 'var(--sol-calme-fg)' }}
        >
          Annuler
        </button>
      )}
    </div>
  );
}
