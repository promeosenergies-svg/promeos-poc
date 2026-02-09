/**
 * PROMEOS - Regulatory Watchers Page
 * Monitor regulatory changes from Légifrance, CRE, RTE
 */
import { useState, useEffect } from 'react';
import { listWatchers, runWatcher, listRegEvents, reviewRegEvent } from '../services/api';

export default function WatchersPage() {
  const [watchers, setWatchers] = useState([]);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [runResults, setRunResults] = useState({});
  const [expandedEvent, setExpandedEvent] = useState(null);
  const [filterSource, setFilterSource] = useState('');
  const [filterReviewed, setFilterReviewed] = useState('');

  useEffect(() => {
    loadData();
  }, [filterSource, filterReviewed]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [watchersData, eventsData] = await Promise.all([
        listWatchers(),
        listRegEvents(filterSource, filterReviewed === 'true' ? true : filterReviewed === 'false' ? false : null)
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
      // Reload events after running watcher
      setTimeout(() => loadData(), 1000);
    } catch (error) {
      setRunResults(prev => ({ ...prev, [watcherName]: { error: error.message } }));
    }
  };

  const handleReview = async (eventId) => {
    const note = prompt('Note de révision (optionnel):');
    try {
      await reviewRegEvent(eventId, note || '');
      loadData(); // Reload to show updated status
    } catch (error) {
      console.error('Error reviewing event:', error);
      alert('Erreur lors de la révision');
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
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Veille Réglementaire</h1>
          <p className="text-gray-600">
            Surveillance automatique des changements réglementaires (Légifrance, CRE, RTE)
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
                      <p className="text-blue-600">Exécution en cours...</p>
                    ) : runResults[watcher.name].error ? (
                      <p className="text-red-600">Erreur: {runResults[watcher.name].error}</p>
                    ) : (
                      <p className="text-green-600">
                        ✓ {runResults[watcher.name].new_events} nouveaux événements
                      </p>
                    )}
                  </div>
                )}

                <button
                  onClick={() => handleRunWatcher(watcher.name)}
                  className="w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm"
                  disabled={runResults[watcher.name]?.loading}
                >
                  Exécuter Maintenant
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Events Section */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-800">Événements Réglementaires</h2>
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
              <select
                value={filterReviewed}
                onChange={(e) => setFilterReviewed(e.target.value)}
                className="px-3 py-1 border border-gray-300 rounded text-sm"
              >
                <option value="">Tous les statuts</option>
                <option value="false">Non révisés</option>
                <option value="true">Révisés</option>
              </select>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow overflow-hidden">
            {events.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                Aucun événement trouvé
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {events.map((event) => (
                  <div key={event.id} className="p-4 hover:bg-gray-50">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-semibold text-gray-800">{event.title}</h3>
                          {event.reviewed && (
                            <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded">
                              ✓ Révisé
                            </span>
                          )}
                        </div>

                        <div className="flex items-center gap-3 text-sm text-gray-600 mb-2">
                          <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">
                            {event.source_name}
                          </span>
                          {event.published_at && (
                            <span>📅 {new Date(event.published_at).toLocaleDateString('fr-FR')}</span>
                          )}
                          {event.tags && (
                            <span className="text-xs">
                              🏷️ {event.tags}
                            </span>
                          )}
                        </div>

                        {expandedEvent === event.id && (
                          <div className="mt-3 p-3 bg-gray-50 rounded">
                            <p className="text-sm text-gray-700 mb-2">{event.snippet}</p>
                            {event.url && (
                              <a
                                href={event.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sm text-blue-500 hover:text-blue-700"
                              >
                                🔗 Lien source →
                              </a>
                            )}
                            {event.review_note && (
                              <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded">
                                <p className="text-xs text-green-800">
                                  <strong>Note:</strong> {event.review_note}
                                </p>
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      <div className="flex gap-2 ml-4">
                        <button
                          onClick={() => setExpandedEvent(expandedEvent === event.id ? null : event.id)}
                          className="px-3 py-1 text-sm text-blue-500 hover:text-blue-700"
                        >
                          {expandedEvent === event.id ? 'Masquer' : 'Détails'}
                        </button>
                        {!event.reviewed && (
                          <button
                            onClick={() => handleReview(event.id)}
                            className="px-3 py-1 text-sm bg-green-500 text-white rounded hover:bg-green-600"
                          >
                            Marquer révisé
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

        {/* Info Panel */}
        <div className="mt-8 bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-yellow-800 mb-2">⚠️ Stockage Minimal</h3>
          <p className="text-sm text-gray-700">
            Les watchers stockent uniquement un hash de contenu + snippet de 500 caractères maximum.
            Aucune copie massive de contenu réglementaire n'est effectuée (conformité droits d'auteur).
          </p>
        </div>
      </div>
    </div>
  );
}
