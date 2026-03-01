/**
 * PROMEOS - Actions & Plan (/actions) V4 WOW
 * Table/Kanban toggle, group-by, search, colored status pills,
 * inline status change, context-aware empty states, impact bulk bar.
 */
import { useState, useMemo, useEffect, useCallback } from 'react';
import { useSearchParams, useParams } from 'react-router-dom';
import {
  Plus, Download, Printer, ListChecks, RefreshCw,
  AlertTriangle, BadgeEuro, ShieldCheck,
  Users, ArrowUpDown, UserPlus, FileText,
  Columns3, List, ChevronRight, ChevronDown, Search, CheckCircle, X,
} from 'lucide-react';
import { Card, CardBody, Badge, Button, Select, Pagination, EmptyState, Tabs, TrustBadge, PageShell } from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td, ThCheckbox, TdCheckbox } from '../ui';
import { useToast } from '../ui/ToastProvider';
import Modal from '../ui/Modal';
import CreateActionModal from '../components/CreateActionModal';
import ActionDetailDrawer from '../components/ActionDetailDrawer';
import ROISummaryBar from '../components/ROISummaryBar';
import { getActionsList, syncActions, patchAction, exportActionsCSV, downloadAuditPDF } from '../services/api';
import { useScope } from '../contexts/ScopeContext';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { track } from '../services/tracker';
import { ACTION_STATUS_LABELS, ACTION_TYPE_LABELS } from '../domain/compliance/complianceLabels.fr';

/* Backend → frontend field mappers */
const SOURCE_MAP = { compliance: 'conformite', consumption: 'conso', billing: 'facture', purchase: 'maintenance', insight: 'operat' };
const STATUS_TO_FE = { open: 'backlog', in_progress: 'in_progress', done: 'done', blocked: 'planned', false_positive: 'done' };
const STATUS_TO_BE = { backlog: 'open', in_progress: 'in_progress', done: 'done', planned: 'blocked' };
const PRIO_TO_FE = { 1: 'critical', 2: 'high', 3: 'medium', 4: 'low', 5: 'low' };

function mapBackendAction(a) {
  // V46: OPERAT actions (insight with source_id starting with "operat:")
  const isOperat = a.source_type === 'insight' && a.source_id?.startsWith('operat:');
  return {
    id: a.id,
    titre: a.title,
    type: isOperat ? 'operat' : (SOURCE_MAP[a.source_type] || a.source_type),
    site_id: a.site_id,
    site_nom: `Site ${a.site_id || '?'}`,
    impact_eur: a.estimated_gain_eur || 0,
    co2e_kg: a.co2e_savings_est_kg || 0,
    effort: a.severity || 'medium',
    statut: STATUS_TO_FE[a.status] || 'backlog',
    priorite: PRIO_TO_FE[a.priority] || 'medium',
    owner: a.owner,
    due_date: a.due_date,
    created_at: a.created_at || null,
    campaign_sites: a.campaign_sites || null,
    _backend: a,
  };
}

const TYPE_BADGE = {
  conformite: { status: 'crit', label: 'Conformité' },
  conso: { status: 'warn', label: 'Conso' },
  facture: { status: 'info', label: 'Facture' },
  maintenance: { status: 'neutral', label: 'Maintenance' },
  operat: { status: 'crit', label: 'OPERAT' },
};

const PRIORITY_BADGE = {
  critical: 'crit', high: 'warn', medium: 'info', low: 'neutral',
};

const PRIORITY_LABEL = {
  critical: 'P1', high: 'P2', medium: 'P3', low: 'P4',
};

const PRIORITY_RANK = { critical: 4, high: 3, medium: 2, low: 1 };

const STATUT_LABELS = ACTION_STATUS_LABELS;

const STATUT_PILL = {
  backlog:     'bg-gray-100 text-gray-700',
  planned:     'bg-blue-100 text-blue-700',
  in_progress: 'bg-amber-100 text-amber-700',
  done:        'bg-green-100 text-green-700',
};

const STATUT_TABS = [
  { id: '', label: 'Toutes' },
  ...Object.entries(ACTION_STATUS_LABELS).map(([id, label]) => ({ id, label })),
];

const TYPE_OPTIONS = [
  { value: '', label: 'Tous types' },
  ...Object.entries(ACTION_TYPE_LABELS).map(([value, label]) => ({ value, label })),
];

const BULK_STATUS_OPTIONS = Object.entries(ACTION_STATUS_LABELS).map(([value, label]) => ({ value, label }));

const GROUP_OPTIONS = [
  { value: 'none', label: 'Pas de groupement' },
  { value: 'site_nom', label: 'Par site' },
  { value: 'type', label: 'Par type' },
  { value: 'owner', label: 'Par responsable' },
  { value: 'priorite', label: 'Par priorité' },
  { value: 'statut', label: 'Par statut' },
];

