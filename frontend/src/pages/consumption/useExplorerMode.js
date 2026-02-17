/**
 * PROMEOS — useExplorerMode (Sprint V13)
 * Persists the Explorer UI mode (Classic / Expert) in localStorage.
 * Does NOT affect the URL — layout preference only.
 *
 * Classic = historical layout: all core controls visible at once.
 * Expert  = advanced layout with layers panel, portfolio, extra controls.
 */
import { useState, useCallback } from 'react';

const STORAGE_KEY = 'promeos_explorer_ui_mode';
const VALID_MODES = ['classic', 'expert'];

function loadMode() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (VALID_MODES.includes(raw)) return raw;
  } catch { /* ignore */ }
  return 'classic'; // default
}

export default function useExplorerMode() {
  const [uiMode, _setUiMode] = useState(loadMode);

  const setUiMode = useCallback((mode) => {
    if (!VALID_MODES.includes(mode)) return;
    _setUiMode(mode);
    try { localStorage.setItem(STORAGE_KEY, mode); } catch { /* ignore */ }
  }, []);

  const toggleUiMode = useCallback(() => {
    _setUiMode(prev => {
      const next = prev === 'classic' ? 'expert' : 'classic';
      try { localStorage.setItem(STORAGE_KEY, next); } catch { /* ignore */ }
      return next;
    });
  }, []);

  return {
    uiMode,
    isClassic: uiMode === 'classic',
    isExpert: uiMode === 'expert',
    setUiMode,
    toggleUiMode,
  };
}
