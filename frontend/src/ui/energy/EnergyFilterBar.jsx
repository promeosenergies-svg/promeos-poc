/**
 * PROMEOS — EnergyFilterBar (Sprint P1.S3a UI Courbe de charge).
 *
 * Composant de filtre transversal énergie. Pur display : émet `onChange`
 * sans calculer aucune donnée métier. Les options sont des constantes
 * documentées (cf. contrat API /api/energy/loadcurve).
 *
 * Props :
 * - scope         : { kind, id, label } (lecture seule, vient du ScopeContext)
 * - period        : '7d' | '30d' | '90d' | 'custom'
 * - granularity   : '15min' | '30min' | 'hour' | 'day' | 'month' | 'year'
 * - compare       : 'none' | 'n-1' | 'baseline'
 * - display       : 'kwh' | 'kw'
 * - onChange      : (next) => void
 */
import { Activity, Layers, RefreshCw } from 'lucide-react';

const PERIOD_OPTIONS = [
  { value: '7d', label: '7 jours' },
  { value: '30d', label: '30 jours' },
  { value: '90d', label: '90 jours' },
];

const GRANULARITY_OPTIONS = [
  { value: '15min', label: '15 min', hint: '≤ 7 j' },
  { value: '30min', label: '30 min', hint: '≤ 30 j' },
  { value: 'hour', label: '1 h', hint: '≤ 90 j' },
  { value: 'day', label: '1 j', hint: '' },
  { value: 'month', label: '1 mois', hint: '' },
  { value: 'year', label: '1 an', hint: '' },
];

const COMPARE_OPTIONS = [
  { value: 'none', label: 'Aucune' },
  { value: 'n-1', label: 'N-1' },
  { value: 'baseline', label: 'Baseline' },
];

const DISPLAY_OPTIONS = [
  { value: 'kwh', label: 'kWh' },
  { value: 'kw', label: 'kW' },
];

function FilterGroup({ label, icon: Icon, children }) {
  return (
    <div className="flex items-center gap-1.5 text-xs">
      {Icon && <Icon size={12} className="text-gray-400" aria-hidden="true" />}
      <span className="text-gray-500 font-medium">{label}</span>
      {children}
    </div>
  );
}

function SegmentedSelect({ value, options, onChange, ariaLabel }) {
  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className="inline-flex rounded-lg border border-gray-200 bg-white overflow-hidden"
    >
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            title={opt.hint || opt.label}
            className={`px-2.5 py-1 text-xs font-medium transition ${
              active ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-50'
            }`}
            aria-pressed={active}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

export default function EnergyFilterBar({
  scope,
  period = '30d',
  granularity = 'hour',
  compare = 'none',
  display = 'kwh',
  onChange,
  className = '',
}) {
  const emit = (patch) => {
    if (typeof onChange === 'function') {
      onChange({ scope, period, granularity, compare, display, ...patch });
    }
  };

  return (
    <div
      className={`flex flex-wrap items-center gap-x-4 gap-y-2 p-3 rounded-xl border border-gray-200 bg-gray-50 ${className}`}
      data-testid="energy-filter-bar"
    >
      <FilterGroup label="Site" icon={Layers}>
        <span className="text-sm font-medium text-gray-800" data-testid="filter-scope-label">
          {scope?.label || (scope?.id ? `#${scope.id}` : '—')}
        </span>
      </FilterGroup>

      <FilterGroup label="Période">
        <SegmentedSelect
          value={period}
          options={PERIOD_OPTIONS}
          onChange={(v) => emit({ period: v })}
          ariaLabel="Période"
        />
      </FilterGroup>

      <FilterGroup label="Granularité" icon={Activity}>
        <SegmentedSelect
          value={granularity}
          options={GRANULARITY_OPTIONS}
          onChange={(v) => emit({ granularity: v })}
          ariaLabel="Granularité"
        />
      </FilterGroup>

      <FilterGroup label="Comparer" icon={RefreshCw}>
        <SegmentedSelect
          value={compare}
          options={COMPARE_OPTIONS}
          onChange={(v) => emit({ compare: v })}
          ariaLabel="Comparaison"
        />
      </FilterGroup>

      <FilterGroup label="Affichage">
        <SegmentedSelect
          value={display}
          options={DISPLAY_OPTIONS}
          onChange={(v) => emit({ display: v })}
          ariaLabel="Affichage"
        />
      </FilterGroup>
    </div>
  );
}

export { PERIOD_OPTIONS, GRANULARITY_OPTIONS, COMPARE_OPTIONS, DISPLAY_OPTIONS };
