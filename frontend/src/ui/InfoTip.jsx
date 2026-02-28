/**
 * PROMEOS Design System — InfoTip
 * Self-contained info icon with portal tooltip.
 *
 * Features:
 *   - Returns null when content is empty/undefined (no black dot, no empty bubble)
 *   - Portal rendering in document.body (avoids stacking context / overflow clipping)
 *   - max-width 280px, text wrapping, border, shadow, z-index 120
 *   - aria-label, focus ring, keyboard accessible (Tab + Enter/Space)
 *   - ~200ms hover delay (anti-flicker)
 *
 * Usage:
 *   <InfoTip content="Explanation text" />
 *   <InfoTip content={TOOLTIPS.executive.risqueConformite} position="bottom" />
 */
import { useState, useRef, useCallback, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Info } from 'lucide-react';

const DELAY_MS = 200;
const OFFSET   = 8;   // px gap between icon and tooltip bubble

function _getCoords(rect, position) {
  const cx = rect.left + rect.width / 2;
  const cy = rect.top  + rect.height / 2;
  switch (position) {
    case 'bottom': return { top: rect.bottom + OFFSET, left: cx,            transform: 'translateX(-50%)' };
    case 'left':   return { top: cy,                   left: rect.left - OFFSET, transform: 'translate(-100%, -50%)' };
    case 'right':  return { top: cy,                   left: rect.right + OFFSET, transform: 'translateY(-50%)' };
    default:       return { top: rect.top - OFFSET,    left: cx,            transform: 'translate(-50%, -100%)' };
  }
}

export default function InfoTip({
  content,
  position  = 'top',
  size      = 12,
  className = '',
}) {
  const [visible, setVisible] = useState(false);
  const [coords,  setCoords]  = useState(null);
  const triggerRef = useRef(null);
  const timerRef   = useRef(null);
  const tooltipId  = useRef(`it-${Math.random().toString(36).slice(2)}`);

  const show = useCallback(() => {
    if (!content) return;
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      if (triggerRef.current) {
        const rect = triggerRef.current.getBoundingClientRect();
        const raw  = _getCoords(rect, position);
        const vw   = typeof window !== 'undefined' ? window.innerWidth  : 1280;
        const vh   = typeof window !== 'undefined' ? window.innerHeight : 800;
        setCoords({
          ...raw,
          left: Math.max(8, Math.min(raw.left, vw - 296)),   // 280px + 16px margin
          top:  Math.max(8, Math.min(raw.top,  vh - 80)),
        });
      }
      setVisible(true);
    }, DELAY_MS);
  }, [position, content]);

  const hide = useCallback(() => {
    clearTimeout(timerRef.current);
    setVisible(false);
  }, []);

  useEffect(() => () => clearTimeout(timerRef.current), []);

  // Guard: after hooks — no content → render nothing
  if (!content) return null;

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        aria-label="Aide contextuelle"
        aria-describedby={visible ? tooltipId.current : undefined}
        className={`inline-flex items-center justify-center shrink-0 text-gray-400
          hover:text-gray-600 rounded cursor-help transition-colors
          focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1
          ${className}`}
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
      >
        <Info size={size} aria-hidden="true" />
      </button>

      {visible && coords && createPortal(
        <div
          id={tooltipId.current}
          role="tooltip"
          className="fixed pointer-events-none z-[120]"
          style={{ top: coords.top, left: coords.left, transform: coords.transform }}
        >
          <div className="max-w-[280px] px-3 py-2 text-xs text-gray-700 leading-relaxed
            bg-white border border-gray-200 rounded-lg shadow-lg">
            {content}
          </div>
        </div>,
        document.body,
      )}
    </>
  );
}
