/**
 * PROMEOS — HeatmapLegend
 * Légende contextuelle pour la heatmap 7×24.
 * Échelle de couleur + guide d'interprétation + annotations automatiques.
 */

export default function HeatmapLegend({ schedule, stats, isExpert }) {
  const annotations = [];

  if (stats?.night_ratio > 0.15) {
    annotations.push({
      type: 'warn',
      text: `Consommation nocturne élevée (${Math.round(stats.night_ratio * 100)}% du total entre 22h et 6h)`,
    });
  }
  if (stats?.weekend_ratio > 0.1) {
    annotations.push({
      type: 'warn',
      text: `Weekend actif — ${Math.round(stats.weekend_ratio * 100)}% de consommation samedi-dimanche`,
    });
  } else if (stats?.weekend_ratio != null) {
    annotations.push({
      type: 'ok',
      text: 'Bonne coupure weekend — consommation minimale samedi-dimanche',
    });
  }
  if (stats?.off_hours_ratio > 0.3) {
    annotations.push({
      type: 'crit',
      text: `${Math.round(stats.off_hours_ratio * 100)}% de consommation hors horaires d'activité. Vérifiez la programmation.`,
    });
  }

  return (
    <div className="space-y-3 mb-4" data-testid="heatmap-legend">
      {/* Échelle de couleur */}
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <span>Faible</span>
        <div className="flex-1 h-2 rounded-full bg-gradient-to-r from-green-200 via-yellow-200 to-red-400" />
        <span>Élevé</span>
      </div>

      {/* Guide rapide */}
      <div className="flex flex-wrap gap-3 text-xs">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-green-200" /> Normal
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-yellow-200" /> À surveiller
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-red-400" /> Anormal
        </span>
        {schedule && (
          <span className="text-gray-400 ml-2">
            Horaires déclarés : {schedule.open_time || '?'}–{schedule.close_time || '?'} (
            {schedule.open_days || 'lun-ven'})
          </span>
        )}
      </div>

      {/* Annotations */}
      {annotations.length > 0 && (
        <div className="space-y-1">
          {annotations.map((a, i) => (
            <div
              key={i}
              className={`text-xs px-3 py-1.5 rounded ${
                a.type === 'ok'
                  ? 'bg-green-50 text-green-700'
                  : a.type === 'warn'
                    ? 'bg-amber-50 text-amber-700'
                    : 'bg-red-50 text-red-700'
              }`}
            >
              {a.type === 'ok' ? '✅' : '⚠️'} {a.text}
            </div>
          ))}
        </div>
      )}

      {/* Expert: raw values */}
      {isExpert && stats && (
        <div className="text-[10px] text-gray-400 flex gap-4">
          {stats.avg_kwh != null && <span>Moy: {stats.avg_kwh} kWh</span>}
          {stats.night_ratio != null && <span>Nuit: {Math.round(stats.night_ratio * 100)}%</span>}
          {stats.weekend_ratio != null && <span>WE: {Math.round(stats.weekend_ratio * 100)}%</span>}
          {stats.off_hours_ratio != null && (
            <span>Hors-h: {Math.round(stats.off_hours_ratio * 100)}%</span>
          )}
        </div>
      )}
    </div>
  );
}
