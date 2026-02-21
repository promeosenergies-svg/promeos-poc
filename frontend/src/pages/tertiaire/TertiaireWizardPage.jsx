/**
 * PROMEOS V41 — Assistant création EFA (6 étapes)
 * Route: /conformite/tertiaire/wizard
 * Sélection de bâtiments depuis le Patrimoine (zéro duplication).
 */
import { useState, useCallback, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Building2, MapPin, Users, Calendar, CheckCircle2,
  ArrowRight, ArrowLeft, Loader2, AlertTriangle,
} from 'lucide-react';
import { PageShell, Card, CardBody, Button, Input, Select, Badge } from '../../ui';
import {
  createTertiaireEfa, addTertiaireResponsibility, getTertiaireCatalog,
} from '../../services/api';
import ProofDepositCTA from './components/ProofDepositCTA';

export const STEPS = [
  { key: 'nom', label: 'Identification', icon: Building2, description: "Nom et type de l'EFA" },
  { key: 'role', label: 'Rôle assujetti', icon: Users, description: 'Propriétaire, locataire ou mandataire' },
  { key: 'batiments', label: 'Bâtiments', icon: MapPin, description: 'Sélectionner les bâtiments du patrimoine' },
  { key: 'responsable', label: 'Responsable', icon: Users, description: 'Contact du responsable EFA' },
  { key: 'reporting', label: 'Reporting', icon: Calendar, description: 'Période et année de référence' },
  { key: 'confirmation', label: 'Confirmation', icon: CheckCircle2, description: 'Vérification et création' },
];

const ROLES = [
  { value: 'proprietaire', label: 'Propriétaire' },
  { value: 'locataire', label: 'Locataire' },
  { value: 'mandataire', label: 'Mandataire' },
];

const USAGES = [
  'Bureaux',
  'Commerce',
  'Enseignement',
  'Hôtellerie',
  'Santé',
  'Logistique / Entrepôt',
  'Industrie tertiaire',
  'Administration',
  'Culture / Loisirs',
  'Autre',
];

