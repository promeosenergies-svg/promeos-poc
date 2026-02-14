/**
 * PROMEOS - Patrimoine (/patrimoine) V4 — WOW Cockpit
 * SiteDrawer + address sub-line + skeleton + premium empty states + actionable KPIs + bulk EUR.
 */
import { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Building2, Search, RotateCcw, BookmarkPlus, Download, Star,
  Plus, ChevronDown, Rows3, Rows4, Upload, MapPin,
  ShieldCheck, AlertTriangle, Ruler, BadgeEuro, Zap,
  ExternalLink, MoreHorizontal, Eye, Copy, FileText,
  Gauge, TrendingUp, Lightbulb, ChevronRight,
} from 'lucide-react';
import {
  Card, CardBody, Badge, Button, Select, Pagination, EmptyState, TrustBadge,
  PageShell, KpiCard, Modal, Input, Drawer, Skeleton,
} from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td, ThCheckbox, TdCheckbox } from '../ui';
import { useScope } from '../contexts/ScopeContext';
import { useExpertMode } from '../contexts/ExpertModeContext';
import CreateActionModal from '../components/CreateActionModal';
import PatrimoineWizard from '../components/PatrimoineWizard';
import { track } from '../services/tracker';

const DEFAULT_PAGE_SIZE = 25;

const USAGE_OPTIONS = [
  { value: '', label: 'Tous les usages' },
  { value: 'bureau', label: 'Bureau' }, { value: 'commerce', label: 'Commerce' },
  { value: 'entrepot', label: 'Entrepot' }, { value: 'hotel', label: 'Hotel' },
  { value: 'sante', label: 'Sante' }, { value: 'enseignement', label: 'Enseignement' },
  { value: 'copropriete', label: 'Copropriete' }, { value: 'collectivite', label: 'Collectivite' },
];

const STATUT_OPTIONS = [
  { value: '', label: 'Tous les statuts' },
  { value: 'conforme', label: 'Conforme' }, { value: 'non_conforme', label: 'Non conforme' },
  { value: 'a_risque', label: 'A risque' }, { value: 'a_evaluer', label: 'A evaluer' },
];

const STATUT_BADGE = {
  conforme: { status: 'ok', label: 'Conforme' },
  non_conforme: { status: 'crit', label: 'Non conforme' },
  a_risque: { status: 'warn', label: 'A risque' },
  a_evaluer: { status: 'neutral', label: 'A evaluer' },
};

const USAGE_COLOR = {
  bureau: 'bg-blue-100 text-blue-700',
  commerce: 'bg-purple-100 text-purple-700',
  entrepot: 'bg-gray-100 text-gray-700',
  hotel: 'bg-amber-100 text-amber-700',
  sante: 'bg-red-100 text-red-700',
  enseignement: 'bg-green-100 text-green-700',
  copropriete: 'bg-indigo-100 text-indigo-700',
  collectivite: 'bg-teal-100 text-teal-700',
};

// Saved views (localStorage)
const VIEWS_KEY = 'promeos_saved_views';
function loadViews() { try { return JSON.parse(localStorage.getItem(VIEWS_KEY) || '[]'); } catch { return []; } }
function persistViews(v) { localStorage.setItem(VIEWS_KEY, JSON.stringify(v)); }

