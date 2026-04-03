import React from 'react';
import { useNavigate } from 'react-router-dom';

export default function ComplianceCard({ data, archetypeFilter }) {
  const navigate = useNavigate();
  if (!data) return null;

  const items = data.items || [];
  const bacsScore = data.bacs_score ?? data.usage_coverage?.coverage_pct ?? 0;
  const uncoveredThermal = items.filter((i) => i.concerned_by_bacs && !i.bacs_covered).length;

  const plural = uncoveredThermal > 1 ? 's' : '';
  const bacsTooltip = `Score BACS : ${Math.round(bacsScore)}/100 — ${
    uncoveredThermal > 0
      ? `${uncoveredThermal} usage${plural} thermique${plural} non équipé${plural} BACS (art. R175-2-3 du CCH).`
      : 'Tous les usages thermiques sont équipés BACS.'
  }`;

  const conformiteUrl = archetypeFilter
    ? `/conformite/tertiaire?archetype=${archetypeFilter}#bacs`
    : '/conformite/tertiaire#bacs';

  const statusCell = (ok) =>
    ok ? (
      <div className="text-center py-1 rounded bg-green-50 text-green-600 text-[10px] font-semibold">
        ✓
      </div>
    ) : (
      <div className="text-center py-1 rounded bg-red-50 text-red-600 text-[10px] font-semibold">
        ✗
      </div>
    );

  const tagCell = (label) => (
    <div className="text-center py-1 rounded bg-blue-50 text-blue-600 text-[10px] font-semibold">
      {label}
    </div>
  );

  const naCell = () => (
    <div className="text-center py-1 rounded bg-gray-100 text-gray-400 text-[10px]">—</div>
  );

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 overflow-hidden">
      <div className="flex justify-between items-center mb-3">
        <span className="text-[13px] font-semibold">Conformité usages</span>
        <span
          className="text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-50 text-amber-600 cursor-help"
          title={bacsTooltip}
          onClick={() => navigate(conformiteUrl)}
        >
          BACS {Math.round(bacsScore)}
        </span>
      </div>
      <div className="grid gap-0.5 text-[11px]" style={{ gridTemplateColumns: 'auto 1fr 1fr 1fr' }}>
        <div className="p-1.5" />
        <div className="p-1.5 text-center font-semibold text-gray-400 text-[10px]">BACS</div>
        <div className="p-1.5 text-center font-semibold text-gray-400 text-[10px]">DT</div>
        <div className="p-1.5 text-center font-semibold text-gray-400 text-[10px]">ISO</div>
        {items.slice(0, 4).map((item) => (
          <React.Fragment key={item.type || item.label}>
            <div className="p-1.5 font-medium">{item.label}</div>
            {item.concerned_by_bacs ? statusCell(item.bacs_covered) : naCell()}
            {item.concerned_by_dt ? statusCell(item.is_significant) : naCell()}
            {item.concerned_by_iso50001 ? tagCell('UES') : naCell()}
          </React.Fragment>
        ))}
      </div>
      {uncoveredThermal > 0 && (
        <div className="mt-2.5 p-2 bg-amber-50 rounded-md text-[11px] text-amber-600">
          ⚠ {uncoveredThermal} usage{plural} thermique{plural} sans BACS
        </div>
      )}
      <button
        onClick={() => navigate(conformiteUrl)}
        className="mt-2.5 w-full px-3 py-2 rounded-lg border border-gray-200 bg-white text-xs font-medium hover:border-blue-400 hover:text-blue-600 transition text-center"
      >
        Conformité détaillée →
      </button>
    </div>
  );
}
