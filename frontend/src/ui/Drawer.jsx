/**
 * PROMEOS Design System — Drawer
 * Slide-over panel from the right (or left). Reuses Modal's patterns.
 */
import { useEffect, useRef, useCallback } from 'react';
import { X } from 'lucide-react';

export default function Drawer({
  open,
  onClose,
  title,
  children,
  side = 'right',
  wide,
  className = '',
  noPadding = false,
  id,
  ariaLabel,
}) {
  const ref = useRef(null);

  useEffect(() => {
    if (open) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      requestAnimationFrame(() => ref.current?.focus());
      return () => {
        document.body.style.overflow = prev;
      };
    }
  }, [open]);

  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape' && open) onClose();
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose]);

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

  const sideClass = side === 'left' ? 'left-0' : 'right-0';
  const widthClass = wide ? 'w-full max-w-2xl' : 'w-full max-w-md';

  return (
    <div
      className="fixed inset-0 z-[200] flex"
      role="dialog"
      aria-modal="true"
      aria-label={ariaLabel || title}
    >
      <div
        className="absolute inset-0 bg-black/40 animate-[fadeIn_0.2s_ease-out]"
        onClick={onClose}
      />
      <div
        ref={ref}
        id={id}
        tabIndex={-1}
        onKeyDown={handleKeyDown}
        className={`absolute ${sideClass} top-0 h-full ${widthClass} bg-white shadow-xl ${side === 'left' ? 'border-r' : 'border-l'} border-gray-200
          flex flex-col focus:outline-none ${side === 'left' ? 'animate-[slideInLeft_0.25s_ease-out]' : 'animate-[slideInRight_0.25s_ease-out]'} ${className}`}
      >
        {/* Header rendu seulement si title (évite double h2 quand children
            gère son propre titre, cas SolPanel mobile). Close button toujours
            accessible via overlay click + Escape (4 patterns a11y core). */}
        {title ? (
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
            <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition
                focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              aria-label="Fermer"
            >
              <X size={18} />
            </button>
          </div>
        ) : (
          // Pas de header — bouton Fermer seul, absolute top-right, pour
          // drawers avec titre interne (SolPanel a son propre <h2>).
          <button
            type="button"
            onClick={onClose}
            className="absolute top-2 right-2 z-10 p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            aria-label="Fermer"
          >
            <X size={18} />
          </button>
        )}
        <div className={`flex-1 min-h-0 ${noPadding ? '' : 'overflow-y-auto px-6 py-4'}`}>
          {children}
        </div>
      </div>
    </div>
  );
}
