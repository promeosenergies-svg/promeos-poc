/**
 * SmeBegesProfileCard — Conformité P1 2026-05-23
 *
 * Saisie minimale des données entreprise nécessaires aux gates SMÉ/BEGES :
 * - Organisation : effectif_total, chiffre_affaires_eur, bilan_eur
 * - Entité juridique : consommation_annuelle_moyenne_3y_gwh, iso_50001 (actif + date_validite)
 *
 * Doctrine /conformite hub unique : pas de menu Settings, on saisit ici.
 * REGLE ABSOLUE : pas de calcul métier — les gates (SMÉ, BEGES) sont calculées
 * côté backend par `regulatory_rules_service` après PATCH.
 */
import { useState, useEffect } from 'react';
import { Building2, ChevronDown, ChevronUp, Save } from 'lucide-react';
import { Button } from '../../ui';
import api from '../../services/api/core';
import { crudUpdateOrganisation, crudUpdateEntite, crudListEntites } from '../../services/api';
import { useToast } from '../../ui/ToastProvider';

const FieldNumber = ({ id, label, value, onChange, suffix, step = 1, min = 0 }) => (
  <div className="flex flex-col gap-1">
    <label htmlFor={id} className="text-xs text-gray-600">
      {label}
    </label>
    <div className="flex items-center gap-1">
      <input
        id={id}
        type="number"
        min={min}
        step={step}
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))}
        className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:border-emerald-500 focus:outline-none"
      />
      {suffix && <span className="text-xs text-gray-500">{suffix}</span>}
    </div>
  </div>
);

