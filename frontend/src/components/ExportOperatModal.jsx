/**
 * PROMEOS — Export OPERAT Modal (Chantier 2)
 * Modal with year selection + preview + CSV download.
 */
import { useState } from 'react';
import { Download, FileSpreadsheet, Loader2 } from 'lucide-react';
import { useScope } from '../contexts/ScopeContext';
import { exportOperatCsv, previewOperatExport } from '../services/api';
import { Modal, Button } from '../ui';

const YEARS = [2025, 2024, 2023, 2022, 2021, 2020];

export default function ExportOperatModal({ open, onClose }) {
  const { org } = useScope();
  const [year, setYear] = useState(2025);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState(null);

  const handlePreview = async () => {
    if (!org?.id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await previewOperatExport(org.id, year);
      setPreview(data);
    } catch (err) {
      setPreview(null);
      setError(err?.response?.data?.detail || "Erreur lors de l'apercu");
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!org?.id) return;
    setDownloading(true);
    setError(null);
    try {
      const blob = await exportOperatCsv(org.id, year);
      const url = window.URL.createObjectURL(new Blob([blob]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `OPERAT_export_${org.id}_${year}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Erreur lors du telechargement');
    } finally {
      setDownloading(false);
    }
  };

  const handleClose = () => {
    setPreview(null);
    onClose();
  };

  return (
    <Modal open={open} onClose={handleClose} title="Export OPERAT (CSV)">
      <div className="space-y-4">
        <p className="text-sm text-gray-600">
          Generez un fichier CSV compatible avec la plateforme OPERAT (ADEME) pour declarer vos
          consommations energetiques.
        </p>

        {/* Year selector */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Annee de reference</label>
          <div className="flex gap-2 flex-wrap">
            {YEARS.map((y) => (
              <button
                key={y}
                onClick={() => {
                  setYear(y);
                  setPreview(null);
                }}
                className={`px-3 py-1.5 rounded text-sm font-medium transition ${
                  year === y
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {y}
              </button>
            ))}
          </div>
        </div>

        {/* Preview button */}
        <Button size="sm" variant="secondary" onClick={handlePreview} disabled={loading}>
          {loading ? (
            <Loader2 size={14} className="animate-spin mr-1" />
          ) : (
            <FileSpreadsheet size={14} className="mr-1" />
          )}
          Apercu ({year})
        </Button>

        {/* Preview table */}
        {preview && (
          <div className="border rounded-lg overflow-auto max-h-60">
            <table className="text-xs w-full">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  {(preview.columns || []).slice(0, 6).map((col) => (
                    <th
                      key={col}
                      className="px-2 py-1.5 text-left text-gray-500 font-medium whitespace-nowrap"
                    >
                      {col.replace(/_/g, ' ')}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {(preview.rows || []).map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    {(preview.columns || []).slice(0, 6).map((col) => (
                      <td key={col} className="px-2 py-1 text-gray-700 whitespace-nowrap">
                        {row[col] || '-'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="px-2 py-1 bg-gray-50 text-xs text-gray-400">
              {preview.efa_count} EFA · {preview.columns?.length} colonnes
            </div>
          </div>
        )}

        {/* Error banner */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded px-3 py-2 text-xs text-red-700">
            {error}
          </div>
        )}

        {/* Download button */}
        <div className="flex justify-end gap-2 pt-2 border-t">
          <Button size="sm" variant="secondary" onClick={handleClose}>
            Fermer
          </Button>
          <Button size="sm" onClick={handleDownload} disabled={downloading}>
            {downloading ? (
              <Loader2 size={14} className="animate-spin mr-1" />
            ) : (
              <Download size={14} className="mr-1" />
            )}
            Telecharger CSV
          </Button>
        </div>
      </div>
    </Modal>
  );
}
