/**
 * PROMEOS — V101 SegmentationWidget
 * Compact card for Patrimoine cockpit + Site360.
 * V101: Next Best Step card + top 2 recommendations with action creation.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UserCheck,
  ChevronRight,
  AlertCircle,
  Lightbulb,
  Plus,
  Loader2,
  Sparkles,
  Check,
} from 'lucide-react';
import { getSegmentationNextStep, createActionFromRecommendation } from '../services/api';
import { Badge } from '../ui';

const CONFIDENCE_CFG = {
  high: { color: 'bg-green-500', label: 'Eleve', badge: 'ok' },
  medium: { color: 'bg-amber-500', label: 'Moyen', badge: 'warn' },
  low: { color: 'bg-red-400', label: 'Faible', badge: 'crit' },
};

function getConfidenceLevel(score) {
  if (score >= 70) return CONFIDENCE_CFG.high;
  if (score >= 40) return CONFIDENCE_CFG.medium;
  return CONFIDENCE_CFG.low;
}

const DERIVED_LABEL = {
  naf: 'Code NAF',
  questionnaire: 'Questionnaire',
  patrimoine: 'Patrimoine',
  mix: 'Mixte',
};

export default function SegmentationWidget({ onSegmentationClick, compact = false }) {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [creatingAction, setCreatingAction] = useState(null);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    getSegmentationNextStep()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-4 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-1/3 mb-3" />
        <div className="h-6 bg-gray-200 rounded w-2/3" />
      </div>
    );
  }

  if (!data?.profile_summary) {
    return (
      <div className="bg-white rounded-lg shadow p-4 border-l-4 border-gray-300">
        <div className="flex items-center gap-2 text-gray-500">
          <AlertCircle size={18} />
          <span className="text-sm">Profil non detecte</span>
        </div>
        <button
          onClick={() => (onSegmentationClick ? onSegmentationClick() : navigate('/segmentation'))}
          className="mt-2 inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800"
        >
          Configurer <ChevronRight size={14} />
        </button>
      </div>
    );
  }

  const ps = data.profile_summary;
  const nbs = data.next_best_step;
  const recs = data.top_recommendations || [];
  const label = ps.segment_label || ps.typologie;
  const conf = getConfidenceLevel(ps.confidence_score);

  const handleCtaClick = () => {
    if (!nbs?.cta) return;
    if (nbs.cta.type === 'modal' && onSegmentationClick) {
      onSegmentationClick();
    } else if (nbs.cta.type === 'route' && nbs.cta.route) {
      navigate(nbs.cta.route);
    }
  };

  const handleCreateAction = async (key) => {
    setCreatingAction(key);
    try {
      const result = await createActionFromRecommendation(key);
      setToast(result.status === 'existing' ? 'Action deja creee' : 'Action creee');
      setTimeout(() => setToast(null), 3000);
    } catch {
      setToast('Erreur');
      setTimeout(() => setToast(null), 3000);
    } finally {
      setCreatingAction(null);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500">
      {/* Toast */}
      {toast && (
        <div className="mb-2 px-2 py-1.5 bg-green-50 border border-green-200 rounded-lg flex items-center gap-1.5">
          <Check size={12} className="text-green-600" />
          <span className="text-xs text-green-700">{toast}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <UserCheck size={18} className="text-blue-600" />
          <h3 className="text-sm font-semibold text-gray-700">Profil énergie</h3>
        </div>
        <button
          onClick={() => (onSegmentationClick ? onSegmentationClick() : navigate('/segmentation'))}
          className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 transition"
        >
          Affiner <ChevronRight size={14} />
        </button>
      </div>

      {/* Segment + confidence */}
      <div className="flex items-center gap-2 mb-2">
        <p className="text-base font-bold text-gray-900">{label}</p>
        <Badge status={conf.badge}>{Math.round(ps.confidence_score)}%</Badge>
      </div>

      {/* Confidence bar */}
      <div className="mb-3">
        <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full ${conf.color} rounded-full transition-all`}
            style={{ width: `${ps.confidence_score}%` }}
          />
        </div>
      </div>

      {/* Next Best Step card */}
      {nbs && !compact && (
        <div className="mb-3 p-3 bg-indigo-50 border border-indigo-200 rounded-lg">
          <div className="flex items-start gap-2">
            <Sparkles size={16} className="text-indigo-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-gray-900">{nbs.title}</p>
              <p className="text-xs text-gray-600 mt-0.5">{nbs.why}</p>
              {nbs.score_gain_hint && (
                <span className="inline-block mt-1 text-[10px] px-1.5 py-0.5 bg-indigo-100 text-indigo-700 rounded">
                  {nbs.score_gain_hint}
                </span>
              )}
              {nbs.cta && (
                <button
                  onClick={handleCtaClick}
                  className="mt-2 flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition"
                >
                  {nbs.cta.label}
                  <ChevronRight size={12} />
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Top 2 recommendations with "+" action button */}
      {!compact && recs.length > 0 && (
        <div className="mt-2">
          <p className="text-[11px] text-gray-400 uppercase font-semibold mb-1">Recommandations</p>
          <ul className="space-y-1">
            {recs.map((r) => (
              <li key={r.key} className="flex items-center gap-1.5 text-xs text-gray-600">
                <Lightbulb size={12} className="text-blue-500 flex-shrink-0" />
                <span className="flex-1">{r.label}</span>
                <button
                  onClick={() => handleCreateAction(r.key)}
                  disabled={creatingAction === r.key}
                  className="p-1 rounded hover:bg-blue-50 text-blue-500 hover:text-blue-700 transition disabled:opacity-50"
                  title="Créer une action"
                >
                  {creatingAction === r.key ? (
                    <Loader2 size={12} className="animate-spin" />
                  ) : (
                    <Plus size={12} />
                  )}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Derived from */}
      {ps.derived_from && !compact && (
        <p className="mt-2 text-[10px] text-gray-400">
          Source : {DERIVED_LABEL[ps.derived_from] || 'Mixte'}
        </p>
      )}
    </div>
  );
}
