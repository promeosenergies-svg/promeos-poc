/**
 * PROMEOS — FavorableHoursPanel (Sprint P1.S6).
 *
 * Affiche `favorable_hours[]` du payload `/api/energy/market-exposure`.
 * Catégorise visuellement par `reason` ∈ « prix bas » | « prix négatif »
 * | « heure solaire » (FavorableHourReason backend).
 *
 * Doctrine : aucun calcul métier FE. La catégorisation est faite par le
 * backend (`reason`). Le composant ne fait que regrouper visuellement.
 */
import { Sun, BatteryCharging, Leaf } from 'lucide-react';

const TS_FMT = (ts) => {
  try {
    return new Date(ts).toLocaleString('fr-FR', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return ts;
  }
};

function fmtEurPerMwh(v) {
  if (v === null || v === undefined) return '—';
  return `${Number(v).toLocaleString('fr-FR', { maximumFractionDigits: 2 })} €/MWh`;
}

const REASON_CONFIG = {
  'prix bas': {
    icon: BatteryCharging,
    tint: 'bg-emerald-50 border-emerald-200 text-emerald-700',
    label: 'Prix bas',
    pedagogie: 'Plages favorables pour démarrer une recharge ou un cycle planifié.',
  },
  'prix négatif': {
    icon: Leaf,
    tint: 'bg-blue-50 border-blue-200 text-blue-700',
    label: 'Prix négatif',
    pedagogie: 'Prix spot négatifs — opportunité de consommer payée par le marché.',
  },
  'heure solaire': {
    icon: Sun,
    tint: 'bg-amber-50 border-amber-200 text-amber-700',
    label: 'Heure solaire',
    pedagogie: 'Pic photovoltaïque — corrélation prix bas + production renouvelable.',
  },
};

function HourBadge({ hour }) {
  const cfg = REASON_CONFIG[hour.reason] || {
    icon: BatteryCharging,
    tint: 'bg-gray-50 border-gray-200 text-gray-600',
    label: hour.reason,
    pedagogie: '',
  };
  const Icon = cfg.icon;
  return (
    <div
      className={`rounded-lg border p-2 flex items-center gap-2 text-xs ${cfg.tint}`}
      data-testid="favorable-hour-row"
      data-reason={hour.reason}
    >
      <Icon size={14} className="shrink-0" aria-hidden="true" />
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate">{TS_FMT(hour.timestamp)}</p>
        <p className="text-[10px] font-mono opacity-70">{fmtEurPerMwh(hour.spot_price_eur_mwh)}</p>
      </div>
    </div>
  );
}

export default function FavorableHoursPanel({
  favorableHours,
  className = '',
  testId = 'favorable-hours-panel',
}) {
  if (!Array.isArray(favorableHours) || favorableHours.length === 0) {
    return null;
  }

  // Regroupement par reason (ordre canonique d'affichage).
  const REASONS_ORDER = ['prix bas', 'prix négatif', 'heure solaire'];
  const grouped = REASONS_ORDER.map((reason) => ({
    reason,
    cfg: REASON_CONFIG[reason],
    hours: favorableHours.filter((h) => h.reason === reason),
  })).filter((g) => g.hours.length > 0);

  return (
    <div
      className={`rounded-xl border border-gray-200 bg-white p-4 space-y-3 ${className}`}
      data-testid={testId}
    >
      <h3 className="text-sm font-semibold text-gray-800">Heures favorables</h3>
      {grouped.map(({ reason, cfg, hours }) => (
        <div key={reason} data-testid={`favorable-group-${reason.replace(/\s+/g, '-')}`}>
          <p className="text-[11px] text-gray-500 mb-1.5 flex items-center gap-1.5">
            <cfg.icon size={11} aria-hidden="true" />
            {cfg.label} <span className="font-mono">({hours.length})</span> · {cfg.pedagogie}
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
            {hours.slice(0, 8).map((h, i) => (
              <HourBadge key={`${reason}-${i}`} hour={h} />
            ))}
          </div>
          {hours.length > 8 && (
            <p className="text-[10px] text-gray-400 italic mt-1">+{hours.length - 8} autres…</p>
          )}
        </div>
      ))}
    </div>
  );
}
