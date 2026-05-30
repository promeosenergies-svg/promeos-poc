/**
 * PROMEOS — DisplacementSimulationCard (Sprint P1.S6).
 *
 * Affiche `simulation` (EnergyDisplacementSimulation) du payload
 * `/api/energy/market-exposure` :
 *   - label
 *   - flexible_share_pct
 *   - estimated_delta_eur
 *   - warning (par défaut backend :
 *     « Simulation indicative — ne constitue pas une promesse d'économie. »)
 *
 * Doctrine : warning OBLIGATOIRE, aucune promesse d'économie certaine,
 * aucun calcul FE.
 */
import { AlertTriangle, FlaskConical } from 'lucide-react';

const DEFAULT_WARNING = "Simulation indicative — ne constitue pas une promesse d'économie.";

function fmtEur(v) {
  if (v === null || v === undefined) return '—';
  const num = Number(v);
  const sign = num > 0 ? '+' : '';
  return `${sign}${num.toLocaleString('fr-FR', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
  })}`;
}

function fmtPct(v) {
  if (v === null || v === undefined) return '—';
  return `${Number(v).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} %`;
}

export default function DisplacementSimulationCard({
  simulation,
  className = '',
  testId = 'displacement-simulation-card',
}) {
  if (!simulation) return null;
  const warning = simulation.warning || DEFAULT_WARNING;
  const delta = simulation.estimated_delta_eur;
  const deltaColour =
    delta == null
      ? 'text-gray-500'
      : delta < 0
        ? 'text-emerald-700'
        : delta > 0
          ? 'text-red-700'
          : 'text-gray-500';

  return (
    <div
      className={`rounded-xl border border-blue-200 bg-blue-50/40 p-4 space-y-3 ${className}`}
      data-testid={testId}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <FlaskConical size={14} className="text-blue-600" aria-hidden="true" />
          <h3 className="text-sm font-semibold text-blue-900">
            {simulation.label || 'Simulation indicative'}
          </h3>
        </div>
        <span
          className="text-[9px] uppercase tracking-wide px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 font-semibold"
          data-testid="simulation-status-badge"
        >
          Simulation
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3 text-xs">
        <div>
          <p className="text-[10px] uppercase tracking-wide text-blue-700 font-medium">
            Part flexible
          </p>
          <p className="text-base font-mono font-semibold text-blue-900 mt-0.5">
            {fmtPct(simulation.flexible_share_pct)}
          </p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wide text-blue-700 font-medium">
            Delta estimé
          </p>
          <p
            className={`text-base font-mono font-semibold mt-0.5 ${deltaColour}`}
            data-testid="simulation-delta-eur"
          >
            {fmtEur(delta)}
          </p>
        </div>
      </div>
      <div
        className="rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-[11px] text-amber-800 flex items-start gap-2"
        role="note"
        data-testid="simulation-warning"
      >
        <AlertTriangle size={12} className="shrink-0 mt-0.5" aria-hidden="true" />
        <p className="font-medium">{warning}</p>
      </div>
    </div>
  );
}
