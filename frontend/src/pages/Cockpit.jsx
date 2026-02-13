/**
 * PROMEOS — Vue Executive (/cockpit) V4
 * PageShell + KpiCard + Progress + Expert Mode + Table UI kit
 */
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText, Rocket, ArrowRight, Info, Database, ShieldCheck, ListChecks,
  Building2, Zap,
} from 'lucide-react';
import { useScope } from '../contexts/ScopeContext';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { Badge, Button, Card, CardBody, KpiCard, PageShell, Progress, Modal } from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';

const Cockpit = () => {
  const navigate = useNavigate();
  const { org, portefeuille, portefeuilles, scopedSites } = useScope();
  const { isExpert } = useExpertMode();
  const [showMaturiteModal, setShowMaturiteModal] = useState(false);

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

  const scopeLabel = portefeuille
    ? `${org.nom} / ${portefeuille.nom}`
    : org.nom;

  const ptfWithCounts = useMemo(() => {
    return portefeuilles.map(pf => {
      const count = scopedSites.filter(s => ((s.id - 1) % 5) + 1 === pf.id).length;
      return { ...pf, nb_sites: count };
    }).filter(pf => pf.nb_sites > 0);
  }, [portefeuilles, scopedSites]);

  const getBadgeConformite = (statut) => {
    const statusMap = {
      conforme: 'ok',
      derogation: 'info',
      a_risque: 'warn',
      non_conforme: 'crit',
      a_evaluer: 'neutral',
    };
    const labels = {
      conforme: 'Conforme',
      derogation: 'Derogation',
      a_risque: 'A risque',
      non_conforme: 'Non conforme',
      a_evaluer: 'A evaluer',
    };
    return <Badge status={statusMap[statut] || 'neutral'}>{labels[statut] || statut || 'Non defini'}</Badge>;
  };

  return (
    <PageShell
      icon={FileText}
      title="Vue executive"
      subtitle={`KPIs portefeuille & priorites multi-sites — ${scopeLabel} · ${kpis.total} sites`}
    >
      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <KpiCard
          icon={Building2}
          title="Sites Actifs"
          value={kpis.total}
          sub="dans le perimetre"
          color="bg-blue-600"
        />
        <KpiCard
          icon={Zap}
          title="Avancement Decret 2030"
          value={`${kpis.avgAvancement}%`}
          sub="trajectoire moyenne"
          color="bg-green-600"
        />
        <KpiCard
          icon={ShieldCheck}
          title="Sites Non Conformes"
          value={kpis.nonConformes + kpis.aRisque}
          sub={`Non conformes: ${kpis.nonConformes} | A risque: ${kpis.aRisque}`}
          color="bg-orange-500"
        />
        <KpiCard
          icon={ListChecks}
          title="Risque Financier"
          value={`${(kpis.risqueTotal / 1000).toFixed(0)}k EUR`}
          sub={`${kpis.nonConformes + kpis.aRisque} sites a risque`}
          color="bg-red-600"
        />

        {/* Maturite — special gradient card */}
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
        <Button variant="secondary" onClick={() => navigate('/actions')} className="bg-white text-indigo-700 hover:bg-indigo-50 border-0">
          Plan d'action <ArrowRight size={16} />
        </Button>
      </div>

      {/* Portefeuilles (only if no specific PF selected) */}
      {!portefeuille && ptfWithCounts.length > 0 && (
        <Card>
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-800">Portefeuilles</h3>
          </div>
          <CardBody>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {ptfWithCounts.map(ptf => (
                <div key={ptf.id} className="border rounded-lg p-4 hover:shadow-md transition cursor-pointer">
                  <h4 className="font-semibold text-gray-900 mb-1">{ptf.nom}</h4>
                  <div className="text-2xl font-bold text-blue-600">{ptf.nb_sites} sites</div>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      )}

      {/* Sites Table */}
      <Card>
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-800">Sites ({scopedSites.length})</h3>
        </div>
        <Table>
          <Thead>
            <tr>
              <Th>Site</Th>
              <Th>Ville</Th>
              <Th>Surface</Th>
              <Th>Conformite</Th>
              <Th className="text-right">Risque EUR</Th>
              {isExpert && <Th className="text-right">Conso kWh/an</Th>}
              <Th className="text-center">Anomalies</Th>
            </tr>
          </Thead>
          <Tbody>
            {scopedSites.map(site => (
              <Tr key={site.id} onClick={() => navigate(`/sites/${site.id}`)}>
                <Td>
                  <div className="font-medium text-gray-900">{site.nom}</div>
                  <div className="text-xs text-gray-400">{site.usage}</div>
                </Td>
                <Td>{site.ville}</Td>
                <Td>{site.surface_m2?.toLocaleString()} m2</Td>
                <Td>{getBadgeConformite(site.statut_conformite)}</Td>
                <Td className="text-right font-medium text-red-600">
                  {site.risque_eur > 0 ? `${site.risque_eur.toLocaleString()} EUR` : '-'}
                </Td>
                {isExpert && (
                  <Td className="text-right text-gray-600">
                    {site.conso_kwh_an > 0 ? site.conso_kwh_an.toLocaleString() : '-'}
                  </Td>
                )}
                <Td className="text-center">
                  {site.anomalies_count > 0 ? (
                    <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-700">
                      {site.anomalies_count}
                    </span>
                  ) : (
                    <span className="text-gray-400">0</span>
                  )}
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      </Card>

      {/* Maturite de pilotage — detail modal */}
      <Modal open={showMaturiteModal} onClose={() => setShowMaturiteModal(false)} title="Detail maturite de pilotage">
        <div className="space-y-5">
          <p className="text-sm text-gray-600">
            % de sites avec donnees a jour, obligations suivies et plan d'action actif (pondere).
          </p>

          <div className="text-center">
            <div className="text-4xl font-bold text-indigo-700">{kpis.readinessScore}%</div>
            <div className="text-xs text-gray-400 mt-1">Score global perimetre</div>
          </div>

          <div className="space-y-4">
            <div>
              <div className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-1">
                <Database size={16} className="text-blue-500" />
                Couverture donnees
              </div>
              <Progress value={kpis.couvertureDonnees} color="blue" label="Sites avec consommation renseignee (poids: 30%)" />
            </div>

            <div>
              <div className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-1">
                <ShieldCheck size={16} className="text-green-500" />
                Suivi conformite
              </div>
              <Progress value={kpis.suiviConformite} color="green" label="Sites conformes / total (poids: 40%)" />
            </div>

            <div>
              <div className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-1">
                <ListChecks size={16} className="text-amber-500" />
                Actions actives
              </div>
              <Progress value={kpis.actionsActives} color="amber" label="Taux d'actions en cours sur sites a risque (poids: 30%)" />
            </div>
          </div>

          <div className="bg-gray-50 rounded-lg p-3 flex items-center gap-2 text-xs text-gray-500">
            <div className="w-2 h-2 rounded-full bg-yellow-400 shrink-0" />
            <span>Source: RegOps + donnees sites · Periode: 30 derniers jours · Confiance: moyenne</span>
          </div>

          <button
            onClick={() => { setShowMaturiteModal(false); navigate('/actions'); }}
            className="w-full text-center py-2.5 bg-indigo-50 text-indigo-700 rounded-lg text-sm font-medium hover:bg-indigo-100 transition flex items-center justify-center gap-2"
          >
            <ListChecks size={16} />
            Voir les actions
          </button>
        </div>
      </Modal>
    </PageShell>
  );
};

export default Cockpit;
