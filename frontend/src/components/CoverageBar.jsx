/**
 * PROMEOS — CoverageBar (V67)
 * Barre visuelle proportionnelle : covered (vert) | partial (orange) | missing (rouge).
 * Props: { covered, partial, missing, total, minMonth, maxMonth }
 */

export default function CoverageBar({ covered = 0, partial = 0, missing = 0, total = 0, minMonth, maxMonth }) {
  if (total === 0) return null;

  const pctCovered = Math.round((covered / total) * 100);
  const pctPartial = Math.round((partial / total) * 100);
  const pctMissing = 100 - pctCovered - pctPartial;

  return (
    <div className="space-y-1">
      <div className="flex h-3 rounded-full overflow-hidden bg-gray-100">
        {pctCovered > 0 && (
          <div
            className="bg-green-500 transition-all"
            style={{ width: `${pctCovered}%` }}
            title={`${covered} mois couverts`}
          />
        )}
        {pctPartial > 0 && (
          <div
            className="bg-orange-400 transition-all"
            style={{ width: `${pctPartial}%` }}
            title={`${partial} mois partiels`}
          />
        )}
        {pctMissing > 0 && (
          <div
            className="bg-red-400 transition-all"
            style={{ width: `${Math.max(pctMissing, 0)}%` }}
            title={`${missing} mois manquants`}
          />
        )}
      </div>
      {(minMonth || maxMonth) && (
        <div className="flex justify-between text-xs text-gray-400">
          <span>{minMonth || ''}</span>
          <span>{maxMonth || ''}</span>
        </div>
      )}
    </div>
  );
}
