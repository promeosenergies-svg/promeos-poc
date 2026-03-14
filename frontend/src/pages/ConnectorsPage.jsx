/**
 * PROMEOS - Connectors Management Page
 * Test and sync external data connectors (RTE, PVGIS, Enedis, MeteoFrance)
 */
import { useState, useEffect } from 'react';
import { Link2, Play, RefreshCw, CheckCircle, XCircle, Lock, Globe } from 'lucide-react';
import { listConnectors, testConnector, syncConnector } from '../services/api';
import { PageShell, Card, CardBody, Badge, Button, EmptyState, Modal, Input, Select } from '../ui';
import { SkeletonCard } from '../ui/Skeleton';
import { useToast } from '../ui/ToastProvider';

const SYNC_OBJECT_TYPES = [
  { value: 'site', label: 'Site' },
  { value: 'meter', label: 'Compteur' },
  { value: 'batiment', label: 'Bâtiment' },
];

/** Display labels business-friendly pour les connecteurs */
const CONNECTOR_LABELS = {
  rte_eco2mix: 'RTE éCO2mix',
  pvgis: 'PVGIS — Production photovoltaïque',
  meteofrance: 'Météo-France',
  enedis_opendata: 'Open Data Enedis',
  enedis_dataconnect: 'Enedis DataConnect',
};

