/**
 * PROMEOS — Sprint 1 Patrimoine : Creation rapide de site
 * 1 formulaire, 1 ecran, 5 champs visibles + section optionnelle.
 * Remplace le wizard 7-etapes comme CTA principal.
 */
import { useState } from 'react';
import {
  X,
  MapPin,
  Loader2,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  ExternalLink,
} from 'lucide-react';
import { quickCreateSite } from '../services/api';

const USAGE_OPTIONS = [
  { value: 'bureau', label: 'Bureau' },
  { value: 'commerce', label: 'Commerce' },
  { value: 'entrepot', label: 'Entrepot' },
  { value: 'usine', label: 'Usine' },
  { value: 'hotel', label: 'Hotel' },
  { value: 'sante', label: 'Sante' },
  { value: 'enseignement', label: 'Enseignement' },
  { value: 'copropriete', label: 'Copropriete' },
  { value: 'collectivite', label: 'Collectivite' },
  { value: 'logement_social', label: 'Logement social' },
  { value: 'magasin', label: 'Magasin' },
];

export default function QuickCreateSite({ onClose, onSuccess }) {
  const [form, setForm] = useState({
    nom: '',
    usage: 'bureau',
    adresse: '',
    code_postal: '',
    ville: '',
    surface_m2: '',
    siret: '',
    naf_code: '',
  });
  const [showMore, setShowMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [duplicate, setDuplicate] = useState(null);

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    if (field === 'nom' || field === 'code_postal') setDuplicate(null);
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.nom.trim()) {
      setError('Le nom du site est obligatoire');
      return;
    }

    setLoading(true);
    setError(null);
    setDuplicate(null);

    try {
      const payload = {
        nom: form.nom.trim(),
        usage: form.usage || undefined,
        adresse: form.adresse || undefined,
        code_postal: form.code_postal || undefined,
        ville: form.ville || undefined,
        surface_m2: form.surface_m2 ? parseFloat(form.surface_m2) : undefined,
        siret: form.siret || undefined,
        naf_code: form.naf_code || undefined,
      };

      const result = await quickCreateSite(payload);

      if (result.status === 'duplicate_detected') {
        setDuplicate(result);
        setLoading(false);
        return;
      }

      onSuccess?.(result);
      onClose();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Erreur lors de la creation');
    } finally {
      setLoading(false);
    }
  };

  const forceCreate = async () => {
    // Retry without code_postal to bypass duplicate check
    setDuplicate(null);
    const payload = {
      nom: form.nom.trim(),
      usage: form.usage || undefined,
      adresse: form.adresse || undefined,
      ville: form.ville || undefined,
      surface_m2: form.surface_m2 ? parseFloat(form.surface_m2) : undefined,
      siret: form.siret || undefined,
      naf_code: form.naf_code || undefined,
    };
    setLoading(true);
    try {
      const result = await quickCreateSite(payload);
      onSuccess?.(result);
      onClose();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Erreur lors de la creation');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div className="flex items-center gap-2">
            <MapPin size={20} className="text-blue-600" />
            <h2 className="text-lg font-semibold text-gray-900">Nouveau site</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md hover:bg-gray-100 text-gray-400 hover:text-gray-600"
          >
            <X size={18} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          {/* Nom */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nom du site <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={form.nom}
              onChange={(e) => handleChange('nom', e.target.value)}
              placeholder="Ex : Siege social Paris"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              autoFocus
            />
          </div>

          {/* Usage */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Usage</label>
            <select
              value={form.usage}
              onChange={(e) => handleChange('usage', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {USAGE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Adresse row */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Adresse</label>
            <input
              type="text"
              value={form.adresse}
              onChange={(e) => handleChange('adresse', e.target.value)}
              placeholder="12 rue de la Paix"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* CP + Ville */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Code postal</label>
              <input
                type="text"
                value={form.code_postal}
                onChange={(e) => handleChange('code_postal', e.target.value)}
                placeholder="75002"
                maxLength={5}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Ville</label>
              <input
                type="text"
                value={form.ville}
                onChange={(e) => handleChange('ville', e.target.value)}
                placeholder="Paris"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          {/* Plus de details (collapsible) */}
          <button
            type="button"
            onClick={() => setShowMore(!showMore)}
            className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
          >
            {showMore ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            {showMore ? 'Moins de details' : 'Plus de details'}
          </button>

          {showMore && (
            <div className="space-y-3 pt-1 border-t border-gray-100">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Surface (m2)
                  </label>
                  <input
                    type="number"
                    value={form.surface_m2}
                    onChange={(e) => handleChange('surface_m2', e.target.value)}
                    placeholder="1000"
                    min="0"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">SIRET</label>
                  <input
                    type="text"
                    value={form.siret}
                    onChange={(e) => handleChange('siret', e.target.value)}
                    placeholder="12345678901234"
                    maxLength={14}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Code NAF</label>
                <input
                  type="text"
                  value={form.naf_code}
                  onChange={(e) => handleChange('naf_code', e.target.value)}
                  placeholder="69.20Z"
                  maxLength={7}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
          )}

          {/* Duplicate warning */}
          {duplicate && (
            <div className="flex items-start gap-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <AlertTriangle size={18} className="text-amber-600 mt-0.5 shrink-0" />
              <div className="text-sm">
                <p className="font-medium text-amber-800">{duplicate.message}</p>
                <div className="mt-2 flex gap-2">
                  <button
                    type="button"
                    onClick={forceCreate}
                    className="px-3 py-1 text-xs font-medium bg-amber-100 text-amber-800 rounded hover:bg-amber-200"
                  >
                    Creer quand meme
                  </button>
                  <a
                    href={`/sites/${duplicate.existing_site?.id}`}
                    className="inline-flex items-center gap-1 px-3 py-1 text-xs font-medium text-blue-700 bg-blue-50 rounded hover:bg-blue-100"
                  >
                    Voir le site existant <ExternalLink size={12} />
                  </a>
                </div>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between pt-3 border-t border-gray-100">
            <p className="text-xs text-gray-400">Batiment et obligations auto-generes</p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
              >
                Annuler
              </button>
              <button
                type="submit"
                disabled={loading || !form.nom.trim()}
                className="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 size={14} className="animate-spin" /> Creation...
                  </>
                ) : (
                  'Creer le site'
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
