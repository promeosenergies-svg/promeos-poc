/**
 * PROMEOS — Drawer Modulation DT (Phase 3)
 * Simulateur de dossier de modulation pour une EFA.
 * Consomme POST /api/tertiaire/modulation-simulation (zero calcul metier frontend).
 */
import { useState, useCallback } from 'react';
import {
  Calculator,
  Plus,
  Trash2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  Info,
} from 'lucide-react';
import { Drawer, Button, Badge } from '../../ui';
import Explain from '../../ui/Explain';
import { simulateModulation } from '../../services/api';
import { fmtEur, fmtKwh } from '../../utils/format';

const CONSTRAINT_TYPES = [
  { value: 'technique', label: 'Technique' },
  { value: 'architecturale', label: 'Architecturale' },
  { value: 'economique', label: 'Economique' },
];

const EMPTY_ACTION = {
  label: '',
  cout_eur: '',
  economie_annuelle_kwh: '',
  economie_annuelle_eur: '',
  duree_vie_ans: '',
};

export default function ModulationDrawer({ open, onClose, efaId, efaNom }) {
  const [constraintType, setConstraintType] = useState('technique');
  const [description, setDescription] = useState('');
  const [actions, setActions] = useState([{ ...EMPTY_ACTION }]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const addAction = () => setActions([...actions, { ...EMPTY_ACTION }]);
  const removeAction = (i) => setActions(actions.filter((_, idx) => idx !== i));
  const updateAction = (i, field, value) => {
    const updated = [...actions];
    updated[i] = { ...updated[i], [field]: value };
    setActions(updated);
  };

  const simulate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const body = {
        efa_id: efaId,
        contraintes: [
          {
            type: constraintType,
            description,
            actions: actions
              .filter((a) => a.label && a.cout_eur)
              .map((a) => ({
                label: a.label,
                cout_eur: Number(a.cout_eur) || 0,
                economie_annuelle_kwh: Number(a.economie_annuelle_kwh) || 0,
                economie_annuelle_eur: Number(a.economie_annuelle_eur) || 0,
                duree_vie_ans: Number(a.duree_vie_ans) || 0,
              })),
          },
        ],
      };
      const res = await simulateModulation(body);
      setResult(res);
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur de simulation');
    } finally {
      setLoading(false);
    }
  }, [efaId, constraintType, description, actions]);

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={
        <>
          Simulation <Explain term="modulation_dt">modulation</Explain>
        </>
      }
      wide
    >
      <div className="space-y-5" data-testid="modulation-drawer">
        <p className="text-sm text-gray-600">
          EFA : <span className="font-medium">{efaNom}</span>
        </p>

        {/* Formulaire contrainte */}
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-gray-500 uppercase">
              Type de contrainte
            </label>
            <select
              value={constraintType}
              onChange={(e) => setConstraintType(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              {CONSTRAINT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-gray-500 uppercase">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Ex: Batiment classe — isolation exterieure impossible"
              rows={2}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
        </div>

        {/* Actions */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-medium text-gray-500 uppercase">
              Actions envisagees
            </label>
            <button
              onClick={addAction}
              className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
            >
              <Plus size={12} /> Ajouter
            </button>
          </div>
          <div className="space-y-3">
            {actions.map((a, i) => (
              <div key={i} className="p-3 border border-gray-200 rounded-lg space-y-2">
                <div className="flex items-center justify-between">
                  <input
                    type="text"
                    placeholder="Label action"
                    value={a.label}
                    onChange={(e) => updateAction(i, 'label', e.target.value)}
                    className="flex-1 text-sm border-b border-gray-200 focus:border-blue-400 outline-none py-1"
                  />
                  {actions.length > 1 && (
                    <button
                      onClick={() => removeAction(i)}
                      className="ml-2 text-gray-400 hover:text-red-500"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-gray-400">Cout (EUR)</label>
                    <input
                      type="number"
                      value={a.cout_eur}
                      onChange={(e) => updateAction(i, 'cout_eur', e.target.value)}
                      className="w-full text-sm border border-gray-200 rounded px-2 py-1"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-gray-400">Economie kWh/an</label>
                    <input
                      type="number"
                      value={a.economie_annuelle_kwh}
                      onChange={(e) => updateAction(i, 'economie_annuelle_kwh', e.target.value)}
                      className="w-full text-sm border border-gray-200 rounded px-2 py-1"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-gray-400">Economie EUR/an</label>
                    <input
                      type="number"
                      value={a.economie_annuelle_eur}
                      onChange={(e) => updateAction(i, 'economie_annuelle_eur', e.target.value)}
                      className="w-full text-sm border border-gray-200 rounded px-2 py-1"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-gray-400">Duree de vie (ans)</label>
                    <input
                      type="number"
                      value={a.duree_vie_ans}
                      onChange={(e) => updateAction(i, 'duree_vie_ans', e.target.value)}
                      className="w-full text-sm border border-gray-200 rounded px-2 py-1"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Bouton simuler */}
        <Button onClick={simulate} disabled={loading} className="w-full">
          {loading ? (
            <Loader2 size={14} className="animate-spin mr-2" />
          ) : (
            <Calculator size={14} className="mr-2" />
          )}
          Simuler l'impact
        </Button>

        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Resultat */}
        {result && (
          <div className="space-y-4 border-t border-gray-200 pt-4" data-testid="modulation-result">
            <h4 className="text-sm font-semibold text-gray-700">Resultat de la simulation</h4>

            {/* Barre visuelle objectif */}
            <div>
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>Objectif initial : {fmtKwh(result.objectif_initial_kwh)}</span>
                <span>Module : {fmtKwh(result.objectif_module_kwh)}</span>
              </div>
              <div className="h-4 bg-gray-100 rounded-full overflow-hidden flex">
                <div
                  className="bg-blue-500 h-full"
                  style={{
                    width: `${Math.min(100, (result.objectif_initial_kwh / result.objectif_module_kwh) * 100)}%`,
                  }}
                />
                <div
                  className="bg-amber-400 h-full"
                  style={{
                    width: `${Math.max(0, 100 - (result.objectif_initial_kwh / result.objectif_module_kwh) * 100)}%`,
                  }}
                />
              </div>
              {result.delta_objectif_pct > 0 && (
                <p className="text-xs text-amber-600 mt-1">
                  +{result.delta_objectif_pct} % d'assouplissement demande
                </p>
              )}
            </div>

            {/* KPIs */}
            <div className="grid grid-cols-2 gap-3 text-center">
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500">TRI moyen</p>
                <p className="text-lg font-bold text-gray-900">{result.tri_moyen_ans} ans</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500">Cout total</p>
                <p className="text-lg font-bold text-gray-900">{fmtEur(result.cout_total_eur)}</p>
              </div>
            </div>

            {/* Score readiness */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-gray-600">Score robustesse dossier</span>
                <Badge
                  status={
                    result.dossier_readiness_score >= 80
                      ? 'ok'
                      : result.dossier_readiness_score >= 50
                        ? 'warn'
                        : 'crit'
                  }
                >
                  {result.dossier_readiness_score}/100
                </Badge>
              </div>
              <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${
                    result.dossier_readiness_score >= 80
                      ? 'bg-green-500'
                      : result.dossier_readiness_score >= 50
                        ? 'bg-amber-500'
                        : 'bg-red-500'
                  }`}
                  style={{ width: `${result.dossier_readiness_score}%` }}
                />
              </div>
            </div>

            {/* Checklist */}
            <div className="space-y-1.5">
              {result.criteres_remplis?.map((c) => (
                <div key={c} className="flex items-center gap-2 text-sm text-green-700">
                  <CheckCircle2 size={14} className="shrink-0" /> {c}
                </div>
              ))}
              {result.criteres_manquants?.map((c) => (
                <div key={c} className="flex items-center gap-2 text-sm text-red-500">
                  <XCircle size={14} className="shrink-0" /> {c}
                </div>
              ))}
            </div>

            {/* Warnings */}
            {result.warnings?.length > 0 && (
              <div className="rounded-lg bg-amber-50 border border-amber-200 p-3">
                {result.warnings.map((w, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs text-amber-700">
                    <AlertTriangle size={12} className="shrink-0 mt-0.5" /> {w}
                  </div>
                ))}
              </div>
            )}

            {/* Note */}
            <div className="rounded-lg bg-blue-50 border border-blue-200 p-3 flex items-start gap-2">
              <Info size={14} className="text-blue-500 shrink-0 mt-0.5" />
              <p className="text-xs text-blue-700">
                Ce simulateur prepare votre dossier de modulation. Le depot officiel se fait sur
                OPERAT avant le 30/09/2026.
              </p>
            </div>
          </div>
        )}
      </div>
    </Drawer>
  );
}
