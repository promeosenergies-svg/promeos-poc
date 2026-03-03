/**
 * PROMEOS - ROISummaryBar (Sprint V5.0)
 * Compact bar showing estimated vs realized gains with ratio.
 */
import { useState, useEffect } from 'react';
import { BadgeEuro, TrendingUp, ArrowRight } from 'lucide-react';
import { getROISummary } from '../services/api';

const fmtEur = (v) => v != null ? `${Math.round(v).toLocaleString()} EUR` : '— EUR';

export default function ROISummaryBar() {
  const [roi, setRoi] = useState(null);

  useEffect(() => {
    getROISummary().then(setRoi).catch(e => console.error('[ROISummaryBar] load error:', e));
  }, []);

  if (!roi || (roi.total_estimated_eur === 0 && roi.total_realized_eur === 0)) return null;

  const ratio = roi.roi_ratio != null ? `${(roi.roi_ratio * 100).toFixed(0)}%` : '—';
  const isPositive = roi.roi_ratio != null && roi.roi_ratio >= 1;

  return (
    <div className="flex items-center gap-4 px-4 py-2.5 bg-gradient-to-r from-blue-50 to-green-50 rounded-lg border border-blue-100">
      <div className="flex items-center gap-1.5 text-sm">
        <BadgeEuro size={15} className="text-red-500" />
        <span className="text-gray-500">Estime :</span>
        <span className="font-semibold text-red-700">{fmtEur(roi.total_estimated_eur)}</span>
      </div>

      <ArrowRight size={14} className="text-gray-300" />

      <div className="flex items-center gap-1.5 text-sm">
        <BadgeEuro size={15} className="text-green-500" />
        <span className="text-gray-500">Realise :</span>
        <span className="font-semibold text-green-700">{fmtEur(roi.total_realized_eur)}</span>
      </div>

      <div className={`ml-auto flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold ${
        isPositive ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
      }`}>
        <TrendingUp size={12} />
        ROI : {ratio}
      </div>

      {roi.actions_with_realized > 0 && (
        <span className="text-[10px] text-gray-400">{roi.actions_with_realized} action(s) avec gain realise</span>
      )}
    </div>
  );
}
