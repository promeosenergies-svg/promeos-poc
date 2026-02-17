/**
 * PROMEOS — Vue Executive (/cockpit) Phase 6
 * Hero band "Plan d'action", accent MetricCards, mode 1 site insights.
 */
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText, ArrowRight, Search, ShieldCheck, TrendingDown, AlertTriangle,
  Building2, Clock, Zap,
} from 'lucide-react';
import { useScope } from '../contexts/ScopeContext';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { Badge, Button, Card, CardBody, PageShell, Progress, Modal, Pagination, MetricCard, StatusDot, Tabs, EmptyState } from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';
import { HERO_ACCENTS } from '../ui/colorTokens';

const Cockpit = () => {
  const navigate = useNavigate();
  const { org, portefeuille, portefeuilles, scopedSites, sitesCount } = useScope();
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

  const isSingleSite = scopedSites.length === 1;
  const singleSite = isSingleSite ? scopedSites[0] : null;

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

  const ptfTabs = useMemo(() => {
    const tabs = [{ id: 'all', label: `Tous (${scopedSites.length})` }];
    for (const pf of ptfWithCounts) {
      tabs.push({ id: String(pf.id), label: `${pf.nom} (${pf.nb_sites})` });
    }
    return tabs;
  }, [ptfWithCounts, scopedSites.length]);

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
      subtitle={`${scopeLabel} · ${sitesCount} site${sitesCount !== 1 ? 's' : ''}`}
    >
      {/* ── KPIs with accents ── */}
      <div className={`grid gap-4 ${isSingleSite ? 'grid-cols-1 sm:grid-cols-3' : 'grid-cols-2 lg:grid-cols-4'}`}>
        {!isSingleSite && (
          <MetricCard
            accent="sites"
            icon={Building2}
            label="Sites actifs"
            value={kpis.total}
            sub="dans le perimetre"
          />
        )}
        <MetricCard
          accent="conformite"
          icon={ShieldCheck}
          label="Conformite"
          value={`${kpis.total > 0 ? Math.round(kpis.conformes / kpis.total * 100) : 0}%`}
          sub={`${kpis.conformes} conformes / ${kpis.total}`}
          status={kpis.compStatus}
          onClick={() => navigate('/conformite')}
        />
        <MetricCard
          accent="risque"
          icon={TrendingDown}
          label="Risque financier"
          value={kpis.risqueTotal > 0 ? `${(kpis.risqueTotal / 1000).toFixed(0)}k EUR` : '0 EUR'}
          sub={`${kpis.nonConformes + kpis.aRisque} sites concernes`}
          status={kpis.risqueStatus}
          onClick={() => navigate('/actions')}
        />

        {/* Maturite — accent card with progress ring */}
        <Card
          className="cursor-pointer hover:shadow-md hover:-translate-y-0.5 transition-all overflow-hidden"
          onClick={() => setShowMaturiteModal(true)}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setShowMaturiteModal(true); } }}
          aria-label="Detail maturite de pilotage"
        >
          <div className="flex">
            <div className="w-[3px] shrink-0 bg-blue-400 rounded-l-lg" />
            <CardBody className="flex-1">
              <p className="text-xs text-gray-500 font-medium uppercase tracking-wider mb-1">Maturite</p>
              <div className="flex items-center gap-3">
                <div className="relative w-14 h-14">
                  <svg viewBox="0 0 36 36" className="w-14 h-14 -rotate-90">
                    <circle cx="18" cy="18" r="15.5" fill="none" stroke="#e5e7eb" strokeWidth="3" />
                    <circle
                      cx="18" cy="18" r="15.5" fill="none" stroke="#3b82f6" strokeWidth="3"
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
          </div>
        </Card>
      </div>

      {/* ── Hero Band: Plan d'action priorise ── */}
      {(kpis.nonConformes + kpis.aRisque) > 0 && (
        <div className={`rounded-lg border p-5 ${HERO_ACCENTS.executive.bg} ${HERO_ACCENTS.executive.border} ${HERO_ACCENTS.executive.ring}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-indigo-100 flex items-center justify-center">
                <AlertTriangle size={18} className="text-indigo-600" />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-900">
                  {kpis.nonConformes + kpis.aRisque} site{(kpis.nonConformes + kpis.aRisque) > 1 ? 's' : ''} non conforme{(kpis.nonConformes + kpis.aRisque) > 1 ? 's' : ''} ou a risque
                </p>
                {kpis.risqueTotal > 0 && (
                  <p className="text-xs text-gray-500 mt-0.5">
                    Risque estime : {(kpis.risqueTotal / 1000).toFixed(0)}k EUR
                  </p>
                )}
              </div>
            </div>
            <Button size="sm" onClick={() => navigate('/actions')}>
              Plan d'action <ArrowRight size={14} />
            </Button>
          </div>
        </div>
      )}

      {/* ── Mode 1 site: quick insights ── */}
      {isSingleSite && singleSite && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card>
            <CardBody className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
                <ShieldCheck size={16} className="text-gray-500" />
              </div>
              <div>
                <p className="text-[10px] text-gray-500 font-medium uppercase">Statut</p>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <StatusDot status={getStatusInfo(singleSite.statut_conformite).dot} />
                  <span className="text-sm font-medium text-gray-900">{getStatusInfo(singleSite.statut_conformite).label}</span>
                </div>
              </div>
            </CardBody>
          </Card>
          <Card>
            <CardBody className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
                <TrendingDown size={16} className="text-gray-500" />
              </div>
              <div>
                <p className="text-[10px] text-gray-500 font-medium uppercase">Risque</p>
                <p className="text-sm font-medium text-gray-900 mt-0.5">
                  {singleSite.risque_eur > 0 ? `${singleSite.risque_eur.toLocaleString('fr-FR')} EUR` : 'Aucun'}
                </p>
              </div>
            </CardBody>
          </Card>
          <Card>
            <CardBody className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
                <Zap size={16} className="text-gray-500" />
              </div>
              <div>
                <p className="text-[10px] text-gray-500 font-medium uppercase">Consommation</p>
                <p className="text-sm font-medium text-gray-900 mt-0.5">
                  {singleSite.conso_kwh_an > 0 ? `${singleSite.conso_kwh_an.toLocaleString('fr-FR')} kWh/an` : 'Non renseignee'}
                </p>
              </div>
            </CardBody>
          </Card>
        </div>
      )}

      {/* Portfolio tabs */}
      {!portefeuille && !isSingleSite && ptfWithCounts.length > 1 && (
        <Tabs
          tabs={ptfTabs}
          active={activePtf}
          onChange={(id) => { setActivePtf(id); setSitePage(1); setSiteSearch(''); }}
        />
      )}

      {/* Sites Table */}
      {!isSingleSite && (
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
                      <Tr key={site.id} onClick={() => navigate(`/sites/${site.id}`)} className="group cursor-pointer hover:bg-blue-50/40">
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
                        <Td className="text-right text-sm font-medium">
                          {site.risque_eur > 0 ? (
                            <span className="text-amber-700">{site.risque_eur.toLocaleString('fr-FR')} EUR</span>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
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
      )}

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
                  cx="18" cy="18" r="15.5" fill="none" stroke="#3b82f6" strokeWidth="2.5"
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
                <span className="text-xs text-gray-400">poids : 30%</span>
              </div>
              <Progress value={kpis.couvertureDonnees} color="blue" size="sm" />
              <p className="text-xs text-gray-400 mt-0.5">{kpis.couvertureDonnees}% des sites avec consommation renseignee</p>
            </div>

            <div>
              <div className="flex items-center justify-between text-sm text-gray-700 mb-1">
                <span>Suivi conformite</span>
                <span className="text-xs text-gray-400">poids : 40%</span>
              </div>
              <Progress value={kpis.suiviConformite} color="blue" size="sm" />
              <p className="text-xs text-gray-400 mt-0.5">{kpis.suiviConformite}% des sites conformes</p>
            </div>

            <div>
              <div className="flex items-center justify-between text-sm text-gray-700 mb-1">
                <span>Actions actives</span>
                <span className="text-xs text-gray-400">poids : 30%</span>
              </div>
              <Progress value={kpis.actionsActives} color="blue" size="sm" />
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
