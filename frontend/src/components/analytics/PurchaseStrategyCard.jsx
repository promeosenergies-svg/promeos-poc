/**
 * PurchaseStrategyCard — Recommandation strategie d'achat via archetype.
 * Display-only. Donnees de GET /api/purchase/strategy/sites/{id}.
 */

import { useState, useEffect } from 'react';
import { ShoppingCart, Zap } from 'lucide-react';
import { getPurchaseStrategy } from '../../services/api';

const STRATEGY_STYLE = {
  fixe: { label: 'Fixe', bg: 'bg-blue-100', text: 'text-blue-700', desc: 'Budget securise' },
  indexe: { label: 'Indexe', bg: 'bg-amber-100', text: 'text-amber-700', desc: 'Suit le marche' },
  spot: { label: 'Spot', bg: 'bg-red-100', text: 'text-red-700', desc: 'Prix marche temps reel' },
  ppa: { label: 'PPA', bg: 'bg-green-100', text: 'text-green-700', desc: 'Contrat long terme ENR' },
  mix: {
    label: 'Mix',
    bg: 'bg-purple-100',
    text: 'text-purple-700',
    desc: 'Composition optimisee',
  },
};

const COMPOSITION_COLORS = {
  fixe: '#3b82f6',
  indexe: '#f59e0b',
  spot: '#ef4444',
  ppa: '#10b981',
};

export default function PurchaseStrategyCard({ siteId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!siteId) return;
    setLoading(true);
    setData(null);
    let stale = false;
    getPurchaseStrategy(siteId)
      .then((d) => {
        if (!stale) setData(d);
      })
      .catch(() => {
        if (!stale) setData(null);
      })
      .finally(() => {
        if (!stale) setLoading(false);
      });
    return () => {
      stale = true;
    };
  }, [siteId]);

  if (loading) {
    return (
      <div className="p-6 text-sm text-gray-400 animate-pulse">Chargement strategie d'achat...</div>
    );
  }
  if (!data || !data.strategy) return null;

  const style = STRATEGY_STYLE[data.strategy] || STRATEGY_STYLE.fixe;
  const composition = data.composition || {};

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShoppingCart size={16} className="text-indigo-600" />
          <h3 className="text-base font-semibold text-gray-900">Strategie d'achat recommandee</h3>
        </div>
        <span className={`px-3 py-1 rounded-full text-sm font-bold ${style.bg} ${style.text}`}>
          {style.label}
        </span>
      </div>

      {/* Rationale */}
      <p className="text-xs text-gray-600">{data.rationale}</p>

      {/* Composition bar */}
      <div className="space-y-2">
        <div className="text-xs font-medium text-gray-700">Composition optimale</div>
        <div className="flex h-6 rounded-full overflow-hidden">
          {Object.entries(composition)
            .filter(([, pct]) => pct > 0)
            .map(([type, pct]) => (
              <div
                key={type}
                className="flex items-center justify-center text-[10px] font-medium text-white"
                style={{
                  width: `${pct}%`,
                  backgroundColor: COMPOSITION_COLORS[type] || '#94a3b8',
                  minWidth: pct > 5 ? 'auto' : '0',
                }}
              >
                {pct >= 15 && `${type} ${pct}%`}
              </div>
            ))}
        </div>
        <div className="flex gap-3 text-[10px] text-gray-500">
          {Object.entries(composition)
            .filter(([, pct]) => pct > 0)
            .map(([type, pct]) => (
              <span key={type} className="flex items-center gap-1">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: COMPOSITION_COLORS[type] || '#94a3b8' }}
                />
                {type} {pct}%
              </span>
            ))}
        </div>
      </div>

      {/* Flags */}
      <div className="flex flex-wrap gap-2">
        {data.green_recommended && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-green-100 text-green-700">
            <Zap size={10} className="mr-1" />
            Green recommande
          </span>
        )}
        {data.ppa_eligible && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-100 text-emerald-700">
            PPA eligible
          </span>
        )}
        {data.cdc_profile_snapshot?.P_max_kw > 0 && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-gray-100 text-gray-600">
            P_max {Math.round(data.cdc_profile_snapshot.P_max_kw)} kW
          </span>
        )}
      </div>

      {/* Adjustments */}
      {data.adjustments?.length > 0 && (
        <div className="text-[10px] text-gray-400 space-y-0.5">
          {data.adjustments.map((a, i) => (
            <p key={i}>Ajustement : {a}</p>
          ))}
        </div>
      )}
    </div>
  );
}