const QUICK_VIEWS = [
  { id: 'overdue', label: 'En retard', icon: AlertTriangle, color: 'text-red-600' },
  { id: 'high_impact', label: 'Impact élevé', icon: BadgeEuro, color: 'text-amber-600' },
  { id: 'conformite_crit', label: 'Critique conformité', icon: ShieldCheck, color: 'text-blue-600' },
];

const KANBAN_COLUMNS = ['backlog', 'planned', 'in_progress', 'done'];
const KANBAN_DOT = { backlog: 'bg-gray-400', planned: 'bg-blue-500', in_progress: 'bg-amber-500', done: 'bg-green-500' };

function isOverdue(action) {
  if (!action.due_date || action.statut === 'done') return false;
  return new Date(action.due_date) < new Date();
}

/** Default sort: overdue first, then P1->P4, then earliest due_date */
function defaultSort(a, b) {
  const aOver = isOverdue(a) ? 0 : 1;
  const bOver = isOverdue(b) ? 0 : 1;
  if (aOver !== bOver) return aOver - bOver;
  const pa = PRIORITY_RANK[a.priorite] || 0;
  const pb = PRIORITY_RANK[b.priorite] || 0;
  if (pa !== pb) return pb - pa;
  return (a.due_date || '9999').localeCompare(b.due_date || '9999');
}

