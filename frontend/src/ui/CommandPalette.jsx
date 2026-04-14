/**
 * PROMEOS Design System — Command Palette
 * Ctrl+K overlay with search, keyboard nav, quick actions, and shortcuts.
 * B.2: Results grouped by section, 10 actions rapides avec raccourcis visuels.
 */
import { useState, useEffect, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, ArrowRight, CornerDownLeft } from 'lucide-react';
import { MapPin } from 'lucide-react';
import {
  ALL_NAV_ITEMS,
  QUICK_ACTIONS,
  ALL_MAIN_ITEMS,
  COMMAND_SHORTCUTS,
} from '../layout/NavRegistry';
import { useScope } from '../contexts/ScopeContext';

const HITS_KEY = 'promeos_cmd_hits';

/* ── Smart queries — structured syntax with direct actions ──
 * Syntax: <scope>:<verb>  e.g. "sites:non-conformes", "factures:retard"
 * Each query resolves to a direct navigation with filter params.
 */
const SMART_QUERIES = [
  {
    match: /^sites?\s*:\s*non[-\s]?conformes?$/i,
    label: 'Sites non conformes',
    subtitle: 'Filtre conformité : statut "non conforme"',
    to: '/patrimoine?filter=non-conformes',
    section: 'Query',
  },
  {
    match: /^sites?\s*:\s*a[-\s]?evaluer$/i,
    label: 'Sites à évaluer',
    subtitle: 'Filtre : statut "à évaluer"',
    to: '/patrimoine?filter=a-evaluer',
    section: 'Query',
  },
  {
    match: /^factures?\s*:\s*(retard|impay)/i,
    label: 'Factures en retard',
    subtitle: 'Bill Intel filtré sur anomalies de paiement',
    to: '/bill-intel?filter=retard',
    section: 'Query',
  },
  {
    match: /^factures?\s*:\s*anomalies?$/i,
    label: 'Factures avec anomalies',
    subtitle: 'Écarts détectés par shadow billing',
    to: '/bill-intel?filter=anomalies',
    section: 'Query',
  },
  {
    match: /^actions?\s*:\s*urgent/i,
    label: 'Actions urgentes',
    subtitle: 'Actions P0 en cours',
    to: '/anomalies?tab=actions&priority=urgent',
    section: 'Query',
  },
  {
    match: /^actions?\s*:\s*(retard|en[-\s]?retard)/i,
    label: 'Actions en retard',
    subtitle: 'Actions dont la date limite est dépassée',
    to: '/anomalies?tab=actions&filter=late',
    section: 'Query',
  },
  {
    match: /^conso\s*:\s*anomalies?$/i,
    label: 'Anomalies de consommation',
    subtitle: 'Diagnostic conso — insights détectés',
    to: '/diagnostic-conso?filter=anomalies',
    section: 'Query',
  },
  {
    match: /^contrats?\s*:\s*echeance/i,
    label: 'Contrats à échéance',
    subtitle: 'Radar renouvellements',
    to: '/renouvellements',
    section: 'Query',
  },
  {
    match: /^flex\s*:\s*(potentiel|opportunit)/i,
    label: 'Gisements flex détectés',
    subtitle: 'Sites avec potentiel NEBEF / effacement',
    to: '/flex',
    section: 'Query',
  },
  {
    match: /^conformite\s*:\s*dt$/i,
    label: 'Décret Tertiaire',
    subtitle: 'Obligations DT sur le portefeuille',
    to: '/conformite?tab=obligations&regulation=dt',
    section: 'Query',
  },
  {
    match: /^conformite\s*:\s*bacs$/i,
    label: 'Pilotage bâtiment (BACS)',
    subtitle: 'Obligations GTB/GTC',
    to: '/conformite?tab=obligations&regulation=bacs',
    section: 'Query',
  },
];

/** Try to match query against smart syntax. Returns array of results or null. */
function matchSmartQueries(query) {
  const matched = SMART_QUERIES.filter((sq) => sq.match.test(query));
  if (matched.length === 0) return null;
  return matched.map((sq) => ({ type: 'query', ...sq }));
}

function loadHits() {
  try {
    return JSON.parse(localStorage.getItem(HITS_KEY) || '{}');
  } catch {
    return {};
  }
}

function recordHit(path) {
  const hits = loadHits();
  hits[path] = (hits[path] || 0) + 1;
  try {
    localStorage.setItem(HITS_KEY, JSON.stringify(hits));
  } catch {
    /* noop */
  }
}

export default function CommandPalette({ open, onClose, onToggleExpert }) {
  const { orgSites: scopedSites = [] } = useScope();
  const [query, setQuery] = useState('');
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef(null);
  const navigate = useNavigate();
  const hitsRef = useRef(loadHits());

  useEffect(() => {
    if (open) {
      hitsRef.current = loadHits();
      setQuery('');
      setSelectedIdx(0);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  const results = useMemo(() => {
    const q = query.toLowerCase().trim();
    const hits = hitsRef.current;

    // Smart queries first (structured syntax like "sites:non-conformes")
    const smart = q ? matchSmartQueries(q) : null;
    if (smart) return smart;

    if (!q) {
      // Default: pages ranked by frequency, then shortcuts
      const pages = ALL_MAIN_ITEMS.map((item) => ({
        type: 'page',
        ...item,
        _score: hits[item.to] || 0,
      }))
        .sort((a, b) => b._score - a._score)
        .slice(0, 8);
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

    // Sites search — match by nom, ville, adresse
    const siteResults = scopedSites
      .filter((s) => {
        const searchable = [s.nom, s.ville, s.adresse, s.code_postal, s.usage]
          .filter(Boolean)
          .join(' ')
          .toLowerCase();
        return searchable.includes(q);
      })
      .slice(0, 5)
      .map((s) => ({
        type: 'site',
        to: `/sites/${s.id}`,
        label: s.nom,
        section: 'Sites',
        icon: MapPin,
        keywords: [s.ville, s.usage].filter(Boolean),
        subtitle: [s.ville, s.usage].filter(Boolean).join(' · '),
      }));

    // Boost pages by frequency (frequent pages float to top)
    const allPages = [...pages, ...legacyPages].sort(
      (a, b) => (hits[b.to] || 0) - (hits[a.to] || 0)
    );
    return [...siteResults, ...allPages, ...actions, ...shortcuts];
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    recordHit(item.to);
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
              <div className="mt-3 text-[10px] text-gray-400 space-y-0.5">
                <p className="font-semibold text-gray-500">Smart queries :</p>
                <p>
                  <code className="text-violet-500">sites:non-conformes</code> ·{' '}
                  <code className="text-violet-500">factures:retard</code> ·{' '}
                  <code className="text-violet-500">actions:urgent</code>
                </p>
                <p>
                  <code className="text-violet-500">flex:potentiel</code> ·{' '}
                  <code className="text-violet-500">contrats:echeance</code> ·{' '}
                  <code className="text-violet-500">conformite:dt</code>
                </p>
              </div>
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
                  <span className="flex-1 truncate">
                    {item.label}
                    {item.subtitle && (
                      <span className="ml-1.5 text-xs text-gray-400 font-normal">
                        {item.subtitle}
                      </span>
                    )}
                  </span>
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
                  {item.type === 'site' && (
                    <span className="text-[10px] px-1.5 py-0.5 bg-emerald-50 text-emerald-700 rounded font-medium">
                      Site
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
