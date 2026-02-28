/**
 * PROMEOS — StickyFilterBar v5 (Sprint V13)
 * Unified sticky bar supporting Classic and Expert UI modes.
 *
 * Classic mode (default):
 *   Row 1 : Sites (chips + add) • Énergie • Période • Granularité
 *   Row 2 : Mode pills (Agrège/Superpose/Empile/Sépare) • Unité pills (kWh/kW/EUR)
 *   Row 3 : Actions (Enregistrer / Effacer / Copier le lien / Presets)
 *   Row 4 : Résumé contexte (toujours visible)
 *   [opt]  : Plage de dates personnalisée (collapsible)
 *
 * Expert mode:
 *   Same as Classic but Row 2 mode pills only shown for multi-site/portfolio
 *   (preserves V4 / Sprint V12 behavior exactly).
 *
 * Props (all optional / backward-compat):
 *   uiMode                      'classic' | 'expert' (default: 'classic')
 *   siteIds, setSiteIds         multi-site (new)
 *   siteId, setSiteId           legacy single-site fallback
 *   sites                       [{id, nom}] available sites
 *   energyType, setEnergyType
 *   availableTypes              energy types available
 *   days, setDays               period in days
 *   startDate, setStartDate     ISO8601 custom range start
 *   endDate, setEndDate         ISO8601 custom range end
 *   mode, setMode               agrege|superpose|empile|separe
 *   unit, setUnit               kwh|kw|eur
 *   availability                data quality metadata
 *   isPortfolioMode             boolean — Portfolio mode active
 *   onTogglePortfolio()         toggle Portfolio mode
 *   onSave(name, state)         save named preset callback
 *   onReset()                   reset to defaults callback
 *   onCopyLink()                copy shareable URL callback
 *   savedPresets                [{ name, savedAt }]
 *   onLoadPreset(name)          load preset callback
 *   onDeletePreset(name)        delete preset callback
 */
import { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, Zap, Flame, Save, RotateCcw, Link, ChevronDown, Trash2, Plus, LayoutGrid } from 'lucide-react';
import { TrustBadge } from '../../ui';
import { computeGranularity, colorForSite, getAvailableGranularities } from './helpers';
import { MODE_LABELS, UNIT_LABELS, MAX_SITES } from './types';
import InfoTooltip from './InfoTooltip';

const ENERGY_OPTIONS = [
  { value: 'electricity', label: 'Électricité', icon: Zap },
  { value: 'gas', label: 'Gaz', icon: Flame },
];

// Quick period pills — 'ytd' is a sentinel computed to Jan-1 → today
const PERIOD_PILLS = [
  { value: 7,     label: '7 j' },
  { value: 30,    label: '30 j' },
  { value: 90,    label: '90 j' },
  { value: 365,   label: '12 m' },
  { value: 'ytd', label: 'YTD' },
];

const GRAN_LABELS = { '30min': '30 min', '1h': '1 heure', jour: 'Jour', semaine: 'Semaine' };

// In Portfolio mode, only Agrege is meaningful
const MODE_ORDER = ['agrege', 'superpose', 'empile', 'separe'];
const UNIT_ORDER = ['kwh', 'kw', 'eur'];

const MODE_TOOLTIPS = {
  agrege:   'Somme de tous les sites sur une seule courbe.',
  superpose:'Courbe de chaque site superposée, même axe Y.',
  empile:   'Courbe de chaque site empilée (aires cumulées).',
  separe:   'Un sous-graphique par site, axe indépendant.',
};

const UNIT_TOOLTIPS = {
  kwh: 'Énergie consommée en kilowatt-heure.',
  kw:  'Puissance instantanée en kilowatt.',
  eur: 'Coût estimé en euros (tarif réglementé).',
};

/** Compute YTD start (Jan 1 of current year) as ISO string */
function ytdStart() {
  return `${new Date().getFullYear()}-01-01`;
}
/** Today as ISO string */
function todayISO() {
  return new Date().toISOString().split('T')[0];
}

