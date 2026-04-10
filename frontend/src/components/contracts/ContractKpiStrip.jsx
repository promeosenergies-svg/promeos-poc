/**
 * PROMEOS — Contrats V2 KPI Strip (5 cartes)
 */
import { KpiCardCompact as _KpiCardCompact } from '../../ui';
import { FileText, AlertTriangle, Zap, DollarSign, TrendingUp } from 'lucide-react';

const KPI_DEFS = [
  {
    key: 'active_cadres',
    label: 'Contrats actifs',
    icon: FileText,
    color: 'text-emerald-600',
    accent: 'border-l-emerald-500',
  },
  {
    key: 'expiring_90d',
    label: 'Expirent <90j',
    icon: AlertTriangle,
    color: 'text-amber-600',
    accent: 'border-l-amber-500',
  },
  { key: 'total_volume_mwh', label: 'Volume engage', icon: Zap, unit: 'MWh/an' },
  { key: 'total_budget_eur', label: 'Budget annuel', icon: DollarSign, format: 'eur' },
  {
    key: 'total_shadow_gap_eur',
    label: 'Ecart shadow billing',
    icon: TrendingUp,
    color: 'text-red-600',
    accent: 'border-l-red-500',
    format: 'eur_signed',
  },
];

function fmtVal(value, format) {
  if (value == null) return '—';
  if (format === 'eur') return `${Math.round(value / 1000)} k€`;
  if (format === 'eur_signed')
    return `${value >= 0 ? '+' : ''}${Math.round(value).toLocaleString('fr-FR')} €`;
  if (typeof value === 'number') return value.toLocaleString('fr-FR');
  return value;
}

export default function ContractKpiStrip({ kpis = {} }) {
  return (
    <div className="grid grid-cols-5 gap-2.5 mb-4">
      {KPI_DEFS.map(({ key, label, icon: Icon, color, accent, unit, format }) => (
        <div
          key={key}
          className={`bg-white border border-gray-200 rounded-lg p-3.5 transition hover:shadow-sm ${accent ? `border-l-[3px] ${accent}` : ''}`}
        >
          <div className="flex items-center gap-1.5 mb-0.5">
            <Icon size={12} className={color || 'text-gray-400'} />
            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
              {label}
            </span>
          </div>
          <div className={`text-xl font-extrabold tracking-tight ${color || 'text-gray-900'}`}>
            {fmtVal(kpis[key], format)}
            {unit && <span className="text-xs font-medium text-gray-400 ml-1">{unit}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}
