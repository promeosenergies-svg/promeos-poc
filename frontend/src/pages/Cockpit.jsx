import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Rocket, ArrowRight, Navigation } from 'lucide-react';

const API = 'http://127.0.0.1:8000';

const Cockpit = () => {
  const navigate = useNavigate();
  const [cockpitData, setCockpitData] = useState(null);
  const [portefeuilles, setPortefeuilles] = useState([]);
  const [sites, setSites] = useState([]);
  const [readiness, setReadiness] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/cockpit`).then(r => r.json()),
      fetch(`${API}/api/portefeuilles`).then(r => r.json()),
      fetch(`${API}/api/sites`).then(r => r.json()),
      fetch(`${API}/api/guidance/readiness`).then(r => r.json()),
    ])
    .then(([cockpit, ptf, sitesData, readinessData]) => {
      setCockpitData(cockpit);
      setPortefeuilles(ptf.portefeuilles);
      setSites(sitesData.sites);
      setReadiness(readinessData);
      setLoading(false);
    })
    .catch(err => {
      console.error('Erreur chargement donnees:', err);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-xl text-gray-600">Chargement...</div>
      </div>
    );
  }

  if (!cockpitData) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-xl text-red-600">Erreur de chargement des donnees</div>
      </div>
    );
  }

  const { organisation, stats } = cockpitData;

  const getBadgeConformite = (statut) => {
    if (!statut) return <span className="px-2 py-1 text-xs rounded bg-gray-200 text-gray-700">Non defini</span>;

    const styles = {
      conforme: 'bg-green-100 text-green-800',
      derogation: 'bg-blue-100 text-blue-800',
      a_risque: 'bg-orange-100 text-orange-800',
      non_conforme: 'bg-red-100 text-red-800'
    };

    const labels = {
      conforme: 'Conforme',
      derogation: 'Derogation',
      a_risque: 'A risque',
      non_conforme: 'Non conforme'
    };

    return (
      <span className={`px-2 py-1 text-xs font-medium rounded ${styles[statut]}`}>
        {labels[statut]}
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-blue-600 to-blue-800 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <h1 className="text-3xl font-bold">PROMEOS Cockpit Executif</h1>
          <p className="text-blue-100 mt-1">{organisation.nom} - {organisation.type_client}</p>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">

        {/* KPIs Section + CTA */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">

          {/* KPI 1 : Total Sites */}
          <div className="bg-white rounded-lg shadow p-6 border-l-4 border-blue-500">
            <div className="text-sm text-gray-600 mb-1">Sites Actifs</div>
            <div className="text-3xl font-bold text-gray-900">{stats.sites_actifs}</div>
            <div className="text-xs text-gray-500 mt-1">sur {stats.total_sites} sites</div>
          </div>

          {/* KPI 2 : Avancement Decret */}
          <div className="bg-white rounded-lg shadow p-6 border-l-4 border-green-500">
            <div className="text-sm text-gray-600 mb-1">Avancement Decret 2030</div>
            <div className="text-3xl font-bold text-gray-900">{stats.avancement_decret_pct}%</div>
            <div className="text-xs text-gray-500 mt-1">Trajectoire moyenne</div>
          </div>

          {/* KPI 3 : Sites Non Conformes */}
          <div className="bg-white rounded-lg shadow p-6 border-l-4 border-orange-500">
            <div className="text-sm text-gray-600 mb-1">Sites Non Conformes</div>
            <div className="text-3xl font-bold text-gray-900">
              {stats.sites_tertiaire_ko + stats.sites_bacs_ko}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              Tertiaire: {stats.sites_tertiaire_ko} | BACS: {stats.sites_bacs_ko}
            </div>
          </div>

          {/* KPI 4 : Risque Financier */}
          <div className="bg-white rounded-lg shadow p-6 border-l-4 border-red-500">
            <div className="text-sm text-gray-600 mb-1">Risque Financier</div>
            <div className="text-3xl font-bold text-gray-900">
              {(stats.risque_financier_euro / 1000).toFixed(0)}k EUR
            </div>
            <div className="text-xs text-gray-500 mt-1">{stats.alertes_actives} alertes actives</div>
          </div>

          {/* KPI 5 : Readiness Score + CTA */}
          <div
            className="bg-gradient-to-br from-indigo-600 to-purple-700 rounded-lg shadow p-6 text-white cursor-pointer hover:from-indigo-700 hover:to-purple-800 transition"
            onClick={() => navigate('/action-plan')}
          >
            <div className="flex items-center gap-2 mb-2">
              <Navigation size={18} />
              <div className="text-sm font-medium opacity-90">Readiness</div>
            </div>
            <div className="text-3xl font-bold">
              {readiness ? `${readiness.readiness_score}%` : '...'}
            </div>
            <div className="flex items-center gap-1 mt-2 text-xs opacity-80">
              Voir le plan d'action <ArrowRight size={12} />
            </div>
          </div>
        </div>

        {/* CTA Card */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-700 rounded-xl p-6 text-white mb-8 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Rocket size={32} />
            <div>
              <h3 className="text-lg font-bold">Rendre mon patrimoine actionnable</h3>
              <p className="text-blue-200 text-sm mt-0.5">
                {readiness
                  ? `${readiness.summary.sites_non_conformes} sites non conformes, ${(readiness.summary.risque_financier_total / 1000).toFixed(0)}k EUR de risque — consultez le plan d'action priorise`
                  : 'Consultez votre plan d\'action priorise par risque et impact'}
              </p>
            </div>
          </div>
          <button
            onClick={() => navigate('/action-plan')}
            className="bg-white text-indigo-700 px-6 py-2.5 rounded-lg font-semibold hover:bg-indigo-50 transition flex items-center gap-2 shrink-0"
          >
            Plan d'action
            <ArrowRight size={16} />
          </button>
        </div>

        {/* Portefeuilles Section */}
        <div className="bg-white rounded-lg shadow mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-800">Portefeuilles</h2>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {portefeuilles.map(ptf => (
                <div key={ptf.id} className="border rounded-lg p-4 hover:shadow-md transition">
                  <h3 className="font-semibold text-gray-900 mb-1">{ptf.nom}</h3>
                  <p className="text-sm text-gray-600 mb-2">{ptf.description}</p>
                  <div className="text-2xl font-bold text-blue-600">{ptf.nb_sites} sites</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Sites Section */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
            <h2 className="text-xl font-semibold text-gray-800">Sites ({sites.length})</h2>
            <div className="text-sm text-gray-600">
              Echeance : {cockpitData.echeance_prochaine}
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Site</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ville</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Surface</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Decret 2030</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">BACS</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Avancement</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {sites.slice(0, 50).map(site => (
                  <tr key={site.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => navigate(`/sites/${site.id}`)}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{site.nom}</div>
                      {site.anomalie_facture && (
                        <span className="text-xs text-red-600">Anomalie facture</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {site.ville}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {site.surface_m2} m2
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getBadgeConformite(site.statut_decret_tertiaire)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getBadgeConformite(site.statut_bacs)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full"
                            style={{width: `${Math.min(site.avancement_decret_pct, 100)}%`}}
                          ></div>
                        </div>
                        <span className="text-xs text-gray-600">{Math.round(site.avancement_decret_pct)}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {site.action_recommandee ? (
                        <span className="text-xs bg-yellow-50 text-yellow-800 px-2 py-1 rounded">
                          {site.action_recommandee.length > 30
                            ? site.action_recommandee.substring(0, 30) + '...'
                            : site.action_recommandee}
                        </span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {sites.length > 50 && (
            <div className="px-6 py-4 bg-gray-50 text-center text-sm text-gray-600">
              Affichage de 50 sites sur {sites.length} (pagination a implementer)
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Cockpit;
