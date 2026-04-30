/**
 * SolTooltip — Tooltip accessible WCAG 2.1 SC 1.4.13 (Phase 16.A · 30/04/2026).
 *
 * Remplace l'usage de `title=""` HTML natif (non visible au focus clavier sur
 * Chrome 120+ et silencieux au tap mobile) par un vrai popover focusable +
 * dismissable + hoverable conforme WCAG 1.4.13 "Content on Hover or Focus".
 *
 * Phase 16.bis.B (audit /simplify + /frontend-design sévère) :
 *  - palette warm cohérente (var(--sol-bg-paper) + ink-900) au lieu de
 *    dark UI corporate qui rompait la palette journal Sol
 *  - outline focus-visible explicite (la version v1 mettait outline:none =
 *    a11y régression silencieuse alors que le composant prétendait WCAG 1.4.13)
 *  - timer cleanup useEffect onUnmount (évite setState on unmounted component)
 *  - rôle ARIA cohérent : pas de `role="button"` (qui implique activation
 *    Enter/Space) — le déclencheur est juste tabbable + aria-describedby
 *
 * Comportement :
 *   - hover souris → tooltip visible (delay 80ms anti-flicker)
 *   - focus clavier (Tab) → tooltip visible, dismissable via ESC ou blur
 *   - tap mobile → toggle le tooltip (compatible iOS Safari/Android Chrome)
 *   - aria-describedby relie l'élément déclencheur au popover (lecteurs d'écran)
 *
 * Props :
 *   - content : ReactNode | string — texte ou markup du tooltip
 *   - children : ReactNode — élément déclencheur
 *   - placement : 'top' | 'bottom' (défaut top)
 *   - className : string optionnel sur le span déclencheur
 */
import { useEffect, useId, useRef, useState } from 'react';

const HOVER_DELAY_MS = 80;

export default function SolTooltip({ content, children, placement = 'top', className = '' }) {
  const [open, setOpen] = useState(false);
  const idTip = useId();
  const triggerRef = useRef(null);
  const timerRef = useRef(null);

  const show = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setOpen(true), HOVER_DELAY_MS);
  };
  const hide = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setOpen(false);
  };

  // Phase 16.bis.B — cleanup unmount : évite setState on unmounted (warning
  // React + leak) si l'utilisateur navigue alors qu'un timer 80ms est pending.
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  // ESC handler scoped : ne s'active que si CE tooltip est ouvert. Ferme
  // le tooltip ET reset le focus — ne propage pas au parent (les modals
  // gèrent leur propre ESC).
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        setOpen(false);
        triggerRef.current?.blur();
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open]);

  if (!content) return <span className={className}>{children}</span>;

  return (
    <span style={{ position: 'relative', display: 'inline-block' }}>
      <span
        ref={triggerRef}
        tabIndex={0}
        aria-describedby={open ? idTip : undefined}
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
        onClick={(e) => {
          // Tap mobile : toggle visibility. e.stopPropagation conservé seulement
          // pour éviter qu'un click cliché parent (ex: Link) ne s'active sur tap
          // d'acronyme — comportement attendu pour un déclencheur de tooltip.
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        className={`cursor-help ${className}`}
        style={{
          borderBottom: '1px dotted var(--sol-ink-400)',
          textDecoration: 'none',
        }}
        // Phase 16.bis.B — focus-visible CSS via :focus-visible pseudo-class.
        // On laisse l'outline natif du browser apparaître au focus clavier
        // (vs `outline:none` v1 qui violait WCAG 2.4.7).
      >
        {children}
      </span>
      {open && (
        <span
          id={idTip}
          role="tooltip"
          onMouseEnter={show}
          onMouseLeave={hide}
          style={{
            position: 'absolute',
            zIndex: 50,
            ...(placement === 'top' ? { bottom: 'calc(100% + 6px)' } : { top: 'calc(100% + 6px)' }),
            left: 0,
            maxWidth: '320px',
            minWidth: '200px',
            padding: '8px 10px',
            // Phase 16.bis.B — palette warm cohérente Sol journal :
            // fond paper subtil + texte ink-900 + border ink-300 + shadow doux.
            // Avant : ink-900 fond + paper texte = palette dark UI qui rompait
            // l'aesthetic journal v2 (audit /frontend-design P0).
            background: 'var(--sol-bg-paper)',
            color: 'var(--sol-ink-900)',
            border: '0.5px solid var(--sol-ink-300)',
            borderRadius: 6,
            fontSize: 12,
            lineHeight: 1.45,
            fontFamily: 'var(--sol-font-body)',
            boxShadow: '0 6px 16px rgba(15, 23, 42, 0.10)',
            pointerEvents: 'auto',
            whiteSpace: 'normal',
            textTransform: 'none',
            letterSpacing: 0,
            fontWeight: 400,
          }}
        >
          {content}
        </span>
      )}
    </span>
  );
}
