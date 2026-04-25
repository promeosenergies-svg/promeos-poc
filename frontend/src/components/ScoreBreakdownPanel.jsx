/**
 * PROMEOS — ScoreBreakdownPanel (CX Gap #4)
 * Décomposition live du score conformité par framework.
 * Appelle GET /regops/score_explain — données backend, zéro calcul frontend.
 */
import { useState, useEffect } from 'react';
import { AlertTriangle, ArrowRight, HelpCircle, ShieldCheck } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { getScoreExplain } from '../services/api/conformite';
import { fmtNum } from '../utils/format';

const FW_PATHS = {
  tertiaire_operat: '/conformite',
  bacs: '/conformite?tab=bacs',
  aper: '/conformite?tab=aper',
};

function BreakdownBar({ reg }) {
  const navigate = useNavigate();
  const pct = Math.round(reg.sub_score);
  const barColor = pct >= 80 ? 'bg-emerald-400' : pct >= 50 ? 'bg-amber-400' : 'bg-red-400';
  const contribution = Math.round(reg.sub_score * reg.weight) / 100;

  return (
    <div className="py-3 border-b border-gray-100 last:border-0">
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-medium text-gray-800">{reg.label}</span>
        <span className="text-sm font-bold text-gray-900">{pct}/100</span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden mb-1.5">
        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
      <div className="flex items-center justify-between text-[11px] text-gray-500">
        <span>
          Poids : {Math.round(reg.weight * 100)}% — contribution : {fmtNum(contribution, 1)} pts
        </span>
        {reg.penalties_count > 0 && (
          <span className="text-red-500">
            {reg.penalties_count} finding{reg.penalties_count > 1 ? 's' : ''}
          </span>
        )}
      </div>
      {reg.worst_finding_label && (
        <p className="text-[11px] text-red-500 mt-0.5 flex items-center gap-1">
          <AlertTriangle size={10} /> {reg.worst_finding_label}
        </p>
      )}
      {FW_PATHS[reg.regulation] && (
        <button
          onClick={() => navigate(FW_PATHS[reg.regulation])}
          className="text-[11px] text-blue-600 hover:text-blue-800 mt-1 flex items-center gap-0.5"
        >
          Detail <ArrowRight size={10} />
        </button>
      )}
    </div>
  );
}

export default function ScoreBreakdownPanel({ siteId, open }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || !siteId) return;
    setLoading(true);
    getScoreExplain('site', siteId)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [open, siteId]);

  if (!open || loading)
    return loading ? (
      <div className="pt-4 border-t border-gray-100 mt-4 space-y-3">
        <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
          Décomposition live
        </p>
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-14 bg-gray-100 rounded-lg animate-pulse" />
        ))}
      </div>
    ) : null;

  if (!data) return null;

  return (
    <div className="pt-4 border-t border-gray-100 mt-4 space-y-4">
      <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
        Décomposition live — Site #{data.scope?.id}
      </p>

      <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
        <ShieldCheck size={18} className="text-blue-600" />
        <div>
          <p className="text-lg font-bold text-gray-900">{Math.round(data.score)}/100</p>
          <p className="text-[11px] text-gray-500">
            {data.frameworks_evaluated}/{data.frameworks_total} cadres — {data.confidence}
          </p>
        </div>
      </div>

      {(data.per_regulation || []).map((reg) => (
        <BreakdownBar key={reg.regulation} reg={reg} />
      ))}

      <div className="p-2.5 bg-blue-50 rounded-lg">
        <p className="text-[10px] font-mono text-blue-700">{data.formula_explain}</p>
      </div>

      {data.how_to_improve?.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
            Priorités
          </p>
          {data.how_to_improve.map((a, i) => (
            <div
              key={i}
              className="flex items-center gap-2 py-1.5 text-sm text-gray-700 border-b border-gray-50 last:border-0"
            >
              <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 text-[10px] font-bold flex items-center justify-center">
                {i + 1}
              </span>
              <span className="flex-1">{a.action}</span>
              <span className="text-xs text-gray-400">+{a.potential_gain} pts</span>
            </div>
          ))}
        </div>
      )}

      <p className="text-[10px] text-gray-400 font-mono">
        <HelpCircle size={10} className="inline mr-1" />
        {data._meta?.module || 'compliance_score_service'}
      </p>
    </div>
  );
}
