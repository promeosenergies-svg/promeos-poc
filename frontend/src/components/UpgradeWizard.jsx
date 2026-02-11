import React, { useState, useEffect } from 'react';
import { useDemo } from '../contexts/DemoContext';
import {
  X, ChevronRight, ChevronLeft, Building2,
  FileSpreadsheet, Check, Rocket, Sparkles, AlertTriangle, Upload,
} from 'lucide-react';
import { createOnboarding, importSitesCsv, getDemoTemplates } from '../services/api';

const STEPS = [
  { key: 'bienvenue', label: 'Bienvenue' },
  { key: 'organisation', label: 'Organisation' },
  { key: 'sites', label: 'Import Sites' },
  { key: 'confirmation', label: 'Confirmation' },
];

const TYPE_CLIENT_OPTIONS = [
  { value: 'retail', label: 'Retail / Grande distribution' },
  { value: 'industrie', label: 'Industrie' },
  { value: 'tertiaire', label: 'Tertiaire / Bureaux' },
  { value: 'copropriete', label: 'Syndic / Copropriete' },
  { value: 'logement_social', label: 'Bailleur social' },
  { value: 'collectivite', label: 'Collectivite territoriale' },
  { value: 'hotellerie', label: 'Hotellerie / Residences' },
  { value: 'sante', label: 'Sante / Medico-social' },
  { value: 'enseignement', label: 'Enseignement' },
  { value: 'mixte', label: 'Patrimoine mixte' },
];

