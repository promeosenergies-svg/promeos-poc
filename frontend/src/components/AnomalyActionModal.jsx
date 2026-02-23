/**
 * AnomalyActionModal — V65
 * Modale légère (front-only, pas d'API) pour créer ou éditer
 * une action locale associée à une anomalie.
 * Stockage : localStorage via anomalyActions.js
 */
import { useState, useEffect } from 'react';
import Modal from '../ui/Modal';
import { Button, Input } from '../ui';
import {
  getAnomalyAction,
  saveAnomalyAction,
  ACTION_STATUS,
  ACTION_STATUS_LABEL,
} from '../services/anomalyActions';

const STATUS_OPTIONS = [
  { value: ACTION_STATUS.TODO,        label: ACTION_STATUS_LABEL.todo        },
  { value: ACTION_STATUS.IN_PROGRESS, label: ACTION_STATUS_LABEL.in_progress },
  { value: ACTION_STATUS.RESOLVED,    label: ACTION_STATUS_LABEL.resolved    },
];

const EMPTY_FORM = {
  title:    '',
  status:   ACTION_STATUS.TODO,
  owner:    '',
  due_date: '',
  notes:    '',
};

/**
 * @param {object}  props
 * @param {boolean} props.open
 * @param {function} props.onClose
 * @param {number|string|null} props.orgId
 * @param {number}  props.siteId
 * @param {string}  props.anomalyCode
 * @param {string}  props.anomalyTitle - Prérempli dans le champ titre
 */
export default function AnomalyActionModal({ open, onClose, orgId, siteId, anomalyCode, anomalyTitle }) {
  const [form, setForm] = useState(EMPTY_FORM);

  // Charger l'action existante (ou préremplir le titre) à l'ouverture
  useEffect(() => {
    if (!open) return;
    const existing = getAnomalyAction(orgId, siteId, anomalyCode);
    if (existing) {
      setForm({
        title:    existing.title    ?? anomalyTitle ?? '',
        status:   existing.status   ?? ACTION_STATUS.TODO,
        owner:    existing.owner    ?? '',
        due_date: existing.due_date ?? '',
        notes:    existing.notes    ?? '',
      });
    } else {
      setForm({ ...EMPTY_FORM, title: anomalyTitle ?? '' });
    }
  }, [open, orgId, siteId, anomalyCode, anomalyTitle]);

  function handleChange(field, value) {
    setForm(prev => ({ ...prev, [field]: value }));
  }

  function handleSave(e) {
    e.preventDefault();
    if (!form.title.trim()) return;
    saveAnomalyAction(orgId, siteId, anomalyCode, {
      title:    form.title.trim(),
      status:   form.status,
      owner:    form.owner.trim(),
      due_date: form.due_date,
      notes:    form.notes.trim(),
    });
    onClose();
  }

  function handleMarkResolved() {
    saveAnomalyAction(orgId, siteId, anomalyCode, {
      title:    (form.title || anomalyTitle || '').trim(),
      status:   ACTION_STATUS.RESOLVED,
      owner:    form.owner.trim(),
      due_date: form.due_date,
      notes:    form.notes.trim(),
    });
    onClose();
  }

  return (
    <Modal open={open} onClose={onClose} title="Action sur anomalie">
      <form onSubmit={handleSave} className="space-y-3">

        {/* Titre */}
        <Input
          label="Titre de l'action"
          placeholder="ex : Déclarer OPERAT pour ce site"
          value={form.title}
          onChange={e => handleChange('title', e.target.value)}
          required
        />

        {/* Statut */}
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">Statut</label>
          <select
            value={form.status}
            onChange={e => handleChange('status', e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
          >
            {STATUS_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        {/* Responsable + Échéance */}
        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Responsable"
            placeholder="Jean Dupont"
            value={form.owner}
            onChange={e => handleChange('owner', e.target.value)}
          />
          <Input
            label="Échéance"
            type="date"
            value={form.due_date}
            onChange={e => handleChange('due_date', e.target.value)}
          />
        </div>

        {/* Notes */}
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">Notes</label>
          <textarea
            rows={2}
            placeholder="Détails ou contexte supplémentaire..."
            value={form.notes}
            onChange={e => handleChange('notes', e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between pt-1">
          <button
            type="button"
            onClick={handleMarkResolved}
            className="text-sm font-medium text-green-600 hover:text-green-700 hover:underline transition"
          >
            Marquer comme résolu
          </button>
          <div className="flex items-center gap-2">
            <Button variant="secondary" type="button" onClick={onClose}>Annuler</Button>
            <Button type="submit">Sauvegarder</Button>
          </div>
        </div>

      </form>
    </Modal>
  );
}