export default function ConnectorsPage() {
  const [connectors, setConnectors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [testResults, setTestResults] = useState({});
  const [syncResults, setSyncResults] = useState({});
  const [syncModal, setSyncModal] = useState(null);
  const [syncForm, setSyncForm] = useState({ objectType: 'site', objectId: '' });
  const { toast } = useToast();

  useEffect(() => {
    loadConnectors();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadConnectors = async () => {
    setLoading(true);
    try {
      const data = await listConnectors();
      setConnectors(data.connectors || []);
    } catch {
      toast('Erreur lors du chargement des connecteurs', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleTest = async (connectorName) => {
    try {
      setTestResults((prev) => ({ ...prev, [connectorName]: { loading: true } }));
      const result = await testConnector(connectorName);
      setTestResults((prev) => ({ ...prev, [connectorName]: result }));
      if (result?.status === 'ok') {
        toast(`${CONNECTOR_LABELS[connectorName] || connectorName} : connexion OK`, 'success');
      }
    } catch (error) {
      setTestResults((prev) => ({
        ...prev,
        [connectorName]: { status: 'error', message: error.message },
      }));
      toast(`${CONNECTOR_LABELS[connectorName] || connectorName} : échec du test`, 'error');
    }
  };

  const handleSyncSubmit = async () => {
    if (!syncModal || !syncForm.objectId) return;
    const connectorName = syncModal;
    try {
      setSyncResults((prev) => ({ ...prev, [connectorName]: { loading: true } }));
      setSyncModal(null);
      const result = await syncConnector(
        connectorName,
        syncForm.objectType,
        parseInt(syncForm.objectId)
      );
      setSyncResults((prev) => ({ ...prev, [connectorName]: result }));
      const label = CONNECTOR_LABELS[connectorName] || connectorName;
      toast(`${label} : ${result.datapoints_created || 0} points synchronisés`, 'success');
    } catch (error) {
      setSyncResults((prev) => ({ ...prev, [connectorName]: { error: error.message } }));
      toast(
        `Erreur de synchronisation ${CONNECTOR_LABELS[connectorName] || connectorName}`,
        'error'
      );
    }
  };

  const getStatusIcon = (result) => {
    if (!result) return null;
    if (result.loading) return <RefreshCw size={16} className="text-blue-500 animate-spin" />;
    if (result.status === 'ok') return <CheckCircle size={16} className="text-green-600" />;
    if (result.status === 'error') return <XCircle size={16} className="text-red-500" />;
    return null;
  };

  if (loading) {
    return (
      <PageShell icon={Link2} title="Connexions" subtitle="Chargement...">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </PageShell>
    );
  }

  return (
    <PageShell
      icon={Link2}
      title="Connexions"
      subtitle="Sources : Enedis, GRDF, fournisseurs, GTB, IoT..."
      actions={
        <Button variant="secondary" onClick={loadConnectors}>
          <RefreshCw size={14} className="mr-1.5" /> Actualiser
        </Button>
      }
    >
      {connectors.length === 0 ? (
        <EmptyState
          icon={Link2}
          title="Aucun connecteur configuré"
          text="Les connecteurs permettent de synchroniser automatiquement les données depuis Enedis, RTE, PVGIS et Météo-France."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {connectors.map((connector) => (
            <Card key={connector.name} className="hover:shadow-md transition-shadow duration-200">
              <CardBody>
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-base font-semibold text-gray-900">
                      {CONNECTOR_LABELS[connector.name] || connector.name}
                    </h3>
                    <p className="text-sm text-gray-500 mt-1">{connector.description}</p>
                  </div>
                  {getStatusIcon(testResults[connector.name])}
                </div>

                <div className="mb-4">
                  {connector.requires_auth ? (
                    <Badge status="warning">
                      <Lock size={10} className="mr-1" /> Authentification requise
                    </Badge>
                  ) : (
                    <Badge status="ok">
                      <Globe size={10} className="mr-1" /> Public
                    </Badge>
                  )}
                  {connector.requires_auth && (
                    <p className="text-[10px] text-gray-400 mt-1">
                      En démo, les données sont simulées — aucune authentification nécessaire.
                    </p>
                  )}
                </div>

                {testResults[connector.name]?.message && (
                  <p className="text-xs text-gray-500 mb-3 bg-gray-50 rounded-lg px-3 py-2">
                    {testResults[connector.name].message}
                  </p>
                )}

                {syncResults[connector.name] && !syncResults[connector.name].loading && (
                  <div
                    className={`text-xs mb-3 rounded-lg px-3 py-2 ${syncResults[connector.name].error ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}
                  >
                    {syncResults[connector.name].error
                      ? `Erreur: ${syncResults[connector.name].error}`
                      : `${syncResults[connector.name].datapoints_created || 0} points de données créés`}
                  </div>
                )}

                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    className="flex-1 text-sm"
                    onClick={() => handleTest(connector.name)}
                    disabled={testResults[connector.name]?.loading}
                  >
                    <Play size={14} className="mr-1" /> Tester
                  </Button>
                  <Button
                    className="flex-1 text-sm"
                    onClick={() => {
                      setSyncModal(connector.name);
                      setSyncForm({ objectType: 'site', objectId: '' });
                    }}
                    disabled={syncResults[connector.name]?.loading}
                  >
                    <RefreshCw size={14} className="mr-1" /> Synchroniser
                  </Button>
                </div>
              </CardBody>
            </Card>
          ))}
        </div>
      )}

      {/* Info panel */}
      <Card className="mt-6 border-blue-200 bg-blue-50/50">
        <CardBody>
          <h3 className="text-sm font-semibold text-blue-800 mb-2">À propos des Connecteurs</h3>
          <ul className="text-sm text-gray-700 space-y-1.5">
            <li>
              <strong>RTE eCO2mix:</strong> Intensité CO2 du réseau électrique français (API
              publique)
            </li>
            <li>
              <strong>PVGIS:</strong> Estimations de production photovoltaïque (EU JRC, API
              publique)
            </li>
            <li>
              <strong>Enedis DataConnect:</strong> Données de consommation des compteurs Linky
              (OAuth requis)
            </li>
            <li>
              <strong>Météo-France:</strong> Données météorologiques historiques (clé API requise)
            </li>
          </ul>
        </CardBody>
      </Card>

      {/* Sync Modal — replaces native prompt() */}
      <Modal
        open={!!syncModal}
        onClose={() => setSyncModal(null)}
        title={`Synchroniser — ${syncModal}`}
      >
        <div className="space-y-4">
          <Select
            label="Type d'objet"
            value={syncForm.objectType}
            onChange={(e) => setSyncForm((prev) => ({ ...prev, objectType: e.target.value }))}
            options={SYNC_OBJECT_TYPES}
          />
          <Input
            label="ID de l'objet"
            type="number"
            value={syncForm.objectId}
            onChange={(e) => setSyncForm((prev) => ({ ...prev, objectId: e.target.value }))}
            placeholder="Ex: 1"
          />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={() => setSyncModal(null)}>
              Annuler
            </Button>
            <Button onClick={handleSyncSubmit} disabled={!syncForm.objectId}>
              Synchroniser
            </Button>
          </div>
        </div>
      </Modal>
    </PageShell>
  );
}
