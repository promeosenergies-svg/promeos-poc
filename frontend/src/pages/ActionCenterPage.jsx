/**
 * PROMEOS — Action Center Console
 * Unified view of all actionable issues across compliance, billing, purchase, patrimoine.
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import {
  getActionCenterIssues,
  getActionCenterActions,
  getActionCenterActionsSummary,
  createActionCenterAction,
  resolveActionCenterAction,
  reopenActionCenterAction,
} from '../services/api';
import ActionDetailPanel from '../components/ActionDetailPanel';
import { RiskBadge } from '../lib/risk/normalizeRisk';
import EmptyState from '../ui/EmptyState';

const PRIORITY_COLORS = {
  critical: 'bg-red-100 text-red-800 border-red-300',
  high: 'bg-orange-100 text-orange-800 border-orange-300',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  low: 'bg-blue-100 text-blue-800 border-blue-300',
};

const STATUS_LABELS = {
  open: 'Ouvert',
  in_progress: 'En cours',
  resolved: 'Résolu',
  dismissed: 'Écarté',
  reopened: 'Réouvert',
};

const SLA_BADGES = {
  on_track: { label: 'Dans les temps', cls: 'text-green-700 bg-green-50' },
  at_risk: { label: 'À risque', cls: 'text-amber-700 bg-amber-50' },
  overdue: { label: 'En retard', cls: 'text-red-700 bg-red-50' },
  resolved: { label: 'Résolu', cls: 'text-gray-500 bg-gray-50' },
};

const DOMAIN_LABELS = {
  compliance: 'Conformité',
  billing: 'Facturation',
  purchase: 'Achat',
  patrimoine: 'Patrimoine',
};

export default function ActionCenterPage() {
  const [issues, setIssues] = useState([]);
  const [actions, setActions] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedItem, setSelectedItem] = useState(null);

  // Filters
  const [filterDomain, setFilterDomain] = useState('');
  const [filterPriority, setFilterPriority] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterOwner, setFilterOwner] = useState('');
  const [tab, setTab] = useState('issues'); // issues | actions

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (filterDomain) params.domain = filterDomain;
      if (filterPriority) params.priority = filterPriority;
      if (filterStatus) params.status = filterStatus;

      const [issuesRes, actionsRes, summaryRes] = await Promise.all([
        getActionCenterIssues(params).catch(() => ({ issues: [], total: 0 })),
        getActionCenterActions(params).catch(() => ({ actions: [], total: 0 })),
        getActionCenterActionsSummary().catch(() => null),
      ]);

      setIssues(issuesRes?.issues || []);
      setActions(actionsRes?.actions || []);
      setSummary(summaryRes);
    } catch (e) {
      setError("Impossible de charger le centre d'action");
    } finally {
      setLoading(false);
    }
  }, [filterDomain, filterPriority, filterStatus]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreateAction = async (issue) => {
    try {
      await createActionCenterAction(issue);
      loadData();
    } catch (e) {
      console.error('Erreur création action', e);
    }
  };

  const handleResolve = async (actionId) => {
    try {
      await resolveActionCenterAction(actionId, { resolution_note: 'Résolu depuis la console' });
      loadData();
    } catch (e) {
      console.error('Erreur résolution', e);
    }
  };

  const handleReopen = async (actionId) => {
    try {
      await reopenActionCenterAction(actionId, { reason: 'Réouvert depuis la console' });
      loadData();
    } catch (e) {
      console.error('Erreur réouverture', e);
    }
  };

  const currentList = tab === 'issues' ? issues : actions;

  const filteredList = useMemo(() => {
    let list = [...currentList];
    if (filterOwner && tab === 'actions') {
      list = list.filter((a) => (a.owner || '').toLowerCase().includes(filterOwner.toLowerCase()));
    }
    return list;
  }, [currentList, filterOwner, tab]);

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Centre d'action</h1>
          <p className="text-sm text-gray-500 mt-1">
            Signaux critiques et actions de remédiation — tous domaines
          </p>
        </div>
        {summary && (
          <div className="flex gap-3">
            <div className="text-center px-4 py-2 rounded-lg bg-red-50">
              <div className="text-lg font-bold text-red-700">{summary.overdue_count || 0}</div>
              <div className="text-xs text-red-600">En retard</div>
            </div>
            <div className="text-center px-4 py-2 rounded-lg bg-orange-50">
              <div className="text-lg font-bold text-orange-700">{summary.open_count || 0}</div>
              <div className="text-xs text-orange-600">Ouvertes</div>
            </div>
            <div className="text-center px-4 py-2 rounded-lg bg-green-50">
              <div className="text-lg font-bold text-green-700">{summary.resolved_count || 0}</div>
              <div className="text-xs text-green-600">Résolues</div>
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b mb-4">
        <button
          onClick={() => setTab('issues')}
          className={`px-4 py-2 text-sm font-medium border-b-2 ${tab === 'issues' ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500'}`}
        >
          Signaux ({issues.length})
        </button>
        <button
          onClick={() => setTab('actions')}
          className={`px-4 py-2 text-sm font-medium border-b-2 ml-4 ${tab === 'actions' ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500'}`}
        >
          Actions ({actions.length})
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-4 flex-wrap">
        <select
          value={filterDomain}
          onChange={(e) => setFilterDomain(e.target.value)}
          className="text-sm border rounded px-2 py-1"
        >
          <option value="">Tous domaines</option>
          {Object.entries(DOMAIN_LABELS).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <select
          value={filterPriority}
          onChange={(e) => setFilterPriority(e.target.value)}
          className="text-sm border rounded px-2 py-1"
        >
          <option value="">Toutes priorités</option>
          <option value="critical">Critique</option>
          <option value="high">Haute</option>
          <option value="medium">Moyenne</option>
          <option value="low">Basse</option>
        </select>
        {tab === 'actions' && (
          <>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="text-sm border rounded px-2 py-1"
            >
              <option value="">Tous statuts</option>
              {Object.entries(STATUS_LABELS).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
            <input
              type="text"
              placeholder="Filtrer par owner..."
              value={filterOwner}
              onChange={(e) => setFilterOwner(e.target.value)}
              className="text-sm border rounded px-2 py-1 w-40"
            />
          </>
        )}
        {(filterDomain || filterPriority || filterStatus || filterOwner) && (
          <button
            onClick={() => {
              setFilterDomain('');
              setFilterPriority('');
              setFilterStatus('');
              setFilterOwner('');
            }}
            className="text-sm text-blue-600 underline"
          >
            Réinitialiser
          </button>
        )}
      </div>

      {/* Error */}
      {error && <div className="bg-red-50 text-red-700 p-3 rounded mb-4">{error}</div>}

      {/* Loading */}
      {loading && <div className="text-center py-8 text-gray-400">Chargement...</div>}

      {/* Empty */}
      {!loading && filteredList.length === 0 && (
        <EmptyState
          variant="empty"
          title="Aucun signal"
          text="Toutes les actions sont traitées ou aucun signal détecté."
        />
      )}

      {/* List */}
      {!loading && filteredList.length > 0 && (
        <div className="space-y-2">
          {filteredList.map((item, idx) => {
            const priority = item.priority || item.severity || 'medium';
            const sla = item.sla_status || 'on_track';
            const slaBadge = SLA_BADGES[sla] || SLA_BADGES.on_track;
            const domain = DOMAIN_LABELS[item.domain] || item.domain;

            return (
              <div
                key={item.issue_id || item.id || idx}
                onClick={() => setSelectedItem(item)}
                className={`border rounded-lg p-4 cursor-pointer hover:shadow-md transition-shadow ${
                  sla === 'overdue' ? 'border-red-300 bg-red-50/30' : 'border-gray-200'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={`text-xs font-medium px-2 py-0.5 rounded border ${PRIORITY_COLORS[priority] || PRIORITY_COLORS.medium}`}
                      >
                        {priority === 'critical'
                          ? 'Critique'
                          : priority === 'high'
                            ? 'Haute'
                            : priority === 'medium'
                              ? 'Moyenne'
                              : 'Basse'}
                      </span>
                      <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                        {domain}
                      </span>
                      {tab === 'actions' && item.status && (
                        <span className="text-xs text-gray-600 bg-gray-100 px-2 py-0.5 rounded">
                          {STATUS_LABELS[item.status] || item.status}
                        </span>
                      )}
                      <span className={`text-xs px-2 py-0.5 rounded ${slaBadge.cls}`}>
                        {slaBadge.label}
                      </span>
                    </div>
                    <div className="font-medium text-gray-900 text-sm">{item.issue_label}</div>
                    <div className="text-xs text-gray-500 mt-1">
                      {item.site_name || `Site #${item.site_id}`}
                      {item.owner && <span className="ml-2">· {item.owner}</span>}
                      {item.due_date && (
                        <span className="ml-2">
                          · Échéance {new Date(item.due_date).toLocaleDateString('fr-FR')}
                        </span>
                      )}
                      {item.estimated_impact_eur && (
                        <span className="ml-2 inline-flex items-center gap-1">
                          · <RiskBadge riskEur={item.estimated_impact_eur} size="sm" />
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-1 ml-4">
                    {tab === 'issues' && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleCreateAction(item);
                        }}
                        className="text-xs bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700"
                      >
                        Créer action
                      </button>
                    )}
                    {tab === 'actions' && item.status !== 'resolved' && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleResolve(item.id);
                        }}
                        className="text-xs bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700"
                      >
                        Résoudre
                      </button>
                    )}
                    {tab === 'actions' && item.status === 'resolved' && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleReopen(item.id);
                        }}
                        className="text-xs bg-amber-600 text-white px-3 py-1 rounded hover:bg-amber-700"
                      >
                        Réouvrir
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Detail Panel */}
      {selectedItem && (
        <ActionDetailPanel
          item={selectedItem}
          onClose={() => setSelectedItem(null)}
          onResolve={handleResolve}
          onReopen={handleReopen}
          isAction={tab === 'actions'}
        />
      )}
    </div>
  );
}
