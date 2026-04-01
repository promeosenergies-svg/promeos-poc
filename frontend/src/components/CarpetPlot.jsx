/**
 * CarpetPlot — Heatmap 24h × N jours (Canvas)
 *
 * Différenciant marché PROMEOS : visualisation instantanée des patterns
 * de consommation (talon nocturne, pointes midi, weekends, dérives).
 *
 * Props :
 * - data: [{t: ISO_timestamp, v: number}] — données horaires (format EMS)
 * - days: nombre de jours à afficher (default 30)
 * - onCellClick: (day, hour, value) => void
 */
import { useState, useMemo, useRef, useEffect, useCallback } from 'react';

const MARGIN_LEFT = 36;
const MARGIN_TOP = 4;
const MARGIN_BOTTOM = 20;

const PALETTE = [
  '#E6F1FB', // < P10
  '#B5D4F4', // P10-P25
  '#85B7EB', // P25-P50
  '#378ADD', // P50-P75
  '#185FA5', // P75-P90
  '#0C447C', // P90-P95
  '#E24B4A', // > P95
];

function quantile(sorted, q) {
  const pos = (sorted.length - 1) * q;
  const base = Math.floor(pos);
  const rest = pos - base;
  if (sorted[base + 1] !== undefined) {
    return sorted[base] + rest * (sorted[base + 1] - sorted[base]);
  }
  return sorted[base];
}

function cellSize(canvasWidth, canvasHeight, numDays) {
  return {
    w: Math.max(Math.floor((canvasWidth - MARGIN_LEFT) / numDays), 4),
    h: Math.max(Math.floor((canvasHeight - MARGIN_TOP - MARGIN_BOTTOM) / 24), 8),
  };
}

function getColor(value, thresholds) {
  if (value == null) return '#F3F4F6';
  for (let i = thresholds.length - 1; i >= 0; i--) {
    if (value >= thresholds[i]) return PALETTE[i + 1] || PALETTE[PALETTE.length - 1];
  }
  return PALETTE[0];
}

