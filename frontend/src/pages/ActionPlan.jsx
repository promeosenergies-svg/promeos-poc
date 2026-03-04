import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useScope } from '../contexts/ScopeContext';
import {
  Navigation, ShieldCheck, ShieldAlert, ShieldX,
  Euro, ChevronRight,
  Filter,
} from 'lucide-react';

const STATUT_BADGE = {
  non_conforme: { label: 'Non conforme', bg: 'bg-red-100', text: 'text-red-800' },
  a_risque: { label: 'À risque', bg: 'bg-orange-100', text: 'text-orange-800' },
  conforme: { label: 'Conforme', bg: 'bg-green-100', text: 'text-green-800' },
  manquant: { label: 'Manquant', bg: 'bg-red-100', text: 'text-red-800' },
};

const TYPE_LABELS = {
  bacs: 'BACS',
  decret_tertiaire: 'Décret Tertiaire',
  evidence: 'Preuves',
};

const ActionPlan = () => {
  const navigate = useNavigate();
  const { selectedSiteId } = useScope();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [portefeuilles, setPortefeuilles] = useState([]);
  const [selectedPtf, setSelectedPtf] = useState('');

  const fetchPlan = useCallback((ptfId) => {
    setLoading(true);
    const params = new URLSearchParams({ limit: '100' });
    if (selectedSiteId) params.set('site_id', selectedSiteId);
    else if (ptfId) params.set('portefeuille_id', ptfId);
    fetch(`/api/guidance/action-plan?${params}`)
      .then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); })
      .then(json => { setData(json); setLoading(false); })
      .catch(() => { setData(null); setLoading(false); });
  }, [selectedSiteId]);

  useEffect(() => {
    fetchPlan(selectedPtf);
    fetch(`/api/portefeuilles`)
      .then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); })
      .then(json => setPortefeuilles(json.portefeuilles || []))
      .catch(() => {});
  }, [selectedPtf, selectedSiteId, fetchPlan]);

  const handleFilterChange = (ptfId) => {
    setSelectedPtf(ptfId);
    fetchPlan(ptfId);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-xl text-gray-600">Chargement du plan d'action...</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-xl text-red-600">Erreur de chargement</div>
      </div>
    );
  }

  const { readiness_score, summary, actions } = data;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-indigo-600 to-purple-700 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center gap-3 mb-2">
            <Navigation size={28} />
            <h1 className="text-2xl font-bold">Plan d'action PROMEOS</h1>
          </div>
          <p className="text-indigo-200 text-sm">
            Actions prioritaires pour la conformité énergétique de votre patrimoine
          </p>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">

        {/* Readiness Score */}
        <div className="bg-white rounded-lg shadow mb-8 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-800">Score de maturité</h2>
            <span className={`text-3xl font-bold ${
              readiness_score >= 70 ? 'text-green-600' :
              readiness_score >= 40 ? 'text-orange-600' : 'text-red-600'
            }`}>
              {readiness_score}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-4">
            <div
              className={`h-4 rounded-full transition-all ${
                readiness_score >= 70 ? 'bg-green-500' :
                readiness_score >= 40 ? 'bg-orange-500' : 'bg-red-500'
              }`}
              style={{ width: `${Math.min(readiness_score, 100)}%` }}
            />
          </div>
          <p className="text-sm text-gray-500 mt-2">
            {readiness_score}% de vos sites sont pleinement conformes
          </p>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500">
            <div className="text-sm text-gray-500">Sites total</div>
            <div className="text-2xl font-bold text-gray-900">{summary.total_sites}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-green-500">
            <div className="text-sm text-gray-500 flex items-center gap-1">
              <ShieldCheck size={14} /> Conformes
            </div>
            <div className="text-2xl font-bold text-green-600">{summary.sites_conformes}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-orange-500">
            <div className="text-sm text-gray-500 flex items-center gap-1">
              <ShieldAlert size={14} /> À risque
            </div>
            <div className="text-2xl font-bold text-orange-600">{summary.sites_a_risque}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-red-500">
            <div className="text-sm text-gray-500 flex items-center gap-1">
              <ShieldX size={14} /> Non conformes
            </div>
            <div className="text-2xl font-bold text-red-600">{summary.sites_non_conformes}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 border-l-4 border-purple-500">
            <div className="text-sm text-gray-500 flex items-center gap-1">
              <Euro size={14} /> Risque financier
            </div>
            <div className="text-2xl font-bold text-purple-600">
              {(summary.risque_financier_total / 1000).toFixed(0)}k
            </div>
          </div>
        </div>

        {/* Filter + Actions table */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-800">
              Actions ({actions.length})
            </h2>
            <div className="flex items-center gap-2">
              <Filter size={16} className="text-gray-400" />
              <select
                value={selectedPtf}
                onChange={e => handleFilterChange(e.target.value)}
                className="border rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
              >
                <option value="">Tous les portefeuilles</option>
                {portefeuilles.map(p => (
                  <option key={p.id} value={p.id}>{p.nom} ({p.nb_sites} sites)</option>
                ))}
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-12">#</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Site</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Statut</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Risque</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Échéance</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-8"></th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {actions.map(action => {
                  const badge = STATUT_BADGE[action.statut] || STATUT_BADGE.a_risque;
                  return (
                    <tr
                      key={`${action.site_id}-${action.obligation_type}-${action.rank}`}
                      className="hover:bg-gray-50 cursor-pointer"
                      onClick={() => navigate(`/sites/${action.site_id}`)}
                    >
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold ${
                          action.priority >= 90 ? 'bg-red-100 text-red-700' :
                          action.priority >= 60 ? 'bg-orange-100 text-orange-700' :
                          'bg-yellow-100 text-yellow-700'
                        }`}>
                          {action.rank}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-sm font-medium text-gray-900">{action.site_nom}</div>
                        <div className="text-xs text-gray-500">{action.ville} — {action.portefeuille_nom}</div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className="text-xs font-medium text-gray-700 bg-gray-100 px-2 py-1 rounded">
                          {TYPE_LABELS[action.obligation_type] || action.obligation_type}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-gray-900">{action.action_label}</span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-medium rounded ${badge.bg} ${badge.text}`}>
                          {badge.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm">
                        {action.risque_financier_euro > 0 ? (
                          <span className="text-red-600 font-medium">
                            {action.risque_financier_euro.toLocaleString('fr-FR')} EUR
                          </span>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        {action.echeance || '-'}
                      </td>
                      <td className="px-4 py-3">
                        <ChevronRight size={16} className="text-gray-400" />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {actions.length === 0 && (
            <div className="p-8 text-center">
              <ShieldCheck size={48} className="mx-auto text-green-400 mb-3" />
              <p className="text-gray-600">Aucune action requise. Votre patrimoine est conforme.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ActionPlan;
