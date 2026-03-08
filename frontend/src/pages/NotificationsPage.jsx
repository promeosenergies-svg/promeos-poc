/**
 * PROMEOS - Alert Inbox (/notifications) Phase 6 — Finitions
 * Sticky filter bar, sync meta, improved density, accent hover.
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useScope } from '../contexts/ScopeContext';
import {
  getNotificationsList,
  syncNotifications,
  patchNotification,
  getNotificationsSummary,
} from '../services/api';
import {
  Card,
  Button,
  PageShell,
  MetricCard,
  StatusDot,
  EmptyState,
  ErrorState,
  SkeletonCard,
  Pagination,
  Tabs,
  Drawer,
  ActiveFiltersBar,
} from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';
import { useToast } from '../ui/ToastProvider';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { useActionDrawer } from '../contexts/ActionDrawerContext';
import {
  Bell,
  RefreshCw,
  ExternalLink,
  Eye,
  X,
  Trash2,
  Search,
  Clock,
  Database,
  Plus,
} from 'lucide-react';

const SEVERITY_STATUS = { critical: 'crit', warn: 'warn', info: 'info' };
const SEVERITY_LABEL = { critical: 'Critique', warn: 'Attention', info: 'Info' };

const SOURCE_LABELS = {
  compliance: 'Conformité',
  billing: 'Facturation',
  purchase: 'Achats',
  consumption: 'Consommation',
  action_hub: 'Actions',
};

const STATUS_LABELS = {
  new: 'Nouveau',
  read: 'Lu',
  dismissed: 'Ignoré',
};

const TRIAGE_TABS = [
  { id: 'all', label: 'Toutes' },
  { id: 'new', label: 'Nouvelles' },
  { id: 'read', label: 'Lues' },
  { id: 'dismissed', label: 'Ignorées' },
];

export default function NotificationsPage() {
  const navigate = useNavigate();
  const { openActionDrawer } = useActionDrawer();
  const { selectedSiteId } = useScope();
  const { isExpert } = useExpertMode();
  const { toast } = useToast();
  const [events, setEvents] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [lastSync, setLastSync] = useState(null);
  const [selected, setSelected] = useState(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [triageTab, setTriageTab] = useState('all');
  const [filterSource, setFilterSource] = useState('');
  const [page, setPage] = useState(1);
  const [drawerEvent, setDrawerEvent] = useState(null);
  const pageSize = 20;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = selectedSiteId ? { site_id: selectedSiteId } : {};
      const [evts, sum] = await Promise.all([
        getNotificationsList(params),
        getNotificationsSummary(),
      ]);
      setEvents(evts);
      setSummary(sum);
      setLastSync(new Date());
    } catch {
      setError('Erreur de chargement des alertes');
    } finally {
      setLoading(false);
    }
  }, [selectedSiteId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const r = await syncNotifications();
      toast(`Synchronisation : ${r.created} créées, ${r.updated} mises à jour`, 'success');
      await load();
    } catch (e) {
      toast('Erreur synchronisation', 'error');
    } finally {
      setSyncing(false);
    }
  };

  const handlePatch = async (id, status) => {
    try {
      await patchNotification(id, { status });
      setEvents((prev) => prev.map((e) => (e.id === id ? { ...e, status } : e)));
      if (drawerEvent?.id === id) setDrawerEvent((prev) => ({ ...prev, status }));
    } catch {
      toast('Erreur lors de la mise à jour', 'error');
    }
  };

  const handleBulkAction = async (status) => {
    const ids = Array.from(selected);
    if (ids.length === 0) return;
    await Promise.allSettled(ids.map((id) => patchNotification(id, { status })));
    setEvents((prev) => prev.map((e) => (ids.includes(e.id) ? { ...e, status } : e)));
    setSelected(new Set());
    toast(
      `${ids.length} alerte(s) ${status === 'dismissed' ? 'ignorée(s)' : 'marquée(s) lue(s)'}`,
      'success'
    );
  };

  const toggleSelect = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === pageData.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(pageData.map((e) => e.id)));
    }
  };

  const filteredEvents = useMemo(() => {
    let list = events;
    if (triageTab !== 'all') {
      list = list.filter((e) => e.status === triageTab);
    }
    if (filterSource) {
      list = list.filter((e) => e.source_type === filterSource);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        (e) => e.title.toLowerCase().includes(q) || (e.message || '').toLowerCase().includes(q)
      );
    }
    return list;
  }, [events, triageTab, filterSource, searchQuery]);

  const totalFiltered = filteredEvents.length;
  const pageData = filteredEvents.slice((page - 1) * pageSize, page * pageSize);

  const tabsWithCounts = useMemo(() => {
    const counts = { all: events.length, new: 0, read: 0, dismissed: 0 };
    for (const e of events) {
      counts[e.status] = (counts[e.status] || 0) + 1;
    }
    return TRIAGE_TABS.map((t) => ({
      ...t,
      label: `${t.label} (${counts[t.id] || 0})`,
    }));
  }, [events]);

  if (loading) {
    return (
      <PageShell icon={Bell} title="Alertes" subtitle="Chargement...">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </PageShell>
    );
  }

  if (error) {
    return (
      <PageShell icon={Bell} title="Alertes">
        <ErrorState title="Erreur" message={error} onRetry={load} />
      </PageShell>
    );
  }

  return (
    <PageShell
      icon={Bell}
      title="Alertes"
      subtitle={`${events.length} alertes${events.filter((e) => e.status === 'new').length > 0 ? ` · ${events.filter((e) => e.status === 'new').length} nouvelles` : ''}`}
      actions={
        <div className="flex items-center gap-2">
          {/* Sync meta — compact */}
          {lastSync && (
            <div className="hidden sm:flex items-center gap-3 mr-1 text-[11px] text-gray-400">
              <span className="flex items-center gap-1">
                <Clock size={11} />
                {lastSync.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
              </span>
              {summary && (
                <span className="flex items-center gap-1" title="Couverture sources">
                  <Database size={11} />
                  {Object.keys(summary.by_source || {}).length} sources
                </span>
              )}
            </div>
          )}
          <Button size="sm" onClick={handleSync} disabled={syncing}>
            <RefreshCw size={14} className={syncing ? 'animate-spin' : ''} />
            {syncing ? 'Sync...' : 'Synchroniser'}
          </Button>
        </div>
      }
    >
      {/* Summary KPIs with accents */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricCard
            accent="risque"
            icon={Bell}
            label="Critique"
            value={summary.by_severity?.critical || 0}
            sub={summary.new_critical > 0 ? `${summary.new_critical} nouvelle(s)` : undefined}
            status="crit"
          />
          <MetricCard
            accent="alertes"
            label="Attention"
            value={summary.by_severity?.warn || 0}
            sub={summary.new_warn > 0 ? `${summary.new_warn} nouvelle(s)` : undefined}
            status="warn"
          />
          <MetricCard
            accent="conformite"
            label="Info"
            value={summary.by_severity?.info || 0}
            status="info"
          />
        </div>
      )}

      {/* Triage tabs */}
      <Tabs
        tabs={tabsWithCounts}
        active={triageTab}
        onChange={(id) => {
          setTriageTab(id);
          setPage(1);
          setSelected(new Set());
        }}
      />

      {/* Sticky filter bar */}
      <div className="sticky top-0 z-10 bg-white/95 backdrop-blur-sm -mx-6 px-6 py-3 border-b border-gray-100 flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Rechercher..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setPage(1);
            }}
            className="w-full pl-9 pr-3 py-1.5 border border-gray-300 rounded-lg text-sm placeholder:text-gray-400
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        <select
          value={filterSource}
          onChange={(e) => {
            setFilterSource(e.target.value);
            setPage(1);
          }}
          className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-white
            focus:outline-none focus:ring-2 focus:ring-blue-500"
          aria-label="Filtrer par source"
        >
          <option value="">Toutes sources</option>
          {Object.entries(SOURCE_LABELS).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>

        {selected.size > 0 && (
          <div className="flex items-center gap-2 ml-auto">
            <span className="text-xs text-gray-500">{selected.size} sélectionnée(s)</span>
            <Button variant="secondary" size="sm" onClick={() => handleBulkAction('read')}>
              <Eye size={14} /> Marquer lues
            </Button>
            <Button variant="secondary" size="sm" onClick={() => handleBulkAction('dismissed')}>
              <Trash2 size={14} /> Ignorer
            </Button>
          </div>
        )}
      </div>

      {/* Active Filters Bar */}
      <ActiveFiltersBar
        filters={[
          searchQuery.trim() && {
            key: 'search',
            label: 'Recherche',
            value: searchQuery,
            onRemove: () => { setSearchQuery(''); setPage(1); },
          },
          triageTab !== 'all' && {
            key: 'triage',
            label: 'Statut',
            value: TRIAGE_TABS.find((t) => t.id === triageTab)?.label || triageTab,
            onRemove: () => { setTriageTab('all'); setPage(1); },
          },
          filterSource && {
            key: 'source',
            label: 'Source',
            value: SOURCE_LABELS[filterSource] || filterSource,
            onRemove: () => { setFilterSource(''); setPage(1); },
          },
        ].filter(Boolean)}
        total={events.length}
        filtered={totalFiltered}
        onReset={() => {
          setSearchQuery('');
          setTriageTab('all');
          setFilterSource('');
          setPage(1);
        }}
      />

      {/* Events Table */}
      {totalFiltered === 0 ? (
        <EmptyState
          icon={Bell}
          title={
            searchQuery.trim() || filterSource ? 'Aucune alerte pour ces filtres' : 'Aucune alerte'
          }
          text={
            searchQuery.trim() || filterSource
              ? 'Modifiez vos filtres ou réinitialiser la vue.'
              : 'Synchronisez pour détecter les alertes depuis toutes les briques.'
          }
          ctaLabel={searchQuery.trim() || filterSource ? 'Réinitialiser' : 'Synchroniser'}
          onCta={
            searchQuery.trim() || filterSource
              ? () => {
                  setSearchQuery('');
                  setFilterSource('');
                }
              : handleSync
          }
        />
      ) : (
        <Card>
          <Table>
            <Thead>
              <tr>
                <Th className="w-8">
                  <input
                    type="checkbox"
                    checked={selected.size === pageData.length && pageData.length > 0}
                    onChange={toggleSelectAll}
                    className="rounded border-gray-300"
                    aria-label="Selectionner tout"
                  />
                </Th>
                <Th className="w-8">Sev.</Th>
                <Th>Titre</Th>
                <Th>Source</Th>
                <Th className="text-right">Impact</Th>
                <Th>Echeance</Th>
                <Th>Statut</Th>
                {isExpert && <Th>ID</Th>}
                <Th className="text-right w-24">Actions</Th>
              </tr>
            </Thead>
            <Tbody>
              {pageData.map((evt) => {
                const isNew = evt.status === 'new';
                return (
                  <Tr
                    key={evt.id}
                    className={`${isNew ? 'bg-blue-50/30' : ''} cursor-pointer hover:bg-blue-50/40`}
                    onClick={() => setDrawerEvent(evt)}
                  >
                    <Td onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selected.has(evt.id)}
                        onChange={() => toggleSelect(evt.id)}
                        className="rounded border-gray-300"
                      />
                    </Td>
                    <Td>
                      <StatusDot status={SEVERITY_STATUS[evt.severity] || 'info'} />
                    </Td>
                    <Td className="max-w-md">
                      <div className="flex items-center gap-2">
                        {isNew && (
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0" />
                        )}
                        <div className="min-w-0">
                          <p
                            className={`truncate ${isNew ? 'font-semibold text-gray-900' : 'font-medium text-gray-800'}`}
                          >
                            {evt.title}
                          </p>
                          {evt.message && (
                            <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">
                              {evt.message}
                            </p>
                          )}
                        </div>
                      </div>
                    </Td>
                    <Td>
                      <span className="text-xs text-gray-500">
                        {SOURCE_LABELS[evt.source_type] || evt.source_type}
                      </span>
                    </Td>
                    <Td className="text-right text-sm font-medium">
                      {evt.estimated_impact_eur ? (
                        <span className="text-amber-700">
                          {Math.round(evt.estimated_impact_eur).toLocaleString('fr-FR')} EUR
                        </span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </Td>
                    <Td className="text-xs text-gray-500 whitespace-nowrap">
                      {evt.due_date || '-'}
                    </Td>
                    <Td>
                      <span
                        className={`text-xs ${isNew ? 'font-medium text-gray-900' : 'text-gray-500'}`}
                      >
                        {STATUS_LABELS[evt.status] || evt.status}
                      </span>
                    </Td>
                    {isExpert && <Td className="text-xs text-gray-400 font-mono">{evt.id}</Td>}
                    <Td className="text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1">
                        {evt.deeplink_path && (
                          <button
                            onClick={() => navigate(evt.deeplink_path)}
                            className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                            title="Ouvrir"
                            aria-label="Ouvrir le lien"
                          >
                            <ExternalLink size={14} />
                          </button>
                        )}
                        {evt.status === 'new' && (
                          <button
                            onClick={() => handlePatch(evt.id, 'read')}
                            className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                            title="Marquer lu"
                            aria-label="Marquer comme lu"
                          >
                            <Eye size={14} />
                          </button>
                        )}
                        {evt.status !== 'dismissed' && (
                          <button
                            onClick={() => handlePatch(evt.id, 'dismissed')}
                            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-50 rounded transition-colors"
                            title="Ignorer"
                            aria-label="Ignorer cette alerte"
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
          {totalFiltered > pageSize && (
            <div className="flex items-center justify-between px-4 py-2 border-t border-gray-100">
              <span className="text-xs text-gray-400">
                {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, totalFiltered)} sur {totalFiltered}
              </span>
              <Pagination
                page={page}
                pageSize={pageSize}
                total={totalFiltered}
                onChange={setPage}
              />
            </div>
          )}
        </Card>
      )}

      {/* Detail Drawer */}
      <Drawer
        open={!!drawerEvent}
        onClose={() => setDrawerEvent(null)}
        title="Détail de l'alerte"
        wide
      >
        {drawerEvent && (
          <div className="space-y-6">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <StatusDot status={SEVERITY_STATUS[drawerEvent.severity] || 'info'} />
                <span className="text-xs font-medium text-gray-500 uppercase">
                  {SEVERITY_LABEL[drawerEvent.severity] || drawerEvent.severity}
                </span>
                <span className="text-xs text-gray-400">·</span>
                <span className="text-xs text-gray-500">
                  {STATUS_LABELS[drawerEvent.status] || drawerEvent.status}
                </span>
              </div>
              <h3 className="text-lg font-semibold text-gray-900">{drawerEvent.title}</h3>
            </div>

            {drawerEvent.message && (
              <div>
                <p className="text-xs text-gray-500 font-medium uppercase mb-1">Description</p>
                <p className="text-sm text-gray-700">{drawerEvent.message}</p>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-500 font-medium uppercase mb-1">Source</p>
                <p className="text-sm text-gray-900">
                  {SOURCE_LABELS[drawerEvent.source_type] || drawerEvent.source_type}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 font-medium uppercase mb-1">Impact estime</p>
                <p className="text-sm text-gray-900">
                  {drawerEvent.estimated_impact_eur
                    ? `${Math.round(drawerEvent.estimated_impact_eur).toLocaleString('fr-FR')} EUR`
                    : 'Non estime'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 font-medium uppercase mb-1">Echeance</p>
                <p className="text-sm text-gray-900">{drawerEvent.due_date || 'Non definie'}</p>
              </div>
              {drawerEvent.site_nom && (
                <div>
                  <p className="text-xs text-gray-500 font-medium uppercase mb-1">Site</p>
                  <p className="text-sm text-gray-900">{drawerEvent.site_nom}</p>
                </div>
              )}
            </div>

            {isExpert && (
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500 font-medium uppercase mb-1">Debug</p>
                <p className="text-xs font-mono text-gray-400">ID : {drawerEvent.id}</p>
                {drawerEvent.source_id && (
                  <p className="text-xs font-mono text-gray-400">
                    Source ID : {drawerEvent.source_id}
                  </p>
                )}
                {drawerEvent.created_at && (
                  <p className="text-xs font-mono text-gray-400">Cree : {drawerEvent.created_at}</p>
                )}
              </div>
            )}

            <div className="flex items-center gap-2 pt-2 border-t border-gray-100">
              <Button
                size="sm"
                variant="primary"
                data-testid="cta-notif-create-action"
                onClick={() => {
                  setDrawerEvent(null);
                  openActionDrawer({
                    prefill: {
                      titre: drawerEvent.title,
                      type: SOURCE_LABELS[drawerEvent.source_type]?.toLowerCase() || 'autre',
                      impact_eur: drawerEvent.estimated_impact_eur || undefined,
                    },
                    siteId: drawerEvent.site_id,
                    sourceType: drawerEvent.source_type || 'manual',
                    sourceId: drawerEvent.source_id || `notif:${drawerEvent.id}`,
                    idempotencyKey: `notif:${drawerEvent.id}`,
                  });
                }}
              >
                <Plus size={14} /> Créer action
              </Button>
              {drawerEvent.deeplink_path && (
                <Button
                  size="sm"
                  onClick={() => {
                    setDrawerEvent(null);
                    navigate(drawerEvent.deeplink_path);
                  }}
                >
                  <ExternalLink size={14} /> Ouvrir
                </Button>
              )}
              {drawerEvent.status === 'new' && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handlePatch(drawerEvent.id, 'read')}
                >
                  <Eye size={14} /> Marquer lu
                </Button>
              )}
              {drawerEvent.status !== 'dismissed' && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handlePatch(drawerEvent.id, 'dismissed')}
                >
                  <X size={14} /> Ignorer
                </Button>
              )}
            </div>
          </div>
        )}
      </Drawer>
    </PageShell>
  );
}