export default function TertiaireWizardPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const prefillSiteId = searchParams.get('site_id');
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [form, setForm] = useState({
    nom: '',
    role_assujetti: 'proprietaire',
    selectedBuildings: [],
    resp_entity: '',
    resp_email: '',
    reporting_start: '',
    notes: '',
  });

  // V41: Patrimoine catalog
  const [catalog, setCatalog] = useState(null);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [catalogError, setCatalogError] = useState(null);

  useEffect(() => {
    setCatalogLoading(true);
    getTertiaireCatalog()
      .then((data) => {
        setCatalog(data);
        // V42: Auto-select buildings from prefill site_id
        if (prefillSiteId && data?.sites) {
          const targetSite = data.sites.find(
            (s) => String(s.site_id) === prefillSiteId
          );
          if (targetSite && targetSite.batiments.length > 0) {
            const preselected = targetSite.batiments.map((bat) => ({
              building_id: bat.id,
              nom: bat.nom,
              surface_m2: bat.surface_m2,
              site_nom: targetSite.site_nom,
              usage_label: '',
            }));
            updateField('selectedBuildings', preselected);
          }
        }
      })
      .catch((err) => setCatalogError(err?.message || 'Erreur chargement patrimoine'))
      .finally(() => setCatalogLoading(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const updateField = useCallback((field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  }, []);

  const canNext = () => {
    switch (step) {
      case 0: return form.nom.trim().length > 0;
      case 1: return !!form.role_assujetti;
      case 2: return form.selectedBuildings.length > 0
               && form.selectedBuildings.every((b) => !!b.usage_label);
      case 3: return true;
      case 4: return true;
      case 5: return true;
      default: return false;
    }
  };

  const handleSubmit = async () => {
    setSaving(true);
    setSubmitError(null);
    try {
      // V41: Create EFA with buildings atomically
      const efa = await createTertiaireEfa({
        org_id: 1,
        nom: form.nom.trim(),
        role_assujetti: form.role_assujetti,
        reporting_start: form.reporting_start || null,
        notes: form.notes || null,
        buildings: form.selectedBuildings.map((b) => ({
          building_id: b.building_id,
          usage_label: b.usage_label,
        })),
      });

      // Add responsibility (still separate, only if provided)
      if (form.resp_entity || form.resp_email) {
        await addTertiaireResponsibility(efa.id, {
          role: form.role_assujetti,
          entity_value: form.resp_entity || null,
          contact_email: form.resp_email || null,
        });
      }

      navigate(`/conformite/tertiaire/efa/${efa.id}`, { state: { justCreated: true } });
    } catch (err) {
      console.error('Erreur création EFA:', err);
      const detail = err?.response?.data?.detail || err?.message || 'Erreur inconnue';
      setSubmitError(`Impossible de créer l'EFA : ${detail}`);
      setSaving(false);
    }
  };

  const toggleBuilding = (bat, siteName) => {
    const exists = form.selectedBuildings.find((b) => b.building_id === bat.id);
    if (exists) {
      updateField('selectedBuildings',
        form.selectedBuildings.filter((b) => b.building_id !== bat.id));
    } else {
      updateField('selectedBuildings', [
        ...form.selectedBuildings,
        {
          building_id: bat.id,
          nom: bat.nom,
          surface_m2: bat.surface_m2,
          site_nom: siteName,
          usage_label: '',
        },
      ]);
    }
  };

  const setUsageForBuilding = (buildingId, usageLabel) => {
    updateField('selectedBuildings',
      form.selectedBuildings.map((b) =>
        b.building_id === buildingId ? { ...b, usage_label: usageLabel } : b
      ));
  };

  const totalSurface = form.selectedBuildings.reduce((s, b) => s + (b.surface_m2 || 0), 0);
  const currentStep = STEPS[step];

  return (
    <PageShell
      title="Nouvelle EFA — Assistant"
      subtitle={`Étape ${step + 1}/${STEPS.length} — ${currentStep.label}`}
      backPath="/conformite/tertiaire"
    >
      {/* Progress bar */}
      <div className="flex gap-1 mb-6">
        {STEPS.map((s, i) => (
          <div
            key={s.key}
            className={`h-1 flex-1 rounded-full transition-colors ${
              i <= step ? 'bg-indigo-500' : 'bg-gray-200'
            }`}
          />
        ))}
      </div>

      <Card>
        <CardBody className="p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-lg bg-indigo-100 flex items-center justify-center">
              <currentStep.icon size={20} className="text-indigo-600" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-gray-900">{currentStep.label}</h3>
              <p className="text-sm text-gray-500">{currentStep.description}</p>
            </div>
          </div>

          {/* Step 0: Identification */}
          {step === 0 && (
            <div className="space-y-4">
              <Input
                label="Nom de l'EFA"
                value={form.nom}
                onChange={(e) => updateField('nom', e.target.value)}
                placeholder="Ex : Tour Montparnasse — Bureaux étages 10-20"
              />
            </div>
          )}

          {/* Step 1: Rôle assujetti */}
          {step === 1 && (
            <div className="space-y-4">
              <p className="text-sm text-gray-600 mb-3">
                Quel est votre rôle par rapport à cette entité fonctionnelle ?
              </p>
              <div className="space-y-2">
                {ROLES.map((r) => (
                  <button
                    key={r.value}
                    type="button"
                    onClick={() => updateField('role_assujetti', r.value)}
                    className={`w-full text-left p-3 rounded-lg border transition-colors ${
                      form.role_assujetti === r.value
                        ? 'border-indigo-500 bg-indigo-50'
                        : 'border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <span className="text-sm font-medium text-gray-900">{r.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 2: Bâtiments du patrimoine (V41) */}
          {step === 2 && (
            <div className="space-y-4">
              {catalogLoading && (
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <Loader2 size={16} className="animate-spin" />
                  Chargement du patrimoine…
                </div>
              )}

              {catalogError && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-3">
                  <p className="text-sm text-red-700">{catalogError}</p>
                </div>
              )}

              {catalog && catalog.total_buildings === 0 && (
                <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-center">
                  <AlertTriangle size={24} className="mx-auto text-amber-500 mb-2" />
                  <p className="text-sm font-medium text-amber-800">
                    Aucun bâtiment dans le patrimoine
                  </p>
                  <p className="text-xs text-amber-600 mt-1 mb-3">
                    Pour créer une EFA, vous devez d'abord enregistrer vos bâtiments dans le module Patrimoine.
                  </p>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => navigate('/patrimoine')}
                  >
                    Compléter le patrimoine
                  </Button>
                </div>
              )}

              {catalog && catalog.total_buildings > 0 && (
                <>
                  <p className="text-sm text-gray-600">
                    Sélectionnez un ou plusieurs bâtiments, puis choisissez l'usage OPERAT pour chacun :
                  </p>
                  {catalog.sites.map((site) => (
                    site.batiments.length > 0 && (
                      <div key={site.site_id} className="border border-gray-200 rounded-lg p-3">
                        <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
                          {site.site_nom}{site.ville ? ` — ${site.ville}` : ''}
                        </p>
                        {site.batiments.map((bat) => {
                          const selected = form.selectedBuildings.find(
                            (b) => b.building_id === bat.id
                          );
                          return (
                            <div key={bat.id} className="flex items-center gap-3 py-2 border-b border-gray-50 last:border-0">
                              <input
                                type="checkbox"
                                checked={!!selected}
                                onChange={() => toggleBuilding(bat, site.site_nom)}
                                className="h-4 w-4 rounded border-gray-300 text-indigo-600"
                              />
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-gray-900">{bat.nom}</p>
                                <p className="text-xs text-gray-400">
                                  {bat.surface_m2} m²
                                  {bat.annee_construction ? ` · ${bat.annee_construction}` : ''}
                                </p>
                              </div>
                              {selected && (
                                <select
                                  value={selected.usage_label}
                                  onChange={(e) => setUsageForBuilding(bat.id, e.target.value)}
                                  className="w-48 text-sm border border-gray-300 rounded-md px-2 py-1"
                                  data-testid={`usage-select-${bat.id}`}
                                >
                                  <option value="">Usage OPERAT…</option>
                                  {USAGES.map((u) => (
                                    <option key={u} value={u}>{u}</option>
                                  ))}
                                </select>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )
                  ))}

                  {/* Surface totale (lecture seule) */}
                  {form.selectedBuildings.length > 0 && (
                    <div className="rounded-lg bg-indigo-50 border border-indigo-100 p-3">
                      <p className="text-xs text-indigo-600 font-medium">
                        Surface totale : {totalSurface.toLocaleString('fr-FR')} m²
                        ({form.selectedBuildings.length} bâtiment{form.selectedBuildings.length > 1 ? 's' : ''})
                      </p>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* Step 3: Responsable */}
          {step === 3 && (
            <div className="space-y-4">
              <Input
                label="Entité responsable"
                value={form.resp_entity}
                onChange={(e) => updateField('resp_entity', e.target.value)}
                placeholder="Ex : SCI Immobilier Tertiaire"
              />
              <Input
                label="Email de contact"
                type="email"
                value={form.resp_email}
                onChange={(e) => updateField('resp_email', e.target.value)}
                placeholder="contact@exemple.fr"
              />
            </div>
          )}

          {/* Step 4: Reporting */}
          {step === 4 && (
            <div className="space-y-4">
              <Input
                label="Début de la période de reporting"
                type="date"
                value={form.reporting_start}
                onChange={(e) => updateField('reporting_start', e.target.value)}
              />
              <Input
                label="Notes (optionnel)"
                value={form.notes}
                onChange={(e) => updateField('notes', e.target.value)}
                placeholder="Informations complémentaires…"
              />
            </div>
          )}

          {/* Step 5: Confirmation */}
          {step === 5 && (
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-gray-700">Récapitulatif</h4>
              <div className="rounded-lg border border-gray-200 divide-y divide-gray-100">
                {[
                  ['Nom', form.nom],
                  ['Rôle', ROLES.find((r) => r.value === form.role_assujetti)?.label || form.role_assujetti],
                  ['Bâtiments', form.selectedBuildings.length > 0
                    ? form.selectedBuildings.map((b) => `${b.nom} (${b.surface_m2} m² — ${b.usage_label})`).join(', ')
                    : 'Aucun'],
                  ['Surface totale', form.selectedBuildings.length > 0
                    ? `${totalSurface.toLocaleString('fr-FR')} m²`
                    : 'Non renseignée'],
                  ['Responsable', form.resp_entity || 'Non renseigné'],
                  ['Email', form.resp_email || 'Non renseigné'],
                  ['Début reporting', form.reporting_start || 'Non renseigné'],
                ].map(([label, value]) => (
                  <div key={label} className="flex justify-between px-4 py-2.5">
                    <span className="text-xs text-gray-500">{label}</span>
                    <span className="text-xs font-medium text-gray-900 max-w-[60%] text-right">{value}</span>
                  </div>
                ))}
              </div>

              {/* Preuves (optionnel) — ne bloque pas la création */}
              <div className="mt-4 p-3 rounded-lg border border-dashed border-amber-300 bg-amber-50/50">
                <p className="text-xs text-amber-700 font-medium mb-2">
                  Preuves (optionnel)
                </p>
                <p className="text-[11px] text-amber-600 mb-2">
                  Vous pouvez déposer des justificatifs OPERAT (attestation, dossier de modulation…) dans la Mémobox.
                  Cette étape est facultative et peut être réalisée ultérieurement.
                </p>
                <ProofDepositCTA
                  hint={[
                    `EFA:${form.nom || '(nouveau)'}`,
                    'Étape:Confirmation',
                    `Rôle:${ROLES.find((r) => r.value === form.role_assujetti)?.label || form.role_assujetti}`,
                    `Bâtiments:${form.selectedBuildings.length}`,
                    `Surface:${totalSurface} m²`,
                  ].join(' | ')}
                  label="Déposer une preuve dans la Mémobox"
                  variant="secondary"
                  size="xs"
                />
              </div>
            </div>
          )}

          {/* Erreur de soumission */}
          {submitError && (
            <div data-testid="wizard-submit-error" className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 flex items-start gap-2">
              <AlertTriangle size={16} className="text-red-500 shrink-0 mt-0.5" />
              <p className="text-sm text-red-700">{submitError}</p>
            </div>
          )}

          {/* Navigation */}
          <div className="flex items-center justify-between mt-8">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => step > 0 ? setStep(step - 1) : navigate('/conformite/tertiaire')}
            >
              <ArrowLeft size={14} /> {step > 0 ? 'Précédent' : 'Annuler'}
            </Button>

            {step < STEPS.length - 1 ? (
              <Button size="sm" onClick={() => setStep(step + 1)} disabled={!canNext()}>
                Suivant <ArrowRight size={14} />
              </Button>
            ) : (
              <Button size="sm" onClick={handleSubmit} disabled={saving}>
                {saving ? <><Loader2 size={14} className="animate-spin" /> Création…</> : 'Créer l\'EFA'}
              </Button>
            )}
          </div>
        </CardBody>
      </Card>
    </PageShell>
  );
}