// ── Site Search Dropdown ──────────────────────────────────────────────────────
// Portaled to document.body — escapes the sticky+backdrop-blur stacking context.
function SiteSearchDropdown({ sites, selectedIds, onAdd, onClose, anchorRef }) {
  const [query, setQuery] = useState('');
  const [coords, setCoords] = useState(null);
  const inputRef = useRef(null);
  const dropRef = useRef(null);

  useEffect(() => { inputRef.current?.focus(); }, []);

  // Compute fixed position from the anchor element
  useEffect(() => {
    if (anchorRef?.current) {
      const r = anchorRef.current.getBoundingClientRect();
      setCoords({ top: r.bottom + 4, left: r.left });
    }
  }, [anchorRef]);

  // Outside-click closes the dropdown (checks both anchor and portaled div)
  useEffect(() => {
    function handler(e) {
      if (
        dropRef.current && !dropRef.current.contains(e.target) &&
        anchorRef?.current && !anchorRef.current.contains(e.target)
      ) {
        onClose();
      }
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [onClose, anchorRef]);

  const available = sites.filter(
    s => !selectedIds.includes(s.id) &&
      s.nom.toLowerCase().includes(query.toLowerCase())
  );

  if (!coords) return null;

  return createPortal(
    <div
      ref={dropRef}
      className="fixed w-60 bg-white rounded-lg shadow-lg border border-gray-200 z-[120] py-1"
      style={{ top: coords.top, left: coords.left }}
    >
      <div className="px-2 py-1.5 border-b border-gray-100">
        <input
          ref={inputRef}
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Rechercher un site..."
          className="w-full text-xs border border-gray-200 rounded-md px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-400"
        />
      </div>
      <div className="max-h-52 overflow-y-auto">
        {available.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-3">Aucun site disponible</p>
        )}
        {available.map((s, idx) => {
          const color = colorForSite(s.id, idx);
          return (
            <button
              key={s.id}
              onClick={() => { onAdd(s.id); onClose(); }}
              className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50 text-left"
            >
              <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: color }} />
              <span className="truncate">{s.nom}</span>
            </button>
          );
        })}
      </div>
    </div>,
    document.body,
  );
}

// ── Mode pills sub-component ──────────────────────────────────────────────────
function ModePills({ mode, setMode, isPortfolioMode, availableModes, showTooltips = false }) {
  return (
    <div className="flex gap-1 bg-gray-100 rounded-lg p-0.5">
      {availableModes.map(m => (
        <button
          key={m}
          onClick={() => setMode(m)}
          disabled={isPortfolioMode && m !== 'agrege'}
          className={`flex items-center gap-1 px-3 py-1 rounded-md text-xs font-medium transition ${
            mode === m
              ? 'bg-white text-blue-700 shadow-sm'
              : isPortfolioMode && m !== 'agrege'
                ? 'text-gray-300 cursor-not-allowed'
                : 'text-gray-600 hover:text-gray-900'
          }`}
          title={isPortfolioMode && m !== 'agrege' ? 'Non disponible en mode Portfolio' : undefined}
        >
          {MODE_LABELS[m]}
          {showTooltips && MODE_TOOLTIPS[m] && (
            <InfoTooltip text={MODE_TOOLTIPS[m]} />
          )}
        </button>
      ))}
    </div>
  );
}

