/**
 * PROMEOS - PatrimoineWizard (DIAMANT VNext)
 * 6-step staging pipeline: mode → upload → preview → corrections → validation → result.
 */
import React, { useState, useMemo } from 'react';
import {
  X, ChevronRight, ChevronLeft, Check, Upload, Download,
  FileSpreadsheet, AlertTriangle, ShieldCheck, Zap, Search,
  Building2, Play, XCircle,
  SkipForward, RefreshCw, CheckCircle2, Sparkles,
  ExternalLink, FileText,
} from 'lucide-react';
import {
  stagingImport, stagingSummary, stagingRows,
  stagingValidate, stagingFix, stagingAutofix,
  stagingActivate, loadPatrimoineDemo,
} from '../services/api';

const API_BASE = import.meta.env.VITE_API_URL || '';

const STEPS = [
  { key: 'mode', label: 'Mode' },
  { key: 'upload', label: 'Import' },
  { key: 'preview', label: 'Apercu' },
  { key: 'corrections', label: 'Corrections' },
  { key: 'validation', label: 'Validation' },
  { key: 'result', label: 'Resultat' },
];

const MODES = [
  { value: 'express', icon: Zap, title: 'Express', desc: 'Upload CSV, validation rapide, activation directe.', time: '2 min' },
  { value: 'import', icon: FileSpreadsheet, title: 'Import complet', desc: 'CSV/Excel avec quality gate et corrections.', time: '5 min' },
  { value: 'assiste', icon: ShieldCheck, title: 'Assiste', desc: 'Import depuis factures + enrichissement IA.', time: '10 min' },
  { value: 'demo', icon: Play, title: 'Demo', desc: 'Charger le dataset demo (Collectivite Azur).', time: '10 sec' },
];

const SEV = {
  critical: { bg: 'bg-red-50', border: 'border-red-200', badge: 'bg-red-100 text-red-700', label: 'Critique' },
  blocking: { bg: 'bg-red-50', border: 'border-red-200', badge: 'bg-red-100 text-red-700', label: 'Bloquant' },
  warning: { bg: 'bg-amber-50', border: 'border-amber-200', badge: 'bg-amber-100 text-amber-700', label: 'Avertissement' },
  info: { bg: 'bg-blue-50', border: 'border-blue-200', badge: 'bg-blue-100 text-blue-700', label: 'Info' },
};