/* ── Kanban Board ────────────────────────────────────────────── */
function KanbanBoard({ actions, onStatusChange, onCardClick, selected, onToggleSelect: _onToggleSelect }) {
  const [dragId, setDragId] = useState(null);

  const columnActions = useMemo(() => {
    const map = {};
    KANBAN_COLUMNS.forEach(col => { map[col] = actions.filter(a => a.statut === col); });
    return map;
  }, [actions]);

  function handleDragStart(e, actionId) {
    setDragId(actionId);
    e.dataTransfer.effectAllowed = 'move';
  }

  function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }

  function handleDrop(e, newStatus) {
    e.preventDefault();
    if (dragId) {
      onStatusChange(dragId, newStatus);
      setDragId(null);
    }
  }

  return (
    <div className="grid grid-cols-4 gap-4">
      {KANBAN_COLUMNS.map(col => (
        <div
          key={col}
          onDragOver={handleDragOver}
          onDrop={(e) => handleDrop(e, col)}
          className="bg-gray-50 rounded-xl p-3 min-h-[400px]"
        >
          <div className="flex items-center gap-2 mb-3 px-1">
            <span className={`w-2.5 h-2.5 rounded-full ${KANBAN_DOT[col]}`} />
            <span className="text-sm font-semibold text-gray-700">{STATUT_LABELS[col]}</span>
            <span className="text-xs text-gray-400 ml-auto">{columnActions[col].length}</span>
          </div>
          <div className="space-y-2">
            {columnActions[col].map(a => {
              const typeBadge = TYPE_BADGE[a.type] || TYPE_BADGE.maintenance;
              return (
                <div
                  key={a.id}
                  draggable
                  onDragStart={(e) => handleDragStart(e, a.id)}
                  onClick={() => onCardClick(a)}
                  className={`bg-white rounded-lg border p-3 cursor-grab active:cursor-grabbing
                    hover:shadow-md transition-shadow ${dragId === a.id ? 'opacity-50' : ''}
                    ${selected.has(a.id) ? 'ring-2 ring-blue-400' : 'border-gray-200'}`}
                >
                  <p className="text-sm font-medium text-gray-900 line-clamp-2">{a.titre}</p>
                  <div className="flex items-center gap-1.5 mt-2">
                    <Badge status={PRIORITY_BADGE[a.priorite] || 'neutral'}>
                      {PRIORITY_LABEL[a.priorite]}
                    </Badge>
                    <Badge status={typeBadge.status}>{typeBadge.label}</Badge>
                  </div>
                  <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
                    <span>{a.impact_eur.toLocaleString()} EUR</span>
                    <span>{a.owner || 'Non assigné'}</span>
                  </div>
                  {isOverdue(a) && (
                    <div className="mt-1.5 text-xs font-medium text-red-600 flex items-center gap-1">
                      <AlertTriangle size={12} /> En retard
                    </div>
                  )}
                </div>
              );
            })}
            {columnActions[col].length === 0 && (
              <p className="text-xs text-gray-400 text-center py-8">Aucune action</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ── Grouped Table View ──────────────────────────────────────── */
function GroupedTableView({ actions, groupBy, onCardClick, selected, onToggleSelect: _onToggleSelect, onInlineStatus }) {
  const [collapsed, setCollapsed] = useState(new Set());

  const groups = useMemo(() => {
    const map = {};
    actions.forEach(a => {
      const key = groupBy === 'owner'
        ? (a[groupBy] || 'Non assigné')
        : (a[groupBy] || 'Non défini');
      if (!map[key]) map[key] = [];
      map[key].push(a);
    });
    return Object.entries(map).sort((a, b) => a[0].localeCompare(b[0]));
  }, [actions, groupBy]);

  function toggleGroup(key) {
    setCollapsed(prev => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  }

  return (
    <div className="space-y-4">
      {groups.map(([key, items]) => (
        <Card key={key}>
          <button
            onClick={() => toggleGroup(key)}
            className="w-full flex items-center gap-2 px-4 py-3 bg-gray-50 hover:bg-gray-100 transition text-left"
          >
            {collapsed.has(key) ? <ChevronRight size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
            <span className="text-sm font-semibold text-gray-800">{key}</span>
            <span className="text-xs text-gray-400">{items.length} action(s)</span>
            <span className="ml-auto text-xs font-medium text-gray-500">
              {items.reduce((s, a) => s + a.impact_eur, 0).toLocaleString()} EUR
            </span>
          </button>
          {!collapsed.has(key) && (
            <Table compact>
              <Thead>
                <tr>
                  <Th>Action</Th>
                  <Th>Type</Th>
                  <Th sortable={false}>Priorité</Th>
                  <Th className="text-right">Impact EUR</Th>
                  <Th>Échéance</Th>
                  <Th>Responsable</Th>
                  <Th>Statut</Th>
                </tr>
              </Thead>
              <Tbody>
                {items.map(a => {
                  const typeBadge = TYPE_BADGE[a.type] || TYPE_BADGE.maintenance;
                  const overdue = isOverdue(a);
                  return (
                    <Tr key={a.id} selected={selected.has(a.id)} onClick={() => onCardClick(a)}>
                      <Td className="font-medium text-gray-900 max-w-xs truncate">{a.titre}</Td>
                      <Td><Badge status={typeBadge.status}>{typeBadge.label}</Badge></Td>
                      <Td><Badge status={PRIORITY_BADGE[a.priorite] || 'neutral'}>{PRIORITY_LABEL[a.priorite]}</Badge></Td>
                      <Td className="text-right font-medium">{a.impact_eur.toLocaleString()} EUR</Td>
                      <Td className={`text-sm whitespace-nowrap ${overdue ? 'text-red-600 font-semibold' : ''}`}>
                        {a.due_date}
                        {overdue && <span className="ml-1 text-xs bg-red-50 text-red-600 px-1.5 py-0.5 rounded">En retard</span>}
                      </Td>
                      <Td className="text-sm">{a.owner || <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-400 rounded">Non assigné</span>}</Td>
                      <Td>
                        <select
                          value={a.statut}
                          onChange={(e) => { e.stopPropagation(); onInlineStatus(a.id, e.target.value); }}
                          onClick={(e) => e.stopPropagation()}
                          className={`text-xs font-medium px-2.5 py-0.5 rounded-full border-0 cursor-pointer
                            appearance-none hover:ring-2 hover:ring-blue-300 transition
                            ${STATUT_PILL[a.statut] || STATUT_PILL.backlog}`}
                        >
                          {BULK_STATUS_OPTIONS.map(opt => (
                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                          ))}
                        </select>
                      </Td>
                    </Tr>
                  );
                })}
              </Tbody>
            </Table>
          )}
        </Card>
      ))}
    </div>
  );
}

/* ── Main Component ──────────────────────────────────────────── */
export default function ActionsPage({ autoCreate = false }) {
  const { scopedSites } = useScope();
  const { isExpert } = useExpertMode();
  const { toast } = useToast();
  const [searchParams] = useSearchParams();
  const { actionId: urlActionId } = useParams();
  const [actions, setActions] = useState([]);
  const [_loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [filterStatut, setFilterStatut] = useState('');
  const [filterType, setFilterType] = useState(searchParams.get('source') === 'operat' ? 'operat' : '');
  const [quickView, setQuickView] = useState('');
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);
  const [createPrefill, setCreatePrefill] = useState(null);
  const [detailAction, setDetailAction] = useState(null);
  const [selected, setSelected] = useState(new Set());
  const [sortCol, setSortCol] = useState('');
  const [sortDir, setSortDir] = useState('');
  const [showAssign, setShowAssign] = useState(false);
  const [showBulkStatus, setShowBulkStatus] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [viewMode, setViewMode] = useState('table');
  const [groupBy, setGroupBy] = useState('none');
  const [searchQuery, setSearchQuery] = useState('');
  const pageSize = 15;

  const ownerOptions = useMemo(() => {
    const unique = [...new Set(actions.map(a => a.owner).filter(Boolean))];
    unique.sort((a, b) => a.localeCompare(b));
    return unique;
  }, [actions]);

  const fetchActions = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getActionsList();
      setActions(data.map(mapBackendAction));
    } catch {
      /* fallback: keep current state */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchActions(); }, [fetchActions]);

  // Auto-open detail drawer when navigating to /actions/:actionId
  useEffect(() => {
    if (urlActionId && actions.length > 0 && !detailAction) {
      const found = actions.find(a => String(a.id) === urlActionId);
      if (found) setDetailAction(found);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlActionId, actions]);

  // Auto-open create modal when navigating to /actions/new
  useEffect(() => {
    if (autoCreate && !showCreate) {
      const prefill = {};
      const type = searchParams.get('type');
      const siteId = searchParams.get('site_id');
      const titre = searchParams.get('titre');
      if (type) prefill.type = type;
      if (siteId) prefill.site_id = parseInt(siteId);
      if (titre) prefill.titre = decodeURIComponent(titre);
      setCreatePrefill(prefill);
      setShowCreate(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoCreate]);

  async function handleSync() {
    setSyncing(true);
    try {
      await syncActions();
      await fetchActions();
      track('action_hub_sync', {});
    } catch { /* noop */ }
    setSyncing(false);
  }

  async function handleDownloadPDF() {
    setPdfLoading(true);
    try {
      const resp = await downloadAuditPDF();
      const blob = new Blob([resp.data], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const el = document.createElement('a');
      el.href = url;
      el.download = 'audit_promeos.pdf';
      el.click();
      URL.revokeObjectURL(url);
      track('download_audit_pdf', {});
    } catch { toast('Erreur lors du téléchargement du PDF', 'error'); }
    setPdfLoading(false);
  }

  const filtered = useMemo(() => {
    let result = [...actions];

    // Quick views
    if (quickView === 'overdue') result = result.filter(isOverdue);
    else if (quickView === 'high_impact') result = result.filter(a => a.impact_eur >= 10000);
    else if (quickView === 'conformite_crit') result = result.filter(a => a.type === 'conformite' && (a.priorite === 'critical' || a.priorite === 'high'));

    if (filterStatut) result = result.filter(a => a.statut === filterStatut);
    if (filterType) result = result.filter(a => a.type === filterType);

    // Search
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(a =>
        a.titre.toLowerCase().includes(q) ||
        a.site_nom.toLowerCase().includes(q) ||
        (a.owner || '').toLowerCase().includes(q)
      );
    }

    // Sort
    if (sortCol) {
      result.sort((a, b) => {
        let va = a[sortCol], vb = b[sortCol];
        if (sortCol === 'priorite') {
          va = PRIORITY_RANK[va] || 0; vb = PRIORITY_RANK[vb] || 0;
        }
        if (typeof va === 'number') return sortDir === 'asc' ? va - vb : vb - va;
        return sortDir === 'asc' ? String(va || '').localeCompare(String(vb || '')) : String(vb || '').localeCompare(String(va || ''));
      });
    } else {
      result.sort(defaultSort);
    }
    return result;
  }, [actions, filterStatut, filterType, quickView, sortCol, sortDir, searchQuery]);

  const total = filtered.length;
  const pageData = filtered.slice((page - 1) * pageSize, page * pageSize);

  const stats = useMemo(() => ({
    total: actions.length,
    backlog: actions.filter(a => a.statut === 'backlog').length,
    planned: actions.filter(a => a.statut === 'planned').length,
    in_progress: actions.filter(a => a.statut === 'in_progress').length,
    done: actions.filter(a => a.statut === 'done').length,
    total_impact: actions.reduce((s, a) => s + a.impact_eur, 0),
    total_co2e_kg: actions.reduce((s, a) => s + (a.co2e_kg || 0), 0),
    overdue: actions.filter(isOverdue).length,
  }), [actions]);

  function handleSort(col) {
    if (sortCol === col) {
      setSortDir(d => d === 'asc' ? 'desc' : d === 'desc' ? '' : 'asc');
      if (sortDir === 'desc') setSortCol('');
    } else { setSortCol(col); setSortDir('asc'); }
    setPage(1);
  }

  function handleSaveAction(action) {
    setActions(prev => [action, ...prev]);
  }

  function toggleSelect(id) {
    setSelected(prev => { const next = new Set(prev); next.has(id) ? next.delete(id) : next.add(id); return next; });
  }

  function toggleSelectAll() {
    if (selected.size === pageData.length) setSelected(new Set());
    else setSelected(new Set(pageData.map(a => a.id)));
  }

  async function handleInlineStatusChange(actionId, newStatus) {
    const beStatus = STATUS_TO_BE[newStatus] || newStatus;
    try {
      await patchAction(actionId, { status: beStatus });
    } catch { /* silent fallback */ }
    setActions(prev => prev.map(a => a.id === actionId ? { ...a, statut: newStatus } : a));
    track('inline_status_change', { action_id: actionId, status: newStatus });
  }

  async function bulkChangeStatus(newStatus) {
    const beStatus = STATUS_TO_BE[newStatus] || newStatus;
    const ids = [...selected];
    await Promise.all(ids.map(id => patchAction(id, { status: beStatus }).catch(() => toast('Erreur lors du changement de statut', 'error'))));
    setActions(prev => prev.map(a => selected.has(a.id) ? { ...a, statut: newStatus } : a));
    track('bulk_status_change', { count: selected.size, status: newStatus });
    setSelected(new Set());
    setShowBulkStatus(false);
  }

  async function bulkAssign(owner) {
    const ids = [...selected];
    await Promise.all(ids.map(id => patchAction(id, { owner }).catch(() => toast('Erreur lors de l\'assignation', 'error'))));
    setActions(prev => prev.map(a => selected.has(a.id) ? { ...a, owner } : a));
    track('bulk_assign', { count: selected.size, owner });
    setSelected(new Set());
    setShowAssign(false);
  }

  function handleBulkCreate() {
    const rows = actions.filter(a => selected.has(a.id));
    const types = [...new Set(rows.map(r => r.type))];
    const sites = [...new Set(rows.map(r => r.site_nom))];
    setCreatePrefill({
      titre: rows.length === 1 ? rows[0].titre : `Action groupée (${rows.length} items)`,
      type: types.length === 1 ? types[0] : 'conformite',
      site: sites.length === 1 ? sites[0] : sites.slice(0, 3).join(', '),
      description: rows.map(r => `- ${r.titre}`).join('\n'),
    });
    setShowCreate(true);
  }

  async function exportPlan30j() {
    try {
      const resp = await exportActionsCSV();
      const blob = new Blob([resp.data], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const el = document.createElement('a'); el.href = url; el.download = 'actions_promeos.csv'; el.click();
      URL.revokeObjectURL(url);
      track('export_csv', { type: 'plan_backend' });
    } catch {
      /* fallback client-side */
      const next30 = actions
        .filter(a => a.statut !== 'done' && a.due_date)
        .filter(a => { const d = new Date(a.due_date); const now = new Date(); const diff = (d - now) / 86400000; return diff >= 0 && diff <= 30; })
        .sort((a, b) => a.due_date.localeCompare(b.due_date));
      const header = 'titre,type,site,priorite,echeance,impact_eur,owner,statut';
      const csv = [header, ...next30.map(a => `"${a.titre}",${a.type},${a.site_nom},${a.priorite},${a.due_date},${a.impact_eur},${a.owner || 'Non assigné'},${a.statut}`)].join('\n');
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const el = document.createElement('a'); el.href = url; el.download = 'plan-30-jours.csv'; el.click();
      URL.revokeObjectURL(url);
      track('export_csv', { type: 'plan_30j', rows: next30.length });
    }
  }

  function exportSelected() {
    const rows = actions.filter(a => selected.has(a.id));
    const header = 'titre,type,site,priorite,echeance,impact_eur,owner,statut';
    const csv = [header, ...rows.map(a => `"${a.titre}",${a.type},${a.site_nom},${a.priorite},${a.due_date},${a.impact_eur},${a.owner || 'Non assigné'},${a.statut}`)].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const el = document.createElement('a'); el.href = url; el.download = 'actions-export.csv'; el.click();
    URL.revokeObjectURL(url);
    track('export_csv', { type: 'selected', rows: rows.length });
  }

  function resetAllFilters() {
    setFilterStatut('');
    setFilterType('');
    setQuickView('');
    setSearchQuery('');
    setPage(1);
  }

  function renderEmptyState() {
    if (quickView === 'overdue') {
      return <EmptyState icon={CheckCircle} title="Aucune action en retard" text="Toutes vos actions sont dans les temps. Continuez ainsi !" />;
    }
    if (quickView === 'high_impact') {
      return <EmptyState icon={BadgeEuro} title="Aucune action à fort impact" text="Aucune action avec un impact supérieur à 10 000 EUR n'a été détectée." />;
    }
    if (quickView === 'conformite_crit') {
      return <EmptyState icon={ShieldCheck} title="Pas d'action critique conformité" text="Aucune action de conformité critique ou haute priorité." />;
    }
    if (filterStatut || filterType || searchQuery.trim()) {
      return <EmptyState icon={ListChecks} title="Aucune action pour ce filtre" text="Essayez de modifier vos filtres ou de réinitialiser la vue." ctaLabel="Réinitialiser" onCta={resetAllFilters} />;
    }
    return <EmptyState icon={ListChecks} title="Aucune action" text="Synchronisez vos données ou créez votre première action pour commencer." ctaLabel="Créer action" onCta={() => setShowCreate(true)} />;
  }

  return (
    <PageShell
      icon={ListChecks}
      title="Plan d'actions"
      subtitle={`${stats.total} actions · ${stats.total_impact.toLocaleString()} EUR d'impact total${stats.total_co2e_kg > 0 ? ` · ${Math.round(stats.total_co2e_kg).toLocaleString()} kgCO₂e` : ''}${stats.overdue > 0 ? ` · ${stats.overdue} en retard` : ''}`}
      actions={
        <>
          <Button variant="secondary" size="sm" onClick={handleSync} disabled={syncing}>
            <RefreshCw size={16} className={syncing ? 'animate-spin' : ''} /> {syncing ? 'Sync...' : 'Synchroniser'}
          </Button>
          {isExpert && (
            <Button variant="secondary" size="sm" onClick={handleDownloadPDF} disabled={pdfLoading} title="Rapport d'audit PDF complet">
              <FileText size={16} className={pdfLoading ? 'animate-pulse' : ''} /> {pdfLoading ? 'PDF...' : 'Rapport PDF'}
            </Button>
          )}
          <Button variant="secondary" size="sm" onClick={exportPlan30j} title="Exporter CSV">
            <Printer size={16} /> Exporter CSV
          </Button>
          <Button onClick={() => { setCreatePrefill(null); setShowCreate(true); }}><Plus size={16} /> Créer action</Button>
        </>
      }
    >

      {/* ROI Summary (V5.0) */}
      <ROISummaryBar />

      {/* Quick views with counts */}
      <div className="flex items-center gap-2">
        {QUICK_VIEWS.map(qv => {
          const Icon = qv.icon;
          const isActive = quickView === qv.id;
          const count = qv.id === 'overdue' ? stats.overdue
            : qv.id === 'high_impact' ? actions.filter(a => a.impact_eur >= 10000).length
            : actions.filter(a => a.type === 'conformite' && (a.priorite === 'critical' || a.priorite === 'high')).length;
          return (
            <button
              key={qv.id}
              onClick={() => { setQuickView(isActive ? '' : qv.id); setPage(1); track('quick_view', { view: qv.id }); }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition border
                ${isActive ? 'bg-blue-50 border-blue-300 text-blue-700' : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'}`}
            >
              <Icon size={14} className={isActive ? 'text-blue-600' : qv.color} />
              {qv.label}
              {count > 0 && (
                <span className={`ml-0.5 px-1.5 py-0 rounded-full text-[10px] font-bold ${isActive ? 'bg-blue-200 text-blue-800' : 'bg-gray-200 text-gray-600'}`}>
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Clickable stats cards */}
      <div className="grid grid-cols-5 gap-3">
        {[
          { label: 'À planifier', value: stats.backlog, color: 'text-gray-700', bg: 'bg-gray-50', statut: 'backlog', ringColor: 'ring-gray-400' },
          { label: 'Planifiée', value: stats.planned, color: 'text-blue-700', bg: 'bg-blue-50', statut: 'planned', ringColor: 'ring-blue-400' },
          { label: 'En cours', value: stats.in_progress, color: 'text-amber-700', bg: 'bg-amber-50', statut: 'in_progress', ringColor: 'ring-amber-400' },
          { label: 'Terminée', value: stats.done, color: 'text-green-700', bg: 'bg-green-50', statut: 'done', ringColor: 'ring-green-400' },
          { label: 'En retard', value: stats.overdue, color: 'text-red-700', bg: 'bg-red-50', statut: '_overdue', ringColor: 'ring-red-400' },
        ].map(c => {
          const isCardActive = c.statut === '_overdue' ? quickView === 'overdue' : filterStatut === c.statut;
          return (
            <Card
              key={c.label}
              className={`cursor-pointer transition-all hover:shadow-md ${isCardActive ? `ring-2 ${c.ringColor}` : ''} ${c.statut !== '_overdue' && c.value === 0 ? '' : ''}`}
              onClick={() => {
                if (c.statut === '_overdue') {
                  setQuickView(quickView === 'overdue' ? '' : 'overdue');
                  setFilterStatut('');
                } else {
                  setFilterStatut(filterStatut === c.statut ? '' : c.statut);
                  setQuickView('');
                }
                setPage(1);
              }}
            >
              <CardBody className={c.bg}>
                <p className="text-xs text-gray-500">{c.label}</p>
                <p className={`text-2xl font-bold ${c.color}`}>{c.value}</p>
              </CardBody>
            </Card>
          );
        })}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <Tabs tabs={STATUT_TABS} active={filterStatut} onChange={(id) => { setFilterStatut(id); setPage(1); }} />
        <div className="ml-auto">
          <Select options={TYPE_OPTIONS} value={filterType} onChange={(e) => { setFilterType(e.target.value); setPage(1); }} />
        </div>
      </div>

      {/* Toolbar: search + group-by + view toggle */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Rechercher une action..."
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
            className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm placeholder:text-gray-400
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Select
            options={GROUP_OPTIONS}
            value={groupBy}
            onChange={(e) => { setGroupBy(e.target.value); setPage(1); }}
          />
          <div className="flex items-center bg-gray-100 rounded-lg p-0.5">
            <button
              onClick={() => setViewMode('table')}
              className={`p-1.5 rounded-md transition ${viewMode === 'table' ? 'bg-white shadow-sm text-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
              title="Vue tableau"
            >
              <List size={16} />
            </button>
            <button
              onClick={() => setViewMode('kanban')}
              className={`p-1.5 rounded-md transition ${viewMode === 'kanban' ? 'bg-white shadow-sm text-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
              title="Vue Kanban"
            >
              <Columns3 size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Filtered impact summary */}
      {(filterStatut || filterType || quickView || searchQuery.trim()) && total > 0 && (
        <div className="flex items-center gap-3 px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm">
          <span className="text-gray-500">Résultat filtré :</span>
          <span className="font-semibold text-gray-900">{total} action(s)</span>
          <span className="text-gray-400">&middot;</span>
          <span className="font-bold text-red-600">{filtered.reduce((s, a) => s + a.impact_eur, 0).toLocaleString()} EUR</span>
          <span className="text-gray-400 text-xs">d'impact</span>
          <button onClick={resetAllFilters} className="ml-auto text-xs text-blue-600 hover:text-blue-800 font-medium">
            Réinitialiser
          </button>
        </div>
      )}

      {/* Content: table / kanban / grouped */}
      {total === 0 ? renderEmptyState() : viewMode === 'kanban' ? (
        <KanbanBoard
          actions={filtered}
          onStatusChange={handleInlineStatusChange}
          onCardClick={(a) => { setDetailAction(a); track('row_click', { action_id: a.id }); }}
          selected={selected}
          onToggleSelect={toggleSelect}
        />
      ) : groupBy !== 'none' ? (
        <GroupedTableView
          actions={filtered}
          groupBy={groupBy}
          onCardClick={(a) => { setDetailAction(a); track('row_click', { action_id: a.id }); }}
          selected={selected}
          onToggleSelect={toggleSelect}
          onInlineStatus={handleInlineStatusChange}
        />
      ) : (
        <Card>
          <Table compact={false}>
            <Thead sticky>
              <tr>
                <ThCheckbox
                  checked={selected.size === pageData.length && pageData.length > 0}
                  onChange={toggleSelectAll}
                />
                <Th sortable sorted={sortCol === 'titre' ? sortDir : ''} onSort={() => handleSort('titre')}>Action</Th>
                <Th>Type</Th>
                <Th>Site</Th>
                <Th sortable sorted={sortCol === 'priorite' ? sortDir : ''} onSort={() => handleSort('priorite')}>Priorité</Th>
                <Th sortable sorted={sortCol === 'impact_eur' ? sortDir : ''} onSort={() => handleSort('impact_eur')} className="text-right">Impact EUR</Th>
                <Th className="text-right">CO₂e</Th>
                <Th sortable sorted={sortCol === 'due_date' ? sortDir : ''} onSort={() => handleSort('due_date')}>Échéance</Th>
                <Th>Responsable</Th>
                <Th>Statut</Th>
              </tr>
            </Thead>
            <Tbody>
              {pageData.map((a) => {
                const typeBadge = TYPE_BADGE[a.type] || TYPE_BADGE.maintenance;
                const overdue = isOverdue(a);
                return (
                  <Tr
                    key={a.id}
                    selected={selected.has(a.id)}
                    onClick={() => { setDetailAction(a); track('row_click', { action_id: a.id }); }}
                  >
                    <TdCheckbox checked={selected.has(a.id)} onChange={() => toggleSelect(a.id)} />
                    <Td className="font-medium text-gray-900 max-w-xs truncate">{a.titre}</Td>
                    <Td><Badge status={typeBadge.status}>{typeBadge.label}</Badge></Td>
                    <Td className="text-sm">{a.site_nom}</Td>
                    <Td>
                      <Badge status={PRIORITY_BADGE[a.priorite] || 'neutral'}>{PRIORITY_LABEL[a.priorite] || a.priorite}</Badge>
                    </Td>
                    <Td className="text-right font-medium">{a.impact_eur.toLocaleString()} EUR</Td>
                    <Td className="text-right text-emerald-600 text-sm">{a.co2e_kg > 0 ? `${Math.round(a.co2e_kg).toLocaleString()} kg` : '—'}</Td>
                    <Td className={`text-sm whitespace-nowrap ${overdue ? 'text-red-600 font-semibold' : ''}`}>
                      {a.due_date}
                      {overdue && <span className="ml-1 text-xs bg-red-50 text-red-600 px-1.5 py-0.5 rounded">En retard</span>}
                    </Td>
                    <Td className="text-sm">
                      {a.owner
                        ? a.owner
                        : <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-400 rounded">Non assigné</span>
                      }
                    </Td>
                    <Td>
                      <select
                        value={a.statut}
                        onChange={(e) => { e.stopPropagation(); handleInlineStatusChange(a.id, e.target.value); }}
                        onClick={(e) => e.stopPropagation()}
                        className={`text-xs font-medium px-2.5 py-0.5 rounded-full border-0 cursor-pointer
                          appearance-none hover:ring-2 hover:ring-blue-300 transition
                          ${STATUT_PILL[a.statut] || STATUT_PILL.backlog}`}
                      >
                        {BULK_STATUS_OPTIONS.map(opt => (
                          <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                      </select>
                    </Td>
                  </Tr>
                );
              })}
            </Tbody>
          </Table>
          <div className="flex items-center justify-between px-4 py-2 border-t border-gray-100">
            <TrustBadge
              source="PROMEOS"
              period={`périmètre : ${scopedSites.length} sites`}
              confidence="medium"
            />
            <Pagination page={page} pageSize={pageSize} total={total} onChange={setPage} />
          </div>
        </Card>
      )}

      {/* Sticky bulk bar */}
      {selected.size > 0 && (
        <div className="sticky bottom-4 z-30 flex items-center gap-4 px-5 py-3 bg-white border border-gray-200 rounded-xl shadow-xl text-sm">
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center justify-center w-7 h-7 bg-blue-600 text-white rounded-full text-xs font-bold">
              {selected.size}
            </span>
            <div>
              <span className="font-semibold text-gray-900">sélectionnée(s)</span>
              <span className="ml-2 text-gray-500">&middot;</span>
              <span className="ml-2 font-bold text-red-600">
                {actions.filter(a => selected.has(a.id)).reduce((s, a) => s + a.impact_eur, 0).toLocaleString()} EUR
              </span>
              <span className="ml-1 text-xs text-gray-400">d'impact total</span>
            </div>
          </div>
          <div className="flex-1" />
          <Button size="sm" variant="secondary" onClick={() => setShowAssign(true)}>
            <UserPlus size={14} /> Assigner
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setShowBulkStatus(true)}>
            <ArrowUpDown size={14} /> Statut
          </Button>
          <Button size="sm" variant="secondary" onClick={handleBulkCreate}>
            <Plus size={14} /> Créer action
          </Button>
          <Button size="sm" variant="secondary" onClick={exportSelected}>
            <Download size={14} /> Exporter
          </Button>
          <button
            onClick={() => setSelected(new Set())}
            className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition"
            title="Désélectionner"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* Create Modal */}
      <CreateActionModal
        open={showCreate}
        onClose={() => { setShowCreate(false); setCreatePrefill(null); }}
        onSave={handleSaveAction}
        prefill={createPrefill}
      />

      {/* Assign Modal */}
      <Modal open={showAssign} onClose={() => setShowAssign(false)} title="Assigner un responsable">
        <div className="space-y-2">
          <p className="text-sm text-gray-600">{selected.size} action(s) sélectionnée(s)</p>
          {ownerOptions.map(owner => (
            <button
              key={owner}
              onClick={() => bulkAssign(owner)}
              className="w-full text-left px-4 py-2.5 rounded-lg hover:bg-blue-50 text-sm font-medium text-gray-700 transition"
            >
              <Users size={14} className="inline mr-2 text-gray-400" />
              {owner}
            </button>
          ))}
          {ownerOptions.length === 0 && (
            <p className="text-sm text-gray-400 py-2">Aucun responsable connu. Les responsables apparaissent automatiquement.</p>
          )}
        </div>
      </Modal>

      {/* Bulk Status Modal */}
      <Modal open={showBulkStatus} onClose={() => setShowBulkStatus(false)} title="Changer le statut">
        <div className="space-y-2">
          <p className="text-sm text-gray-600">{selected.size} action(s) sélectionnée(s)</p>
          {BULK_STATUS_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => bulkChangeStatus(opt.value)}
              className="w-full text-left px-4 py-2.5 rounded-lg hover:bg-blue-50 text-sm font-medium text-gray-700 transition"
            >
              <span className={`inline-block w-2.5 h-2.5 rounded-full mr-2 ${KANBAN_DOT[opt.value]}`} />
              {opt.label}
            </button>
          ))}
        </div>
      </Modal>

      {/* Detail Drawer (V5.0) */}
      <ActionDetailDrawer
        action={detailAction}
        open={!!detailAction}
        onClose={() => setDetailAction(null)}
        onUpdate={(actionId, changes) => {
          setActions(prev => prev.map(a =>
            a.id === actionId ? { ...a, ...changes } : a
          ));
        }}
      />
    </PageShell>
  );
}
