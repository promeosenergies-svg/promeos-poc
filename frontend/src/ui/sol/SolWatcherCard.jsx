/**
 * PROMEOS — SolWatcherCard (Lot 2 Phase 7, Pattern B prélude)
 *
 * Card compacte pour watcher réglementaire/marché : name + description +
 * bouton "Exécuter" avec feedback runResult inline (succès/erreur).
 * Utilisée dans le preludeSlot de SolListPage /watchers, à la place
 * d'un SolKpiRow (watchers = objets actionables, pas chiffres agrégés).
 *
 * Props :
 *   - name: string
 *   - description?: string
 *   - status?: 'idle' | 'running' | 'ok' | 'error'
 *   - resultMessage?: string
 *   - onRun?: () => void
 *   - runLabel?: string (default "Exécuter")
 */
import React from 'react';

const STATUS_FEEDBACK = {
  ok: { bg: 'var(--sol-succes-bg)', fg: 'var(--sol-succes-fg)' },
  error: { bg: 'var(--sol-refuse-bg)', fg: 'var(--sol-refuse-fg)' },
};

export default function SolWatcherCard({
  name,
  description,
  status = 'idle',
  resultMessage,
  onRun,
  runLabel = 'Exécuter',
}) {
  const feedback = STATUS_FEEDBACK[status];

  return (
    <div
      style={{
        background: 'var(--sol-bg-paper)',
        border: '1px solid var(--sol-ink-200)',
        borderRadius: 6,
        padding: '14px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        minHeight: 120,
      }}
    >
      <div>
        <h3
          style={{
            fontFamily: 'var(--sol-font-display)',
            fontSize: 15,
            fontWeight: 600,
            color: 'var(--sol-ink-900)',
            margin: 0,
            lineHeight: 1.25,
          }}
        >
          {name}
        </h3>
        {description && (
          <p
            style={{
              fontFamily: 'var(--sol-font-body)',
              fontSize: 13,
              color: 'var(--sol-ink-500)',
              margin: '4px 0 0',
              lineHeight: 1.4,
            }}
          >
            {description}
          </p>
        )}
      </div>

      {feedback && resultMessage && (
        <div
          role="status"
          style={{
            fontFamily: 'var(--sol-font-mono)',
            fontSize: 11,
            padding: '6px 10px',
            borderRadius: 4,
            background: feedback.bg,
            color: feedback.fg,
            fontWeight: 600,
          }}
        >
          {resultMessage}
        </div>
      )}

      <button
        type="button"
        onClick={onRun}
        disabled={status === 'running'}
        className="sol-btn sol-btn--secondary"
        style={{
          fontSize: 12,
          padding: '6px 12px',
          width: '100%',
          textAlign: 'center',
          opacity: status === 'running' ? 0.6 : 1,
          cursor: status === 'running' ? 'wait' : 'pointer',
        }}
      >
        {status === 'running' ? 'Exécution…' : runLabel}
      </button>
    </div>
  );
}
