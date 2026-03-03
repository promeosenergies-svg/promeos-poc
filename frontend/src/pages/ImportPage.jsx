/**
 * PROMEOS - Page Import de sites
 * Upload CSV + apercu + validation + import + Demo Packs
 */
import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, CheckCircle, AlertTriangle, Download, Trash2, Database, Package, RotateCcw, Loader2, RefreshCw } from 'lucide-react';
import { importSitesStandalone, seedDemoPack, getDemoPackStatus, getDemoPacks, resetDemoPack, clearApiCache } from '../services/api';
import { PageShell, Card, CardBody, Badge, Button, EmptyState, Modal } from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';
import { useToast } from '../ui/ToastProvider';
import { useScope } from '../contexts/ScopeContext';

function ImportPage() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const fileRef = useRef(null);
  const { toast } = useToast();
  const { clearScope, applyDemoScope, org, scope, scopeLabel } = useScope();
  const navigate = useNavigate();

  // Demo Packs state — fetched from backend (no hardcoded IDs)
  const [demoPacks, setDemoPacks] = useState([]);
  const [selectedPack, setSelectedPack] = useState(null);
  const [selectedSize, setSelectedSize] = useState('S');
  const [packLoading, setPackLoading] = useState(false);
  const [packResult, setPackResult] = useState(null);
  const [packStatus, setPackStatus] = useState(null);
  const [resetLoading, setResetLoading] = useState(false);
  const [showResetModal, setShowResetModal] = useState(false);
  const [statusError, setStatusError] = useState(false);

  const packDef = demoPacks.find(p => p.key === selectedPack);
  const totalRows = packStatus?.total_rows || 0;

  // Mismatch: backend has a loaded pack for a different org than current scope
  const syncInProgress = !!(
    packStatus?.org_id &&
    scope?.orgId &&
    packStatus.org_id !== scope.orgId
  );

  const refreshStatus = () => {
    getDemoPackStatus()
      .then((s) => {
        setPackStatus(s); setStatusError(false);
        // Auto-sync scope is handled by the syncInProgress useEffect below.
        // Do NOT call applyDemoScope here — it triggers setApiSites([]) and
        // can cause a race that empties orgSites right after a successful seed.
      })
      .catch(() => {
        // Do NOT reset packStatus to null — the optimistic value set after
        // seed must survive a transient status-pack fetch failure.
        setStatusError(true);
      });
  };

  useEffect(() => { refreshStatus(); }, []);

  // Fetch available packs from backend — single source of truth
  useEffect(() => {
    getDemoPacks()
      .then(data => {
        const packs = data?.packs || [];
        setDemoPacks(packs);
        // Auto-select default pack (or first available)
        const def = packs.find(p => p.is_default) || packs[0];
        if (def && !selectedPack) setSelectedPack(def.key);
      })
      .catch(() => {
        toast('Impossible de charger la liste des packs demo', 'error');
      });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-silently sync scope when mismatch is detected
  useEffect(() => {
    if (syncInProgress && packStatus?.org_id && packStatus?.org_nom) {
      applyDemoScope({ orgId: packStatus.org_id, orgNom: packStatus.org_nom });
    }
  }, [packStatus?.org_id, scope?.orgId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleFileChange = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    setFile(f);
    setResult(null);
    setError(null);

    if (f.size > 50 * 1024 * 1024) {
      setError('Fichier trop volumineux (max 50 Mo)');
      toast('Fichier trop volumineux (max 50 Mo)', 'error');
      return;
    }
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target.result;
      const lines = text.split('\n').filter(l => l.trim());
      if (lines.length === 0) {
        setError('Fichier vide ou illisible');
        toast('Fichier vide ou illisible', 'error');
        return;
      }
      const delimiter = lines[0].includes(';') ? ';' : ',';
      const headers = lines[0].split(delimiter).map(h => h.trim());
      const rows = lines.slice(1, 6).map(line =>
        line.split(delimiter).map(c => c.trim())
      );
      setPreview({ headers, rows, total: lines.length - 1 });
    };
    reader.onerror = () => {
      setError('Erreur de lecture du fichier');
      toast('Erreur de lecture du fichier', 'error');
    };
    reader.readAsText(f);
  };

  const handleImport = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const res = await importSitesStandalone(file);
      setResult(res);
      toast(`${res.imported} site${res.imported > 1 ? 's' : ''} importe${res.imported > 1 ? 's' : ''} avec succes`, 'success');
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
      toast('Erreur lors de l\'import', 'error');
    }
    setLoading(false);
  };

  /**
   * Shared seed logic — called by handleSeedPack and handleReplay.
   * @param {string} successToast  — toast message on success
   */
  const performSeed = async (successToast) => {
    setPackLoading(true);
    setPackResult(null);
    try {
      // reset=true: always wipe existing demo data before seeding a new pack
      const res = await seedDemoPack(selectedPack, selectedSize, true);
      setPackResult(res);

      // Optimistic packStatus update — don't wait for refreshStatus() to confirm.
      // This guarantees "Pack chargé: <org_nom>" is shown immediately after seed,
      // even if the subsequent getDemoPackStatus() call is delayed or fails.
      if (res.org_id) {
        setPackStatus({
          org_id: res.org_id,
          org_nom: res.org_nom,
          pack: res.pack,
          size: res.size,
          total_rows: res.total_rows ?? 0,
        });
      }

      // Invalidate stale GET cache BEFORE switching scope
      clearApiCache();

      // Switch global scope to the seeded org immediately
      if (res.org_id) {
        applyDemoScope({
          orgId: res.org_id,
          orgNom: res.org_nom,
          defaultSiteId: res.default_site_id,
          defaultSiteName: res.default_site_name,
        });
      }
      toast(successToast, 'success');
      refreshStatus(); // Async refresh — confirms/enriches packStatus from backend

      // Navigate to patrimoine to prove the switch worked
      navigate('/patrimoine');
    } catch (err) {
      const status = err.response?.status;
      const raw = err.response?.data?.detail;
      // Backend may return {message, available_packs} or a plain string
      const detail = typeof raw === 'object' ? raw.message : (raw || err.message || 'Erreur inconnue');
      toast(
        status
          ? `Echec du chargement (HTTP\u00a0${status}) — ${detail}`
          : `Echec du chargement — ${detail}`,
        'error',
      );
    }
    setPackLoading(false);
  };

  /** First load or switching packs */
  const handleSeedPack = () =>
    performSeed('Démo chargée — contexte appliqué à toute l\'application.');

  /** Re-seed the same pack (reset + replay) */
  const handleReplay = () =>
    performSeed('Démo relancée — contexte mis à jour.');

  const handleResetPack = async () => {
    setShowResetModal(false);
    setResetLoading(true);
    try {
      await resetDemoPack('hard', true);
      setPackResult(null);
      clearApiCache();
      clearScope();
      toast('Démo réinitialisée — retour à un contexte neutre.', 'success');
      refreshStatus();
    } catch (err) {
      toast(err.response?.data?.detail || 'Erreur lors du reset', 'error');
    }
    setResetLoading(false);
  };

  const clearFile = () => {
    setFile(null);
    setPreview(null);
    setResult(null);
    setError(null);
    if (fileRef.current) fileRef.current.value = '';
  };

  return (
    <PageShell
      icon={Upload}
      title="Imports"
      subtitle="Fichiers, CSV, historiques & controles"
      actions={
        <a
          href="/template_import_sites.csv"
          download
          className="inline-flex items-center gap-2 px-4 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 hover:bg-gray-50 transition"
        >
          <Download size={14} />
          Modèle CSV
        </a>
      }
    >
      {/* Demo Packs */}
      <Card className="border-indigo-200 bg-indigo-50/30">
        <CardBody>
          <div className="flex items-center gap-2 mb-3">
            <Package size={18} className="text-indigo-600" />
            <h2 className="font-semibold text-indigo-900">Demo Packs</h2>
            {totalRows > 0 && (
              <Badge status="info">{totalRows.toLocaleString('fr-FR')} lignes</Badge>
            )}
          </div>
          <p className="text-sm text-indigo-700 mb-4">
            Charger un jeu de données complet : sites, compteurs, relevés 90j, météo, conformité, monitoring, factures, actions, achat.
          </p>

          {statusError && (
            <p className="text-xs text-amber-600 mb-2">Statut demo indisponible — reset manuel possible.</p>
          )}

          {/* Status row — always visible for clarity */}
          <div className="flex flex-wrap gap-x-6 gap-y-1 mb-3 text-xs">
            <p className="text-indigo-700">
              <span className="text-indigo-400 font-semibold">Contexte actif :</span>{' '}
              {org ? (
                <strong>{org.nom}</strong>
              ) : (
                <span className="text-gray-400 italic">Aucun</span>
              )}
            </p>
            <p className="text-indigo-700">
              <span className="text-indigo-400 font-semibold">Portée :</span>{' '}
              <strong>{scopeLabel}</strong>
            </p>
            <p className="text-indigo-700">
              <span className="text-indigo-400 font-semibold">Pack chargé :</span>{' '}
              {packStatus?.org_nom ? (
                <strong>{packStatus.org_nom}</strong>
              ) : (
                <span className="text-gray-400 italic">Aucun</span>
              )}
            </p>
            <p className="text-indigo-700">
              <span className="text-indigo-400 font-semibold">Pack à charger :</span>{' '}
              <strong>{packDef?.label || selectedPack}</strong>
            </p>
            {syncInProgress && (
              <p className="text-amber-600 flex items-center gap-1">
                <Loader2 size={12} className="animate-spin" />
                Synchronisation du contexte…
              </p>
            )}
          </div>

          {/* Pack selector — from backend registry */}
          <div className="flex flex-wrap gap-3 mb-4">
            {demoPacks.map(p => {
              const isLoaded = packStatus?.pack === p.key;
              const isSelected = selectedPack === p.key;
              return (
                <button
                  key={p.key}
                  onClick={() => setSelectedPack(p.key)}
                  className={`flex-1 min-w-[200px] p-3 rounded-lg border-2 text-left transition ${
                    isSelected
                      ? 'border-indigo-500 bg-white shadow-sm'
                      : 'border-transparent bg-white/50 hover:border-indigo-200'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-gray-800 text-sm">{p.label}</p>
                    {isLoaded && (
                      <Badge status="success">Chargé</Badge>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">{p.description}</p>
                </button>
              );
            })}
          </div>

          {/* Size selector + actions */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex gap-1 bg-white rounded-lg p-0.5 border border-gray-200">
              {packDef && packDef.sizes.map(sz => (
                <button
                  key={sz}
                  onClick={() => setSelectedSize(sz)}
                  className={`px-3 py-1.5 rounded-md text-sm transition ${
                    selectedSize === sz
                      ? 'bg-indigo-600 text-white font-medium'
                      : 'text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  {sz}
                </button>
              ))}
            </div>

            <Button onClick={handleSeedPack} disabled={packLoading || resetLoading || !selectedPack}>
              {packLoading ? (
                <><Loader2 size={14} className="mr-1.5 animate-spin" />Chargement...</>
              ) : (
                <><Database size={14} className="mr-1.5" />Charger la démo</>
              )}
            </Button>

            <Button variant="secondary" onClick={() => setShowResetModal(true)} disabled={resetLoading || packLoading}>
              {resetLoading ? (
                <><Loader2 size={14} className="mr-1.5 animate-spin" />Reset...</>
              ) : (
                <><RotateCcw size={14} className="mr-1.5" />Reset</>
              )}
            </Button>

            <Button variant="secondary" onClick={handleReplay} disabled={packLoading || resetLoading || !selectedPack}>
              <RefreshCw size={14} className="mr-1.5" />Reset + relancer
            </Button>
          </div>

          {/* Pack result */}
          {packResult && packResult.status === 'ok' && (
            <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle size={16} className="text-green-600" />
                <span className="font-medium text-green-800 text-sm">
                  Pack {packResult.pack} ({packResult.size}) charge en {packResult.elapsed_s}s
                </span>
              </div>
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 text-xs">
                <div className="bg-white rounded p-2 text-center">
                  <p className="font-bold text-gray-800">{packResult.sites_count}</p>
                  <p className="text-gray-500">Sites</p>
                </div>
                <div className="bg-white rounded p-2 text-center">
                  <p className="font-bold text-gray-800">{packResult.readings_count?.toLocaleString('fr-FR')}</p>
                  <p className="text-gray-500">Releves</p>
                </div>
                <div className="bg-white rounded p-2 text-center">
                  <p className="font-bold text-gray-800">{packResult.monitoring?.alerts_count || 0}</p>
                  <p className="text-gray-500">Alertes</p>
                </div>
                <div className="bg-white rounded p-2 text-center">
                  <p className="font-bold text-gray-800">{packResult.billing?.invoices_count || 0}</p>
                  <p className="text-gray-500">Factures</p>
                </div>
                <div className="bg-white rounded p-2 text-center">
                  <p className="font-bold text-gray-800">{packResult.actions?.actions_count || 0}</p>
                  <p className="text-gray-500">Actions</p>
                </div>
                <div className="bg-white rounded p-2 text-center">
                  <p className="font-bold text-gray-800">{packResult.compliance?.findings_count || 0}</p>
                  <p className="text-gray-500">Findings</p>
                </div>
              </div>
            </div>
          )}
        </CardBody>
      </Card>

      {/* Legacy demo seed removed in V55 — HELIOS is the only official pack */}

      {/* Upload zone */}
      <div
        className={`border-2 border-dashed rounded-xl p-8 text-center transition cursor-pointer
          ${file ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'}`}
        onClick={() => !file && fileRef.current?.click()}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".csv,.txt"
          onChange={handleFileChange}
          className="hidden"
        />
        {!file ? (
          <>
            <Upload size={40} className="mx-auto text-gray-400 mb-3" />
            <p className="text-gray-600 font-medium">Cliquer pour selectionner un fichier CSV</p>
            <p className="text-sm text-gray-400 mt-1">ou glissez-deposez ici</p>
            <p className="text-xs text-gray-400 mt-2">Format: nom, adresse, code_postal, ville, surface_m2, type, naf_code</p>
          </>
        ) : (
          <div className="flex items-center justify-center gap-3">
            <FileText size={24} className="text-blue-500" />
            <span className="font-medium text-gray-700">{file.name}</span>
            <span className="text-sm text-gray-400">({(file.size / 1024).toFixed(1)} Ko)</span>
            <button onClick={(e) => { e.stopPropagation(); clearFile(); }} className="ml-4 p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition">
              <Trash2 size={16} />
            </button>
          </div>
        )}
      </div>

      {/* Preview */}
      {preview && !result && (
        <Card>
          <CardBody>
            <h2 className="font-semibold text-gray-700 mb-3">
              Apercu ({preview.total} ligne{preview.total > 1 ? 's' : ''})
            </h2>
            <div className="overflow-x-auto">
              <Table>
                <Thead>
                  <Tr>
                    {preview.headers.map((h, i) => (
                      <Th key={i}>{h}</Th>
                    ))}
                  </Tr>
                </Thead>
                <Tbody>
                  {preview.rows.map((row, ri) => (
                    <Tr key={ri}>
                      {row.map((cell, ci) => (
                        <Td key={ci}>{cell || <span className="text-gray-300">-</span>}</Td>
                      ))}
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </div>
            {preview.total > 5 && (
              <p className="text-xs text-gray-400 mt-2">... et {preview.total - 5} ligne(s) de plus</p>
            )}
            <div className="mt-4">
              <Button onClick={handleImport} disabled={loading}>
                <Upload size={14} className="mr-1.5" />
                {loading ? 'Importation en cours...' : `Importer ${preview.total} site${preview.total > 1 ? 's' : ''}`}
              </Button>
            </div>
          </CardBody>
        </Card>
      )}

      {/* Error */}
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardBody className="flex items-center gap-3">
            <AlertTriangle size={20} className="text-red-500 shrink-0" />
            <p className="text-red-700 text-sm">{error}</p>
          </CardBody>
        </Card>
      )}

      {/* Result */}
      {result && (
        <Card>
          <CardBody>
            <div className="flex items-center gap-3 mb-4">
              <CheckCircle size={24} className="text-green-500" />
              <h2 className="font-semibold text-gray-700">Import termine</h2>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="bg-green-50 rounded-lg p-4">
                <p className="text-2xl font-bold text-green-700">{result.imported}</p>
                <p className="text-sm text-green-600">sites importes</p>
              </div>
              <div className={`rounded-lg p-4 ${result.errors > 0 ? 'bg-red-50' : 'bg-gray-50'}`}>
                <p className={`text-2xl font-bold ${result.errors > 0 ? 'text-red-700' : 'text-gray-400'}`}>{result.errors}</p>
                <p className={`text-sm ${result.errors > 0 ? 'text-red-600' : 'text-gray-400'}`}>erreurs</p>
              </div>
            </div>

            {result.sites?.length > 0 && (
              <Table>
                <Thead>
                  <Tr>
                    <Th>Nom</Th>
                    <Th>Type</Th>
                    <Th>CVC (kW)</Th>
                    <Th>Obligations</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {result.sites.map((s) => (
                    <Tr key={s.id}>
                      <Td className="font-medium">{s.nom}</Td>
                      <Td><Badge status="info">{s.type}</Badge></Td>
                      <Td>{s.cvc_power_kw} kW</Td>
                      <Td>{s.obligations}</Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            )}

            {result.error_details?.length > 0 && (
              <div className="mt-4">
                <h3 className="font-medium text-red-700 mb-2">Erreurs</h3>
                {result.error_details.map((e, i) => (
                  <p key={i} className="text-sm text-red-600">Ligne {e.row}: {e.error}</p>
                ))}
              </div>
            )}

            <div className="mt-4">
              <Button variant="secondary" onClick={clearFile}>Nouvel import</Button>
            </div>
          </CardBody>
        </Card>
      )}

      {/* Empty state when nothing is happening */}
      {!file && !result && (
        <EmptyState
          icon={Upload}
          title="Pret a importer"
          text="Selectionnez un fichier CSV ci-dessus ou utilisez le mode demo pour commencer."
        />
      )}

      {/* Confirmation modal for hard reset */}
      <Modal open={showResetModal} onClose={() => setShowResetModal(false)} title="Confirmer la suppression">
        <p className="text-sm text-gray-600 mb-2">
          Cette action va supprimer <strong>toutes les données démo</strong> (sites, compteurs, relevés, factures, alertes, actions).
        </p>
        <p className="text-sm text-red-600 mb-4">
          Les données importées manuellement ne seront pas affectées (reset soft).
        </p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={() => setShowResetModal(false)}>Annuler</Button>
          <Button onClick={handleResetPack}>
            <Trash2 size={14} className="mr-1.5" />Confirmer la suppression
          </Button>
        </div>
      </Modal>
    </PageShell>
  );
}

export default ImportPage;