export default function Patrimoine() {
  const navigate = useNavigate();
  const { scopedSites } = useScope();
  const { isExpert } = useExpertMode();
  const [search, setSearch] = useState('');
  const [filterUsage, setFilterUsage] = useState('');
  const [filterStatut, setFilterStatut] = useState('');
  const [filterAnomalies, setFilterAnomalies] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [sortCol, setSortCol] = useState('');
  const [sortDir, setSortDir] = useState('');
  const [selected, setSelected] = useState(new Set());
  const [compact, setCompact] = useState(false);
  const [showActionModal, setShowActionModal] = useState(false);
  const [showWizard, setShowWizard] = useState(false);
  const [savedViews, setSavedViews] = useState(loadViews);
  const [showViewMenu, setShowViewMenu] = useState(false);
  const [showSaveViewModal, setShowSaveViewModal] = useState(false);
  const [newViewName, setNewViewName] = useState('');
  const [drawerSite, setDrawerSite] = useState(null);
  const [favorites, setFavorites] = useState(() => {
    try { return new Set(JSON.parse(localStorage.getItem('promeos_fav_sites') || '[]')); } catch { return new Set(); }
  });

  const patrimoineStats = useMemo(() => {
    const total = scopedSites.length;
    const conformes = scopedSites.filter(s => s.statut_conformite === 'conforme').length;
    const nonConformes = scopedSites.filter(s => s.statut_conformite === 'non_conforme').length;
    const aRisque = scopedSites.filter(s => s.statut_conformite === 'a_risque').length;
    const risqueTotal = scopedSites.reduce((sum, s) => sum + (s.risque_eur || 0), 0);
    const surfaceTotale = scopedSites.reduce((sum, s) => sum + (s.surface_m2 || 0), 0);
    const anomaliesTotal = scopedSites.reduce((sum, s) => sum + (s.anomalies_count || 0), 0);
    const withAnomalies = scopedSites.filter(s => (s.anomalies_count || 0) > 0).length;
    return { total, conformes, nonConformes, aRisque, risqueTotal, surfaceTotale, anomaliesTotal, withAnomalies };
  }, [scopedSites]);

  const filtered = useMemo(() => {
    let result = [...scopedSites];
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(s =>
        s.nom.toLowerCase().includes(q) ||
        s.ville.toLowerCase().includes(q) ||
        s.adresse.toLowerCase().includes(q) ||
        (s.code_postal || '').includes(q)
      );
    }
    if (filterUsage) result = result.filter(s => s.usage === filterUsage);
    if (filterStatut) result = result.filter(s => s.statut_conformite === filterStatut);
    if (filterAnomalies) result = result.filter(s => (s.anomalies_count || 0) > 0);
    if (sortCol) {
      result.sort((a, b) => {
        const va = a[sortCol], vb = b[sortCol];
        if (typeof va === 'number') return sortDir === 'asc' ? va - vb : vb - va;
        return sortDir === 'asc' ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
      });
    }
    return result;
  }, [scopedSites, search, filterUsage, filterStatut, filterAnomalies, sortCol, sortDir]);

  const total = filtered.length;
  const pageData = filtered.slice((page - 1) * pageSize, page * pageSize);

  // Selected sites stats for bulk bar
  const selectedStats = useMemo(() => {
    if (selected.size === 0) return null;
    const sites = scopedSites.filter(s => selected.has(s.id));
    return {
      count: sites.length,
      risque: sites.reduce((sum, s) => sum + (s.risque_eur || 0), 0),
      surface: sites.reduce((sum, s) => sum + (s.surface_m2 || 0), 0),
    };
  }, [selected, scopedSites]);

  function handleSort(col) {
    if (sortCol === col) {
      setSortDir(d => d === 'asc' ? 'desc' : d === 'desc' ? '' : 'asc');
      if (sortDir === 'desc') setSortCol('');
    } else { setSortCol(col); setSortDir('asc'); }
    setPage(1);
    track('filter_apply', { action: 'sort', col });
  }

  function resetFilters() {
    setSearch(''); setFilterUsage(''); setFilterStatut(''); setFilterAnomalies(false); setPage(1);
    track('filter_apply', { action: 'reset' });
  }

  function toggleSelect(id) {
    setSelected(prev => { const next = new Set(prev); next.has(id) ? next.delete(id) : next.add(id); return next; });
  }

  function toggleSelectAll() {
    if (selected.size === pageData.length) setSelected(new Set());
    else setSelected(new Set(pageData.map(s => s.id)));
  }

  // Saved views
  function saveCurrentView() { setNewViewName(''); setShowSaveViewModal(true); }

  function confirmSaveView() {
    if (!newViewName.trim()) return;
    const view = { id: Date.now(), name: newViewName.trim(), filters: { search, filterUsage, filterStatut, filterAnomalies }, sort: { sortCol, sortDir }, pageSize };
    const next = [...savedViews, view];
    setSavedViews(next);
    persistViews(next);
    track('view_save', { name: newViewName.trim() });
    setShowSaveViewModal(false);
  }

  function applyView(view) {
    setSearch(view.filters.search || '');
    setFilterUsage(view.filters.filterUsage || '');
    setFilterStatut(view.filters.filterStatut || '');
    setFilterAnomalies(view.filters.filterAnomalies || false);
    setSortCol(view.sort.sortCol || '');
    setSortDir(view.sort.sortDir || '');
    if (view.pageSize) setPageSize(view.pageSize);
    setPage(1);
    setShowViewMenu(false);
    track('filter_apply', { action: 'apply_view', name: view.name });
  }

  function deleteView(viewId) {
    const next = savedViews.filter(v => v.id !== viewId);
    setSavedViews(next);
    persistViews(next);
  }

  // Bulk actions
  function exportCsv() {
    const rows = filtered.filter(s => selected.size === 0 || selected.has(s.id));
    const header = 'id,nom,adresse,code_postal,ville,usage,statut,risque_eur,surface_m2,anomalies,conso_kwh_an';
    const csv = [header, ...rows.map(s => `${s.id},"${s.nom}","${s.adresse}",${s.code_postal},${s.ville},${s.usage},${s.statut_conformite},${s.risque_eur},${s.surface_m2},${s.anomalies_count},${s.conso_kwh_an}`)].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'patrimoine.csv'; a.click();
    URL.revokeObjectURL(url);
    track('export_csv', { rows: rows.length });
  }

  function toggleFavorites() {
    const next = new Set(favorites);
    for (const id of selected) { next.has(id) ? next.delete(id) : next.add(id); }
    setFavorites(next);
    localStorage.setItem('promeos_fav_sites', JSON.stringify([...next]));
    setSelected(new Set());
    track('bulk_action', { action: 'toggle_favorite', count: selected.size });
  }

  const openSiteDrawer = useCallback((site, e) => {
    if (e) e.stopPropagation();
    setDrawerSite(site);
    track('row_click', { site_id: site.id });
  }, []);

  const hasFilters = search || filterUsage || filterStatut || filterAnomalies;
  const isEmptyPatrimoine = scopedSites.length === 0;

  return (
    <PageShell
      icon={Building2}
      title="Patrimoine"
      subtitle={isEmptyPatrimoine ? 'Aucun site — importez votre patrimoine pour commencer' : `${patrimoineStats.total} sites · ${(patrimoineStats.surfaceTotale / 1000).toFixed(0)}k m2 · ${patrimoineStats.conformes} conformes · ${(patrimoineStats.risqueTotal / 1000).toFixed(0)}k EUR de risque`}
      actions={
        <>
          <Button variant="secondary" size="sm" onClick={exportCsv}><Download size={14} className="mr-1" />Exporter</Button>
          <Button variant="secondary" size="sm" onClick={() => setShowWizard(true)}><Upload size={14} className="mr-1" />Importer patrimoine</Button>
          <Button onClick={() => setShowActionModal(true)}><Plus size={16} /> Creer action</Button>
        </>
      }
    >

      {/* Empty patrimoine: welcome state */}
      {isEmptyPatrimoine ? (
        <div className="flex flex-col items-center justify-center py-16">
          <div className="w-20 h-20 rounded-2xl bg-indigo-100 flex items-center justify-center mb-6">
            <Building2 size={36} className="text-indigo-600" />
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Bienvenue sur PROMEOS</h2>
          <p className="text-gray-500 text-center max-w-md mb-8">
            Importez votre patrimoine immobilier pour commencer le pilotage energetique.
            CSV, Excel ou donnees de demonstration.
          </p>
          <div className="flex items-center gap-3">
            <Button size="lg" onClick={() => setShowWizard(true)}>
              <Upload size={18} className="mr-2" /> Importer mon patrimoine
            </Button>
            <Button variant="secondary" size="lg" onClick={() => setShowWizard(true)}>
              <Zap size={18} className="mr-2" /> Charger la demo
            </Button>
          </div>
          <p className="text-xs text-gray-400 mt-4">10 sites demo — prets en 10 secondes</p>
        </div>
      ) : (
        <>
          {/* KPI overview cards — all clickable */}
          <div className="grid grid-cols-4 gap-4">
            <KpiCard
              icon={Building2}
              title="Sites actifs"
              value={patrimoineStats.total}
              sub={`${(patrimoineStats.surfaceTotale / 1000).toFixed(0)}k m2 totaux`}
              color="bg-blue-600"
              onClick={() => { setFilterStatut(''); setFilterAnomalies(false); setPage(1); }}
              className={!filterStatut && !filterAnomalies ? 'ring-2 ring-blue-400' : ''}
            />
            <KpiCard
              icon={ShieldCheck}
              title="Conformes"
              value={patrimoineStats.conformes}
              sub={`${patrimoineStats.total > 0 ? Math.round(patrimoineStats.conformes / patrimoineStats.total * 100) : 0}% du parc`}
              color="bg-green-600"
              onClick={() => { setFilterStatut(filterStatut === 'conforme' ? '' : 'conforme'); setFilterAnomalies(false); setPage(1); }}
              className={filterStatut === 'conforme' ? 'ring-2 ring-green-400' : ''}
            />
            <KpiCard
              icon={AlertTriangle}
              title="Non conformes"
              value={patrimoineStats.nonConformes + patrimoineStats.aRisque}
              sub={`${patrimoineStats.nonConformes} NC · ${patrimoineStats.aRisque} a risque`}
              color="bg-red-600"
              onClick={() => { setFilterStatut(filterStatut === 'non_conforme' ? '' : 'non_conforme'); setFilterAnomalies(false); setPage(1); }}
              className={filterStatut === 'non_conforme' ? 'ring-2 ring-red-400' : ''}
            />
            <KpiCard
              icon={BadgeEuro}
              title="Risque financier"
              value={`${(patrimoineStats.risqueTotal / 1000).toFixed(0)}k EUR`}
              sub={`${patrimoineStats.withAnomalies} sites avec anomalies`}
              color="bg-amber-600"
              onClick={() => { setFilterAnomalies(!filterAnomalies); setFilterStatut(''); setPage(1); }}
              className={filterAnomalies ? 'ring-2 ring-amber-400' : ''}
            />
          </div>

          {/* Filters + Saved Views */}
          <Card className="p-4">
            <div className="flex items-end gap-3">
              <div className="flex-1 relative">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text" placeholder="Rechercher par nom, ville, adresse, code postal..."
                  value={search}
                  onChange={(e) => { setSearch(e.target.value); setPage(1); track('filter_apply', { field: 'search' }); }}
                  className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <Select options={USAGE_OPTIONS} value={filterUsage} onChange={(e) => { setFilterUsage(e.target.value); setPage(1); track('filter_apply', { field: 'usage', value: e.target.value }); }} />
              <Select options={STATUT_OPTIONS} value={filterStatut} onChange={(e) => { setFilterStatut(e.target.value); setPage(1); track('filter_apply', { field: 'statut', value: e.target.value }); }} />
              {hasFilters && <Button variant="ghost" size="sm" onClick={resetFilters}><RotateCcw size={14} /> Reset</Button>}

              <div className="border-l border-gray-200 pl-3 flex items-center gap-1">
                <button onClick={saveCurrentView} className="p-2 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700" title="Sauvegarder cette vue"><BookmarkPlus size={16} /></button>
                {savedViews.length > 0 && (
                  <div className="relative">
                    <button onClick={() => setShowViewMenu(!showViewMenu)} className="p-2 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700 flex items-center gap-1 text-xs">
                      Vues <ChevronDown size={12} />
                    </button>
                    {showViewMenu && (
                      <div className="absolute right-0 top-full mt-1 w-48 bg-white border rounded-lg shadow-lg z-20 py-1">
                        {savedViews.map(v => (
                          <div key={v.id} className="flex items-center justify-between px-3 py-2 hover:bg-gray-50">
                            <button onClick={() => applyView(v)} className="text-sm text-gray-700 hover:text-blue-600 truncate flex-1 text-left">{v.name}</button>
                            <button onClick={() => deleteView(v.id)} className="text-gray-400 hover:text-red-500 text-xs ml-2">x</button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
                <button onClick={() => setCompact(!compact)} className="p-2 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700" title={compact ? 'Confortable' : 'Compact'}>
                  {compact ? <Rows4 size={16} /> : <Rows3 size={16} />}
                </button>
              </div>
            </div>
          </Card>

          {/* Bulk actions bar */}
          {selectedStats && (
            <div className="flex items-center gap-3 px-4 py-2.5 bg-white border border-gray-200 rounded-lg shadow-lg text-sm">
              <div className="w-7 h-7 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold">{selectedStats.count}</div>
              <span className="font-medium text-gray-700">site(s) selectionne(s)</span>
              {selectedStats.risque > 0 && (
                <span className="text-xs text-red-600 font-medium px-2 py-0.5 bg-red-50 rounded-full">{selectedStats.risque.toLocaleString()} EUR de risque</span>
              )}
              <div className="flex-1" />
              <Button size="sm" onClick={() => setShowActionModal(true)}><Plus size={14} /> Creer action</Button>
              <Button size="sm" variant="secondary" onClick={exportCsv}><Download size={14} /> Exporter</Button>
              <Button size="sm" variant="ghost" onClick={toggleFavorites}><Star size={14} /> Favori</Button>
              <button onClick={() => setSelected(new Set())} className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600" title="Deselectionner">
                <RotateCcw size={14} />
              </button>
            </div>
          )}

          {/* Table */}
          {total === 0 ? (
            <EmptyState
              icon={Search}
              title="Aucun site ne correspond"
              text={`Aucun resultat pour "${search || filterUsage || filterStatut}". Essayez d'autres criteres ou reinitialiser.`}
              ctaLabel="Reinitialiser les filtres"
              onCta={resetFilters}
            />
          ) : (
            <Card>
              <Table compact={compact} pinFirst>
                <Thead sticky>
                  <tr>
                    <ThCheckbox
                      checked={selected.size === pageData.length && pageData.length > 0}
                      onChange={toggleSelectAll}
                    />
                    <Th sortable sorted={sortCol === 'nom' ? sortDir : ''} onSort={() => handleSort('nom')} pin>Site</Th>
                    <Th>Usage</Th>
                    <Th>Conformite</Th>
                    <Th sortable sorted={sortCol === 'risque_eur' ? sortDir : ''} onSort={() => handleSort('risque_eur')} className="text-right">Risque</Th>
                    <Th sortable sorted={sortCol === 'surface_m2' ? sortDir : ''} onSort={() => handleSort('surface_m2')} className="text-right">Surface</Th>
                    {isExpert && <Th sortable sorted={sortCol === 'conso_kwh_an' ? sortDir : ''} onSort={() => handleSort('conso_kwh_an')} className="text-right">Conso</Th>}
                    <Th sortable sorted={sortCol === 'anomalies_count' ? sortDir : ''} onSort={() => handleSort('anomalies_count')} className="text-right">Anomalies</Th>
                    <Th className="w-10" />
                  </tr>
                </Thead>
                <Tbody>
                  {pageData.map((site) => {
                    const badge = STATUT_BADGE[site.statut_conformite] || STATUT_BADGE.a_evaluer;
                    const isFav = favorites.has(site.id);
                    const usageColor = USAGE_COLOR[site.usage] || 'bg-gray-100 text-gray-600';
                    return (
                      <Tr
                        key={site.id}
                        selected={selected.has(site.id)}
                        className="group"
                        onClick={() => openSiteDrawer(site)}
                      >
                        <TdCheckbox checked={selected.has(site.id)} onChange={() => toggleSelect(site.id)} />
                        <Td pin>
                          <div className="min-w-0">
                            <div className="flex items-center gap-1">
                              {isFav && <Star size={12} className="text-amber-400 fill-amber-400 shrink-0" />}
                              <span className="font-medium text-gray-900 truncate">{site.nom}</span>
                            </div>
                            <div className="text-xs text-gray-400 truncate mt-0.5">{site.adresse}, {site.code_postal} {site.ville}</div>
                          </div>
                        </Td>
                        <Td><span className={`capitalize text-xs px-2 py-0.5 rounded-full font-medium ${usageColor}`}>{site.usage}</span></Td>
                        <Td><Badge status={badge.status}>{badge.label}</Badge></Td>
                        <Td className="text-right">
                          {site.risque_eur > 0
                            ? <span className={`font-medium ${site.risque_eur > 10000 ? 'text-red-600' : 'text-amber-600'}`}>{site.risque_eur.toLocaleString()} EUR</span>
                            : <span className="text-gray-300">-</span>}
                        </Td>
                        <Td className="text-right text-gray-600">{site.surface_m2.toLocaleString()} m2</Td>
                        {isExpert && (
                          <Td className="text-right text-gray-600">
                            {site.conso_kwh_an > 0 ? `${(site.conso_kwh_an / 1000).toFixed(0)}k` : '-'}
                          </Td>
                        )}
                        <Td className="text-right">
                          {site.anomalies_count > 0
                            ? <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${site.anomalies_count > 4 ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>{site.anomalies_count}</span>
                            : <span className="text-gray-300">0</span>}
                        </Td>
                        <Td>
                          <ChevronRight size={16} className="text-gray-300 group-hover:text-gray-500 transition" />
                        </Td>
                      </Tr>
                    );
                  })}
                </Tbody>
              </Table>
              <div className="flex items-center justify-between px-4 py-2 border-t border-gray-100">
                <TrustBadge source="PROMEOS" period="donnees demo" confidence="medium" />
                <Pagination page={page} pageSize={pageSize} total={total} onChange={setPage} />
              </div>
            </Card>
          )}
        </>
      )}

      {/* Site Detail Drawer */}
      <Drawer open={!!drawerSite} onClose={() => setDrawerSite(null)} title={drawerSite?.nom || 'Site'} wide>
        {drawerSite && <SiteDrawerContent site={drawerSite} navigate={navigate} onCreateAction={() => { setDrawerSite(null); setShowActionModal(true); }} />}
      </Drawer>

      <CreateActionModal open={showActionModal} onClose={() => setShowActionModal(false)} onSave={() => {}} />
      {showWizard && <PatrimoineWizard onClose={() => setShowWizard(false)} />}

      {/* Save View Modal */}
      <Modal open={showSaveViewModal} onClose={() => setShowSaveViewModal(false)} title="Sauvegarder la vue">
        <div className="space-y-4">
          <Input label="Nom de la vue" value={newViewName} onChange={e => setNewViewName(e.target.value)} placeholder="Ex: Sites non conformes Paris" autoFocus />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={() => setShowSaveViewModal(false)}>Annuler</Button>
            <Button onClick={confirmSaveView} disabled={!newViewName.trim()}>Sauvegarder</Button>
          </div>
        </div>
      </Modal>
    </PageShell>
  );
}


/* ========================================
 * SiteDrawerContent — inline component
 * ======================================== */

function SiteDrawerContent({ site, navigate, onCreateAction }) {
  const badge = STATUT_BADGE[site.statut_conformite] || STATUT_BADGE.a_evaluer;
  const usageColor = USAGE_COLOR[site.usage] || 'bg-gray-100 text-gray-600';

  return (
    <div className="space-y-6">
      {/* Identity */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <span className={`capitalize text-xs px-2.5 py-1 rounded-full font-medium ${usageColor}`}>{site.usage}</span>
          <Badge status={badge.status}>{badge.label}</Badge>
        </div>
        <div className="flex items-start gap-2 text-sm text-gray-600">
          <MapPin size={14} className="text-gray-400 mt-0.5 shrink-0" />
          <span>{site.adresse}, {site.code_postal} {site.ville}</span>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-3">
        <StatTile icon={Ruler} label="Surface" value={`${site.surface_m2.toLocaleString()} m2`} />
        <StatTile icon={Gauge} label="Compteurs" value={site.nb_compteurs || 0} />
        <StatTile icon={TrendingUp} label="Conso annuelle" value={site.conso_kwh_an > 0 ? `${(site.conso_kwh_an / 1000).toFixed(0)}k kWh` : '-'} />
        <StatTile icon={BadgeEuro} label="Risque" value={site.risque_eur > 0 ? `${site.risque_eur.toLocaleString()} EUR` : '-'} color={site.risque_eur > 0 ? 'text-red-600' : ''} />
      </div>

      {/* Anomalies */}
      {site.anomalies_count > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
          <div className="flex items-center gap-2">
            <AlertTriangle size={16} className="text-amber-600" />
            <span className="text-sm font-medium text-amber-800">{site.anomalies_count} anomalie(s) detectee(s)</span>
          </div>
        </div>
      )}

      {/* Conformite summary */}
      <div className="bg-gray-50 rounded-lg p-4 space-y-2">
        <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider">Conformite</h4>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Statut</span>
          <Badge status={badge.status}>{badge.label}</Badge>
        </div>
        {site.derniere_evaluation && (
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Derniere evaluation</span>
            <span className="text-gray-900">{new Date(site.derniere_evaluation).toLocaleDateString('fr-FR')}</span>
          </div>
        )}
        {site.operat_status && (
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">OPERAT</span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
              site.operat_status === 'verified' ? 'bg-green-100 text-green-700' :
              site.operat_status === 'submitted' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'
            }`}>{site.operat_status === 'verified' ? 'Verifie' : site.operat_status === 'submitted' ? 'Soumis' : 'Non demarre'}</span>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="space-y-2">
        <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</h4>
        <button onClick={() => navigate(`/sites/${site.id}`)} className="w-full flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 transition text-left">
          <Eye size={16} className="text-blue-600 shrink-0" />
          <div className="flex-1"><p className="text-sm font-medium text-gray-800">Voir la fiche site</p><p className="text-xs text-gray-500">Details, compteurs, consommations</p></div>
          <ExternalLink size={14} className="text-gray-300" />
        </button>
        <button onClick={() => navigate(`/conformite`)} className="w-full flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 transition text-left">
          <ShieldCheck size={16} className="text-green-600 shrink-0" />
          <div className="flex-1"><p className="text-sm font-medium text-gray-800">Voir la conformite</p><p className="text-xs text-gray-500">Decret Tertiaire, BACS, obligations</p></div>
          <ExternalLink size={14} className="text-gray-300" />
        </button>
        <button onClick={onCreateAction} className="w-full flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 transition text-left">
          <Lightbulb size={16} className="text-amber-600 shrink-0" />
          <div className="flex-1"><p className="text-sm font-medium text-gray-800">Creer une action</p><p className="text-xs text-gray-500">Correction, amelioration, conformite</p></div>
          <ChevronRight size={14} className="text-gray-300" />
        </button>
      </div>

      {/* Quick info */}
      <div className="text-xs text-gray-400 pt-2 border-t">
        Site #{site.id} · {site.nb_compteurs || 0} compteur(s) · Derniere mise a jour: {site.derniere_evaluation ? new Date(site.derniere_evaluation).toLocaleDateString('fr-FR') : '-'}
      </div>
    </div>
  );
}

function StatTile({ icon: Icon, label, value, color = '' }) {
  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <div className="flex items-center gap-2 mb-1">
        <Icon size={14} className="text-gray-400" />
        <span className="text-xs text-gray-500">{label}</span>
      </div>
      <span className={`text-lg font-bold text-gray-900 ${color}`}>{value}</span>
    </div>
  );
}
