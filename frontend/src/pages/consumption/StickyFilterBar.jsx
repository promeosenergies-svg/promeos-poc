/**
 * PROMEOS — StickyFilterBar (Consumption Explorer)
 * Unified sticky bar: Site + Energy toggle + Period + Granularity (auto) + Data quality
 */
import { Zap, Flame } from 'lucide-react';
import { TrustBadge } from '../../ui';
import { computeGranularity } from './helpers';

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

export default function StickyFilterBar({
  siteId, setSiteId, sites,
  energyType, setEnergyType, availableTypes,
  days, setDays,
  availability,
}) {
  const gran = computeGranularity(days);
  const confidence = availability?.has_data
    ? (availability.readings_count > 1000 ? 'high' : availability.readings_count > 200 ? 'medium' : 'low')
    : null;

  return (
    <div className="sticky top-0 z-20 bg-white/95 backdrop-blur border-b border-gray-100 -mx-4 px-4 py-2.5 md:-mx-6 md:px-6">
      <div className="flex items-center gap-3 flex-wrap">
        {/* Site selector */}
        {sites?.length > 1 && (
          <select
            value={siteId || ''}
            onChange={(e) => setSiteId(Number(e.target.value))}
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
    </div>
  );
}
