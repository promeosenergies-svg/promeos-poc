/**
 * PROMEOS - Page Import de sites
 * Upload CSV + apercu + validation + import
 */
import { useState, useRef } from 'react';
import { Upload, FileText, CheckCircle, AlertTriangle, Download, Trash2, Database } from 'lucide-react';
import { importSitesStandalone, seedDemo } from '../services/api';
import { PageShell, Card, CardBody, Badge, Button, EmptyState } from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';
import { useToast } from '../ui/ToastProvider';

function ImportPage() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [seedLoading, setSeedLoading] = useState(false);
  const fileRef = useRef(null);
  const { toast } = useToast();

  const handleFileChange = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    setFile(f);
    setResult(null);
    setError(null);

    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target.result;
      const lines = text.split('\n').filter(l => l.trim());
      const delimiter = lines[0].includes(';') ? ';' : ',';
      const headers = lines[0].split(delimiter).map(h => h.trim());
      const rows = lines.slice(1, 6).map(line =>
        line.split(delimiter).map(c => c.trim())
      );
      setPreview({ headers, rows, total: lines.length - 1 });
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

  const handleSeedDemo = async () => {
    setSeedLoading(true);
    try {
      const res = await seedDemo();
      toast(`Demo chargee : ${res.sites_created} sites, ${res.compteurs_created} compteurs`, 'success');
    } catch (err) {
      toast(err.response?.data?.detail || 'Erreur lors du chargement demo', 'error');
    }
    setSeedLoading(false);
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
          Template CSV
        </a>
      }
    >
      {/* Demo seed */}
      <Card className="border-amber-200 bg-amber-50/50">
        <CardBody className="flex items-center justify-between">
          <div>
            <p className="font-medium text-amber-800">Mode demonstration</p>
            <p className="text-sm text-amber-600">Charger 3 sites demo (commerce, bureau, entrepot) avec compteurs et obligations.</p>
          </div>
          <Button
            variant="secondary"
            onClick={handleSeedDemo}
            disabled={seedLoading}
          >
            <Database size={14} className="mr-1.5" />
            {seedLoading ? 'Chargement...' : 'Charger demo'}
          </Button>
        </CardBody>
      </Card>

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
    </PageShell>
  );
}

export default ImportPage;
