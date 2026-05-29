/**
 * PROMEOS — TopPeaksTable (Sprint P1.S3a UI Courbe de charge).
 *
 * Affichage des top pics consommation issus du backend
 * (`/api/energy/loadcurve` ne fournit pas encore ce champ — placeholder
 * documenté en attente). Pas de calcul métier FE : si le champ
 * `topPeaks` n'est pas fourni par l'API, on affiche un EmptyState
 * informatif explicitement non-bloquant.
 *
 * Props :
 * - points        : liste éventuelle [{ timestamp, kw_avg, kwh,
 *                                       rank, provenance }]
 * - granularity   : pour formatter timestamps
 * - loading       : bool
 */
import { EmptyState } from '../index';
import { TrendingUp } from 'lucide-react';

const TS_FMT = (ts) =>
  new Date(ts).toLocaleString('fr-FR', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });

function fmtNumber(v, decimals = 2) {
  if (v === null || v === undefined) return '—';
  return Number(v).toLocaleString('fr-FR', { maximumFractionDigits: decimals });
}

export default function TopPeaksTable({
  points,
  // `granularity` est réservé pour un futur formatage (ex: jour vs heure)
  // et reste accepté en prop pour compatibilité avec LoadCurveTab.
  granularity: _granularity = 'hour',
  loading = false,
  className = '',
}) {
  if (loading) {
    return (
      <div
        className={`rounded-xl border border-gray-200 bg-white p-4 ${className}`}
        data-testid="top-peaks-loading"
      >
        <div className="animate-pulse h-32 bg-gray-100 rounded" />
      </div>
    );
  }

  // L'endpoint /api/energy/loadcurve ne fournit pas encore de top_peaks.
  // Pas de calcul FE : on affiche un EmptyState explicite non-bloquant
  // jusqu'à extension backend P1.S3b ou P1.S4.
  if (!Array.isArray(points) || points.length === 0) {
    return (
      <div
        className={`rounded-xl border border-gray-200 bg-white p-4 ${className}`}
        data-testid="top-peaks-empty"
      >
        <EmptyState
          icon={TrendingUp}
          title="Top pics indisponible dans cette version"
          text="Le classement des pics sera exposé par le backend dans un prochain sprint."
        />
      </div>
    );
  }

  return (
    <div
      className={`rounded-xl border border-gray-200 bg-white p-4 ${className}`}
      data-testid="top-peaks-table"
    >
      <h3 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-1.5">
        <TrendingUp size={14} className="text-blue-600" aria-hidden="true" />
        Top pics
      </h3>
      <table className="w-full text-xs">
        <thead className="text-gray-500 border-b border-gray-100">
          <tr>
            <th className="text-left font-medium py-1.5">#</th>
            <th className="text-left font-medium py-1.5">Quand</th>
            <th className="text-right font-medium py-1.5">kW moyen</th>
            <th className="text-right font-medium py-1.5">kWh</th>
          </tr>
        </thead>
        <tbody>
          {points.map((p, i) => (
            <tr key={p.timestamp || i} className="border-b border-gray-50 last:border-0">
              <td className="py-1.5 text-gray-500">{p.rank ?? i + 1}</td>
              <td className="py-1.5 text-gray-800 font-medium">{TS_FMT(p.timestamp)}</td>
              <td className="py-1.5 text-right font-mono text-gray-700">{fmtNumber(p.kw_avg)}</td>
              <td className="py-1.5 text-right font-mono text-gray-700">{fmtNumber(p.kwh)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
