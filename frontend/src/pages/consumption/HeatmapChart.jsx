/**
 * PROMEOS — HeatmapChart (HP/HC 7x24 grid)
 * Cells colored by HP (red) / HC (blue), intensity = kWh.
 * P1-2: Clickable cells with drill-down callback + tooltip + filter ouvre/weekend.
 */
import { useState } from 'react';

const DAY_LABELS = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];

function cellColor(avgKwh, isHP, maxKwh) {
  const intensity = maxKwh > 0 ? Math.min(avgKwh / maxKwh, 1) : 0;
  const alpha = 0.15 + intensity * 0.7;
  if (isHP) return `rgba(239, 68, 68, ${alpha})`; // red
  return `rgba(59, 130, 246, ${alpha})`; // blue
}

export default function HeatmapChart({ data, unit = 'kWh', onCellClick, filter = 'all' }) {
  const [hover, setHover] = useState(null);

  if (!data?.length) return null;

  // Filter: 'all', 'weekday' (Lun-Ven), 'weekend' (Sam-Dim)
  const visibleDays = filter === 'weekday' ? [0,1,2,3,4]
    : filter === 'weekend' ? [5,6]
    : [0,1,2,3,4,5,6];

  const filteredData = data.filter(c => visibleDays.includes(c.day));
  const maxKwh = Math.max(...filteredData.map(c => c.avg_kwh), 0.01);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-4 text-xs text-gray-500">
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-red-400" /> HP
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-blue-400" /> HC
        </div>
        <span className="ml-auto">Intensite = consommation moyenne ({unit})</span>
        {onCellClick && <span className="text-blue-500">Cliquez sur un creneau pour le detail</span>}
      </div>

      <div className="overflow-x-auto">
        <table className="border-collapse">
          <thead>
            <tr>
              <th className="w-10" />
              {Array.from({ length: 24 }, (_, h) => (
                <th key={h} className="text-[10px] text-gray-400 font-normal px-0.5 text-center w-7">
                  {h}h
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibleDays.map((dow) => (
              <tr key={dow}>
                <td className="text-[10px] text-gray-500 font-medium pr-1 text-right">{DAY_LABELS[dow]}</td>
                {Array.from({ length: 24 }, (_, h) => {
                  const cell = filteredData.find(c => c.day === dow && c.hour === h) || { avg_kwh: 0, period: 'HC' };
                  const isHP = cell.period === 'HP';
                  const bg = cellColor(cell.avg_kwh, isHP, maxKwh);
                  const isHovered = hover?.day === dow && hover?.hour === h;

                  return (
                    <td
                      key={h}
                      className="p-0"
                      onMouseEnter={() => setHover({ day: dow, hour: h, ...cell })}
                      onMouseLeave={() => setHover(null)}
                      onClick={() => onCellClick?.({ day: dow, dayLabel: DAY_LABELS[dow], hour: h, ...cell })}
                    >
                      <div
                        className={`w-7 h-6 rounded-sm border transition ${onCellClick ? 'cursor-pointer' : ''} ${isHovered ? 'border-gray-500 ring-1 ring-gray-300' : 'border-transparent'}`}
                        style={{ backgroundColor: bg }}
                        title={`${DAY_LABELS[dow]} ${h}h — ${cell.avg_kwh} ${unit} (${cell.period})`}
                      />
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Hover tooltip */}
      {hover && (
        <div className="text-xs text-gray-600 bg-gray-50 rounded-lg px-3 py-1.5 inline-flex items-center gap-3">
          <span className="font-medium">{DAY_LABELS[hover.day]} {hover.hour}h</span>
          <span>{hover.avg_kwh} {unit}</span>
          <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${hover.period === 'HP' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'}`}>
            {hover.period}
          </span>
        </div>
      )}
    </div>
  );
}