const PatrimoineWizard = ({ onClose }) => {
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

  const readPreview = (f) => {
    const reader = new FileReader();
    reader.onload = (ev) => {
      setCsvPreview(ev.target.result.split('\n').filter(l => l.trim()).slice(0, 6));
    };
    reader.readAsText(f);
  };

  const handleFileSelect = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f); setError(null); readPreview(f);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f) { setFile(f); setError(null); readPreview(f); }
  };

  const doUpload = async () => {
    setLoading(true); setError(null);
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
      setSummary(sum); setPreviewRows(rows); setStep(2);
    } catch (err) { setError(err.response?.data?.detail || err.message); }
    finally { setLoading(false); }
  };

  const doValidate = async () => {
    setLoading(true); setError(null);
    try {
      const result = await stagingValidate(batchId);
      setFindings(result.findings || []);
      const sum = await stagingSummary(batchId);
      setSummary(sum);
      setStep(result.can_activate ? 4 : 3);
    } catch (err) { setError(err.response?.data?.detail || err.message); }
    finally { setLoading(false); }
  };

  const doAutofix = async () => {
    setLoading(true);
    try {
      await stagingAutofix(batchId);
      const result = await stagingValidate(batchId);
      setFindings(result.findings || []);
      setSummary(await stagingSummary(batchId));
    } catch (err) { setError(err.response?.data?.detail || err.message); }
    finally { setLoading(false); }
  };

  const doFix = async (finding, fixType, params) => {
    setLoading(true);
    try {
      await stagingFix(batchId, fixType, params);
      const result = await stagingValidate(batchId);
      setFindings(result.findings || []);
      setSummary(await stagingSummary(batchId));
    } catch (err) { setError(err.response?.data?.detail || err.message); }
    finally { setLoading(false); }
  };

  const doActivate = async () => {
    setLoading(true); setError(null);
    try {
      const pfId = parseInt(portefeuilleId) || 1;
      setActivationResult(await stagingActivate(batchId, pfId));
      setStep(5);
    } catch (err) { setError(err.response?.data?.detail || err.message); }
    finally { setLoading(false); }
  };

  const doDemo = async () => {
    setLoading(true); setError(null);
    try { setDemoResult(await loadPatrimoineDemo()); setStep(5); }
    catch (err) { setError(err.response?.data?.detail || err.message); }
    finally { setLoading(false); }
  };

  const handleNext = () => {
    if (mode === 'demo' && step === 0) { doDemo(); return; }
    if (step === 0) setStep(1);
    else if (step === 1) doUpload();
    else if (step === 2) doValidate();
    else if (step === 3) setStep(4);
    else if (step === 4) doActivate();
    else if (step === 5) handleClose();
  };

  const handleClose = () => {
    if (activationResult || demoResult) window.location.reload();
    else onClose();
  };

  const canProceed = () => {
    if (step === 0) return !!mode;
    if (step === 1) return file !== null;
    if (step === 2) return summary !== null;
    if (step === 4) return summary?.can_activate !== false;
    return true;
  };

  const unresolvedBlocking = findings.filter(
    f => (f.severity === 'blocking' || f.severity === 'critical') && !f.resolved
  );

  const filteredFindings = useMemo(() => {
    if (issueFilter === 'all') return findings;
    return findings.filter(f => f.severity === issueFilter);
  }, [findings, issueFilter]);

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div className="flex items-center gap-2">
            <Building2 size={22} className="text-indigo-600" />
            <h2 className="text-lg font-bold text-gray-900">Importer patrimoine</h2>
            {batchId && <span className="text-xs text-gray-400 ml-2">Batch #{batchId}</span>}
          </div>
          <button onClick={handleClose} className="text-gray-400 hover:text-gray-600"><X size={20} /></button>
        </div>

        {/* Step indicator */}
        <div className="px-6 py-3 flex items-center gap-1">
          {STEPS.map((s, i) => (
            <React.Fragment key={s.key}>
              <div className={`flex items-center gap-1 text-xs ${i <= step ? 'text-indigo-600 font-medium' : 'text-gray-400'}`}>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${
                  i < step ? 'bg-indigo-600 text-white' : i === step ? 'bg-indigo-100 text-indigo-700 ring-2 ring-indigo-600' : 'bg-gray-100 text-gray-400'
                }`}>{i < step ? <Check size={12} /> : i + 1}</div>
                <span className="hidden lg:inline">{s.label}</span>
              </div>
              {i < STEPS.length - 1 && <div className={`flex-1 h-0.5 ${i < step ? 'bg-indigo-600' : 'bg-gray-200'}`} />}
            </React.Fragment>
          ))}
        </div>

        <div className="px-6 py-5 min-h-[380px]">

          {/* Step 0: Mode */}
          {step === 0 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">Choisissez le mode d'import</h3>
              <p className="text-sm text-gray-500 mb-4">Comment souhaitez-vous alimenter votre patrimoine ?</p>
              <div className="grid grid-cols-2 gap-3">
                {MODES.map(m => {
                  const Icon = m.icon;
                  return (
                    <button key={m.value} onClick={() => setMode(m.value)}
                      className={`text-left p-4 border-2 rounded-xl transition ${mode === m.value ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200 hover:border-gray-300'}`}>
                      <div className="flex items-center gap-2 mb-1">
                        <Icon size={18} className={mode === m.value ? 'text-indigo-600' : 'text-gray-400'} />
                        <span className={`font-medium text-sm ${mode === m.value ? 'text-indigo-700' : 'text-gray-700'}`}>{m.title}</span>
                        <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">{m.time}</span>
                      </div>
                      <p className="text-xs text-gray-500">{m.desc}</p>
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
              <p className="text-sm text-gray-500 mb-3">Format CSV ou Excel. Les noms de colonnes sont detectes automatiquement.</p>
              <div className="flex items-center gap-2 mb-4 p-3 bg-indigo-50 border border-indigo-200 rounded-lg">
                <FileText size={16} className="text-indigo-600 shrink-0" />
                <span className="text-sm text-indigo-700">Besoin du format ?</span>
                <a href={`${API_BASE}/api/patrimoine/import/template?format=xlsx`} className="text-sm text-indigo-600 underline hover:text-indigo-800 flex items-center gap-1" download><Download size={12} /> Excel</a>
                <span className="text-indigo-300">|</span>
                <a href={`${API_BASE}/api/patrimoine/import/template?format=csv`} className="text-sm text-indigo-600 underline hover:text-indigo-800 flex items-center gap-1" download><Download size={12} /> CSV</a>
              </div>
              <div onDragOver={e => e.preventDefault()} onDrop={handleDrop}
                className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center hover:border-indigo-400 transition">
                <Upload size={32} className="mx-auto text-gray-400 mb-3" />
                <p className="text-sm text-gray-600 mb-2">{file ? file.name : 'Glissez votre fichier ici ou cliquez'}</p>
                <input type="file" accept=".csv,.xlsx,.xls,.txt" onChange={handleFileSelect}
                  className="text-sm text-gray-500 file:mr-3 file:py-1.5 file:px-4 file:rounded-lg file:border-0 file:text-sm file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100" />
              </div>
              {csvPreview && (
                <div className="mt-4">
                  <p className="text-xs font-medium text-gray-600 mb-1">Apercu ({file?.name})</p>
                  <div className="bg-gray-50 rounded-lg border text-xs font-mono overflow-x-auto p-3 max-h-32">
                    {csvPreview.map((line, i) => (
                      <div key={i} className={i === 0 ? 'font-bold text-indigo-700' : 'text-gray-600'}>{line}</div>
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
              <p className="text-sm text-gray-500 mb-3">Donnees importees dans la zone de staging.</p>
              <div className="grid grid-cols-4 gap-3 mb-4">
                <StatCard label="Sites" value={summary.sites} icon={Building2} color="indigo" />
                <StatCard label="Compteurs" value={summary.compteurs} icon={Zap} color="amber" />
                <StatCard label="Findings" value={summary.findings_total || 0} icon={AlertTriangle} color="orange" />
                <StatCard label="Score" value={`${summary.quality_score || 0}%`} icon={ShieldCheck}
                  color={summary.quality_score >= 80 ? 'green' : summary.quality_score >= 50 ? 'amber' : 'red'} />
              </div>
              {mappingInfo && Object.keys(mappingInfo.mapping || {}).length > 0 && (
                <div className="mb-3 p-2 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-xs font-medium text-blue-700 mb-1">Colonnes detectees:</p>
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(mappingInfo.mapping).map(([raw, canonical]) => (
                      <span key={raw} className="text-[10px] px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">"{raw}" → {canonical}</span>
                    ))}
                  </div>
                </div>
              )}
              {previewRows?.rows?.length > 0 && (
                <div className="border rounded-lg overflow-hidden">
                  <div className="bg-gray-50 px-3 py-2 border-b">
                    <span className="text-xs font-medium text-gray-600">{previewRows.total} site(s)</span>
                  </div>
                  <div className="overflow-x-auto max-h-48">
                    <table className="w-full text-xs">
                      <thead className="bg-gray-50 sticky top-0"><tr>
                        {['#','Nom','Ville','CP','m²','Cpt','Err'].map(h => (
                          <th key={h} className="px-2 py-1.5 text-left font-medium text-gray-500">{h}</th>
                        ))}
                      </tr></thead>
                      <tbody className="divide-y divide-gray-100">
                        {previewRows.rows.map(r => (
                          <tr key={r.id} className={r.skip ? 'opacity-40' : r.issues_count > 0 ? 'bg-red-50/50' : ''}>
                            <td className="px-2 py-1 text-gray-400">{r.row_number}</td>
                            <td className="px-2 py-1 font-medium text-gray-800 max-w-[160px] truncate">{r.nom}</td>
                            <td className="px-2 py-1 text-gray-600">{r.ville || '-'}</td>
                            <td className="px-2 py-1 text-gray-600">{r.code_postal || '-'}</td>
                            <td className="px-2 py-1 text-gray-600">{r.surface_m2 || '-'}</td>
                            <td className="px-2 py-1 text-gray-600">{r.compteurs?.length || 0}</td>
                            <td className="px-2 py-1">{r.issues_count > 0
                              ? <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-red-100 text-red-700">{r.issues_count}</span>
                              : <span className="text-green-500">✓</span>}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
              <div className="mt-3 bg-indigo-50 border border-indigo-200 rounded-lg p-3">
                <p className="text-sm text-indigo-700">Cliquez "Lancer la validation" pour executer le quality gate.</p>
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
                    {unresolvedBlocking.length > 0 ? `${unresolvedBlocking.length} probleme(s) bloquant(s) a resoudre.` : 'Aucun probleme bloquant.'}
                  </p>
                </div>
                <button onClick={doAutofix} disabled={loading}
                  className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100 transition">
                  <Sparkles size={12} /> Auto-corriger
                </button>
              </div>
              <div className="flex items-center gap-1 mb-3">
                {['all', 'critical', 'blocking', 'warning', 'info'].map(f => {
                  const count = f === 'all' ? findings.length : findings.filter(x => x.severity === f).length;
                  if (f !== 'all' && count === 0) return null;
                  return (
                    <button key={f} onClick={() => setIssueFilter(f)}
                      className={`text-[10px] px-2 py-1 rounded-full transition ${issueFilter === f ? 'bg-gray-800 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                      {f === 'all' ? 'Tous' : (SEV[f]?.label || f)} ({count})
                    </button>
                  );
                })}
              </div>
              <div className="space-y-2 max-h-72 overflow-y-auto">
                {filteredFindings.map((f, i) => {
                  const sev = SEV[f.severity] || SEV.info;
                  let ev = {};
                  try { ev = JSON.parse(f.evidence || '{}'); } catch {}
                  return (
                    <div key={f.id || i} className={`${sev.bg} ${sev.border} border rounded-lg p-3`}>
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${sev.badge}`}>{sev.label}</span>
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
                  <div className="text-center py-8 text-gray-400">
                    <CheckCircle2 size={32} className="mx-auto mb-2" />
                    <p className="text-sm">Aucun probleme detecte</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Step 4: Validation */}
          {step === 4 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">Plan d'execution</h3>
              <p className="text-sm text-gray-500 mb-4">Verifiez le resume avant activation.</p>
              {summary && (
                <div className="bg-gray-50 border rounded-lg p-4 mb-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Row label="Sites a creer" value={summary.sites} vc="text-indigo-600 font-bold" />
                      <Row label="Compteurs a creer" value={summary.compteurs} vc="text-indigo-600 font-bold" />
                      <Row label="Points de livraison" value={`≤ ${summary.compteurs}`} vc="text-gray-500" />
                    </div>
                    <div className="space-y-2">
                      <Row label="Bloquants" value={summary.blocking || 0} vc={summary.blocking > 0 ? 'text-red-600 font-bold' : 'text-green-600 font-bold'} />
                      <Row label="Avertissements" value={summary.warnings || 0} vc="text-amber-600" />
                      <Row label="Score" value={`${summary.quality_score || 0}%`} vc={summary.quality_score >= 80 ? 'text-green-600 font-bold' : 'text-amber-600 font-bold'} />
                    </div>
                  </div>
                  <div className="mt-3 pt-3 border-t flex items-center justify-between">
                    <span className="text-sm text-gray-600">Pret pour activation</span>
                    <span className={`text-sm font-bold ${summary.can_activate ? 'text-green-600' : 'text-red-600'}`}>{summary.can_activate ? '✓ Oui' : '✗ Non'}</span>
                  </div>
                </div>
              )}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">Portefeuille cible (ID)</label>
                <input type="number" value={portefeuilleId} onChange={e => setPortefeuilleId(e.target.value)} placeholder="1" min="1"
                  className="w-40 border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none" />
                <p className="text-xs text-gray-400 mt-1">Les sites seront crees dans ce portefeuille.</p>
              </div>
              {unresolvedBlocking.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start gap-2">
                  <AlertTriangle size={16} className="text-red-500 shrink-0 mt-0.5" />
                  <p className="text-sm text-red-700">{unresolvedBlocking.length} probleme(s) bloquant(s). Retournez a Corrections.</p>
                </div>
              )}
            </div>
          )}

          {/* Step 5: Result */}
          {step === 5 && (
            <div>
              <div className="flex items-center gap-3 mb-4">
                <CheckCircle2 size={28} className="text-green-500" />
                <h3 className="text-xl font-bold text-gray-900">{demoResult ? 'Demo chargee !' : 'Patrimoine active !'}</h3>
              </div>
              {activationResult && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 space-y-2 mb-4">
                  <Row label="Sites crees" value={activationResult.sites_created} />
                  <Row label="Compteurs crees" value={activationResult.compteurs_created} />
                  {activationResult.delivery_points_created > 0 && <Row label="Points de livraison" value={activationResult.delivery_points_created} />}
                  <Row label="Batiments" value={activationResult.batiments} />
                  <Row label="Obligations" value={activationResult.obligations} />
                </div>
              )}
              {demoResult && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 space-y-2 mb-4">
                  <Row label="Statut" value={demoResult.status} />
                  <Row label="Organisation" value={demoResult.org_name || 'Collectivite Azur'} />
                  <Row label="Sites" value={demoResult.sites} />
                  <Row label="Compteurs" value={demoResult.compteurs} />
                  <Row label="Liens N-N" value={demoResult.nn_links} />
                </div>
              )}
              {batchId && activationResult && (
                <div className="mb-4">
                  <a href={`${API_BASE}/api/patrimoine/staging/${batchId}/export/report.csv`}
                    className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition" download>
                    <Download size={14} /> Telecharger le rapport CSV
                  </a>
                </div>
              )}
              <div className="bg-gray-50 border rounded-lg p-4">
                <p className="text-sm font-medium text-gray-700 mb-3">Prochaines etapes</p>
                <div className="space-y-2">
                  <NxStep icon={Zap} label="Connecter Enedis/GRDF" desc="Synchronisez vos consommations reelles" />
                  <NxStep icon={FileSpreadsheet} label="Importer des factures" desc="Bill Intelligence pour l'analyse tarifaire" />
                  <NxStep icon={ShieldCheck} label="Lancer un audit conformite" desc="Decret Tertiaire et BACS" />
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
              <AlertTriangle size={18} className="text-red-500 shrink-0 mt-0.5" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t bg-gray-50 rounded-b-2xl">
          <button onClick={() => step > 0 && step < 5 ? setStep(step - 1) : handleClose()}
            className="flex items-center gap-1 text-gray-600 hover:text-gray-800 text-sm">
            <ChevronLeft size={16} /> {step > 0 && step < 5 ? 'Precedent' : 'Fermer'}
          </button>
          <div className="flex items-center gap-2">
            {step === 3 && (
              <button onClick={doValidate} className="flex items-center gap-1 px-3 py-2 text-sm text-gray-500 hover:text-gray-700">
                <RefreshCw size={14} /> Re-valider
              </button>
            )}
            {step < 5 && (
              <button onClick={handleNext} disabled={!canProceed() || loading}
                className={`flex items-center gap-1 px-5 py-2 rounded-lg text-sm font-semibold transition ${
                  !canProceed() || loading ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : step === 4 ? 'bg-gradient-to-r from-green-500 to-emerald-600 text-white hover:from-green-600 hover:to-emerald-700'
                  : 'bg-indigo-600 text-white hover:bg-indigo-700'
                }`}>
                {loading ? 'Chargement...' : step === 0 && mode === 'demo' ? 'Charger la demo' : step === 2 ? 'Lancer la validation' : step === 4 ? 'Activer le patrimoine' : 'Suivant'}
                {!loading && <ChevronRight size={16} />}
              </button>
            )}
            {step === 5 && (
              <button onClick={handleClose} className="flex items-center gap-1 px-5 py-2 rounded-lg text-sm font-semibold bg-indigo-600 text-white hover:bg-indigo-700 transition">
                Voir le patrimoine <ChevronRight size={16} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

function StatCard({ label, value, icon: Icon, color }) {
  const c = { indigo: 'bg-indigo-50 text-indigo-700', amber: 'bg-amber-50 text-amber-700', orange: 'bg-orange-50 text-orange-700', green: 'bg-green-50 text-green-700', red: 'bg-red-50 text-red-700' };
  return (<div className={`${c[color] || c.indigo} rounded-lg p-3 text-center`}><Icon size={18} className="mx-auto mb-1" /><div className="text-xl font-bold">{value}</div><div className="text-[10px] uppercase tracking-wide">{label}</div></div>);
}

function Row({ label, value, vc = '' }) {
  return (<div className="flex justify-between text-sm"><span className="text-gray-600">{label}</span><span className={`font-medium ${vc}`}>{String(value)}</span></div>);
}

function NxStep({ icon: Icon, label, desc }) {
  return (
    <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-100 transition cursor-pointer">
      <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center shrink-0"><Icon size={16} className="text-indigo-600" /></div>
      <div><p className="text-sm font-medium text-gray-800">{label}</p><p className="text-xs text-gray-500">{desc}</p></div>
      <ExternalLink size={14} className="ml-auto text-gray-300" />
    </div>
  );
}

function FixBtn({ f, ev, onFix }) {
  const skipA = () => onFix(f, 'skip', { staging_site_id: f.staging_site_id, staging_compteur_id: f.staging_compteur_id });
  const skipS = () => onFix(f, 'skip', { staging_site_id: f.staging_site_id });
  const skipC = () => onFix(f, 'skip', { staging_compteur_id: f.staging_compteur_id });
  const btn = (lbl, fn) => (<button onClick={fn} className="text-xs px-2 py-1 rounded bg-white border text-gray-600 hover:bg-gray-50 flex items-center gap-1"><SkipForward size={12} /> {lbl}</button>);
  if (['skip','merge','remap'].includes(f.suggested_action)) return btn('Ignorer', f.staging_compteur_id ? skipC : skipA);
  if (['fix_siret','create_entite','fix_address'].includes(f.suggested_action)) return btn('Ignorer', skipS);
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
  if (ev.numero_serie && !ev.field && !ev.reason) p.push(`Compteur: ${ev.numero_serie || ev.meter_id}`);
  if (!p.length && ev.site_name) p.push(ev.site_name);
  return p.length ? <p className="text-xs text-gray-600 mt-1">{p.join(' — ')}</p> : null;
}

export default PatrimoineWizard;
