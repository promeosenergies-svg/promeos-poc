/**
 * PROMEOS - Page Import de sites
 * Upload CSV + apercu + validation + import
 */
import { useState, useRef } from 'react';
import { Upload, FileText, CheckCircle, AlertTriangle, Download, Trash2 } from 'lucide-react';
import { importSitesStandalone, seedDemo } from '../services/api';

function ImportPage() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [seedLoading, setSeedLoading] = useState(false);
  const [seedResult, setSeedResult] = useState(null);
  const fileRef = useRef(null);

  const handleFileChange = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    setFile(f);
    setResult(null);
    setError(null);

    // Parse preview (first 5 lines)
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
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
    setLoading(false);
  };

  const handleSeedDemo = async () => {
    setSeedLoading(true);
    setSeedResult(null);
    try {
      const res = await seedDemo();
      setSeedResult(res);
    } catch (err) {
      setSeedResult({ error: err.response?.data?.detail || err.message });
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
    <div className="max-w-5xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold text-gray-800 mb-2">Imports</h1>
      <p className="text-gray-500 mb-8">Fichiers, CSV, historiques & contrôles</p>

      {/* Demo seed button */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-8 flex items-center justify-between">
        <div>
          <p className="font-medium text-amber-800">Mode demonstration</p>
          <p className="text-sm text-amber-600">Charger 3 sites demo (commerce, bureau, entrepot) avec compteurs et obligations.</p>
        </div>
        <button
          onClick={handleSeedDemo}
          disabled={seedLoading}
          className="px-4 py-2 bg-amber-500 text-white rounded-lg text-sm font-semibold hover:bg-amber-600 disabled:opacity-50 transition whitespace-nowrap"
        >
          {seedLoading ? 'Chargement...' : 'Charger demo'}
        </button>
      </div>

      {seedResult && (
        <div className={`rounded-lg p-4 mb-6 ${seedResult.error ? 'bg-red-50 border border-red-200' : 'bg-green-50 border border-green-200'}`}>
          {seedResult.error ? (
            <p className="text-red-700 text-sm">{seedResult.error}</p>
          ) : (
            <p className="text-green-700 text-sm">
              Demo chargee : {seedResult.sites_created} sites, {seedResult.compteurs_created} compteurs, {seedResult.entites_juridiques} entites juridiques.
            </p>
          )}
        </div>
      )}

      {/* CSV Template download */}
      <div className="flex items-center gap-4 mb-6">
        <a
          href="/template_import_sites.csv"
          download
          className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50 transition"
        >
          <Download size={16} />
          Telecharger le template CSV
        </a>
        <span className="text-xs text-gray-400">Format: nom, adresse, code_postal, ville, surface_m2, type, naf_code</span>
      </div>

      {/* Upload zone */}
      <div
        className={`border-2 border-dashed rounded-xl p-8 text-center mb-6 transition ${
          file ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
        }`}
        onClick={() => !file && fileRef.current?.click()}
        style={{ cursor: file ? 'default' : 'pointer' }}
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
          </>
        ) : (
          <div className="flex items-center justify-center gap-3">
            <FileText size={24} className="text-blue-500" />
            <span className="font-medium text-gray-700">{file.name}</span>
            <span className="text-sm text-gray-400">({(file.size / 1024).toFixed(1)} Ko)</span>
            <button onClick={clearFile} className="ml-4 p-1 text-gray-400 hover:text-red-500">
              <Trash2 size={16} />
            </button>
          </div>
        )}
      </div>

      {/* Preview */}
      {preview && !result && (
        <div className="bg-white rounded-lg shadow p-5 mb-6">
          <h2 className="font-semibold text-gray-700 mb-3">
            Apercu ({preview.total} ligne{preview.total > 1 ? 's' : ''} detectee{preview.total > 1 ? 's' : ''})
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b-2 border-gray-200">
                  {preview.headers.map((h, i) => (
                    <th key={i} className="text-left px-3 py-2 text-gray-500 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.rows.map((row, ri) => (
                  <tr key={ri} className="border-b border-gray-100">
                    {row.map((cell, ci) => (
                      <td key={ci} className="px-3 py-2 text-gray-700">{cell || <span className="text-gray-300">-</span>}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {preview.total > 5 && (
            <p className="text-xs text-gray-400 mt-2">... et {preview.total - 5} ligne(s) de plus</p>
          )}

          <button
            onClick={handleImport}
            disabled={loading}
            className="mt-4 px-6 py-2.5 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 transition flex items-center gap-2"
          >
            {loading ? (
              <>Importation en cours...</>
            ) : (
              <>
                <Upload size={16} />
                Importer {preview.total} site{preview.total > 1 ? 's' : ''}
              </>
            )}
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 flex items-center gap-3">
          <AlertTriangle size={20} className="text-red-500" />
          <p className="text-red-700 text-sm">{error}</p>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="bg-white rounded-lg shadow p-5">
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
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b-2 border-gray-200">
                    <th className="text-left px-3 py-2">Nom</th>
                    <th className="text-left px-3 py-2">Type</th>
                    <th className="text-left px-3 py-2">CVC (kW)</th>
                    <th className="text-left px-3 py-2">Obligations</th>
                  </tr>
                </thead>
                <tbody>
                  {result.sites.map((s) => (
                    <tr key={s.id} className="border-b border-gray-100">
                      <td className="px-3 py-2 font-medium">{s.nom}</td>
                      <td className="px-3 py-2">
                        <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">{s.type}</span>
                      </td>
                      <td className="px-3 py-2">{s.cvc_power_kw} kW</td>
                      <td className="px-3 py-2">{s.obligations}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {result.error_details?.length > 0 && (
            <div className="mt-4">
              <h3 className="font-medium text-red-700 mb-2">Erreurs</h3>
              {result.error_details.map((e, i) => (
                <p key={i} className="text-sm text-red-600">Ligne {e.row}: {e.error}</p>
              ))}
            </div>
          )}

          <button
            onClick={clearFile}
            className="mt-4 px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50 transition"
          >
            Nouvel import
          </button>
        </div>
      )}
    </div>
  );
}

export default ImportPage;
