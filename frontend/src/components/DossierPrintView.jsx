/**
 * PROMEOS — DossierPrintView (Étape 5)
 * Printable HTML view for a source dossier.
 * Renders inside a Drawer; uses window.print() for export.
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { Printer, FileText, AlertTriangle, CheckCircle, Clock, Paperclip, X, ExternalLink } from 'lucide-react';
import Drawer from '../ui/Drawer';
import { Badge, Button } from '../ui';
import { buildDossier, STATUS_LABELS_FR, PRIORITY_LABELS_FR } from '../models/dossierModel';
import { SOURCE_LABELS_FR } from '../models/evidenceRules';
import { getActionsList, getActionEvidence } from '../services/api';

const STATUS_DOT = {
  open: 'bg-gray-400',
  in_progress: 'bg-amber-500',
  done: 'bg-green-500',
  blocked: 'bg-blue-500',
  false_positive: 'bg-red-400',
};

/**
 * @param {{ open, onClose, sourceType, sourceId, sourceLabel?, siteLabel?, orgLabel?, period? }} props
 */
export default function DossierPrintView({ open, onClose, sourceType, sourceId, sourceLabel, siteLabel, orgLabel, period }) {
  const [actions, setActions] = useState([]);
  const [evidenceMap, setEvidenceMap] = useState(new Map());
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(async () => {
    if (!sourceType || !sourceId) return;
    setLoading(true);
    try {
      const allActions = await getActionsList({ source_type: sourceType });
      const linked = allActions.filter((a) => a.source_id === sourceId);
      setActions(linked);

      // Fetch evidence for each linked action
      const evMap = new Map();
      const results = await Promise.allSettled(
        linked.map((a) => getActionEvidence(a.id).then((ev) => [a.id, ev])),
      );
      for (const r of results) {
        if (r.status === 'fulfilled') {
          const [id, ev] = r.value;
          evMap.set(id, ev);
        }
      }
      setEvidenceMap(evMap);
    } catch {
      /* graceful degradation */
    } finally {
      setLoading(false);
    }
  }, [sourceType, sourceId]);

  useEffect(() => {
    if (open) fetchData();
  }, [open, fetchData]);

  const dossier = useMemo(
    () =>
      buildDossier(
        { sourceType, sourceId, label: sourceLabel, siteLabel, orgLabel, period },
        actions,
        evidenceMap,
      ),
    [sourceType, sourceId, sourceLabel, siteLabel, orgLabel, period, actions, evidenceMap],
  );

  function handlePrint() {
    window.print();
  }

  if (!open) return null;

  return (
    <Drawer open={open} onClose={onClose} wide title="Dossier source" data-testid="dossier-print-view">
      {/* Print-only styles */}
      <style>{`
        @media print {
          body > *:not([data-print-root]) { display: none !important; }
          [data-print-root] { position: static !important; }
          .no-print { display: none !important; }
          .print-break { page-break-before: always; }
        }
      `}</style>

      <div data-print-root className="space-y-6 pb-8">
        {/* Toolbar (hidden in print) */}
        <div className="flex items-center justify-between no-print">
          <div className="flex items-center gap-2">
            <FileText size={18} className="text-blue-600" />
            <span className="text-sm font-semibold text-gray-900">Aperçu du dossier</span>
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={handlePrint} data-testid="dossier-print-btn">
              <Printer size={14} /> Imprimer / Export PDF
            </Button>
            <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400">
              <X size={16} />
            </button>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full" />
            <span className="ml-3 text-sm text-gray-500">Chargement du dossier…</span>
          </div>
        ) : !dossier.header ? (
          <p className="text-center text-gray-400 py-12">Aucune donnée disponible.</p>
        ) : (
          <>
            {/* ── Header ──────────────────────────────────────── */}
            <div className="border border-gray-200 rounded-xl p-5 bg-white" data-testid="dossier-header">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-bold text-gray-900">
                  Dossier — {dossier.header.sourceLabel}
                </h2>
                <Badge status="info">{SOURCE_LABELS_FR[sourceType] || sourceType}</Badge>
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm text-gray-600">
                {dossier.header.orgLabel && (
                  <div><span className="text-gray-400">Organisation :</span> {dossier.header.orgLabel}</div>
                )}
                {dossier.header.siteLabel && (
                  <div><span className="text-gray-400">Site :</span> {dossier.header.siteLabel}</div>
                )}
                {dossier.header.period && (
                  <div><span className="text-gray-400">Période :</span> {dossier.header.period}</div>
                )}
                <div><span className="text-gray-400">Source ID :</span> {dossier.header.sourceId}</div>
                <div>
                  <span className="text-gray-400">Généré le :</span>{' '}
                  {new Date(dossier.header.generatedAt).toLocaleDateString('fr-FR', {
                    day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit',
                  })}
                </div>
              </div>
            </div>

            {/* ── Stats bar ───────────────────────────────────── */}
            <div className="grid grid-cols-5 gap-3" data-testid="dossier-stats">
              {[
                { label: 'Actions', value: dossier.stats.total, color: 'text-gray-900' },
                { label: 'Ouvertes', value: dossier.stats.open, color: 'text-amber-700' },
                { label: 'Terminées', value: dossier.stats.done, color: 'text-green-700' },
                { label: 'Pièces', value: dossier.stats.evidenceCount, color: 'text-blue-700' },
                { label: 'À compléter', value: dossier.stats.missingCount, color: dossier.stats.missingCount > 0 ? 'text-red-700' : 'text-gray-400' },
              ].map((s) => (
                <div key={s.label} className="bg-gray-50 rounded-lg p-3 text-center">
                  <p className="text-xs text-gray-500">{s.label}</p>
                  <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
                </div>
              ))}
            </div>

            {/* ── Actions table ────────────────────────────────── */}
            <div data-testid="dossier-actions">
              <h3 className="text-sm font-semibold text-gray-800 mb-2 flex items-center gap-1.5">
                <FileText size={14} /> Actions liées ({dossier.actions.length})
              </h3>
              {dossier.actions.length === 0 ? (
                <p className="text-sm text-gray-400 italic">Aucune action liée à cette source.</p>
              ) : (
                <table className="w-full text-sm border border-gray-200 rounded-lg overflow-hidden">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">Action</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">Statut</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">Priorité</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">Responsable</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">Échéance</th>
                      <th className="px-3 py-2 text-center text-xs font-semibold text-gray-500">Preuves</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dossier.actions.map((a) => (
                      <tr key={a.id} className="border-t border-gray-100">
                        <td className="px-3 py-2 font-medium text-gray-900 max-w-xs truncate">{a.title}</td>
                        <td className="px-3 py-2">
                          <span className="flex items-center gap-1.5">
                            <span className={`w-2 h-2 rounded-full ${STATUS_DOT[a.status] || 'bg-gray-300'}`} />
                            {STATUS_LABELS_FR[a.status] || a.status}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-xs">
                          {PRIORITY_LABELS_FR[a.priority] || `P${a.priority}`}
                        </td>
                        <td className="px-3 py-2">{a.owner || <span className="text-gray-400 italic">Non assigné</span>}</td>
                        <td className="px-3 py-2 whitespace-nowrap">
                          {a.dueDate || '—'}
                        </td>
                        <td className="px-3 py-2 text-center">
                          {a.evidenceRequired ? (
                            a.evidenceCount > 0 ? (
                              <span className="text-green-600 font-medium">{a.evidenceCount} ✓</span>
                            ) : (
                              <span className="text-red-600 font-medium flex items-center justify-center gap-1">
                                <AlertTriangle size={12} /> Manquante
                              </span>
                            )
                          ) : (
                            a.evidenceCount > 0 ? (
                              <span className="text-gray-600">{a.evidenceCount}</span>
                            ) : (
                              <span className="text-gray-400">—</span>
                            )
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* ── Evidence list ────────────────────────────────── */}
            {dossier.evidence.length > 0 && (
              <div className="print-break" data-testid="dossier-evidence">
                <h3 className="text-sm font-semibold text-gray-800 mb-2 flex items-center gap-1.5">
                  <Paperclip size={14} /> Pièces justificatives ({dossier.evidence.length})
                </h3>
                <div className="space-y-1">
                  {dossier.evidence.map((e, i) => (
                    <div key={i} className="flex items-center gap-3 px-3 py-2 bg-gray-50 rounded-lg text-sm">
                      <Paperclip size={12} className="text-gray-400 shrink-0" />
                      <span className="font-medium text-gray-800 truncate">{e.label || e.file_url || 'Pièce'}</span>
                      <span className="text-xs text-gray-400 ml-auto shrink-0">Action : {e.actionTitle}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ── Missing items ────────────────────────────────── */}
            {dossier.missing.length > 0 && (
              <div data-testid="dossier-missing">
                <h3 className="text-sm font-semibold text-red-700 mb-2 flex items-center gap-1.5">
                  <AlertTriangle size={14} /> À compléter ({dossier.missing.length})
                </h3>
                <div className="space-y-1">
                  {dossier.missing.map((m, i) => (
                    <div key={i} className="flex items-center gap-3 px-3 py-2 bg-red-50 border border-red-100 rounded-lg text-sm">
                      <AlertTriangle size={12} className="text-red-500 shrink-0" />
                      <div>
                        <span className="font-medium text-red-800">{m.labelFR}</span>
                        <span className="text-xs text-red-500 ml-2">— {m.actionTitle}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ── Footer ─────────────────────────────────────── */}
            <div className="border-t border-gray-200 pt-4 text-xs text-gray-400 text-center">
              PROMEOS — Dossier généré automatiquement · {new Date().toLocaleDateString('fr-FR')}
            </div>
          </>
        )}
      </div>
    </Drawer>
  );
}
