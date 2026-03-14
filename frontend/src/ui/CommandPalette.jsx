/**
 * PROMEOS Design System — Command Palette
 * Ctrl+K overlay with search, keyboard nav, quick actions, and shortcuts.
 * B.2: Results grouped by section, 10 actions rapides avec raccourcis visuels.
 */
import { useState, useEffect, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, ArrowRight, CornerDownLeft } from 'lucide-react';
import {
  ALL_NAV_ITEMS,
  QUICK_ACTIONS,
  ALL_MAIN_ITEMS,
  COMMAND_SHORTCUTS,
} from '../layout/NavRegistry';

export default function CommandPalette({ open, onClose, onToggleExpert }) {
  const [query, setQuery] = useState('');
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (open) {
      setQuery('');
      setSelectedIdx(0);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  const results = useMemo(() => {
    const q = query.toLowerCase().trim();
    if (!q) {
      // Default: pages grouped by section + shortcuts
      const pages = ALL_MAIN_ITEMS.slice(0, 8).map((item) => ({ type: 'page', ...item }));
      const shortcuts = COMMAND_SHORTCUTS.map((a) => ({ type: 'shortcut', ...a }));
      return [...pages, ...shortcuts];
    }

    // Search in ALL_MAIN_ITEMS (section-aware) + legacy ALL_NAV_ITEMS + QUICK_ACTIONS + COMMAND_SHORTCUTS
    const seen = new Set();
    const matchItem = (item) => {
      const searchable = [item.label, item.section, ...(item.keywords || [])]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return searchable.includes(q);
    };

    const pages = ALL_MAIN_ITEMS.filter(matchItem).map((item) => {
      seen.add(item.to);
      return { type: 'page', ...item };
    });

    // Add legacy items not in main sections
    const legacyPages = ALL_NAV_ITEMS.filter((item) => !seen.has(item.to) && matchItem(item)).map(
      (item) => {
        seen.add(item.to);
        return { type: 'page', ...item };
      }
    );

    const actions = QUICK_ACTIONS.filter((a) => !seen.has(a.to) && matchItem(a)).map((a) => ({
      type: 'action',
      ...a,
    }));
    const shortcuts = COMMAND_SHORTCUTS.filter(matchItem).map((a) => ({ type: 'shortcut', ...a }));

    return [...pages, ...legacyPages, ...actions, ...shortcuts];
  }, [query]);

  useEffect(() => {
    setSelectedIdx(0);
  }, [query]);

  const handleSelect = (item) => {
    if (item.to === '#expert-toggle') {
      if (onToggleExpert) onToggleExpert();
      onClose();
      return;
    }
    navigate(item.to);
    onClose();
  };

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIdx((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && results[selectedIdx]) {
      e.preventDefault();
      handleSelect(results[selectedIdx]);
    } else if (e.key === 'Escape') {
      onClose();
    }
  };

  if (!open) return null;

  // Group results by section for display
  let lastSection = null;

  return (
    <div className="fixed inset-0 z-[200] flex items-start justify-center pt-[15vh]">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div
        className="relative w-full max-w-lg bg-white rounded-xl shadow-2xl border border-gray-200 overflow-hidden"
        onKeyDown={handleKeyDown}
      >
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-100">
          <Search size={18} className="text-gray-400 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Rechercher pages, actions..."
            className="flex-1 text-sm bg-transparent outline-none placeholder:text-gray-400"
          />
          <kbd className="hidden sm:inline-flex items-center px-1.5 py-0.5 text-[10px] font-mono text-gray-400 bg-gray-100 rounded border border-gray-200">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-80 overflow-y-auto py-2">
          {results.length === 0 && (
            <div className="px-4 py-6 text-center">
              <p className="text-sm text-gray-400">Aucun résultat pour « {query} »</p>
              <p className="text-xs text-gray-300 mt-2">
                Essayez : conformité, actions, patrimoine, monitoring...
              </p>
            </div>
          )}
          {results.map((item, idx) => {
            const Icon = item.icon;
            const isSelected = idx === selectedIdx;

            // Section separator for grouped display
            const showSectionHeader =
              item.section && item.section !== lastSection && item.type === 'page';
            if (item.section) lastSection = item.section;
            const showShortcutHeader =
              item.type === 'shortcut' && (idx === 0 || results[idx - 1]?.type !== 'shortcut');

            return (
              <div key={item.to + (item.key || '') + idx}>
                {showSectionHeader && (
                  <p className="px-4 pt-2 pb-1 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                    {item.section}
                  </p>
                )}
                {showShortcutHeader && (
                  <p className="px-4 pt-2 pb-1 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                    Actions rapides
                  </p>
                )}
                <button
                  onClick={() => handleSelect(item)}
                  className={`w-full flex items-center gap-3 px-4 py-2.5 text-left text-sm transition
                    ${isSelected ? 'bg-blue-50 text-blue-700' : 'text-gray-700 hover:bg-gray-50'}`}
                >
                  {Icon && (
                    <Icon size={16} className={isSelected ? 'text-blue-500' : 'text-gray-400'} />
                  )}
                  {!Icon && (
                    <ArrowRight
                      size={16}
                      className={isSelected ? 'text-blue-500' : 'text-gray-400'}
                    />
                  )}
                  <span className="flex-1 truncate">{item.label}</span>
                  {item.shortcut && (
                    <kbd className="hidden sm:inline-flex items-center px-1.5 py-0.5 text-[10px] font-mono text-gray-400 bg-gray-100 rounded border border-gray-200">
                      {item.shortcut}
                    </kbd>
                  )}
                  {!item.shortcut && item.section && (
                    <span className="text-xs text-gray-400">{item.section}</span>
                  )}
                  {item.type === 'action' && (
                    <span className="text-[10px] px-1.5 py-0.5 bg-amber-50 text-amber-700 rounded font-medium">
                      Action
                    </span>
                  )}
                  {isSelected && <CornerDownLeft size={12} className="text-gray-400" />}
                </button>
              </div>
            );
          })}
        </div>

        {/* Footer hint */}
        <div className="px-4 py-2 border-t border-gray-100 flex items-center gap-4 text-[10px] text-gray-400">
          <span>
            <kbd className="px-1 bg-gray-100 rounded">↑↓</kbd> Naviguer
          </span>
          <span>
            <kbd className="px-1 bg-gray-100 rounded">↵</kbd> Ouvrir
          </span>
          <span>
            <kbd className="px-1 bg-gray-100 rounded">esc</kbd> Fermer
          </span>
        </div>
      </div>
    </div>
  );
}
