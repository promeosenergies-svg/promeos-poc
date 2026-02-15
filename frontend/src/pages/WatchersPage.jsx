/**
 * PROMEOS - Regulatory Watchers Page
 * Monitor regulatory changes from Legifrance, CRE, RTE
 * Pipeline: NEW -> REVIEWED -> APPLIED | DISMISSED
 */
import { useState, useEffect } from 'react';
import { Eye, Play, RefreshCw, ExternalLink } from 'lucide-react';
import { listWatchers, runWatcher, listRegEvents, reviewRegEvent } from '../services/api';
import { PageShell, Card, CardBody, Badge, Button, EmptyState, Modal, Tabs } from '../ui';
import { SkeletonCard } from '../ui/Skeleton';
import { useToast } from '../ui/ToastProvider';

const STATUS_TABS = [
  { id: 'all', label: 'Tous' },
  { id: 'new', label: 'Nouveaux' },
  { id: 'reviewed', label: 'Revises' },
  { id: 'applied', label: 'Appliques' },
  { id: 'dismissed', label: 'Ignores' },
];

const STATUS_BADGE = {
  new: 'info',
  reviewed: 'warning',
  applied: 'ok',
  dismissed: 'neutral',
};

export default function WatchersPage() {
  const [watchers, setWatchers] = useState([]);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [runResults, setRunResults] = useState({});
  const [expandedEvent, setExpandedEvent] = useState(null);
  const [filterSource, setFilterSource] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [reviewModal, setReviewModal] = useState(null);
  const [reviewNotes, setReviewNotes] = useState('');
  const { toast } = useToast();

  useEffect(() => {
    loadData();
  }, [filterSource, filterStatus]);

  const loadData = async () => {
    setLoading(true);
    try {
      const statusParam = filterStatus === 'all' ? null : filterStatus;
      const [watchersData, eventsData] = await Promise.all([
        listWatchers(),
        listRegEvents(filterSource || null, null, statusParam)
      ]);
      setWatchers(watchersData.watchers || []);
      setEvents(eventsData.events || []);
    } catch {
      toast('Erreur lors du chargement des donnees de veille', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRunWatcher = async (watcherName) => {
    try {
      setRunResults(prev => ({ ...prev, [watcherName]: { loading: true } }));
      const result = await runWatcher(watcherName);
      setRunResults(prev => ({ ...prev, [watcherName]: result }));
      toast(`${watcherName}: ${result.new_events} nouveaux evenements`, 'success');
      setTimeout(() => loadData(), 1000);
    } catch (error) {
      setRunResults(prev => ({ ...prev, [watcherName]: { error: error.message } }));
      toast(`Erreur execution ${watcherName}`, 'error');
    }
  };

  const handleReviewSubmit = async (eventId, decision) => {
    try {
      await reviewRegEvent(eventId, decision, reviewNotes);
      setReviewModal(null);
      setReviewNotes('');
      toast(`Evenement ${decision === 'apply' ? 'applique' : 'ignore'}`, 'success');
      loadData();
    } catch {
      toast('Erreur lors de la revision', 'error');
    }
  };

  if (loading && watchers.length === 0) {
    return (
      <PageShell icon={Eye} title="Veille" subtitle="Chargement...">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <SkeletonCard /><SkeletonCard /><SkeletonCard />
        </div>
        <SkeletonCard />
      </PageShell>
    );
  }

  return (
    <PageShell
      icon={Eye}
      title="Veille"
      subtitle="Reglementaire & marche : alertes et syntheses"
      actions={
        <Button variant="secondary" onClick={loadData}>
          <RefreshCw size={14} className="mr-1.5" /> Actualiser
        </Button>
      }
    >
      {/* Watchers Section */}
      <div>
        <h2 className="text-base font-semibold text-gray-800 mb-3">Watchers Actifs</h2>
        {watchers.length === 0 ? (
          <EmptyState icon={Eye} title="Aucun watcher configure" text="Configurez vos sources de veille reglementaire." />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {watchers.map((watcher) => (
              <Card key={watcher.name} className="hover:shadow-md transition-shadow duration-200">
                <CardBody>
                  <h3 className="font-semibold text-gray-900 mb-1">{watcher.name}</h3>
                  <p className="text-sm text-gray-500 mb-3">{watcher.description}</p>

                  {runResults[watcher.name] && !runResults[watcher.name].loading && (
                    <div className={`text-xs mb-3 rounded-lg px-3 py-2 ${runResults[watcher.name].error ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
                      {runResults[watcher.name].error
                        ? `Erreur: ${runResults[watcher.name].error}`
                        : `${runResults[watcher.name].new_events} nouveaux evenements`
                      }
                    </div>
                  )}

                  <Button
                    variant="secondary"
                    className="w-full text-sm"
                    onClick={() => handleRunWatcher(watcher.name)}
                    disabled={runResults[watcher.name]?.loading}
                  >
                    {runResults[watcher.name]?.loading ? (
                      <><RefreshCw size={14} className="mr-1.5 animate-spin" /> Execution...</>
                    ) : (
                      <><Play size={14} className="mr-1.5" /> Executer</>
                    )}
                  </Button>
                </CardBody>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Events Section */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold text-gray-800">Evenements Reglementaires</h2>
          <select
            value={filterSource}
            onChange={(e) => setFilterSource(e.target.value)}
            className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-200 focus:border-blue-400"
          >
            <option value="">Toutes les sources</option>
            {watchers.map(w => (
              <option key={w.name} value={w.name}>{w.name}</option>
            ))}
          </select>
        </div>

        <Tabs
          tabs={STATUS_TABS}
          active={filterStatus}
          onChange={setFilterStatus}
        />

        <div className="mt-4">
          {events.length === 0 ? (
            <EmptyState icon={Eye} title="Aucun evenement" text="Executez un watcher pour detecter les evenements reglementaires." />
          ) : (
            <Card>
              <div className="divide-y divide-gray-100">
                {events.map((event) => (
                  <div key={event.id} className="px-5 py-4 hover:bg-gray-50 transition">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <h3 className="font-semibold text-gray-900 text-sm">{event.title}</h3>
                          <Badge status={STATUS_BADGE[event.status] || 'info'}>
                            {event.status || 'new'}
                          </Badge>
                        </div>

                        <div className="flex items-center gap-3 text-xs text-gray-500">
                          <Badge status="info">{event.source_name}</Badge>
                          {event.published_at && (
                            <span>{new Date(event.published_at).toLocaleDateString('fr-FR')}</span>
                          )}
                          {event.tags && <span className="text-gray-400">{event.tags}</span>}
                        </div>

                        {expandedEvent === event.id && (
                          <div className="mt-3 p-3 bg-gray-50 rounded-lg space-y-2">
                            <p className="text-sm text-gray-700">{event.snippet}</p>
                            {event.url && (
                              <a href={event.url} target="_blank" rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800">
                                <ExternalLink size={12} /> Lien source
                              </a>
                            )}
                            {event.review_note && (
                              <div className="p-2 bg-green-50 border border-green-200 rounded">
                                <p className="text-xs text-green-800"><strong>Note:</strong> {event.review_note}</p>
                              </div>
                            )}
                            {event.reviewed_at && (
                              <p className="text-xs text-gray-400">
                                Revise le {new Date(event.reviewed_at).toLocaleDateString('fr-FR')}
                                {event.reviewed_by && ` par ${event.reviewed_by}`}
                              </p>
                            )}
                          </div>
                        )}
                      </div>

                      <div className="flex gap-2 ml-4 shrink-0">
                        <Button
                          variant="ghost"
                          className="text-sm"
                          onClick={() => setExpandedEvent(expandedEvent === event.id ? null : event.id)}
                        >
                          {expandedEvent === event.id ? 'Masquer' : 'Details'}
                        </Button>
                        {(event.status === 'new' || !event.status) && (
                          <Button
                            className="text-sm"
                            onClick={() => { setReviewModal(event); setReviewNotes(''); }}
                          >
                            Reviser
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      </div>

      {/* Info Panel */}
      <Card className="border-yellow-200 bg-yellow-50/50">
        <CardBody>
          <h3 className="text-sm font-semibold text-yellow-800 mb-1">Stockage Minimal</h3>
          <p className="text-sm text-gray-700">
            Les watchers stockent uniquement un hash de contenu + snippet de 500 caracteres maximum.
            Aucune copie massive de contenu reglementaire n'est effectuee (conformite droits d'auteur).
          </p>
        </CardBody>
      </Card>

      {/* Review Modal */}
      <Modal open={!!reviewModal} onClose={() => setReviewModal(null)} title="Reviser l'evenement">
        {reviewModal && (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">{reviewModal.title}</p>

            {reviewModal.snippet && (
              <div className="p-3 bg-gray-50 rounded-lg text-sm text-gray-700 max-h-32 overflow-y-auto">
                {reviewModal.snippet}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
              <textarea
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-200 focus:border-blue-400"
                rows={3}
                placeholder="Notes de revision (optionnel)..."
              />
            </div>

            <div className="flex justify-end gap-3">
              <Button variant="secondary" onClick={() => setReviewModal(null)}>Annuler</Button>
              <Button variant="secondary" onClick={() => handleReviewSubmit(reviewModal.id, 'dismiss')}>Ignorer</Button>
              <Button onClick={() => handleReviewSubmit(reviewModal.id, 'apply')}>Appliquer</Button>
            </div>
          </div>
        )}
      </Modal>
    </PageShell>
  );
}
