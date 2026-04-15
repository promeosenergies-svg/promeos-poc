/**
 * PROMEOS — Step 32 : Wizard creation site guide
 * 7 etapes : Organisation → Entite → Portefeuille → Site → Batiments → Compteurs → Recap
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  X,
  ChevronRight,
  ChevronLeft,
  Check,
  Building2,
  FileText,
  Folder,
  MapPin,
  Home,
  Gauge,
  Plus,
  Trash2,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import {
  crudListOrganisations,
  crudCreateOrganisation,
  crudListEntites,
  crudCreateEntite,
  crudListPortefeuilles,
  crudCreatePortefeuille,
  crudCreateSite,
  crudCreateBatiment,
  createMeter,
} from '../services/api';

// ── Constants ──────────────────────────────────────────────────────────────

const STEPS = [
  { id: 'org', label: 'Societe', icon: Building2 },
  { id: 'entite', label: 'Entité juridique', icon: FileText },
  { id: 'portefeuille', label: 'Portefeuille', icon: Folder },
  { id: 'site', label: 'Site', icon: MapPin },
  { id: 'batiments', label: 'Bâtiments', icon: Home, optional: true },
  { id: 'compteurs', label: 'Compteurs', icon: Gauge, optional: true },
  { id: 'recap', label: 'Confirmation', icon: Check },
];

const SITE_TYPES = [
  { value: 'bureau', label: 'Bureau' },
  { value: 'entrepot', label: 'Entrepôt' },
  { value: 'magasin', label: 'Magasin' },
  { value: 'usine', label: 'Usine' },
  { value: 'commerce', label: 'Commerce' },
  { value: 'copropriete', label: 'Copropriété' },
  { value: 'logement_social', label: 'Logement social' },
  { value: 'collectivite', label: 'Collectivité' },
  { value: 'hotel', label: 'Hôtel' },
  { value: 'sante', label: 'Santé' },
  { value: 'enseignement', label: 'Enseignement' },
];

const ENERGY_TYPES = [
  { value: 'electricity', label: 'Électricité' },
  { value: 'gas', label: 'Gaz' },
];

function validateSiren(v) {
  if (!v) return true; // optional
  const clean = v.replace(/[\s-]/g, '');
  return /^\d{9}$/.test(clean);
}

function validatePrm(v) {
  if (!v) return false;
  const clean = v.replace(/[\s-]/g, '');
  return /^\d{14}$/.test(clean);
}

// ── Sub-components for each step ───────────────────────────────────────────

function StepOrganisation({ data, setData, orgs, loading }) {
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [newSiren, setNewSiren] = useState('');
  const navigate = useNavigate();

  if (loading) return <p className="text-sm text-gray-500">Chargement des organisations...</p>;

  return (
    <div className="space-y-4">
      {/* Shortcut Sirene : auto-complete patrimoine entier depuis un SIREN */}
      <div className="flex items-center gap-3 p-3 bg-indigo-50 border border-indigo-200 rounded-lg">
        <div className="text-xl">⚡</div>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-indigo-900">Plus rapide : créer depuis un SIREN</p>
          <p className="text-[11px] text-indigo-600">
            Auto-complète organisation + entité + sites depuis la base Sirene officielle.
          </p>
        </div>
        <button
          type="button"
          onClick={() => navigate('/onboarding/sirene')}
          className="px-3 py-1.5 bg-indigo-600 text-white text-xs font-medium rounded hover:bg-indigo-700 whitespace-nowrap"
        >
          Ouvrir →
        </button>
      </div>

      <label className="block text-sm font-medium text-gray-700">Societe</label>
      {!creating ? (
        <>
          <select
            className="w-full border rounded-lg px-3 py-2 text-sm"
            value={data.org?.id || ''}
            onChange={(e) => {
              const org = orgs.find((o) => o.id === Number(e.target.value));
              setData((d) => ({ ...d, org: org || null, entite: null, portefeuille: null }));
            }}
          >
            <option value="">-- Sélectionnez --</option>
            {orgs.map((o) => (
              <option key={o.id} value={o.id}>
                {o.nom} {o.siren ? `(${o.siren})` : ''}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => setCreating(true)}
            className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
          >
            <Plus size={14} /> Creer une nouvelle societe
          </button>
        </>
      ) : (
        <div className="space-y-3 bg-blue-50 rounded-lg p-4">
          <input
            className="w-full border rounded-lg px-3 py-2 text-sm"
            placeholder="Nom de l'organisation *"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
          />
          <input
            className="w-full border rounded-lg px-3 py-2 text-sm"
            placeholder="SIREN (9 chiffres, optionnel)"
            value={newSiren}
            onChange={(e) => setNewSiren(e.target.value)}
          />
          {newSiren && !validateSiren(newSiren) && (
            <p className="text-xs text-red-500">SIREN invalide (9 chiffres attendus)</p>
          )}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => {
                if (!newName.trim()) return;
                setData((d) => ({
                  ...d,
                  org: { id: null, nom: newName.trim(), siren: newSiren || null, _new: true },
                  entite: null,
                  portefeuille: null,
                }));
                setCreating(false);
              }}
              disabled={!newName.trim() || (newSiren && !validateSiren(newSiren))}
              className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              Valider
            </button>
            <button
              type="button"
              onClick={() => setCreating(false)}
              className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800"
            >
              Annuler
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function StepEntite({ data, setData, entites, loading }) {
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ nom: '', siren: '', siret: '', naf_code: '' });

  if (loading) return <p className="text-sm text-gray-500">Chargement des entites...</p>;

  return (
    <div className="space-y-4">
      <label className="block text-sm font-medium text-gray-700">
        Entité juridique (societe: {data.org?.nom})
      </label>
      {!creating ? (
        <>
          <select
            className="w-full border rounded-lg px-3 py-2 text-sm"
            value={data.entite?.id || ''}
            onChange={(e) => {
              const ent = entites.find((x) => x.id === Number(e.target.value));
              setData((d) => ({ ...d, entite: ent || null, portefeuille: null }));
            }}
          >
            <option value="">-- Sélectionnez --</option>
            {entites.map((e) => (
              <option key={e.id} value={e.id}>
                {e.nom} ({e.siren})
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => setCreating(true)}
            className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
          >
            <Plus size={14} /> Créer une nouvelle entité
          </button>
        </>
      ) : (
        <div className="space-y-3 bg-blue-50 rounded-lg p-4">
          <input
            className="w-full border rounded-lg px-3 py-2 text-sm"
            placeholder="Nom *"
            value={form.nom}
            onChange={(e) => setForm((f) => ({ ...f, nom: e.target.value }))}
          />
          <input
            className="w-full border rounded-lg px-3 py-2 text-sm"
            placeholder="SIREN (9 chiffres) *"
            value={form.siren}
            onChange={(e) => setForm((f) => ({ ...f, siren: e.target.value }))}
          />
          {form.siren && !validateSiren(form.siren) && (
            <p className="text-xs text-red-500">SIREN invalide (9 chiffres attendus)</p>
          )}
          <input
            className="w-full border rounded-lg px-3 py-2 text-sm"
            placeholder="SIRET (14 chiffres, optionnel)"
            value={form.siret}
            onChange={(e) => setForm((f) => ({ ...f, siret: e.target.value }))}
            onBlur={async (e) => {
              const val = e.target.value.replace(/\s/g, '');
              if (val.length !== 14) return;
              try {
                const { lookupSiret } = await import('../services/api');
                const res = await lookupSiret(val);
                if (res?.found) {
                  setForm((f) => ({
                    ...f,
                    siren: res.siren || f.siren,
                    naf_code: res.naf_code || f.naf_code,
                    nom: f.nom || res.nom || '',
                    _sirene: res,
                  }));
                }
              } catch {
                /* API down — non bloquant */
              }
            }}
          />
          {form._sirene && (
            <div className="text-xs text-green-600 bg-green-50 rounded-lg px-3 py-2">
              ✓ SIRENE : {form._sirene.nom} · NAF {form._sirene.naf_code} ({form._sirene.naf_label})
              {form._sirene.archetype && (
                <span className="ml-1 font-semibold">· {form._sirene.archetype}</span>
              )}
            </div>
          )}
          <input
            className="w-full border rounded-lg px-3 py-2 text-sm"
            placeholder="Code NAF (optionnel)"
            value={form.naf_code}
            onChange={(e) => setForm((f) => ({ ...f, naf_code: e.target.value }))}
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => {
                if (!form.nom.trim() || !validateSiren(form.siren)) return;
                setData((d) => ({
                  ...d,
                  entite: { id: null, ...form, _new: true },
                  portefeuille: null,
                }));
                setCreating(false);
              }}
              disabled={!form.nom.trim() || !form.siren || !validateSiren(form.siren)}
              className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              Valider
            </button>
            <button
              type="button"
              onClick={() => setCreating(false)}
              className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800"
            >
              Annuler
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function StepPortefeuille({ data, setData, portefeuilles, loading }) {
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ nom: '', description: '' });

  if (loading) return <p className="text-sm text-gray-500">Chargement des portefeuilles...</p>;

  return (
    <div className="space-y-4">
      <label className="block text-sm font-medium text-gray-700">
        Portefeuille (entite: {data.entite?.nom})
      </label>
      {!creating ? (
        <>
          <select
            className="w-full border rounded-lg px-3 py-2 text-sm"
            value={data.portefeuille?.id || ''}
            onChange={(e) => {
              const pf = portefeuilles.find((x) => x.id === Number(e.target.value));
              setData((d) => ({ ...d, portefeuille: pf || null }));
            }}
          >
            <option value="">-- Sélectionnez --</option>
            {portefeuilles.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nom}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => setCreating(true)}
            className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
          >
            <Plus size={14} /> Créer un nouveau portefeuille
          </button>
        </>
      ) : (
        <div className="space-y-3 bg-blue-50 rounded-lg p-4">
          <input
            className="w-full border rounded-lg px-3 py-2 text-sm"
            placeholder="Nom *"
            value={form.nom}
            onChange={(e) => setForm((f) => ({ ...f, nom: e.target.value }))}
          />
          <input
            className="w-full border rounded-lg px-3 py-2 text-sm"
            placeholder="Description (optionnel)"
            value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => {
                if (!form.nom.trim()) return;
                setData((d) => ({
                  ...d,
                  portefeuille: { id: null, ...form, _new: true },
                }));
                setCreating(false);
              }}
              disabled={!form.nom.trim()}
              className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              Valider
            </button>
            <button
              type="button"
              onClick={() => setCreating(false)}
              className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800"
            >
              Annuler
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function StepSite({ data, setData }) {
  const site = data.site || {};
  const update = (field, value) => setData((d) => ({ ...d, site: { ...d.site, [field]: value } }));

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Nom du site *</label>
          <input
            className="w-full border rounded-lg px-3 py-2 text-sm"
            value={site.nom || ''}
            onChange={(e) => update('nom', e.target.value)}
            placeholder="Ex: Siege social Paris"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Type de site *</label>
          <select
            className="w-full border rounded-lg px-3 py-2 text-sm"
            value={site.type || ''}
            onChange={(e) => update('type', e.target.value)}
          >
            <option value="">-- Sélectionnez --</option>
            {SITE_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="border-t pt-3">
        <p className="text-xs text-gray-500 mb-3">Champs recommandes</p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <input
            className="border rounded-lg px-3 py-2 text-sm"
            placeholder="Adresse"
            value={site.adresse || ''}
            onChange={(e) => update('adresse', e.target.value)}
          />
          <input
            className="border rounded-lg px-3 py-2 text-sm"
            placeholder="Code postal"
            value={site.code_postal || ''}
            onChange={(e) => update('code_postal', e.target.value)}
          />
          <input
            className="border rounded-lg px-3 py-2 text-sm"
            placeholder="Ville"
            value={site.ville || ''}
            onChange={(e) => update('ville', e.target.value)}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Surface (m²)</label>
          <input
            type="number"
            className="w-full border rounded-lg px-3 py-2 text-sm"
            value={site.surface_m2 || ''}
            onChange={(e) => update('surface_m2', e.target.value ? Number(e.target.value) : null)}
            min="0"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Surface tertiaire (m²)
          </label>
          <input
            type="number"
            className="w-full border rounded-lg px-3 py-2 text-sm"
            value={site.tertiaire_area_m2 || ''}
            onChange={(e) =>
              update('tertiaire_area_m2', e.target.value ? Number(e.target.value) : null)
            }
            min="0"
          />
        </div>
      </div>

      <div className="border-t pt-3">
        <p className="text-xs text-gray-500 mb-3">Champs optionnels</p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <input
            className="border rounded-lg px-3 py-2 text-sm"
            placeholder="SIRET"
            value={site.siret || ''}
            onChange={(e) => update('siret', e.target.value)}
          />
          <input
            className="border rounded-lg px-3 py-2 text-sm"
            placeholder="Code NAF"
            value={site.naf_code || ''}
            onChange={(e) => update('naf_code', e.target.value)}
          />
          <input
            className="border rounded-lg px-3 py-2 text-sm"
            placeholder="Region"
            value={site.region || ''}
            onChange={(e) => update('region', e.target.value)}
          />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
          <input
            type="number"
            className="border rounded-lg px-3 py-2 text-sm"
            placeholder="Latitude"
            value={site.latitude || ''}
            onChange={(e) => update('latitude', e.target.value ? Number(e.target.value) : null)}
            step="0.0001"
          />
          <input
            type="number"
            className="border rounded-lg px-3 py-2 text-sm"
            placeholder="Longitude"
            value={site.longitude || ''}
            onChange={(e) => update('longitude', e.target.value ? Number(e.target.value) : null)}
            step="0.0001"
          />
        </div>
      </div>
    </div>
  );
}

function StepBatiments({ data, setData }) {
  const batiments = data.batiments || [];
  const addBat = () => {
    if (batiments.length >= 5) return;
    setData((d) => ({
      ...d,
      batiments: [
        ...d.batiments,
        { nom: '', surface_m2: '', annee_construction: '', cvc_power_kw: '' },
      ],
    }));
  };
  const removeBat = (idx) =>
    setData((d) => ({ ...d, batiments: d.batiments.filter((_, i) => i !== idx) }));
  const updateBat = (idx, field, value) =>
    setData((d) => ({
      ...d,
      batiments: d.batiments.map((b, i) => (i === idx ? { ...b, [field]: value } : b)),
    }));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-gray-700">Bâtiments (optionnel)</label>
        {batiments.length < 5 && (
          <button
            type="button"
            onClick={addBat}
            className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
          >
            <Plus size={14} /> Ajouter un batiment
          </button>
        )}
      </div>
      {batiments.length === 0 && (
        <p className="text-sm text-gray-500 italic">
          Aucun batiment. Vous pouvez passer cette etape.
        </p>
      )}
      {batiments.map((bat, idx) => (
        <div key={idx} className="bg-gray-50 rounded-lg p-4 space-y-3 relative">
          <button
            type="button"
            onClick={() => removeBat(idx)}
            className="absolute top-2 right-2 text-gray-400 hover:text-red-500"
          >
            <Trash2 size={14} />
          </button>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input
              className="border rounded-lg px-3 py-2 text-sm"
              placeholder="Nom du batiment *"
              value={bat.nom}
              onChange={(e) => updateBat(idx, 'nom', e.target.value)}
            />
            <input
              type="number"
              className="border rounded-lg px-3 py-2 text-sm"
              placeholder="Surface (m²) *"
              value={bat.surface_m2}
              onChange={(e) => updateBat(idx, 'surface_m2', e.target.value)}
              min="0"
            />
            <input
              type="number"
              className="border rounded-lg px-3 py-2 text-sm"
              placeholder="Annee construction"
              value={bat.annee_construction}
              onChange={(e) => updateBat(idx, 'annee_construction', e.target.value)}
            />
            <input
              type="number"
              className="border rounded-lg px-3 py-2 text-sm"
              placeholder="Puissance CVC (kW)"
              value={bat.cvc_power_kw}
              onChange={(e) => updateBat(idx, 'cvc_power_kw', e.target.value)}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function StepCompteurs({ data, setData }) {
  const compteurs = data.compteurs || [];
  const addCompteur = () => {
    if (compteurs.length >= 5) return;
    setData((d) => ({
      ...d,
      compteurs: [...d.compteurs, { prm: '', energy_type: 'electricity', puissance_souscrite: '' }],
    }));
  };
  const removeCompteur = (idx) =>
    setData((d) => ({ ...d, compteurs: d.compteurs.filter((_, i) => i !== idx) }));
  const updateCompteur = (idx, field, value) =>
    setData((d) => ({
      ...d,
      compteurs: d.compteurs.map((c, i) => (i === idx ? { ...c, [field]: value } : c)),
    }));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-gray-700">Compteurs (optionnel)</label>
        {compteurs.length < 5 && (
          <button
            type="button"
            onClick={addCompteur}
            className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
          >
            <Plus size={14} /> Ajouter un compteur
          </button>
        )}
      </div>
      {compteurs.length === 0 && (
        <p className="text-sm text-gray-500 italic">
          Aucun compteur. Vous pouvez passer cette etape.
        </p>
      )}
      {compteurs.map((c, idx) => (
        <div key={idx} className="bg-gray-50 rounded-lg p-4 space-y-3 relative">
          <button
            type="button"
            onClick={() => removeCompteur(idx)}
            className="absolute top-2 right-2 text-gray-400 hover:text-red-500"
          >
            <Trash2 size={14} />
          </button>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <input
              className="border rounded-lg px-3 py-2 text-sm"
              placeholder="PRM/PCE (14 chiffres) *"
              value={c.prm}
              onChange={(e) => updateCompteur(idx, 'prm', e.target.value)}
            />
            {c.prm && !validatePrm(c.prm) && (
              <p className="text-xs text-red-500 sm:col-span-2">PRM/PCE invalide (14 chiffres)</p>
            )}
            <select
              className="border rounded-lg px-3 py-2 text-sm"
              value={c.energy_type}
              onChange={(e) => updateCompteur(idx, 'energy_type', e.target.value)}
            >
              {ENERGY_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
            <input
              type="number"
              className="border rounded-lg px-3 py-2 text-sm"
              placeholder="Puissance souscrite (kVA)"
              value={c.puissance_souscrite}
              onChange={(e) => updateCompteur(idx, 'puissance_souscrite', e.target.value)}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function StepRecap({ data }) {
  const site = data.site || {};
  const batiments = data.batiments || [];
  const compteurs = data.compteurs || [];
  const siteType = SITE_TYPES.find((t) => t.value === site.type);

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-800">Recapitulatif</h3>
      <div className="bg-gray-50 rounded-lg p-4 space-y-3 text-sm">
        <div>
          <span className="font-medium text-gray-600">Societe :</span> {data.org?.nom}{' '}
          {data.org?._new && <span className="text-blue-600">(nouvelle)</span>}
        </div>
        <div>
          <span className="font-medium text-gray-600">Entité juridique :</span> {data.entite?.nom}{' '}
          {data.entite?._new && <span className="text-blue-600">(nouvelle)</span>}
        </div>
        <div>
          <span className="font-medium text-gray-600">Portefeuille :</span> {data.portefeuille?.nom}{' '}
          {data.portefeuille?._new && <span className="text-blue-600">(nouveau)</span>}
        </div>
        <div className="border-t pt-2">
          <span className="font-medium text-gray-600">Site :</span> {site.nom} ({siteType?.label})
          {site.ville && ` — ${site.ville}`}
          {site.surface_m2 && ` — ${site.surface_m2} m²`}
        </div>
        {batiments.length > 0 && (
          <div>
            <span className="font-medium text-gray-600">
              {batiments.length} batiment{batiments.length > 1 ? 's' : ''} :
            </span>{' '}
            {batiments.map((b) => b.nom).join(', ')}
          </div>
        )}
        {compteurs.length > 0 && (
          <div>
            <span className="font-medium text-gray-600">
              {compteurs.length} compteur{compteurs.length > 1 ? 's' : ''} :
            </span>{' '}
            {compteurs.map((c) => c.prm).join(', ')}
          </div>
        )}
      </div>
      <p className="text-xs text-gray-500">
        Cliquez sur <strong>Confirmer la creation</strong> pour creer tous les elements ci-dessus.
      </p>
    </div>
  );
}

// ── Main Wizard ────────────────────────────────────────────────────────────

export default function SiteCreationWizard({ onClose, onSuccess }) {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [wizardData, setWizardData] = useState({
    org: null,
    entite: null,
    portefeuille: null,
    site: {},
    batiments: [],
    compteurs: [],
  });
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  // ── Data loading for dropdowns ─────────────────────────────────────────
  const [orgs, setOrgs] = useState([]);
  const [entites, setEntites] = useState([]);
  const [portefeuilles, setPortefeuilles] = useState([]);
  const [loadingOrgs, setLoadingOrgs] = useState(true);
  const [loadingEntites, setLoadingEntites] = useState(false);
  const [loadingPfs, setLoadingPfs] = useState(false);

  // Load orgs on mount
  useEffect(() => {
    crudListOrganisations()
      .then((r) => {
        const list = r.organisations || [];
        setOrgs(list);
        // Auto-select if single org
        if (list.length === 1) {
          setWizardData((d) => ({ ...d, org: list[0] }));
        }
      })
      .catch(() => setOrgs([]))
      .finally(() => setLoadingOrgs(false));
  }, []);

  // Load entites when org changes
  useEffect(() => {
    const orgId = wizardData.org?.id;
    if (!orgId) {
      setEntites([]);
      return;
    }
    setLoadingEntites(true);
    crudListEntites({ org_id: orgId })
      .then((r) => {
        const list = r.entites || [];
        setEntites(list);
        if (list.length === 1) {
          setWizardData((d) => ({ ...d, entite: list[0] }));
        }
      })
      .catch(() => setEntites([]))
      .finally(() => setLoadingEntites(false));
  }, [wizardData.org?.id]);

  // Load portefeuilles when entite changes
  useEffect(() => {
    const entId = wizardData.entite?.id;
    if (!entId) {
      setPortefeuilles([]);
      return;
    }
    setLoadingPfs(true);
    crudListPortefeuilles({ entite_id: entId })
      .then((r) => {
        const list = r.portefeuilles || [];
        setPortefeuilles(list);
        if (list.length === 1) {
          setWizardData((d) => ({ ...d, portefeuille: list[0] }));
        }
      })
      .catch(() => setPortefeuilles([]))
      .finally(() => setLoadingPfs(false));
  }, [wizardData.entite?.id]);

  // ── Step validation ────────────────────────────────────────────────────
  const canProceed = useMemo(() => {
    const step = STEPS[currentStep];
    switch (step.id) {
      case 'org':
        return !!wizardData.org;
      case 'entite':
        return !!wizardData.entite;
      case 'portefeuille':
        return !!wizardData.portefeuille;
      case 'site':
        return !!(wizardData.site?.nom?.trim() && wizardData.site?.type);
      case 'batiments':
        // Optional — always valid (empty or all filled)
        return wizardData.batiments.every((b) => b.nom?.trim() && b.surface_m2);
      case 'compteurs':
        // Optional — always valid (empty or all with valid PRM)
        return wizardData.compteurs.every((c) => validatePrm(c.prm));
      case 'recap':
        return true;
      default:
        return false;
    }
  }, [currentStep, wizardData]);

  // ── Navigation ─────────────────────────────────────────────────────────
  const goNext = useCallback(() => {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep((s) => s + 1);
      setError(null);
    }
  }, [currentStep]);

  const goPrev = useCallback(() => {
    if (currentStep > 0) {
      setCurrentStep((s) => s - 1);
      setError(null);
    }
  }, [currentStep]);

  // ── Submit (sequential API calls) ──────────────────────────────────────
  const handleSubmit = useCallback(async () => {
    setSubmitting(true);
    setError(null);

    try {
      let orgId = wizardData.org.id;
      let entiteId = wizardData.entite.id;
      let pfId = wizardData.portefeuille.id;

      // 1. Create org if new
      if (wizardData.org._new) {
        const res = await crudCreateOrganisation({
          nom: wizardData.org.nom,
          siren: wizardData.org.siren,
        });
        orgId = res.id;
      }

      // 2. Create entite if new
      if (wizardData.entite._new) {
        const res = await crudCreateEntite({
          organisation_id: orgId,
          nom: wizardData.entite.nom,
          siren: wizardData.entite.siren,
          siret: wizardData.entite.siret || null,
          naf_code: wizardData.entite.naf_code || null,
        });
        entiteId = res.id;
      }

      // 3. Create portefeuille if new
      if (wizardData.portefeuille._new) {
        const res = await crudCreatePortefeuille({
          entite_juridique_id: entiteId,
          nom: wizardData.portefeuille.nom,
          description: wizardData.portefeuille.description || null,
        });
        pfId = res.id;
      }

      // 4. Create site
      const sitePayload = {
        portefeuille_id: pfId,
        nom: wizardData.site.nom,
        type: wizardData.site.type,
        adresse: wizardData.site.adresse || null,
        code_postal: wizardData.site.code_postal || null,
        ville: wizardData.site.ville || null,
        region: wizardData.site.region || null,
        surface_m2: wizardData.site.surface_m2 || null,
        tertiaire_area_m2: wizardData.site.tertiaire_area_m2 || null,
        siret: wizardData.site.siret || null,
        naf_code: wizardData.site.naf_code || null,
        latitude: wizardData.site.latitude || null,
        longitude: wizardData.site.longitude || null,
      };
      const siteRes = await crudCreateSite(sitePayload);
      const newSiteId = siteRes.id;

      // 5. Create batiments
      for (const bat of wizardData.batiments) {
        if (bat.nom?.trim() && bat.surface_m2) {
          await crudCreateBatiment({
            site_id: newSiteId,
            nom: bat.nom.trim(),
            surface_m2: Number(bat.surface_m2),
            annee_construction: bat.annee_construction ? Number(bat.annee_construction) : null,
            cvc_power_kw: bat.cvc_power_kw ? Number(bat.cvc_power_kw) : null,
          });
        }
      }

      // 6. Create compteurs
      for (const c of wizardData.compteurs) {
        if (validatePrm(c.prm)) {
          await createMeter({
            site_id: newSiteId,
            pdl: c.prm.replace(/[\s-]/g, ''),
            energy_type: c.energy_type,
            puissance_souscrite: c.puissance_souscrite ? Number(c.puissance_souscrite) : null,
          });
        }
      }

      // Success
      onSuccess?.();
      onClose();
      navigate(`/sites/${newSiteId}`);
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || 'Erreur inconnue';
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setSubmitting(false);
    }
  }, [wizardData, navigate, onClose, onSuccess]);

  const isRecap = STEPS[currentStep].id === 'recap';
  const isOptional = STEPS[currentStep].optional;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-lg font-semibold text-gray-800">Ajouter un site</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        {/* Progress bar */}
        <div className="px-6 py-3 border-b bg-gray-50">
          <div className="flex items-center gap-1">
            {STEPS.map((step, idx) => {
              const Icon = step.icon;
              const isCurrent = idx === currentStep;
              const isDone = idx < currentStep;
              return (
                <div key={step.id} className="flex items-center flex-1">
                  <div
                    className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium transition ${
                      isCurrent
                        ? 'bg-blue-100 text-blue-700'
                        : isDone
                          ? 'text-green-600'
                          : step.optional
                            ? 'text-gray-400'
                            : 'text-gray-500'
                    }`}
                  >
                    {isDone ? <Check size={12} /> : <Icon size={12} />}
                    <span className="hidden md:inline">{step.label}</span>
                  </div>
                  {idx < STEPS.length - 1 && (
                    <ChevronRight size={12} className="text-gray-300 mx-0.5 shrink-0" />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {STEPS[currentStep].id === 'org' && (
            <StepOrganisation
              data={wizardData}
              setData={setWizardData}
              orgs={orgs}
              loading={loadingOrgs}
            />
          )}
          {STEPS[currentStep].id === 'entite' && (
            <StepEntite
              data={wizardData}
              setData={setWizardData}
              entites={entites}
              loading={loadingEntites}
            />
          )}
          {STEPS[currentStep].id === 'portefeuille' && (
            <StepPortefeuille
              data={wizardData}
              setData={setWizardData}
              portefeuilles={portefeuilles}
              loading={loadingPfs}
            />
          )}
          {STEPS[currentStep].id === 'site' && (
            <StepSite data={wizardData} setData={setWizardData} />
          )}
          {STEPS[currentStep].id === 'batiments' && (
            <StepBatiments data={wizardData} setData={setWizardData} />
          )}
          {STEPS[currentStep].id === 'compteurs' && (
            <StepCompteurs data={wizardData} setData={setWizardData} />
          )}
          {STEPS[currentStep].id === 'recap' && <StepRecap data={wizardData} />}

          {/* Error display */}
          {error && (
            <div className="mt-4 flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
              <AlertCircle size={16} className="shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t bg-gray-50">
          <button
            onClick={goPrev}
            disabled={currentStep === 0}
            className="flex items-center gap-1 px-4 py-2 text-sm text-gray-600 hover:text-gray-800 disabled:opacity-30"
          >
            <ChevronLeft size={16} /> Précédent
          </button>
          <div className="flex items-center gap-2">
            {isOptional && (
              <button
                onClick={goNext}
                className="px-4 py-2 text-sm text-gray-500 hover:text-gray-700"
              >
                Passer cette etape
              </button>
            )}
            {isRecap ? (
              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="flex items-center gap-2 px-5 py-2 text-sm font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
              >
                {submitting ? (
                  <>
                    <Loader2 size={16} className="animate-spin" /> Creation en cours...
                  </>
                ) : (
                  <>
                    <Check size={16} /> Confirmer la creation
                  </>
                )}
              </button>
            ) : (
              <button
                onClick={goNext}
                disabled={!canProceed}
                className="flex items-center gap-1 px-5 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                Suivant <ChevronRight size={16} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
