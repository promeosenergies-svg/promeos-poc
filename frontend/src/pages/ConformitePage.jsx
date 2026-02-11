/**
 * PROMEOS - Conformite (/conformite)
 * Score global + liste obligations + CTA creer action conformite
 */
import { useState } from 'react';
import { ShieldCheck, AlertTriangle, CheckCircle, Clock, FileText, ChevronDown, ChevronUp, Plus } from 'lucide-react';
import { Card, CardBody, Badge, Button, EmptyState } from '../ui';
import Modal from '../ui/Modal';
import CreateActionModal from '../components/CreateActionModal';
import { mockObligations, getObligationScore } from '../mocks/obligations';
import { useScope } from '../contexts/ScopeContext';
import { track } from '../services/tracker';

const SEVERITY_BADGE = {
  critical: 'crit',
  high: 'warn',
  medium: 'info',
  low: 'neutral',
};

const STATUT_CONFIG = {
  non_conforme: { label: 'Non conforme', color: 'text-red-700', bg: 'bg-red-50', border: 'border-red-200', icon: AlertTriangle },
  a_risque: { label: 'A risque', color: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-200', icon: Clock },
  conforme: { label: 'Conforme', color: 'text-green-700', bg: 'bg-green-50', border: 'border-green-200', icon: CheckCircle },
};

function ScoreGauge({ pct }) {
  const color = pct >= 80 ? 'text-green-600' : pct >= 50 ? 'text-amber-600' : 'text-red-600';
  const bg = pct >= 80 ? 'bg-green-100' : pct >= 50 ? 'bg-amber-100' : 'bg-red-100';
  const track_bg = 'bg-gray-200';
  const fill = pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500';

  return (
    <div className="flex items-center gap-4">
      <div className={`w-20 h-20 rounded-full ${bg} flex items-center justify-center`}>
        <span className={`text-2xl font-bold ${color}`}>{pct}%</span>
      </div>
      <div className="flex-1">
        <div className={`h-3 ${track_bg} rounded-full overflow-hidden`}>
          <div className={`h-full ${fill} rounded-full transition-all`} style={{ width: `${pct}%` }} />
        </div>
        <p className="text-xs text-gray-500 mt-1">Score de conformite global</p>
      </div>
    </div>
  );
}

function ObligationCard({ obligation, onCreateAction }) {
  const [expanded, setExpanded] = useState(false);
  const cfg = STATUT_CONFIG[obligation.statut] || STATUT_CONFIG.a_risque;
  const Icon = cfg.icon;
  const pctConforme = obligation.sites_concernes > 0
    ? Math.round(obligation.sites_conformes / obligation.sites_concernes * 100)
    : 100;

  return (
    <Card className={`border-l-4 ${cfg.border}`}>
      <CardBody>
        {/* Header row */}
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3 flex-1 min-w-0">
            <div className={`p-2 rounded-lg ${cfg.bg} mt-0.5`}>
              <Icon size={18} className={cfg.color} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-sm font-bold text-gray-900">{obligation.regulation}</h3>
                <Badge status={SEVERITY_BADGE[obligation.severity] || 'neutral'}>{obligation.severity}</Badge>
                <span className={`text-xs font-medium px-2 py-0.5 rounded ${cfg.bg} ${cfg.color}`}>{cfg.label}</span>
              </div>
              <p className="text-sm text-gray-600 mt-1">{obligation.description}</p>
            </div>
          </div>
          <button
            onClick={() => { setExpanded(!expanded); track('obligation_toggle', { code: obligation.code, expanded: !expanded }); }}
            className="p-1 hover:bg-gray-100 rounded transition ml-2"
          >
            {expanded ? <ChevronUp size={18} className="text-gray-400" /> : <ChevronDown size={18} className="text-gray-400" />}
          </button>
        </div>

        {/* Stats row */}
        <div className="flex items-center gap-6 mt-3 text-sm">
          <div>
            <span className="text-gray-500">Sites concernes: </span>
            <span className="font-medium text-gray-800">{obligation.sites_concernes}</span>
          </div>
          <div>
            <span className="text-gray-500">Conformes: </span>
            <span className="font-medium text-green-700">{obligation.sites_conformes}/{obligation.sites_concernes}</span>
            <span className="text-gray-400 ml-1">({pctConforme}%)</span>
          </div>
          <div className="flex items-center gap-1">
            <Clock size={14} className="text-gray-400" />
            <span className="text-gray-500">Echeance: </span>
            <span className="font-medium text-gray-800">{obligation.echeance}</span>
          </div>
          {obligation.impact_eur > 0 && (
            <div>
              <span className="text-gray-500">Risque: </span>
              <span className="font-bold text-red-600">{obligation.impact_eur.toLocaleString()} EUR</span>
            </div>
          )}
        </div>

        {/* Progress bar */}
        <div className="mt-3">
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <div className="h-full bg-green-500 rounded-full transition-all" style={{ width: `${pctConforme}%` }} />
          </div>
        </div>

        {/* Expanded detail */}
        {expanded && (
          <div className="mt-4 pt-4 border-t border-gray-100 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-blue-50 rounded-lg">
                <p className="text-xs font-semibold text-blue-600 uppercase mb-1">Pourquoi concerne</p>
                <p className="text-sm text-gray-700">{obligation.pourquoi}</p>
              </div>
              <div className="p-3 bg-amber-50 rounded-lg">
                <p className="text-xs font-semibold text-amber-600 uppercase mb-1">Ce qu'il faut faire</p>
                <p className="text-sm text-gray-700">{obligation.quoi_faire}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Echeance</p>
                <p className="text-sm text-gray-700 flex items-center gap-1"><Clock size={14} /> {obligation.echeance}</p>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Preuve attendue</p>
                <p className="text-sm text-gray-700 flex items-center gap-1"><FileText size={14} /> {obligation.preuve}</p>
              </div>
            </div>

            {obligation.statut !== 'conforme' && (
              <Button onClick={() => onCreateAction(obligation)} size="sm">
                <Plus size={14} /> Creer une action conformite
              </Button>
            )}
          </div>
        )}
      </CardBody>
    </Card>
  );
}

export default function ConformitePage() {
  const { org, scopedSites } = useScope();
  const [showCreate, setShowCreate] = useState(false);
  const [prefill, setPrefill] = useState(null);
  const score = getObligationScore();

  function handleCreateFromObligation(obligation) {
    setPrefill({
      titre: `Mise en conformite ${obligation.regulation}`,
      type: 'conformite',
      priorite: obligation.severity === 'critical' ? 'critical' : obligation.severity === 'high' ? 'high' : 'medium',
      description: obligation.quoi_faire,
    });
    setShowCreate(true);
    track('conformite_create_action', { regulation: obligation.code });
  }

  function handleSaveAction(action) {
    track('action_create_from_conformite', { titre: action.titre });
  }

  return (
    <div className="px-6 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Conformite Reglementaire</h2>
          <p className="text-sm text-gray-500 mt-0.5">{org.nom} &middot; {scopedSites.length} sites dans le perimetre</p>
        </div>
        <Button onClick={() => { setPrefill(null); setShowCreate(true); }}>
          <Plus size={16} /> Creer action conformite
        </Button>
      </div>

      {/* Score + summary */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="col-span-2">
          <CardBody>
            <ScoreGauge pct={score.pct} />
          </CardBody>
        </Card>
        <Card>
          <CardBody className="bg-red-50">
            <div className="flex items-center gap-2 mb-1">
              <AlertTriangle size={16} className="text-red-600" />
              <p className="text-xs text-gray-500 font-medium">Non conformes</p>
            </div>
            <p className="text-2xl font-bold text-red-700">{score.non_conformes}</p>
            <p className="text-xs text-gray-500 mt-1">obligations</p>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="bg-amber-50">
            <div className="flex items-center gap-2 mb-1">
              <Clock size={16} className="text-amber-600" />
              <p className="text-xs text-gray-500 font-medium">A risque</p>
            </div>
            <p className="text-2xl font-bold text-amber-700">{score.a_risque}</p>
            <p className="text-xs text-gray-500 mt-1">obligations</p>
          </CardBody>
        </Card>
      </div>

      {/* Impact financier */}
      {score.total_impact_eur > 0 && (
        <Card className="border-l-4 border-l-red-400">
          <CardBody className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Risque financier total lie a la non-conformite</p>
              <p className="text-2xl font-bold text-red-600 mt-1">{score.total_impact_eur.toLocaleString()} EUR</p>
            </div>
            <ShieldCheck size={32} className="text-red-200" />
          </CardBody>
        </Card>
      )}

      {/* Obligations list */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">{score.total} obligations reglementaires</h3>
        {mockObligations.length === 0 ? (
          <EmptyState
            icon={ShieldCheck}
            title="Aucune obligation detectee"
            text="Ajoutez des sites a votre patrimoine pour detecter les obligations reglementaires applicables."
            ctaLabel="Aller au patrimoine"
          />
        ) : (
          <div className="space-y-3">
            {mockObligations
              .sort((a, b) => {
                const order = { non_conforme: 0, a_risque: 1, conforme: 2 };
                return (order[a.statut] ?? 9) - (order[b.statut] ?? 9);
              })
              .map((o) => (
                <ObligationCard key={o.id} obligation={o} onCreateAction={handleCreateFromObligation} />
              ))}
          </div>
        )}
      </div>

      {/* Create Action Modal */}
      <CreateActionModal
        open={showCreate}
        onClose={() => { setShowCreate(false); setPrefill(null); }}
        onSave={handleSaveAction}
        prefill={prefill}
      />
    </div>
  );
}
