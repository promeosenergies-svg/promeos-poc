/**
 * PROMEOS - SitePicker
 * Multi-site selector with search, chips, collections, and quick picks.
 */
import { useState, useEffect, useMemo, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Search, X, Star, FolderOpen, ChevronDown, Save, Check } from 'lucide-react';
import { getEmsCollections, createEmsCollection } from '../services/api';
import useFloatingPortalPosition from '../hooks/useFloatingPortalPosition';

const MAX_RECENT = 5;
const LS_KEY = 'promeos_ems_recent_sites';

function loadRecent() {
  try { return JSON.parse(localStorage.getItem(LS_KEY) || '[]'); } catch { return []; }
}
function saveRecent(ids) {
  localStorage.setItem(LS_KEY, JSON.stringify(ids.slice(0, MAX_RECENT)));
}

export default function SitePicker({ sites, selectedIds, onChange, maxSelection = 8 }) {
  const [search, setSearch] = useState('');
  const [open, setOpen] = useState(false);
  const [collections, setCollections] = useState([]);
  const [_showCollections, setShowCollections] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [recent] = useState(loadRecent);
  const ref = useRef(null);
  const triggerRef = useRef(null);
  const dropRef = useRef(null);

  // Premium positioning: scroll/resize/zoom auto-reposition
  const { style: dropStyle } = useFloatingPortalPosition({
    isOpen: open,
    triggerRef,
    portalRef: dropRef,
  });

  // Load collections on mount
  useEffect(() => {
    getEmsCollections().then(setCollections).catch(() => {});
  }, []);

  // Close on outside click — check both trigger area and portaled dropdown
  useEffect(() => {
    function onClick(e) {
      if (
        ref.current && !ref.current.contains(e.target) &&
        !(dropRef.current && dropRef.current.contains(e.target))
      ) {
        setOpen(false);
        setShowCollections(false);
      }
    }
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  // Track recent selections
  useEffect(() => {
    if (selectedIds.length > 0) {
      const merged = [...new Set([...selectedIds, ...loadRecent()])];
      saveRecent(merged.slice(0, MAX_RECENT));
    }
  }, [selectedIds]);

  const filtered = useMemo(() => {
    if (!search.trim()) return sites;
    const q = search.toLowerCase();
    return sites.filter(s =>
      s.nom.toLowerCase().includes(q) ||
      (s.ville || '').toLowerCase().includes(q) ||
      (s.usage || '').toLowerCase().includes(q)
    );
  }, [sites, search]);

  const selectedSites = useMemo(() =>
    sites.filter(s => selectedIds.includes(s.id)),
  [sites, selectedIds]);

  const toggle = (id) => {
    if (selectedIds.includes(id)) {
      onChange(selectedIds.filter(x => x !== id));
    } else if (selectedIds.length < maxSelection) {
      onChange([...selectedIds, id]);
    }
  };

  const selectAll = (ids) => {
    const capped = ids.slice(0, maxSelection);
    onChange(capped);
    setOpen(false);
  };

  const handleSaveCollection = async () => {
    if (!saveName.trim() || selectedIds.length === 0) return;
    await createEmsCollection(saveName, selectedIds);
    const updated = await getEmsCollections();
    setCollections(updated);
    setSaveName('');
  };

  const chipLabel = selectedSites.length === 0
    ? 'Selectionner des sites'
    : selectedSites.length === 1
      ? selectedSites[0].nom
      : `${selectedSites.length} sites`;

  return (
    <div ref={ref} className="relative">
      {/* Trigger button */}
      <button
        ref={triggerRef}
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2 px-3 py-1.5 text-sm border border-gray-300 rounded-lg bg-white
          hover:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition min-w-[180px]"
      >
        <span className="truncate flex-1 text-left">{chipLabel}</span>
        <ChevronDown size={14} className={`text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {/* Selected chips (when multi) */}
      {selectedSites.length > 1 && (
        <div className="flex flex-wrap gap-1 mt-1.5">
          {selectedSites.map(s => (
            <span key={s.id} className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full text-xs font-medium">
              {s.nom}
              <button onClick={() => toggle(s.id)} className="hover:bg-blue-100 rounded-full p-0.5">
                <X size={10} />
              </button>
            </span>
          ))}
          {selectedSites.length > 0 && (
            <button onClick={() => onChange([])} className="text-xs text-gray-400 hover:text-gray-600 ml-1">
              Tout effacer
            </button>
          )}
        </div>
      )}

      {/* Dropdown — portaled to body, auto-repositions on scroll/resize/zoom */}
      {open && createPortal(
        <div
          ref={dropRef}
          className="fixed z-[120] w-80 bg-white border border-gray-200 rounded-xl shadow-xl max-h-[420px] flex flex-col"
          style={dropStyle}
        >
          {/* Search */}
          <div className="p-2 border-b border-gray-100">
            <div className="relative">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Rechercher un site..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-200 rounded-lg
                  focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                autoFocus
              />
            </div>
          </div>

          {/* Quick picks: collections */}
          {collections.length > 0 && (
            <div className="px-2 py-1.5 border-b border-gray-100">
              <p className="text-[10px] font-semibold text-gray-400 uppercase px-1 mb-1">Collections</p>
              <div className="flex flex-wrap gap-1">
                {collections.slice(0, 4).map(c => (
                  <button
                    key={c.id}
                    onClick={() => selectAll(c.site_ids)}
                    className="flex items-center gap-1 px-2 py-0.5 text-xs bg-gray-50 hover:bg-blue-50 hover:text-blue-700 rounded-md border border-gray-200 transition"
                  >
                    {c.is_favorite && <Star size={10} className="text-amber-500" />}
                    <FolderOpen size={10} />
                    {c.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Recent */}
          {recent.length > 0 && !search.trim() && (
            <div className="px-2 py-1.5 border-b border-gray-100">
              <p className="text-[10px] font-semibold text-gray-400 uppercase px-1 mb-1">Recents</p>
              <div className="flex flex-wrap gap-1">
                {recent.slice(0, 3).map(id => {
                  const s = sites.find(x => x.id === id);
                  if (!s) return null;
                  return (
                    <button
                      key={id}
                      onClick={() => { if (!selectedIds.includes(id)) toggle(id); }}
                      className="px-2 py-0.5 text-xs bg-gray-50 hover:bg-blue-50 rounded-md border border-gray-200 transition"
                    >
                      {s.nom}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Site list */}
          <div className="overflow-y-auto flex-1 py-1">
            {filtered.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-4">Aucun site trouve</p>
            ) : (
              filtered.map(s => {
                const isSelected = selectedIds.includes(s.id);
                const atMax = !isSelected && selectedIds.length >= maxSelection;
                return (
                  <button
                    key={s.id}
                    onClick={() => !atMax && toggle(s.id)}
                    disabled={atMax}
                    className={`w-full flex items-center gap-2 px-3 py-2 text-left transition text-sm
                      ${isSelected ? 'bg-blue-50 text-blue-800' : atMax ? 'opacity-40 cursor-not-allowed' : 'hover:bg-gray-50'}`}
                  >
                    <div className={`w-4 h-4 rounded border flex items-center justify-center shrink-0
                      ${isSelected ? 'bg-blue-600 border-blue-600' : 'border-gray-300'}`}>
                      {isSelected && <Check size={10} className="text-white" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{s.nom}</p>
                      <p className="text-xs text-gray-400 truncate">{s.ville || ''} {s.usage ? `· ${s.usage}` : ''}</p>
                    </div>
                    {s.conso_kwh_an > 0 && (
                      <span className="text-xs text-gray-400 shrink-0">
                        {(s.conso_kwh_an / 1000).toFixed(0)}k kWh
                      </span>
                    )}
                  </button>
                );
              })
            )}
          </div>

          {/* Footer: count + save */}
          <div className="border-t border-gray-100 px-3 py-2 flex items-center gap-2">
            <span className="text-xs text-gray-500">{selectedIds.length}/{maxSelection} sites</span>
            <div className="flex-1" />
            <input
              type="text"
              placeholder="Sauvegarder..."
              value={saveName}
              onChange={e => setSaveName(e.target.value)}
              className="text-xs border border-gray-200 rounded px-2 py-1 w-28 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <button
              onClick={handleSaveCollection}
              disabled={!saveName.trim() || selectedIds.length === 0}
              className="p-1 text-blue-600 hover:bg-blue-50 rounded disabled:opacity-30 transition"
              title="Sauvegarder la collection"
            >
              <Save size={14} />
            </button>
          </div>
        </div>,
        document.body,
      )}
    </div>
  );
}
