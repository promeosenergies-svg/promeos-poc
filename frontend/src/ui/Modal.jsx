import { useEffect, useRef, useCallback } from 'react';
import { X } from 'lucide-react';

export default function Modal({ open, onClose, title, children, wide }) {
  const ref = useRef(null);

  useEffect(() => {
    if (open) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      // Auto-focus the modal container for keyboard nav
      requestAnimationFrame(() => ref.current?.focus());
      return () => { document.body.style.overflow = prev; };
    }
  }, [open]);

  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape' && open) onClose(); }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  // Basic focus trap: Tab cycles within modal
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
    <div className="fixed inset-0 z-[200] flex items-center justify-center" role="dialog" aria-modal="true" aria-label={title}>
      <div className="absolute inset-0 bg-black/25 backdrop-blur-[2px]" onClick={onClose} />
      <div
        ref={ref}
        tabIndex={-1}
        onKeyDown={handleKeyDown}
        className={`relative bg-white rounded-xl shadow-xl border border-gray-200 max-h-[85vh] overflow-y-auto
          focus:outline-none
          ${wide ? 'w-full max-w-2xl' : 'w-full max-w-lg'}`}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
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
        <div className="px-6 py-4">{children}</div>
      </div>
    </div>
  );
}
