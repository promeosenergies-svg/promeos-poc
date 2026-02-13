/**
 * PROMEOS - Create Action Modal
 * Shared modal for creating actions from Dashboard, Patrimoine, Site360, Conformite.
 */
import { useState, useEffect } from 'react';
import { Button, Input, Select } from '../ui';
import Modal from '../ui/Modal';
import { track } from '../services/tracker';

const TYPE_OPTIONS = [
  { value: 'conformite', label: 'Conformite' },
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
  { value: 'backlog', label: 'Backlog' },
  { value: 'planned', label: 'Planifiee' },
  { value: 'in_progress', label: 'En cours' },
];

export default function CreateActionModal({ open, onClose, onSave, defaultSite = '', defaultType = 'conformite', prefill = null }) {
  const defaults = {
    titre: '',
    type: defaultType,
    site: defaultSite,
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
        titre: '', type: defaultType, site: defaultSite, impact_eur: '', effort: '',
        priorite: 'high', statut: 'backlog', owner: '', due_date: '', description: '',
        ...(prefill || {}),
      });
    }
  }, [open, prefill]);

  function handleChange(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (!form.titre.trim()) return;
    const action = {
      ...form,
      id: Date.now(),
      impact_eur: Number(form.impact_eur) || 0,
      created_at: new Date().toISOString(),
    };
    track('action_create', { type: form.type, site: form.site });
    onSave(action);
    setForm({ titre: '', type: defaultType, site: defaultSite, impact_eur: '', effort: '', priorite: 'high', statut: 'backlog', owner: '', due_date: '', description: '' });
    onClose();
  }

  return (
    <Modal open={open} onClose={onClose} title="Creer une action" wide>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Titre"
          placeholder="ex: Declarer OPERAT pour Bureau Paris 3"
          value={form.titre}
          onChange={(e) => handleChange('titre', e.target.value)}
          required
        />
        <div className="grid grid-cols-2 gap-4">
          <Select label="Type" options={TYPE_OPTIONS} value={form.type} onChange={(e) => handleChange('type', e.target.value)} />
          <Select label="Priorite" options={PRIORITE_OPTIONS} value={form.priorite} onChange={(e) => handleChange('priorite', e.target.value)} />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Input label="Site concerne" placeholder="Bureau Paris 3" value={form.site} onChange={(e) => handleChange('site', e.target.value)} />
          <Select label="Statut" options={STATUT_OPTIONS} value={form.statut} onChange={(e) => handleChange('statut', e.target.value)} />
        </div>
        <div className="grid grid-cols-3 gap-4">
          <Input label="Impact EUR" type="number" placeholder="5000" value={form.impact_eur} onChange={(e) => handleChange('impact_eur', e.target.value)} />
          <Input label="Effort (j/h)" placeholder="2j" value={form.effort} onChange={(e) => handleChange('effort', e.target.value)} />
          <Input label="Echeance" type="date" value={form.due_date} onChange={(e) => handleChange('due_date', e.target.value)} />
        </div>
        <Input label="Responsable" placeholder="Jean Dupont" value={form.owner} onChange={(e) => handleChange('owner', e.target.value)} />
        {form.obligation_code && (
          <div className="p-3 bg-blue-50 rounded-lg">
            <p className="text-xs font-semibold text-blue-600 uppercase mb-0.5">Obligation liee</p>
            <p className="text-sm text-blue-800 font-medium">{form.obligation_code}</p>
          </div>
        )}
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">Description</label>
          <textarea
            rows={3}
            placeholder="Details supplementaires..."
            value={form.description}
            onChange={(e) => handleChange('description', e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm placeholder:text-gray-400
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" type="button" onClick={onClose}>Annuler</Button>
          <Button type="submit">Creer l'action</Button>
        </div>
      </form>
    </Modal>
  );
}
