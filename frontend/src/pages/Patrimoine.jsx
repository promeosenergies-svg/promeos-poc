/**
 * PROMEOS - Patrimoine (/patrimoine) V3
 * Scope-filtered table + saved views + bulk actions + premium table + density toggle + trust badge.
 */
import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Building2, Search, RotateCcw, BookmarkPlus, Download, Star,
  Plus, ChevronDown, Rows3, Rows4, Upload,
} from 'lucide-react';
import { Card, Badge, Button, Select, Pagination, EmptyState, TrustBadge, PageShell } from '../ui';
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
  const [favorites, setFavorites] = useState(() => {
    try { return new Set(JSON.parse(localStorage.getItem('promeos_fav_sites') || '[]')); } catch { return new Set(); }
  });

  const filtered = useMemo(() => {
    let result = [...scopedSites];
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(s => s.nom.toLowerCase().includes(q) || s.ville.toLowerCase().includes(q) || s.adresse.toLowerCase().includes(q));
    }
    if (filterUsage) result = result.filter(s => s.usage === filterUsage);
    if (filterStatut) result = result.filter(s => s.statut_conformite === filterStatut);
    if (sortCol) {
      result.sort((a, b) => {
        const va = a[sortCol], vb = b[sortCol];
        if (typeof va === 'number') return sortDir === 'asc' ? va - vb : vb - va;
        return sortDir === 'asc' ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
      });
    }
    return result;
  }, [scopedSites, search, filterUsage, filterStatut, sortCol, sortDir]);

  const total = filtered.length;
  const pageData = filtered.slice((page - 1) * pageSize, page * pageSize);

  function handleSort(col) {
    if (sortCol === col) {
      setSortDir(d => d === 'asc' ? 'desc' : d === 'desc' ? '' : 'asc');
      if (sortDir === 'desc') setSortCol('');
    } else { setSortCol(col); setSortDir('asc'); }
    setPage(1);
    track('filter_apply', { action: 'sort', col });
  }

  function resetFilters() {
    setSearch(''); setFilterUsage(''); setFilterStatut(''); setPage(1);
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
  function saveCurrentView() {
    const name = prompt('Nom de la vue:');
    if (!name) return;
    const view = { id: Date.now(), name, filters: { search, filterUsage, filterStatut }, sort: { sortCol, sortDir }, pageSize };
    const next = [...savedViews, view];
    setSavedViews(next);
    persistViews(next);
    track('view_save', { name });
  }

  function applyView(view) {
    setSearch(view.filters.search || '');
    setFilterUsage(view.filters.filterUsage || '');
    setFilterStatut(view.filters.filterStatut || '');
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
    const header = 'id,nom,ville,usage,statut,risque_eur,surface_m2,anomalies';
    const csv = [header, ...rows.map(s => `${s.id},${s.nom},${s.ville},${s.usage},${s.statut_conformite},${s.risque_eur},${s.surface_m2},${s.anomalies_count}`)].join('\n');
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

  const hasFilters = search || filterUsage || filterStatut;

  return (
    <PageShell
      icon={Building2}
      title="Patrimoine"
      subtitle={`${scopedSites.length} sites dans le scope`}
      actions={
        <>
          <Button variant="secondary" size="sm" onClick={() => setShowWizard(true)}><Upload size={14} className="mr-1" />Importer patrimoine</Button>
          <Button onClick={() => setShowActionModal(true)}><Plus size={16} /> Creer action</Button>
        </>
      }
    >

      {/* Filters + Saved Views */}
      <Card className="p-4">
        <div className="flex items-end gap-3">
          <div className="flex-1 relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text" placeholder="Rechercher par nom, ville, adresse..."
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
      {selected.size > 0 && (
        <div className="flex items-center gap-3 px-4 py-2.5 bg-blue-50 border border-blue-200 rounded-lg text-sm">
          <span className="font-medium text-blue-700">{selected.size} site(s) selectionne(s)</span>
          <div className="flex-1" />
          <Button size="sm" onClick={() => setShowActionModal(true)}><Plus size={14} /> Creer action</Button>
          <Button size="sm" variant="secondary" onClick={exportCsv}><Download size={14} /> Exporter CSV</Button>
          <Button size="sm" variant="ghost" onClick={toggleFavorites}><Star size={14} /> Favori</Button>
          <Button size="sm" variant="ghost" onClick={() => setSelected(new Set())}>Deselectionner</Button>
        </div>
      )}

      {/* Table */}
      {total === 0 ? (
        <EmptyState icon={Building2} title="Aucun site trouve" text="Modifiez vos filtres ou importez de nouveaux sites." ctaLabel="Reinitialiser les filtres" onCta={resetFilters} />
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
                <Th sortable sorted={sortCol === 'ville' ? sortDir : ''} onSort={() => handleSort('ville')}>Ville</Th>
                <Th>Usage</Th>
                <Th>Conformite</Th>
                <Th sortable sorted={sortCol === 'risque_eur' ? sortDir : ''} onSort={() => handleSort('risque_eur')} className="text-right">Risque EUR</Th>
                <Th sortable sorted={sortCol === 'surface_m2' ? sortDir : ''} onSort={() => handleSort('surface_m2')} className="text-right">Surface</Th>
                {isExpert && <Th sortable sorted={sortCol === 'conso_kwh_an' ? sortDir : ''} onSort={() => handleSort('conso_kwh_an')} className="text-right">Conso kWh/an</Th>}
                <Th sortable sorted={sortCol === 'anomalies_count' ? sortDir : ''} onSort={() => handleSort('anomalies_count')} className="text-right">Anomalies</Th>
              </tr>
            </Thead>
            <Tbody>
              {pageData.map((site) => {
                const badge = STATUT_BADGE[site.statut_conformite] || STATUT_BADGE.a_evaluer;
                const isFav = favorites.has(site.id);
                return (
                  <Tr
                    key={site.id}
                    selected={selected.has(site.id)}
                    onClick={() => { track('row_click', { site_id: site.id }); navigate(`/sites/${site.id}`); }}
                  >
                    <TdCheckbox checked={selected.has(site.id)} onChange={() => toggleSelect(site.id)} />
                    <Td pin className="font-medium text-gray-900">
                      {isFav && <Star size={12} className="inline text-amber-400 mr-1 fill-amber-400" />}
                      {site.nom}
                    </Td>
                    <Td>{site.ville}</Td>
                    <Td><span className="capitalize text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">{site.usage}</span></Td>
                    <Td><Badge status={badge.status}>{badge.label}</Badge></Td>
                    <Td className="text-right font-medium text-red-600">{site.risque_eur > 0 ? `${site.risque_eur.toLocaleString()} EUR` : '-'}</Td>
                    <Td className="text-right">{site.surface_m2.toLocaleString()} m2</Td>
                    {isExpert && (
                      <Td className="text-right text-gray-600">
                        {site.conso_kwh_an > 0 ? site.conso_kwh_an.toLocaleString() : '-'}
                      </Td>
                    )}
                    <Td className="text-right">
                      {site.anomalies_count > 0 ? <span className={`font-medium ${site.anomalies_count > 4 ? 'text-red-600' : 'text-amber-600'}`}>{site.anomalies_count}</span> : <span className="text-gray-400">0</span>}
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

      <CreateActionModal open={showActionModal} onClose={() => setShowActionModal(false)} onSave={() => {}} />
      {showWizard && <PatrimoineWizard onClose={() => setShowWizard(false)} />}
    </PageShell>
  );
}
