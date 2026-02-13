/**
 * PROMEOS - Notifications & Alert Center V1 (/notifications)
 * Sprint 10.2: in-app alerts from 5 briques with severity, deeplinks, workflow.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getNotificationsList,
  syncNotifications,
  patchNotification,
  getNotificationsSummary,
} from '../services/api';
import { Card, CardBody, Badge, Button } from '../ui';
import {
  Bell, AlertTriangle, AlertCircle, Info, RefreshCw,
  ExternalLink, Check, X, Eye,
} from 'lucide-react';

const SEVERITY_META = {
  critical: { label: 'Critique', color: 'bg-red-100 text-red-800', icon: AlertCircle, badge: 'crit' },
  warn:     { label: 'Attention', color: 'bg-orange-100 text-orange-800', icon: AlertTriangle, badge: 'warn' },
  info:     { label: 'Info', color: 'bg-blue-100 text-blue-800', icon: Info, badge: 'info' },
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

function SeverityCard({ severity, count, newCount }) {
  const meta = SEVERITY_META[severity] || SEVERITY_META.info;
  const Icon = meta.icon;
  return (
    <Card>
      <CardBody className={`${meta.color} bg-opacity-50`}>
        <div className="flex items-center gap-3">
          <Icon size={24} />
          <div>
            <p className="text-2xl font-bold">{count}</p>
            <p className="text-xs">{meta.label}{newCount > 0 ? ` (${newCount} nouveau${newCount > 1 ? 'x' : ''})` : ''}</p>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

export default function NotificationsPage() {
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState(null);
  const [filterSeverity, setFilterSeverity] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterSource, setFilterSource] = useState('');

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
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filterSeverity, filterStatus, filterSource]);

  const handleSync = async () => {
    setSyncing(true);
    setMessage(null);
    try {
      const r = await syncNotifications();
      setMessage(`Sync terminee: ${r.created} creees, ${r.updated} maj, ${r.skipped} inchangees`);
      await load();
    } catch (e) {
      setMessage('Erreur: ' + (e.response?.data?.detail || e.message));
    } finally {
      setSyncing(false);
    }
  };

  const handlePatch = async (id, status) => {
    try {
      await patchNotification(id, { status });
      setEvents(prev => prev.map(e => e.id === id ? { ...e, status } : e));
    } catch (e) {
      console.error(e);
    }
  };

  const getSevMeta = (severity) => SEVERITY_META[severity] || SEVERITY_META.info;

  return (
    <div className="px-6 py-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Alertes</h2>
          <p className="text-sm text-gray-500 mt-0.5">Centre d'alertes : conformite, factures, contrats, conso, actions</p>
        </div>
        <Button size="sm" onClick={handleSync} disabled={syncing}>
          <RefreshCw size={14} className={syncing ? 'animate-spin' : ''} />
          {syncing ? 'Sync...' : 'Synchroniser'}
        </Button>
      </div>

      {message && (
        <div className="p-3 bg-blue-50 text-blue-800 rounded-lg text-sm">{message}</div>
      )}

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-3 gap-4">
          <SeverityCard severity="critical" count={summary.by_severity?.critical || 0} newCount={summary.new_critical || 0} />
          <SeverityCard severity="warn" count={summary.by_severity?.warn || 0} newCount={summary.new_warn || 0} />
          <SeverityCard severity="info" count={summary.by_severity?.info || 0} newCount={0} />
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
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
        <span className="text-xs text-gray-400 ml-2">{events.length} alerte(s)</span>
      </div>

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
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">Severite</th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">Titre</th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">Source</th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">Impact</th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">Echeance</th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">Statut</th>
                  <th className="text-right py-3 px-4 text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody>
                {events.map((evt) => {
                  const meta = getSevMeta(evt.severity);
                  const Icon = meta.icon;
                  return (
                    <tr key={evt.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${meta.color}`}>
                          <Icon size={12} /> {meta.label}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-800 max-w-md">
                        <p className="font-medium truncate">{evt.title}</p>
                        {evt.message && (
                          <p className="text-xs text-gray-500 mt-0.5 truncate">{evt.message}</p>
                        )}
                      </td>
                      <td className="py-3 px-4 text-sm">
                        <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                          {SOURCE_LABELS[evt.source_type] || evt.source_type}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-sm text-red-600 font-medium">
                        {evt.estimated_impact_eur ? `${Math.round(evt.estimated_impact_eur)} EUR` : '-'}
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-600">
                        {evt.due_date || '-'}
                      </td>
                      <td className="py-3 px-4 text-sm">
                        <Badge status={evt.status === 'new' ? 'warn' : evt.status === 'read' ? 'neutral' : 'ok'}>
                          {STATUS_LABELS[evt.status] || evt.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-right">
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
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
