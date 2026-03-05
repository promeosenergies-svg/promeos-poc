/**
 * PROMEOS — CreateActionDrawer (Étape 4)
 * Drawer version of CreateActionModal. Single entry point via ActionDrawerContext.
 * Adds: auto-deadline by severity, evidence_required toggle.
 */
import { useState, useEffect, useMemo } from 'react';
import { Paperclip, Lock } from 'lucide-react';
import Drawer from '../ui/Drawer';
import { Button, Input, Select } from '../ui';
import { track } from '../services/tracker';
import { createAction, getActionTemplates } from '../services/api';
import { computeEvidenceRequirement } from '../models/evidenceRules';
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

/** Auto-deadline offset in days by severity. */
export const DEADLINE_DAYS = { critical: 7, high: 14, medium: 30, low: 60 };

function autoDeadline(severity) {
  const days = DEADLINE_DAYS[severity];
  if (!days) return '';
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

export default function CreateActionDrawer({
  open,
  onClose,
  onSave,
  prefill = null,
  siteId = null,
  sourceType = 'manual',
  sourceId = null,
  idempotencyKey = null,
  evidenceRequired: defaultEvReq = false,
}) {
  const [saving, setSaving] = useState(false);
  const { orgSites, selectedSiteId: scopeSiteId } = useScope();

  const siteOptions = useMemo(() => {
    const opts = (orgSites || []).map((s) => ({ value: String(s.id), label: s.nom }));
    if (!opts.length) return [{ value: '', label: 'Aucun site' }];
    return [{ value: '', label: 'Sélectionner un site…' }, ...opts];
  }, [orgSites]);

  const defaultSiteValue = useMemo(() => {
    if (scopeSiteId) return String(scopeSiteId);
    if (orgSites?.length) return String(orgSites[0].id);
    return '';
  }, [scopeSiteId, orgSites]);

  const buildDefaults = () => ({
    titre: '',
    type: 'conformite',
    site: defaultSiteValue,
    impact_eur: '',
    effort: '',
    priorite: 'high',
    statut: 'backlog',
    owner: '',
    due_date: '',
    description: '',
    evidence_required: defaultEvReq,
    ...(prefill || {}),
  });

  const [form, setForm] = useState(buildDefaults);
  const [templates, setTemplates] = useState([]);

  // Fetch action templates on mount
  useEffect(() => {
    getActionTemplates()
      .then((d) => setTemplates(d?.templates || []))
      .catch(() => {});
  }, []);

  function applyTemplate(code) {
    if (!code) return;
    const tpl = templates.find((t) => t.code === code);
    if (!tpl) return;
    setForm((prev) => ({
      ...prev,
      titre: tpl.title,
      description: tpl.description || '',
      type:
        tpl.category === 'conformite'
          ? 'conformite'
          : tpl.category === 'achat'
            ? 'facture'
            : 'conso',
      impact_eur: tpl.estimated_gain_eur ? String(tpl.estimated_gain_eur) : '',
      priorite: tpl.priority <= 2 ? 'high' : 'medium',
      due_date: autoDeadline(tpl.priority <= 2 ? 'high' : 'medium'),
    }));
  }

  useEffect(() => {
    if (open) {
      const d = buildDefaults();
      // Auto-deadline if not already set
      if (!d.due_date && d.priorite) {
        d.due_date = autoDeadline(d.priorite);
      }
      // Auto evidence_required via centralized rules
      if (!prefill?.evidence_required) {
        const evReq = computeEvidenceRequirement({ sourceType, severity: d.priorite });
        d.evidence_required = evReq.required;
      }
      setForm(d);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, prefill, defaultEvReq]);

  // Evidence requirement computed from current form state
  const evidenceReq = useMemo(
    () => computeEvidenceRequirement({ sourceType, severity: form.priorite }),
    [sourceType, form.priorite]
  );

  function handleChange(field, value) {
    setForm((prev) => {
      const next = { ...prev, [field]: value };
      // Auto-adjust deadline when severity changes
      if (field === 'priorite' && !prev._deadlineLocked) {
        next.due_date = autoDeadline(value);
        // Auto evidence_required via centralized rules
        const evReq = computeEvidenceRequirement({ sourceType, severity: value });
        if (evReq.required) next.evidence_required = true;
      }
      // Mark deadline as manually edited
      if (field === 'due_date') next._deadlineLocked = true;
      return next;
    });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.titre.trim()) return;
    setSaving(true);
    try {
      const idemKey = idempotencyKey || prefill?._idempotencyKey || undefined;
      const impactEur = Number(form.impact_eur) || 0;
      const co2eKg = impactEur > 0 ? Math.round((impactEur / 0.15) * 0.052) : undefined;
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
        co2e_savings_est_kg: co2eKg,
        evidence_required: form.evidence_required || false,
      };
      const result = await createAction(payload);

      // Idempotency UX: detect existing action
      if (result?.status === 'existing') {
        track('action_create', { type: form.type, source: sourceType, existed: true });
        onSave?.({ ...result, _existed: true });
      } else {
        track('action_create', { type: form.type, source: sourceType, backend: true });
        onSave?.(result);
      }
    } catch (err) {
      // Error tracked via analytics; toast shown by interceptor
      track('action_create_error', { type: form.type, source: sourceType });
      setSaving(false);
      return; // Stay open so user can retry
    } finally {
      setSaving(false);
    }
    onClose();
  }

  const showEvidenceToggle =
    evidenceReq.required || form.priorite === 'critical' || form.priorite === 'high';

  return (
    <Drawer open={open} onClose={onClose} title="Créer une action" wide>
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Source context */}
        {sourceType && sourceType !== 'manual' && (
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <p className="text-[11px] font-semibold text-slate-500 uppercase mb-0.5">Source</p>
            <p className="text-sm text-slate-700 font-medium">
              {sourceType === 'compliance'
                ? 'Conformité'
                : sourceType === 'billing'
                  ? 'Facturation'
                  : sourceType === 'insight'
                    ? 'Diagnostic'
                    : sourceType}
              {sourceId && <span className="text-slate-400 ml-1.5">· {sourceId}</span>}
            </p>
          </div>
        )}

        {/* V113: Template selector */}
        {templates.length > 0 && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Modele d'action</label>
            <select
              onChange={(e) => applyTemplate(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              defaultValue=""
            >
              <option value="">-- Choisir un modele (optionnel) --</option>
              {templates.map((t) => (
                <option key={t.code} value={t.code}>
                  [{t.category}] {t.title}
                  {t.estimated_gain_eur ? ` (${t.estimated_gain_eur.toLocaleString('fr-FR')} EUR)` : ''}
                </option>
              ))}
            </select>
          </div>
        )}

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

        {/* Evidence required toggle — centralized rules */}
        {showEvidenceToggle && (
          <label
            className={`flex items-center gap-2 p-3 rounded-lg border cursor-pointer ${
              evidenceReq.lock
                ? 'bg-amber-50 border-amber-300'
                : form.evidence_required
                  ? 'bg-amber-50 border-amber-200'
                  : 'bg-slate-50 border-slate-200'
            }`}
          >
            <input
              type="checkbox"
              checked={form.evidence_required}
              onChange={(e) => handleChange('evidence_required', e.target.checked)}
              disabled={evidenceReq.lock}
              className="rounded border-amber-300 text-amber-600 focus:ring-amber-500"
            />
            {evidenceReq.lock ? (
              <Lock size={14} className="text-amber-600" />
            ) : (
              <Paperclip size={14} className="text-amber-600" />
            )}
            <span className="text-xs font-medium text-amber-700">Preuve requise pour clôturer</span>
            {evidenceReq.labelFR && (
              <span
                className={`ml-auto px-1.5 py-0.5 text-[10px] font-semibold rounded-full ${
                  evidenceReq.lock ? 'bg-amber-200 text-amber-800' : 'bg-slate-200 text-slate-600'
                }`}
              >
                {evidenceReq.lock ? 'Requis' : 'Recommandé'}
              </span>
            )}
          </label>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" type="button" onClick={onClose} disabled={saving}>
            Annuler
          </Button>
          <Button type="submit" disabled={saving}>
            {saving ? 'Enregistrement...' : "Créer l'action"}
          </Button>
        </div>
      </form>
    </Drawer>
  );
}
