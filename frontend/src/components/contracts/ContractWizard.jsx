/**
 * PROMEOS — Contract Wizard (3 modes: Manuel, CSV, PDF)
 * Manuel: 4 etapes (Cadre → Annexes → Tarification → Verification)
 *
 * Selections intelligentes:
 *  - Fournisseurs: Combobox groupé par catégorie, filtré par type d'énergie
 *  - Modèle prix: adapté dynamiquement au type d'énergie (elec ≠ gaz)
 *  - Grille tarification: adaptée à l'option tarifaire choisie
 *  - Durées pré-calculées: boutons 1/2/3/4/5 ans
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import {
  X,
  ChevronRight,
  ChevronLeft,
  Check,
  Upload,
  FileText,
  Zap,
  Flame,
  Leaf,
  AlertCircle,
  Calendar,
  Info as InfoIcon,
} from 'lucide-react';
import { Button, Modal, Combobox } from '../../ui';
import { getSuppliers, createCadre, importCsv } from '../../services/api';
import { useScope } from '../../contexts/ScopeContext';

const STEPS = ['Cadre', 'Annexes', 'Tarification', 'Verification'];
const MODES = [
  { key: 'manual', label: '\u270F\uFE0F Manuel' },
  { key: 'csv', label: '\uD83D\uDCCA CSV' },
  { key: 'pdf', label: '\uD83D\uDCC4 PDF' },
];

/* Labels français pour les codes tarifs */
const PERIOD_LABELS = {
  BASE: 'Base',
  HP: 'Heures Pleines',
  HC: 'Heures Creuses',
  HPH: 'HP Hiver',
  HCH: 'HC Hiver',
  HPB: 'HP Ete',
  HCB: 'HC Ete',
  POINTE: 'Pointe',
};
const SEASON_LABELS = { ANNUEL: 'Annuel', HIVER: 'Hiver', ETE: 'Ete' };

/* Helper: ajouter N mois a une date (clamp fin de mois) */
function addMonths(dateStr, months) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const targetMonth = d.getMonth() + months;
  d.setMonth(targetMonth);
  // Clamp: si le jour a deborde (ex: 31 jan + 1 mois = 3 mars), revenir au dernier jour du mois cible
  if (d.getMonth() !== ((targetMonth % 12) + 12) % 12) {
    d.setDate(0); // dernier jour du mois precedent
  }
  return d.toISOString().slice(0, 10);
}

const INITIAL_FORM = {
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
  green_percentage: null,
  notes: '',
};

