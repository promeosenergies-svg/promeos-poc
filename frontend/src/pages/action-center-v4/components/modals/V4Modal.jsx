import { useCallback, useEffect, useRef } from 'react';
import { X } from 'lucide-react';

/**
 * M2-5.11.A — Modal centré custom Sol (variante de `V4Drawer` pour les
 * dialogs de petite taille). Contourne `src/ui/Modal.jsx` legacy (titre
 * sans-serif Tailwind gris) pour porter la signature Sol sur les 5 modals
 * du drawer (LifecycleTransition / EvidenceUpload / EvidenceVerify /
 * BlockerAdd / BlockerResolve).
 *
 * Couvre `Modal.shared` + amélioration : header Sol Fraunces + footer
 * sticky avec gap natif + close button 28×28 Sol + backdrop tokenisé.
 * Largeur par défaut 480px (cohérent maquette modal § doctrine).
 *
 * A11y : `role=dialog aria-modal`, focus trap Tab, Escape → close, lock
 * body scroll, focus restauré au close (next render du parent).
 *
 * M2-6.C.1-reduit — ajout prop `variant` (Q36=A) :
 *   - `"default"` (fallback) : style standard Sol crème/brun (M2-5.11.A inchangé)
 *   - `"warning"` : border-top ambre `--sol-attention-line` pour signaler une
 *     action métier d'attention (ex. transition lifecycle vers `closed`). PAS
 *     destructif (Q30=C — closed préserve les preuves), juste « confirmation
 *     attentive » vs « danger irréversible ». Tokens existants `--sol-attention-*`
 *     réutilisés (palette Sol §3.2), pas de nouveau token créé.
 *
 * Ajout aussi `testId` (Q37=A) pour assertions Playwright sur le `data-testid`
 * + `data-variant` (assertion variant warning runtime).
 */
// M2-6.C.P2-cleanup P2-2 — ref-counter module-scoped pour empiler les modals
// simultanés sans race condition mount/unmount. Le pattern naïf
// `body.style.overflow = 'hidden'` puis `= prev` cassait si deux modals
// s'ouvraient en succession rapide : le second snapshote `prev = 'hidden'`
// (laissé par le premier), puis le premier se ferme et restaure '', et au
// final le second close laisse 'hidden' bloqué pour toujours. Compteur global
// + snapshot unique du style original (sur premier mount) résout proprement.
let openModalsCount = 0;
let bodyOverflowBeforeLock = '';

export function V4Modal({
  open,
  onClose,
  ariaLabel,
  title,
  children,
  footer,
  width = 480,
  variant = 'default',
  testId = 'v4-modal',
}) {
  const ref = useRef(null);

  // Lock body scroll (ref-counted) + focus initial dans le modal.
  useEffect(() => {
    if (!open) return undefined;
    if (openModalsCount === 0) {
      bodyOverflowBeforeLock = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
    }
    openModalsCount += 1;
    requestAnimationFrame(() => ref.current?.focus());
    return () => {
      openModalsCount -= 1;
      if (openModalsCount === 0) {
        document.body.style.overflow = bodyOverflowBeforeLock;
      }
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

  // Focus trap Tab — pattern V4Drawer.
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
      className="fixed inset-0 z-[200] flex items-center justify-center px-4"
      role="dialog"
      aria-modal="true"
      aria-label={ariaLabel || title}
      data-testid={testId}
      data-variant={variant}
    >
      <div
        className="absolute inset-0 animate-[fadeIn_0.2s_ease-out]"
        style={{ background: 'var(--sol-backdrop-overlay)' }}
        onClick={onClose}
        aria-hidden="true"
        data-testid={`${testId}-backdrop`}
      />

      <div
        ref={ref}
        tabIndex={-1}
        onKeyDown={handleKeyDown}
        className="relative flex max-h-[90vh] w-full flex-col rounded-[8px] focus:outline-none"
        style={{
          maxWidth: `${width}px`,
          background: 'var(--sol-bg-paper)',
          border: '1px solid var(--sol-rule)',
          // M2-6.C.1-reduit — variant warning (Q30=C/Q36=A) : border-top 3px ambre
          // `--sol-attention-line` pour signal attentif (vs destructif rouge).
          // L'ajout 3px en haut compense visuellement la border 1px standard
          // (la box-shadow `--sol-shadow-dropdown` absorbe le shift mineur).
          ...(variant === 'warning' ? { borderTop: '3px solid var(--sol-attention-line)' } : {}),
          boxShadow: 'var(--sol-shadow-dropdown)',
        }}
      >
        <header
          className="flex items-center justify-between px-5 py-3.5"
          style={{ borderBottom: '1px solid var(--sol-rule)' }}
        >
          <h2
            className="text-[15px] font-medium tracking-[-0.005em]"
            style={{
              fontFamily: 'var(--sol-font-display)',
              color: 'var(--sol-ink-900)',
            }}
          >
            {title}
          </h2>
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
        </header>

        <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>

        {footer && (
          <footer
            className="flex flex-wrap items-center justify-end gap-2 px-5 py-3"
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
