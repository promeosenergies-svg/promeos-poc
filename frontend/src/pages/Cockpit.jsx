/**
 * PROMEOS — Vue exécutive (/cockpit) Cockpit V2
 * Résumé exécutif + KPIs décideur + Briefing + Risques + Opportunités.
 * EssentialsRow + données relégués en bas.
 */
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText, ArrowRight, Search, ShieldCheck, TrendingDown, AlertTriangle,
  Zap,
} from 'lucide-react';
import { useScope } from '../contexts/ScopeContext';
import { useExpertMode } from '../contexts/ExpertModeContext';
import useRenderTiming from '../hooks/useRenderTiming';
import { toActionsList } from '../services/routes';
import { Button, Card, CardBody, PageShell, Progress, Modal, Pagination, StatusDot, Tabs, EmptyState, ScopeSummary } from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';
import { SkeletonCard, SkeletonTable } from '../ui/Skeleton';
import { KPI_ACCENTS } from '../ui/colorTokens';
// Cockpit V2 — model + sub-components
import {
  buildWatchlist, buildTopSites, buildOpportunities, checkConsistency, buildBriefing,
  buildTodayActions, buildExecutiveSummary, buildExecutiveKpis,
} from '../models/dashboardEssentials';
import EssentialsRow from './cockpit/EssentialsRow';
import WatchlistCard from './cockpit/WatchlistCard';
import OpportunitiesCard from './cockpit/OpportunitiesCard';
import TopSitesCard from './cockpit/TopSitesCard';
import ModuleLaunchers from './cockpit/ModuleLaunchers';
import BriefingHeroCard from './cockpit/BriefingHeroCard';
import ExecutiveSummaryCard from './cockpit/ExecutiveSummaryCard';
import ExecutiveKpiRow from './cockpit/ExecutiveKpiRow';
import ImpactDecisionPanel from './cockpit/ImpactDecisionPanel';
import DataActivationPanel from './cockpit/DataActivationPanel';
import { READINESS_WEIGHTS, ACTIONS_SCORE, getRiskStatus, getStatusBadgeProps } from '../lib/constants';

// ── Consistency banner (inline — too small for its own file) ─────────────────
function ConsistencyBanner({ issues }) {
  if (!issues?.length) return null;
  return (
    <div className="flex items-start gap-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
      <AlertTriangle size={13} className="shrink-0 mt-0.5" />
      <span>{issues[0].label} — synchronisation recommandée.</span>
    </div>
  );
}

