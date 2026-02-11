/**
 * PROMEOS - Actions & Plan (/actions) V3
 * Quick views + SLA + bulk actions + tags + priority P1-P3 + premium table
 */
import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus, Download, Printer, Clock, ListChecks,
  MessageSquare, Paperclip, AlertTriangle, BadgeEuro, ShieldCheck,
  Tag, Users, ArrowUpDown,
} from 'lucide-react';
import { Card, CardBody, Badge, Button, Select, Pagination, EmptyState, Tabs, TrustBadge } from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td, ThCheckbox, TdCheckbox } from '../ui';
import Modal from '../ui/Modal';
import CreateActionModal from '../components/CreateActionModal';
import { mockActions } from '../mocks/actions';
import { track } from '../services/tracker';

const TYPE_BADGE = {
  conformite: { status: 'crit', label: 'Conformite' },
  conso: { status: 'warn', label: 'Conso' },
  facture: { status: 'info', label: 'Facture' },
  maintenance: { status: 'neutral', label: 'Maintenance' },
};

const PRIORITY_BADGE = {
  critical: 'crit', high: 'warn', medium: 'info', low: 'neutral',
};

const PRIORITY_LABEL = {
  critical: 'P1', high: 'P2', medium: 'P3', low: 'P4',
};

const STATUT_LABELS = {
  backlog: 'Backlog', planned: 'Planifie', in_progress: 'En cours', done: 'Termine',
};

const STATUT_TABS = [
  { id: '', label: 'Toutes' },
  { id: 'backlog', label: 'Backlog' },
  { id: 'planned', label: 'Planifie' },
  { id: 'in_progress', label: 'En cours' },
  { id: 'done', label: 'Termine' },
];

const TYPE_OPTIONS = [
  { value: '', label: 'Tous types' },
  { value: 'conformite', label: 'Conformite' },
  { value: 'conso', label: 'Conso' },
  { value: 'facture', label: 'Facture' },
  { value: 'maintenance', label: 'Maintenance' },
];

const QUICK_VIEWS = [
  { id: 'overdue', label: 'En retard', icon: AlertTriangle, color: 'text-red-600' },
  { id: 'high_impact', label: 'Impact eleve', icon: BadgeEuro, color: 'text-amber-600' },
  { id: 'conformite_crit', label: 'Critique conformite', icon: ShieldCheck, color: 'text-blue-600' },
];

function isOverdue(action) {
  if (!action.due_date || action.statut === 'done') return false;
  return new Date(action.due_date) < new Date();
}

