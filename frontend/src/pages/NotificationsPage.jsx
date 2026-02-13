/**
 * PROMEOS - Notifications & Alert Center V2 (/notifications)
 * PageShell + KpiCard + FilterBar + useToast + Expert Mode
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getNotificationsList,
  syncNotifications,
  patchNotification,
  getNotificationsSummary,
} from '../services/api';
import { Card, CardBody, Badge, Button, PageShell, KpiCard, FilterBar, Select } from '../ui';
import { useToast } from '../ui/ToastProvider';
import { useExpertMode } from '../contexts/ExpertModeContext';
import {
  Bell, AlertTriangle, AlertCircle, Info, RefreshCw,
  ExternalLink, Eye, X, Trash2,
} from 'lucide-react';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';

const SEVERITY_META = {
  critical: { label: 'Critique', color: 'bg-red-100 text-red-800', icon: AlertCircle, badge: 'crit', kpiColor: 'bg-red-600' },
  warn:     { label: 'Attention', color: 'bg-orange-100 text-orange-800', icon: AlertTriangle, badge: 'warn', kpiColor: 'bg-amber-600' },
  info:     { label: 'Info', color: 'bg-blue-100 text-blue-800', icon: Info, badge: 'info', kpiColor: 'bg-blue-600' },
};

const SOURCE_LABELS = {
  compliance: 'Conformite',
  billing: 'Facturation',
  purchase: 'Achats',
  consumption: 'Consommation',
  action_hub: 'Actions',
};

const STATUS_LABELS = {
  new: 'Nouveau',
  read: 'Lu',
  dismissed: 'Ignore',
};

export default function NotificationsPage() {
  const navigate = useNavigate();
  const { isExpert } = useExpertMode();
  const { toast } = useToast();
  const [events, setEvents] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [filterSeverity, setFilterSeverity] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterSource, setFilterSource] = useState('');
  const [selected, setSelected] = useState(new Set());

  const load = async () => {
    setLoading(true);
    try {
      const params = {};
      if (filterSeverity) params.severity = filterSeverity;
      if (filterStatus) params.status = filterStatus;
      if (filterSource) params.source_type = filterSource;
      const [evts, sum] = await Promise.all([
        getNotificationsList(params),
        getNotificationsSummary(),
      ]);
      setEvents(evts);
      setSummary(sum);
    } catch (e) {
      toast('Erreur chargement alertes', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filterSeverity, filterStatus, filterSource]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const r = await syncNotifications();
      toast(`Sync terminee: ${r.created} creees, ${r.updated} maj, ${r.skipped} inchangees`, 'success');
      await load();
    } catch (e) {
      toast('Erreur: ' + (e.response?.data?.detail || e.message), 'error');
    } finally {
      setSyncing(false);
    }
  };

  const handlePatch = async (id, status) => {
    try {
      await patchNotification(id, { status });
      setEvents(prev => prev.map(e => e.id === id ? { ...e, status } : e));
      toast(`Alerte ${status === 'read' ? 'marquee lue' : 'ignoree'}`, 'success');
    } catch (e) {
      toast('Erreur mise a jour', 'error');
    }
  };

  const handleBulkDismiss = async () => {
    const ids = Array.from(selected);
    for (const id of ids) {
      try {
        await patchNotification(id, { status: 'dismissed' });
      } catch {}
    }
    setEvents(prev => prev.map(e => ids.includes(e.id) ? { ...e, status: 'dismissed' } : e));
    setSelected(new Set());
    toast(`${ids.length} alerte(s) ignoree(s)`, 'success');
  };

  const hasFilters = filterSeverity || filterStatus || filterSource;
  const resetFilters = () => { setFilterSeverity(''); setFilterStatus(''); setFilterSource(''); };

  const toggleSelect = (id) => {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const getSevMeta = (severity) => SEVERITY_META[severity] || SEVERITY_META.info;

  return (
    <PageShell
      icon={Bell}
      title="Alertes"
      subtitle="Centre d'alertes : conformite, factures, contrats, conso, actions"
      actions={
        <>
          {isExpert && selected.size > 0 && (
            <Button variant="secondary" size="sm" onClick={handleBulkDismiss}>
              <Trash2 size={14} /> Ignorer {selected.size}
            </Button>
          )}
          <Button size="sm" onClick={handleSync} disabled={syncing}>
            <RefreshCw size={14} className={syncing ? 'animate-spin' : ''} />
            {syncing ? 'Sync...' : 'Synchroniser'}
          </Button>
        </>
      }
    >
      {/* Summary KPIs */}
      {summary && (
        <div className="grid grid-cols-3 gap-4">
          <KpiCard
            icon={AlertCircle}
            title="Critique"
            value={summary.by_severity?.critical || 0}
            sub={summary.new_critical > 0 ? `${summary.new_critical} nouveau${summary.new_critical > 1 ? 'x' : ''}` : undefined}
            color="bg-red-600"
          />
          <KpiCard
            icon={AlertTriangle}
            title="Attention"
            value={summary.by_severity?.warn || 0}
            sub={summary.new_warn > 0 ? `${summary.new_warn} nouveau${summary.new_warn > 1 ? 'x' : ''}` : undefined}
            color="bg-amber-600"
          />
          <KpiCard
            icon={Info}
            title="Info"
            value={summary.by_severity?.info || 0}
            color="bg-blue-600"
          />
        </div>
      )}

      {/* Filters */}
      <FilterBar onReset={hasFilters ? resetFilters : undefined} count={events.length}>
        <select
          value={filterSeverity}
          onChange={(e) => setFilterSeverity(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Toutes severites</option>
          <option value="critical">Critique</option>
          <option value="warn">Attention</option>
          <option value="info">Info</option>
        </select>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Tous statuts</option>
          <option value="new">Nouveau</option>
          <option value="read">Lu</option>
          <option value="dismissed">Ignore</option>
        </select>
        <select
          value={filterSource}
          onChange={(e) => setFilterSource(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Toutes sources</option>
          <option value="compliance">Conformite</option>
          <option value="billing">Facturation</option>
          <option value="purchase">Achats</option>
          <option value="consumption">Consommation</option>
          <option value="action_hub">Actions</option>
        </select>
      </FilterBar>

      {/* Events Table */}
      {loading ? (
        <div className="text-center py-16 text-gray-400">Chargement...</div>
      ) : events.length === 0 ? (
        <Card>
          <CardBody className="text-center py-12">
            <Bell size={32} className="mx-auto text-gray-300 mb-4" />
            <p className="text-gray-500 text-lg mb-2">Aucune alerte</p>
            <p className="text-gray-400 text-sm mb-6">
              Synchronisez pour detecter les alertes depuis toutes les briques.
            </p>
            <Button onClick={handleSync} disabled={syncing}>Synchroniser</Button>
          </CardBody>
        </Card>
      ) : (
        <Card>
          <Table>
            <Thead>
              <tr>
                {isExpert && <Th className="w-8"><span className="sr-only">Select</span></Th>}
                <Th>Severite</Th>
                <Th>Titre</Th>
                <Th>Source</Th>
                <Th>Impact</Th>
                <Th>Echeance</Th>
                <Th>Statut</Th>
                {isExpert && <Th>ID</Th>}
                <Th className="text-right">Actions</Th>
              </tr>
            </Thead>
            <Tbody>
              {events.map((evt) => {
                const meta = getSevMeta(evt.severity);
                const Icon = meta.icon;
                return (
                  <Tr key={evt.id}>
                    {isExpert && (
                      <Td>
                        <input
                          type="checkbox"
                          checked={selected.has(evt.id)}
                          onChange={() => toggleSelect(evt.id)}
                          className="rounded border-gray-300"
                        />
                      </Td>
                    )}
                    <Td>
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${meta.color}`}>
                        <Icon size={12} /> {meta.label}
                      </span>
                    </Td>
                    <Td className="max-w-md">
                      <p className="font-medium text-gray-800 truncate">{evt.title}</p>
                      {evt.message && (
                        <p className="text-xs text-gray-500 mt-0.5 truncate">{evt.message}</p>
                      )}
                    </Td>
                    <Td>
                      <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                        {SOURCE_LABELS[evt.source_type] || evt.source_type}
                      </span>
                    </Td>
                    <Td className="text-red-600 font-medium">
                      {evt.estimated_impact_eur ? `${Math.round(evt.estimated_impact_eur)} EUR` : '-'}
                    </Td>
                    <Td className="text-gray-600">{evt.due_date || '-'}</Td>
                    <Td>
                      <Badge status={evt.status === 'new' ? 'warn' : evt.status === 'read' ? 'neutral' : 'ok'}>
                        {STATUS_LABELS[evt.status] || evt.status}
                      </Badge>
                    </Td>
                    {isExpert && (
                      <Td className="text-xs text-gray-400 font-mono">{evt.id}</Td>
                    )}
                    <Td className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        {evt.deeplink_path && (
                          <button
                            onClick={() => navigate(evt.deeplink_path)}
                            className="p-1 text-blue-500 hover:bg-blue-50 rounded"
                            title="Voir"
                          >
                            <ExternalLink size={14} />
                          </button>
                        )}
                        {evt.status === 'new' && (
                          <button
                            onClick={() => handlePatch(evt.id, 'read')}
                            className="p-1 text-green-500 hover:bg-green-50 rounded"
                            title="Marquer lu"
                          >
                            <Eye size={14} />
                          </button>
                        )}
                        {evt.status !== 'dismissed' && (
                          <button
                            onClick={() => handlePatch(evt.id, 'dismissed')}
                            className="p-1 text-gray-400 hover:bg-gray-100 rounded"
                            title="Ignorer"
                          >
                            <X size={14} />
                          </button>
                        )}
                      </div>
                    </Td>
                  </Tr>
                );
              })}
            </Tbody>
          </Table>
        </Card>
      )}
    </PageShell>
  );
}