const Cockpit = () => {
  useRenderTiming('Cockpit');
  const navigate = useNavigate();
  const { org, portefeuille, portefeuilles, scopedSites, sitesLoading } = useScope();
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
      ? Math.round(sites.filter(s => s.statut_conformite === 'non_conforme' || s.statut_conformite === 'a_risque').length > 0 ? ACTIONS_SCORE.withIssues : ACTIONS_SCORE.noIssues)
      : 0;
    const readinessScore = total > 0
      ? Math.round(couvertureDonnees * READINESS_WEIGHTS.data + suiviConformite * READINESS_WEIGHTS.conformity + actionsActives * READINESS_WEIGHTS.actions)
      : 0;
    const compStatus = nonConformes > 0 ? 'crit' : aRisque > 0 ? 'warn' : total > 0 ? 'ok' : 'neutral';
    const risqueStatus = getRiskStatus(risqueTotal);
    return { total, conformes, nonConformes, aRisque, risqueTotal, readinessScore, couvertureDonnees, suiviConformite, actionsActives, compStatus, risqueStatus };
  }, [scopedSites]);

  const isSingleSite = scopedSites.length === 1;
  const singleSite = isSingleSite ? scopedSites[0] : null;

  // Cockpit V2 — derived model data (no extra API calls)
  const watchlist         = useMemo(() => buildWatchlist(kpis, scopedSites),                          [kpis, scopedSites]);         // eslint-disable-line react-hooks/exhaustive-deps
  const briefing          = useMemo(() => buildBriefing(kpis, watchlist),                             [kpis, watchlist]);           // eslint-disable-line react-hooks/exhaustive-deps
  const consistency       = useMemo(() => checkConsistency(kpis),                                     [kpis]);                     // eslint-disable-line react-hooks/exhaustive-deps
  const opportunities     = useMemo(() => buildOpportunities(kpis, scopedSites, { isExpert }),        [kpis, scopedSites, isExpert]); // eslint-disable-line react-hooks/exhaustive-deps
  const topSites          = useMemo(() => buildTopSites(scopedSites),                                 [scopedSites]);              // eslint-disable-line react-hooks/exhaustive-deps
  const executiveSummary  = useMemo(() => buildExecutiveSummary(kpis, topSites),                      [kpis, topSites]);           // eslint-disable-line react-hooks/exhaustive-deps
  const executiveKpis     = useMemo(() => buildExecutiveKpis(kpis, scopedSites),                      [kpis, scopedSites]);        // eslint-disable-line react-hooks/exhaustive-deps
  const _todayActions     = useMemo(() => buildTodayActions(kpis, watchlist, opportunities),          [kpis, watchlist, opportunities]); // eslint-disable-line react-hooks/exhaustive-deps

  const _scopeLabel = portefeuille
    ? `${org?.nom || 'Organisation'} / ${portefeuille.nom}`
    : (org?.nom || 'Organisation');

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
    const { variant, label } = getStatusBadgeProps(statut);
    return { dot: variant, label };
  };

  // V18-B: guard — don't show empty state while sites are loading
  if (sitesLoading) {
    return (
      <PageShell icon={FileText} title="Vue exécutive" subtitle={<ScopeSummary />}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <SkeletonCard /><SkeletonCard /><SkeletonCard /><SkeletonCard />
        </div>
        <SkeletonTable rows={5} cols={5} />
      </PageShell>
    );
  }

  return (
    <PageShell
      icon={FileText}
      title="Vue exécutive"
      subtitle={<ScopeSummary />}
    >
      {/* ── Résumé exécutif (Cockpit V2) ── */}
      <ExecutiveSummaryCard bullets={executiveSummary} onNavigate={navigate} />

      {/* ── KPIs décideur 4 tuiles (Cockpit V2) ── */}
      <ExecutiveKpiRow kpis={executiveKpis} onNavigate={navigate} />

      {/* ── Impact & Décision ── */}
      <ImpactDecisionPanel kpis={kpis} />

      {/* ── Briefing du jour ── */}
      <BriefingHeroCard briefing={briefing} onNavigate={navigate} />

      {/* ── Avertissement cohérence données ── */}
      {!consistency.ok && <ConsistencyBanner issues={consistency.issues} />}

      <WatchlistCard
        watchlist={watchlist}
        consistency={consistency}
        onNavigate={navigate}
      />

      {isExpert && opportunities.length > 0 && (
        <OpportunitiesCard opportunities={opportunities} onNavigate={navigate} />
      )}

      {!isSingleSite && (
        <TopSitesCard topSites={topSites} onNavigate={navigate} />
      )}

      <ModuleLaunchers kpis={kpis} isExpert={isExpert} onNavigate={navigate} />

      {/* ── Activation des données V37 ── */}
      <DataActivationPanel kpis={kpis} />

      {/* ── Données & connexions (relégué) ── */}
      <EssentialsRow
        kpis={kpis}
        sites={scopedSites}
        onOpenMaturite={() => setShowMaturiteModal(true)}
        onNavigate={navigate}
      />

      {/* ── Risque résiduel : plan d'action ── */}
      {(kpis.nonConformes + kpis.aRisque) > 0 && (
        <div className="rounded-lg border p-5 bg-amber-50 border-amber-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${KPI_ACCENTS.alertes.iconBg}`}>
                <AlertTriangle size={18} className={KPI_ACCENTS.alertes.iconText} />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-900">
                  {kpis.nonConformes + kpis.aRisque} site{(kpis.nonConformes + kpis.aRisque) > 1 ? 's' : ''} non conforme{(kpis.nonConformes + kpis.aRisque) > 1 ? 's' : ''} ou à risque
                </p>
                {kpis.risqueTotal > 0 && (
                  <p className="text-xs text-gray-500 mt-0.5">
                    Risque estimé : {(kpis.risqueTotal / 1000).toFixed(0)}k€
                  </p>
                )}
              </div>
            </div>
            <Button size="sm" onClick={() => navigate(toActionsList())}>
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
                  {singleSite.risque_eur > 0 ? `${singleSite.risque_eur.toLocaleString('fr-FR')} €` : 'Aucun'}
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
                  {singleSite.conso_kwh_an > 0 ? `${singleSite.conso_kwh_an.toLocaleString('fr-FR')} kWh/an` : 'Non renseignée'}
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
                placeholder="Rechercher un site…"
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
                title="Aucun site trouvé"
                text={siteSearch ? 'Essayez un autre terme de recherche.' : 'Aucun site dans ce périmètre.'}
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
                    <Th sortable sorted={siteSort.col === 'statut_conformite' ? siteSort.dir : ''} onSort={() => handleSiteSort('statut_conformite')}>Conformité</Th>
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
                            <span className="text-amber-700">{site.risque_eur.toLocaleString('fr-FR')} €</span>
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

      {/* Maturité de pilotage — détail modal */}
      <Modal open={showMaturiteModal} onClose={() => setShowMaturiteModal(false)} title="Maturité de pilotage">
        <div className="space-y-5">
          <p className="text-sm text-gray-600">
            Pourcentage de sites avec données à jour, obligations suivies et plan d'action actif (pondéré).
          </p>

          <div className="text-center">
            <div className="relative w-24 h-24 mx-auto">
              <svg viewBox="0 0 36 36" className="w-24 h-24 -rotate-90">
                <circle cx="18" cy="18" r="15.5" fill="none" className="stroke-gray-200" strokeWidth="2.5" />
                <circle
                  cx="18" cy="18" r="15.5" fill="none" className="stroke-blue-500" strokeWidth="2.5"
                  strokeDasharray={`${kpis.readinessScore * 0.975} 100`}
                  strokeLinecap="round"
                />
              </svg>
              <span className="absolute inset-0 flex items-center justify-center text-2xl font-bold text-gray-900">
                {kpis.readinessScore}%
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-2">Score global périmètre</p>
          </div>

          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between text-sm text-gray-700 mb-1">
                <span>Couverture données</span>
                <span className="text-xs text-gray-400">poids : {Math.round(READINESS_WEIGHTS.data * 100)}%</span>
              </div>
              <Progress value={kpis.couvertureDonnees} color="blue" size="sm" />
              <p className="text-xs text-gray-400 mt-0.5">{kpis.couvertureDonnees}% des sites avec consommation renseignée</p>
            </div>

            <div>
              <div className="flex items-center justify-between text-sm text-gray-700 mb-1">
                <span>Suivi conformité</span>
                <span className="text-xs text-gray-400">poids : {Math.round(READINESS_WEIGHTS.conformity * 100)}%</span>
              </div>
              <Progress value={kpis.suiviConformite} color="blue" size="sm" />
              <p className="text-xs text-gray-400 mt-0.5">{kpis.suiviConformite}% des sites conformes</p>
            </div>

            <div>
              <div className="flex items-center justify-between text-sm text-gray-700 mb-1">
                <span>Actions actives</span>
                <span className="text-xs text-gray-400">poids : {Math.round(READINESS_WEIGHTS.actions * 100)}%</span>
              </div>
              <Progress value={kpis.actionsActives} color="blue" size="sm" />
              <p className="text-xs text-gray-400 mt-0.5">{kpis.actionsActives}% taux d'actions en cours</p>
            </div>
          </div>

          <button
            onClick={() => { setShowMaturiteModal(false); navigate(toActionsList()); }}
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
