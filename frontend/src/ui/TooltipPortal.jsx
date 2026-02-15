/**
 * PROMEOS Design System — TooltipPortal
 * Portal-based tooltip rendered in document.body with position:fixed.
 * Avoids clipping by ancestor overflow/stacking contexts (e.g. NavRail under header).
 *
 * Uses JS positioning (getBoundingClientRect) for pixel-perfect placement.
 * Falls back to CSS-only Tooltip if createPortal is unavailable (SSR).
 */
import { useState, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';

const OFFSET = 8; // px gap between trigger and tooltip

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

export default function TooltipPortal({ text, children, position = 'right', className = '' }) {
  const [visible, setVisible] = useState(false);
  const [coords, setCoords] = useState(null);
  const triggerRef = useRef(null);

  const show = useCallback(() => {
    if (triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setCoords(computePosition(rect, position));
    }
    setVisible(true);
  }, [position]);

  const hide = useCallback(() => setVisible(false), []);

  return (
    <span
      ref={triggerRef}
      className={`inline-flex ${className}`}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      {children}
      {visible && coords && createPortal(
        <span
          className="fixed z-[9999] px-2 py-1 text-xs text-white bg-gray-900 rounded shadow-lg whitespace-nowrap pointer-events-none transition-opacity duration-100"
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
