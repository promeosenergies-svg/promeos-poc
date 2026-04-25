/**
 * PROMEOS — SolToast
 *
 * Toast Sol-themed pour feedback bref (snooze, confirmation, info).
 * Remplace window.alert() qui sonne amateur en démo (audit Marie).
 *
 * Usage :
 *   const [toast, setToast] = useState(null);
 *   setToast({ message: '...', kind: 'info' });
 *   return <SolToast toast={toast} onClose={() => setToast(null)} />
 */
import { useEffect } from 'react';
import { Check, Info, X } from 'lucide-react';

const KIND_STYLES = {
  info: {
    background: 'var(--sol-calme-bg, #ecfdf5)',
    color: 'var(--sol-calme-fg, #047857)',
    Icon: Info,
  },
  success: {
    background: 'var(--sol-calme-bg, #ecfdf5)',
    color: 'var(--sol-calme-fg, #047857)',
    Icon: Check,
  },
  warning: {
    background: 'var(--sol-attention-bg, #fef3c7)',
    color: 'var(--sol-attention-fg, #b45309)',
    Icon: Info,
  },
};

export default function SolToast({ toast, onClose, autoCloseMs = 3500 }) {
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => onClose && onClose(), autoCloseMs);
    return () => clearTimeout(timer);
  }, [toast, onClose, autoCloseMs]);

  if (!toast) return null;
  const style = KIND_STYLES[toast.kind || 'info'] || KIND_STYLES.info;
  const Icon = style.Icon;

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        position: 'fixed',
        bottom: 24,
        right: 24,
        zIndex: 9999,
        background: 'var(--sol-bg-paper)',
        border: '1px solid var(--sol-ink-200)',
        borderLeft: `3px solid ${style.color}`,
        borderRadius: 8,
        padding: '12px 16px',
        boxShadow: '0 4px 12px rgba(15, 23, 42, 0.12)',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        maxWidth: 420,
        animation: 'slideInRight 300ms cubic-bezier(0.16, 1, 0.3, 1) backwards',
      }}
    >
      <div
        style={{
          width: 32,
          height: 32,
          borderRadius: '50%',
          background: style.background,
          color: style.color,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        <Icon size={16} />
      </div>
      <div
        style={{
          fontSize: 13,
          color: 'var(--sol-ink-900)',
          fontFamily: 'var(--sol-font-body)',
          lineHeight: 1.4,
          flex: 1,
        }}
      >
        {toast.message}
      </div>
      <button
        type="button"
        onClick={onClose}
        style={{
          all: 'unset',
          cursor: 'pointer',
          color: 'var(--sol-ink-400)',
          padding: 12,
          minWidth: 44,
          minHeight: 44,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
        aria-label="Fermer"
      >
        <X size={14} aria-hidden="true" />
      </button>
    </div>
  );
}
