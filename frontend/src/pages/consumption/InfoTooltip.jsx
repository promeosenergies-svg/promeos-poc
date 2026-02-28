/**
 * PROMEOS — InfoTooltip (Sprint V13)
 * Small "?" bubble with a hover tooltip in French.
 * Renders inline; works next to any label or button.
 *
 * Props:
 *   text       — tooltip text (required, French)
 *   position   — 'top' (default) | 'bottom'
 */
import { useState } from 'react';

export default function InfoTooltip({ text, position = 'top' }) {
  const [show, setShow] = useState(false);

  // Guard: no text → render nothing (hooks must run unconditionally first)
  if (!text) return null;

  return (
    <span className="relative inline-flex items-center">
      <button
        type="button"
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        onFocus={() => setShow(true)}
        onBlur={() => setShow(false)}
        className="w-3.5 h-3.5 rounded-full bg-gray-200 text-gray-500 hover:bg-gray-300 text-[9px] font-bold flex items-center justify-center cursor-help leading-none"
        aria-label={text}
        tabIndex={0}
      >
        ?
      </button>
      {show && (
        <span
          role="tooltip"
          className={`absolute z-50 w-48 text-[10px] leading-snug bg-gray-800 text-white rounded-md px-2.5 py-1.5 shadow-lg pointer-events-none whitespace-normal
            ${position === 'bottom'
              ? 'top-full left-1/2 -translate-x-1/2 mt-1'
              : 'bottom-full left-1/2 -translate-x-1/2 mb-1'
            }`}
        >
          {text}
        </span>
      )}
    </span>
  );
}
