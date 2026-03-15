import React, { useState, useEffect } from 'react';
import {
  X,
  ChevronRight,
  ChevronLeft,
  Building2,
  Building,
  MapPin,
  FileSpreadsheet,
  Check,
  Rocket,
  AlertTriangle,
  Upload,
  Zap,
  Plus,
  Trash2,
  SkipForward,
} from 'lucide-react';
import { createOnboarding, importSitesCsv, createCompteur } from '../services/api';

const STEPS = [
  { key: 'organisation', label: 'Societe' },
  { key: 'entite', label: 'Entité juridique' },
  { key: 'sites', label: 'Sites' },
  { key: 'compteurs', label: 'Compteurs' },
  { key: 'resume', label: 'Résumé' },
];

const TYPE_CLIENT_OPTIONS = [
  { value: 'retail', label: 'Retail / Grande distribution' },
  { value: 'industrie', label: 'Industrie' },
  { value: 'tertiaire', label: 'Tertiaire / Bureaux' },
  { value: 'copropriete', label: 'Syndic / Copropriété' },
  { value: 'logement_social', label: 'Bailleur social' },
  { value: 'collectivite', label: 'Collectivité territoriale' },
  { value: 'hotellerie', label: 'Hôtellerie / Résidences' },
  { value: 'sante', label: 'Santé / Médico-social' },
  { value: 'enseignement', label: 'Enseignement' },
  { value: 'mixte', label: 'Patrimoine mixte' },
];

const TYPE_SITE_OPTIONS = [
  { value: 'bureau', label: 'Bureau' },
  { value: 'commerce', label: 'Commerce' },
  { value: 'entrepot', label: 'Entrepôt' },
  { value: 'usine', label: 'Usine / Industrie' },
  { value: 'hotel', label: 'Hôtel' },
  { value: 'sante', label: 'Santé / EHPAD' },
  { value: 'enseignement', label: 'Enseignement' },
  { value: 'collectivite', label: 'Collectivité' },
  { value: 'copropriete', label: 'Copropriété' },
  { value: 'logement_social', label: 'Logement social' },
  { value: 'magasin', label: 'Magasin' },
];

const COMPTEUR_TYPES = [
  { value: 'electricite', label: 'Électricité' },
  { value: 'gaz', label: 'Gaz' },
  { value: 'eau', label: 'Eau' },
];

const emptySite = {
  nom: '',
  type: 'bureau',
  ville: '',
  code_postal: '',
  surface_m2: '',
  naf_code: '',
};
const emptyCompteur = { site_index: 0, type: 'electricite', numero_serie: '', puissance_kw: '' };

