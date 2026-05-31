/**
 * PROMEOS — OffHoursSlotsTable (Sprint Énergie P3.2).
 *
 * Tableau « Top créneaux hors horaires » — affiche les `top_off_hours`
 * fournis par `/api/energy/off-hours-analysis`.
 *
 * Doctrine zéro calcul métier frontend : status, reason, ranking arrivent
 * du backend.
 *
 * Props :
 * - slots       : list[OffHoursSlot]
 * - loading     : bool
 */
import React from 'react';
import { Clock, HelpCircle } from 'lucide-react';

const STATUS_TINT = {
  sain: 'text-emerald-700 bg-emerald-50',
  vigilance: 'text-amber-700 bg-amber-50',
  critique: 'text-red-700 bg-red-50',
};

const STATUS_LABEL = {
  sain: 'Sain',
  vigilance: 'Vigilance',
  critique: 'Critique',
};

function fmtNumber(v, decimals = 2) {
  if (v === null || v === undefined) return '—';
  return Number(v).toLocaleString('fr-FR', { maximumFractionDigits: decimals });
}

function ProvenanceDot({ provenance }) {
  if (!provenance?.service) return null;
  return (
    <span className="relative inline-block group" data-testid="off-hours-slot-provenance">
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

export default function OffHoursSlotsTable({
  slots,
  loading = false,
  className = '',
  testId = 'off-hours-slots-table',
}) {
  if (loading) {
    return (
      <div
        className={`rounded-xl border border-gray-200 bg-white p-4 ${className}`}
        data-testid="off-hours-slots-loading"
      >
        <div className="animate-pulse h-32 bg-gray-100 rounded" />
      </div>
    );
  }

  if (!Array.isArray(slots) || slots.length === 0) {
    return null;
  }

  return (
    <div
      className={`rounded-xl border border-gray-200 bg-white p-4 ${className}`}
      data-testid={testId}
    >
      <h3 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-1.5">
        <Clock size={14} className="text-blue-600" aria-hidden="true" />
        Top créneaux hors horaires
      </h3>
      <table className="w-full text-xs">
        <thead className="text-gray-500 border-b border-gray-100">
          <tr>
            <th className="text-left font-medium py-1.5">Jour</th>
            <th className="text-left font-medium py-1.5">Heure</th>
            <th className="text-right font-medium py-1.5">kWh</th>
            <th className="text-right font-medium py-1.5">kW moyen</th>
            <th className="text-left font-medium py-1.5 pl-3">Statut</th>
            <th className="text-left font-medium py-1.5 pl-3">Motif</th>
            <th className="text-right font-medium py-1.5 w-6"></th>
          </tr>
        </thead>
        <tbody>
          {slots.map((s, i) => (
            <tr
              key={`${s.day_of_week}-${s.hour}-${i}`}
              className="border-b border-gray-50 last:border-0"
              data-testid={`off-hours-slot-row-${i}`}
              data-status={s.status}
              data-day={s.day_of_week}
            >
              <td className="py-1.5 text-gray-800 font-medium">{s.label}</td>
              <td className="py-1.5 font-mono text-gray-600">{String(s.hour).padStart(2, '0')}h</td>
              <td className="py-1.5 text-right font-mono text-gray-800">{fmtNumber(s.kwh)}</td>
              <td className="py-1.5 text-right font-mono text-gray-600">{fmtNumber(s.kw_avg)}</td>
              <td className="py-1.5 pl-3">
                <span
                  className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                    STATUS_TINT[s.status] || STATUS_TINT.sain
                  }`}
                >
                  {STATUS_LABEL[s.status] || s.status}
                </span>
              </td>
              <td className="py-1.5 pl-3 text-gray-600 italic">{s.reason || '—'}</td>
              <td className="py-1.5 text-right">
                <ProvenanceDot provenance={s.provenance} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
