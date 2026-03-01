/**
 * PROMEOS - BacsWizard (Decret BACS Expert)
 * 4-step wizard: Eligibilite, Inventaire CVC, Resultat, Plan d'actions
 */
import { useState, useCallback } from 'react';
import {
  X, ChevronRight, ChevronLeft, Check, Plus, Trash2,
  ShieldCheck, AlertTriangle, Clock, Calculator, FileText,
  Building2, Thermometer, Snowflake, Wind,
} from 'lucide-react';
import { Card, CardBody, Badge, Button } from '../ui';
import {
  createBacsAsset, addCvcSystem, recomputeBacs,
  getBacsScoreExplain,
} from '../services/api';

const PHASES = [
  { id: 'eligibilite', label: 'Éligibilité', icon: Building2 },
  { id: 'inventaire', label: 'Inventaire CVC', icon: Thermometer },
  { id: 'resultat', label: 'Résultat', icon: ShieldCheck },
  { id: 'actions', label: 'Plan d\'actions', icon: FileText },
];

const SYSTEM_TYPES = [
  { value: 'heating', label: 'Chauffage', icon: Thermometer, color: 'text-red-500' },
  { value: 'cooling', label: 'Climatisation', icon: Snowflake, color: 'text-blue-500' },
  { value: 'ventilation', label: 'Ventilation', icon: Wind, color: 'text-gray-500' },
];

const ARCHITECTURES = [
  { value: 'cascade', label: 'Cascade', desc: 'Unités en série — Putile = somme des kW' },
  { value: 'network', label: 'Réseau', desc: 'Unités en réseau — Putile = somme des kW' },
  { value: 'independent', label: 'Indépendant', desc: 'Unités séparées — Putile = max des kW' },
];