export default function ContractWizard({ open, onClose, onCreated }) {
  const { scopedSites } = useScope();
  const [mode, setMode] = useState('manual');
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // Referentiels charges depuis l'API
  const [refs, setRefs] = useState({
    suppliers_by_category: {},
    pricing_models_elec: [],
    pricing_models_gaz: [],
    tariff_options_by_segment: {},
    pricing_grid_by_tariff: {},
    contract_durations: [],
  });

  // Form state
  const [form, setForm] = useState(INITIAL_FORM);
  const [selectedSites, setSelectedSites] = useState([]);
  const [pricing, setPricing] = useState([]);

  // Reset state quand le wizard s'ouvre
  useEffect(() => {
    if (open) {
      setMode('manual');
      setStep(0);
      setError(null);
      setSaving(false);
      setForm(INITIAL_FORM);
      setSelectedSites([]);
      setPricing([]);
    }
  }, [open]);

  // Charger les referentiels
  useEffect(() => {
    getSuppliers()
      .then((d) => setRefs((prev) => ({ ...prev, ...d })))
      .catch(() => {});
  }, []);

  const handleField = useCallback((k, v) => setForm((f) => ({ ...f, [k]: v })), []);
  const toggleSite = (siteId) => {
    setSelectedSites((prev) =>
      prev.includes(siteId) ? prev.filter((id) => id !== siteId) : [...prev, siteId]
    );
  };

  /* ── Fournisseurs filtrés par énergie, groupés ── */
  const supplierOptions = useMemo(() => {
    const cat = refs.suppliers_by_category || {};
    const result = [];
    for (const [group, items] of Object.entries(cat)) {
      for (const s of items) {
        // Filtrer par type d'énergie sélectionné
        if (s.energy && !s.energy.includes(form.energy_type)) continue;
        result.push({
          value: s.name,
          label: s.name,
          group,
          hint: s.hint || '',
        });
      }
    }
    return result;
  }, [refs.suppliers_by_category, form.energy_type]);

  /* ── Modèles prix selon énergie ── */
  const pricingModelOptions = useMemo(() => {
    const models = form.energy_type === 'gaz' ? refs.pricing_models_gaz : refs.pricing_models_elec;
    return (models || []).map((m) => ({
      value: m.value,
      label: m.label,
      hint: m.hint || '',
    }));
  }, [form.energy_type, refs.pricing_models_elec, refs.pricing_models_gaz]);

  /* ── Reset pricing_model si incompatible avec l'énergie ── */
  useEffect(() => {
    if (!form.pricing_model) return;
    const valid = pricingModelOptions.some((o) => o.value === form.pricing_model);
    if (!valid) handleField('pricing_model', '');
  }, [form.energy_type, form.pricing_model, pricingModelOptions, handleField]);

  /* ── Reset supplier si incompatible avec l'énergie ── */
  useEffect(() => {
    if (!form.supplier_name) return;
    const valid = supplierOptions.some((o) => o.value === form.supplier_name);
    if (!valid) handleField('supplier_name', '');
  }, [form.energy_type, form.supplier_name, supplierOptions, handleField]);

  /* ── Durées pré-calculées ── */
  const durations = refs.contract_durations?.length
    ? refs.contract_durations
    : [
        { months: 12, label: '1 an' },
        { months: 24, label: '2 ans' },
        { months: 36, label: '3 ans' },
      ];

  const handleDuration = (months) => {
    if (!form.start_date) return;
    handleField('end_date', addMonths(form.start_date, months));
  };

  /* ── Adaptation grille tarification ── */
  const updatePricingGrid = useCallback(
    (tariffOption) => {
      const grid = refs.pricing_grid_by_tariff?.[tariffOption];
      if (grid) {
        setPricing(
          grid.map((g) => ({
            period_code: g.period_code,
            season: g.season,
            unit_price_eur_kwh: '',
            subscription_eur_month: '',
          }))
        );
      }
    },
    [refs.pricing_grid_by_tariff]
  );

  /* ── Validation step 1 ── */
  const step1Valid = form.supplier_name && form.energy_type && form.start_date && form.end_date;
  const step1Warnings = useMemo(() => {
    const w = [];
    if (form.start_date && form.end_date) {
      const start = new Date(form.start_date);
      const end = new Date(form.end_date);
      const months = (end - start) / (1000 * 60 * 60 * 24 * 30.44);
      if (months > 60) w.push('Duree > 5 ans : verifier la coherence');
      if (months < 6) w.push('Duree < 6 mois : verifier la coherence');
      if (end <= start) w.push('Date fin anterieure a la date debut');
    }
    if (form.pricing_model === 'INDEXE_SPOT')
      w.push("Contrat spot : risque de prix eleve, verifier l'appetence au risque");
    return w;
  }, [form.start_date, form.end_date, form.pricing_model]);

  /* ── Submit ── */
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
      await importCsv(file);
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
      <div className="bg-white rounded-2xl w-[820px] max-w-[96vw] max-h-[93vh] overflow-y-auto shadow-xl">
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

        {/* ════════ Manual mode ════════ */}
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
              {/* ──── Step 1: Cadre ──── */}
              {step === 0 && (
                <div className="space-y-4">
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-2.5 text-xs text-blue-800">
                    <b>Mono-site ?</b> Cadre + annexe fusionnes automatiquement.
                  </div>

                  {/* Énergie (selector prominent) */}
                  <div>
                    <label className="block text-[11px] font-bold text-gray-500 mb-1.5">
                      Type d&apos;energie *
                    </label>
                    <div className="flex gap-2">
                      <EnergyToggle
                        active={form.energy_type === 'elec'}
                        onClick={() => handleField('energy_type', 'elec')}
                        icon={<Zap size={16} />}
                        label="Electricite"
                        color="blue"
                      />
                      <EnergyToggle
                        active={form.energy_type === 'gaz'}
                        onClick={() => handleField('energy_type', 'gaz')}
                        icon={<Flame size={16} />}
                        label="Gaz naturel"
                        color="orange"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    {/* Fournisseur (Combobox groupé + filtré par énergie) */}
                    <Combobox
                      label="Fournisseur"
                      required
                      value={form.supplier_name}
                      onChange={(v) => handleField('supplier_name', v)}
                      options={supplierOptions}
                      grouped
                      allowCustom
                      placeholder="Rechercher un fournisseur..."
                    />

                    {/* Modèle de prix (filtré par énergie) */}
                    <Combobox
                      label="Modele de prix"
                      required
                      value={form.pricing_model}
                      onChange={(v) => handleField('pricing_model', v)}
                      options={pricingModelOptions}
                      placeholder="Selectionner le modele..."
                    />

                    {/* Ref contrat */}
                    <Field label="Ref contrat">
                      <input
                        value={form.contract_ref}
                        onChange={(e) => handleField('contract_ref', e.target.value)}
                        placeholder={`CADRE-${new Date().getFullYear()}-001`}
                        className="w-full p-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                      />
                    </Field>

                    {/* Offre verte */}
                    <Field label="Offre verte">
                      <div className="flex items-center gap-3">
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={form.is_green}
                            onChange={(e) => handleField('is_green', e.target.checked)}
                            className="accent-emerald-600 w-4 h-4"
                          />
                          <Leaf size={14} className="text-emerald-600" />
                          <span className="text-sm">Energie verte</span>
                        </label>
                        {form.is_green && (
                          <input
                            type="number"
                            min={0}
                            max={100}
                            value={form.green_percentage ?? ''}
                            onChange={(e) =>
                              handleField(
                                'green_percentage',
                                e.target.value ? parseInt(e.target.value) : null
                              )
                            }
                            placeholder="100"
                            className="w-16 p-1.5 border rounded text-sm text-center"
                          />
                        )}
                        {form.is_green && <span className="text-xs text-gray-400">%</span>}
                      </div>
                    </Field>
                  </div>

                  {/* Dates + durée rapide */}
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Date debut *">
                      <input
                        type="date"
                        value={form.start_date}
                        onChange={(e) => handleField('start_date', e.target.value)}
                        className="w-full p-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                      />
                    </Field>
                    <div>
                      <Field label="Date fin *">
                        <input
                          type="date"
                          value={form.end_date}
                          onChange={(e) => handleField('end_date', e.target.value)}
                          className="w-full p-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                        />
                      </Field>
                      {form.start_date && (
                        <div className="flex gap-1 mt-1.5">
                          {durations.map((d) => (
                            <button
                              key={d.months}
                              type="button"
                              onClick={() => handleDuration(d.months)}
                              className={`px-2 py-0.5 rounded text-[10px] font-bold border transition ${
                                form.end_date === addMonths(form.start_date, d.months)
                                  ? 'bg-blue-100 border-blue-400 text-blue-700'
                                  : 'bg-gray-50 border-gray-200 text-gray-500 hover:bg-blue-50 hover:border-blue-300'
                              }`}
                            >
                              {d.label}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Préavis + reconduction */}
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="Preavis (mois)">
                      <input
                        type="number"
                        value={form.notice_period_months}
                        onChange={(e) =>
                          handleField('notice_period_months', parseInt(e.target.value) || 3)
                        }
                        min={0}
                        max={60}
                        className="w-full p-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                      />
                    </Field>
                    <Field label="Reconduction tacite">
                      <div className="flex gap-2 mt-0.5">
                        <button
                          type="button"
                          onClick={() => handleField('tacit_renewal', false)}
                          className={`flex-1 py-2 rounded-lg text-sm font-bold border transition ${
                            !form.tacit_renewal
                              ? 'bg-gray-100 border-gray-400 text-gray-800'
                              : 'bg-white border-gray-200 text-gray-400'
                          }`}
                        >
                          Non
                        </button>
                        <button
                          type="button"
                          onClick={() => handleField('tacit_renewal', true)}
                          className={`flex-1 py-2 rounded-lg text-sm font-bold border transition ${
                            form.tacit_renewal
                              ? 'bg-blue-100 border-blue-400 text-blue-800'
                              : 'bg-white border-gray-200 text-gray-400'
                          }`}
                        >
                          Oui
                        </button>
                      </div>
                    </Field>
                  </div>

                  {/* Warnings */}
                  {step1Warnings.length > 0 && (
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-2.5 text-xs text-amber-800 flex items-start gap-2">
                      <AlertCircle size={14} className="flex-shrink-0 mt-0.5" />
                      <div>
                        {step1Warnings.map((w, i) => (
                          <div key={i}>{w}</div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ──── Step 2: Annexes (site selection) ──── */}
              {step === 1 && (
                <div className="space-y-3">
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-2.5 text-xs text-blue-800 flex items-center gap-2">
                    <InfoIcon size={14} />
                    <span>
                      <b>Cochez les sites</b> a rattacher. Chacun deviendra une annexe.
                      {selectedSites.length > 0 && (
                        <span className="ml-2 font-bold">
                          {selectedSites.length} site(s) selectionne(s)
                        </span>
                      )}
                    </span>
                  </div>
                  <div className="space-y-1.5 max-h-[400px] overflow-y-auto">
                    {(scopedSites || []).map((site) => (
                      <label
                        key={site.id}
                        className={`flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition ${
                          selectedSites.includes(site.id)
                            ? 'border-blue-500 bg-blue-50/40'
                            : 'border-gray-200 hover:border-blue-300'
                        }`}
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
                            {site.surface_m2 && `${site.surface_m2} m\u00B2 \u00B7 `}
                            {site.ville || ''}
                          </div>
                        </div>
                        {/* Badge type contrat */}
                        <span className="text-[10px] text-gray-300">
                          {selectedSites.length > 1 ? 'Cadre' : 'Unique'}
                        </span>
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

              {/* ──── Step 3: Tarification ──── */}
              {step === 2 && (
                <div className="space-y-3">
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-2.5 text-xs text-blue-800">
                    <b>Grille tarifaire cadre</b> — heritee par toutes les annexes sauf override.
                  </div>

                  {/* Option tarifaire pour adapter la grille */}
                  {form.energy_type === 'elec' && (
                    <div>
                      <label className="block text-[11px] font-bold text-gray-500 mb-1">
                        Option tarifaire (adapte la grille)
                      </label>
                      <div className="flex flex-wrap gap-1.5">
                        {[
                          { value: 'base', label: 'Base' },
                          { value: 'hp_hc', label: 'HP/HC' },
                          { value: 'cu4', label: 'CU 4 postes' },
                          { value: 'mu4', label: 'MU 4 postes' },
                          { value: 'cu', label: 'CU (C4)' },
                          { value: 'lu', label: 'LU' },
                        ].map((opt) => {
                          const isActive =
                            pricing.length > 0 &&
                            JSON.stringify(pricing.map((p) => p.period_code + p.season)) ===
                              JSON.stringify(
                                (refs.pricing_grid_by_tariff?.[opt.value] || []).map(
                                  (g) => g.period_code + g.season
                                )
                              );
                          return (
                            <button
                              key={opt.value}
                              type="button"
                              onClick={() => updatePricingGrid(opt.value)}
                              className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition ${
                                isActive
                                  ? 'bg-blue-100 border-blue-400 text-blue-700'
                                  : 'bg-white border-gray-200 text-gray-500 hover:bg-blue-50 hover:border-blue-300'
                              }`}
                            >
                              {opt.label}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {pricing.length === 0 ? (
                    <div className="text-center py-8 text-gray-400 text-sm">
                      <Calendar size={32} className="mx-auto mb-2 text-gray-300" />
                      Selectionnez une option tarifaire pour generer la grille
                    </div>
                  ) : (
                    <table className="w-full text-sm border-collapse">
                      <thead>
                        <tr className="bg-gray-50">
                          <th className="p-2.5 text-left text-[10px] font-bold text-gray-400 uppercase border border-gray-100">
                            Periode
                          </th>
                          <th className="p-2.5 text-left text-[10px] font-bold text-gray-400 uppercase border border-gray-100">
                            Saison
                          </th>
                          <th className="p-2.5 text-right text-[10px] font-bold text-gray-400 uppercase border border-gray-100 w-[140px]">
                            Prix unitaire (€/kWh HT)
                          </th>
                          <th className="p-2.5 text-right text-[10px] font-bold text-gray-400 uppercase border border-gray-100 w-[130px]">
                            Abonnement (€/mois)
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {pricing.map((p, i) => (
                          <tr key={i} className="hover:bg-gray-50/50">
                            <td className="p-2.5 border border-gray-100 font-medium">
                              {PERIOD_LABELS[p.period_code] || p.period_code}
                            </td>
                            <td className="p-2.5 border border-gray-100 text-gray-500">
                              {SEASON_LABELS[p.season] || p.season}
                            </td>
                            <td className="p-2.5 border border-gray-100 text-right">
                              <input
                                className="w-[110px] text-right p-1.5 border rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                                value={p.unit_price_eur_kwh}
                                onChange={(e) => {
                                  const next = [...pricing];
                                  next[i] = {
                                    ...next[i],
                                    unit_price_eur_kwh: e.target.value,
                                  };
                                  setPricing(next);
                                }}
                                placeholder="0.0000"
                                step="0.0001"
                              />
                            </td>
                            <td className="p-2.5 border border-gray-100 text-right">
                              <input
                                className="w-[100px] text-right p-1.5 border rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                                value={p.subscription_eur_month}
                                onChange={(e) => {
                                  const next = [...pricing];
                                  next[i] = {
                                    ...next[i],
                                    subscription_eur_month: e.target.value,
                                  };
                                  setPricing(next);
                                }}
                                placeholder="0.00"
                                step="0.01"
                              />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}

                  {/* Aide contextuelle pricing model */}
                  {form.pricing_model && (
                    <div className="bg-gray-50 rounded-lg p-2.5 text-[11px] text-gray-500 flex items-start gap-2">
                      <InfoIcon size={12} className="flex-shrink-0 mt-0.5" />
                      <span>
                        {form.pricing_model === 'FIXE' &&
                          'Prix fixe : le prix unitaire est garanti pour toute la duree du contrat.'}
                        {form.pricing_model === 'FIXE_HORS_ACHEMINEMENT' &&
                          'Fixe hors acheminement : seule la part fourniture est fixe. Les couts TURPE suivent les tarifs reglementes.'}
                        {form.pricing_model === 'INDEXE_TRVE' &&
                          'Indexe TRVE : le prix suit le tarif reglemente de vente (% du TRVE publie par la CRE).'}
                        {form.pricing_model === 'INDEXE_PEG' &&
                          "Indexe PEG : le prix suit les cotations du Point d'Echange de Gaz (marche forward)."}
                        {form.pricing_model === 'INDEXE_SPOT' &&
                          'Indexe spot : prix cale sur le marche spot (EPEX Spot elec ou PEG gaz). Risque de volatilite eleve.'}
                        {form.pricing_model === 'VARIABLE_AUTRE' &&
                          'Variable autre : formule specifique (click, tunnel, collar...). Verifier les conditions particulieres.'}
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* ──── Step 4: Verification ──── */}
              {step === 3 && (
                <div className="space-y-3">
                  <div className="bg-green-50 border border-green-200 rounded-lg p-2.5 text-xs text-green-800">
                    <b>Verification</b> — Resume avant enregistrement
                  </div>
                  {error && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-2.5 text-xs text-red-700">
                      {error}
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-3">
                    <SummaryItem label="Fournisseur" value={form.supplier_name} />
                    <SummaryItem
                      label="Energie"
                      value={form.energy_type === 'elec' ? 'Electricite' : 'Gaz naturel'}
                      icon={
                        form.energy_type === 'elec' ? (
                          <Zap size={12} className="text-blue-500" />
                        ) : (
                          <Flame size={12} className="text-orange-500" />
                        )
                      }
                    />
                    <SummaryItem
                      label="Modele prix"
                      value={
                        pricingModelOptions.find((o) => o.value === form.pricing_model)?.label ||
                        form.pricing_model
                      }
                    />
                    <SummaryItem label="Ref" value={form.contract_ref} />
                    <SummaryItem
                      label="Periode"
                      value={
                        form.start_date && form.end_date
                          ? `${form.start_date} \u2192 ${form.end_date}`
                          : ''
                      }
                    />
                    <SummaryItem
                      label="Sites rattaches"
                      value={`${selectedSites.length} site(s) \u2192 ${selectedSites.length > 1 ? 'Cadre' : 'Unique'}`}
                    />
                    <SummaryItem label="Preavis" value={`${form.notice_period_months} mois`} />
                    <SummaryItem label="Reconduction" value={form.tacit_renewal ? 'Oui' : 'Non'} />
                    {form.is_green && (
                      <SummaryItem
                        label="Offre verte"
                        value={`${form.green_percentage || 100}%`}
                        icon={<Leaf size={12} className="text-emerald-500" />}
                      />
                    )}
                    <SummaryItem
                      label="Lignes tarif"
                      value={`${pricing.filter((p) => p.unit_price_eur_kwh).length} ligne(s)`}
                    />
                  </div>
                </div>
              )}
            </div>
          </>
        )}

        {/* ════════ CSV mode ════════ */}
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
              <b>Auto-groupement :</b> meme fournisseur+ref = 1 cadre + N annexes
            </div>
            {error && (
              <div className="mt-2 bg-red-50 border border-red-200 rounded-lg p-2.5 text-xs text-red-700">
                {error}
              </div>
            )}
          </div>
        )}

        {/* ════════ PDF mode ════════ */}
        {mode === 'pdf' && (
          <div className="px-6 py-4">
            <div className="border-2 border-dashed border-gray-300 rounded-xl p-9 text-center">
              <FileText size={36} className="mx-auto text-gray-300 mb-2" />
              <div className="text-sm font-bold">Deposer le contrat PDF</div>
              <div className="text-xs text-gray-400">Extraction IA assistee</div>
            </div>
            <div className="mt-3 bg-amber-50 border border-amber-200 rounded-lg p-2.5 text-xs text-amber-800">
              <b>Revue manuelle obligatoire</b> — Fonctionnalite en cours de developpement
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
                  disabled={
                    (step === 0 && !step1Valid) || (step === 1 && selectedSites.length === 0)
                  }
                >
                  Suivant <ChevronRight size={12} />
                </Button>
              ) : (
                <Button size="sm" variant="primary" onClick={handleSubmit} disabled={saving}>
                  {saving ? '...' : 'Enregistrer'}
                </Button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Sub-components ── */

function Field({ label, children }) {
  return (
    <div>
      <label className="block text-[11px] font-bold text-gray-500 mb-1">{label}</label>
      {children}
    </div>
  );
}

function SummaryItem({ label, value, icon }) {
  return (
    <div className="bg-gray-50 rounded-lg p-2.5">
      <div className="text-[10px] text-gray-400 mb-0.5">{label}</div>
      <div className="text-sm font-semibold flex items-center gap-1.5">
        {icon}
        {value || '\u2014'}
      </div>
    </div>
  );
}

function EnergyToggle({ active, onClick, icon, label, color }) {
  const colors = {
    blue: active
      ? 'bg-blue-50 border-blue-400 text-blue-700'
      : 'bg-white border-gray-200 text-gray-400',
    orange: active
      ? 'bg-orange-50 border-orange-400 text-orange-700'
      : 'bg-white border-gray-200 text-gray-400',
  };
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg border-2 font-bold text-sm transition ${colors[color]}`}
    >
      {icon}
      {label}
    </button>
  );
}
