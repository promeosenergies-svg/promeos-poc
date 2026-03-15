/**
 * PROMEOS — Sprint 2 : Ajout compteur depuis le drawer site
 * Formulaire inline. Si PRM/PCE saisi, auto-cree le DeliveryPoint.
 */
import { useState } from 'react';
import { ArrowLeft, Loader2, CheckCircle2 } from 'lucide-react';
import { createCompteur } from '../services/api';

const ENERGY_TYPES = [
  { value: 'electricite', label: 'Electricite' },
  { value: 'gaz', label: 'Gaz' },
  { value: 'eau', label: 'Eau' },
];

export default function DrawerAddCompteur({ siteId, onBack, onSuccess }) {
  const [form, setForm] = useState({
    type: 'electricite',
    meter_id: '',
    puissance_souscrite_kw: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const payload = {
        site_id: siteId,
        type: form.type,
      };
      if (form.meter_id.trim()) {
        payload.meter_id = form.meter_id.replace(/[\s-]/g, '');
      }
      if (form.puissance_souscrite_kw) {
        payload.puissance_souscrite_kw = parseFloat(form.puissance_souscrite_kw);
      }

      await createCompteur(payload);

      setSuccess(true);
      setTimeout(() => {
        onSuccess?.();
      }, 600);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Erreur lors de la creation du compteur');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-green-600">
        <CheckCircle2 size={40} className="mb-3" />
        <p className="text-sm font-medium">Compteur ajoute</p>
        {form.meter_id.trim() && (
          <p className="text-xs text-gray-500 mt-1">Point de livraison cree automatiquement</p>
        )}
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
        <h3 className="text-sm font-semibold text-gray-900">Ajouter un compteur</h3>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Type energie */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Type d'energie <span className="text-red-500">*</span>
          </label>
          <select
            value={form.type}
            onChange={(e) => handleChange('type', e.target.value)}
            className="w-full px-2.5 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            {ENERGY_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>

        {/* PRM / PCE */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            {form.type === 'gaz' ? 'PCE' : 'PRM'}{' '}
            <span className="text-gray-400 font-normal">(optionnel — 14 chiffres)</span>
          </label>
          <input
            type="text"
            value={form.meter_id}
            onChange={(e) => handleChange('meter_id', e.target.value)}
            placeholder={form.type === 'gaz' ? 'Ex : 21234567890123' : 'Ex : 01234567890123'}
            maxLength={14}
            className="w-full px-2.5 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <p className="text-[11px] text-gray-400 mt-1">
            Le point de livraison sera cree automatiquement a partir du{' '}
            {form.type === 'gaz' ? 'PCE' : 'PRM'}.
          </p>
        </div>

        {/* Puissance souscrite */}
        {form.type === 'electricite' && (
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Puissance souscrite (kVA){' '}
              <span className="text-gray-400 font-normal">(optionnel)</span>
            </label>
            <input
              type="number"
              value={form.puissance_souscrite_kw}
              onChange={(e) => handleChange('puissance_souscrite_kw', e.target.value)}
              placeholder="36"
              min="0"
              className="w-full px-2.5 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
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
              'Ajouter le compteur'
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
