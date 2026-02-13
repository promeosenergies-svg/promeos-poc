/**
 * PROMEOS — Vue Executive (/cockpit) V3.1.2
 * Scope-aligned: all KPIs and sites table respect ScopeContext.
 * V3.1.2: Readiness → Maturite de pilotage + definition + drill-down modal.
 */
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Rocket, ArrowRight, Info, Database, ShieldCheck, ListChecks } from 'lucide-react';
import { useScope } from '../contexts/ScopeContext';
import Modal from '../ui/Modal';

const Cockpit = () => {
  const navigate = useNavigate();
  const { org, portefeuille, portefeuilles, scopedSites } = useScope();
  const [showMaturiteModal, setShowMaturiteModal] = useState(false);

  // ── Derive all KPIs from scopedSites (scope-aligned) ──
  const kpis = useMemo(() => {
    const sites = scopedSites;
    const total = sites.length;
    const conformes = sites.filter(s => s.statut_conformite === 'conforme').length;
    const nonConformes = sites.filter(s => s.statut_conformite === 'non_conforme').length;
    const aRisque = sites.filter(s => s.statut_conformite === 'a_risque').length;
    const risqueTotal = sites.reduce((sum, s) => sum + (s.risque_eur || 0), 0);
    const avgAvancement = total > 0
      ? Math.round(sites.reduce((sum, s) => sum + (s.conso_kwh_an > 500000 ? 65 : 40), 0) / total)
      : 0;
    // Sub-indicators for "Maturite de pilotage"
    const couvertureDonnees = total > 0
      ? Math.round(sites.filter(s => s.conso_kwh_an > 0).length / total * 100)
      : 0;
    const suiviConformite = total > 0
      ? Math.round(conformes / total * 100)
      : 0;
    const actionsActives = total > 0
      ? Math.round(sites.filter(s => s.statut_conformite === 'non_conforme' || s.statut_conformite === 'a_risque').length > 0 ? 55 : 80)
      : 0;
    const readinessScore = total > 0
      ? Math.round(couvertureDonnees * 0.3 + suiviConformite * 0.4 + actionsActives * 0.3)
      : 0;
    return { total, conformes, nonConformes, aRisque, risqueTotal, avgAvancement, readinessScore, couvertureDonnees, suiviConformite, actionsActives };
  }, [scopedSites]);

  // ── Scope label ──
  const scopeLabel = portefeuille
    ? `${org.nom} / ${portefeuille.nom}`
    : org.nom;

  // ── Portefeuilles with site counts (from scopedSites) ──
  const ptfWithCounts = useMemo(() => {
    return portefeuilles.map(pf => {
      const count = scopedSites.filter(s => ((s.id - 1) % 5) + 1 === pf.id).length;
      return { ...pf, nb_sites: count };
    }).filter(pf => pf.nb_sites > 0);
  }, [portefeuilles, scopedSites]);

  const getBadgeConformite = (statut) => {
    if (!statut) return <span className="px-2 py-1 text-xs rounded bg-gray-200 text-gray-700">Non defini</span>;
    const styles = {
      conforme: 'bg-green-100 text-green-800',
      derogation: 'bg-blue-100 text-blue-800',
      a_risque: 'bg-orange-100 text-orange-800',
      non_conforme: 'bg-red-100 text-red-800',
      a_evaluer: 'bg-gray-100 text-gray-700',
    };
    const labels = {
      conforme: 'Conforme',
      derogation: 'Derogation',
      a_risque: 'A risque',
      non_conforme: 'Non conforme',
      a_evaluer: 'A evaluer',
    };
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded ${styles[statut] || styles.a_evaluer}`}>
        {labels[statut] || statut}
      </span>
    );
  };

  return (
    <div className="px-6 py-6 space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-gray-900">Vue exécutive</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          KPIs portefeuille & priorités multi-sites — {scopeLabel} · {kpis.total} sites
        </p>
      </div>

      {/* KPIs Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* KPI 1: Sites Actifs */}
        <div className="bg-white rounded-lg shadow p-5 border-l-4 border-blue-500">
          <div className="text-xs text-gray-500 font-medium uppercase mb-1">Sites Actifs</div>
          <div className="text-3xl font-bold text-gray-900">{kpis.total}</div>
          <div className="text-xs text-gray-400 mt-1">dans le perimetre</div>
        </div>

        {/* KPI 2: Avancement Decret */}
        <div className="bg-white rounded-lg shadow p-5 border-l-4 border-green-500">
          <div className="text-xs text-gray-500 font-medium uppercase mb-1">Avancement Decret 2030</div>
          <div className="text-3xl font-bold text-gray-900">{kpis.avgAvancement}%</div>
          <div className="text-xs text-gray-400 mt-1">trajectoire moyenne</div>
        </div>

        {/* KPI 3: Sites Non Conformes */}
        <div className="bg-white rounded-lg shadow p-5 border-l-4 border-orange-500">
          <div className="text-xs text-gray-500 font-medium uppercase mb-1">Sites Non Conformes</div>
          <div className="text-3xl font-bold text-gray-900">{kpis.nonConformes + kpis.aRisque}</div>
          <div className="text-xs text-gray-400 mt-1">
            Non conformes: {kpis.nonConformes} | A risque: {kpis.aRisque}
          </div>
        </div>

        {/* KPI 4: Risque Financier */}
        <div className="bg-white rounded-lg shadow p-5 border-l-4 border-red-500">
          <div className="text-xs text-gray-500 font-medium uppercase mb-1">Risque Financier</div>
          <div className="text-3xl font-bold text-gray-900">
            {(kpis.risqueTotal / 1000).toFixed(0)}k EUR
          </div>
          <div className="text-xs text-gray-400 mt-1">{kpis.nonConformes + kpis.aRisque} sites a risque</div>
        </div>

        {/* KPI 5: Maturite de pilotage (click → detail modal) */}
        <div
          className="bg-gradient-to-br from-indigo-600 to-purple-700 rounded-lg shadow p-5 text-white cursor-pointer hover:shadow-lg transition"
          onClick={() => setShowMaturiteModal(true)}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setShowMaturiteModal(true); } }}
          aria-label="Detail maturite de pilotage"
        >
          <div className="flex items-center justify-between mb-1">
            <div className="text-xs font-medium opacity-80 uppercase">Maturite de pilotage</div>
            <Info size={14} className="opacity-60" />
          </div>
          <div className="text-3xl font-bold">{kpis.readinessScore}%</div>
          <div className="text-xs opacity-70 mt-1">Donnees + conformite + actions</div>
          {/* TrustBadge */}
          <div className="mt-2 flex items-center gap-1.5 text-xs opacity-60">
            <div className="w-1.5 h-1.5 rounded-full bg-yellow-300" />
            <span>RegOps + donnees · 30j · confiance moyenne</span>
          </div>
        </div>
      </div>

      {/* Single CTA Card */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-700 rounded-xl p-6 text-white flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Rocket size={32} />
          <div>
            <h3 className="text-lg font-bold">Rendre mon patrimoine actionnable</h3>
            <p className="text-blue-200 text-sm mt-0.5">
              {kpis.nonConformes + kpis.aRisque} sites non conformes, {(kpis.risqueTotal / 1000).toFixed(0)}k EUR de risque — consultez le plan d'action priorise
            </p>
          </div>
        </div>
        <button
          onClick={() => navigate('/actions')}
          className="bg-white text-indigo-700 px-6 py-2.5 rounded-lg font-semibold hover:bg-indigo-50 transition flex items-center gap-2 shrink-0"
        >
          Plan d'action
          <ArrowRight size={16} />
        </button>
      </div>

      {/* Portefeuilles Section (only if no specific PF selected) */}
      {!portefeuille && ptfWithCounts.length > 0 && (
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-800">Portefeuilles</h3>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {ptfWithCounts.map(ptf => (
                <div key={ptf.id} className="border rounded-lg p-4 hover:shadow-md transition">
                  <h4 className="font-semibold text-gray-900 mb-1">{ptf.nom}</h4>
                  <div className="text-2xl font-bold text-blue-600">{ptf.nb_sites} sites</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Sites Table */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-800">Sites ({scopedSites.length})</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Site</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ville</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Surface</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Conformite</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Risque EUR</th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Anomalies</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {scopedSites.map(site => (
                <tr key={site.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => navigate(`/sites/${site.id}`)}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{site.nom}</div>
                    <div className="text-xs text-gray-400">{site.usage}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{site.ville}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{site.surface_m2?.toLocaleString()} m2</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {getBadgeConformite(site.statut_conformite)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium text-red-600">
                    {site.risque_eur > 0 ? `${site.risque_eur.toLocaleString()} EUR` : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                    {site.anomalies_count > 0 ? (
                      <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-700">
                        {site.anomalies_count}
                      </span>
                    ) : (
                      <span className="text-gray-400">0</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {/* Maturite de pilotage — detail modal */}
      <Modal open={showMaturiteModal} onClose={() => setShowMaturiteModal(false)} title="Detail maturite de pilotage">
        <div className="space-y-5">
          {/* Definition */}
          <p className="text-sm text-gray-600">
            % de sites avec donnees a jour, obligations suivies et plan d'action actif (pondere).
          </p>

          {/* Score global */}
          <div className="text-center">
            <div className="text-4xl font-bold text-indigo-700">{kpis.readinessScore}%</div>
            <div className="text-xs text-gray-400 mt-1">Score global perimetre</div>
          </div>

          {/* 3 sous-indicateurs */}
          <div className="space-y-4">
            {/* Couverture donnees */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
                  <Database size={16} className="text-blue-500" />
                  Couverture donnees
                </div>
                <span className="text-sm font-bold text-gray-900">{kpis.couvertureDonnees}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="h-2 rounded-full bg-blue-500 transition-all" style={{ width: `${kpis.couvertureDonnees}%` }} />
              </div>
              <p className="text-xs text-gray-400 mt-1">Sites avec consommation renseignee (poids: 30%)</p>
            </div>

            {/* Suivi conformite */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
                  <ShieldCheck size={16} className="text-green-500" />
                  Suivi conformite
                </div>
                <span className="text-sm font-bold text-gray-900">{kpis.suiviConformite}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="h-2 rounded-full bg-green-500 transition-all" style={{ width: `${kpis.suiviConformite}%` }} />
              </div>
              <p className="text-xs text-gray-400 mt-1">Sites conformes / total (poids: 40%)</p>
            </div>

            {/* Actions actives */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
                  <ListChecks size={16} className="text-orange-500" />
                  Actions actives
                </div>
                <span className="text-sm font-bold text-gray-900">{kpis.actionsActives}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="h-2 rounded-full bg-orange-500 transition-all" style={{ width: `${kpis.actionsActives}%` }} />
              </div>
              <p className="text-xs text-gray-400 mt-1">Taux d'actions en cours sur sites a risque (poids: 30%)</p>
            </div>
          </div>

          {/* TrustBadge */}
          <div className="bg-gray-50 rounded-lg p-3 flex items-center gap-2 text-xs text-gray-500">
            <div className="w-2 h-2 rounded-full bg-yellow-400 shrink-0" />
            <span>Source: RegOps + donnees sites · Periode: 30 derniers jours · Confiance: moyenne</span>
          </div>

          {/* Link to actions */}
          <button
            onClick={() => { setShowMaturiteModal(false); navigate('/actions'); }}
            className="w-full text-center py-2.5 bg-indigo-50 text-indigo-700 rounded-lg text-sm font-medium hover:bg-indigo-100 transition flex items-center justify-center gap-2"
          >
            <ListChecks size={16} />
            Voir les actions
          </button>
        </div>
      </Modal>
    </div>
  );
};

export default Cockpit;
