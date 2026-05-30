/**
 * PROMEOS — BaseloadComparisonCard (Sprint P1.S6).
 *
 * Affiche `baseload_comparison` du payload `/api/energy/market-exposure` :
 *   - real_profile_cost_eur (coût spot pondéré profil réel)
 *   - baseload_cost_eur     (coût spot ruban baseload équivalent)
 *   - delta_eur             (real - baseload ; > 0 = profil plus coûteux)
 *   - delta_eur_mwh         (delta moyen €/MWh)
 *   - formula               (description backend de la formule)
 *   - provenance
 *
 * Doctrine : aucun calcul métier FE. delta, ratio, signes sont tous
 * fournis par le backend.
 */
import { Layers, HelpCircle } from 'lucide-react';

function fmtEur(v, decimals = 0) {
  if (v === null || v === undefined) return '—';
  return Number(v).toLocaleString('fr-FR', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: decimals,
  });
}

function fmtEurPerMwh(v) {
  if (v === null || v === undefined) return '—';
  return `${Number(v).toLocaleString('fr-FR', { maximumFractionDigits: 2 })} €/MWh`;
}

function fmtDelta(v) {
  if (v === null || v === undefined) return null;
  const num = Number(v);
  const sign = num > 0 ? '+' : '';
  const colour = num > 0 ? 'text-red-700' : num < 0 ? 'text-emerald-700' : 'text-gray-500';
  return (
    <span
      className={`font-mono ${colour}`}
      data-testid="baseload-delta-eur"
      data-sign={num >= 0 ? 'positive' : 'negative'}
    >
      {sign}
      {Number(num).toLocaleString('fr-FR', {
        style: 'currency',
        currency: 'EUR',
        maximumFractionDigits: 0,
      })}
    </span>
  );
}

function fmtDeltaMwh(v) {
  if (v === null || v === undefined) return null;
  const num = Number(v);
  const sign = num > 0 ? '+' : '';
  return `${sign}${Number(num).toLocaleString('fr-FR', { maximumFractionDigits: 2 })} €/MWh`;
}

function ProvenanceTooltip({ provenance, formula }) {
  if (!provenance && !formula) return null;
  return (
    <span className="relative inline-block group" data-testid="baseload-provenance">
      <HelpCircle size={13} className="text-gray-300 hover:text-gray-500 cursor-help" />
      <div className="absolute right-0 top-5 z-10 hidden group-hover:block w-72 rounded-lg border border-gray-200 bg-white p-3 text-xs text-gray-700 shadow-lg">
        {provenance?.source && (
          <>
            <p className="text-gray-500">Source</p>
            <p className="font-mono break-words">{provenance.source}</p>
          </>
        )}
        {provenance?.service && (
          <>
            <p className="text-gray-500 mt-1">Service</p>
            <p className="font-mono text-[11px] break-words">{provenance.service}</p>
          </>
        )}
        {formula && (
          <>
            <p className="text-gray-500 mt-1">Formule</p>
            <p className="text-[11px]">{formula}</p>
          </>
        )}
      </div>
    </span>
  );
}

export default function BaseloadComparisonCard({
  baseloadComparison,
  className = '',
  testId = 'baseload-comparison-card',
}) {
  if (!baseloadComparison) return null;
  const {
    real_profile_cost_eur,
    baseload_cost_eur,
    delta_eur,
    delta_eur_mwh,
    formula,
    provenance,
  } = baseloadComparison;

  return (
    <div
      className={`rounded-xl border border-gray-200 bg-white p-4 ${className}`}
      data-testid={testId}
    >
      <div className="flex items-start justify-between gap-2 mb-3">
        <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-1.5">
          <Layers size={14} className="text-blue-600" aria-hidden="true" />
          Comparaison baseload
        </h3>
        <ProvenanceTooltip provenance={provenance} formula={formula} />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
        <div
          className="rounded-lg border border-gray-200 bg-gray-50 p-3"
          data-testid="baseload-real-profile"
        >
          <p className="text-[10px] uppercase tracking-wide text-gray-500 font-medium">
            Coût profil réel
          </p>
          <p className="text-lg font-bold font-mono text-gray-800 mt-1">
            {fmtEur(real_profile_cost_eur)}
          </p>
        </div>
        <div
          className="rounded-lg border border-blue-200 bg-blue-50 p-3"
          data-testid="baseload-cost"
        >
          <p className="text-[10px] uppercase tracking-wide text-blue-700 font-medium">
            Coût ruban baseload
          </p>
          <p className="text-lg font-bold font-mono text-blue-800 mt-1">
            {fmtEur(baseload_cost_eur)}
          </p>
        </div>
        <div
          className="rounded-lg border border-gray-200 bg-white p-3"
          data-testid="baseload-delta"
        >
          <p className="text-[10px] uppercase tracking-wide text-gray-500 font-medium">
            Écart vs baseload
          </p>
          <p className="text-lg font-bold mt-1">{fmtDelta(delta_eur)}</p>
          {delta_eur_mwh != null && (
            <p className="text-[10px] text-gray-500 mt-0.5">{fmtDeltaMwh(delta_eur_mwh)}</p>
          )}
        </div>
      </div>
      {formula && (
        <p className="text-[10px] text-gray-400 italic mt-2" data-testid="baseload-formula">
          {formula}
        </p>
      )}
    </div>
  );
}