function ProgressBar({ phase }) {
  return (
    <div className="flex items-center gap-2 px-6 py-3 border-b border-gray-100 bg-gray-50">
      {PHASES.map((p, i) => {
        const Icon = p.icon;
        const isCurrent = i === phase;
        const isDone = i < phase;
        return (
          <div key={p.id} className="flex items-center gap-2 flex-1">
            <div className={`flex items-center gap-1.5 text-xs font-medium
              ${isCurrent ? 'text-blue-600' : isDone ? 'text-green-600' : 'text-gray-400'}`}>
              {isDone ? <Check size={14} /> : <Icon size={14} />}
              <span className="hidden sm:inline">{p.label}</span>
            </div>
            {i < PHASES.length - 1 && (
              <div className={`flex-1 h-0.5 ${isDone ? 'bg-green-400' : 'bg-gray-200'}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Phase 1: Eligibilite ──

function StepEligibilite({ data, setData, onNext }) {
  return (
    <div className="space-y-5">
      <h3 className="text-base font-semibold text-gray-800">Éligibilité & périmètre</h3>

      <label className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg cursor-pointer">
        <input
          type="checkbox"
          checked={data.is_tertiary}
          onChange={(e) => setData({ ...data, is_tertiary: e.target.checked })}
          className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
        <div>
          <p className="text-sm font-medium text-gray-800">Bâtiment tertiaire non-résidentiel</p>
          <p className="text-xs text-gray-500">Critère obligatoire pour le décret BACS</p>
        </div>
      </label>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Date du permis de construire</label>
        <input
          type="date"
          value={data.pc_date || ''}
          onChange={(e) => setData({ ...data, pc_date: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      <label className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg cursor-pointer">
        <input
          type="checkbox"
          checked={data.has_renewal}
          onChange={(e) => setData({ ...data, has_renewal: e.target.checked })}
          className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
        <div>
          <p className="text-sm font-medium text-gray-800">Renouvellement CVC depuis le 09/04/2023</p>
          <p className="text-xs text-gray-500">Déclenche l'obligation même sous 70 kW</p>
        </div>
      </label>

      {data.has_renewal && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Date du renouvellement</label>
          <input
            type="date"
            value={data.renewal_date || ''}
            onChange={(e) => setData({ ...data, renewal_date: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Responsable</label>
        <select
          value={data.responsible_type || 'owner'}
          onChange={(e) => setData({ ...data, responsible_type: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="owner">Propriétaire</option>
          <option value="tenant">Locataire</option>
          <option value="syndic">Syndic</option>
        </select>
      </div>

      <div className="flex justify-end pt-2">
        <Button onClick={onNext}>
          Suivant <ChevronRight size={14} className="ml-1" />
        </Button>
      </div>
    </div>
  );
}

// ── Phase 2: Inventaire CVC ──

function StepInventaire({ systems, setSystems, putile, onNext, onPrev }) {
  const [editing, setEditing] = useState(null); // index or null

  const addSystem = () => {
    setSystems([...systems, { type: 'heating', architecture: 'cascade', units: [{ label: '', kw: 0 }] }]);
    setEditing(systems.length);
  };

  const removeSystem = (idx) => {
    setSystems(systems.filter((_, i) => i !== idx));
    if (editing === idx) setEditing(null);
  };

  const updateSystem = (idx, field, value) => {
    const updated = [...systems];
    updated[idx] = { ...updated[idx], [field]: value };
    setSystems(updated);
  };

  const addUnit = (sysIdx) => {
    const updated = [...systems];
    updated[sysIdx].units = [...updated[sysIdx].units, { label: '', kw: 0 }];
    setSystems(updated);
  };

  const updateUnit = (sysIdx, unitIdx, field, value) => {
    const updated = [...systems];
    updated[sysIdx].units = [...updated[sysIdx].units];
    updated[sysIdx].units[unitIdx] = { ...updated[sysIdx].units[unitIdx], [field]: value };
    setSystems(updated);
  };

  const removeUnit = (sysIdx, unitIdx) => {
    const updated = [...systems];
    updated[sysIdx].units = updated[sysIdx].units.filter((_, i) => i !== unitIdx);
    setSystems(updated);
  };

  // Compute local putile preview
  const totalKw = systems.reduce((sum, s) => {
    if (s.type === 'ventilation') return sum;
    const kws = s.units.map(u => parseFloat(u.kw) || 0).filter(k => k > 0);
    if (!kws.length) return sum;
    const sysKw = (s.architecture === 'independent') ? Math.max(...kws) : kws.reduce((a, b) => a + b, 0);
    return sum + sysKw;
  }, 0);

  const sysIcon = (type) => SYSTEM_TYPES.find(t => t.value === type);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-gray-800">Inventaire CVC</h3>
        <Button size="sm" variant="outline" onClick={addSystem}>
          <Plus size={14} className="mr-1" /> Ajouter un système
        </Button>
      </div>

      {/* Putile preview bar */}
      <div className="p-4 bg-gray-50 rounded-lg">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Puissance utile (Putile)</span>
          <span className="text-lg font-bold text-gray-900">{totalKw.toFixed(0)} kW</span>
        </div>
        <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              totalKw > 290 ? 'bg-red-500' : totalKw > 70 ? 'bg-amber-500' : 'bg-green-500'
            }`}
            style={{ width: `${Math.min(100, (totalKw / 400) * 100)}%` }}
          />
        </div>
        <div className="flex justify-between mt-1 text-xs text-gray-500">
          <span>0 kW</span>
          <span className={totalKw > 70 ? 'font-bold text-amber-600' : ''}>70 kW</span>
          <span className={totalKw > 290 ? 'font-bold text-red-600' : ''}>290 kW</span>
          <span>400+ kW</span>
        </div>
      </div>

      {/* Systems list */}
      {systems.length === 0 && (
        <div className="text-center py-8 text-gray-400 text-sm">
          Aucun système CVC. Cliquez "Ajouter" pour commencer l'inventaire.
        </div>
      )}

      {systems.map((sys, idx) => {
        const typeInfo = sysIcon(sys.type);
        const Icon = typeInfo?.icon || Thermometer;
        return (
          <Card key={idx} className="border-l-4 border-l-blue-400">
            <CardBody className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Icon size={16} className={typeInfo?.color || 'text-gray-500'} />
                  <span className="text-sm font-medium text-gray-800">
                    Système {idx + 1}: {typeInfo?.label || sys.type}
                  </span>
                </div>
                <button onClick={() => removeSystem(idx)} className="p-1 text-gray-400 hover:text-red-500">
                  <Trash2 size={14} />
                </button>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Type</label>
                  <select
                    value={sys.type}
                    onChange={(e) => updateSystem(idx, 'type', e.target.value)}
                    className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm"
                  >
                    {SYSTEM_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Architecture</label>
                  <select
                    value={sys.architecture}
                    onChange={(e) => updateSystem(idx, 'architecture', e.target.value)}
                    className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm"
                  >
                    {ARCHITECTURES.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
                  </select>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {ARCHITECTURES.find(a => a.value === sys.architecture)?.desc}
                  </p>
                </div>
              </div>

              {/* Units */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-600">Unités</span>
                  <button onClick={() => addUnit(idx)} className="text-xs text-blue-600 hover:underline flex items-center gap-0.5">
                    <Plus size={12} /> Ajouter
                  </button>
                </div>
                {sys.units.map((unit, ui) => (
                  <div key={ui} className="flex items-center gap-2">
                    <input
                      placeholder="Label"
                      value={unit.label}
                      onChange={(e) => updateUnit(idx, ui, 'label', e.target.value)}
                      className="flex-1 px-2 py-1.5 border border-gray-300 rounded text-sm"
                    />
                    <input
                      type="number"
                      placeholder="kW"
                      value={unit.kw || ''}
                      onChange={(e) => updateUnit(idx, ui, 'kw', parseFloat(e.target.value) || 0)}
                      className="w-24 px-2 py-1.5 border border-gray-300 rounded text-sm text-right"
                    />
                    <span className="text-xs text-gray-400">kW</span>
                    {sys.units.length > 1 && (
                      <button onClick={() => removeUnit(idx, ui)} className="p-1 text-gray-400 hover:text-red-500">
                        <Trash2 size={12} />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </CardBody>
          </Card>
        );
      })}

      <div className="flex justify-between pt-2">
        <Button variant="outline" onClick={onPrev}>
          <ChevronLeft size={14} className="mr-1" /> Précédent
        </Button>
        <Button onClick={onNext} disabled={systems.length === 0}>
          Évaluer <ChevronRight size={14} className="ml-1" />
        </Button>
      </div>
    </div>
  );
}

// ── Phase 3: Resultat ──

function StepResultat({ assessment, scoreExplain, loading, onNext, onPrev }) {
  if (loading) {
    return (
      <div className="text-center py-12">
        <Calculator size={32} className="text-blue-400 mx-auto mb-3 animate-pulse" />
        <p className="text-sm text-gray-500">Évaluation BACS en cours...</p>
      </div>
    );
  }

  if (!assessment) {
    return (
      <div className="text-center py-12 text-gray-400">
        <AlertTriangle size={28} className="mx-auto mb-2" />
        <p className="text-sm">Erreur: pas de résultat disponible.</p>
        <Button variant="outline" className="mt-4" onClick={onPrev}>Retour</Button>
      </div>
    );
  }

  const a = assessment;
  const deadline = a.deadline_date ? new Date(a.deadline_date) : null;
  const daysLeft = deadline ? Math.ceil((deadline - new Date()) / (1000 * 60 * 60 * 24)) : null;

  return (
    <div className="space-y-5">
      <h3 className="text-base font-semibold text-gray-800">Résultat de l'évaluation</h3>

      {/* Main verdict */}
      <Card className={`border-l-4 ${a.is_obligated ? 'border-l-red-500 bg-red-50' : 'border-l-green-500 bg-green-50'}`}>
        <CardBody className="flex items-center gap-4">
          <ShieldCheck size={28} className={a.is_obligated ? 'text-red-500' : 'text-green-500'} />
          <div>
            <h4 className="text-lg font-bold text-gray-900">
              {a.is_obligated ? 'Site assujetti au décret BACS' : 'Site non assujetti'}
            </h4>
            {a.is_obligated && (
              <p className="text-sm text-gray-600">
                Seuil: {a.threshold_applied} kW | Déclencheur: {a.trigger_reason || 'seuil'}
              </p>
            )}
          </div>
          <Badge status={a.is_obligated ? 'crit' : 'ok'} className="ml-auto">
            {a.is_obligated ? 'Assujetti' : 'Hors périmètre'}
          </Badge>
        </CardBody>
      </Card>

      {/* KPIs row */}
      {a.is_obligated && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-3 bg-gray-50 rounded-lg text-center">
            <p className="text-xs text-gray-500">Échéance</p>
            <p className="text-sm font-bold text-gray-800">{a.deadline_date || '—'}</p>
            {daysLeft !== null && (
              <p className={`text-xs ${daysLeft < 0 ? 'text-red-600 font-bold' : daysLeft < 180 ? 'text-amber-600' : 'text-green-600'}`}>
                {daysLeft < 0 ? `${Math.abs(daysLeft)}j en retard` : `${daysLeft}j restants`}
              </p>
            )}
          </div>
          <div className="p-3 bg-gray-50 rounded-lg text-center">
            <p className="text-xs text-gray-500">Seuil</p>
            <p className="text-sm font-bold text-gray-800">{a.threshold_applied} kW</p>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg text-center">
            <p className="text-xs text-gray-500">Score conformité</p>
            <p className={`text-sm font-bold ${(a.compliance_score || 0) >= 50 ? 'text-green-600' : 'text-red-600'}`}>
              {a.compliance_score?.toFixed(0) ?? '—'}%
            </p>
          </div>
          <div className="p-3 bg-gray-50 rounded-lg text-center">
            <p className="text-xs text-gray-500">Confiance</p>
            <p className="text-sm font-bold text-gray-800">{((a.confidence_score || 0) * 100).toFixed(0)}%</p>
          </div>
        </div>
      )}

      {/* TRI exemption */}
      {a.tri_exemption_possible !== null && (
        <Card className={`border-l-4 ${a.tri_exemption_possible ? 'border-l-amber-400' : 'border-l-gray-300'}`}>
          <CardBody>
            <div className="flex items-center gap-2">
              <Clock size={16} className="text-amber-500" />
              <h4 className="text-sm font-semibold text-gray-800">Exemption TRI</h4>
              <Badge status={a.tri_exemption_possible ? 'warn' : 'neutral'}>
                {a.tri_exemption_possible ? 'Exemption possible' : 'Pas d\'exemption'}
              </Badge>
            </div>
            {a.tri_years && (
              <p className="text-sm text-gray-600 mt-1">
                TRI = {a.tri_years} ans {a.tri_years > 10 ? '(> 10 ans: exemption art. R. 175-7)' : '(<= 10 ans)'}
              </p>
            )}
          </CardBody>
        </Card>
      )}

      {/* Findings list */}
      {a.findings && a.findings.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-semibold text-gray-700">Constats détaillés</h4>
          {a.findings.map((f, i) => (
            <Card key={i} className="border-l-2 border-l-gray-300">
              <CardBody className="py-2">
                <div className="flex items-center gap-2 mb-1">
                  <Badge status={f.status === 'NON_COMPLIANT' ? 'crit' : f.status === 'AT_RISK' ? 'warn' : 'ok'}>
                    {{ NON_COMPLIANT: 'Non conforme', AT_RISK: 'À risque', COMPLIANT: 'Conforme', UNKNOWN: 'À qualifier' }[f.status] || f.status}
                  </Badge>
                  <span className="text-xs text-gray-500">{f.regulation || f.rule_id}</span>
                </div>
                <p className="text-sm text-gray-700">{f.explanation}</p>
              </CardBody>
            </Card>
          ))}
        </div>
      )}

      {/* Putile trace */}
      {scoreExplain?.putile?.trace && (
        <details className="text-xs text-gray-500">
          <summary className="cursor-pointer text-blue-600 hover:underline">Trace Putile (audit)</summary>
          <pre className="mt-1 p-2 bg-gray-50 rounded text-xs whitespace-pre-wrap">
            {scoreExplain.putile.trace.join('\n')}
          </pre>
        </details>
      )}

      <div className="flex justify-between pt-2">
        <Button variant="outline" onClick={onPrev}>
          <ChevronLeft size={14} className="mr-1" /> Précédent
        </Button>
        <Button onClick={onNext}>
          Plan d'actions <ChevronRight size={14} className="ml-1" />
        </Button>
      </div>
    </div>
  );
}

// ── Phase 4: Plan d'actions ──

function StepActions({ assessment, onClose }) {
  if (!assessment?.is_obligated) {
    return (
      <div className="space-y-5">
        <h3 className="text-base font-semibold text-gray-800">Plan d'actions</h3>
        <div className="text-center py-8">
          <Check size={32} className="text-green-500 mx-auto mb-2" />
          <p className="text-sm text-gray-600">Ce site n'est pas assujetti au décret BACS.</p>
          <p className="text-xs text-gray-400 mt-1">Aucune action requise.</p>
        </div>
        <div className="flex justify-end">
          <Button onClick={onClose}>Fermer</Button>
        </div>
      </div>
    );
  }

  const actions = [
    { priority: 'CRITICAL', label: 'Installer un systeme GTB/GTC conforme', effort: 'Élevé', roi: 'Conformité réglementaire' },
    { priority: 'HIGH', label: 'Planifier l\'inspection quinquennale', effort: 'Moyen', roi: 'Éviter sanction' },
    { priority: 'MEDIUM', label: 'Évaluer le TRI pour exemption éventuelle', effort: 'Faible', roi: 'Potentielle exemption' },
    { priority: 'LOW', label: 'Documenter le responsable et les preuves', effort: 'Faible', roi: 'Auditabilité' },
  ];

  return (
    <div className="space-y-5">
      <h3 className="text-base font-semibold text-gray-800">Plan d'actions recommandé</h3>

      {actions.map((a, i) => (
        <Card key={i} className={`border-l-4 ${
          a.priority === 'CRITICAL' ? 'border-l-red-500' :
          a.priority === 'HIGH' ? 'border-l-orange-400' :
          a.priority === 'MEDIUM' ? 'border-l-amber-400' : 'border-l-gray-300'
        }`}>
          <CardBody className="flex items-center gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <Badge status={a.priority === 'CRITICAL' ? 'crit' : a.priority === 'HIGH' ? 'warn' : 'info'}>
                  {{ CRITICAL: 'Critique', HIGH: 'Élevée', MEDIUM: 'Moyenne', LOW: 'Faible' }[a.priority] || a.priority}
                </Badge>
                <span className="text-sm font-medium text-gray-800">{a.label}</span>
              </div>
              <div className="flex gap-4 text-xs text-gray-500">
                <span>Effort: {a.effort}</span>
                <span>ROI: {a.roi}</span>
              </div>
            </div>
          </CardBody>
        </Card>
      ))}

      <Card>
        <CardBody className="text-center py-4">
          <p className="text-sm text-gray-500">Export du rapport BACS</p>
          <Button variant="outline" size="sm" className="mt-2" onClick={() => {
            const blob = new Blob([JSON.stringify(assessment, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `bacs_assessment_${assessment.id || 'export'}.json`;
            a.click();
            URL.revokeObjectURL(url);
          }}>
            <FileText size={14} className="mr-1" /> Télécharger JSON
          </Button>
        </CardBody>
      </Card>

      <div className="flex justify-end pt-2">
        <Button onClick={onClose}>
          <Check size={14} className="mr-1" /> Terminer
        </Button>
      </div>
    </div>
  );
}

// ── Main Wizard ──

export default function BacsWizard({ siteId, onClose }) {
  const [phase, setPhase] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Phase 1 data
  const [eligData, setEligData] = useState({
    is_tertiary: true,
    pc_date: '',
    has_renewal: false,
    renewal_date: '',
    responsible_type: 'owner',
  });

  // Phase 2 data
  const [systems, setSystems] = useState([]);
  const [assetId, setAssetId] = useState(null);

  // Phase 3 data
  const [assessment, setAssessment] = useState(null);
  const [scoreExplain, setScoreExplain] = useState(null);

  // Phase 1 → 2: Create asset
  const handleEligNext = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await createBacsAsset(
        siteId,
        eligData.is_tertiary,
        eligData.pc_date || null,
      );
      setAssetId(result.id);
      setPhase(1);
    } catch (err) {
      if (err.response?.status === 409) {
        // Asset already exists — skip to phase 2
        setPhase(1);
      } else {
        setError(err.response?.data?.detail || 'Erreur création asset');
      }
    }
    setLoading(false);
  }, [siteId, eligData]);

  // Phase 2 → 3: Submit systems + recompute
  const handleInventaireNext = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Submit each system
      if (assetId) {
        for (const sys of systems) {
          await addCvcSystem(
            assetId,
            sys.type,
            sys.architecture,
            JSON.stringify(sys.units),
          );
        }
      }

      // Recompute
      const result = await recomputeBacs(siteId);
      setAssessment(result.assessment);

      // Get score explain
      try {
        const explain = await getBacsScoreExplain(siteId);
        setScoreExplain(explain);
      } catch { /* best-effort */ }

      setPhase(2);
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur évaluation');
    }
    setLoading(false);
  }, [siteId, assetId, systems]);

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-black/40 animate-[fadeIn_0.2s_ease-out]" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col animate-[slideInUp_0.25s_ease-out]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <h2 className="text-lg font-semibold text-gray-900">Évaluation BACS</h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            aria-label="Fermer"
          >
            <X size={18} />
          </button>
        </div>

        {/* Progress */}
        <ProgressBar phase={phase} />

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              <AlertTriangle size={14} className="inline mr-1" /> {error}
            </div>
          )}

          {phase === 0 && (
            <StepEligibilite data={eligData} setData={setEligData} onNext={handleEligNext} />
          )}
          {phase === 1 && (
            <StepInventaire
              systems={systems}
              setSystems={setSystems}
              onNext={handleInventaireNext}
              onPrev={() => setPhase(0)}
            />
          )}
          {phase === 2 && (
            <StepResultat
              assessment={assessment}
              scoreExplain={scoreExplain}
              loading={loading}
              onNext={() => setPhase(3)}
              onPrev={() => setPhase(1)}
            />
          )}
          {phase === 3 && (
            <StepActions assessment={assessment} onClose={onClose} />
          )}
        </div>
      </div>
    </div>
  );
}
