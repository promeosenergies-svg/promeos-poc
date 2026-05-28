/**
 * PROMEOS — Drawer Modulation DT (Phase 3 · enrichi S2 2026-05-28).
 *
 * Simulateur de dossier de modulation pour une EFA.
 * Consomme POST /api/tertiaire/modulation-simulation (zero calcul metier
 * frontend — doctrine §8.1).
 *
 * S2 simplicité métier (2026-05-28) — TRI par typologie :
 *   Le backend `tertiaire_modulation_service` renvoie déjà `tri_par_typologie`
 *   avec label_fr, tri_ans, seuil_disproportion_ans, is_disproportionate,
 *   source, source_url (Article 11.I arrêté 10/04/2020 modifié). Le drawer
 *   rend désormais cette décomposition (typologie → durée réglementaire,
 *   TRI calculé, décision disproportion / non-disproportion) avec sources
 *   Légifrance cliquables — vocabulaire FR exclusif aligné sur la doctrine
 *   §6 conformité (« enveloppe du bâtiment », « équipements », « optimisation
 *   et exploitation »).
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
  ExternalLink,
} from 'lucide-react';
import { Drawer, Button, Badge } from '../../ui';
import Explain from '../../ui/Explain';
import { simulateModulation } from '../../services/api';
import { fmtEur, fmtKwh } from '../../utils/format';

const CONSTRAINT_TYPES = [
  { value: 'technique', label: 'Technique' },
  { value: 'architecturale', label: 'Architecturale' },
  { value: 'economique', label: 'Économique' },
];

// Vocabulaire FR exclusif aligné sur la doctrine §6 conformité PROMEOS.
// Source canonique : Article 11.I de l'arrêté 10/04/2020 modifié.
// Le 4ᵉ libellé « systèmes locaux et personnalisés » est rendu en
// sous-libellé contextuel quand la typologie OPTIMIZATION_SYSTEM est
// utilisée pour des dispositifs GTB/GTC/BACS (cf. Annexe IV BACS).
const TYPOLOGY_OPTIONS = [
  { value: '', label: 'Sélectionner une typologie…' },
  {
    value: 'STRUCTURAL_ENVELOPE',
    label: 'Enveloppe du bâtiment',
    helper: "Travaux structuraux d'isolation, façade, toiture, menuiseries.",
  },
  {
    value: 'ENERGY_EQUIPMENT',
    label: 'Équipements',
    helper: 'Renouvellement CVC, ECS, éclairage, ventilation.',
  },
  {
    value: 'OPTIMIZATION_SYSTEM',
    label: 'Optimisation et exploitation',
    helper: 'Systèmes locaux et personnalisés : GTB / GTC / BACS, pilotage.',
  },
];

const EMPTY_ACTION = {
  label: '',
  cout_eur: '',
  economie_annuelle_kwh: '',
  economie_annuelle_eur: '',
  duree_vie_ans: '',
  typologie: '',
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
                // S2 — propagation de la typologie OPERAT (Article 11.I)
                // au backend pour le test de disproportion par typologie.
                // Vide → backend marque UNKNOWN (fail-closed prudent).
                typologie: a.typologie || undefined,
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
              placeholder="Ex : bâtiment classé — isolation extérieure impossible"
              rows={2}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
        </div>

        {/* Actions */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-medium text-gray-500 uppercase">
              Actions envisagées
            </label>
            <button
              type="button"
              onClick={addAction}
              className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
            >
              <Plus size={12} /> Ajouter
            </button>
          </div>
          <div className="space-y-3">
            {actions.map((a, i) => (
              <div
                key={i}
                className="p-3 border border-gray-200 rounded-lg space-y-2"
                data-testid="modulation-action-row"
              >
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
                      type="button"
                      onClick={() => removeAction(i)}
                      className="ml-2 text-gray-400 hover:text-red-500"
                      aria-label="Supprimer l'action"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>

                {/* S2 — Typologie OPERAT Art. 11.I (test disproportion par
                    typologie). Optionnelle : si absente, l'action n'est pas
                    comptée dans la décomposition (fail-closed prudent). */}
                <div>
                  <label className="text-[10px] text-gray-400 uppercase tracking-wider">
                    Typologie OPERAT (Art. 11.I)
                  </label>
                  <select
                    value={a.typologie}
                    onChange={(e) => updateAction(i, 'typologie', e.target.value)}
                    data-testid="modulation-action-typologie"
                    className="mt-0.5 block w-full text-sm border border-gray-200 rounded px-2 py-1"
                  >
                    {TYPOLOGY_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                  {a.typologie &&
                    (() => {
                      const helper = TYPOLOGY_OPTIONS.find((o) => o.value === a.typologie)?.helper;
                      return helper ? (
                        <p className="text-[10px] text-gray-500 mt-0.5">{helper}</p>
                      ) : null;
                    })()}
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-gray-400">Coût (€)</label>
                    <input
                      type="number"
                      value={a.cout_eur}
                      onChange={(e) => updateAction(i, 'cout_eur', e.target.value)}
                      className="w-full text-sm border border-gray-200 rounded px-2 py-1"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-gray-400">Économie kWh/an</label>
                    <input
                      type="number"
                      value={a.economie_annuelle_kwh}
                      onChange={(e) => updateAction(i, 'economie_annuelle_kwh', e.target.value)}
                      className="w-full text-sm border border-gray-200 rounded px-2 py-1"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-gray-400">Économie €/an</label>
                    <input
                      type="number"
                      value={a.economie_annuelle_eur}
                      onChange={(e) => updateAction(i, 'economie_annuelle_eur', e.target.value)}
                      className="w-full text-sm border border-gray-200 rounded px-2 py-1"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-gray-400">Durée de vie (ans)</label>
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
            {typeof error === 'string' ? error : JSON.stringify(error)}
          </div>
        )}

        {/* Résultat */}
        {result && (
          <div className="space-y-4 border-t border-gray-200 pt-4" data-testid="modulation-result">
            <h4 className="text-sm font-semibold text-gray-700">Résultat de la simulation</h4>

            {/* Barre visuelle objectif */}
            <div>
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>Objectif initial : {fmtKwh(result.objectif_initial_kwh)}</span>
                <span>Modulé : {fmtKwh(result.objectif_module_kwh)}</span>
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
                  +{result.delta_objectif_pct} % d'assouplissement demandé
                </p>
              )}
            </div>

            {/* KPIs globaux */}
            <div className="grid grid-cols-2 gap-3 text-center">
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500">TRI moyen (agrégé)</p>
                <p className="text-lg font-bold text-gray-900">{result.tri_moyen_ans} ans</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500">Coût total</p>
                <p className="text-lg font-bold text-gray-900">{fmtEur(result.cout_total_eur)}</p>
              </div>
            </div>

            {/* S2 — Décomposition TRI par typologie (Article 11.I) */}
            {Array.isArray(result.tri_par_typologie) && result.tri_par_typologie.length > 0 && (
              <div data-testid="modulation-tri-par-typologie">
                <div className="flex items-center justify-between mb-2">
                  <h5 className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Disproportion économique par typologie
                  </h5>
                  <Badge status={result.disproportion_globale ? 'warn' : 'ok'}>
                    {result.disproportion_globale
                      ? 'Disproportion invocable'
                      : 'Pas de disproportion'}
                  </Badge>
                </div>
                <div className="overflow-x-auto rounded-lg border border-gray-200">
                  <table className="w-full text-xs">
                    <thead className="bg-gray-50 text-gray-500">
                      <tr>
                        <th className="text-left px-3 py-2 font-semibold">Typologie</th>
                        <th className="text-right px-3 py-2 font-semibold">Durée réglementaire</th>
                        <th className="text-right px-3 py-2 font-semibold">TRI calculé</th>
                        <th className="text-left px-3 py-2 font-semibold">Décision</th>
                        <th className="text-left px-3 py-2 font-semibold">Source</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.tri_par_typologie.map((row) => (
                        <tr
                          key={row.typologie}
                          className="border-t border-gray-100"
                          data-testid={`modulation-tri-row-${row.typologie}`}
                        >
                          <td className="px-3 py-2 text-gray-800">
                            <div className="font-medium">{row.label_fr}</div>
                            <div className="text-[10px] text-gray-400 font-mono">
                              {row.typologie} · {row.actions_count} action
                              {row.actions_count > 1 ? 's' : ''}
                            </div>
                          </td>
                          <td className="px-3 py-2 text-right text-gray-700">
                            {row.seuil_disproportion_ans} ans
                          </td>
                          <td
                            className={`px-3 py-2 text-right font-semibold ${
                              row.is_disproportionate ? 'text-amber-700' : 'text-gray-800'
                            }`}
                          >
                            {row.tri_ans != null ? `${row.tri_ans} ans` : '—'}
                          </td>
                          <td className="px-3 py-2">
                            {row.is_disproportionate ? (
                              <span className="inline-flex items-center gap-1 text-amber-700">
                                <AlertTriangle size={12} /> Disproportion
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-green-700">
                                <CheckCircle2 size={12} /> Non disproportionnée
                              </span>
                            )}
                          </td>
                          <td className="px-3 py-2">
                            {row.source_url ? (
                              <a
                                href={row.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800"
                              >
                                Légifrance <ExternalLink size={10} />
                              </a>
                            ) : (
                              <span className="text-gray-400">—</span>
                            )}
                            <div className="text-[10px] text-gray-400">{row.source}</div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {/* Formule + période + confiance (TrustBadge inline,
                    aligné contrat « source / formule / unité / période /
                    confiance » obligatoire sur tout chiffre réglementaire). */}
                <div className="mt-2 grid grid-cols-1 sm:grid-cols-3 gap-2 text-[11px] text-gray-500">
                  <div>
                    <span className="font-semibold text-gray-600">Formule&nbsp;:</span> TRI = coût
                    (€) ÷ économie annuelle (€/an)
                  </div>
                  <div>
                    <span className="font-semibold text-gray-600">Période&nbsp;:</span> Jalons -40 %
                    / -50 % / -60 % (2030 / 2040 / 2050)
                  </div>
                  <div>
                    <span className="font-semibold text-gray-600">Confiance&nbsp;:</span> Verbatim
                    Légifrance · Article 11.I
                  </div>
                </div>
                {result.disproportion_explication && (
                  <p className="mt-2 text-xs text-gray-700">{result.disproportion_explication}</p>
                )}
              </div>
            )}

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
              <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 space-y-1">
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
                Ce simulateur prépare votre dossier de modulation. Le dépôt officiel se fait sur
                OPERAT avant le 30/09/2026.
              </p>
            </div>
          </div>
        )}
      </div>
    </Drawer>
  );
}
