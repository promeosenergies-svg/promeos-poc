/**
 * PROMEOS — useFloatingPortalPosition
 * Premium portal positioning hook.
 *
 * Computes fixed top/left for a portaled overlay anchored to a trigger element.
 * Auto-repositions on scroll, resize, and visualViewport zoom (mobile pinch).
 * No flicker: useLayoutEffect fires synchronously before browser paint.
 *
 * @param {object} opts
 * @param {boolean}  opts.isOpen       — when true, attach listeners and compute position
 * @param {Ref}      opts.triggerRef   — ref to the trigger/anchor element
 * @param {Ref}      opts.portalRef    — ref to the portaled overlay div
 * @param {string}   opts.placement    — 'bottom-start' | 'bottom-end' | 'top-start' (default: 'bottom-start')
 * @param {number}   opts.offset       — px gap between trigger and overlay (default: 8)
 * @param {number}   opts.clampPadding — min distance from viewport edges (default: 8)
 *
 * @returns {{ style: {top, left}, updatePosition: () => void }}
 *   style           — spread onto the overlay element (add className="fixed" separately)
 *   updatePosition  — force immediate repositioning (e.g. after content resize)
 *
 * Usage:
 *   const dropRef = useRef(null);
 *   const { style } = useFloatingPortalPosition({ isOpen, triggerRef, portalRef: dropRef });
 *   // In JSX: <div ref={dropRef} className="fixed z-[120] ..." style={style}>
 */
import { useState, useLayoutEffect, useCallback, useRef } from 'react';

const OFF_SCREEN = Object.freeze({ top: -9999, left: -9999 });

function _computePos(triggerEl, portalEl, placement, offset, pad) {
  const tr = triggerEl.getBoundingClientRect();
  const pw = portalEl.offsetWidth  || 200; // fallback if portal hasn't laid out yet
  const ph = portalEl.offsetHeight || 40;
  const vw = window.innerWidth;
  const vh = window.innerHeight;

  let top, left;

  switch (placement) {
    case 'bottom-end':
      top  = tr.bottom + offset;
      left = tr.right - pw;
      break;
    case 'top-start':
      top  = tr.top - ph - offset;
      left = tr.left;
      break;
    default: // 'bottom-start'
      top  = tr.bottom + offset;
      left = tr.left;
  }

  // Auto-flip vertically when overflow
  if (placement.startsWith('bottom') && top + ph > vh - pad && tr.top - ph - offset >= pad) {
    top = tr.top - ph - offset;
  } else if (placement.startsWith('top') && top < pad && tr.bottom + offset + ph <= vh - pad) {
    top = tr.bottom + offset;
  }

  // Clamp to viewport
  return {
    top:  Math.max(pad, Math.min(top,  vh - ph - pad)),
    left: Math.max(pad, Math.min(left, vw - pw - pad)),
  };
}

export default function useFloatingPortalPosition({
  isOpen,
  triggerRef,
  portalRef,
  placement = 'bottom-start',
  offset = 8,
  clampPadding = 8,
}) {
  const [style, setStyle] = useState(OFF_SCREEN);
  const rafRef = useRef(null);

  const update = useCallback(() => {
    const tEl = triggerRef?.current;
    const pEl = portalRef?.current;
    if (!tEl || !pEl) return;
    setStyle(_computePos(tEl, pEl, placement, offset, clampPadding));
  }, [triggerRef, portalRef, placement, offset, clampPadding]);

  const rafUpdate = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(update);
  }, [update]);

  useLayoutEffect(() => {
    if (!isOpen) {
      setStyle(OFF_SCREEN);
      return;
    }

    // Synchronous initial position — before browser paint, no flicker
    update();

    const captOpts = { capture: true, passive: true };
    window.addEventListener('scroll', rafUpdate, captOpts);
    window.addEventListener('resize', rafUpdate, { passive: true });
    // visualViewport: handles mobile pinch-zoom + address-bar resize
    if (window.visualViewport) {
      window.visualViewport.addEventListener('scroll', rafUpdate);
      window.visualViewport.addEventListener('resize', rafUpdate);
    }

    return () => {
      window.removeEventListener('scroll', rafUpdate, captOpts);
      window.removeEventListener('resize', rafUpdate);
      if (window.visualViewport) {
        window.visualViewport.removeEventListener('scroll', rafUpdate);
        window.visualViewport.removeEventListener('resize', rafUpdate);
      }
      cancelAnimationFrame(rafRef.current);
    };
  }, [isOpen, update, rafUpdate]);

  return { style, updatePosition: update };
}
