/**
 * PROMEOS — Contract Wizard (3 modes: Manuel, CSV, PDF)
 * Manuel: 4 etapes (Cadre → Annexes → Tarification → Verification)
 */
import { useState, useEffect } from 'react';
import { X, ChevronRight, ChevronLeft, Check, Upload, FileText } from 'lucide-react';
import { Button, Modal } from '../../ui';
import { getSuppliers, createCadre, importCsv } from '../../services/api';
import { useScope } from '../../contexts/ScopeContext';

const STEPS = ['Cadre', 'Annexes', 'Tarification', 'Verification'];
const MODES = [
  { key: 'manual', label: '✏️ Manuel' },
  { key: 'csv', label: '📊 CSV' },
  { key: 'pdf', label: '📄 PDF' },
];

export default function ContractWizard({ open, onClose, onCreated }) {
  const { scopedSites } = useScope();
  const [mode, setMode] = useState('manual');
  const [step, setStep] = useState(0);
  const [suppliers, setSuppliers] = useState([]);
  const [pricingModels, setPricingModels] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // Form state
  const [form, setForm] = useState({
    supplier_name: '',
    energy_type: 'elec',
    contract_ref: '',
    contract_type: 'UNIQUE',
    pricing_model: '',
    start_date: '',
    end_date: '',
    tacit_renewal: false,
    notice_period_months: 3,
    is_green: false,
    notes: '',
  });
  const [selectedSites, setSelectedSites] = useState([]);
  const [pricing, setPricing] = useState([
    { period_code: 'HP', season: 'HIVER', unit_price_eur_kwh: '', subscription_eur_month: '' },
    { period_code: 'HC', season: 'HIVER', unit_price_eur_kwh: '', subscription_eur_month: '' },
    { period_code: 'HP', season: 'ETE', unit_price_eur_kwh: '', subscription_eur_month: '' },
    { period_code: 'HC', season: 'ETE', unit_price_eur_kwh: '', subscription_eur_month: '' },
  ]);

  useEffect(() => {
    getSuppliers()
      .then((d) => {
        setSuppliers(d.suppliers || []);
        setPricingModels(d.pricing_models || []);
      })
      .catch(() => {});
  }, []);

  const handleField = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const toggleSite = (siteId) => {
    setSelectedSites((prev) =>
      prev.includes(siteId) ? prev.filter((id) => id !== siteId) : [...prev, siteId]
    );
  };

  const handleSubmit = async () => {
    setSaving(true);
    setError(null);
    try {
      const annexes = selectedSites.map((sid) => ({
        site_id: sid,
        annexe_ref: `ANX-${sid}`,
      }));
      const pricingData = pricing
        .filter((p) => p.unit_price_eur_kwh)
        .map((p) => ({
          ...p,
          unit_price_eur_kwh: parseFloat(p.unit_price_eur_kwh),
          subscription_eur_month: p.subscription_eur_month
            ? parseFloat(p.subscription_eur_month)
            : null,
        }));

      await createCadre({
        ...form,
        contract_type: selectedSites.length > 1 ? 'CADRE' : 'UNIQUE',
        pricing: pricingData,
        annexes,
      });
      onCreated?.();
      onClose();
    } catch (e) {
      setError(e.response?.data?.detail || 'Erreur creation');
    } finally {
      setSaving(false);
    }
  };

  const handleCsvImport = async (file) => {
    setSaving(true);
    setError(null);
    try {
      const result = await importCsv(file);
      onCreated?.();
      onClose();
    } catch (e) {
      setError(e.response?.data?.detail || 'Erreur import CSV');
    } finally {
      setSaving(false);
    }
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center bg-black/40 backdrop-blur-[2px]"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-white rounded-2xl w-[780px] max-w-[96vw] max-h-[93vh] overflow-y-auto shadow-xl">
        {/* Header */}
        <div className="px-6 py-4 border-b flex justify-between items-center">
          <h2 className="text-lg font-extrabold">Nouveau contrat</h2>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded border flex items-center justify-center text-gray-400 hover:text-gray-700"
          >
            <X size={14} />
          </button>
        </div>

        {/* Mode tabs */}
        <div className="flex gap-0.5 bg-gray-50 rounded-lg p-1 w-fit mx-6 mt-3.5">
          {MODES.map((m) => (
            <button
              key={m.key}
              onClick={() => setMode(m.key)}
              className={`px-4 py-1.5 rounded-md text-xs font-bold transition ${mode === m.key ? 'bg-white shadow-sm text-gray-900' : 'text-gray-400'}`}
            >
              {m.label}
            </button>
          ))}
        </div>

        {/* Manual mode */}
        {mode === 'manual' && (
          <>
            {/* Step indicator */}
            <div className="flex px-6 mt-3.5 mb-1.5">
              {STEPS.map((s, i) => (
                <div
                  key={s}
                  className={`flex-1 flex items-center gap-1.5 text-[11px] font-bold ${i === step ? 'text-blue-600' : i < step ? 'text-emerald-600' : 'text-gray-300'}`}
                >
                  <span
                    className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] border-2 ${i === step ? 'border-blue-500 bg-blue-50 text-blue-600' : i < step ? 'border-emerald-500 bg-emerald-50 text-emerald-600' : 'border-gray-200 bg-white'}`}
                  >
                    {i < step ? <Check size={10} /> : i + 1}
                  </span>
                  <span>{s}</span>
                  {i < STEPS.length - 1 && (
                    <div
                      className={`flex-1 h-0.5 mx-1 ${i < step ? 'bg-emerald-400' : 'bg-gray-200'}`}
                    />
                  )}
                </div>
              ))}
            </div>

            <div className="px-6 pb-5">
              {/* Step 1: Cadre */}
              {step === 0 && (
                <div className="space-y-3">
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-2.5 text-xs text-blue-800">
                    <b>💡 Mono-site ?</b> Cadre + annexe fusionnes automatiquement.
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Fournisseur *">
                      <select
                        value={form.supplier_name}
                        onChange={(e) => handleField('supplier_name', e.target.value)}
                        className="w-full p-2 border rounded-md text-xs"
                      >
                        <option value="">Selectionner...</option>
                        {suppliers.map((s) => (
                          <option key={s} value={s}>
                            {s}
                          </option>
                        ))}
                      </select>
                    </Field>
                    <Field label="Energie *">
                      <select
                        value={form.energy_type}
                        onChange={(e) => handleField('energy_type', e.target.value)}
                        className="w-full p-2 border rounded-md text-xs"
                      >
                        <option value="elec">Electricite</option>
                        <option value="gaz">Gaz naturel</option>
                      </select>
                    </Field>
                    <Field label="Ref contrat">
                      <input
                        value={form.contract_ref}
                        onChange={(e) => handleField('contract_ref', e.target.value)}
                        placeholder="CADRE-2026-001"
                        className="w-full p-2 border rounded-md text-xs"
                      />
                    </Field>
                    <Field label="Modele prix">
                      <select
                        value={form.pricing_model}
                        onChange={(e) => handleField('pricing_model', e.target.value)}
                        className="w-full p-2 border rounded-md text-xs"
                      >
                        <option value="">Selectionner...</option>
                        {pricingModels.map((m) => (
                          <option key={m} value={m}>
                            {m.replace(/_/g, ' ')}
                          </option>
                        ))}
                      </select>
                    </Field>
                    <Field label="Debut *">
                      <input
                        type="date"
                        value={form.start_date}
                        onChange={(e) => handleField('start_date', e.target.value)}
                        className="w-full p-2 border rounded-md text-xs"
                      />
                    </Field>
                    <Field label="Fin *">
                      <input
                        type="date"
                        value={form.end_date}
                        onChange={(e) => handleField('end_date', e.target.value)}
                        className="w-full p-2 border rounded-md text-xs"
                      />
                    </Field>
                    <Field label="Preavis (mois)">
                      <input
                        type="number"
                        value={form.notice_period_months}
                        onChange={(e) =>
                          handleField('notice_period_months', parseInt(e.target.value) || 3)
                        }
                        className="w-full p-2 border rounded-md text-xs"
                      />
                    </Field>
                    <Field label="Reconduction">
                      <select
                        value={form.tacit_renewal ? 'oui' : 'non'}
                        onChange={(e) => handleField('tacit_renewal', e.target.value === 'oui')}
                        className="w-full p-2 border rounded-md text-xs"
                      >
                        <option value="non">Non</option>
                        <option value="oui">Oui</option>
                      </select>
                    </Field>
                  </div>
                </div>
              )}

              {/* Step 2: Annexes (site selection) */}
              {step === 1 && (
                <div className="space-y-3">
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-2.5 text-xs text-blue-800">
                    <b>Cochez les sites</b> a rattacher. Chacun deviendra une annexe.
                  </div>
                  <div className="space-y-1.5 max-h-[400px] overflow-y-auto">
                    {(scopedSites || []).map((site) => (
                      <label
                        key={site.id}
                        className={`flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition ${selectedSites.includes(site.id) ? 'border-blue-500 bg-blue-50/40' : 'border-gray-200 hover:border-blue-300'}`}
                      >
                        <input
                          type="checkbox"
                          checked={selectedSites.includes(site.id)}
                          onChange={() => toggleSite(site.id)}
                          className="accent-blue-600 w-4 h-4"
                        />
                        <div className="flex-1">
                          <div className="font-bold text-sm">{site.nom}</div>
                          <div className="text-[11px] text-gray-400">
                            {site.surface_m2 && `${site.surface_m2} m² · `}
                            {site.ville || ''}
                          </div>
                        </div>
                      </label>
                    ))}
                    {(!scopedSites || scopedSites.length === 0) && (
                      <div className="text-center text-gray-400 text-sm py-6">
                        Aucun site disponible
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Step 3: Tarification */}
              {step === 2 && (
                <div className="space-y-3">
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-2.5 text-xs text-blue-800">
                    <b>Grille cadre</b> — herite par toutes annexes sauf override.
                  </div>
                  <table className="w-full text-xs border-collapse">
                    <thead>
                      <tr className="bg-gray-50">
                        <th className="p-2 text-left text-[9px] font-bold text-gray-400 uppercase border border-gray-100">
                          Periode
                        </th>
                        <th className="p-2 text-left text-[9px] font-bold text-gray-400 uppercase border border-gray-100">
                          Saison
                        </th>
                        <th className="p-2 text-right text-[9px] font-bold text-gray-400 uppercase border border-gray-100 w-[120px]">
                          €/kWh HT
                        </th>
                        <th className="p-2 text-right text-[9px] font-bold text-gray-400 uppercase border border-gray-100 w-[120px]">
                          Abo €/mois
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {pricing.map((p, i) => (
                        <tr key={i}>
                          <td className="p-2 border border-gray-100">{p.period_code}</td>
                          <td className="p-2 border border-gray-100">{p.season}</td>
                          <td className="p-2 border border-gray-100 text-right">
                            <input
                              className="w-[90px] text-right p-1 border rounded text-xs"
                              value={p.unit_price_eur_kwh}
                              onChange={(e) => {
                                const next = [...pricing];
                                next[i] = { ...next[i], unit_price_eur_kwh: e.target.value };
                                setPricing(next);
                              }}
                              placeholder="0.0000"
                            />
                          </td>
                          <td className="p-2 border border-gray-100 text-right">
                            <input
                              className="w-[90px] text-right p-1 border rounded text-xs"
                              value={p.subscription_eur_month}
                              onChange={(e) => {
                                const next = [...pricing];
                                next[i] = { ...next[i], subscription_eur_month: e.target.value };
                                setPricing(next);
                              }}
                              placeholder="0.00"
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Step 4: Verification */}
              {step === 3 && (
                <div className="space-y-3">
                  <div className="bg-green-50 border border-green-200 rounded-lg p-2.5 text-xs text-green-800">
                    <b>✓ Verification</b> — Resume avant enregistrement
                  </div>
                  {error && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-2.5 text-xs text-red-700">
                      {error}
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-2">
                    <Info label="Fournisseur" value={form.supplier_name} />
                    <Info label="Modele" value={form.pricing_model} />
                    <Info label="Periode" value={`${form.start_date} → ${form.end_date}`} />
                    <Info label="Annexes" value={`${selectedSites.length} site(s)`} />
                    <Info
                      label="Energie"
                      value={form.energy_type === 'elec' ? 'Electricite' : 'Gaz'}
                    />
                    <Info label="Preavis" value={`${form.notice_period_months} mois`} />
                  </div>
                </div>
              )}
            </div>
          </>
        )}

        {/* CSV mode */}
        {mode === 'csv' && (
          <div className="px-6 py-4">
            <div
              className="border-2 border-dashed border-gray-300 rounded-xl p-9 text-center hover:border-blue-500 hover:bg-blue-50/20 transition cursor-pointer"
              onClick={() => document.getElementById('csv-input')?.click()}
            >
              <Upload size={36} className="mx-auto text-gray-300 mb-2" />
              <div className="text-sm font-bold">Glisser ou cliquer</div>
              <div className="text-xs text-gray-400">.csv .xlsx .xls — max 500 lignes</div>
              <input
                id="csv-input"
                type="file"
                accept=".csv,.xlsx,.xls"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && handleCsvImport(e.target.files[0])}
              />
            </div>
            <div className="mt-3 bg-green-50 border border-green-200 rounded-lg p-2.5 text-xs text-green-800">
              <b>📋 Auto-groupement :</b> meme fournisseur+ref → 1 cadre + N annexes
            </div>
            {error && (
              <div className="mt-2 bg-red-50 border border-red-200 rounded-lg p-2.5 text-xs text-red-700">
                {error}
              </div>
            )}
          </div>
        )}

        {/* PDF mode */}
        {mode === 'pdf' && (
          <div className="px-6 py-4">
            <div className="border-2 border-dashed border-gray-300 rounded-xl p-9 text-center">
              <FileText size={36} className="mx-auto text-gray-300 mb-2" />
              <div className="text-sm font-bold">Deposer le contrat PDF</div>
              <div className="text-xs text-gray-400">Extraction IA assistee</div>
            </div>
            <div className="mt-3 bg-amber-50 border border-amber-200 rounded-lg p-2.5 text-xs text-amber-800">
              <b>⚠️ Revue manuelle obligatoire</b> — Fonctionnalite en cours de developpement
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="px-6 py-3.5 border-t flex justify-between">
          <Button size="sm" onClick={onClose}>
            Annuler
          </Button>
          {mode === 'manual' && (
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={() => setStep((s) => Math.max(0, s - 1))}
                disabled={step === 0}
              >
                <ChevronLeft size={12} /> Precedent
              </Button>
              {step < 3 ? (
                <Button
                  size="sm"
                  variant="primary"
                  onClick={() => setStep((s) => s + 1)}
                  disabled={step === 1 && selectedSites.length === 0}
                >
                  Suivant <ChevronRight size={12} />
                </Button>
              ) : (
                <Button size="sm" variant="primary" onClick={handleSubmit} disabled={saving}>
                  {saving ? '...' : '✓ Enregistrer'}
                </Button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div>
      <label className="block text-[11px] font-bold text-gray-500 mb-1">{label}</label>
      {children}
    </div>
  );
}

function Info({ label, value }) {
  return (
    <div>
      <div className="text-[10px] text-gray-400">{label}</div>
      <div className="text-sm font-semibold">{value || '—'}</div>
    </div>
  );
}
