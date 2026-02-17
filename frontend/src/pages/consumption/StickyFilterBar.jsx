/**
 * PROMEOS — StickyFilterBar v2 (Consumption Explorer)
 * Unified sticky bar: multi-site chips + mode selector + unit toggle
 *   + Energy toggle + Period + Granularity (auto) + Data quality
 *
 * Props:
 *   siteIds        {number[]}   selected site IDs
 *   setSiteIds     {fn}         update site IDs (max 5)
 *   sites          {object[]}   all available sites {id, nom}
 *   energyType     {string}
 *   setEnergyType  {fn}
 *   availableTypes {string[]}
 *   days           {number}
 *   setDays        {fn}
 *   mode           {string}     agrege|superpose|empile|separe
 *   setMode        {fn}
 *   unit           {string}     kwh|kw|eur
 *   setUnit        {fn}
 *   availability   {object}
 */
import { X, Zap, Flame } from 'lucide-react';
import { TrustBadge } from '../../ui';
import { computeGranularity, colorForSite } from './helpers';
import { MODE_LABELS, UNIT_LABELS, MAX_SITES } from './types';

const ENERGY_OPTIONS = [
  { value: 'electricity', label: 'Electricite', icon: Zap },
  { value: 'gas', label: 'Gaz', icon: Flame },
];

const PERIOD_OPTIONS = [
  { value: 30, label: '30 jours' },
  { value: 60, label: '60 jours' },
  { value: 90, label: '90 jours' },
  { value: 180, label: '6 mois' },
  { value: 365, label: '1 an' },
];

const GRAN_LABELS = { '30min': '30 min', '1h': '1 heure', jour: 'Jour', semaine: 'Semaine' };

const MODE_ORDER = ['agrege', 'superpose', 'empile', 'separe'];
const UNIT_ORDER = ['kwh', 'kw', 'eur'];

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
  // Period
  days,
  setDays,
  // Mode + Unit (new)
  mode,
  setMode,
  unit,
  setUnit,
  // Data quality
  availability,
}) {
  const gran = computeGranularity(days);
  const confidence = availability?.has_data
    ? (availability.readings_count > 1000 ? 'high' : availability.readings_count > 200 ? 'medium' : 'low')
    : null;

  // Resolve effective selected site IDs (multi or single legacy)
  const effectiveSiteIds = siteIds.length > 0 ? siteIds : (siteId ? [siteId] : []);
  const isMultiMode = sites.length > 1 && setSiteIds;

  const toggleSite = (id) => {
    if (!setSiteIds) {
      // Legacy single-site mode
      if (setSiteId) setSiteId(id);
      return;
    }
    if (effectiveSiteIds.includes(id)) {
      // Deselect — keep at least one site
      if (effectiveSiteIds.length > 1) {
        setSiteIds(effectiveSiteIds.filter(s => s !== id));
      }
    } else if (effectiveSiteIds.length < MAX_SITES) {
      setSiteIds([...effectiveSiteIds, id]);
    }
  };

  return (
    <div className="sticky top-0 z-20 bg-white/95 backdrop-blur border-b border-gray-100 -mx-4 px-4 py-2.5 md:-mx-6 md:px-6 space-y-2">

      {/* Row 1: Site chips + Energy toggle + Period + Granularity + Trust badge */}
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
          // Single-site legacy selector
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

        {/* Period dropdown */}
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white"
        >
          {PERIOD_OPTIONS.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>

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
    </div>
  );
}
