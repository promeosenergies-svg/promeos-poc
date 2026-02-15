/**
 * PROMEOS — Vue Executive (/cockpit) V5 — Top Pages WOW
 * Neutral design, scope-aware KPIs, portfolio tabs, sites table.
 */
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText, ArrowRight, Search,
} from 'lucide-react';
import { useScope } from '../contexts/ScopeContext';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { Badge, Button, Card, CardBody, PageShell, Progress, Modal, Pagination, MetricCard, StatusDot, Tabs, EmptyState } from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';

const Cockpit = () => {
  const navigate = useNavigate();
  const { org, portefeuille, portefeuilles, scopedSites } = useScope();
  const { isExpert } = useExpertMode();
  const [showMaturiteModal, setShowMaturiteModal] = useState(false);
  const [siteSort, setSiteSort] = useState({ col: '', dir: '' });
  const [siteSearch, setSiteSearch] = useState('');
  const [sitePage, setSitePage] = useState(1);
  const [activePtf, setActivePtf] = useState('all');
  const sitePageSize = 20;

  const kpis = useMemo(() => {
    const sites = scopedSites;
    const total = sites.length;
    const conformes = sites.filter(s => s.statut_conformite === 'conforme').length;
    const nonConformes = sites.filter(s => s.statut_conformite === 'non_conforme').length;
    const aRisque = sites.filter(s => s.statut_conformite === 'a_risque').length;
    const risqueTotal = sites.reduce((sum, s) => sum + (s.risque_eur || 0), 0);
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
    const compStatus = nonConformes > 0 ? 'crit' : aRisque > 0 ? 'warn' : total > 0 ? 'ok' : 'neutral';
    const risqueStatus = risqueTotal > 50000 ? 'crit' : risqueTotal > 10000 ? 'warn' : 'ok';
    return { total, conformes, nonConformes, aRisque, risqueTotal, readinessScore, couvertureDonnees, suiviConformite, actionsActives, compStatus, risqueStatus };
  }, [scopedSites]);

  const scopeLabel = portefeuille
    ? `${org.nom} / ${portefeuille.nom}`
    : org.nom;

  const ptfWithCounts = useMemo(() => {
    return portefeuilles.map(pf => {
      const sites = scopedSites.filter(s => ((s.id - 1) % 5) + 1 === pf.id);
      const count = sites.length;
      const conformes = sites.filter(s => s.statut_conformite === 'conforme').length;
      const risque = sites.reduce((sum, s) => sum + (s.risque_eur || 0), 0);
      const pctConf = count > 0 ? Math.round(conformes / count * 100) : 0;
      return { ...pf, nb_sites: count, conformes, risque, pctConf };
    }).filter(pf => pf.nb_sites > 0);
  }, [portefeuilles, scopedSites]);

  // Portfolio tabs
  const ptfTabs = useMemo(() => {
    const tabs = [{ id: 'all', label: `Tous (${scopedSites.length})` }];
    for (const pf of ptfWithCounts) {
      tabs.push({ id: String(pf.id), label: `${pf.nom} (${pf.nb_sites})` });
    }
    return tabs;
  }, [ptfWithCounts, scopedSites.length]);

  // Filter sites by active portfolio tab
  const portfolioFilteredSites = useMemo(() => {
    if (activePtf === 'all') return scopedSites;
    const pfId = parseInt(activePtf);
    return scopedSites.filter(s => ((s.id - 1) % 5) + 1 === pfId);
  }, [activePtf, scopedSites]);

  const filteredSites = useMemo(() => {
    let list = [...portfolioFilteredSites];
    if (siteSearch.trim()) {
      const q = siteSearch.toLowerCase();
      list = list.filter(s =>
        s.nom.toLowerCase().includes(q) ||
        (s.ville || '').toLowerCase().includes(q) ||
        (s.usage || '').toLowerCase().includes(q)
      );
    }
    if (siteSort.col) {
      list.sort((a, b) => {
        let va = a[siteSort.col];
        let vb = b[siteSort.col];
        if (typeof va === 'number' && typeof vb === 'number') {
          return siteSort.dir === 'asc' ? va - vb : vb - va;
        }
        return siteSort.dir === 'asc'
          ? String(va || '').localeCompare(String(vb || ''))
          : String(vb || '').localeCompare(String(va || ''));
      });
    }
    return list;
  }, [portfolioFilteredSites, siteSearch, siteSort]);

  const sitesPageData = filteredSites.slice((sitePage - 1) * sitePageSize, sitePage * sitePageSize);

  function handleSiteSort(col) {
    setSiteSort(prev => {
      if (prev.col === col) {
        if (prev.dir === 'asc') return { col, dir: 'desc' };
        if (prev.dir === 'desc') return { col: '', dir: '' };
      }
      return { col, dir: 'asc' };
    });
    setSitePage(1);
  }

  const getStatusInfo = (statut) => {
    const map = {
      conforme: { dot: 'ok', label: 'Conforme' },
      derogation: { dot: 'info', label: 'Derogation' },
      a_risque: { dot: 'warn', label: 'A risque' },
      non_conforme: { dot: 'crit', label: 'Non conforme' },
      a_evaluer: { dot: 'neutral', label: 'A evaluer' },
    };
    return map[statut] || { dot: 'neutral', label: statut || 'Non defini' };
  };

  return (
    <PageShell
      icon={FileText}
      title="Vue executive"
      subtitle={`${scopeLabel} · ${kpis.total} sites`}
    >
      {/* KPIs — neutral MetricCards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Sites actifs"
          value={kpis.total}
          sub="dans le perimetre"
        />
        <MetricCard
          label="Conformite"
          value={`${kpis.total > 0 ? Math.round(kpis.conformes / kpis.total * 100) : 0}%`}
          sub={`${kpis.conformes} conformes / ${kpis.total}`}
          status={kpis.compStatus}
          onClick={() => navigate('/conformite')}
        />
        <MetricCard
          label="Risque financier"
          value={kpis.risqueTotal > 0 ? `${(kpis.risqueTotal / 1000).toFixed(0)}k EUR` : '0 EUR'}
          sub={`${kpis.nonConformes + kpis.aRisque} sites concernes`}
          status={kpis.risqueStatus}
          onClick={() => navigate('/actions')}
        />

        {/* Maturite — neutral card with progress ring */}
        <Card
          className="cursor-pointer hover:shadow-md hover:-translate-y-0.5 transition-all"
          onClick={() => setShowMaturiteModal(true)}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setShowMaturiteModal(true); } }}
          aria-label="Detail maturite de pilotage"
        >
          <CardBody>
            <p className="text-xs text-gray-500 font-medium uppercase tracking-wider mb-1">Maturite</p>
            <div className="flex items-center gap-3">
              <div className="relative w-14 h-14">
                <svg viewBox="0 0 36 36" className="w-14 h-14 -rotate-90">
                  <circle cx="18" cy="18" r="15.5" fill="none" stroke="#e5e7eb" strokeWidth="3" />
                  <circle
                    cx="18" cy="18" r="15.5" fill="none" stroke="#6b7280" strokeWidth="3"
                    strokeDasharray={`${kpis.readinessScore * 0.975} 100`}
                    strokeLinecap="round"
                  />
                </svg>
                <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-gray-900">
                  {kpis.readinessScore}%
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-500">Donnees + conformite + actions</p>
              </div>
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Priority action — neutral CTA */}
      {(kpis.nonConformes + kpis.aRisque) > 0 && (
        <Card>
          <CardBody>
            <div className="flex items-center justify-between">
              <div className="min-w-0">
                <p className="text-sm text-gray-900">
                  <span className="font-semibold">{kpis.nonConformes + kpis.aRisque} sites</span> non conformes ou a risque
                  {kpis.risqueTotal > 0 && <> — <span className="font-semibold">{(kpis.risqueTotal / 1000).toFixed(0)}k EUR</span> de risque</>}
                </p>
              </div>
              <Button variant="secondary" size="sm" onClick={() => navigate('/actions')}>
                Plan d'action <ArrowRight size={14} />
              </Button>
            </div>
          </CardBody>
        </Card>
      )}

      {/* Portfolio tabs (only if no specific PF selected and multiple exist) */}
      {!portefeuille && ptfWithCounts.length > 1 && (
        <Tabs
          tabs={ptfTabs}
          active={activePtf}
          onChange={(id) => { setActivePtf(id); setSitePage(1); setSiteSearch(''); }}
        />
      )}

      {/* Sites Table */}
      <Card>
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between gap-4">
          <h3 className="text-lg font-semibold text-gray-800">Sites ({filteredSites.length})</h3>
          <div className="relative w-64">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Rechercher un site..."
              value={siteSearch}
              onChange={(e) => { setSiteSearch(e.target.value); setSitePage(1); }}
              className="w-full pl-9 pr-3 py-1.5 border border-gray-300 rounded-lg text-sm placeholder:text-gray-400
                focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {filteredSites.length === 0 ? (
          <div className="py-12">
            <EmptyState
              icon={Search}
              title="Aucun site trouve"
              text={siteSearch ? 'Essayez un autre terme de recherche.' : 'Aucun site dans ce perimetre.'}
              ctaLabel={siteSearch ? 'Effacer' : undefined}
              onCta={siteSearch ? () => setSiteSearch('') : undefined}
            />
          </div>
        ) : (
          <>
            <Table>
              <Thead>
                <tr>
                  <Th sortable sorted={siteSort.col === 'nom' ? siteSort.dir : ''} onSort={() => handleSiteSort('nom')}>Site</Th>
                  <Th sortable sorted={siteSort.col === 'ville' ? siteSort.dir : ''} onSort={() => handleSiteSort('ville')}>Ville</Th>
                  <Th sortable sorted={siteSort.col === 'surface_m2' ? siteSort.dir : ''} onSort={() => handleSiteSort('surface_m2')}>Surface</Th>
                  <Th sortable sorted={siteSort.col === 'statut_conformite' ? siteSort.dir : ''} onSort={() => handleSiteSort('statut_conformite')}>Conformite</Th>
                  <Th sortable sorted={siteSort.col === 'risque_eur' ? siteSort.dir : ''} onSort={() => handleSiteSort('risque_eur')} className="text-right">Risque</Th>
                  {isExpert && <Th sortable sorted={siteSort.col === 'conso_kwh_an' ? siteSort.dir : ''} onSort={() => handleSiteSort('conso_kwh_an')} className="text-right">Conso kWh/an</Th>}
                  <Th className="w-10" />
                </tr>
              </Thead>
              <Tbody>
                {sitesPageData.map(site => {
                  const si = getStatusInfo(site.statut_conformite);
                  return (
                    <Tr key={site.id} onClick={() => navigate(`/sites/${site.id}`)} className="group">
                      <Td>
                        <div className="font-medium text-gray-900">{site.nom}</div>
                        <div className="text-xs text-gray-400">{site.usage}</div>
                      </Td>
                      <Td>{site.ville}</Td>
                      <Td>{site.surface_m2?.toLocaleString()} m2</Td>
                      <Td>
                        <div className="flex items-center gap-1.5">
                          <StatusDot status={si.dot} />
                          <span className="text-xs text-gray-600">{si.label}</span>
                        </div>
                      </Td>
                      <Td className="text-right font-medium text-gray-700">
                        {site.risque_eur > 0 ? `${site.risque_eur.toLocaleString()} EUR` : '-'}
                      </Td>
                      {isExpert && (
                        <Td className="text-right text-gray-600">
                          {site.conso_kwh_an > 0 ? site.conso_kwh_an.toLocaleString() : '-'}
                        </Td>
                      )}
                      <Td className="text-right">
                        <ArrowRight size={14} className="text-gray-300 group-hover:text-gray-500 transition" />
                      </Td>
                    </Tr>
                  );
                })}
              </Tbody>
            </Table>
            <div className="flex items-center justify-end px-4 py-2 border-t border-gray-100">
              <Pagination page={sitePage} pageSize={sitePageSize} total={filteredSites.length} onChange={setSitePage} />
            </div>
          </>
        )}
      </Card>

      {/* Maturite de pilotage — detail modal */}
      <Modal open={showMaturiteModal} onClose={() => setShowMaturiteModal(false)} title="Maturite de pilotage">
        <div className="space-y-5">
          <p className="text-sm text-gray-600">
            Pourcentage de sites avec donnees a jour, obligations suivies et plan d'action actif (pondere).
          </p>

          <div className="text-center">
            <div className="relative w-24 h-24 mx-auto">
              <svg viewBox="0 0 36 36" className="w-24 h-24 -rotate-90">
                <circle cx="18" cy="18" r="15.5" fill="none" stroke="#e5e7eb" strokeWidth="2.5" />
                <circle
                  cx="18" cy="18" r="15.5" fill="none" stroke="#374151" strokeWidth="2.5"
                  strokeDasharray={`${kpis.readinessScore * 0.975} 100`}
                  strokeLinecap="round"
                />
              </svg>
              <span className="absolute inset-0 flex items-center justify-center text-2xl font-bold text-gray-900">
                {kpis.readinessScore}%
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-2">Score global perimetre</p>
          </div>

          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between text-sm text-gray-700 mb-1">
                <span>Couverture donnees</span>
                <span className="text-xs text-gray-400">poids: 30%</span>
              </div>
              <Progress value={kpis.couvertureDonnees} color="gray" size="sm" />
              <p className="text-xs text-gray-400 mt-0.5">{kpis.couvertureDonnees}% des sites avec consommation renseignee</p>
            </div>

            <div>
              <div className="flex items-center justify-between text-sm text-gray-700 mb-1">
                <span>Suivi conformite</span>
                <span className="text-xs text-gray-400">poids: 40%</span>
              </div>
              <Progress value={kpis.suiviConformite} color="gray" size="sm" />
              <p className="text-xs text-gray-400 mt-0.5">{kpis.suiviConformite}% des sites conformes</p>
            </div>

            <div>
              <div className="flex items-center justify-between text-sm text-gray-700 mb-1">
                <span>Actions actives</span>
                <span className="text-xs text-gray-400">poids: 30%</span>
              </div>
              <Progress value={kpis.actionsActives} color="gray" size="sm" />
              <p className="text-xs text-gray-400 mt-0.5">{kpis.actionsActives}% taux d'actions en cours</p>
            </div>
          </div>

          <button
            onClick={() => { setShowMaturiteModal(false); navigate('/actions'); }}
            className="w-full text-center py-2.5 bg-gray-50 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-100 transition"
          >
            Voir les actions
          </button>
        </div>
      </Modal>
    </PageShell>
  );
};

export default Cockpit;
