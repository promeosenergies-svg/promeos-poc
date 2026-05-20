import { useCallback, useEffect, useRef } from 'react';
import { X } from 'lucide-react';

/**
 * M2-5.10.B.bis — Drawer custom Sol (maquette §8.4 lignes 79-93 + 640-648).
 *
 * Contourne `src/ui/Drawer.jsx` (legacy générique Tailwind sans-serif) qui
 * cassait la signature Sol du drawer V4 (audit UI Sol P0-1) :
 * - **Largeur fixe 760px** (vs max-w-2xl=672px du wrapper — audit P0-2)
 * - **Header sticky Sol** : breadcrumb MONO + bouton close 28×28 Sol
 * - **Body scrollable** sans padding (les sections gèrent leur propre padding)
 * - **Footer sticky** fond `--sol-bg-canvas` distinct du body papier (audit P0-3)
 *
 * Le footer reste optionnel ; si non fourni, le body occupe toute la place.
 *
 * A11y : `role=dialog aria-modal`, focus trap Tab, Escape → close, lock body
 * scroll, focus restauré au close (next render du parent).
 */
export function V4Drawer({
  open,
  onClose,
  ariaLabel,
  breadcrumb,
  headerActions,
  footer,
  children,
  width = 760,
}) {
  const ref = useRef(null);

  // Lock body scroll + focus initial dans le drawer.
  useEffect(() => {
    if (!open) return undefined;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    requestAnimationFrame(() => ref.current?.focus());
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  // Escape → close.
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  // Focus trap Tab — pattern repris du Drawer shared (cohérent).
  const handleKeyDown = useCallback((e) => {
    if (e.key !== 'Tab' || !ref.current) return;
    const focusable = ref.current.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }, []);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[200] flex"
      role="dialog"
      aria-modal="true"
      aria-label={ariaLabel}
    >
      {/* Backdrop atténué — maquette opacity 0.45 (token Sol M2-5.10.bis). */}
      <div
        className="absolute inset-0 animate-[fadeIn_0.2s_ease-out]"
        style={{ background: 'var(--sol-backdrop-overlay)' }}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel Sol. */}
      <div
        ref={ref}
        tabIndex={-1}
        onKeyDown={handleKeyDown}
        className="absolute right-0 top-0 flex h-full max-w-full animate-[slideInRight_0.25s_ease-out] flex-col focus:outline-none"
        style={{
          width: `${width}px`,
          background: 'var(--sol-bg-paper)',
          borderLeft: '1px solid var(--sol-rule)',
          boxShadow: 'var(--sol-shadow-drawer)',
        }}
      >
        {/* Header sticky Sol — breadcrumb + close + headerActions (slot). */}
        <header
          className="flex-shrink-0 px-[26px] pb-3 pt-3.5"
          style={{
            background: 'var(--sol-bg-canvas)',
            borderBottom: '1px solid var(--sol-rule)',
          }}
        >
          <div className="mb-2.5 flex items-center gap-2.5">
            <div className="min-w-0 flex-1">{breadcrumb}</div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Fermer"
              className="inline-flex h-7 w-7 items-center justify-center rounded-[6px] border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--sol-ink-900)]"
              style={{
                background: 'var(--sol-bg-paper)',
                borderColor: 'var(--sol-rule)',
                color: 'var(--sol-ink-500)',
              }}
            >
              <X size={14} aria-hidden="true" />
            </button>
          </div>
          {headerActions}
        </header>

        {/* Body scrollable — les sections enfantes gèrent leur padding. */}
        <div className="min-h-0 flex-1 overflow-y-auto px-[26px] pb-6 pt-4">{children}</div>

        {/* Footer sticky Sol optionnel. */}
        {footer && (
          <footer
            className="flex-shrink-0 px-[26px] py-3"
            style={{
              background: 'var(--sol-bg-canvas)',
              borderTop: '1px solid var(--sol-rule)',
            }}
          >
            {footer}
          </footer>
        )}
      </div>
    </div>
  );
}
