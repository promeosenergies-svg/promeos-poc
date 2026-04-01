/**
 * Carte "Potentiel de flexibilité" — s'intègre dans la fiche site (Site360).
 * Affiche le score flex, les 4 dimensions, les top levers.
 */
import { useState, useEffect } from 'react';
import { getFlexAssessment, getFlexAssets } from '../../services/api';

export default function FlexPotentialCard({ siteId }) {
  const [data, setData] = useState(null);
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!siteId) return;
    setLoading(true);
    Promise.all([
      getFlexAssessment(siteId).catch(() => null),
      getFlexAssets({ site_id: siteId }).catch(() => ({ assets: [] })),
    ]).then(([assessment, assetRes]) => {
      setData(assessment);
      setAssets(assetRes?.assets || []);
      setLoading(false);
    });
  }, [siteId]);

  if (loading) return <div className="border rounded-lg p-4 bg-gray-50 animate-pulse h-32" />;
  if (!data) return null;

  const score = data.flex_score || data.flex_potential_score || 0;
  const dims = data.dimensions || {};
  const levers = (data.levers || []).slice(0, 3);
  const scoreColor =
    score >= 60 ? 'text-green-700' : score >= 30 ? 'text-amber-700' : 'text-gray-500';

  return (
    <div className="border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-700">Potentiel de flexibilité</h3>
        <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded">
          {data.source === 'asset_based' ? 'Assets inventoriés' : 'Estimation heuristique'}
        </span>
      </div>

      <div className="flex items-baseline gap-2 mb-3">
        <span className={`text-2xl font-bold ${scoreColor}`}>{score}</span>
        <span className="text-sm text-gray-400">/100</span>
        {data.potential_kw > 0 && (
          <span className="text-sm text-gray-500 ml-2">
            {Math.round(data.potential_kw)} kW pilotable
          </span>
        )}
      </div>

      {/* 4 dimensions */}
      {Object.keys(dims).length > 0 && (
        <div className="grid grid-cols-2 gap-2 mb-3 text-xs">
          <DimBar label="Technique" value={dims.technical_readiness} />
          <DimBar label="Données" value={dims.data_confidence} />
          <DimBar label="Économique" value={dims.economic_relevance} />
          <DimPill label="Réglementaire" value={dims.regulatory_alignment} />
        </div>
      )}

      {/* Top levers */}
      {levers.length > 0 && (
        <div className="space-y-1">
          {levers.map((l, i) => (
            <div key={i} className="flex items-center justify-between text-xs text-gray-600">
              <span>{l.label || l.lever}</span>
              <span className="font-medium">
                {l.kw ? `${Math.round(l.kw)} kW` : `${l.score}/100`}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Source + confidence */}
      <div className="mt-2 text-xs text-gray-400">
        {assets.length > 0
          ? `${assets.length} asset${assets.length !== 1 ? 's' : ''} inventorié${assets.length !== 1 ? 's' : ''}`
          : data.source === 'heuristic'
            ? 'Estimation heuristique'
            : 'Données insuffisantes'}
        {data.kpi && <span className="ml-2">· Confiance : {data.kpi.confidence || 'N/A'}</span>}
      </div>
    </div>
  );
}

function DimBar({ label, value }) {
  const v = value || 0;
  const color = v >= 60 ? 'bg-green-500' : v >= 30 ? 'bg-amber-400' : 'bg-gray-300';
  return (
    <div>
      <div className="flex justify-between mb-0.5">
        <span className="text-gray-500">{label}</span>
        <span className="font-medium">{v}%</span>
      </div>
      <div className="h-1.5 bg-gray-100 rounded-full">
        <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${v}%` }} />
      </div>
    </div>
  );
}

function DimPill({ label, value }) {
  const colors = {
    aligned: 'text-green-700 bg-green-50',
    partial: 'text-amber-700 bg-amber-50',
    misaligned: 'text-red-700 bg-red-50',
    unknown: 'text-gray-500 bg-gray-50',
  };
  const labels = {
    aligned: 'Aligné',
    partial: 'Partiel',
    misaligned: 'Non aligné',
    unknown: 'À évaluer',
  };
  return (
    <div>
      <span className="text-gray-500">{label}</span>
      <span className={`ml-1 text-xs px-1.5 py-0.5 rounded ${colors[value] || colors.unknown}`}>
        {labels[value] || value || 'À évaluer'}
      </span>
    </div>
  );
}
