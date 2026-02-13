/**
 * PROMEOS - PatrimoineWizard (DIAMANT)
 * 6-step staging pipeline: mode → upload → summary → corrections → validation → activation result.
 */
import React, { useState } from 'react';
import {
  X, ChevronRight, ChevronLeft, Check, Upload,
  FileSpreadsheet, AlertTriangle, ShieldCheck, Zap,
  Building2, LayoutGrid, Play, XCircle, ArrowRightLeft,
  SkipForward, RefreshCw, CheckCircle2, Info,
} from 'lucide-react';
import {
  stagingImport, stagingSummary, stagingValidate,
  stagingFix, stagingActivate, loadPatrimoineDemo,
} from '../services/api';

const STEPS = [
  { key: 'mode', label: 'Mode' },
  { key: 'upload', label: 'Import' },
  { key: 'summary', label: 'Apercu' },
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

const SEVERITY_COLORS = {
  blocking: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', badge: 'bg-red-100 text-red-700' },
  warning: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', badge: 'bg-amber-100 text-amber-700' },
  info: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', badge: 'bg-blue-100 text-blue-700' },
};

const PatrimoineWizard = ({ onClose }) => {
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // State
  const [mode, setMode] = useState('import');
  const [file, setFile] = useState(null);
  const [csvPreview, setCsvPreview] = useState(null);
  const [batchId, setBatchId] = useState(null);
  const [summary, setSummary] = useState(null);
  const [findings, setFindings] = useState([]);
  const [activationResult, setActivationResult] = useState(null);
  const [portefeuilleId, setPortefeuilleId] = useState('');
  const [demoResult, setDemoResult] = useState(null);

  // ── Helpers ──

  const handleFileSelect = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setError(null);
    const reader = new FileReader();
    reader.onload = (ev) => {
      const lines = ev.target.result.split('\n').filter(l => l.trim());
      setCsvPreview(lines.slice(0, 6));
    };
    reader.readAsText(f);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f) {
      setFile(f);
      setError(null);
      const reader = new FileReader();
      reader.onload = (ev) => {
        const lines = ev.target.result.split('\n').filter(l => l.trim());
        setCsvPreview(lines.slice(0, 6));
      };
      reader.readAsText(f);
    }
  };

  const doUpload = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await stagingImport(file, mode);
      setBatchId(result.batch_id);
      if (result.parse_errors?.length > 0) {
        setError(`${result.parse_errors.length} erreur(s) de parsing (lignes ignorees).`);
      }
      // Load summary
      const sum = await stagingSummary(result.batch_id);
      setSummary(sum);
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
      if (result.can_activate) {
        setStep(4); // Skip corrections if clean
      } else {
        setStep(3);
      }
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
      // Refresh findings
      const result = await stagingValidate(batchId);
      setFindings(result.findings || []);
      const sum = await stagingSummary(batchId);
      setSummary(sum);
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
      const result = await stagingActivate(batchId, pfId);
      setActivationResult(result);
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
      const result = await loadPatrimoineDemo();
      setDemoResult(result);
      setStep(5);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleNext = () => {
    if (mode === 'demo' && step === 0) { doDemo(); return; }
    if (step === 0) { setStep(1); return; }
    if (step === 1) { doUpload(); return; }
    if (step === 2) { doValidate(); return; }
    if (step === 3) { setStep(4); return; } // go to validation
    if (step === 4) { doActivate(); return; }
    if (step === 5) { handleClose(); return; }
  };

  const handleClose = () => {
    if (activationResult || demoResult) window.location.reload();
    else onClose();
  };

  const canProceed = () => {
    if (step === 0) return !!mode;
    if (step === 1) return file !== null;
    if (step === 2) return summary !== null;
    if (step === 3) return true;
    if (step === 4) return summary?.can_activate !== false;
    return true;
  };

  const unresolvedBlocking = findings.filter(f => f.severity === 'blocking' && !f.resolved);

  // ── Render ──

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
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
                  i < step ? 'bg-indigo-600 text-white' :
                  i === step ? 'bg-indigo-100 text-indigo-700 ring-2 ring-indigo-600' :
                  'bg-gray-100 text-gray-400'
                }`}>
                  {i < step ? <Check size={12} /> : i + 1}
                </div>
                <span className="hidden lg:inline">{s.label}</span>
              </div>
              {i < STEPS.length - 1 && <div className={`flex-1 h-0.5 ${i < step ? 'bg-indigo-600' : 'bg-gray-200'}`} />}
            </React.Fragment>
          ))}
        </div>

        {/* Step content */}
        <div className="px-6 py-5 min-h-[340px]">

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
                      className={`text-left p-4 border-2 rounded-xl transition ${
                        mode === m.value ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200 hover:border-gray-300'
                      }`}>
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
              <p className="text-sm text-gray-500 mb-4">Format CSV ou Excel. Colonnes attendues: nom, adresse, code_postal, ville, surface_m2, type, siret, numero_serie, meter_id, type_compteur, puissance_kw</p>

              <div
                onDragOver={e => e.preventDefault()}
                onDrop={handleDrop}
                className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center hover:border-indigo-400 transition"
              >
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

          {/* Step 2: Summary */}
          {step === 2 && summary && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">Apercu du staging</h3>
              <p className="text-sm text-gray-500 mb-4">Donnees importees dans la zone de staging (pas encore actives).</p>

              <div className="grid grid-cols-4 gap-3 mb-4">
                <StatCard label="Sites" value={summary.sites} icon={Building2} color="indigo" />
                <StatCard label="Compteurs" value={summary.compteurs} icon={Zap} color="amber" />
                <StatCard label="Findings" value={summary.findings_total || 0} icon={AlertTriangle} color="orange" />
                <StatCard label="Score qualite" value={`${summary.quality_score || 0}%`} icon={ShieldCheck}
                  color={summary.quality_score >= 80 ? 'green' : summary.quality_score >= 50 ? 'amber' : 'red'} />
              </div>

              <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3">
                <p className="text-sm text-indigo-700">
                  Cliquez sur "Valider" pour lancer le quality gate (5 regles de controle).
                </p>
              </div>
            </div>
          )}

          {/* Step 3: Corrections */}
          {step === 3 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">Corrections</h3>
              <p className="text-sm text-gray-500 mb-4">
                {unresolvedBlocking.length > 0
                  ? `${unresolvedBlocking.length} probleme(s) bloquant(s) a resoudre avant activation.`
                  : 'Aucun probleme bloquant. Vous pouvez continuer.'}
              </p>

              <div className="space-y-2 max-h-64 overflow-y-auto">
                {findings.map((f, i) => {
                  const sev = SEVERITY_COLORS[f.severity] || SEVERITY_COLORS.info;
                  let evidence = {};
                  try { evidence = JSON.parse(f.evidence || '{}'); } catch {}
                  return (
                    <div key={f.id || i} className={`${sev.bg} ${sev.border} border rounded-lg p-3`}>
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${sev.badge}`}>{f.severity}</span>
                          <span className="text-sm font-medium text-gray-800">{f.rule_id}</span>
                          {f.resolved && <CheckCircle2 size={14} className="text-green-500" />}
                        </div>
                        {!f.resolved && (
                          <div className="flex items-center gap-1">
                            {f.suggested_action === 'skip' && (
                              <button onClick={() => doFix(f, 'skip', { staging_site_id: f.staging_site_id, staging_compteur_id: f.staging_compteur_id })}
                                className="text-xs px-2 py-1 rounded bg-white border text-gray-600 hover:bg-gray-50 flex items-center gap-1">
                                <SkipForward size={12} /> Ignorer
                              </button>
                            )}
                            {f.suggested_action === 'merge' && (
                              <button onClick={() => doFix(f, 'skip', { staging_site_id: f.staging_site_id, staging_compteur_id: f.staging_compteur_id })}
                                className="text-xs px-2 py-1 rounded bg-white border text-gray-600 hover:bg-gray-50 flex items-center gap-1">
                                <ArrowRightLeft size={12} /> Ignorer doublon
                              </button>
                            )}
                            {f.suggested_action === 'remap' && (
                              <button onClick={() => doFix(f, 'skip', { staging_compteur_id: f.staging_compteur_id })}
                                className="text-xs px-2 py-1 rounded bg-white border text-gray-600 hover:bg-gray-50 flex items-center gap-1">
                                <XCircle size={12} /> Ignorer
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                      <p className="text-xs text-gray-600 mt-1">
                        {evidence.site_a && evidence.site_b && `"${evidence.site_a}" ↔ "${evidence.site_b}" (similarite: ${evidence.similarity})`}
                        {evidence.value && `Champ: ${evidence.field} = "${evidence.value}"`}
                        {evidence.missing_fields && `Champs manquants: ${evidence.missing_fields.join(', ')} (${evidence.site_name})`}
                        {evidence.siret && `SIRET "${evidence.siret}" non reconnu (${evidence.site_name})`}
                        {evidence.numero_serie && !evidence.field && `Compteur: ${evidence.numero_serie || evidence.meter_id}`}
                      </p>
                    </div>
                  );
                })}
                {findings.length === 0 && (
                  <div className="text-center py-8 text-gray-400">
                    <CheckCircle2 size={32} className="mx-auto mb-2" />
                    <p className="text-sm">Aucun probleme detecte</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Step 4: Final validation */}
          {step === 4 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">Validation finale</h3>
              <p className="text-sm text-gray-500 mb-4">Verifiez le resume avant activation.</p>

              {summary && (
                <div className="bg-gray-50 border rounded-lg p-4 space-y-2 mb-4">
                  <Row label="Sites a creer" value={summary.sites} />
                  <Row label="Compteurs a creer" value={summary.compteurs} />
                  <Row label="Problemes bloquants" value={summary.blocking || 0} valueClass={summary.blocking > 0 ? 'text-red-600 font-bold' : 'text-green-600'} />
                  <Row label="Score qualite" value={`${summary.quality_score || 0}%`} />
                  <Row label="Peut etre active" value={summary.can_activate ? 'Oui' : 'Non'}
                    valueClass={summary.can_activate ? 'text-green-600 font-bold' : 'text-red-600 font-bold'} />
                </div>
              )}

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">Portefeuille cible (ID)</label>
                <input type="number" value={portefeuilleId} onChange={e => setPortefeuilleId(e.target.value)}
                  placeholder="1" min="1"
                  className="w-40 border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none" />
                <p className="text-xs text-gray-400 mt-1">Les sites seront crees dans ce portefeuille.</p>
              </div>

              {unresolvedBlocking.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start gap-2">
                  <AlertTriangle size={16} className="text-red-500 shrink-0 mt-0.5" />
                  <p className="text-sm text-red-700">
                    {unresolvedBlocking.length} probleme(s) bloquant(s) restant(s). Retournez a l'etape Corrections.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Step 5: Result */}
          {step === 5 && (
            <div>
              <div className="flex items-center gap-3 mb-4">
                <CheckCircle2 size={28} className="text-green-500" />
                <h3 className="text-xl font-bold text-gray-900">
                  {demoResult ? 'Demo chargee !' : 'Patrimoine active !'}
                </h3>
              </div>

              {activationResult && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 space-y-2">
                  <Row label="Sites crees" value={activationResult.sites_created} />
                  <Row label="Compteurs crees" value={activationResult.compteurs_created} />
                  <Row label="Batiments" value={activationResult.batiments} />
                  <Row label="Obligations" value={activationResult.obligations} />
                </div>
              )}

              {demoResult && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 space-y-2">
                  <Row label="Statut" value={demoResult.status} />
                  <Row label="Organisation" value={demoResult.org_name || 'Collectivite Azur'} />
                  <Row label="Sites" value={demoResult.sites} />
                  <Row label="Compteurs" value={demoResult.compteurs} />
                  <Row label="Liens N-N" value={demoResult.nn_links} />
                </div>
              )}

              <p className="mt-4 text-sm text-gray-500">
                Fermez cette fenetre pour voir votre patrimoine mis a jour.
              </p>
            </div>
          )}

          {/* Error display */}
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
              <AlertTriangle size={18} className="text-red-500 shrink-0 mt-0.5" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t bg-gray-50 rounded-b-2xl">
          <button
            onClick={() => step > 0 && step < 5 ? setStep(step - 1) : handleClose()}
            className="flex items-center gap-1 text-gray-600 hover:text-gray-800 text-sm"
          >
            <ChevronLeft size={16} />
            {step > 0 && step < 5 ? 'Precedent' : 'Fermer'}
          </button>

          <div className="flex items-center gap-2">
            {step === 3 && (
              <button onClick={() => { doValidate(); }}
                className="flex items-center gap-1 px-3 py-2 text-sm text-gray-500 hover:text-gray-700">
                <RefreshCw size={14} /> Re-valider
              </button>
            )}

            {step < 5 && (
              <button
                onClick={handleNext}
                disabled={!canProceed() || loading}
                className={`flex items-center gap-1 px-5 py-2 rounded-lg text-sm font-semibold transition ${
                  !canProceed() || loading
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    : step === 4
                      ? 'bg-gradient-to-r from-green-500 to-emerald-600 text-white hover:from-green-600 hover:to-emerald-700'
                      : 'bg-indigo-600 text-white hover:bg-indigo-700'
                }`}
              >
                {loading ? 'Chargement...' :
                 step === 0 && mode === 'demo' ? 'Charger la demo' :
                 step === 2 ? 'Lancer la validation' :
                 step === 4 ? 'Activer le patrimoine' :
                 'Suivant'}
                {!loading && <ChevronRight size={16} />}
              </button>
            )}

            {step === 5 && (
              <button onClick={handleClose}
                className="flex items-center gap-1 px-5 py-2 rounded-lg text-sm font-semibold bg-indigo-600 text-white hover:bg-indigo-700 transition">
                Voir le patrimoine
                <ChevronRight size={16} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// ── Sub-components ──

function StatCard({ label, value, icon: Icon, color }) {
  const colors = {
    indigo: 'bg-indigo-50 text-indigo-700',
    amber: 'bg-amber-50 text-amber-700',
    orange: 'bg-orange-50 text-orange-700',
    green: 'bg-green-50 text-green-700',
    red: 'bg-red-50 text-red-700',
  };
  return (
    <div className={`${colors[color] || colors.indigo} rounded-lg p-3 text-center`}>
      <Icon size={18} className="mx-auto mb-1" />
      <div className="text-xl font-bold">{value}</div>
      <div className="text-[10px] uppercase tracking-wide">{label}</div>
    </div>
  );
}

function Row({ label, value, valueClass = '' }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-gray-600">{label}</span>
      <span className={`font-medium ${valueClass}`}>{String(value)}</span>
    </div>
  );
}

export default PatrimoineWizard;