export default function SmeBegesProfileCard({ org, onUpdated }) {
  const { toast } = useToast();
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [entites, setEntites] = useState([]);
  const [selectedEjId, setSelectedEjId] = useState(null);
  const [orgForm, setOrgForm] = useState({
    effectif_total: null,
    chiffre_affaires_eur: null,
    bilan_eur: null,
  });
  const [ejForm, setEjForm] = useState({
    consommation_annuelle_moyenne_3y_gwh: null,
    iso_50001_actif: false,
    iso_50001_date_validite: null,
  });

  // Fetch full org detail on open (useScope ne porte que id+nom).
  useEffect(() => {
    if (!open || !org?.id) return;
    api
      .get(`/patrimoine/crud/organisations/${org.id}`)
      .then((r) => {
        const o = r.data || {};
        setOrgForm({
          effectif_total: o.effectif_total ?? null,
          chiffre_affaires_eur: o.chiffre_affaires_eur ?? null,
          bilan_eur: o.bilan_eur ?? null,
        });
      })
      .catch(() => {});
  }, [open, org?.id]);

  // Load EJs of the org
  useEffect(() => {
    if (!open || !org?.id) return;
    crudListEntites({ organisation_id: org.id })
      .then((data) => {
        const list = data?.entites || [];
        setEntites(list);
        if (list.length > 0 && !selectedEjId) {
          setSelectedEjId(list[0].id);
        }
      })
      .catch(() => setEntites([]));
  }, [open, org?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Hydrate EJ form when selectedEjId changes
  useEffect(() => {
    if (!selectedEjId) return;
    const ej = entites.find((e) => e.id === selectedEjId);
    if (!ej) return;
    setEjForm({
      consommation_annuelle_moyenne_3y_gwh: ej.consommation_annuelle_moyenne_3y_gwh ?? null,
      iso_50001_actif: !!ej.iso_50001_actif,
      iso_50001_date_validite: ej.iso_50001_date_validite ?? null,
    });
  }, [selectedEjId, entites]);

  const handleSave = async () => {
    if (!org?.id) return;
    setSaving(true);
    try {
      await crudUpdateOrganisation(org.id, orgForm);
      if (selectedEjId) {
        await crudUpdateEntite(selectedEjId, ejForm);
      }
      toast('Profil entreprise mis à jour — les règles SMÉ/BEGES seront recalculées', 'success');
      if (onUpdated) onUpdated();
    } catch (err) {
      const msg =
        err?.response?.data?.detail?.message ||
        (Array.isArray(err?.response?.data?.detail) ? err.response.data.detail[0]?.msg : null) ||
        'Erreur lors de la sauvegarde';
      toast(msg, 'error');
    } finally {
      setSaving(false);
    }
  };

  if (!org) return null;

  return (
    <div className="mt-4 rounded-lg border border-gray-200 bg-white">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-3 hover:bg-gray-50"
        aria-expanded={open}
      >
        <div className="flex items-center gap-2">
          <Building2 size={16} className="text-emerald-600" />
          <span className="font-medium text-sm text-gray-900">Profil entreprise (SMÉ / BEGES)</span>
          <span className="text-xs text-gray-500">
            — effectif, CA, bilan, conso 3 ans, ISO 50001
          </span>
        </div>
        {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      {open && (
        <div className="border-t border-gray-100 p-4">
          <p className="mb-3 text-xs text-gray-600">
            Ces données déterminent si vous êtes assujetti à l'Audit énergétique réglementaire (Loi
            2025-391) et au BEGES (Décret 2022-982). Mise à jour annuelle recommandée.
          </p>

          {/* Organisation */}
          <div className="mb-4">
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-700">
              Groupe consolidé — {org.nom}
            </h4>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <FieldNumber
                id="org-effectif"
                label="Effectif total (ETP)"
                value={orgForm.effectif_total}
                onChange={(v) => setOrgForm({ ...orgForm, effectif_total: v })}
              />
              <FieldNumber
                id="org-ca"
                label="Chiffre d'affaires"
                value={orgForm.chiffre_affaires_eur}
                onChange={(v) => setOrgForm({ ...orgForm, chiffre_affaires_eur: v })}
                suffix="€"
                step={1000}
              />
              <FieldNumber
                id="org-bilan"
                label="Bilan"
                value={orgForm.bilan_eur}
                onChange={(v) => setOrgForm({ ...orgForm, bilan_eur: v })}
                suffix="€"
                step={1000}
              />
            </div>
          </div>

          {/* Entité juridique */}
          {entites.length > 0 && (
            <div className="mb-4">
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-700">
                Entité juridique
              </h4>
              {entites.length > 1 && (
                <div className="mb-3">
                  <label htmlFor="ej-select" className="text-xs text-gray-600">
                    Sélectionner une entité
                  </label>
                  <select
                    id="ej-select"
                    value={selectedEjId ?? ''}
                    onChange={(e) => setSelectedEjId(Number(e.target.value))}
                    className="mt-1 w-full rounded border border-gray-300 px-2 py-1 text-sm"
                  >
                    {entites.map((e) => (
                      <option key={e.id} value={e.id}>
                        {e.nom} ({e.siren})
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <FieldNumber
                  id="ej-conso"
                  label="Consommation moyenne 3 ans"
                  value={ejForm.consommation_annuelle_moyenne_3y_gwh}
                  onChange={(v) =>
                    setEjForm({ ...ejForm, consommation_annuelle_moyenne_3y_gwh: v })
                  }
                  suffix="GWh"
                  step={0.1}
                />
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-gray-600" htmlFor="ej-iso">
                    Certification ISO 50001 active
                  </label>
                  <div className="flex items-center gap-2 pt-1">
                    <input
                      id="ej-iso"
                      type="checkbox"
                      checked={ejForm.iso_50001_actif}
                      onChange={(e) => setEjForm({ ...ejForm, iso_50001_actif: e.target.checked })}
                      className="h-4 w-4 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                    />
                    <span className="text-xs text-gray-700">
                      {ejForm.iso_50001_actif ? 'Oui' : 'Non'}
                    </span>
                  </div>
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-gray-600" htmlFor="ej-iso-date">
                    Validité ISO 50001
                  </label>
                  <input
                    id="ej-iso-date"
                    type="date"
                    value={ejForm.iso_50001_date_validite ?? ''}
                    onChange={(e) =>
                      setEjForm({
                        ...ejForm,
                        iso_50001_date_validite: e.target.value || null,
                      })
                    }
                    disabled={!ejForm.iso_50001_actif}
                    className="w-full rounded border border-gray-300 px-2 py-1 text-sm disabled:bg-gray-50 disabled:text-gray-400"
                  />
                </div>
              </div>
            </div>
          )}

          <div className="flex justify-end">
            <Button onClick={handleSave} disabled={saving} size="sm">
              <Save size={14} />
              {saving ? 'Sauvegarde...' : 'Enregistrer le profil'}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
