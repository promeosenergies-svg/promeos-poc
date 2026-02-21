/**
 * PROMEOS — Dev-only render timing hook.
 * Measures time from mount start to first paint (useEffect fires after paint).
 * Data surfaced in DevPanel > Perf tab.
 *
 * Usage:  useRenderTiming('Cockpit');
 * In production builds, this is a no-op (tree-shaken by Vite).
 */
import { useRef, useEffect } from 'react';

// Module-level ring buffer — shared across all components using the hook
let _renderTimings = [];
const MAX_ENTRIES = 30;

/** @returns {Array} Last render timings for DevPanel */
export function getRenderTimings() {
  return _renderTimings;
}

export default function useRenderTiming(componentName) {
  const startRef = useRef(null);

  // Capture mount start time (during render phase)
  if (import.meta.env.DEV && startRef.current === null) {
    startRef.current = performance.now();
  }

  useEffect(() => {
    if (!import.meta.env.DEV || startRef.current === null) return;

    const duration = Math.round(performance.now() - startRef.current);
    const entry = {
      component: componentName,
      duration,
      ts: Date.now(),
    };
    _renderTimings = [..._renderTimings, entry].slice(-MAX_ENTRIES);

    if (duration > 100) {
      console.warn(`[perf] ${componentName} render: ${duration}ms (>100ms)`);
    }

    // Reset for next render
    startRef.current = null;
  });
}
