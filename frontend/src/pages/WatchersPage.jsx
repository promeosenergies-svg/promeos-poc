/**
 * PROMEOS - Regulatory Watchers Page
 * Monitor regulatory changes from Legifrance, CRE, RTE
 * Pipeline: NEW -> REVIEWED -> APPLIED | DISMISSED
 */
import { useState, useEffect } from 'react';
import { listWatchers, runWatcher, listRegEvents, reviewRegEvent } from '../services/api';

const STATUS_TABS = [
  { key: null, label: 'Tous' },
  { key: 'new', label: 'Nouveaux' },
  { key: 'reviewed', label: 'Revises' },
  { key: 'applied', label: 'Appliques' },
  { key: 'dismissed', label: 'Ignores' },
];

const STATUS_BADGE = {
  new: 'bg-blue-100 text-blue-700',
  reviewed: 'bg-amber-100 text-amber-700',
  applied: 'bg-green-100 text-green-700',
  dismissed: 'bg-gray-100 text-gray-500',
};

export default function WatchersPage() {
  const [watchers, setWatchers] = useState([]);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [runResults, setRunResults] = useState({});
  const [expandedEvent, setExpandedEvent] = useState(null);
  const [filterSource, setFilterSource] = useState('');
  const [filterStatus, setFilterStatus] = useState(null);
  const [reviewModal, setReviewModal] = useState(null);
  const [reviewNotes, setReviewNotes] = useState('');

  useEffect(() => {
    loadData();
  }, [filterSource, filterStatus]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [watchersData, eventsData] = await Promise.all([
        listWatchers(),
        listRegEvents(filterSource || null, null, filterStatus)
      ]);

      setWatchers(watchersData.watchers || []);
      setEvents(eventsData.events || []);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRunWatcher = async (watcherName) => {
    try {
      setRunResults(prev => ({ ...prev, [watcherName]: { loading: true } }));
      const result = await runWatcher(watcherName);
      setRunResults(prev => ({ ...prev, [watcherName]: result }));
      setTimeout(() => loadData(), 1000);
    } catch (error) {
      setRunResults(prev => ({ ...prev, [watcherName]: { error: error.message } }));
    }
  };

  const handleReviewSubmit = async (eventId, decision) => {
    try {
      await reviewRegEvent(eventId, decision, reviewNotes);
      setReviewModal(null);
      setReviewNotes('');
      loadData();
    } catch (error) {
      console.error('Error reviewing event:', error);
      alert('Erreur lors de la revision');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Veille</h1>
          <p className="text-gray-600">
            Reglementaire & marche : alertes et syntheses
          </p>
        </div>

        {/* Watchers Section */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">Watchers Actifs</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {watchers.map((watcher) => (
              <div key={watcher.name} className="bg-white rounded-lg shadow p-4">
                <div className="mb-3">
                  <h3 className="font-semibold text-gray-800">{watcher.name}</h3>
                  <p className="text-sm text-gray-600">{watcher.description}</p>
                </div>

                {runResults[watcher.name] && (
                  <div className="mb-3 p-2 bg-blue-50 rounded text-sm">
                    {runResults[watcher.name].loading ? (
                      <p className="text-blue-600">Execution en cours...</p>
                    ) : runResults[watcher.name].error ? (
                      <p className="text-red-600">Erreur: {runResults[watcher.name].error}</p>
                    ) : (
                      <p className="text-green-600">
                        {runResults[watcher.name].new_events} nouveaux evenements
                      </p>
                    )}
                  </div>
                )}

                <button
                  onClick={() => handleRunWatcher(watcher.name)}
                  className="w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm"
                  disabled={runResults[watcher.name]?.loading}
                >
                  Executer Maintenant
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Events Section */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-800">Evenements Reglementaires</h2>
            <div className="flex gap-3">
              <select
                value={filterSource}
                onChange={(e) => setFilterSource(e.target.value)}
                className="px-3 py-1 border border-gray-300 rounded text-sm"
              >
                <option value="">Toutes les sources</option>
                {watchers.map(w => (
                  <option key={w.name} value={w.name}>{w.name}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Status tabs */}
          <div className="flex gap-1 mb-4 border-b border-gray-200">
            {STATUS_TABS.map(tab => (
              <button
                key={tab.key || 'all'}
                onClick={() => setFilterStatus(tab.key)}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                  filterStatus === tab.key
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="bg-white rounded-lg shadow overflow-hidden">
            {events.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                Aucun evenement trouve
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {events.map((event) => (
                  <div key={event.id} className="p-4 hover:bg-gray-50">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-semibold text-gray-800">{event.title}</h3>
                          <span className={`px-2 py-0.5 text-xs rounded font-medium ${STATUS_BADGE[event.status] || STATUS_BADGE.new}`}>
                            {event.status || 'new'}
                          </span>
                        </div>

                        <div className="flex items-center gap-3 text-sm text-gray-600 mb-2">
                          <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">
                            {event.source_name}
                          </span>
                          {event.published_at && (
                            <span>{new Date(event.published_at).toLocaleDateString('fr-FR')}</span>
                          )}
                          {event.tags && (
                            <span className="text-xs text-gray-400">{event.tags}</span>
                          )}
                          {event.dedup_key && (
                            <span className="text-xs text-gray-300 font-mono truncate max-w-32" title={event.dedup_key}>
                              {event.dedup_key.slice(0, 12)}...
                            </span>
                          )}
                        </div>

                        {expandedEvent === event.id && (
                          <div className="mt-3 p-3 bg-gray-50 rounded space-y-2">
                            <p className="text-sm text-gray-700">{event.snippet}</p>
                            {event.url && (
                              <a
                                href={event.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sm text-blue-500 hover:text-blue-700"
                              >
                                Lien source
                              </a>
                            )}
                            {event.review_note && (
                              <div className="p-2 bg-green-50 border border-green-200 rounded">
                                <p className="text-xs text-green-800">
                                  <strong>Note:</strong> {event.review_note}
                                </p>
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

                      <div className="flex gap-2 ml-4">
                        <button
                          onClick={() => setExpandedEvent(expandedEvent === event.id ? null : event.id)}
                          className="px-3 py-1 text-sm text-blue-500 hover:text-blue-700"
                        >
                          {expandedEvent === event.id ? 'Masquer' : 'Details'}
                        </button>
                        {(event.status === 'new' || !event.status) && (
                          <button
                            onClick={() => { setReviewModal(event); setReviewNotes(''); }}
                            className="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
                          >
                            Reviser
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Review Modal */}
        {reviewModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-lg mx-4">
              <h3 className="text-lg font-bold text-gray-900 mb-2">Reviser l'evenement</h3>
              <p className="text-sm text-gray-600 mb-4">{reviewModal.title}</p>

              {reviewModal.snippet && (
                <div className="p-3 bg-gray-50 rounded mb-4 text-sm text-gray-700 max-h-32 overflow-y-auto">
                  {reviewModal.snippet}
                </div>
              )}

              <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
              <textarea
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-4"
                rows={3}
                placeholder="Notes de revision (optionnel)..."
              />

              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setReviewModal(null)}
                  className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
                >
                  Annuler
                </button>
                <button
                  onClick={() => handleReviewSubmit(reviewModal.id, 'dismiss')}
                  className="px-4 py-2 text-sm bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
                >
                  Ignorer
                </button>
                <button
                  onClick={() => handleReviewSubmit(reviewModal.id, 'apply')}
                  className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Appliquer
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Info Panel */}
        <div className="mt-8 bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-yellow-800 mb-2">Stockage Minimal</h3>
          <p className="text-sm text-gray-700">
            Les watchers stockent uniquement un hash de contenu + snippet de 500 caracteres maximum.
            Aucune copie massive de contenu reglementaire n'est effectuee (conformite droits d'auteur).
          </p>
        </div>
      </div>
    </div>
  );
}
