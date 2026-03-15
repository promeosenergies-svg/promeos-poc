/**
 * PROMEOS - PatrimoineWizard V2 (WOW Polish)
 * 6-step staging pipeline: mode → upload → preview → corrections → validation → result.
 * Close confirmation, premium DnD, sticky preview table, clickable steps.
 */
import React, { useState, useMemo, useCallback } from 'react';
import {
  X,
  ChevronRight,
  ChevronLeft,
  Check,
  Upload,
  Download,
  FileSpreadsheet,
  AlertTriangle,
  ShieldCheck,
  Zap,
  Search,
  Building2,
  Play,
  SkipForward,
  RefreshCw,
  CheckCircle2,
  Sparkles,
  ExternalLink,
  FileText,
  File,
  Trash2,
} from 'lucide-react';
import {
  stagingImport,
  stagingSummary,
  stagingRows,
  stagingValidate,
  stagingFix,
  stagingAutofix,
  stagingActivate,
  loadPatrimoineDemo,
  recomputeSegmentation,
} from '../services/api';
import { useScope } from '../contexts/ScopeContext';

const API_BASE = import.meta.env.VITE_API_URL || '';

const STEPS = [
  { key: 'mode', label: 'Mode' },
  { key: 'upload', label: 'Import' },
  { key: 'preview', label: 'Aperçu' },
  { key: 'corrections', label: 'Corrections' },
  { key: 'validation', label: 'Validation' },
  { key: 'result', label: 'Résultat' },
];

const MODES = [
  {
    value: 'express',
    icon: Zap,
    title: 'Import rapide',
    desc: 'CSV ou Excel — validation automatique, creation immediate.',
    time: '2 min',
    color: 'text-amber-600 bg-amber-100',
    recommended: true,
  },
  {
    value: 'import',
    icon: FileSpreadsheet,
    title: 'Import avec verification',
    desc: 'Controle qualite, corrections manuelles, puis activation.',
    time: '5 min',
    color: 'text-indigo-600 bg-indigo-100',
    recommended: false,
  },
];

const SEV = {
  critical: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    badge: 'bg-red-100 text-red-700',
    label: 'Critique',
  },
  blocking: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    badge: 'bg-red-100 text-red-700',
    label: 'Bloquant',
  },
  warning: {
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    badge: 'bg-amber-100 text-amber-700',
    label: 'Avertissement',
  },
  info: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    badge: 'bg-blue-100 text-blue-700',
    label: 'Info',
  },
};

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