const UpgradeWizard = ({ onClose }) => {
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [csvFile, setCsvFile] = useState(null);
  const [csvPreview, setCsvPreview] = useState(null);

  const [formData, setFormData] = useState({
    orgNom: '',
    orgSiren: '',
    orgType: 'tertiaire',
    ejNom: '',
    ejSiren: '',
    importMethod: 'manual',
    sites: [{ ...emptySite }],
    compteurs: [],
  });

  useEffect(() => {
    if (step === 1 && !formData.ejNom) {
      setFormData((prev) => ({
        ...prev,
        ejNom: prev.orgNom,
        ejSiren: prev.orgSiren,
      }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step]);

  const updateField = (key, value) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
    setError(null);
  };

  const updateSite = (index, key, value) => {
    setFormData((prev) => {
      const sites = [...prev.sites];
      sites[index] = { ...sites[index], [key]: value };
      return { ...prev, sites };
    });
  };

  const addSite = () => {
    setFormData((prev) => ({ ...prev, sites: [...prev.sites, { ...emptySite }] }));
  };

  const removeSite = (index) => {
    setFormData((prev) => ({
      ...prev,
      sites: prev.sites.filter((_, i) => i !== index),
      compteurs: prev.compteurs
        .filter((c) => c.site_index !== index)
        .map((c) => ({ ...c, site_index: c.site_index > index ? c.site_index - 1 : c.site_index })),
    }));
  };

  const updateCompteur = (index, key, value) => {
    setFormData((prev) => {
      const compteurs = [...prev.compteurs];
      compteurs[index] = { ...compteurs[index], [key]: value };
      return { ...prev, compteurs };
    });
  };

  const addCompteur = () => {
    setFormData((prev) => ({
      ...prev,
      compteurs: [...prev.compteurs, { ...emptyCompteur }],
    }));
  };

  const removeCompteur = (index) => {
    setFormData((prev) => ({
      ...prev,
      compteurs: prev.compteurs.filter((_, i) => i !== index),
    }));
  };

  const handleCsvSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setCsvFile(file);
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target.result;
      const lines = text.split('\n').filter((l) => l.trim());
      setCsvPreview(lines.slice(0, 6));
    };
    reader.readAsText(file);
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);

    try {
      const sitesPayload =
        formData.importMethod === 'manual'
          ? formData.sites
              .filter((s) => s.nom.trim())
              .map((s) => ({
                nom: s.nom,
                type: s.type || null,
                code_postal: s.code_postal || null,
                ville: s.ville || null,
                surface_m2: s.surface_m2 ? parseFloat(s.surface_m2) : null,
                naf_code: s.naf_code || null,
              }))
          : [];

      const payload = {
        organisation: {
          nom: formData.orgNom,
          siren: formData.orgSiren || null,
          type_client: formData.orgType,
        },
        portefeuilles: [{ nom: 'Principal' }],
        sites: sitesPayload.length > 0 ? sitesPayload : undefined,
      };

      const onboardResult = await createOnboarding(payload);

      let csvResult = null;
      if (formData.importMethod === 'csv' && csvFile) {
        csvResult = await importSitesCsv(csvFile);
      }

      let compteursCreated = 0;
      if (formData.compteurs.length > 0 && onboardResult.sites?.length > 0) {
        for (const c of formData.compteurs) {
          const siteObj = onboardResult.sites[c.site_index];
          if (siteObj) {
            try {
              await createCompteur({
                site_id: siteObj.id,
                type: c.type,
                numero_serie: c.numero_serie || null,
                puissance_souscrite_kw: c.puissance_kw ? parseFloat(c.puissance_kw) : null,
              });
              compteursCreated++;
            } catch {
              /* skip individual compteur errors */
            }
          }
        }
      }

      setResult({
        ...onboardResult,
        csv_imported: csvResult?.imported || 0,
        csv_errors: csvResult?.errors || 0,
        compteurs_created: compteursCreated,
      });
      setStep(4);
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    onClose(!!result);
  };

  const canProceed = () => {
    if (step === 0) return formData.orgNom.trim().length > 0;
    if (step === 1) return true;
    if (step === 2) {
      if (formData.importMethod === 'csv') return csvFile !== null;
      return formData.sites.some((s) => s.nom.trim().length > 0);
    }
    if (step === 3) return true;
    return true;
  };

  const handleNext = () => {
    if (step === 3) {
      handleSubmit();
    } else if (step < STEPS.length - 1) {
      setStep(step + 1);
    } else {
      handleClose();
    }
  };

  const handleSkip = () => {
    if (step === 2) {
      setFormData((prev) => ({ ...prev, sites: [], compteurs: [] }));
      setStep(3);
    } else if (step === 3) {
      setFormData((prev) => ({ ...prev, compteurs: [] }));
      handleSubmit();
    }
  };

  return (
    <div className="fixed inset-0 z-[200] bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div className="flex items-center gap-2">
            <Rocket size={22} className="text-blue-600" />
            <h2 className="text-lg font-bold text-gray-900">Onboarding</h2>
          </div>
          <button onClick={handleClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        {/* Step indicator */}
        <div className="px-6 py-3 flex items-center gap-1">
          {STEPS.map((s, i) => (
            <React.Fragment key={s.key}>
              <div
                className={`flex items-center gap-1 text-xs ${
                  i <= step ? 'text-blue-600 font-medium' : 'text-gray-400'
                }`}
              >
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${
                    i < step
                      ? 'bg-blue-600 text-white'
                      : i === step
                        ? 'bg-blue-100 text-blue-700 ring-2 ring-blue-600'
                        : 'bg-gray-100 text-gray-400'
                  }`}
                >
                  {i < step ? <Check size={12} /> : i + 1}
                </div>
                <span className="hidden lg:inline">{s.label}</span>
              </div>
              {i < STEPS.length - 1 && (
                <div className={`flex-1 h-0.5 ${i < step ? 'bg-blue-600' : 'bg-gray-200'}`} />
              )}
            </React.Fragment>
          ))}
        </div>

        {/* Step content */}
        <div className="px-6 py-5 min-h-[320px]">
          {/* Step 0: Organisation */}
          {step === 0 && (
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Building2 size={20} className="text-blue-600" />
                <h3 className="text-lg font-semibold text-gray-900">Votre societe</h3>
              </div>
              <p className="text-sm text-gray-500 mb-5">Qui êtes-vous ?</p>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nom de la societe *
                  </label>
                  <input
                    type="text"
                    value={formData.orgNom}
                    onChange={(e) => updateField('orgNom', e.target.value)}
                    placeholder="Ex: Nexity, Ville de Lyon, OPH 93..."
                    className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      SIREN (optionnel)
                    </label>
                    <input
                      type="text"
                      value={formData.orgSiren}
                      onChange={(e) => updateField('orgSiren', e.target.value)}
                      placeholder="9 chiffres"
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
                      onChange={(e) => updateField('orgType', e.target.value)}
                      className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    >
                      {TYPE_CLIENT_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Step 1: Entite Juridique */}
          {step === 1 && (
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Building size={20} className="text-indigo-600" />
                <h3 className="text-lg font-semibold text-gray-900">Entité juridique</h3>
              </div>
              <p className="text-sm text-gray-500 mb-5">
                Qui signe les contrats ? (pré-rempli depuis l'organisation)
              </p>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Raison sociale
                  </label>
                  <input
                    type="text"
                    value={formData.ejNom}
                    onChange={(e) => updateField('ejNom', e.target.value)}
                    placeholder="Ex: Nexity SA"
                    className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">SIREN</label>
                  <input
                    type="text"
                    value={formData.ejSiren}
                    onChange={(e) => updateField('ejSiren', e.target.value)}
                    placeholder="9 chiffres"
                    maxLength={9}
                    className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <p className="text-xs text-blue-700">
                    L'entité juridique est créée automatiquement. Vous pourrez en ajouter d'autres
                    plus tard.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Sites */}
          {step === 2 && (
            <div>
              <div className="flex items-center gap-2 mb-1">
                <MapPin size={20} className="text-green-600" />
                <h3 className="text-lg font-semibold text-gray-900">Vos sites</h3>
              </div>
              <p className="text-sm text-gray-500 mb-4">Quels bâtiments gérez-vous ?</p>

              <div className="flex gap-2 mb-4">
                {[
                  { value: 'manual', icon: Building2, title: 'Saisie manuelle' },
                  { value: 'csv', icon: FileSpreadsheet, title: 'Import CSV' },
                ].map((opt) => {
                  const Icon = opt.icon;
                  return (
                    <button
                      key={opt.value}
                      onClick={() => updateField('importMethod', opt.value)}
                      className={`flex-1 flex items-center justify-center gap-2 p-2.5 border rounded-lg text-sm transition ${
                        formData.importMethod === opt.value
                          ? 'border-blue-500 bg-blue-50 text-blue-700 font-medium'
                          : 'border-gray-200 text-gray-600 hover:border-gray-300'
                      }`}
                    >
                      <Icon size={16} />
                      {opt.title}
                    </button>
                  );
                })}
              </div>

              {formData.importMethod === 'manual' && (
                <div className="space-y-3">
                  {formData.sites.map((site, i) => (
                    <div key={i} className="border rounded-lg p-3 bg-gray-50">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium text-gray-500">Site {i + 1}</span>
                        {formData.sites.length > 1 && (
                          <button
                            onClick={() => removeSite(i)}
                            className="text-gray-400 hover:text-red-500"
                          >
                            <Trash2 size={14} />
                          </button>
                        )}
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <input
                          type="text"
                          value={site.nom}
                          onChange={(e) => updateSite(i, 'nom', e.target.value)}
                          placeholder="Nom du site *"
                          className="col-span-2 border rounded px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-blue-500"
                        />
                        <select
                          value={site.type}
                          onChange={(e) => updateSite(i, 'type', e.target.value)}
                          className="border rounded px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-blue-500"
                        >
                          {TYPE_SITE_OPTIONS.map((o) => (
                            <option key={o.value} value={o.value}>
                              {o.label}
                            </option>
                          ))}
                        </select>
                        <input
                          type="text"
                          value={site.ville}
                          onChange={(e) => updateSite(i, 'ville', e.target.value)}
                          placeholder="Ville"
                          className="border rounded px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-blue-500"
                        />
                        <input
                          type="text"
                          value={site.code_postal}
                          onChange={(e) => updateSite(i, 'code_postal', e.target.value)}
                          placeholder="Code postal"
                          maxLength={5}
                          className="border rounded px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-blue-500"
                        />
                        <input
                          type="number"
                          value={site.surface_m2}
                          onChange={(e) => updateSite(i, 'surface_m2', e.target.value)}
                          placeholder="Surface m²"
                          className="border rounded px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-blue-500"
                        />
                      </div>
                    </div>
                  ))}
                  <button
                    onClick={addSite}
                    className="w-full flex items-center justify-center gap-1.5 py-2 border-2 border-dashed border-gray-300 rounded-lg text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600 transition"
                  >
                    <Plus size={14} /> Ajouter un site
                  </button>
                </div>
              )}

              {formData.importMethod === 'csv' && (
                <div>
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-5 text-center">
                    <Upload size={28} className="mx-auto text-gray-400 mb-2" />
                    <p className="text-sm text-gray-600 mb-2">
                      Glissez votre fichier CSV ou cliquez
                    </p>
                    <input
                      type="file"
                      accept=".csv,.txt"
                      onChange={handleCsvSelect}
                      className="text-sm text-gray-500 file:mr-3 file:py-1 file:px-3 file:rounded file:border-0 file:text-sm file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                    />
                  </div>
                  <p className="mt-2 text-xs text-gray-400">
                    Format : nom,adresse,code_postal,ville,surface_m2,type,naf_code
                  </p>
                  {csvPreview && (
                    <div className="mt-3">
                      <p className="text-xs font-medium text-gray-600 mb-1">
                        Aperçu ({csvFile?.name})
                      </p>
                      <div className="bg-gray-50 rounded border text-xs font-mono overflow-x-auto p-2 max-h-28">
                        {csvPreview.map((line, i) => (
                          <div
                            key={i}
                            className={i === 0 ? 'font-bold text-blue-700' : 'text-gray-600'}
                          >
                            {line}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Step 3: Compteurs */}
          {step === 3 && (
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Zap size={20} className="text-amber-500" />
                <h3 className="text-lg font-semibold text-gray-900">Compteurs</h3>
              </div>
              <p className="text-sm text-gray-500 mb-4">
                Rattachez des compteurs à vos sites (optionnel — ajoutables plus tard).
              </p>

              {formData.sites.filter((s) => s.nom.trim()).length === 0 &&
              formData.importMethod === 'manual' ? (
                <div className="bg-gray-50 border rounded-lg p-4 text-center text-sm text-gray-500">
                  Aucun site saisi. Les compteurs seront ajoutables après création.
                </div>
              ) : (
                <>
                  {formData.compteurs.map((c, i) => (
                    <div key={i} className="border rounded-lg p-3 bg-gray-50 mb-2">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium text-gray-500">Compteur {i + 1}</span>
                        <button
                          onClick={() => removeCompteur(i)}
                          className="text-gray-400 hover:text-red-500"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        {formData.importMethod === 'manual' && (
                          <select
                            value={c.site_index}
                            onChange={(e) =>
                              updateCompteur(i, 'site_index', parseInt(e.target.value))
                            }
                            className="col-span-2 border rounded px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-blue-500"
                          >
                            {formData.sites
                              .filter((s) => s.nom.trim())
                              .map((s, si) => (
                                <option key={si} value={si}>
                                  {s.nom || `Site ${si + 1}`}
                                </option>
                              ))}
                          </select>
                        )}
                        <select
                          value={c.type}
                          onChange={(e) => updateCompteur(i, 'type', e.target.value)}
                          className="border rounded px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-blue-500"
                        >
                          {COMPTEUR_TYPES.map((t) => (
                            <option key={t.value} value={t.value}>
                              {t.label}
                            </option>
                          ))}
                        </select>
                        <input
                          type="text"
                          value={c.numero_serie}
                          onChange={(e) => updateCompteur(i, 'numero_serie', e.target.value)}
                          placeholder="N° de série (optionnel)"
                          className="border rounded px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-blue-500"
                        />
                        {c.type === 'electricite' && (
                          <input
                            type="number"
                            value={c.puissance_kw}
                            onChange={(e) => updateCompteur(i, 'puissance_kw', e.target.value)}
                            placeholder="Puissance souscrite kW"
                            className="col-span-2 border rounded px-2.5 py-1.5 text-sm outline-none focus:ring-1 focus:ring-blue-500"
                          />
                        )}
                      </div>
                    </div>
                  ))}
                  <button
                    onClick={addCompteur}
                    className="w-full flex items-center justify-center gap-1.5 py-2 border-2 border-dashed border-gray-300 rounded-lg text-sm text-gray-500 hover:border-amber-400 hover:text-amber-600 transition"
                  >
                    <Plus size={14} /> Ajouter un compteur
                  </button>
                </>
              )}
            </div>
          )}

          {/* Step 4: Resume */}
          {step === 4 && result && (
            <div>
              <div className="flex items-center gap-3 mb-4">
                <Check size={28} className="text-green-500" />
                <h3 className="text-xl font-bold text-gray-900">Patrimoine créé !</h3>
              </div>
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Societe</span>
                  <span className="font-medium">{formData.orgNom}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Entité juridique</span>
                  <span className="font-medium">{formData.ejNom || formData.orgNom}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Sites créés</span>
                  <span className="font-medium">
                    {(result.sites_created || 0) + (result.csv_imported || 0)}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Compteurs ajoutés</span>
                  <span className="font-medium">{result.compteurs_created || 0}</span>
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
                  <p className="text-sm font-medium text-gray-700 mb-2">Sites provisionnés :</p>
                  <div className="space-y-1 max-h-36 overflow-y-auto">
                    {result.sites.map((s) => (
                      <div
                        key={s.id}
                        className="flex items-center justify-between text-sm bg-gray-50 rounded px-3 py-1.5"
                      >
                        <span>{s.nom}</span>
                        <span className="text-xs text-gray-400">
                          {s.type} | {s.obligations} obligation(s)
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <p className="mt-4 text-sm text-gray-500">
                Fermez cette fenêtre pour accéder à votre cockpit personnalisé.
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
            onClick={() => (step > 0 && step < 4 ? setStep(step - 1) : handleClose())}
            className="flex items-center gap-1 text-gray-600 hover:text-gray-800 text-sm"
          >
            <ChevronLeft size={16} />
            {step > 0 && step < 4 ? 'Précédent' : 'Fermer'}
          </button>

          <div className="flex items-center gap-2">
            {(step === 2 || step === 3) && !loading && (
              <button
                onClick={handleSkip}
                className="flex items-center gap-1 px-3 py-2 text-sm text-gray-500 hover:text-gray-700 transition"
              >
                <SkipForward size={14} />
                Je n'ai pas tout
              </button>
            )}

            {step < 4 && (
              <button
                onClick={handleNext}
                disabled={!canProceed() || loading}
                className={`flex items-center gap-1 px-5 py-2 rounded-lg text-sm font-semibold transition ${
                  !canProceed() || loading
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    : step === 3
                      ? 'bg-gradient-to-r from-green-500 to-emerald-600 text-white hover:from-green-600 hover:to-emerald-700'
                      : 'bg-blue-600 text-white hover:bg-blue-700'
                }`}
              >
                {loading ? 'Création en cours...' : step === 3 ? 'Créer mon patrimoine' : 'Suivant'}
                {!loading && <ChevronRight size={16} />}
              </button>
            )}
            {step === 4 && (
              <button
                onClick={handleClose}
                className="flex items-center gap-1 px-5 py-2 rounded-lg text-sm font-semibold bg-blue-600 text-white hover:bg-blue-700 transition"
              >
                Accéder au cockpit
                <ChevronRight size={16} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default UpgradeWizard;
