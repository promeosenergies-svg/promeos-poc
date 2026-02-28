/**
 * PROMEOS Design System — TooltipPortal (Sprint WOW 6.6)
 * Portal-based tooltip rendered in document.body with position:fixed.
 * Avoids clipping by ancestor overflow/stacking contexts (e.g. NavPanel backdrop-filter).
 *
 * Features:
 *   - Hover delay (anti-flicker)
 *   - Viewport clamping (stays on screen)
 *   - aria-describedby linkage (a11y)
 *   - prefers-reduced-motion support
 *   - Keyboard focus support (onFocus/onBlur)
 */
import { useState, useRef, useCallback, useEffect } from 'react';
import { createPortal } from 'react-dom';

const OFFSET = 8; // px gap between trigger and tooltip

/** Default hover delay — prevents flicker on quick mouse-through. */
export const TOOLTIP_DELAY_MS = 100;

/**
 * Compute tooltip position relative to viewport.
 * Exported for unit testing.
 */
export function computePosition(triggerRect, position = 'right') {
  if (!triggerRect) return { top: 0, left: 0 };

  const { top, left, width, height } = triggerRect;
  const cx = left + width / 2;
  const cy = top + height / 2;

  switch (position) {
    case 'right':
      return { top: cy, left: left + width + OFFSET, transform: 'translateY(-50%)' };
    case 'left':
      return { top: cy, left: left - OFFSET, transform: 'translate(-100%, -50%)' };
    case 'bottom':
      return { top: top + height + OFFSET, left: cx, transform: 'translateX(-50%)' };
    case 'top':
    default:
      return { top: top - OFFSET, left: cx, transform: 'translate(-50%, -100%)' };
  }
}

/**
 * Clamp tooltip coordinates to stay within the viewport.
 * Exported for unit testing.
 *
 * @param {object} coords        — { top, left, transform }
 * @param {number} viewportW     — window.innerWidth
 * @param {number} viewportH     — window.innerHeight
 * @param {number} estW          — estimated tooltip width (default 180)
 * @param {number} estH          — estimated tooltip height (default 28)
 */
export function clampCoords(coords, viewportW, viewportH, estW = 180, estH = 28) {
  return {
    ...coords,
    left: Math.max(4, Math.min(coords.left, viewportW - estW - 4)),
    top:  Math.max(4, Math.min(coords.top,  viewportH - estH - 4)),
  };
}

export default function TooltipPortal({
  text,
  children,
  position = 'right',
  delayMs = TOOLTIP_DELAY_MS,
  className = '',
}) {
  const [visible, setVisible] = useState(false);
  const [coords, setCoords] = useState(null);
  const triggerRef = useRef(null);
  const timerRef   = useRef(null);
  // Stable unique id per tooltip instance (for aria-describedby linkage)
  const tooltipId  = useRef(`tp-${Math.random().toString(36).slice(2)}`);

  const show = useCallback(() => {
    // Guard: no text → never show tooltip
    if (!text) return;
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      if (triggerRef.current) {
        const rect = triggerRef.current.getBoundingClientRect();
        const raw  = computePosition(rect, position);
        const vw   = (typeof window !== 'undefined' ? window.innerWidth  : 1280);
        const vh   = (typeof window !== 'undefined' ? window.innerHeight : 800);
        setCoords(clampCoords(raw, vw, vh));
      }
      setVisible(true);
    }, delayMs);
  }, [text, position, delayMs]);

  const hide = useCallback(() => {
    clearTimeout(timerRef.current);
    setVisible(false);
  }, []);

  // Cleanup pending timer on unmount
  useEffect(() => () => clearTimeout(timerRef.current), []);

  return (
    <span
      ref={triggerRef}
      className={`inline-flex ${className}`}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
      aria-describedby={visible ? tooltipId.current : undefined}
    >
      {children}
      {visible && coords && createPortal(
        <span
          id={tooltipId.current}
          className="fixed z-[120] px-2 py-1 text-xs text-white bg-gray-900 rounded shadow-lg whitespace-nowrap pointer-events-none transition-opacity duration-100 motion-reduce:transition-none"
          style={{ top: coords.top, left: coords.left, transform: coords.transform }}
          role="tooltip"
        >
          {text}
        </span>,
        document.body,
      )}
    </span>
  );
}
