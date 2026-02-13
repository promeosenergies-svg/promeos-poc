/**
 * PROMEOS Design System — Drawer
 * Slide-over panel from the right (or left). Reuses Modal's patterns.
 */
import { useEffect, useRef, useCallback } from 'react';
import { X } from 'lucide-react';

export default function Drawer({ open, onClose, title, children, side = 'right', wide, className = '' }) {
  const ref = useRef(null);

  useEffect(() => {
    if (open) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      requestAnimationFrame(() => ref.current?.focus());
      return () => { document.body.style.overflow = prev; };
    }
  }, [open]);

  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape' && open) onClose(); }
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
    <div className="fixed inset-0 z-50 flex" role="dialog" aria-modal="true" aria-label={title}>
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div
        ref={ref}
        tabIndex={-1}
        onKeyDown={handleKeyDown}
        className={`absolute ${sideClass} top-0 h-full ${widthClass} bg-white shadow-xl border-l border-gray-200
          flex flex-col focus:outline-none ${className}`}
      >
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
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {children}
        </div>
      </div>
    </div>
  );
}
