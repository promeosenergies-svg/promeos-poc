/**
 * PROMEOS V39 — Assistant création EFA (7 étapes)
 * Route: /conformite/tertiaire/wizard
 */
import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Building2, MapPin, Ruler, Users, Calendar, FileText, CheckCircle2,
  ArrowRight, ArrowLeft, Loader2,
} from 'lucide-react';
import { PageShell, Card, CardBody, Button, Input, Select, Badge } from '../../ui';
import {
  createTertiaireEfa, addTertiaireBuilding, addTertiaireResponsibility,
} from '../../services/api';
import ProofDepositCTA from './components/ProofDepositCTA';

const STEPS = [
  { key: 'nom', label: 'Identification', icon: Building2, description: 'Nom et type de l\'EFA' },
  { key: 'role', label: 'Rôle assujetti', icon: Users, description: 'Propriétaire, locataire ou mandataire' },
  { key: 'batiment', label: 'Bâtiment', icon: MapPin, description: 'Association bâtiment et surface' },
  { key: 'usage', label: 'Usage', icon: Ruler, description: 'Catégorie d\'activité OPERAT' },
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
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    nom: '',
    role_assujetti: 'proprietaire',
    surface_m2: '',
    usage_label: '',
    resp_entity: '',
    resp_email: '',
    reporting_start: '',
    notes: '',
  });

  const updateField = useCallback((field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  }, []);

  const canNext = () => {
    switch (step) {
      case 0: return form.nom.trim().length > 0;
      case 1: return !!form.role_assujetti;
      case 2: return form.surface_m2 && Number(form.surface_m2) > 0;
      case 3: return !!form.usage_label;
      case 4: return true;
      case 5: return true;
      case 6: return true;
      default: return false;
    }
  };

  const handleSubmit = async () => {
    setSaving(true);
    try {
      // 1. Create EFA
      const efa = await createTertiaireEfa({
        org_id: 1,
        nom: form.nom.trim(),
        role_assujetti: form.role_assujetti,
        reporting_start: form.reporting_start || null,
        notes: form.notes || null,
      });

      // 2. Add building
      if (form.surface_m2) {
        await addTertiaireBuilding(efa.id, {
          usage_label: form.usage_label || null,
          surface_m2: Number(form.surface_m2),
        });
      }

      // 3. Add responsibility
      if (form.resp_entity || form.resp_email) {
        await addTertiaireResponsibility(efa.id, {
          role: form.role_assujetti,
          entity_value: form.resp_entity || null,
          contact_email: form.resp_email || null,
        });
      }

      navigate(`/conformite/tertiaire/efa/${efa.id}`);
    } catch (err) {
      console.error('Erreur création EFA:', err);
      setSaving(false);
    }
  };

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

          {/* Step content */}
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

          {step === 2 && (
            <div className="space-y-4">
              <Input
                label="Surface tertiaire (m²)"
                type="number"
                value={form.surface_m2}
                onChange={(e) => updateField('surface_m2', e.target.value)}
                placeholder="Ex : 2500"
              />
              <p className="text-xs text-gray-400">
                Le seuil d'assujettissement est de 1 000 m² de surface de plancher.
              </p>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <p className="text-sm text-gray-600 mb-3">Catégorie d'activité principale :</p>
              <div className="grid grid-cols-2 gap-2">
                {USAGES.map((u) => (
                  <button
                    key={u}
                    type="button"
                    onClick={() => updateField('usage_label', u)}
                    className={`text-left p-3 rounded-lg border text-sm transition-colors ${
                      form.usage_label === u
                        ? 'border-indigo-500 bg-indigo-50 font-medium'
                        : 'border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    {u}
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 4 && (
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

          {step === 5 && (
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

          {step === 6 && (
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-gray-700">Récapitulatif</h4>
              <div className="rounded-lg border border-gray-200 divide-y divide-gray-100">
                {[
                  ['Nom', form.nom],
                  ['Rôle', ROLES.find((r) => r.value === form.role_assujetti)?.label || form.role_assujetti],
                  ['Surface', form.surface_m2 ? `${form.surface_m2} m²` : 'Non renseignée'],
                  ['Usage', form.usage_label || 'Non renseigné'],
                  ['Responsable', form.resp_entity || 'Non renseigné'],
                  ['Email', form.resp_email || 'Non renseigné'],
                  ['Début reporting', form.reporting_start || 'Non renseigné'],
                ].map(([label, value]) => (
                  <div key={label} className="flex justify-between px-4 py-2.5">
                    <span className="text-xs text-gray-500">{label}</span>
                    <span className="text-xs font-medium text-gray-900">{value}</span>
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
                    `Surface:${form.surface_m2 || '?'} m²`,
                    `Usage:${form.usage_label || '?'}`,
                  ].join(' | ')}
                  label="Déposer une preuve dans la Mémobox"
                  variant="secondary"
                  size="xs"
                />
              </div>
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
