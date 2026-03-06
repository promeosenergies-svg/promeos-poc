/**
 * PROMEOS — DataQualityBadge (D.1)
 * Badge qualité données multi-taille : sm (pastille), md (score+grade), lg (dimensions+popover).
 * Utilise le score 0-100 du service data_quality_service.
 *
 * Props :
 *   score      : number (0-100)
 *   dimensions : { completeness, freshness, accuracy, consistency } (optionnel, pour lg)
 *   recommendations : string[] (optionnel, pour popover)
 *   size       : 'sm' | 'md' | 'lg'
 *   onClick    : function (optionnel)
 */
import { useState, useRef, useEffect } from 'react';
import { getDataQualityGrade } from '../lib/constants';
import Explain from '../ui/Explain';

const DIM_LABELS = {
  completeness: 'Complétude',
  freshness: 'Fraîcheur',
  accuracy: 'Précision',
  consistency: 'Cohérence',
};

const DIM_ORDER = ['completeness', 'freshness', 'accuracy', 'consistency'];

function DimBar({ label, value }) {
  const pct = Math.max(0, Math.min(100, value ?? 0));
  const barColor = pct >= 70 ? 'bg-green-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-gray-500 w-20 truncate">{label}</span>
      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full ${barColor} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] font-medium text-gray-600 w-7 text-right">{Math.round(pct)}</span>
    </div>
  );
}

export default function DataQualityBadge({ score, dimensions, recommendations, size = 'md', onClick }) {
  const [popoverOpen, setPopoverOpen] = useState(false);
  const ref = useRef(null);
  const grade = getDataQualityGrade(score);

  // Close popover on outside click
  useEffect(() => {
    if (!popoverOpen) return;
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setPopoverOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [popoverOpen]);

  if (score == null || isNaN(score)) return null;

  const roundedScore = Math.round(score);

  // ── sm : pastille seule ──
  if (size === 'sm') {
    return (
      <span
        className={`inline-flex items-center justify-center w-5 h-5 rounded-full text-[9px] font-bold text-white ${grade.bg.replace('bg-', 'bg-').replace('100', '500').replace('bg-gray-100', 'bg-gray-400').replace('bg-green-100', 'bg-green-500').replace('bg-amber-100', 'bg-amber-500').replace('bg-red-100', 'bg-red-500')}`}
        title={`Qualité données : ${roundedScore}/100 (${grade.letter})`}
        data-testid="dq-badge-sm"
        onClick={onClick}
        role={onClick ? 'button' : undefined}
      >
        {grade.letter}
      </span>
    );
  }

  // ── md : pastille + score + grade ──
  if (size === 'md') {
    return (
      <span
        className="inline-flex items-center gap-1.5 cursor-default"
        data-testid="dq-badge-md"
        onClick={onClick}
        role={onClick ? 'button' : undefined}
      >
        <span className={`inline-flex items-center justify-center w-5 h-5 rounded-full text-[9px] font-bold text-white ${grade.letter === 'A' || grade.letter === 'B' ? 'bg-green-500' : grade.letter === 'C' ? 'bg-amber-500' : 'bg-red-500'}`}>
          {grade.letter}
        </span>
        <span className={`text-sm font-semibold ${grade.color}`}>{roundedScore}/100</span>
      </span>
    );
  }

  // ── lg : pastille + score + 4 mini-barres + popover ──
  const togglePopover = () => setPopoverOpen((o) => !o);

  return (
    <div ref={ref} className="relative inline-block" data-testid="dq-badge-lg">
      <button
        onClick={onClick || togglePopover}
        className="inline-flex items-center gap-2 px-2.5 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 transition"
      >
        <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-[10px] font-bold text-white ${grade.letter === 'A' || grade.letter === 'B' ? 'bg-green-500' : grade.letter === 'C' ? 'bg-amber-500' : 'bg-red-500'}`}>
          {grade.letter}
        </span>
        <span className={`text-sm font-bold ${grade.color}`}>{roundedScore}/100</span>
        {dimensions && (
          <div className="flex gap-0.5 ml-1">
            {DIM_ORDER.map((k) => {
              const v = dimensions[k] ?? 0;
              const c = v >= 70 ? 'bg-green-400' : v >= 50 ? 'bg-amber-400' : 'bg-red-400';
              return <div key={k} className={`w-1 h-3 rounded-sm ${c}`} />;
            })}
          </div>
        )}
      </button>

      {/* Popover */}
      {popoverOpen && (
        <div className="absolute top-full left-0 mt-2 w-72 bg-white rounded-xl border border-gray-200 shadow-xl z-50 overflow-hidden">
          {/* Header */}
          <div className="px-4 py-3 border-b border-gray-100 bg-gray-50/50">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold text-gray-800">
                <Explain term="data_quality_score">Score qualité données</Explain>
              </h4>
              <span className={`text-lg font-bold ${grade.color}`}>{roundedScore}/100</span>
            </div>
          </div>

          {/* Dimensions */}
          {dimensions && (
            <div className="px-4 py-3 space-y-2">
              {DIM_ORDER.map((k) => (
                <DimBar key={k} label={DIM_LABELS[k]} value={dimensions[k]} />
              ))}
            </div>
          )}

          {/* Recommendations */}
          {recommendations && recommendations.length > 0 && (
            <div className="px-4 py-2 border-t border-gray-100">
              <p className="text-[10px] font-semibold text-gray-400 uppercase mb-1">Recommandations</p>
              <ul className="space-y-1">
                {recommendations.slice(0, 3).map((r, i) => (
                  <li key={i} className="text-xs text-gray-600 flex items-start gap-1.5">
                    <span className="text-amber-500 mt-0.5">•</span>
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
