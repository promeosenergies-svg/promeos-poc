/**
 * PROMEOS — StickyFilterBar v3 (Consumption Explorer)
 * Unified sticky bar: multi-site chips + mode + unit + period pills
 *   + custom date range + energy toggle + Save/Reset/Copy actions + presets
 *
 * Props (all optional / backward-compat):
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
 *   onSave(name, state)         save named preset callback
 *   onReset()                   reset to defaults callback
 *   onCopyLink()                copy shareable URL callback
 *   savedPresets                [{ name, savedAt }]
 *   onLoadPreset(name)          load preset callback
 *   onDeletePreset(name)        delete preset callback
 */
import { useState } from 'react';
import { X, Zap, Flame, Save, RotateCcw, Link, ChevronDown, Trash2 } from 'lucide-react';
import { TrustBadge } from '../../ui';
import { computeGranularity, colorForSite } from './helpers';
import { MODE_LABELS, UNIT_LABELS, MAX_SITES } from './types';

const ENERGY_OPTIONS = [
  { value: 'electricity', label: 'Electricite', icon: Zap },
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

const MODE_ORDER = ['agrege', 'superpose', 'empile', 'separe'];
const UNIT_ORDER = ['kwh', 'kw', 'eur'];

/** Compute YTD start (Jan 1 of current year) as ISO string */
function ytdStart() {
  return `${new Date().getFullYear()}-01-01`;
}
/** Today as ISO string */
function todayISO() {
  return new Date().toISOString().split('T')[0];
}

export default function StickyFilterBar({
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
  // Mode + Unit (new)
  mode,
  setMode,
  unit,
  setUnit,
  // Data quality
  availability,
  // Action callbacks
  onSave,
  onReset,
  onCopyLink,
  // Presets
  savedPresets = [],
  onLoadPreset,
  onDeletePreset,
}) {
  const [showSaveInput, setShowSaveInput] = useState(false);
  const [presetName, setPresetName] = useState('');
  const [showPresets, setShowPresets] = useState(false);
  const [showCustomDates, setShowCustomDates] = useState(!!(startDate || endDate));

  const gran = computeGranularity(days);
  const confidence = availability?.has_data
    ? (availability.readings_count > 1000 ? 'high' : availability.readings_count > 200 ? 'medium' : 'low')
    : null;

  // Resolve effective selected site IDs (multi or single legacy)
  const effectiveSiteIds = siteIds.length > 0 ? siteIds : (siteId ? [siteId] : []);
  const isMultiMode = sites.length > 1 && setSiteIds;

  const toggleSite = (id) => {
    if (!setSiteIds) {
      if (setSiteId) setSiteId(id);
      return;
    }
    if (effectiveSiteIds.includes(id)) {
      if (effectiveSiteIds.length > 1) {
        setSiteIds(effectiveSiteIds.filter(s => s !== id));
      }
    } else if (effectiveSiteIds.length < MAX_SITES) {
      setSiteIds([...effectiveSiteIds, id]);
    }
  };

  // Determine which period pill is active
  const isCustomRange = !!(startDate || endDate);
  const activePill = isCustomRange ? 'custom' : (days === 'ytd' ? 'ytd' : days);

  const handlePillClick = (value) => {
    if (value === 'ytd') {
      // YTD: clear days, set start=Jan-1, end=today
      if (setStartDate) setStartDate(ytdStart());
      if (setEndDate) setEndDate(todayISO());
      if (setDays) setDays(365); // fallback days value
      setShowCustomDates(false);
    } else {
      // Clear custom range when switching to quick pill
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
    else {
      try { navigator.clipboard.writeText(window.location.href); } catch {}
    }
  };

  return (
    <div className="sticky top-0 z-20 bg-white/95 backdrop-blur border-b border-gray-100 -mx-4 px-4 py-2.5 md:-mx-6 md:px-6 space-y-2">

      {/* Row 1: Site chips + Energy toggle + Period pills + Granularity + Trust badge */}
      <div className="flex items-center gap-3 flex-wrap">

        {/* Multi-site chips */}
        {isMultiMode ? (
          <div className="flex flex-wrap gap-1.5">
            {sites.map((s, idx) => {
              const selected = effectiveSiteIds.includes(s.id);
              const color = colorForSite(s.id, idx);
              return (
                <button
                  key={s.id}
                  onClick={() => toggleSite(s.id)}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition ${
                    selected
                      ? 'text-white border-transparent'
                      : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400'
                  }`}
                  style={selected ? { backgroundColor: color, borderColor: color } : {}}
                  title={selected && effectiveSiteIds.length > 1 ? 'Retirer' : s.nom}
                >
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: selected ? 'rgba(255,255,255,0.6)' : color }}
                  />
                  {s.nom}
                  {selected && effectiveSiteIds.length > 1 && (
                    <X size={10} className="opacity-70" />
                  )}
                </button>
              );
            })}
          </div>
        ) : sites.length > 1 ? (
          <select
            value={siteId || effectiveSiteIds[0] || ''}
            onChange={(e) => setSiteId ? setSiteId(Number(e.target.value)) : toggleSite(Number(e.target.value))}
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white font-medium"
          >
            {sites.map(s => <option key={s.id} value={s.id}>{s.nom}</option>)}
          </select>
        ) : null}

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

        {/* Granularity badge (auto, read-only) */}
        <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-gray-100 rounded-lg text-xs font-medium text-gray-600">
          Granularite : {GRAN_LABELS[gran] || gran}
        </span>

        {/* Data quality badge (right-aligned) */}
        {confidence && (
          <div className="ml-auto">
            <TrustBadge
              source={`${(availability.readings_count || 0).toLocaleString()} releves`}
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

      {/* Row 2: Mode pills (only for multi-site) + Unit toggle (always) */}
      {(setMode || setUnit) && (
        <div className="flex items-center gap-3 flex-wrap">
          {/* Mode pills — visible only when multi-site selected */}
          {setMode && effectiveSiteIds.length > 1 && (
            <div className="flex gap-1 bg-gray-100 rounded-lg p-0.5">
              {MODE_ORDER.map(m => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={`px-3 py-1 rounded-md text-xs font-medium transition ${
                    mode === m ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {MODE_LABELS[m]}
                </button>
              ))}
            </div>
          )}

          {/* Unit toggle */}
          {setUnit && (
            <div className="flex gap-1 bg-gray-100 rounded-lg p-0.5">
              {UNIT_ORDER.map(u => (
                <button
                  key={u}
                  onClick={() => setUnit(u)}
                  className={`px-3 py-1 rounded-md text-xs font-medium transition ${
                    unit === u ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {UNIT_LABELS[u]}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Row 3: Actions (Save / Reset / Copy) + Presets */}
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
            <div className="relative">
              <button
                onClick={() => setShowPresets(v => !v)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition"
              >
                Presets ({savedPresets.length})
                <ChevronDown size={11} />
              </button>
              {showPresets && (
                <div className="absolute top-full left-0 mt-1 w-52 bg-white rounded-lg shadow-lg border border-gray-200 z-30 py-1">
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
                </div>
              )}
            </div>
          )}

          {/* Reset */}
          {onReset && (
            <button
              onClick={onReset}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition"
              title="Reinitialiser les filtres"
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
    </div>
  );
}