export default function CarpetPlot({ data, days = 30, onCellClick }) {
  const canvasRef = useRef(null);
  const [tooltip, setTooltip] = useState(null);

  const { grid, dayLabels, thresholds, stats } = useMemo(() => {
    if (!data || data.length === 0) return { grid: [], dayLabels: [], thresholds: [], stats: null };

    const sorted = [...data].sort((a, b) => new Date(a.t) - new Date(b.t));

    const dayMap = new Map();
    for (const d of sorted) {
      const dt = new Date(typeof d.t === 'string' ? d.t.replace(' ', 'T') : d.t);
      // Consistent UTC for both day bucket and hour index
      const dayKey = dt.toISOString().slice(0, 10);
      const hour = dt.getUTCHours();
      if (!dayMap.has(dayKey)) dayMap.set(dayKey, new Array(24).fill(null));
      dayMap.get(dayKey)[hour] = d.v ?? null;
    }

    const allDays = [...dayMap.entries()].slice(-days);
    const grid = allDays.map(([, hours]) => hours);
    const dayLabels = allDays.map(([d]) => d);

    const allValues = grid
      .flat()
      .filter((v) => v != null)
      .sort((a, b) => a - b);
    if (allValues.length === 0) return { grid, dayLabels, thresholds: [], stats: null };

    const thresholds = [
      quantile(allValues, 0.1),
      quantile(allValues, 0.25),
      quantile(allValues, 0.5),
      quantile(allValues, 0.75),
      quantile(allValues, 0.9),
      quantile(allValues, 0.95),
    ];

    const stats = {
      min: allValues[0],
      max: allValues[allValues.length - 1],
      median: quantile(allValues, 0.5),
    };

    return { grid, dayLabels, thresholds, stats };
  }, [data, days]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || grid.length === 0) return;
    const ctx = canvas.getContext('2d');

    const { w: cellW, h: cellH } = cellSize(canvas.width, canvas.height, grid.length);

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.font = '10px sans-serif';
    ctx.fillStyle = '#9CA3AF';
    ctx.textAlign = 'right';
    for (let h = 0; h < 24; h += 3) {
      ctx.fillText(`${h}h`, MARGIN_LEFT - 4, MARGIN_TOP + h * cellH + cellH / 2 + 3);
    }

    ctx.textAlign = 'center';
    for (let d = 0; d < grid.length; d += 7) {
      const label = dayLabels[d]?.slice(5);
      ctx.fillText(label, MARGIN_LEFT + d * cellW + cellW / 2, canvas.height - 4);
    }

    for (let d = 0; d < grid.length; d++) {
      for (let h = 0; h < 24; h++) {
        ctx.fillStyle = getColor(grid[d][h], thresholds);
        ctx.fillRect(MARGIN_LEFT + d * cellW, MARGIN_TOP + h * cellH, cellW - 1, cellH - 1);
      }
    }
  }, [grid, dayLabels, thresholds]);

  useEffect(() => {
    draw();
  }, [draw]);

  const handleMouseMove = useCallback(
    (e) => {
      const canvas = canvasRef.current;
      if (!canvas || grid.length === 0) return;
      const rect = canvas.getBoundingClientRect();
      const cssX = e.clientX - rect.left;
      const cssY = e.clientY - rect.top;

      // Scale CSS coords to canvas intrinsic resolution for correct hit-test
      const scaleX = canvas.width / rect.width;
      const scaleY = canvas.height / rect.height;
      const x = cssX * scaleX;
      const y = cssY * scaleY;

      const { w: cellW, h: cellH } = cellSize(canvas.width, canvas.height, grid.length);

      const dayIdx = Math.floor((x - MARGIN_LEFT) / cellW);
      const hourIdx = Math.floor((y - MARGIN_TOP) / cellH);

      if (dayIdx >= 0 && dayIdx < grid.length && hourIdx >= 0 && hourIdx < 24) {
        setTooltip({
          x: cssX + 12,
          y: cssY - 12,
          day: dayLabels[dayIdx],
          hour: hourIdx,
          value: grid[dayIdx][hourIdx],
        });
      } else {
        setTooltip(null);
      }
    },
    [grid, dayLabels]
  );

  if (!data || data.length === 0) {
    return (
      <div className="text-center py-8 text-gray-400 text-sm">
        Aucune donnée horaire disponible.
        <br />
        <span className="text-xs">
          Connectez un compteur avec données horaires pour activer le carpet plot.
        </span>
      </div>
    );
  }

  return (
    <div className="relative" data-testid="carpet-plot">
      <canvas
        ref={canvasRef}
        width={Math.max(grid.length * 18 + 40, 500)}
        height={24 * 10 + 28}
        className="w-full"
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setTooltip(null)}
        onClick={() => {
          if (tooltip && onCellClick) {
            onCellClick(tooltip.day, tooltip.hour, tooltip.value);
          }
        }}
        style={{ cursor: tooltip ? 'crosshair' : 'default' }}
      />

      {tooltip && (
        <div
          className="absolute z-10 pointer-events-none bg-white border border-gray-200 rounded-lg shadow-sm px-3 py-2 text-xs"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          <p className="font-medium text-gray-800">
            {tooltip.day} · {tooltip.hour}h–{tooltip.hour + 1}h
          </p>
          <p className="text-gray-600">
            {tooltip.value != null
              ? `${Math.round(tooltip.value * 10) / 10} kWh`
              : 'Pas de données'}
          </p>
        </div>
      )}

      <div className="flex items-center gap-2 mt-2 text-[10px] text-gray-400">
        <span>Faible</span>
        {PALETTE.map((c, i) => (
          <span key={i} className="inline-block w-4 h-3 rounded-sm" style={{ background: c }} />
        ))}
        <span>Élevé</span>
        {stats && (
          <span className="ml-auto">
            Min {Math.round(stats.min)} · Médiane {Math.round(stats.median)} · Max{' '}
            {Math.round(stats.max)} kWh
          </span>
        )}
      </div>
    </div>
  );
}
