/**
 * PROMEOS - Create Action Modal
 * Shared modal for creating actions from Dashboard, Patrimoine, Site360, Conformite.
 */
import { useState, useEffect, useMemo } from 'react';
import { Button, Input, Select } from '../ui';
import Modal from '../ui/Modal';
import { track } from '../services/tracker';
import { createAction } from '../services/api';
import { useScope } from '../contexts/ScopeContext';

const TYPE_OPTIONS = [
  { value: 'conformite', label: 'Conformité' },
  { value: 'conso', label: 'Consommation' },
  { value: 'facture', label: 'Facture' },
  { value: 'maintenance', label: 'Maintenance' },
];

const PRIORITE_OPTIONS = [
  { value: 'critical', label: 'Critique' },
  { value: 'high', label: 'Haute' },
  { value: 'medium', label: 'Moyenne' },
  { value: 'low', label: 'Basse' },
];

const STATUT_OPTIONS = [
  { value: 'backlog', label: 'À planifier' },
  { value: 'planned', label: 'Planifiée' },
  { value: 'in_progress', label: 'En cours' },
];

export default function CreateActionModal({
  open,
  onClose,
  onSave,
  defaultSite = '',
  defaultType = 'conformite',
  prefill = null,
  siteId = null,
  sourceType = 'manual',
  sourceId = null,
  idempotencyKey = null,
}) {
  const [saving, setSaving] = useState(false);
  const { orgSites, selectedSiteId: scopeSiteId } = useScope();

  const siteOptions = useMemo(() => {
    const opts = (orgSites || []).map((s) => ({ value: String(s.id), label: s.nom }));
    if (!opts.length) return [{ value: '', label: 'Aucun site' }];
    return [{ value: '', label: 'Sélectionner un site…' }, ...opts];
  }, [orgSites]);

  const resolvedDefaultSite = useMemo(() => {
    if (defaultSite) return defaultSite;
    if (scopeSiteId) return String(scopeSiteId);
    if (orgSites?.length) return String(orgSites[0].id);
    return '';
  }, [defaultSite, scopeSiteId, orgSites]);

  const defaults = {
    titre: '',
    type: defaultType,
    site: resolvedDefaultSite,
    impact_eur: '',
    effort: '',
    priorite: 'high',
    statut: 'backlog',
    owner: '',
    due_date: '',
    description: '',
    ...(prefill || {}),
  };
  const [form, setForm] = useState(defaults);

  useEffect(() => {
    if (open) {
      setForm({
        titre: '',
        type: defaultType,
        site: resolvedDefaultSite,
        impact_eur: '',
        effort: '',
        priorite: 'high',
        statut: 'backlog',
        owner: '',
        due_date: '',
        description: '',
        ...(prefill || {}),
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, prefill]);

  function handleChange(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.titre.trim()) return;
    setSaving(true);
    try {
      const idemKey = idempotencyKey || prefill?._idempotencyKey || undefined;
      const impactEur = Number(form.impact_eur) || 0;
      // CO2e calculé backend (config/emission_factors.py ELEC=0.052 kgCO₂e/kWh ADEME V23.6)
      // Ne PAS calculer côté front — le backend enrichit co2e_savings_est_kg post-création
      const payload = {
        title: form.titre.trim(),
        source_type: sourceType || 'manual',
        source_id: sourceId || undefined,
        site_id: siteId || (form.site ? Number(form.site) : undefined),
        severity: form.priorite || undefined,
        estimated_gain_eur: impactEur || undefined,
        due_date: form.due_date || undefined,
        owner: form.owner || undefined,
        notes: form.description || undefined,
        rationale: form.description || undefined,
        idempotency_key: idemKey,
        // co2e_savings_est_kg : calculé backend post-création (ADEME 0.052)
      };
      const result = await createAction(payload);
      track('action_create', { type: form.type, site: form.site, backend: true });
      onSave(result);
    } catch {
      // Fallback: emit local action for graceful degradation
      const action = {
        ...form,
        id: Date.now(),
        impact_eur: Number(form.impact_eur) || 0,
        created_at: new Date().toISOString(),
      };
      track('action_create', { type: form.type, site: form.site, backend: false });
      onSave(action);
    } finally {
      setSaving(false);
    }
    setForm({
      titre: '',
      type: defaultType,
      site: resolvedDefaultSite,
      impact_eur: '',
      effort: '',
      priorite: 'high',
      statut: 'backlog',
      owner: '',
      due_date: '',
      description: '',
    });
    onClose();
  }

  return (
    <Modal open={open} onClose={onClose} title="Créer une action" wide>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Titre"
          placeholder="ex: Déclarer OPERAT pour Bureau Paris 3"
          value={form.titre}
          onChange={(e) => handleChange('titre', e.target.value)}
          required
        />
        <div className="grid grid-cols-2 gap-4">
          <Select
            label="Type"
            options={TYPE_OPTIONS}
            value={form.type}
            onChange={(e) => handleChange('type', e.target.value)}
          />
          <Select
            label="Priorité"
            options={PRIORITE_OPTIONS}
            value={form.priorite}
            onChange={(e) => handleChange('priorite', e.target.value)}
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Select
            label="Site concerné"
            options={siteOptions}
            value={form.site}
            onChange={(e) => handleChange('site', e.target.value)}
          />
          <Select
            label="Statut"
            options={STATUT_OPTIONS}
            value={form.statut}
            onChange={(e) => handleChange('statut', e.target.value)}
          />
        </div>
        <div className="grid grid-cols-3 gap-4">
          <Input
            label="Impact EUR"
            type="number"
            placeholder="5000"
            value={form.impact_eur}
            onChange={(e) => handleChange('impact_eur', e.target.value)}
          />
          <Input
            label="Effort (j/h)"
            placeholder="2j"
            value={form.effort}
            onChange={(e) => handleChange('effort', e.target.value)}
          />
          <Input
            label="Échéance"
            type="date"
            value={form.due_date}
            onChange={(e) => handleChange('due_date', e.target.value)}
          />
        </div>
        <Input
          label="Responsable"
          placeholder="Jean Dupont"
          value={form.owner}
          onChange={(e) => handleChange('owner', e.target.value)}
        />
        {form.obligation_code && (
          <div className="p-3 bg-blue-50 rounded-lg">
            <p className="text-xs font-semibold text-blue-600 uppercase mb-0.5">Obligation liée</p>
            <p className="text-sm text-blue-800 font-medium">{form.obligation_code}</p>
          </div>
        )}
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">Description</label>
          <textarea
            rows={3}
            placeholder="Détails supplémentaires..."
            value={form.description}
            onChange={(e) => handleChange('description', e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm placeholder:text-gray-400
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" type="button" onClick={onClose} disabled={saving}>
            Annuler
          </Button>
          <Button type="submit" disabled={saving}>
            {saving ? 'Enregistrement...' : "Créer l'action"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
