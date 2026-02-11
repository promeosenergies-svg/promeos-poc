/**
 * PROMEOS - Actions & Plan (/actions)
 * Backlog table + create modal + detail panel + export "Plan 30j"
 */
import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus, Download, Printer, Filter, ChevronRight,
  MessageSquare, Paperclip, Clock, ListChecks,
} from 'lucide-react';
import { Card, CardBody, Badge, Button, Select, Pagination, EmptyState, Tabs } from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';
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

export default function ActionsPage() {
  const navigate = useNavigate();
  const [actions, setActions] = useState(mockActions);
  const [filterStatut, setFilterStatut] = useState('');
  const [filterType, setFilterType] = useState('');
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);
  const [detailAction, setDetailAction] = useState(null);
  const pageSize = 15;

  const filtered = useMemo(() => {
    let result = [...actions];
    if (filterStatut) result = result.filter(a => a.statut === filterStatut);
    if (filterType) result = result.filter(a => a.type === filterType);
    result.sort((a, b) => {
      const prio = { critical: 4, high: 3, medium: 2, low: 1 };
      return (prio[b.priorite] || 0) - (prio[a.priorite] || 0);
    });
    return result;
  }, [actions, filterStatut, filterType]);

  const total = filtered.length;
  const pageData = filtered.slice((page - 1) * pageSize, page * pageSize);

  const stats = useMemo(() => ({
    total: actions.length,
    backlog: actions.filter(a => a.statut === 'backlog').length,
    planned: actions.filter(a => a.statut === 'planned').length,
    in_progress: actions.filter(a => a.statut === 'in_progress').length,
    done: actions.filter(a => a.statut === 'done').length,
    total_impact: actions.reduce((s, a) => s + a.impact_eur, 0),
  }), [actions]);

  function handleSaveAction(action) {
    setActions(prev => [action, ...prev]);
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

  return (
    <div className="px-6 py-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Actions</h2>
          <p className="text-sm text-gray-500 mt-0.5">{stats.total} actions &middot; {stats.total_impact.toLocaleString()} EUR d'impact total</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={exportPlan30j}><Printer size={16} /> Plan 30 jours</Button>
          <Button onClick={() => setShowCreate(true)}><Plus size={16} /> Creer action</Button>
        </div>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Backlog', value: stats.backlog, color: 'text-gray-700', bg: 'bg-gray-50' },
          { label: 'Planifie', value: stats.planned, color: 'text-blue-700', bg: 'bg-blue-50' },
          { label: 'En cours', value: stats.in_progress, color: 'text-amber-700', bg: 'bg-amber-50' },
          { label: 'Termine', value: stats.done, color: 'text-green-700', bg: 'bg-green-50' },
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

      {/* Table */}
      {total === 0 ? (
        <EmptyState icon={ListChecks} title="Aucune action" text="Creez votre premiere action pour commencer." ctaLabel="Creer action" onCta={() => setShowCreate(true)} />
      ) : (
        <Card>
          <Table>
            <Thead>
              <tr>
                <Th>Action</Th>
                <Th>Type</Th>
                <Th>Site</Th>
                <Th>Priorite</Th>
                <Th className="text-right">Impact EUR</Th>
                <Th>Echeance</Th>
                <Th>Owner</Th>
                <Th>Statut</Th>
              </tr>
            </Thead>
            <Tbody>
              {pageData.map((a) => {
                const typeBadge = TYPE_BADGE[a.type] || TYPE_BADGE.maintenance;
                return (
                  <Tr key={a.id} onClick={() => { setDetailAction(a); track('row_click', { action_id: a.id }); }}>
                    <Td className="font-medium text-gray-900 max-w-xs truncate">{a.titre}</Td>
                    <Td><Badge status={typeBadge.status}>{typeBadge.label}</Badge></Td>
                    <Td className="text-sm">{a.site_nom}</Td>
                    <Td><Badge status={PRIORITY_BADGE[a.priorite] || 'neutral'}>{a.priorite}</Badge></Td>
                    <Td className="text-right font-medium">{a.impact_eur.toLocaleString()} EUR</Td>
                    <Td className="text-sm whitespace-nowrap">{a.due_date}</Td>
                    <Td className="text-sm">{a.owner || '-'}</Td>
                    <Td><span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">{STATUT_LABELS[a.statut]}</span></Td>
                  </Tr>
                );
              })}
            </Tbody>
          </Table>
          <Pagination page={page} pageSize={pageSize} total={total} onChange={setPage} />
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
              <div><p className="text-xs text-gray-500">Priorite</p><Badge status={PRIORITY_BADGE[detailAction.priorite]}>{detailAction.priorite}</Badge></div>
              <div><p className="text-xs text-gray-500">Statut</p><span className="text-sm font-medium">{STATUT_LABELS[detailAction.statut]}</span></div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div><p className="text-xs text-gray-500">Site</p><p className="text-sm font-medium">{detailAction.site_nom}</p></div>
              <div><p className="text-xs text-gray-500">Impact EUR</p><p className="text-sm font-bold text-red-600">{detailAction.impact_eur.toLocaleString()} EUR</p></div>
              <div><p className="text-xs text-gray-500">Effort</p><p className="text-sm">{detailAction.effort}</p></div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div><p className="text-xs text-gray-500">Echeance</p><p className="text-sm flex items-center gap-1"><Clock size={14} /> {detailAction.due_date}</p></div>
              <div><p className="text-xs text-gray-500">Responsable</p><p className="text-sm">{detailAction.owner || 'Non assigne'}</p></div>
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
