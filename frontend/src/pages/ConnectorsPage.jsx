/**
 * PROMEOS - Connectors Management Page
 * Test and sync external data connectors (RTE, PVGIS, Enedis, MeteoFrance)
 */
import { useState, useEffect } from 'react';
import { listConnectors, testConnector, syncConnector } from '../services/api';

export default function ConnectorsPage() {
  const [connectors, setConnectors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [testResults, setTestResults] = useState({});
  const [syncResults, setSyncResults] = useState({});

  useEffect(() => {
    loadConnectors();
  }, []);

  const loadConnectors = async () => {
    setLoading(true);
    try {
      const data = await listConnectors();
      setConnectors(data.connectors || []);
    } catch (error) {
      console.error('Error loading connectors:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTest = async (connectorName) => {
    try {
      setTestResults(prev => ({ ...prev, [connectorName]: { loading: true } }));
      const result = await testConnector(connectorName);
      setTestResults(prev => ({ ...prev, [connectorName]: result }));
    } catch (error) {
      setTestResults(prev => ({ ...prev, [connectorName]: { status: 'error', message: error.message } }));
    }
  };

  const handleSync = async (connectorName) => {
    const objectType = prompt('Object type (site, meter, batiment):');
    const objectId = prompt('Object ID:');

    if (!objectType || !objectId) return;

    try {
      setSyncResults(prev => ({ ...prev, [connectorName]: { loading: true } }));
      const result = await syncConnector(connectorName, objectType, parseInt(objectId));
      setSyncResults(prev => ({ ...prev, [connectorName]: result }));
    } catch (error) {
      setSyncResults(prev => ({ ...prev, [connectorName]: { error: error.message } }));
    }
  };

  const getAuthBadge = (requiresAuth) => {
    if (requiresAuth) {
      return <span className="px-2 py-1 bg-orange-100 text-orange-700 text-xs rounded">🔒 Auth Required</span>;
    }
    return <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded">🌐 Public</span>;
  };

  const getTestStatusBadge = (result) => {
    if (result?.loading) {
      return <span className="text-blue-500">Testing...</span>;
    }
    if (result?.status === 'ok') {
      return <span className="text-green-600">✓ OK</span>;
    }
    if (result?.status === 'error') {
      return <span className="text-red-600">✗ Error</span>;
    }
    return null;
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
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Connecter des sources</h1>
          <p className="text-gray-600">
            Gestion des connexions aux APIs externes (RTE, PVGIS, Enedis, Météo-France)
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {connectors.map((connector) => (
            <div key={connector.name} className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-gray-800">{connector.name}</h3>
                  <p className="text-sm text-gray-600 mt-1">{connector.description}</p>
                </div>
              </div>

              <div className="mb-4">
                {getAuthBadge(connector.requires_auth)}
              </div>

              {/* Test Result */}
              {testResults[connector.name] && (
                <div className="mb-4 p-3 bg-gray-50 rounded">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Test Status:</span>
                    {getTestStatusBadge(testResults[connector.name])}
                  </div>
                  {testResults[connector.name].message && (
                    <p className="text-xs text-gray-600 mt-1">{testResults[connector.name].message}</p>
                  )}
                </div>
              )}

              {/* Sync Result */}
              {syncResults[connector.name] && (
                <div className="mb-4 p-3 bg-blue-50 rounded">
                  {syncResults[connector.name].loading ? (
                    <p className="text-sm text-blue-600">Synchronization en cours...</p>
                  ) : syncResults[connector.name].error ? (
                    <p className="text-sm text-red-600">Erreur: {syncResults[connector.name].error}</p>
                  ) : (
                    <div className="text-sm">
                      <p className="font-medium text-blue-800">✓ Synchronisé</p>
                      <p className="text-gray-600">
                        {syncResults[connector.name].datapoints_created} datapoints créés
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2">
                <button
                  onClick={() => handleTest(connector.name)}
                  className="flex-1 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm"
                  disabled={testResults[connector.name]?.loading}
                >
                  Test Connection
                </button>
                <button
                  onClick={() => handleSync(connector.name)}
                  className="flex-1 px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 text-sm"
                  disabled={syncResults[connector.name]?.loading}
                >
                  Sync Data
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Info Panel */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-800 mb-2">ℹ️ À propos des Connecteurs</h3>
          <ul className="text-sm text-gray-700 space-y-2">
            <li>
              <strong>RTE eCO2mix:</strong> Intensité CO2 du réseau électrique français (API publique)
            </li>
            <li>
              <strong>PVGIS:</strong> Estimations de production photovoltaïque (EU JRC, API publique)
            </li>
            <li>
              <strong>Enedis DataConnect:</strong> Données de consommation des compteurs Linky (OAuth requis)
            </li>
            <li>
              <strong>Météo-France:</strong> Données météorologiques historiques (API key requis)
            </li>
          </ul>
          <p className="text-xs text-gray-600 mt-4">
            Les connecteurs avec authentification nécessitent des variables d'environnement (.env).
            Voir la documentation pour plus de détails.
          </p>
        </div>
      </div>
    </div>
  );
}