export default function ActionsPage() {
  const navigate = useNavigate();
  const [actions, setActions] = useState(mockActions);
  const [filterStatut, setFilterStatut] = useState('');
  const [filterType, setFilterType] = useState('');
  const [quickView, setQuickView] = useState('');
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);
  const [detailAction, setDetailAction] = useState(null);
  const [selected, setSelected] = useState(new Set());
  const [sortCol, setSortCol] = useState('');
  const [sortDir, setSortDir] = useState('');
  const pageSize = 15;

  const filtered = useMemo(() => {
    let result = [...actions];

    // Quick views
    if (quickView === 'overdue') result = result.filter(isOverdue);
    else if (quickView === 'high_impact') result = result.filter(a => a.impact_eur >= 10000);
    else if (quickView === 'conformite_crit') result = result.filter(a => a.type === 'conformite' && (a.priorite === 'critical' || a.priorite === 'high'));

    if (filterStatut) result = result.filter(a => a.statut === filterStatut);
    if (filterType) result = result.filter(a => a.type === filterType);

    // Sort
    if (sortCol) {
      result.sort((a, b) => {
        let va = a[sortCol], vb = b[sortCol];
        if (sortCol === 'priorite') {
          const rank = { critical: 4, high: 3, medium: 2, low: 1 };
          va = rank[va] || 0; vb = rank[vb] || 0;
        }
        if (typeof va === 'number') return sortDir === 'asc' ? va - vb : vb - va;
        return sortDir === 'asc' ? String(va || '').localeCompare(String(vb || '')) : String(vb || '').localeCompare(String(va || ''));
      });
    } else {
      result.sort((a, b) => {
        const prio = { critical: 4, high: 3, medium: 2, low: 1 };
        return (prio[b.priorite] || 0) - (prio[a.priorite] || 0);
      });
    }
    return result;
  }, [actions, filterStatut, filterType, quickView, sortCol, sortDir]);

  const total = filtered.length;
  const pageData = filtered.slice((page - 1) * pageSize, page * pageSize);

  const stats = useMemo(() => ({
    total: actions.length,
    backlog: actions.filter(a => a.statut === 'backlog').length,
    planned: actions.filter(a => a.statut === 'planned').length,
    in_progress: actions.filter(a => a.statut === 'in_progress').length,
    done: actions.filter(a => a.statut === 'done').length,
    total_impact: actions.reduce((s, a) => s + a.impact_eur, 0),
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

  function bulkChangeStatus(newStatus) {
    setActions(prev => prev.map(a => selected.has(a.id) ? { ...a, statut: newStatus } : a));
    track('bulk_status_change', { count: selected.size, status: newStatus });
    setSelected(new Set());
  }

  function exportPlan30j() {
    const next30 = actions
      .filter(a => a.statut !== 'done' && a.due_date)
      .filter(a => { const d = new Date(a.due_date); const now = new Date(); const diff = (d - now) / 86400000; return diff >= 0 && diff <= 30; })
      .sort((a, b) => a.due_date.localeCompare(b.due_date));

    const header = 'titre,type,site,priorite,echeance,impact_eur,owner,statut';
    const csv = [header, ...next30.map(a => `"${a.titre}",${a.type},${a.site_nom},${a.priorite},${a.due_date},${a.impact_eur},${a.owner},${a.statut}`)].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const el = document.createElement('a'); el.href = url; el.download = 'plan-30-jours.csv'; el.click();
    URL.revokeObjectURL(url);
    track('export_csv', { type: 'plan_30j', rows: next30.length });
  }

  function exportSelected() {
    const rows = actions.filter(a => selected.has(a.id));
    const header = 'titre,type,site,priorite,echeance,impact_eur,owner,statut';
    const csv = [header, ...rows.map(a => `"${a.titre}",${a.type},${a.site_nom},${a.priorite},${a.due_date},${a.impact_eur},${a.owner},${a.statut}`)].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const el = document.createElement('a'); el.href = url; el.download = 'actions-export.csv'; el.click();
    URL.revokeObjectURL(url);
    track('export_csv', { type: 'selected', rows: rows.length });
  }

  return (
    <div className="px-6 py-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Actions</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {stats.total} actions &middot; {stats.total_impact.toLocaleString()} EUR d'impact total
            {stats.overdue > 0 && <span className="text-red-600 ml-2 font-medium">&middot; {stats.overdue} en retard</span>}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={exportPlan30j}><Printer size={16} /> Plan 30 jours</Button>
          <Button onClick={() => setShowCreate(true)}><Plus size={16} /> Creer action</Button>
        </div>
      </div>

      {/* Quick views */}
      <div className="flex items-center gap-2">
        {QUICK_VIEWS.map(qv => {
          const Icon = qv.icon;
          const isActive = quickView === qv.id;
          return (
            <button
              key={qv.id}
              onClick={() => { setQuickView(isActive ? '' : qv.id); setPage(1); track('quick_view', { view: qv.id }); }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition border
                ${isActive ? 'bg-blue-50 border-blue-300 text-blue-700' : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'}`}
            >
              <Icon size={14} className={isActive ? 'text-blue-600' : qv.color} />
              {qv.label}
            </button>
          );
        })}
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-5 gap-3">
        {[
          { label: 'Backlog', value: stats.backlog, color: 'text-gray-700', bg: 'bg-gray-50' },
          { label: 'Planifie', value: stats.planned, color: 'text-blue-700', bg: 'bg-blue-50' },
          { label: 'En cours', value: stats.in_progress, color: 'text-amber-700', bg: 'bg-amber-50' },
          { label: 'Termine', value: stats.done, color: 'text-green-700', bg: 'bg-green-50' },
          { label: 'En retard', value: stats.overdue, color: 'text-red-700', bg: 'bg-red-50' },
        ].map(c => (
          <Card key={c.label}>
            <CardBody className={c.bg}>
              <p className="text-xs text-gray-500">{c.label}</p>
              <p className={`text-2xl font-bold ${c.color}`}>{c.value}</p>
            </CardBody>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <Tabs tabs={STATUT_TABS} active={filterStatut} onChange={(id) => { setFilterStatut(id); setPage(1); }} />
        <div className="ml-auto">
          <Select options={TYPE_OPTIONS} value={filterType} onChange={(e) => { setFilterType(e.target.value); setPage(1); }} />
        </div>
      </div>

      {/* Bulk actions bar */}
      {selected.size > 0 && (
        <div className="flex items-center gap-3 px-4 py-2.5 bg-blue-50 border border-blue-200 rounded-lg text-sm">
          <span className="font-medium text-blue-700">{selected.size} action(s) selectionnee(s)</span>
          <div className="flex-1" />
          <Button size="sm" variant="secondary" onClick={() => bulkChangeStatus('planned')}>
            <ArrowUpDown size={14} /> Planifier
          </Button>
          <Button size="sm" variant="secondary" onClick={() => bulkChangeStatus('in_progress')}>
            <Clock size={14} /> En cours
          </Button>
          <Button size="sm" variant="secondary" onClick={() => bulkChangeStatus('done')}>
            Terminer
          </Button>
          <Button size="sm" variant="secondary" onClick={exportSelected}>
            <Download size={14} /> Exporter
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setSelected(new Set())}>Deselectionner</Button>
        </div>
      )}

      {/* Table */}
      {total === 0 ? (
        <EmptyState icon={ListChecks} title="Aucune action" text="Creez votre premiere action pour commencer." ctaLabel="Creer action" onCta={() => setShowCreate(true)} />
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
                <Th sortable sorted={sortCol === 'priorite' ? sortDir : ''} onSort={() => handleSort('priorite')}>Priorite</Th>
                <Th sortable sorted={sortCol === 'impact_eur' ? sortDir : ''} onSort={() => handleSort('impact_eur')} className="text-right">Impact EUR</Th>
                <Th sortable sorted={sortCol === 'due_date' ? sortDir : ''} onSort={() => handleSort('due_date')}>Echeance</Th>
                <Th>Owner</Th>
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
                      <span className="flex items-center gap-1">
                        <Badge status={PRIORITY_BADGE[a.priorite] || 'neutral'}>{PRIORITY_LABEL[a.priorite] || a.priorite}</Badge>
                      </span>
                    </Td>
                    <Td className="text-right font-medium">{a.impact_eur.toLocaleString()} EUR</Td>
                    <Td className={`text-sm whitespace-nowrap ${overdue ? 'text-red-600 font-semibold' : ''}`}>
                      {a.due_date}
                      {overdue && <span className="ml-1 text-xs bg-red-50 text-red-600 px-1.5 py-0.5 rounded">SLA</span>}
                    </Td>
                    <Td className="text-sm">{a.owner || '-'}</Td>
                    <Td><span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">{STATUT_LABELS[a.statut]}</span></Td>
                  </Tr>
                );
              })}
            </Tbody>
          </Table>
          <div className="flex items-center justify-between px-4 py-2 border-t border-gray-100">
            <TrustBadge source="PROMEOS" period="mise a jour manuelle" confidence="medium" />
            <Pagination page={page} pageSize={pageSize} total={total} onChange={setPage} />
          </div>
        </Card>
      )}

      {/* Create Modal */}
      <CreateActionModal open={showCreate} onClose={() => setShowCreate(false)} onSave={handleSaveAction} />

      {/* Detail Modal */}
      <Modal open={!!detailAction} onClose={() => setDetailAction(null)} title={detailAction?.titre || 'Detail'} wide>
        {detailAction && (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div><p className="text-xs text-gray-500">Type</p><Badge status={(TYPE_BADGE[detailAction.type] || {}).status}>{detailAction.type}</Badge></div>
              <div>
                <p className="text-xs text-gray-500">Priorite</p>
                <Badge status={PRIORITY_BADGE[detailAction.priorite]}>{PRIORITY_LABEL[detailAction.priorite] || detailAction.priorite}</Badge>
              </div>
              <div><p className="text-xs text-gray-500">Statut</p><span className="text-sm font-medium">{STATUT_LABELS[detailAction.statut]}</span></div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div><p className="text-xs text-gray-500">Site</p><p className="text-sm font-medium">{detailAction.site_nom}</p></div>
              <div><p className="text-xs text-gray-500">Impact EUR</p><p className="text-sm font-bold text-red-600">{detailAction.impact_eur.toLocaleString()} EUR</p></div>
              <div><p className="text-xs text-gray-500">Effort</p><p className="text-sm">{detailAction.effort}</p></div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-500">Echeance (SLA)</p>
                <p className={`text-sm flex items-center gap-1 ${isOverdue(detailAction) ? 'text-red-600 font-semibold' : ''}`}>
                  <Clock size={14} /> {detailAction.due_date}
                  {isOverdue(detailAction) && <span className="text-xs bg-red-50 text-red-600 px-1.5 py-0.5 rounded ml-1">EN RETARD</span>}
                </p>
              </div>
              <div><p className="text-xs text-gray-500">Responsable</p><p className="text-sm">{detailAction.owner || 'Non assigne'}</p></div>
            </div>

            {/* Tags */}
            <div className="flex items-center gap-2">
              <Tag size={14} className="text-gray-400" />
              <span className="text-xs px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded">{detailAction.type}</span>
              <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">{detailAction.site_nom}</span>
              {isOverdue(detailAction) && <span className="text-xs px-2 py-0.5 bg-red-50 text-red-600 rounded">en-retard</span>}
            </div>

            {/* Mock comments */}
            <div className="border-t border-gray-100 pt-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1"><MessageSquare size={14} /> Commentaires</h3>
              <div className="space-y-2">
                <div className="p-3 bg-gray-50 rounded-lg text-sm">
                  <p className="font-medium text-gray-700">J. Dupont <span className="text-gray-400 font-normal">— 10/02/2026</span></p>
                  <p className="text-gray-600 mt-1">RDV planifie avec le prestataire pour le 20/02.</p>
                </div>
              </div>
              <div className="mt-3 flex gap-2">
                <input placeholder="Ajouter un commentaire..." className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500" />
                <Button size="sm">Envoyer</Button>
              </div>
            </div>

            {/* Mock attachments */}
            <div className="border-t border-gray-100 pt-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1"><Paperclip size={14} /> Pieces jointes</h3>
              <p className="text-sm text-gray-400">Aucune piece jointe.</p>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