const PatrimoineWizard = ({ onClose }) => {
  const { refreshSites } = useScope();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [mode, setMode] = useState('import');
  const [file, setFile] = useState(null);
  const [csvPreview, setCsvPreview] = useState(null);
  const [batchId, setBatchId] = useState(null);
  const [summary, setSummary] = useState(null);
  const [mappingInfo, setMappingInfo] = useState(null);
  const [findings, setFindings] = useState([]);
  const [previewRows, setPreviewRows] = useState(null);
  const [issueFilter, setIssueFilter] = useState('all');
  const [activationResult, setActivationResult] = useState(null);
  const [portefeuilleId, setPortefeuilleId] = useState('');
  const [demoResult, setDemoResult] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [showCloseConfirm, setShowCloseConfirm] = useState(false);

  const isDirty = file !== null || batchId !== null;

  const readPreview = (f) => {
    const reader = new FileReader();
    reader.onload = (ev) => {
      setCsvPreview(
        ev.target.result
          .split('\n')
          .filter((l) => l.trim())
          .slice(0, 6)
      );
    };
    reader.readAsText(f);
  };

  const handleFileSelect = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setError(null);
    readPreview(f);
  };

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) {
      setFile(f);
      setError(null);
      readPreview(f);
    }
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const removeFile = () => {
    setFile(null);
    setCsvPreview(null);
    setError(null);
  };

  const doUpload = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await stagingImport(file, mode);
      setBatchId(result.batch_id);
      if (result.mapping) setMappingInfo(result.mapping);
      if (result.parse_errors?.length > 0)
        setError(`${result.parse_errors.length} erreur(s) de parsing (lignes ignorees).`);
      const [sum, rows] = await Promise.all([
        stagingSummary(result.batch_id),
        stagingRows(result.batch_id, { page_size: 20 }),
      ]);
      setSummary(sum);
      setPreviewRows(rows);
      setStep(2);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const doValidate = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await stagingValidate(batchId);
      setFindings(result.findings || []);
      const sum = await stagingSummary(batchId);
      setSummary(sum);
      setStep(result.can_activate ? 4 : 3);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const doAutofix = async () => {
    setLoading(true);
    try {
      await stagingAutofix(batchId);
      const result = await stagingValidate(batchId);
      setFindings(result.findings || []);
      setSummary(await stagingSummary(batchId));
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const doFix = async (finding, fixType, params) => {
    setLoading(true);
    try {
      await stagingFix(batchId, fixType, params);
      const result = await stagingValidate(batchId);
      setFindings(result.findings || []);
      setSummary(await stagingSummary(batchId));
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const doActivate = async () => {
    setLoading(true);
    setError(null);
    try {
      const pfId = parseInt(portefeuilleId) || 1;
      setActivationResult(await stagingActivate(batchId, pfId));
      setStep(5);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const doDemo = async () => {
    setLoading(true);
    setError(null);
    try {
      setDemoResult(await loadPatrimoineDemo());
      setStep(5);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleNext = () => {
    if (step === 0) setStep(1);
    else if (step === 1) doUpload();
    else if (step === 2) doValidate();
    else if (step === 3) setStep(4);
    else if (step === 4) doActivate();
    else if (step === 5) handleClose();
  };

  const handleClose = () => {
    if (activationResult || demoResult) {
      refreshSites();
      recomputeSegmentation().catch(() => {});
      onClose();
    } else {
      onClose();
    }
  };

  const requestClose = () => {
    if (isDirty && step > 0 && step < 5) {
      setShowCloseConfirm(true);
    } else {
      handleClose();
    }
  };

  const canProceed = () => {
    if (step === 0) return !!mode;
    if (step === 1) return file !== null;
    if (step === 2) return summary !== null;
    if (step === 4) return summary?.can_activate !== false;
    return true;
  };

  const nextLabel = () => {
    if (loading) return 'Chargement...';
    if (step === 0 && mode === 'demo') return 'Charger la demo';
    if (step === 1) return 'Uploader et analyser';
    if (step === 2) return 'Lancer la validation';
    if (step === 4) return 'Activer le patrimoine';
    return 'Suivant';
  };

  const handleStepClick = (targetStep) => {
    if (targetStep < step && step < 5) setStep(targetStep);
  };

  const unresolvedBlocking = findings.filter(
    (f) => (f.severity === 'blocking' || f.severity === 'critical') && !f.resolved
  );

  const filteredFindings = useMemo(() => {
    if (issueFilter === 'all') return findings;
    return findings.filter((f) => f.severity === issueFilter);
  }, [findings, issueFilter]);

  return (
    <div className="fixed inset-0 z-[200] bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b shrink-0">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
              <Building2 size={18} className="text-indigo-600" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">Importer patrimoine</h2>
              {batchId && <span className="text-xs text-gray-400">Batch #{batchId}</span>}
            </div>
          </div>
          <button
            onClick={requestClose}
            className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition"
          >
            <X size={20} />
          </button>
        </div>

        {/* Step indicator — clickable for back navigation */}
        <div className="px-6 py-3 flex items-center gap-1 border-b bg-gray-50/50 shrink-0">
          {STEPS.map((s, i) => (
            <React.Fragment key={s.key}>
              <button
                onClick={() => handleStepClick(i)}
                disabled={i >= step || step === 5}
                className={`flex items-center gap-1.5 text-xs transition ${
                  i < step
                    ? 'text-indigo-600 font-medium cursor-pointer hover:text-indigo-800'
                    : i === step
                      ? 'text-indigo-600 font-medium'
                      : 'text-gray-400 cursor-default'
                }`}
              >
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition ${
                    i < step
                      ? 'bg-indigo-600 text-white'
                      : i === step
                        ? 'bg-indigo-100 text-indigo-700 ring-2 ring-indigo-600'
                        : 'bg-gray-100 text-gray-400'
                  }`}
                >
                  {i < step ? <Check size={12} /> : i + 1}
                </div>
                <span className="hidden lg:inline">{s.label}</span>
              </button>
              {i < STEPS.length - 1 && (
                <div className={`flex-1 h-0.5 ${i < step ? 'bg-indigo-600' : 'bg-gray-200'}`} />
              )}
            </React.Fragment>
          ))}
        </div>

        {/* Content — scrollable */}
        <div className="px-6 py-5 min-h-[380px] overflow-y-auto flex-1">
          {/* Step 0: Mode */}
          {step === 0 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">
                Importer votre patrimoine
              </h3>
              <p className="text-sm text-gray-500 mb-4">
                Glissez un fichier CSV ou Excel pour creer vos sites.
              </p>
              <div className="space-y-3">
                {MODES.map((m) => {
                  const Icon = m.icon;
                  const active = mode === m.value;
                  return (
                    <button
                      key={m.value}
                      onClick={() => setMode(m.value)}
                      className={`w-full text-left p-4 border-2 rounded-xl transition ${active ? 'border-indigo-500 bg-indigo-50/50' : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50/50'}`}
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${active ? 'bg-indigo-100' : 'bg-gray-100'}`}
                        >
                          <Icon
                            size={18}
                            className={active ? 'text-indigo-600' : 'text-gray-400'}
                          />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span
                              className={`font-medium text-sm ${active ? 'text-indigo-700' : 'text-gray-700'}`}
                            >
                              {m.title}
                            </span>
                            {m.recommended && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 font-medium">
                                Recommande
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-gray-500 mt-0.5">{m.desc}</p>
                        </div>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 shrink-0">
                          {m.time}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Step 1: Upload */}
          {step === 1 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">Importez votre fichier</h3>
              <p className="text-sm text-gray-500 mb-3">
                Format CSV ou Excel. Les noms de colonnes sont détectés automatiquement.
              </p>
              <div className="flex items-center gap-2 mb-4 p-3 bg-indigo-50 border border-indigo-200 rounded-xl">
                <FileText size={16} className="text-indigo-600 shrink-0" />
                <span className="text-sm text-indigo-700">Besoin du format ?</span>
                <a
                  href={`${API_BASE}/api/patrimoine/import/template?format=xlsx`}
                  className="text-sm text-indigo-600 underline hover:text-indigo-800 flex items-center gap-1"
                  download
                >
                  <Download size={12} /> Excel
                </a>
                <span className="text-indigo-300">|</span>
                <a
                  href={`${API_BASE}/api/patrimoine/import/template?format=csv`}
                  className="text-sm text-indigo-600 underline hover:text-indigo-800 flex items-center gap-1"
                  download
                >
                  <Download size={12} /> CSV
                </a>
              </div>

              {!file ? (
                <div
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  className={`border-2 border-dashed rounded-xl p-10 text-center transition-all ${
                    dragOver
                      ? 'border-indigo-500 bg-indigo-50 scale-[1.01]'
                      : 'border-gray-300 hover:border-indigo-400 hover:bg-gray-50/50'
                  }`}
                >
                  <div
                    className={`w-14 h-14 rounded-2xl mx-auto mb-3 flex items-center justify-center transition ${
                      dragOver ? 'bg-indigo-100' : 'bg-gray-100'
                    }`}
                  >
                    <Upload size={24} className={dragOver ? 'text-indigo-600' : 'text-gray-400'} />
                  </div>
                  <p className="text-sm text-gray-600 mb-1">
                    {dragOver ? 'Lachez pour importer' : 'Glissez votre fichier ici'}
                  </p>
                  <p className="text-xs text-gray-400 mb-3">CSV, XLSX — max 10 Mo</p>
                  <label className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-indigo-50 text-indigo-700 hover:bg-indigo-100 cursor-pointer transition">
                    <Search size={14} />
                    Parcourir
                    <input
                      type="file"
                      accept=".csv,.xlsx,.xls,.txt"
                      onChange={handleFileSelect}
                      className="hidden"
                    />
                  </label>
                </div>
              ) : (
                <div className="border-2 border-indigo-200 bg-indigo-50/30 rounded-xl p-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-indigo-100 flex items-center justify-center shrink-0">
                      <File size={20} className="text-indigo-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{file.name}</p>
                      <p className="text-xs text-gray-500">{formatBytes(file.size)}</p>
                    </div>
                    <button
                      onClick={removeFile}
                      className="p-2 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 transition"
                      title="Supprimer"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              )}

              {csvPreview && (
                <div className="mt-4">
                  <p className="text-xs font-medium text-gray-600 mb-1.5">
                    Apercu brut ({file?.name})
                  </p>
                  <div className="bg-gray-900 rounded-xl text-xs font-mono overflow-x-auto p-3 max-h-32">
                    {csvPreview.map((line, i) => (
                      <div
                        key={i}
                        className={i === 0 ? 'font-bold text-indigo-400' : 'text-gray-300'}
                      >
                        {line}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 2: Preview */}
          {step === 2 && summary && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">Apercu de l'import</h3>
              <p className="text-sm text-gray-500 mb-3">
                Données importées dans la zone de staging.
              </p>
              <div className="grid grid-cols-4 gap-3 mb-4">
                <StatCard label="Sites" value={summary.sites} icon={Building2} color="indigo" />
                <StatCard label="Compteurs" value={summary.compteurs} icon={Zap} color="amber" />
                <StatCard
                  label="Constats"
                  value={summary.findings_total || 0}
                  icon={AlertTriangle}
                  color="orange"
                />
                <StatCard
                  label="Score qualité"
                  value={`${summary.quality_score || 0}%`}
                  icon={ShieldCheck}
                  color={
                    summary.quality_grade?.color === 'green'
                      ? 'green'
                      : summary.quality_grade?.color === 'amber'
                        ? 'amber'
                        : summary.quality_grade?.color === 'orange'
                          ? 'orange'
                          : 'red'
                  }
                />
              </div>

              {/* QA Grade indicator */}
              {summary.quality_grade && (
                <QAGradeBadge grade={summary.quality_grade} score={summary.quality_score} />
              )}

              {mappingInfo && Object.keys(mappingInfo.mapping || {}).length > 0 && (
                <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-xl">
                  <p className="text-xs font-medium text-blue-700 mb-1.5">
                    Colonnes détectées automatiquement
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(mappingInfo.mapping).map(([raw, canonical]) => (
                      <span
                        key={raw}
                        className="text-[10px] px-2 py-0.5 rounded-full bg-blue-100 text-blue-700"
                      >
                        "{raw}" → {canonical}
                      </span>
                    ))}
                  </div>
                  {mappingInfo.encoding && (
                    <p className="text-[10px] text-blue-500 mt-1.5">
                      Encoding: {mappingInfo.encoding} · Delimiter: "
                      {mappingInfo.delimiter === ';'
                        ? 'point-virgule'
                        : mappingInfo.delimiter === ','
                          ? 'virgule'
                          : 'tab'}
                      "
                    </p>
                  )}
                </div>
              )}
              {previewRows?.rows?.length > 0 && (
                <div className="border rounded-xl overflow-hidden">
                  <div className="bg-gray-50 px-3 py-2 border-b flex items-center justify-between">
                    <span className="text-xs font-medium text-gray-600">
                      {previewRows.total} site(s) importes
                    </span>
                    {previewRows.total > 20 && (
                      <span className="text-[10px] text-gray-400">20 premiers affiches</span>
                    )}
                  </div>
                  <div className="overflow-x-auto max-h-52">
                    <table className="w-full text-xs">
                      <thead className="bg-gray-50 sticky top-0 z-10">
                        <tr>
                          {[
                            '#',
                            'Nom',
                            'Adresse',
                            'CP',
                            'Ville',
                            'm²',
                            'Usage',
                            'Compteurs',
                            'Erreurs',
                          ].map((h) => (
                            <th
                              key={h}
                              className="px-2 py-1.5 text-left font-medium text-gray-500 whitespace-nowrap"
                            >
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {previewRows.rows.map((r) => (
                          <tr
                            key={r.id}
                            className={
                              r.skip
                                ? 'opacity-40'
                                : r.issues_count > 0
                                  ? 'bg-red-50/50'
                                  : 'hover:bg-gray-50'
                            }
                          >
                            <td className="px-2 py-1.5 text-gray-400">{r.row_number}</td>
                            <td className="px-2 py-1.5 font-medium text-gray-800 max-w-[140px] truncate">
                              {r.nom}
                            </td>
                            <td className="px-2 py-1.5 text-gray-600 max-w-[120px] truncate">
                              {r.adresse || '-'}
                            </td>
                            <td className="px-2 py-1.5 text-gray-600">{r.code_postal || '-'}</td>
                            <td className="px-2 py-1.5 text-gray-600">{r.ville || '-'}</td>
                            <td className="px-2 py-1.5 text-gray-600">{r.surface_m2 || '-'}</td>
                            <td className="px-2 py-1.5 text-gray-600">{r.type || '-'}</td>
                            <td className="px-2 py-1.5 text-gray-600">
                              {r.compteurs?.length || 0}
                            </td>
                            <td className="px-2 py-1.5">
                              {r.issues_count > 0 ? (
                                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-red-100 text-red-700">
                                  {r.issues_count}
                                </span>
                              ) : (
                                <span className="text-green-500">&#10003;</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
              <div className="mt-3 bg-indigo-50 border border-indigo-200 rounded-xl p-3">
                <p className="text-sm text-indigo-700">
                  Cliquez "Lancer la validation" pour exécuter le quality gate sur ces données.
                </p>
              </div>
            </div>
          )}

          {/* Step 3: Corrections */}
          {step === 3 && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-0.5">Corrections</h3>
                  <p className="text-sm text-gray-500">
                    {unresolvedBlocking.length > 0
                      ? `${unresolvedBlocking.length} problème(s) bloquant(s) à résoudre.`
                      : 'Aucun problème bloquant.'}
                  </p>
                </div>
                <button
                  onClick={doAutofix}
                  disabled={loading}
                  className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-xl bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100 transition"
                >
                  <Sparkles size={13} /> Auto-corriger
                </button>
              </div>
              <div className="flex items-center gap-1 mb-3">
                {['all', 'critical', 'blocking', 'warning', 'info'].map((f) => {
                  const count =
                    f === 'all' ? findings.length : findings.filter((x) => x.severity === f).length;
                  if (f !== 'all' && count === 0) return null;
                  return (
                    <button
                      key={f}
                      onClick={() => setIssueFilter(f)}
                      className={`text-[10px] px-2.5 py-1 rounded-full transition ${issueFilter === f ? 'bg-gray-800 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
                    >
                      {f === 'all' ? 'Tous' : SEV[f]?.label || f} ({count})
                    </button>
                  );
                })}
              </div>
              <div className="space-y-2 max-h-72 overflow-y-auto">
                {filteredFindings.map((f, i) => {
                  const sev = SEV[f.severity] || SEV.info;
                  let ev = {};
                  try {
                    ev = JSON.parse(f.evidence || '{}');
                  } catch {}
                  return (
                    <div
                      key={f.id || i}
                      className={`${sev.bg} ${sev.border} border rounded-xl p-3`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${sev.badge}`}
                          >
                            {sev.label}
                          </span>
                          <span className="text-sm font-medium text-gray-800">{f.rule_id}</span>
                          {f.resolved && <CheckCircle2 size={14} className="text-green-500" />}
                        </div>
                        {!f.resolved && <FixBtn f={f} ev={ev} onFix={doFix} />}
                      </div>
                      <EvText ev={ev} />
                    </div>
                  );
                })}
                {filteredFindings.length === 0 && (
                  <div className="text-center py-10 text-gray-400">
                    <CheckCircle2 size={36} className="mx-auto mb-2 text-green-400" />
                    <p className="text-sm font-medium text-gray-600">Aucun problème détecté</p>
                    <p className="text-xs text-gray-400 mt-1">Vous pouvez passer a la validation</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Step 4: Validation */}
          {step === 4 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">Plan d'exécution</h3>
              <p className="text-sm text-gray-500 mb-4">Vérifiez le résumé avant activation.</p>
              {summary && (
                <div className="bg-gray-50 border rounded-xl p-4 mb-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Row
                        label="Sites à créer"
                        value={summary.sites}
                        vc="text-indigo-600 font-bold"
                      />
                      <Row
                        label="Compteurs à créer"
                        value={summary.compteurs}
                        vc="text-indigo-600 font-bold"
                      />
                      <Row
                        label="Points de livraison"
                        value={`≤ ${summary.compteurs}`}
                        vc="text-gray-500"
                      />
                    </div>
                    <div className="space-y-2">
                      <Row
                        label="Bloquants"
                        value={summary.blocking || 0}
                        vc={
                          summary.blocking > 0
                            ? 'text-red-600 font-bold'
                            : 'text-green-600 font-bold'
                        }
                      />
                      <Row
                        label="Avertissements"
                        value={summary.warnings || 0}
                        vc="text-amber-600"
                      />
                      <Row
                        label="Score qualité"
                        value={`${summary.quality_score || 0}% — ${summary.quality_grade?.label || ''}`}
                        vc={
                          summary.quality_grade?.color === 'green'
                            ? 'text-green-600 font-bold'
                            : summary.quality_grade?.color === 'red'
                              ? 'text-red-600 font-bold'
                              : 'text-amber-600 font-bold'
                        }
                      />
                    </div>
                  </div>
                  <div className="mt-3 pt-3 border-t flex items-center justify-between">
                    <span className="text-sm text-gray-600">Pret pour activation</span>
                    <span
                      className={`text-sm font-bold ${summary.can_activate ? 'text-green-600' : 'text-red-600'}`}
                    >
                      {summary.can_activate ? '✓ Oui' : '✗ Non'}
                    </span>
                  </div>
                  {summary.can_auto_activate && (
                    <div className="mt-2 pt-2 border-t flex items-center justify-between">
                      <span className="text-sm text-gray-600">Activation auto</span>
                      <span className="text-sm font-bold text-green-600">Eligible</span>
                    </div>
                  )}
                </div>
              )}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Portefeuille cible (ID)
                </label>
                <input
                  type="number"
                  value={portefeuilleId}
                  onChange={(e) => setPortefeuilleId(e.target.value)}
                  placeholder="1"
                  min="1"
                  className="w-40 border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                />
                <p className="text-xs text-gray-400 mt-1">
                  Les sites seront créés dans ce portefeuille.
                </p>
              </div>
              {unresolvedBlocking.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-3 flex items-start gap-2">
                  <AlertTriangle size={16} className="text-red-500 shrink-0 mt-0.5" />
                  <p className="text-sm text-red-700">
                    {unresolvedBlocking.length} problème(s) bloquant(s). Retournez à Corrections.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Step 5: Result */}
          {step === 5 && (
            <div>
              <div className="flex items-center gap-3 mb-5">
                <div className="w-12 h-12 rounded-2xl bg-green-100 flex items-center justify-center">
                  <CheckCircle2 size={28} className="text-green-500" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-900">
                    {demoResult ? 'Demo chargee !' : 'Patrimoine active !'}
                  </h3>
                  <p className="text-sm text-gray-500">Les entités ont été créées avec succès.</p>
                </div>
              </div>
              {activationResult && (
                <div className="bg-green-50 border border-green-200 rounded-xl p-4 space-y-2 mb-4">
                  <Row label="Sites créés" value={activationResult.sites_created} />
                  <Row label="Compteurs créés" value={activationResult.compteurs_created} />
                  {activationResult.delivery_points_created > 0 && (
                    <Row
                      label="Points de livraison"
                      value={activationResult.delivery_points_created}
                    />
                  )}
                  <Row label="Batiments" value={activationResult.batiments} />
                  <Row label="Obligations" value={activationResult.obligations} />
                </div>
              )}
              {demoResult && (
                <div className="bg-green-50 border border-green-200 rounded-xl p-4 space-y-2 mb-4">
                  <Row label="Statut" value={demoResult.status} />
                  <Row label="Organisation" value={demoResult.org_name || 'Collectivite Azur'} />
                  <Row label="Sites" value={demoResult.sites} />
                  <Row label="Compteurs" value={demoResult.compteurs} />
                  <Row label="Liens N-N" value={demoResult.nn_links} />
                </div>
              )}
              {batchId && activationResult && (
                <div className="mb-4">
                  <a
                    href={`${API_BASE}/api/patrimoine/staging/${batchId}/export/report.csv`}
                    className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-xl hover:bg-indigo-100 transition"
                    download
                  >
                    <Download size={14} /> Telecharger le rapport CSV
                  </a>
                </div>
              )}
              <div className="bg-gray-50 border rounded-xl p-4">
                <p className="text-sm font-medium text-gray-700 mb-3">Prochaines etapes</p>
                <div className="space-y-2">
                  <NxStep
                    icon={Zap}
                    label="Connecter Enedis/GRDF"
                    desc="Synchronisez vos consommations reelles"
                  />
                  <NxStep
                    icon={FileSpreadsheet}
                    label="Importer des factures"
                    desc="Bill Intelligence pour l'analyse tarifaire"
                  />
                  <NxStep
                    icon={ShieldCheck}
                    label="Lancer un audit conformité"
                    desc="Decret Tertiaire et BACS"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Error banner */}
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-xl flex items-start gap-2">
              <AlertTriangle size={18} className="text-red-500 shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-red-800">Erreur</p>
                <p className="text-sm text-red-700">{error}</p>
              </div>
              <button
                onClick={() => setError(null)}
                className="p-1 rounded hover:bg-red-100 text-red-400 hover:text-red-600"
              >
                <X size={14} />
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t bg-gray-50 rounded-b-2xl shrink-0">
          <button
            onClick={() => (step > 0 && step < 5 ? setStep(step - 1) : requestClose())}
            className="flex items-center gap-1 text-gray-600 hover:text-gray-800 text-sm transition"
          >
            <ChevronLeft size={16} /> {step > 0 && step < 5 ? 'Précédent' : 'Fermer'}
          </button>
          <div className="flex items-center gap-2">
            {step === 3 && (
              <button
                onClick={doValidate}
                className="flex items-center gap-1 px-3 py-2 text-sm text-gray-500 hover:text-gray-700 transition"
              >
                <RefreshCw size={14} /> Re-valider
              </button>
            )}
            {step < 5 && (
              <button
                onClick={handleNext}
                disabled={!canProceed() || loading}
                className={`flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-semibold transition ${
                  !canProceed() || loading
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    : step === 4
                      ? 'bg-gradient-to-r from-green-500 to-emerald-600 text-white hover:from-green-600 hover:to-emerald-700 shadow-sm'
                      : 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm'
                }`}
              >
                {nextLabel()}
                {!loading && <ChevronRight size={16} />}
              </button>
            )}
            {step === 5 && (
              <button
                onClick={handleClose}
                className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-semibold bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm transition"
              >
                Voir le patrimoine <ChevronRight size={16} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Close confirmation overlay */}
      {showCloseConfirm && (
        <div className="fixed inset-0 z-[210] bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-sm p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center">
                <AlertTriangle size={20} className="text-amber-600" />
              </div>
              <h3 className="text-lg font-bold text-gray-900">Quitter l'import ?</h3>
            </div>
            <p className="text-sm text-gray-600 mb-5">
              L'import est en cours. Si vous quittez, les données non activées seront perdues.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowCloseConfirm(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition"
              >
                Continuer l'import
              </button>
              <button
                onClick={() => {
                  setShowCloseConfirm(false);
                  onClose();
                }}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition"
              >
                Quitter
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

function StatCard({ label, value, icon: Icon, color }) {
  const c = {
    indigo: 'bg-indigo-50 text-indigo-700',
    amber: 'bg-amber-50 text-amber-700',
    orange: 'bg-orange-50 text-orange-700',
    green: 'bg-green-50 text-green-700',
    red: 'bg-red-50 text-red-700',
  };
  return (
    <div className={`${c[color] || c.indigo} rounded-xl p-3 text-center`}>
      <Icon size={18} className="mx-auto mb-1" />
      <div className="text-xl font-bold">{value}</div>
      <div className="text-[10px] uppercase tracking-wide">{label}</div>
    </div>
  );
}

function QAGradeBadge({ grade, score }) {
  const COLOR_MAP = {
    green: {
      bg: 'bg-green-50',
      border: 'border-green-200',
      text: 'text-green-700',
      bar: 'bg-green-500',
    },
    amber: {
      bg: 'bg-amber-50',
      border: 'border-amber-200',
      text: 'text-amber-700',
      bar: 'bg-amber-500',
    },
    orange: {
      bg: 'bg-orange-50',
      border: 'border-orange-200',
      text: 'text-orange-700',
      bar: 'bg-orange-500',
    },
    red: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', bar: 'bg-red-500' },
  };
  const c = COLOR_MAP[grade.color] || COLOR_MAP.amber;
  return (
    <div className={`${c.bg} ${c.border} border rounded-lg p-3`}>
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-2">
          <ShieldCheck size={16} className={c.text} />
          <span className={`text-sm font-semibold ${c.text}`}>
            Confiance Patrimoine : {grade.label}
          </span>
        </div>
        <span className={`text-lg font-bold ${c.text}`}>{score}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2 mb-1.5">
        <div
          className={`${c.bar} h-2 rounded-full transition-all`}
          style={{ width: `${Math.min(score, 100)}%` }}
        />
      </div>
      <p className={`text-xs ${c.text}`}>{grade.message}</p>
      {grade.gap > 0 && grade.threshold_next && (
        <p className="text-[10px] text-gray-500 mt-1">
          +{grade.gap} points pour atteindre le seuil {grade.threshold_next}%
        </p>
      )}
    </div>
  );
}

function Row({ label, value, vc = '' }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-gray-600">{label}</span>
      <span className={`font-medium ${vc}`}>{String(value)}</span>
    </div>
  );
}

function NxStep({ icon: Icon, label, desc }) {
  return (
    <div className="flex items-center gap-3 p-2.5 rounded-xl hover:bg-gray-100 transition cursor-pointer">
      <div className="w-9 h-9 rounded-lg bg-indigo-100 flex items-center justify-center shrink-0">
        <Icon size={16} className="text-indigo-600" />
      </div>
      <div>
        <p className="text-sm font-medium text-gray-800">{label}</p>
        <p className="text-xs text-gray-500">{desc}</p>
      </div>
      <ExternalLink size={14} className="ml-auto text-gray-300" />
    </div>
  );
}

function FixBtn({ f, _ev, onFix }) {
  const skipA = () =>
    onFix(f, 'skip', {
      staging_site_id: f.staging_site_id,
      staging_compteur_id: f.staging_compteur_id,
    });
  const skipS = () => onFix(f, 'skip', { staging_site_id: f.staging_site_id });
  const skipC = () => onFix(f, 'skip', { staging_compteur_id: f.staging_compteur_id });
  const btn = (lbl, fn) => (
    <button
      onClick={fn}
      className="text-xs px-2 py-1 rounded-lg bg-white border text-gray-600 hover:bg-gray-50 flex items-center gap-1 transition"
    >
      <SkipForward size={12} /> {lbl}
    </button>
  );
  if (['skip', 'merge', 'remap'].includes(f.suggested_action))
    return btn('Ignorer', f.staging_compteur_id ? skipC : skipA);
  if (['fix_siret', 'create_entite', 'fix_address'].includes(f.suggested_action))
    return btn('Ignorer', skipS);
  if (f.suggested_action === 'fix_meter_id') return btn('Ignorer compteur', skipC);
  return btn('Ignorer', skipA);
}

function EvText({ ev }) {
  const p = [];
  if (ev.site_a && ev.site_b) p.push(`"${ev.site_a}" ↔ "${ev.site_b}" (sim: ${ev.similarity})`);
  if (ev.value && ev.field) p.push(`${ev.field} = "${ev.value}"`);
  if (ev.reason && !ev.field) p.push(ev.reason);
  if (ev.missing_fields) p.push(`Manquants: ${ev.missing_fields.join(', ')} (${ev.site_name})`);
  if (ev.siret && !ev.field) p.push(`SIRET "${ev.siret}" (${ev.site_name})`);
  if (ev.siren_extracted) p.push(`SIREN "${ev.siren_extracted}" invalide (${ev.site_name})`);
  if (ev.numero_serie && !ev.field && !ev.reason)
    p.push(`Compteur: ${ev.numero_serie || ev.meter_id}`);
  if (!p.length && ev.site_name) p.push(ev.site_name);
  return p.length ? <p className="text-xs text-gray-600 mt-1">{p.join(' — ')}</p> : null;
}

export default PatrimoineWizard;
