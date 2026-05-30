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
import { AlertTriangle, FlaskConical, HelpCircle } from 'lucide-react';

const DEFAULT_WARNING = "Simulation indicative — ne constitue pas une promesse d'économie.";

function SimulationProvenanceDot({ provenance }) {
  if (!provenance?.service) return null;
  return (
    <span className="relative inline-block group" data-testid="simulation-provenance">
      <HelpCircle size={11} className="text-blue-300 hover:text-blue-500 cursor-help" />
      <span className="absolute right-0 top-4 z-20 hidden group-hover:block w-60 rounded-lg border border-gray-200 bg-white p-2 text-[10px] text-gray-700 shadow-lg">
        {provenance.source && (
          <>
            <span className="block text-gray-500">Source</span>
            <span className="block font-mono break-words">{provenance.source}</span>
          </>
        )}
        <span className="block text-gray-500 mt-1">Service</span>
        <span className="block font-mono break-words">{provenance.service}</span>
        {provenance.formula && (
          <>
            <span className="block text-gray-500 mt-1">Formule</span>
            <span className="block font-mono break-words">{provenance.formula}</span>
          </>
        )}
        {provenance.period && (
          <>
            <span className="block text-gray-500 mt-1">Période</span>
            <span className="block">{provenance.period}</span>
          </>
        )}
        {typeof provenance.confidence === 'number' && (
          <>
            <span className="block text-gray-500 mt-1">Confiance</span>
            <span className="block">{Math.round(provenance.confidence * 100)} %</span>
          </>
        )}
      </span>
    </span>
  );
}

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
        <div className="flex items-center gap-1.5">
          <SimulationProvenanceDot provenance={simulation.provenance} />
          <span
            className="text-[9px] uppercase tracking-wide px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 font-semibold"
            data-testid="simulation-status-badge"
          >
            Simulation
          </span>
        </div>
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
