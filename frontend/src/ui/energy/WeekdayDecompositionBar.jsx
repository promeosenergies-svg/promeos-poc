/**
 * PROMEOS — WeekdayDecompositionBar (Sprint P3.1).
 *
 * Affiche la décomposition de la consommation totale par jour de
 * semaine (Lun → Dim) sous forme de 7 barres horizontales avec
 * `total_kwh`, `share_pct`, `state` fournis par
 * `/api/energy/loadcurve.weekday_decomposition`.
 *
 * Doctrine zéro calcul métier frontend :
 * - Aucun recalcul de `share_pct` (fourni backend).
 * - Aucun choix de `state` (fourni backend).
 * - Couleurs purement cosmétiques selon `state`.
 *
 * Props :
 * - decomposition  : list [{ day_of_week, label, total_kwh,
 *                            avg_kwh_per_day, share_pct, n_days, state,
 *                            provenance }] (cf. EnergyWeekdayDecomposition)
 * - comparison     : { weekday_kwh, weekend_kwh, weekend_share_pct,
 *                      provenance } (optionnel, footer)
 */
import React from 'react';
import { HelpCircle } from 'lucide-react';

const STATE_TINT = {
  sain: 'bg-emerald-500',
  vigilance: 'bg-amber-500',
  critique: 'bg-red-500',
  inactif: 'bg-gray-200',
};

const STATE_LABEL = {
  sain: 'Sain',
  vigilance: 'Vigilance',
  critique: 'Critique',
  inactif: 'Inactif',
};

function fmtKwh(v) {
  if (v === null || v === undefined) return '—';
  return `${Number(v).toLocaleString('fr-FR', { maximumFractionDigits: 0 })} kWh`;
}

function fmtPct(v) {
  if (v === null || v === undefined) return '—';
  return `${Number(v).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} %`;
}

function ProvenanceDot({ provenance }) {
  if (!provenance?.service) return null;
  return (
    <span className="relative inline-block group" data-testid="weekday-decomposition-provenance">
      <HelpCircle size={11} className="text-gray-300 hover:text-gray-500 cursor-help" />
      <span className="absolute right-0 top-4 z-10 hidden group-hover:block w-60 rounded-lg border border-gray-200 bg-white p-2 text-[10px] text-gray-700 shadow-lg">
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

export default function WeekdayDecompositionBar({
  decomposition,
  comparison,
  className = '',
  testId = 'weekday-decomposition-bar',
}) {
  if (!Array.isArray(decomposition) || decomposition.length === 0) {
    return null;
  }

  // Calcul de l'échelle d'affichage : max share_pct rencontré (sinon 100)
  const maxShare = Math.max(
    ...decomposition.map((d) => (d.share_pct != null ? Number(d.share_pct) : 0)),
    1
  );
  const scale = maxShare > 0 ? 100 / maxShare : 1;

  // Provenance commune (la première barre)
  const commonProvenance = decomposition[0]?.provenance;

  return (
    <div
      className={`rounded-xl border border-gray-200 bg-white p-4 ${className}`}
      data-testid={testId}
    >
      <div className="flex items-baseline justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-800">Répartition par jour</h3>
        <ProvenanceDot provenance={commonProvenance} />
      </div>
      <ul className="space-y-1.5" role="list">
        {decomposition.map((row) => {
          const tint = STATE_TINT[row.state] || STATE_TINT.inactif;
          const width = row.share_pct != null ? Math.max(0, Number(row.share_pct) * scale) : 0;
          return (
            <li
              key={row.day_of_week}
              className="flex items-center gap-2 text-xs"
              data-testid={`weekday-decomp-row-${row.day_of_week}`}
              data-state={row.state}
            >
              <span className="w-16 text-gray-700 font-medium">{row.label}</span>
              <div className="flex-1 bg-gray-100 rounded-md h-4 overflow-hidden relative">
                <div
                  className={`h-full ${tint} transition-all`}
                  style={{ width: `${width}%` }}
                  aria-hidden="true"
                />
              </div>
              <span className="w-20 text-right font-mono text-gray-700">
                {fmtKwh(row.total_kwh)}
              </span>
              <span className="w-14 text-right font-mono text-gray-500">
                {fmtPct(row.share_pct)}
              </span>
              <span
                className="w-20 text-[10px] uppercase tracking-wide font-semibold text-right"
                style={{ color: row.state === 'inactif' ? '#9ca3af' : undefined }}
              >
                {STATE_LABEL[row.state] || row.state}
              </span>
            </li>
          );
        })}
      </ul>
      {comparison && (comparison.weekday_kwh != null || comparison.weekend_kwh != null) && (
        <div
          className="mt-3 pt-3 border-t border-gray-100 flex items-center gap-4 text-[11px] text-gray-600"
          data-testid="weekday-weekend-comparison"
        >
          <span>
            Jours ouvrés :{' '}
            <span className="font-mono text-gray-800">{fmtKwh(comparison.weekday_kwh)}</span>
          </span>
          <span>
            Week-end :{' '}
            <span className="font-mono text-gray-800">{fmtKwh(comparison.weekend_kwh)}</span>
          </span>
          <span>
            Part week-end :{' '}
            <span className="font-mono text-gray-800">{fmtPct(comparison.weekend_share_pct)}</span>
          </span>
        </div>
      )}
    </div>
  );
}
