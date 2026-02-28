/**
 * PROMEOS — InfoTooltip (Sprint V13)
 * Small "?" bubble with a hover tooltip in French.
 * Renders inline; works next to any label or button.
 * V2: portal-based to escape sticky/backdrop-blur stacking contexts.
 *
 * Props:
 *   text       — tooltip text (required, French)
 *   position   — 'top' (default) | 'bottom'
 */
import { useState, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';

export default function InfoTooltip({ text, position = 'top' }) {
  const [show, setShow] = useState(false);
  const [coords, setCoords] = useState(null);
  const triggerRef = useRef(null);

  const computeAndShow = useCallback(() => {
    if (triggerRef.current) {
      const r = triggerRef.current.getBoundingClientRect();
      const cx = r.left + r.width / 2;
      setCoords(
        position === 'bottom'
          ? { top: r.bottom + 4, left: cx, transform: 'translateX(-50%)' }
          : { top: r.top - 4,    left: cx, transform: 'translate(-50%, -100%)' },
      );
    }
    setShow(true);
  }, [position]);

  const hide = useCallback(() => setShow(false), []);

  // Guard: no text → render nothing (hooks must run unconditionally first)
  if (!text) return null;

  return (
    <span className="relative inline-flex items-center">
      <button
        ref={triggerRef}
        type="button"
        onMouseEnter={computeAndShow}
        onMouseLeave={hide}
        onFocus={computeAndShow}
        onBlur={hide}
        className="w-3.5 h-3.5 rounded-full bg-gray-200 text-gray-500 hover:bg-gray-300 text-[9px] font-bold flex items-center justify-center cursor-help leading-none"
        aria-label={text}
        tabIndex={0}
      >
        ?
      </button>
      {show && coords && createPortal(
        <span
          role="tooltip"
          className="fixed z-[120] w-48 text-[10px] leading-snug bg-gray-800 text-white rounded-md px-2.5 py-1.5 shadow-lg pointer-events-none whitespace-normal"
          style={{ top: coords.top, left: coords.left, transform: coords.transform }}
        >
          {text}
        </span>,
        document.body,
      )}
    </span>
  );
}
