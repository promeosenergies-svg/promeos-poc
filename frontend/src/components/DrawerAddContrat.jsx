/**
 * PROMEOS — Sprint 2 : Ajout contrat depuis le drawer site
 * Formulaire inline. Rattachement PDL optionnel si des PDL existent.
 */
import { useState, useEffect } from 'react';
import { ArrowLeft, Loader2, CheckCircle2 } from 'lucide-react';
import { patrimoineContractCreate, patrimoineDeliveryPoints } from '../services/api';

const ENERGY_TYPES = [
  { value: 'elec', label: 'Electricite' },
  { value: 'gaz', label: 'Gaz' },
];

const SUPPLIERS = [
  'EDF',
  'Engie',
  'TotalEnergies',
  'Eni',
  'Vattenfall',
  'Alpiq',
  'Ekwateur',
  'Mint Energie',
  'OHM Energie',
];

export default function DrawerAddContrat({ siteId, onBack, onSuccess }) {
  const [form, setForm] = useState({
    energy_type: 'elec',
    supplier_name: '',
    start_date: '',
    end_date: '',
    reference_fournisseur: '',
  });
  const [dps, setDps] = useState([]);
  const [selectedDps, setSelectedDps] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  // Charger les PDL du site
  useEffect(() => {
    patrimoineDeliveryPoints(siteId)
      .then((res) => {
        const points = res.delivery_points || res || [];
        setDps(points);
        // Pre-selectionner tous les PDL du meme type d'energie
        const matching = points.filter((dp) => dp.energy_type === form.energy_type);
        setSelectedDps(new Set(matching.map((dp) => dp.id)));
      })
      .catch(() => setDps([]));
  }, [siteId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setError(null);
    // Mettre a jour la pre-selection PDL quand le type change
    if (field === 'energy_type') {
      const matching = dps.filter((dp) => dp.energy_type === value);
      setSelectedDps(new Set(matching.map((dp) => dp.id)));
    }
  };

  const toggleDp = (dpId) => {
    setSelectedDps((prev) => {
      const next = new Set(prev);
      if (next.has(dpId)) next.delete(dpId);
      else next.add(dpId);
      return next;
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.supplier_name.trim()) {
      setError('Le fournisseur est obligatoire');
      return;
    }
    if (!form.start_date) {
      setError('La date de debut est obligatoire');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const payload = {
        site_id: siteId,
        energy_type: form.energy_type,
        supplier_name: form.supplier_name.trim(),
        start_date: form.start_date,
      };
      if (form.end_date) payload.end_date = form.end_date;
      if (form.reference_fournisseur.trim())
        payload.reference_fournisseur = form.reference_fournisseur.trim();
      if (selectedDps.size > 0) payload.delivery_point_ids = [...selectedDps];

      await patrimoineContractCreate(payload);

      setSuccess(true);
      setTimeout(() => onSuccess?.(), 600);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Erreur lors de la creation du contrat');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-green-600">
        <CheckCircle2 size={40} className="mb-3" />
        <p className="text-sm font-medium">Contrat ajoute</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <button onClick={onBack} className="p-1 rounded hover:bg-gray-100 text-gray-500">
          <ArrowLeft size={16} />
        </button>
        <h3 className="text-sm font-semibold text-gray-900">Ajouter un contrat</h3>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Energie */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Energie <span className="text-red-500">*</span>
          </label>
          <select
            value={form.energy_type}
            onChange={(e) => handleChange('energy_type', e.target.value)}
            className="w-full px-2.5 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            {ENERGY_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>

        {/* Fournisseur */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Fournisseur <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={form.supplier_name}
            onChange={(e) => handleChange('supplier_name', e.target.value)}
            placeholder="Ex : EDF, Engie, TotalEnergies..."
            list="supplier-suggestions"
            className="w-full px-2.5 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <datalist id="supplier-suggestions">
            {SUPPLIERS.map((s) => (
              <option key={s} value={s} />
            ))}
          </datalist>
        </div>

        {/* Dates */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Date de debut <span className="text-red-500">*</span>
            </label>
            <input
              type="date"
              value={form.start_date}
              onChange={(e) => handleChange('start_date', e.target.value)}
              className="w-full px-2.5 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Date de fin <span className="text-gray-400 font-normal">(optionnel)</span>
            </label>
            <input
              type="date"
              value={form.end_date}
              onChange={(e) => handleChange('end_date', e.target.value)}
              className="w-full px-2.5 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>

        {/* Reference */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Reference contrat <span className="text-gray-400 font-normal">(optionnel)</span>
          </label>
          <input
            type="text"
            value={form.reference_fournisseur}
            onChange={(e) => handleChange('reference_fournisseur', e.target.value)}
            placeholder="Ex : CT-2024-001"
            className="w-full px-2.5 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* PDL couverts */}
        {dps.length > 0 && (
          <fieldset className="space-y-2">
            <legend className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
              Points de livraison couverts
            </legend>
            {dps.map((dp) => (
              <label
                key={dp.id}
                className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-gray-50 cursor-pointer text-sm"
              >
                <input
                  type="checkbox"
                  checked={selectedDps.has(dp.id)}
                  onChange={() => toggleDp(dp.id)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-gray-700 font-mono text-xs">{dp.code}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">
                  {dp.energy_type === 'elec'
                    ? 'Electricite'
                    : dp.energy_type === 'gaz'
                      ? 'Gaz'
                      : dp.energy_type}
                </span>
              </label>
            ))}
          </fieldset>
        )}

        {/* Error */}
        {error && (
          <div className="p-2.5 bg-red-50 border border-red-200 rounded-md text-xs text-red-700">
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-2 border-t border-gray-100">
          <button
            type="button"
            onClick={onBack}
            className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800"
          >
            Annuler
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1.5"
          >
            {loading ? (
              <>
                <Loader2 size={13} className="animate-spin" /> Creation...
              </>
            ) : (
              'Ajouter le contrat'
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
