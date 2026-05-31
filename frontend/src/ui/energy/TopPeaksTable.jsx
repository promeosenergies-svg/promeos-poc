/**
 * PROMEOS — TopPeaksTable (Sprint P3.1).
 *
 * Affichage des pics de puissance critiques sur la période, issus du
 * backend `/api/energy/loadcurve.top_peaks` (extension P3.1).
 *
 * Doctrine zéro calcul métier frontend : aucun ranking, aucune
 * détection de pic, aucune action conseillée générée FE — tout vient
 * du backend.
 *
 * Props :
 * - points        : liste [{ rank, timestamp, kwh, kw_avg, period_label,
 *                            context, recommended_action, quality_status,
 *                            provenance }] (cf. EnergyTopPeak Pydantic)
 * - loading       : bool
 */
import React from 'react';
import { EmptyState } from '../index';
import { HelpCircle, TrendingUp } from 'lucide-react';

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

function fmtNumber(v, decimals = 2) {
  if (v === null || v === undefined) return '—';
  return Number(v).toLocaleString('fr-FR', { maximumFractionDigits: decimals });
}

function ProvenanceDot({ provenance }) {
  if (!provenance?.service) return null;
  return (
    <span className="relative inline-block group" data-testid="top-peak-provenance">
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

export default function TopPeaksTable({
  points,
  granularity: _granularity = 'hour',
  loading = false,
  className = '',
  testId = 'top-peaks-table',
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

  if (!Array.isArray(points) || points.length === 0) {
    return (
      <div
        className={`rounded-xl border border-gray-200 bg-white p-4 ${className}`}
        data-testid="top-peaks-empty"
      >
        <EmptyState
          icon={TrendingUp}
          title="Aucun pic de puissance significatif sur la période."
          text="Élargir la période ou affiner la granularité pour faire ressortir des pics."
        />
      </div>
    );
  }

  // Tri visuel par rank si fourni, sinon ordre API préservé.
  const ordered = points.every((p) => Number.isInteger(p.rank))
    ? [...points].sort((a, b) => a.rank - b.rank)
    : points;

  return (
    <div
      className={`rounded-xl border border-gray-200 bg-white p-4 ${className}`}
      data-testid={testId}
    >
      <h3 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-1.5">
        <TrendingUp size={14} className="text-blue-600" aria-hidden="true" />
        Pics de puissance
      </h3>
      <table className="w-full text-xs">
        <thead className="text-gray-500 border-b border-gray-100">
          <tr>
            <th className="text-left font-medium py-1.5 w-8">#</th>
            <th className="text-left font-medium py-1.5">Créneau</th>
            <th className="text-right font-medium py-1.5">kW moyen</th>
            <th className="text-right font-medium py-1.5">kWh</th>
            <th className="text-left font-medium py-1.5 pl-4">Action conseillée</th>
            <th className="text-right font-medium py-1.5 w-6"></th>
          </tr>
        </thead>
        <tbody>
          {ordered.map((p, i) => (
            <tr
              key={`${p.timestamp || i}-${p.rank ?? i}`}
              className="border-b border-gray-50 last:border-0"
              data-testid={`top-peak-row-${p.rank ?? i + 1}`}
              data-rank={p.rank ?? i + 1}
            >
              <td className="py-1.5 text-gray-500 font-mono">{p.rank ?? i + 1}</td>
              <td className="py-1.5 text-gray-800">
                <span className="font-medium">{p.period_label || TS_FMT(p.timestamp)}</span>
                {p.context && (
                  <span className="block text-[10px] text-gray-400 italic">{p.context}</span>
                )}
              </td>
              <td className="py-1.5 text-right font-mono text-red-700">{fmtNumber(p.kw_avg)}</td>
              <td className="py-1.5 text-right font-mono text-gray-700">{fmtNumber(p.kwh)}</td>
              <td className="py-1.5 pl-4 text-gray-600 italic line-clamp-1">
                {p.recommended_action || '—'}
              </td>
              <td className="py-1.5 text-right">
                <ProvenanceDot provenance={p.provenance} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