const UpgradeWizard = ({ onClose }) => {
  const { toggleDemo } = useDemo();
  const [step, setStep] = useState(0);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [csvFile, setCsvFile] = useState(null);
  const [csvPreview, setCsvPreview] = useState(null);

  const [formData, setFormData] = useState({
    mode: 'real',
    selectedTemplate: 'casino_retail',
    orgNom: '',
    orgSiren: '',
    orgType: 'tertiaire',
    portefeuilleName: '',
    importMethod: 'csv',
    manualSite: { nom: '', adresse: '', code_postal: '', ville: '', surface_m2: '', naf_code: '' },
  });

  useEffect(() => {
    getDemoTemplates()
      .then(data => setTemplates(data.templates || []))
      .catch(() => {});
  }, []);

  const updateField = (key, value) => {
    setFormData(prev => ({ ...prev, [key]: value }));
  };

  const updateManualSite = (key, value) => {
    setFormData(prev => ({
      ...prev,
      manualSite: { ...prev.manualSite, [key]: value },
    }));
  };

  const handleCsvSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setCsvFile(file);
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target.result;
      const lines = text.split('\n').filter(l => l.trim());
      setCsvPreview(lines.slice(0, 6));
    };
    reader.readAsText(file);
  };

  const handleFinish = async () => {
    setLoading(true);
    setError(null);

    try {
      if (formData.mode === 'demo') {
        await toggleDemo();
        onClose();
        return;
      }

      const sites = [];
      if (formData.importMethod === 'manual' && formData.manualSite.nom) {
        sites.push({
          nom: formData.manualSite.nom,
          adresse: formData.manualSite.adresse || null,
          code_postal: formData.manualSite.code_postal || null,
          ville: formData.manualSite.ville || null,
          surface_m2: formData.manualSite.surface_m2 ? parseFloat(formData.manualSite.surface_m2) : null,
          naf_code: formData.manualSite.naf_code || null,
        });
      }

      const payload = {
        organisation: {
          nom: formData.orgNom,
          siren: formData.orgSiren || null,
          type_client: formData.orgType,
        },
        portefeuilles: formData.portefeuilleName
          ? [{ nom: formData.portefeuilleName }]
          : [{ nom: 'Principal' }],
        sites: sites.length > 0 ? sites : undefined,
      };

      const onboardResult = await createOnboarding(payload);

      let csvResult = null;
      if (formData.importMethod === 'csv' && csvFile) {
        csvResult = await importSitesCsv(csvFile);
      }

      setResult({
        ...onboardResult,
        csv_imported: csvResult?.imported || 0,
        csv_errors: csvResult?.errors || 0,
      });
      setStep(3);

    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (result) {
      window.location.reload();
    } else {
      onClose();
    }
  };

  const canProceed = () => {
    if (step === 0) return true;
    if (step === 1) return formData.mode === 'demo' || formData.orgNom.trim().length > 0;
    if (step === 2) {
      if (formData.mode === 'demo') return true;
      if (formData.importMethod === 'csv') return csvFile !== null;
      if (formData.importMethod === 'manual') return formData.manualSite.nom.trim().length > 0;
      return true;
    }
    return true;
  };

  const handleNext = () => {
    if (step === 2 && formData.mode !== 'demo') {
      handleFinish();
    } else if (step === 2 && formData.mode === 'demo') {
      handleFinish();
    } else if (step < STEPS.length - 1) {
      setStep(step + 1);
    } else {
      handleClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div className="flex items-center gap-2">
            <Rocket size={22} className="text-blue-600" />
            <h2 className="text-lg font-bold text-gray-900">Configurer mon patrimoine</h2>
          </div>
          <button onClick={handleClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        {/* Step indicator */}
        <div className="px-6 py-4 flex items-center gap-2">
          {STEPS.map((s, i) => (
            <React.Fragment key={s.key}>
              <div className={`flex items-center gap-1.5 text-sm ${
                i <= step ? 'text-blue-600 font-medium' : 'text-gray-400'
              }`}>
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                  i < step ? 'bg-blue-600 text-white' :
                  i === step ? 'bg-blue-100 text-blue-700 ring-2 ring-blue-600' :
                  'bg-gray-100 text-gray-400'
                }`}>
                  {i < step ? <Check size={14} /> : i + 1}
                </div>
                <span className="hidden md:inline">{s.label}</span>
              </div>
              {i < STEPS.length - 1 && (
                <div className={`flex-1 h-0.5 ${i < step ? 'bg-blue-600' : 'bg-gray-200'}`} />
              )}
            </React.Fragment>
          ))}
        </div>

        {/* Step content */}
        <div className="px-6 py-6 min-h-[300px]">

          {/* Step 0: Bienvenue */}
          {step === 0 && (
            <div>
              <div className="flex items-center gap-3 mb-4">
                <Sparkles size={28} className="text-indigo-500" />
                <h3 className="text-xl font-bold text-gray-900">Bienvenue dans PROMEOS</h3>
              </div>
              <p className="text-gray-600 mb-6">
                PROMEOS transforme votre patrimoine immobilier en un plan d'action
                concret pour la conformite energetique.
              </p>
              <div className="space-y-3">
                <label className={`flex items-start gap-3 p-4 border rounded-lg cursor-pointer transition ${
                  formData.mode === 'real' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
                }`}>
                  <input type="radio" name="mode" checked={formData.mode === 'real'}
                    onChange={() => updateField('mode', 'real')} className="mt-1" />
                  <div>
                    <div className="font-medium text-gray-900">Configurer mon patrimoine</div>
                    <div className="text-sm text-gray-500">
                      Creez votre organisation et importez vos sites reels (CSV ou saisie manuelle).
                    </div>
                  </div>
                </label>
                <label className={`flex items-start gap-3 p-4 border rounded-lg cursor-pointer transition ${
                  formData.mode === 'demo' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
                }`}>
                  <input type="radio" name="mode" checked={formData.mode === 'demo'}
                    onChange={() => updateField('mode', 'demo')} className="mt-1" />
                  <div>
                    <div className="font-medium text-gray-900">Explorer en mode demo</div>
                    <div className="text-sm text-gray-500">
                      Decouvrez la plateforme avec 120 sites de demonstration pre-charges.
                    </div>
                  </div>
                </label>
              </div>
            </div>
          )}

          {/* Step 1: Organisation (demo) */}
          {step === 1 && formData.mode === 'demo' && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">Choisir un profil demo</h3>
              <p className="text-sm text-gray-500 mb-6">Selectionnez un profil de demonstration.</p>
              <div className="space-y-3">
                {templates.map(tpl => (
                  <label key={tpl.id} className={`flex items-start gap-3 p-4 border rounded-lg cursor-pointer transition ${
                    formData.selectedTemplate === tpl.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
                  }`}>
                    <input type="radio" name="template" checked={formData.selectedTemplate === tpl.id}
                      onChange={() => updateField('selectedTemplate', tpl.id)} className="mt-1" />
                    <div>
                      <div className="font-medium text-gray-900">{tpl.label}</div>
                      <div className="text-sm text-gray-500">{tpl.description}</div>
                      <div className="flex gap-3 mt-1 text-xs text-gray-400">
                        <span>{tpl.stats_preview.total_sites} sites</span>
                        <span>Risque: {tpl.stats_preview.risque_financier}</span>
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Step 1: Organisation (real) */}
          {step === 1 && formData.mode === 'real' && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">Votre organisation</h3>
              <p className="text-sm text-gray-500 mb-6">
                Renseignez les informations de votre organisation.
              </p>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nom de l'organisation *
                  </label>
                  <input type="text" value={formData.orgNom}
                    onChange={e => updateField('orgNom', e.target.value)}
                    placeholder="Ex: Nexity Immobilier, Ville de Lyon, OPH 93..."
                    className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">SIREN</label>
                    <input type="text" value={formData.orgSiren}
                      onChange={e => updateField('orgSiren', e.target.value)}
                      placeholder="9 chiffres" maxLength={9}
                      className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Type de client</label>
                    <select value={formData.orgType} onChange={e => updateField('orgType', e.target.value)}
                      className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
                      {TYPE_CLIENT_OPTIONS.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nom du portefeuille</label>
                  <input type="text" value={formData.portefeuilleName}
                    onChange={e => updateField('portefeuilleName', e.target.value)}
                    placeholder="Ex: Patrimoine IDF (laissez vide pour 'Principal')"
                    className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Import Sites (demo) */}
          {step === 2 && formData.mode === 'demo' && (
            <div>
              <div className="flex items-center gap-3 mb-4">
                <Check size={28} className="text-green-500" />
                <h3 className="text-xl font-bold text-gray-900">Pret a demarrer</h3>
              </div>
              <p className="text-gray-600 mb-4">
                Le mode demo sera active avec 120 sites de demonstration.
              </p>
            </div>
          )}

          {/* Step 2: Import Sites (real) */}
          {step === 2 && formData.mode === 'real' && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">Import de vos sites</h3>
              <p className="text-sm text-gray-500 mb-6">Comment souhaitez-vous ajouter vos sites ?</p>

              <div className="flex gap-3 mb-6">
                {[
                  { value: 'csv', icon: FileSpreadsheet, title: 'Import CSV' },
                  { value: 'manual', icon: Building2, title: 'Saisie manuelle' },
                ].map(opt => {
                  const Icon = opt.icon;
                  return (
                    <button key={opt.value}
                      onClick={() => updateField('importMethod', opt.value)}
                      className={`flex-1 flex items-center gap-2 p-3 border rounded-lg text-sm transition ${
                        formData.importMethod === opt.value
                          ? 'border-blue-500 bg-blue-50 text-blue-700 font-medium'
                          : 'border-gray-200 text-gray-600 hover:border-gray-300'
                      }`}>
                      <Icon size={18} />
                      {opt.title}
                    </button>
                  );
                })}
              </div>

              {formData.importMethod === 'csv' && (
                <div>
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                    <Upload size={32} className="mx-auto text-gray-400 mb-2" />
                    <p className="text-sm text-gray-600 mb-2">
                      Glissez votre fichier CSV ou cliquez pour selectionner
                    </p>
                    <input type="file" accept=".csv,.txt" onChange={handleCsvSelect}
                      className="text-sm text-gray-500 file:mr-4 file:py-1 file:px-3 file:rounded file:border-0 file:text-sm file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100" />
                  </div>
                  <div className="mt-3 p-3 bg-gray-50 rounded text-xs text-gray-500">
                    Format : <code>nom,adresse,code_postal,ville,surface_m2,type,naf_code</code><br />
                    Le type est auto-detecte via le code NAF si non renseigne.
                  </div>
                  {csvPreview && (
                    <div className="mt-4">
                      <p className="text-sm font-medium text-gray-700 mb-2">Apercu ({csvFile?.name})</p>
                      <div className="bg-gray-50 rounded border text-xs font-mono overflow-x-auto p-2 max-h-32">
                        {csvPreview.map((line, i) => (
                          <div key={i} className={i === 0 ? 'font-bold text-blue-700' : 'text-gray-600'}>
                            {line}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {formData.importMethod === 'manual' && (
                <div className="space-y-3">
                  <p className="text-sm text-gray-500">
                    Ajoutez un premier site. Vous pourrez en ajouter d'autres ensuite.
                  </p>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Nom du site *</label>
                    <input type="text" value={formData.manualSite.nom}
                      onChange={e => updateManualSite('nom', e.target.value)}
                      placeholder="Ex: Siege social, Residence Les Lilas..."
                      className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Ville</label>
                      <input type="text" value={formData.manualSite.ville}
                        onChange={e => updateManualSite('ville', e.target.value)}
                        placeholder="Paris" className="w-full border rounded-lg px-3 py-2 text-sm outline-none" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Code postal</label>
                      <input type="text" value={formData.manualSite.code_postal}
                        onChange={e => updateManualSite('code_postal', e.target.value)}
                        placeholder="75008" maxLength={5} className="w-full border rounded-lg px-3 py-2 text-sm outline-none" />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Surface (m2)</label>
                      <input type="number" value={formData.manualSite.surface_m2}
                        onChange={e => updateManualSite('surface_m2', e.target.value)}
                        placeholder="2500" className="w-full border rounded-lg px-3 py-2 text-sm outline-none" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Code NAF</label>
                      <input type="text" value={formData.manualSite.naf_code}
                        onChange={e => updateManualSite('naf_code', e.target.value)}
                        placeholder="68.32A" className="w-full border rounded-lg px-3 py-2 text-sm outline-none" />
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 3: Confirmation */}
          {step === 3 && result && (
            <div>
              <div className="flex items-center gap-3 mb-4">
                <Check size={28} className="text-green-500" />
                <h3 className="text-xl font-bold text-gray-900">Patrimoine cree !</h3>
              </div>
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Organisation</span>
                  <span className="font-medium">{formData.orgNom}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Portefeuilles</span>
                  <span className="font-medium">{result.portefeuille_ids?.length || 1}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Sites crees</span>
                  <span className="font-medium">{(result.sites_created || 0) + (result.csv_imported || 0)}</span>
                </div>
                {result.csv_errors > 0 && (
                  <div className="flex justify-between text-sm text-orange-600">
                    <span>Erreurs CSV</span>
                    <span className="font-medium">{result.csv_errors}</span>
                  </div>
                )}
              </div>
              {result.sites?.length > 0 && (
                <div className="mt-4">
                  <p className="text-sm font-medium text-gray-700 mb-2">Sites provisionnes :</p>
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {result.sites.map(s => (
                      <div key={s.id} className="flex items-center justify-between text-sm bg-gray-50 rounded px-3 py-1.5">
                        <span>{s.nom}</span>
                        <span className="text-xs text-gray-400">{s.type} | {s.obligations} obligation(s)</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <p className="mt-4 text-sm text-gray-500">
                Fermez cette fenetre pour acceder a votre cockpit personnalise.
              </p>
            </div>
          )}

          {step === 3 && !result && (
            <div>
              <div className="flex items-center gap-3 mb-4">
                <Sparkles size={28} className="text-indigo-500" />
                <h3 className="text-xl font-bold text-gray-900">Mode demo active</h3>
              </div>
              <p className="text-gray-600">
                Explorez PROMEOS avec 120 sites de demonstration.
              </p>
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
          <button
            onClick={() => step > 0 && !result ? setStep(step - 1) : handleClose()}
            className="flex items-center gap-1 text-gray-600 hover:text-gray-800 text-sm"
          >
            <ChevronLeft size={16} />
            {step > 0 && !result ? 'Precedent' : 'Fermer'}
          </button>
          {step < 3 && (
            <button
              onClick={handleNext}
              disabled={!canProceed() || loading}
              className={`flex items-center gap-1 px-6 py-2 rounded-lg text-sm font-semibold transition ${
                !canProceed() || loading
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : step === 2
                    ? 'bg-gradient-to-r from-green-500 to-emerald-600 text-white hover:from-green-600 hover:to-emerald-700'
                    : 'bg-blue-600 text-white hover:bg-blue-700'
              }`}
            >
              {loading ? 'Creation en cours...' :
               step === 2 && formData.mode === 'real' ? 'Creer mon patrimoine' :
               step === 2 && formData.mode === 'demo' ? 'Activer le mode demo' :
               'Suivant'}
              {!loading && <ChevronRight size={16} />}
            </button>
          )}
          {step === 3 && (
            <button onClick={handleClose}
              className="flex items-center gap-1 px-6 py-2 rounded-lg text-sm font-semibold bg-blue-600 text-white hover:bg-blue-700 transition">
              Acceder au cockpit
              <ChevronRight size={16} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default UpgradeWizard;
