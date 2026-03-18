/**
 * Bloc "Pilotabilité réelle" dans BACS / conformité.
 * Montre le lien entre classe GTB et potentiel de pilotage.
 */
import { useState, useEffect } from 'react';
import { getFlexAssets, syncBacsToFlexAssets } from '../../services/api';

export default function BacsFlexLink({ siteId }) {
  const [assets, setAssets] = useState([]);
  const [syncing, setSyncing] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadAssets = () => {
    setLoading(true);
    getFlexAssets({ site_id: siteId })
      .then((r) => setAssets(r?.assets || []))
      .catch(() => setAssets([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (siteId) loadAssets();
  }, [siteId]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await syncBacsToFlexAssets(siteId);
      loadAssets();
    } catch (e) {
      console.error(e);
    } finally {
      setSyncing(false);
    }
  };

  const bacsAssets = assets.filter((a) => a.data_source === 'bacs_sync');
  const controllable = assets.filter((a) => a.is_controllable);

  if (loading) return null;

  return (
    <div className="border rounded-lg p-3 mt-3">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-semibold text-gray-700">Pilotabilité réelle</h4>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="text-xs text-blue-600 hover:underline disabled:text-gray-400"
        >
          {syncing ? 'Synchronisation...' : 'Sync BACS → Flex'}
        </button>
      </div>

      {assets.length === 0 ? (
        <p className="text-xs text-gray-400">
          Aucun asset flex inventorié. Synchronisez depuis BACS ou ajoutez manuellement.
        </p>
      ) : (
        <div className="space-y-1">
          {assets.slice(0, 5).map((a) => (
            <div key={a.id} className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-1.5">
                <span
                  className={`w-2 h-2 rounded-full ${a.is_controllable ? 'bg-green-500' : 'bg-gray-300'}`}
                />
                <span className="text-gray-700">{a.label}</span>
                {a.gtb_class && <span className="text-gray-400">GTB {a.gtb_class}</span>}
              </div>
              <span className="text-gray-500">{a.power_kw ? `${a.power_kw} kW` : '—'}</span>
            </div>
          ))}
          <div className="text-xs text-gray-400 mt-1">
            {controllable.length}/{assets.length} confirmé{controllable.length !== 1 ? 's' : ''}{' '}
            pilotable{controllable.length !== 1 ? 's' : ''}
            {bacsAssets.length > 0 && ` · ${bacsAssets.length} depuis BACS`}
          </div>
        </div>
      )}
    </div>
  );
}
