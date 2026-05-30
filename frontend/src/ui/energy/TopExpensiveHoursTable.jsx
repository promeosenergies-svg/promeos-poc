/**
 * PROMEOS — TopExpensiveHoursTable (Sprint P1.S6).
 *
 * Affiche `top_expensive_hours[]` du payload `/api/energy/market-exposure`.
 * Chaque heure expose :
 *   - timestamp
 *   - spot_price_eur_mwh
 *   - kwh
 *   - cost_eur
 *   - rank (1 = la plus coûteuse — fourni backend)
 *   - recommended_action (string FR backend)
 *   - provenance
 *
 * Doctrine : pas de tri métier FE. Si backend fournit `rank`, on s'en
 * sert pour ordre visuel ; sinon ordre API préservé.
 */
import { TrendingUp, HelpCircle } from 'lucide-react';

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

function fmtNumber(v, decimals = 1) {
  if (v === null || v === undefined) return '—';
  return Number(v).toLocaleString('fr-FR', { maximumFractionDigits: decimals });
}

function ProvenanceDot({ provenance }) {
  if (!provenance?.service) return null;
  return (
    <span className="relative inline-block group" data-testid="top-hour-provenance">
      <HelpCircle size={11} className="text-gray-300 hover:text-gray-500 cursor-help" />
      <span className="absolute right-0 top-4 z-10 hidden group-hover:block w-56 rounded-lg border border-gray-200 bg-white p-2 text-[10px] text-gray-700 shadow-lg">
        <span className="block text-gray-500">Service</span>
        <span className="block font-mono break-words">{provenance.service}</span>
        {provenance.formula && (
          <>
            <span className="block text-gray-500 mt-1">Formule</span>
            <span className="block font-mono break-words">{provenance.formula}</span>
          </>
        )}
      </span>
    </span>
  );
}

export default function TopExpensiveHoursTable({
  topExpensiveHours,
  className = '',
  testId = 'top-expensive-hours-table',
}) {
  if (!Array.isArray(topExpensiveHours) || topExpensiveHours.length === 0) {
    return null;
  }

  // Tri visuel par rank si fourni, sinon ordre API préservé.
  const ordered = topExpensiveHours.every((h) => Number.isInteger(h.rank))
    ? [...topExpensiveHours].sort((a, b) => a.rank - b.rank)
    : topExpensiveHours;

  return (
    <div
      className={`rounded-xl border border-gray-200 bg-white p-4 ${className}`}
      data-testid={testId}
    >
      <h3 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-1.5">
        <TrendingUp size={14} className="text-red-600" aria-hidden="true" />
        Top heures chères
      </h3>
      <table className="w-full text-xs">
        <thead className="text-gray-500 border-b border-gray-100">
          <tr>
            <th className="text-left font-medium py-1.5 w-8">#</th>
            <th className="text-left font-medium py-1.5">Quand</th>
            <th className="text-right font-medium py-1.5">Spot €/MWh</th>
            <th className="text-right font-medium py-1.5">kWh</th>
            <th className="text-right font-medium py-1.5">Coût</th>
            <th className="text-left font-medium py-1.5 pl-4">Action conseillée</th>
            <th className="text-right font-medium py-1.5 w-6"></th>
          </tr>
        </thead>
        <tbody>
          {ordered.map((h, idx) => (
            <tr
              key={`${h.timestamp || idx}-${h.rank ?? idx}`}
              className="border-b border-gray-50 last:border-b-0"
              data-testid={`top-hour-row-${h.rank ?? idx + 1}`}
              data-rank={h.rank ?? idx + 1}
            >
              <td className="py-1.5 text-gray-500 font-mono">{h.rank ?? idx + 1}</td>
              <td className="py-1.5 text-gray-800 font-medium">{TS_FMT(h.timestamp)}</td>
              <td className="py-1.5 text-right font-mono text-gray-700">
                {fmtEurPerMwh(h.spot_price_eur_mwh)}
              </td>
              <td className="py-1.5 text-right font-mono text-gray-700">{fmtNumber(h.kwh, 1)}</td>
              <td className="py-1.5 text-right font-mono text-red-700">{fmtEur(h.cost_eur, 0)}</td>
              <td className="py-1.5 pl-4 text-gray-600 italic line-clamp-1">
                {h.recommended_action || '—'}
              </td>
              <td className="py-1.5 text-right">
                <ProvenanceDot provenance={h.provenance} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
