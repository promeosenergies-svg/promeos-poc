/**
 * PROMEOS — Combobox (recherche + sélection intelligente)
 *
 * Props:
 *   label        — Label au-dessus du champ
 *   value        — Valeur sélectionnée (string)
 *   onChange      — (value) => void
 *   options       — [{ value, label, group?, hint?, icon? }]
 *   placeholder   — Placeholder du champ de recherche
 *   required      — Affiche l'astérisque
 *   disabled      — Désactive le champ
 *   grouped       — Active le groupement par `group`
 *   allowCustom   — Autorise la saisie libre (pas seulement les options)
 *   className     — Classes supplémentaires
 */
import { useState, useRef, useEffect, useMemo } from 'react';
import { ChevronDown, Search, X, Check } from 'lucide-react';

export default function Combobox({
  label,
  value = '',
  onChange,
  options = [],
  placeholder = 'Rechercher...',
  required = false,
  disabled = false,
  grouped = false,
  allowCustom = false,
  className = '',
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [activeIdx, setActiveIdx] = useState(-1);
  const inputRef = useRef(null);
  const listRef = useRef(null);
  const containerRef = useRef(null);

  // Trouver le label de la valeur courante
  const selectedOption = options.find((o) => o.value === value);
  const displayValue = selectedOption?.label || value || '';

  // Filtrage par recherche
  const filtered = useMemo(() => {
    if (!query.trim()) return options;
    const q = query.toLowerCase();
    return options.filter(
      (o) =>
        o.label.toLowerCase().includes(q) ||
        o.value.toLowerCase().includes(q) ||
        (o.hint && o.hint.toLowerCase().includes(q)) ||
        (o.group && o.group.toLowerCase().includes(q))
    );
  }, [options, query]);

  // Grouper si demandé
  const groups = useMemo(() => {
    if (!grouped) return null;
    const map = new Map();
    for (const o of filtered) {
      const g = o.group || 'Autre';
      if (!map.has(g)) map.set(g, []);
      map.get(g).push(o);
    }
    return map;
  }, [filtered, grouped]);

  // Fermer sur clic extérieur
  useEffect(() => {
    const handler = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
        setQuery('');
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  useEffect(() => {
    setActiveIdx(-1);
  }, [filtered]);

  // Scroll active item into view
  useEffect(() => {
    if (activeIdx >= 0 && listRef.current) {
      const items = listRef.current.querySelectorAll('[data-combobox-item]');
      items[activeIdx]?.scrollIntoView({ block: 'nearest' });
    }
  }, [activeIdx]);

  const handleSelect = (opt) => {
    onChange(opt.value);
    setOpen(false);
    setQuery('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIdx((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && activeIdx >= 0) {
      e.preventDefault();
      handleSelect(filtered[activeIdx]);
    } else if (e.key === 'Enter' && allowCustom && query.trim()) {
      e.preventDefault();
      onChange(query.trim());
      setOpen(false);
      setQuery('');
    } else if (e.key === 'Escape') {
      setOpen(false);
      setQuery('');
    }
  };

  const handleOpen = () => {
    if (disabled) return;
    setOpen(true);
    setQuery('');
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  const handleClear = (e) => {
    e.stopPropagation();
    onChange('');
    setOpen(false);
    setQuery('');
  };

  const renderOption = (opt, idx) => {
    const isSelected = opt.value === value;
    const isActive = idx === activeIdx;
    return (
      <li
        key={opt.value}
        data-combobox-item
        role="option"
        aria-selected={isSelected}
        className={`
          flex items-center gap-2 px-3 py-2 text-sm cursor-pointer transition-colors
          ${isActive ? 'bg-blue-50 text-blue-900' : 'text-gray-700 hover:bg-gray-50'}
          ${isSelected ? 'font-medium' : ''}
        `}
        onMouseEnter={() => setActiveIdx(idx)}
        onMouseDown={(e) => {
          e.preventDefault();
          handleSelect(opt);
        }}
      >
        {opt.icon && <span className="text-gray-400 flex-shrink-0">{opt.icon}</span>}
        <span className="flex-1 truncate">
          {opt.label}
          {opt.hint && <span className="ml-2 text-xs text-gray-400">{opt.hint}</span>}
        </span>
        {isSelected && <Check size={14} className="text-blue-600 flex-shrink-0" />}
      </li>
    );
  };

  // Flatten index pour les groupes
  let flatIdx = 0;

  return (
    <div ref={containerRef} className={`relative flex flex-col gap-1 ${className}`}>
      {label && (
        <label className="text-sm font-medium text-gray-700">
          {label}
          {required && <span className="text-red-500 ml-0.5">*</span>}
        </label>
      )}

      {/* Bouton trigger */}
      <button
        type="button"
        onClick={handleOpen}
        disabled={disabled}
        className={`
          flex items-center gap-2 w-full px-3 py-2 border rounded-lg text-sm text-left bg-white
          transition-colors
          ${open ? 'ring-2 ring-blue-500 border-blue-500' : 'border-gray-300 hover:border-gray-400'}
          ${disabled ? 'bg-gray-50 text-gray-400 cursor-not-allowed' : ''}
        `}
      >
        <span className={`flex-1 truncate ${!displayValue ? 'text-gray-400' : 'text-gray-900'}`}>
          {displayValue || placeholder}
        </span>
        {value && !disabled && (
          <X
            size={14}
            className="text-gray-400 hover:text-gray-600 flex-shrink-0"
            onClick={handleClear}
          />
        )}
        <ChevronDown
          size={14}
          className={`text-gray-400 flex-shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-72 overflow-hidden flex flex-col">
          {/* Recherche */}
          <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-100">
            <Search size={14} className="text-gray-400" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              className="flex-1 text-sm outline-none bg-transparent"
            />
            {query && (
              <button
                type="button"
                onClick={() => setQuery('')}
                className="text-gray-400 hover:text-gray-600"
              >
                <X size={12} />
              </button>
            )}
          </div>

          {/* Liste */}
          <ul ref={listRef} role="listbox" className="overflow-y-auto max-h-56">
            {filtered.length === 0 && (
              <li className="px-3 py-4 text-sm text-gray-400 text-center">
                {allowCustom && query.trim()
                  ? `Appuyer sur Entree pour "${query.trim()}"`
                  : 'Aucun resultat'}
              </li>
            )}

            {grouped && groups
              ? [...groups.entries()].map(([group, items]) => (
                  <li key={group}>
                    <div className="px-3 py-1.5 text-xs font-semibold text-gray-400 uppercase tracking-wider bg-gray-50 sticky top-0">
                      {group}
                    </div>
                    <ul>
                      {items.map((opt) => {
                        const idx = flatIdx++;
                        return renderOption(opt, idx);
                      })}
                    </ul>
                  </li>
                ))
              : filtered.map((opt, idx) => renderOption(opt, idx))}
          </ul>
        </div>
      )}
    </div>
  );
}
