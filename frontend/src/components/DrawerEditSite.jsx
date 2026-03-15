/**
 * PROMEOS — Sprint 2 : Mini-formulaire enrichissement site (drawer inline)
 * Remplace le contenu du drawer. Champs : societe/SIRET, surface, adresse/GPS.
 * Appelle PATCH /api/patrimoine/sites/{id} puis geocoding si adresse modifiee.
 */
import { useState } from 'react';
import { ArrowLeft, Loader2, CheckCircle2 } from 'lucide-react';
import { patrimoineSiteUpdate, geocodeOneSite } from '../services/api';

export default function DrawerEditSite({ site, onBack, onSuccess }) {
  const [form, setForm] = useState({
    siret: site.siret || '',
    naf_code: site.naf_code || '',
    surface_m2: site.surface_m2 || '',
    adresse: site.adresse || '',
    code_postal: site.code_postal || '',
    ville: site.ville || '',
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
      // Build payload with only changed fields
      const payload = {};
      if (form.siret !== (site.siret || '')) payload.siret = form.siret || null;
      if (form.naf_code !== (site.naf_code || '')) payload.naf_code = form.naf_code || null;
      if (String(form.surface_m2) !== String(site.surface_m2 || ''))
        payload.surface_m2 = form.surface_m2 ? parseFloat(form.surface_m2) : null;
      if (form.adresse !== (site.adresse || '')) payload.adresse = form.adresse || null;
      if (form.code_postal !== (site.code_postal || ''))
        payload.code_postal = form.code_postal || null;
      if (form.ville !== (site.ville || '')) payload.ville = form.ville || null;

      if (Object.keys(payload).length === 0) {
        onBack();
        return;
      }

      await patrimoineSiteUpdate(site.id, payload);

      // Auto-geocode if address changed
      if (payload.adresse || payload.code_postal || payload.ville) {
        try {
          await geocodeOneSite(site.id, true);
        } catch {
          // Geocoding failure is not blocking
        }
      }

      setSuccess(true);
      setTimeout(() => {
        onSuccess?.();
      }, 600);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Erreur lors de la mise a jour');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-green-600">
        <CheckCircle2 size={40} className="mb-3" />
        <p className="text-sm font-medium">Site mis a jour</p>
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
        <h3 className="text-sm font-semibold text-gray-900">Completer les informations</h3>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Section Etablissement */}
        <fieldset className="space-y-3">
          <legend className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
            Etablissement
          </legend>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">SIRET</label>
              <input
                type="text"
                value={form.siret}
                onChange={(e) => handleChange('siret', e.target.value)}
                placeholder="12345678901234"
                maxLength={14}
                className="w-full px-2.5 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Code NAF</label>
              <input
                type="text"
                value={form.naf_code}
                onChange={(e) => handleChange('naf_code', e.target.value)}
                placeholder="69.20Z"
                maxLength={7}
                className="w-full px-2.5 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
        </fieldset>

        {/* Section Surface */}
        <fieldset className="space-y-3">
          <legend className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
            Surface
          </legend>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Surface totale (m2)
            </label>
            <input
              type="number"
              value={form.surface_m2}
              onChange={(e) => handleChange('surface_m2', e.target.value)}
              placeholder="1000"
              min="0"
              className="w-full px-2.5 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </fieldset>

        {/* Section Localisation */}
        <fieldset className="space-y-3">
          <legend className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
            Localisation
          </legend>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Adresse</label>
            <input
              type="text"
              value={form.adresse}
              onChange={(e) => handleChange('adresse', e.target.value)}
              placeholder="12 rue de la Paix"
              className="w-full px-2.5 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Code postal</label>
              <input
                type="text"
                value={form.code_postal}
                onChange={(e) => handleChange('code_postal', e.target.value)}
                placeholder="75002"
                maxLength={5}
                className="w-full px-2.5 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1">Ville</label>
              <input
                type="text"
                value={form.ville}
                onChange={(e) => handleChange('ville', e.target.value)}
                placeholder="Paris"
                className="w-full px-2.5 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
          <p className="text-[11px] text-gray-400">
            Les coordonnees GPS seront calculees automatiquement a partir de l'adresse.
          </p>
        </fieldset>

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
                <Loader2 size={13} className="animate-spin" /> Enregistrement...
              </>
            ) : (
              'Enregistrer'
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
