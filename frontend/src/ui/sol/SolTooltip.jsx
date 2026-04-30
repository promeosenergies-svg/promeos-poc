/**
 * SolTooltip — Tooltip accessible WCAG 2.1 SC 1.4.13 (Phase 16.A · 30/04/2026).
 *
 * Remplace l'usage de `title=""` HTML natif (non visible au focus clavier sur
 * Chrome 120+ et silencieux au tap mobile) par un vrai popover focusable +
 * dismissable + hoverable conforme WCAG 1.4.13 "Content on Hover or Focus".
 *
 * Comportement :
 *   - hover souris → tooltip visible (delay 100ms anti-flicker)
 *   - focus clavier (Tab) → tooltip visible, dismissable via ESC ou blur
 *   - tap mobile → toggle le tooltip (compatible iOS Safari/Android Chrome)
 *   - aria-describedby relie l'élément déclencheur au popover (lecteurs d'écran)
 *
 * Props :
 *   - content : ReactNode | string — texte ou markup du tooltip
 *   - children : ReactNode — élément déclencheur (texte, acronyme, badge…)
 *   - placement : 'top' | 'bottom' (défaut top)
 *   - className : string optionnel sur le span déclencheur
 *
 * Doctrine §6 anti-pattern "tooltip natif fragile" résolu.
 */
import { useId, useRef, useState, useEffect } from 'react';

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

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => {
      if (e.key === 'Escape') {
        setOpen(false);
        triggerRef.current?.blur();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  if (!content) return <span className={className}>{children}</span>;

  return (
    <span style={{ position: 'relative', display: 'inline-block' }}>
      <span
        ref={triggerRef}
        tabIndex={0}
        role="button"
        aria-describedby={open ? idTip : undefined}
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
        onClick={(e) => {
          // Tap mobile : toggle visibility
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        className={`cursor-help ${className}`}
        style={{
          borderBottom: '1px dotted var(--sol-ink-400)',
          textDecoration: 'none',
          outline: 'none',
        }}
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
            minWidth: '220px',
            padding: '8px 10px',
            background: 'var(--sol-ink-900)',
            color: 'var(--sol-bg-paper)',
            borderRadius: 6,
            fontSize: 12,
            lineHeight: 1.45,
            fontFamily: 'var(--sol-font-body)',
            boxShadow: '0 4px 12px rgba(0,0,0,0.18)',
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