// ── Unit pills sub-component ──────────────────────────────────────────────────
function UnitPills({ unit, setUnit, showTooltips = false }) {
  return (
    <div className="flex gap-1 bg-gray-100 rounded-lg p-0.5">
      {UNIT_ORDER.map(u => (
        <button
          key={u}
          onClick={() => setUnit(u)}
          className={`flex items-center gap-1 px-3 py-1 rounded-md text-xs font-medium transition ${
            unit === u ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          {UNIT_LABELS[u]}
          {showTooltips && UNIT_TOOLTIPS[u] && (
            <InfoTooltip text={UNIT_TOOLTIPS[u]} />
          )}
        </button>
      ))}
    </div>
  );
}

// ── Résumé contexte (Row 4, Classic mode only) ────────────────────────────────
function ResumeContexte({ days, gran, nSites, availability }) {
  const meters = availability?.meters_count ?? null;
  const source = availability?.source ?? null;
  const quality = availability?.readings_count
    ? Math.min(100, Math.round(availability.readings_count / 500 * 100))
    : null;

  const parts = [
    days === 'ytd' ? 'YTD' : `${days} j`,
    GRAN_LABELS[gran] || gran,
    `${nSites} site${nSites > 1 ? 's' : ''}`,
    meters != null ? `${meters} compteur${meters > 1 ? 's' : ''}` : '— compteur',
    source ? `Source\u00a0: ${source}` : null,
    quality != null ? `Qualité\u00a0: ${quality}\u00a0%` : null,
  ].filter(Boolean);

  return (
    <div className="text-[10px] text-gray-400 flex flex-wrap gap-x-3 gap-y-0.5 pt-0.5 border-t border-gray-50">
      {parts.map((p, i) => (
        <span key={i}>{p}</span>
      ))}
    </div>
  );
}

export default function StickyFilterBar({
  // UI mode
  uiMode = 'classic',
  // Multi-site (new)
  siteIds = [],
  setSiteIds,
  // Legacy single-site fallback (still supported)
  siteId,
  setSiteId,
  sites = [],
  // Energy
  energyType,
  setEnergyType,
  availableTypes,
  // Period (quick pills)
  days,
  setDays,
  // Custom date range
  startDate,
  setStartDate,
  endDate,
  setEndDate,
  // Mode + Unit
  mode,
  setMode,
  unit,
  setUnit,
  // Data quality
  availability,
  // Loading state (V19 — from sitesLoading in ScopeContext)
  sitesLoading = false,
  // Portfolio mode (V12)
  isPortfolioMode = false,
  onTogglePortfolio,
  // Action callbacks
  onSave,
  onReset,
  onCopyLink,
  // Presets
  savedPresets = [],
  onLoadPreset,
  onDeletePreset,
  // Granularity selector (V21-C + V22-B)
  granularity = 'auto',
  setGranularity,
  samplingMinutes = null,  // V22-B: actual meter reading interval for intersection
}) {
  const isClassic = uiMode === 'classic';

  const [showSaveInput, setShowSaveInput] = useState(false);
  const [presetName, setPresetName] = useState('');
  const [showPresets, setShowPresets] = useState(false);
  const [showCustomDates, setShowCustomDates] = useState(!!(startDate || endDate));
  const [showAddSite, setShowAddSite] = useState(false);

  const addRef = useRef(null);
  const presetsBtnRef = useRef(null);
  const presetsDropRef = useRef(null);
  const [presetsCoords, setPresetsCoords] = useState(null);

  // Close presets dropdown on outside click
  useEffect(() => {
    if (!showPresets) return;
    const handler = (e) => {
      if (
        presetsDropRef.current && !presetsDropRef.current.contains(e.target) &&
        presetsBtnRef.current && !presetsBtnRef.current.contains(e.target)
      ) {
        setShowPresets(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showPresets]);

  const gran = computeGranularity(days);
  const confidence = availability?.has_data
    ? (availability.readings_count > 1000 ? 'high' : availability.readings_count > 200 ? 'medium' : 'low')
    : null;

  // Resolve effective selected site IDs (multi or single legacy)
  const effectiveSiteIds = siteIds.length > 0 ? siteIds : (siteId ? [siteId] : []);
  // V19: always multi-mode when setSiteIds is provided (even with 0 or 1 sites)
  const isMultiMode = Boolean(setSiteIds);

  const toggleSite = (id) => {
    if (!setSiteIds) {
      if (setSiteId) setSiteId(id);
      return;
    }
    if (effectiveSiteIds.includes(id)) {
      // Don't remove last remaining site
      if (effectiveSiteIds.length > 1) {
        setSiteIds(effectiveSiteIds.filter(s => s !== id));
      }
    } else if (!isPortfolioMode && effectiveSiteIds.length < MAX_SITES) {
      setSiteIds([...effectiveSiteIds, id]);
    }
  };

  // Determine which period pill is active
  const isCustomRange = !!(startDate || endDate);
  const activePill = isCustomRange ? 'custom' : (days === 'ytd' ? 'ytd' : days);

  const handlePillClick = (value) => {
    if (value === 'ytd') {
      if (setStartDate) setStartDate(ytdStart());
      if (setEndDate) setEndDate(todayISO());
      if (setDays) setDays(365);
      setShowCustomDates(false);
    } else {
      if (setStartDate) setStartDate(null);
      if (setEndDate) setEndDate(null);
      if (setDays) setDays(value);
      setShowCustomDates(false);
    }
  };

  const handleSave = () => {
    if (!presetName.trim()) return;
    if (onSave) onSave(presetName.trim());
    setPresetName('');
    setShowSaveInput(false);
  };

  const handleCopyLink = () => {
    if (onCopyLink) onCopyLink();
    else { try { navigator.clipboard.writeText(window.location.href); } catch {} }
  };

  // Modes available in current context
  const availableModes = isPortfolioMode ? ['agrege'] : MODE_ORDER;

  // In Classic mode: always show mode pills. In Expert: only for multi-site / portfolio.
  const showModePills = setMode && (isClassic || effectiveSiteIds.length > 1 || isPortfolioMode);

  return (
    <div className="sticky top-0 z-20 bg-white/95 backdrop-blur border-b border-gray-100 -mx-4 px-4 py-2.5 md:-mx-6 md:px-6 space-y-2">

      {/* Row 1: Site chips (selected only) + add button + Portfolio toggle + Energy + Period + Gran + Trust */}
      <div className="flex items-center gap-3 flex-wrap">

        {/* V19: Site section — ALWAYS visible when setSiteIds is provided */}
        {setSiteIds && !isPortfolioMode && (
          <div className="flex items-center gap-1.5">
            {effectiveSiteIds.length > 0 ? (
              /* Selected site chips */
              <div className="flex gap-1.5 overflow-x-auto max-w-xs" style={{ scrollbarWidth: 'thin' }}>
                {effectiveSiteIds.map((id, idx) => {
                  const site = sites.find(s => s.id === id);
                  const color = colorForSite(id, idx);
                  return (
                    <button
                      key={id}
                      onClick={() => toggleSite(id)}
                      className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border text-white border-transparent shrink-0 transition"
                      style={{ backgroundColor: color, borderColor: color }}
                      title={effectiveSiteIds.length > 1 ? `Retirer ${site?.nom || id}` : site?.nom || String(id)}
                    >
                      <span className="w-2 h-2 rounded-full bg-white/60 shrink-0" />
                      <span className="max-w-[120px] truncate">{site?.nom || id}</span>
                      {effectiveSiteIds.length > 1 && (
                        <X size={10} className="opacity-70 shrink-0" />
                      )}
                    </button>
                  );
                })}
              </div>
            ) : (
              /* Placeholder: loading or no sites yet */
              <span className="text-xs text-gray-400 italic px-1 py-1">
                {sitesLoading ? 'Chargement\u2026' : 'S\u00e9lectionner des sites\u2026'}
              </span>
            )}

            {/* "+" add site button — only when more sites exist to add */}
            {effectiveSiteIds.length < MAX_SITES && sites.length > effectiveSiteIds.length && (
              <div ref={addRef}>
                <button
                  onClick={() => setShowAddSite(v => !v)}
                  className="flex items-center justify-center w-6 h-6 rounded-full bg-gray-100 text-gray-500 hover:bg-gray-200 transition"
                  title="Ajouter un site"
                >
                  <Plus size={12} />
                </button>
                {showAddSite && (
                  <SiteSearchDropdown
                    anchorRef={addRef}
                    sites={sites}
                    selectedIds={effectiveSiteIds}
                    onAdd={(id) => { toggleSite(id); }}
                    onClose={() => setShowAddSite(false)}
                  />
                )}
              </div>
            )}
          </div>
        )}

        {/* Portfolio mode: show label instead of chips */}
        {isMultiMode && isPortfolioMode && (
          <div className="flex items-center gap-2 px-3 py-1 bg-indigo-50 border border-indigo-200 rounded-full">
            <LayoutGrid size={12} className="text-indigo-600" />
            <span className="text-xs font-medium text-indigo-700">
              Portfolio — {sites.length} sites
            </span>
          </div>
        )}

        {/* Portfolio toggle button (shown when multi-site available) */}
        {isMultiMode && onTogglePortfolio && (
          <div className="flex items-center gap-1">
            <button
              onClick={onTogglePortfolio}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition ${
                isPortfolioMode
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-white text-gray-600 border-gray-200 hover:border-indigo-300 hover:text-indigo-600'
              }`}
              title={isPortfolioMode ? 'Quitter le mode Portfolio' : 'Passer en mode Portfolio (tous les sites)'}
            >
              <LayoutGrid size={11} />
              Portfolio
            </button>
            <InfoTooltip text="Portfolio : vue agrégée de tous les sites. Mode Agrégé uniquement." />
          </div>
        )}

        {/* Legacy single-site select (when setSiteIds not provided) */}
        {!setSiteIds && sites.length > 1 && (
          <select
            value={siteId || effectiveSiteIds[0] || ''}
            onChange={(e) => setSiteId ? setSiteId(Number(e.target.value)) : toggleSite(Number(e.target.value))}
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white font-medium"
          >
            {sites.map(s => <option key={s.id} value={s.id}>{s.nom}</option>)}
          </select>
        )}

        {/* Energy toggle */}
        <div className="flex gap-1 bg-gray-100 rounded-lg p-0.5">
          {ENERGY_OPTIONS.map(opt => {
            const Icon = opt.icon;
            const disabled = availableTypes && !availableTypes.includes(opt.value);
            return (
              <button
                key={opt.value}
                onClick={() => !disabled && setEnergyType(opt.value)}
                disabled={disabled}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition ${
                  energyType === opt.value
                    ? 'bg-white text-blue-700 shadow-sm'
                    : disabled
                      ? 'text-gray-300 cursor-not-allowed'
                      : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <Icon size={14} />
                {opt.label}
              </button>
            );
          })}
        </div>

        {/* Period pills — 7j / 30j / 90j / 12m / YTD */}
        <div className="flex gap-1 bg-gray-100 rounded-lg p-0.5">
          {PERIOD_PILLS.map(pill => (
            <button
              key={pill.value}
              onClick={() => handlePillClick(pill.value)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition ${
                activePill === pill.value
                  ? 'bg-white text-blue-700 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {pill.label}
            </button>
          ))}
          {/* Custom date range pill */}
          <button
            onClick={() => setShowCustomDates(v => !v)}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition ${
              isCustomRange || showCustomDates
                ? 'bg-white text-blue-700 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Date perso
          </button>
        </div>

        {/* Granularity selector (V21-C) — pills when setGranularity provided, badge otherwise */}
        {setGranularity ? (
          <div className="flex items-center gap-1">
            <span className="text-xs text-gray-500 shrink-0">Granularité :</span>
            <div className="flex rounded-lg overflow-hidden border border-gray-200 bg-gray-50">
              {getAvailableGranularities(days, samplingMinutes).map((g) => (
                <button
                  key={g.key}
                  onClick={() => setGranularity(g.key)}
                  className={`px-2 py-1 text-xs font-medium transition-colors duration-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
                    granularity === g.key
                      ? 'bg-white text-blue-700 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {g.label}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-gray-100 rounded-lg text-xs font-medium text-gray-600">
            Granularité&nbsp;: {GRAN_LABELS[gran] || gran}
          </span>
        )}

        {/* Data quality badge (right-aligned) */}
        {confidence && (
          <div className="ml-auto">
            <TrustBadge
              source={`${(availability.readings_count || 0).toLocaleString()} relevés`}
              confidence={confidence}
            />
          </div>
        )}
      </div>

      {/* Custom date range row (collapsible) */}
      {showCustomDates && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-gray-500 font-medium">Du</span>
          <input
            type="date"
            value={startDate || ''}
            onChange={(e) => setStartDate && setStartDate(e.target.value || null)}
            className="text-xs border border-gray-200 rounded-md px-2 py-1 bg-white"
          />
          <span className="text-xs text-gray-500 font-medium">au</span>
          <input
            type="date"
            value={endDate || ''}
            onChange={(e) => setEndDate && setEndDate(e.target.value || null)}
            className="text-xs border border-gray-200 rounded-md px-2 py-1 bg-white"
          />
          {(startDate || endDate) && (
            <button
              onClick={() => {
                if (setStartDate) setStartDate(null);
                if (setEndDate) setEndDate(null);
                setShowCustomDates(false);
                if (setDays) setDays(90);
              }}
              className="text-xs text-gray-400 hover:text-gray-600 underline"
            >
              Effacer
            </button>
          )}
        </div>
      )}

      {/* Row 2: Mode pills + Unit toggle (Classic: always shown; Expert: multi-site/portfolio only) */}
      {(showModePills || setUnit) && (
        <div className="flex items-center gap-3 flex-wrap">
          {showModePills && (
            <ModePills
              mode={mode}
              setMode={setMode}
              isPortfolioMode={isPortfolioMode}
              availableModes={availableModes}
              showTooltips={isClassic}
            />
          )}
          {setUnit && (
            <UnitPills
              unit={unit}
              setUnit={setUnit}
              showTooltips={isClassic}
            />
          )}
        </div>
      )}

      {/* Row 3: Actions (Enregistrer / Effacer / Copier le lien / Presets) */}
      {(onSave || onReset || onCopyLink) && (
        <div className="flex items-center gap-2 flex-wrap">

          {/* Save preset */}
          {onSave && (
            showSaveInput ? (
              <div className="flex items-center gap-1.5">
                <input
                  type="text"
                  value={presetName}
                  onChange={(e) => setPresetName(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') handleSave(); if (e.key === 'Escape') setShowSaveInput(false); }}
                  placeholder="Nom du preset..."
                  autoFocus
                  className="text-xs border border-blue-300 rounded-md px-2 py-1 bg-white w-36 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <button
                  onClick={handleSave}
                  disabled={!presetName.trim()}
                  className="px-2.5 py-1 text-xs font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-40"
                >
                  OK
                </button>
                <button
                  onClick={() => setShowSaveInput(false)}
                  className="px-2 py-1 text-xs text-gray-500 hover:text-gray-700"
                >
                  <X size={12} />
                </button>
              </div>
            ) : (
              <button
                onClick={() => setShowSaveInput(true)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition"
              >
                <Save size={12} />
                Enregistrer
              </button>
            )
          )}

          {/* Presets dropdown */}
          {savedPresets.length > 0 && onLoadPreset && (
            <div>
              <button
                ref={presetsBtnRef}
                onClick={() => {
                  if (!showPresets && presetsBtnRef.current) {
                    const r = presetsBtnRef.current.getBoundingClientRect();
                    setPresetsCoords({ top: r.bottom + 4, left: r.left });
                  }
                  setShowPresets(v => !v);
                }}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition"
              >
                Presets ({savedPresets.length})
                <ChevronDown size={11} />
              </button>
              {showPresets && presetsCoords && createPortal(
                <div
                  ref={presetsDropRef}
                  className="fixed w-52 bg-white rounded-lg shadow-lg border border-gray-200 z-[120] py-1"
                  style={{ top: presetsCoords.top, left: presetsCoords.left }}
                >
                  {savedPresets.map(p => (
                    <div key={p.name} className="flex items-center gap-1 px-2 py-1.5 hover:bg-gray-50 group">
                      <button
                        onClick={() => { onLoadPreset(p.name); setShowPresets(false); }}
                        className="flex-1 text-left text-xs font-medium text-gray-700 truncate"
                        title={p.name}
                      >
                        {p.name}
                      </button>
                      {onDeletePreset && (
                        <button
                          onClick={(e) => { e.stopPropagation(); onDeletePreset(p.name); }}
                          className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition"
                          title="Supprimer"
                        >
                          <Trash2 size={11} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>,
                document.body,
              )}
            </div>
          )}

          {/* Reset */}
          {onReset && (
            <button
              onClick={onReset}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition"
              title="Réinitialiser les filtres"
            >
              <RotateCcw size={12} />
              Effacer
            </button>
          )}

          {/* Copy link */}
          <button
            onClick={handleCopyLink}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition"
            title="Copier le lien de partage"
          >
            <Link size={12} />
            Copier le lien
          </button>
        </div>
      )}

      {/* Row 4: Résumé contexte (Classic mode only) */}
      {isClassic && (
        <ResumeContexte
          days={days}
          gran={gran}
          nSites={effectiveSiteIds.length || sites.length}
          availability={availability}
        />
      )}
    </div>
  );
}
