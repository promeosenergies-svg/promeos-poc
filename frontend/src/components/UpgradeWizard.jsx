import React, { useState, useEffect } from 'react';
import { useDemo } from '../contexts/DemoContext';
import {
  X, ChevronRight, ChevronLeft, Building2,
  FileSpreadsheet, Check, Rocket, Sparkles,
} from 'lucide-react';

const API = 'http://127.0.0.1:8000';

const STEPS = [
  { key: 'bienvenue', label: 'Bienvenue' },
  { key: 'organisation', label: 'Organisation' },
  { key: 'sites', label: 'Import Sites' },
  { key: 'confirmation', label: 'Confirmation' },
];

const UpgradeWizard = ({ onClose }) => {
  const { toggleDemo } = useDemo();
  const [step, setStep] = useState(0);
  const [templates, setTemplates] = useState([]);
  const [formData, setFormData] = useState({
    orgNom: '',
    orgSiren: '',
    orgType: 'retail',
    importMethod: 'demo',
    selectedTemplate: 'casino_retail',
  });

  useEffect(() => {
    fetch(`${API}/api/demo/templates`)
      .then(r => r.json())
      .then(data => setTemplates(data.templates || []))
      .catch(() => {});
  }, []);

  const updateField = (key, value) => {
    setFormData(prev => ({ ...prev, [key]: value }));
  };

  const handleFinish = async () => {
    await toggleDemo();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div className="flex items-center gap-2">
            <Rocket size={22} className="text-blue-600" />
            <h2 className="text-lg font-bold text-gray-900">
              Rendre mon patrimoine actionnable
            </h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
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
                <h3 className="text-xl font-bold text-gray-900">
                  Bienvenue dans PROMEOS
                </h3>
              </div>
              <p className="text-gray-600 mb-6">
                PROMEOS transforme votre patrimoine immobilier en un plan d'action
                concret pour la conformite energetique. Choisissez un profil demo
                pour decouvrir la plateforme, ou passez directement a vos donnees reelles.
              </p>
              <div className="space-y-3">
                {templates.map(tpl => (
                  <label
                    key={tpl.id}
                    className={`flex items-start gap-3 p-4 border rounded-lg cursor-pointer transition ${
                      formData.selectedTemplate === tpl.id
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <input
                      type="radio"
                      name="template"
                      checked={formData.selectedTemplate === tpl.id}
                      onChange={() => updateField('selectedTemplate', tpl.id)}
                      className="mt-1"
                    />
                    <div>
                      <div className="font-medium text-gray-900">{tpl.label}</div>
                      <div className="text-sm text-gray-500">{tpl.description}</div>
                      <div className="flex gap-3 mt-1 text-xs text-gray-400">
                        <span>{tpl.stats_preview.total_sites} sites</span>
                        <span>Risque: {tpl.stats_preview.risque_financier}</span>
                        <span>BACS: {tpl.stats_preview.bacs_concernes}</span>
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Step 1: Organisation */}
          {step === 1 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">
                Votre organisation
              </h3>
              <p className="text-sm text-gray-500 mb-6">
                Renseignez les informations de votre organisation pour personnaliser PROMEOS.
              </p>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nom de l'organisation
                  </label>
                  <input
                    type="text"
                    value={formData.orgNom}
                    onChange={e => updateField('orgNom', e.target.value)}
                    placeholder="Ex: Groupe Casino"
                    className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    SIREN
                  </label>
                  <input
                    type="text"
                    value={formData.orgSiren}
                    onChange={e => updateField('orgSiren', e.target.value)}
                    placeholder="Ex: 554008671"
                    maxLength={9}
                    className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Type de client
                  </label>
                  <select
                    value={formData.orgType}
                    onChange={e => updateField('orgType', e.target.value)}
                    className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  >
                    <option value="retail">Retail / Grande distribution</option>
                    <option value="industrie">Industrie</option>
                    <option value="tertiaire">Tertiaire / Bureaux</option>
                    <option value="logistique">Logistique / Entrepots</option>
                    <option value="mixte">Mixte</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Import Sites */}
          {step === 2 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">
                Import de vos sites
              </h3>
              <p className="text-sm text-gray-500 mb-6">
                Comment souhaitez-vous importer vos sites ?
              </p>
              <div className="space-y-3">
                {[
                  {
                    value: 'demo',
                    icon: Sparkles,
                    title: 'Garder les donnees demo',
                    desc: 'Continuez avec les 120 sites de demonstration pour explorer la plateforme.',
                  },
                  {
                    value: 'csv',
                    icon: FileSpreadsheet,
                    title: 'Import fichier CSV',
                    desc: 'Importez vos sites depuis un fichier CSV (nom, adresse, surface, type).',
                  },
                  {
                    value: 'manual',
                    icon: Building2,
                    title: 'Saisie manuelle',
                    desc: 'Ajoutez vos sites un par un directement dans la plateforme.',
                  },
                ].map(opt => {
                  const Icon = opt.icon;
                  return (
                    <label
                      key={opt.value}
                      className={`flex items-start gap-3 p-4 border rounded-lg cursor-pointer transition ${
                        formData.importMethod === opt.value
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <input
                        type="radio"
                        name="importMethod"
                        checked={formData.importMethod === opt.value}
                        onChange={() => updateField('importMethod', opt.value)}
                        className="mt-1"
                      />
                      <div className="flex items-start gap-3">
                        <Icon size={20} className="text-blue-600 mt-0.5 shrink-0" />
                        <div>
                          <div className="font-medium text-gray-900">{opt.title}</div>
                          <div className="text-sm text-gray-500">{opt.desc}</div>
                        </div>
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>
          )}

          {/* Step 3: Confirmation */}
          {step === 3 && (
            <div>
              <div className="flex items-center gap-3 mb-4">
                <Check size={28} className="text-green-500" />
                <h3 className="text-xl font-bold text-gray-900">
                  Pret a demarrer
                </h3>
              </div>
              <p className="text-gray-600 mb-6">
                Voici le resume de votre configuration. Cliquez sur "Activer le
                mode production" pour commencer.
              </p>
              <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Organisation</span>
                  <span className="font-medium text-gray-900">
                    {formData.orgNom || 'Non renseigne'}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">SIREN</span>
                  <span className="font-medium text-gray-900">
                    {formData.orgSiren || 'Non renseigne'}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Type</span>
                  <span className="font-medium text-gray-900">{formData.orgType}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Import</span>
                  <span className="font-medium text-gray-900">
                    {formData.importMethod === 'demo' ? 'Donnees demo' :
                     formData.importMethod === 'csv' ? 'Fichier CSV' : 'Saisie manuelle'}
                  </span>
                </div>
              </div>
              <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-sm text-blue-800">
                  Le mode production desactive la banniere demo. Vos donnees et
                  votre plan d'action restent disponibles. Vous pourrez reactiver
                  le mode demo a tout moment.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer navigation */}
        <div className="flex items-center justify-between px-6 py-4 border-t bg-gray-50 rounded-b-2xl">
          <button
            onClick={() => step > 0 ? setStep(step - 1) : onClose()}
            className="flex items-center gap-1 text-gray-600 hover:text-gray-800 text-sm"
          >
            <ChevronLeft size={16} />
            {step > 0 ? 'Precedent' : 'Annuler'}
          </button>
          <button
            onClick={() => step < STEPS.length - 1 ? setStep(step + 1) : handleFinish()}
            className={`flex items-center gap-1 px-6 py-2 rounded-lg text-sm font-semibold transition ${
              step < STEPS.length - 1
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gradient-to-r from-green-500 to-emerald-600 text-white hover:from-green-600 hover:to-emerald-700'
            }`}
          >
            {step < STEPS.length - 1 ? 'Suivant' : 'Activer le mode production'}
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default UpgradeWizard;
