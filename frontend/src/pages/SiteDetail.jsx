import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Building2,
  MapPin,
  FolderOpen,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  ShieldOff,
  AlertTriangle,
  Euro,
  Zap,
  FileText,
  FileWarning,
  FileCheck,
  Clock,
  ChevronRight,
  ExternalLink,
  Rocket,
  ArrowRight,
} from 'lucide-react';
import { Badge as UIBadge } from '../ui';

const API = 'http://127.0.0.1:8000';

// Badge conformité (shared style)
const STATUT_CONFIG = {
  conforme: { label: 'Conforme', bg: 'bg-green-100', text: 'text-green-800', icon: ShieldCheck },
  derogation: { label: 'Derogation', bg: 'bg-blue-100', text: 'text-blue-800', icon: ShieldOff },
  a_risque: { label: 'A risque', bg: 'bg-orange-100', text: 'text-orange-800', icon: ShieldAlert },
  non_conforme: { label: 'Non conforme', bg: 'bg-red-100', text: 'text-red-800', icon: ShieldX },
};

const EVIDENCE_STATUS_CONFIG = {
  valide: { label: 'Valide', bg: 'bg-green-100', text: 'text-green-700', icon: FileCheck },
  en_attente: { label: 'En attente', bg: 'bg-yellow-100', text: 'text-yellow-700', icon: Clock },
  manquant: { label: 'Manquant', bg: 'bg-red-100', text: 'text-red-700', icon: FileWarning },
  expire: { label: 'Expire', bg: 'bg-gray-100', text: 'text-gray-700', icon: FileWarning },
};

const EVIDENCE_TYPE_LABELS = {
  audit: 'Audit',
  facture: 'Facture',
  certificat: 'Certificat',
  rapport: 'Rapport',
  photo: 'Photo',
  declaration: 'Declaration',
  attestation_bacs: 'Attestation BACS',
  derogation_bacs: 'Derogation BACS',
};

const Badge = ({ statut }) => {
  const cfg = STATUT_CONFIG[statut];
  if (!cfg) return <span className="px-2 py-1 text-xs rounded bg-gray-200 text-gray-700">Inconnu</span>;
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-full ${cfg.bg} ${cfg.text}`}>
      <Icon size={14} />
      {cfg.label}
    </span>
  );
};

const EvidenceBadge = ({ status }) => {
  const cfg = EVIDENCE_STATUS_CONFIG[status];
  if (!cfg) return <span className="px-2 py-1 text-xs rounded bg-gray-200 text-gray-700">{status}</span>;
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full ${cfg.bg} ${cfg.text}`}>
      <Icon size={12} />
      {cfg.label}
    </span>
  );
};

const SiteDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [guardrails, setGuardrails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('conformite');

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      fetch(`${API}/api/sites/${id}/compliance`).then(r => {
        if (!r.ok) throw new Error(`Site ${id} non trouvé`);
        return r.json();
      }),
      fetch(`${API}/api/sites/${id}/guardrails`).then(r => r.json()).catch(() => null),
    ])
      .then(([complianceData, guardrailsData]) => {
        setData(complianceData);
        setGuardrails(guardrailsData);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-xl text-gray-600">Chargement...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-screen gap-4">
        <div className="text-xl text-red-600">{error}</div>
        <Link to="/cockpit" className="text-blue-600 hover:underline flex items-center gap-1">
          <ArrowLeft size={16} /> Retour au cockpit
        </Link>
      </div>
    );
  }

  const { site, obligations, evidences, explanations, actions } = data;

  // Worst statut across both dimensions
  const worstStatut = [site.statut_decret_tertiaire, site.statut_bacs]
    .filter(Boolean)
    .sort((a, b) => {
      const order = { conforme: 0, derogation: 1, a_risque: 2, non_conforme: 3 };
      return (order[b] || 0) - (order[a] || 0);
    })[0] || 'a_risque';

  const tabs = [
    { key: 'conformite', label: 'Conformité', icon: ShieldCheck },
    { key: 'donnees', label: 'Données', icon: FileText },
    { key: 'alertes', label: 'Alertes', icon: AlertTriangle },
  ];

  const grErrors = guardrails?.errors || [];
  const grWarnings = guardrails?.warnings || [];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-blue-600 to-blue-800 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <Link to="/cockpit" className="inline-flex items-center gap-1 text-blue-200 hover:text-white text-sm mb-3 transition">
            <ArrowLeft size={16} /> Retour au cockpit
          </Link>
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-3">
                <Building2 size={28} />
                <h1 className="text-2xl font-bold">{site.nom}</h1>
              </div>
              <div className="flex items-center gap-4 mt-2 text-blue-100 text-sm">
                <span className="flex items-center gap-1"><MapPin size={14} /> {site.ville}</span>
                <span className="flex items-center gap-1"><FolderOpen size={14} /> Portefeuille #{site.portefeuille_id}</span>
                <span>{site.surface_m2} m2</span>
              </div>
            </div>
            <div>
              <Link
                to={`/regops/${id}`}
                className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm font-semibold transition shadow-md"
              >
                <ShieldCheck size={16} />
                Analyse RegOps
                <ArrowRight size={16} />
              </Link>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">

        {/* Guardrails violations */}
        {(grErrors.length > 0 || grWarnings.length > 0) && (
          <div className="mb-6 space-y-2">
            {grErrors.map((v, i) => (
              <div key={`err-${i}`} className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
                <ShieldX size={18} className="text-red-500 shrink-0" />
                <div>
                  <span className="text-sm font-medium text-red-800">{v.message}</span>
                  <UIBadge status="crit" className="ml-2">{v.code}</UIBadge>
                </div>
              </div>
            ))}
            {grWarnings.map((v, i) => (
              <div key={`warn-${i}`} className="flex items-center gap-3 bg-orange-50 border border-orange-200 rounded-lg px-4 py-3">
                <AlertTriangle size={18} className="text-orange-500 shrink-0" />
                <div>
                  <span className="text-sm font-medium text-orange-800">{v.message}</span>
                  <UIBadge status="warn" className="ml-2">{v.code}</UIBadge>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Quick Answer Block */}
        <div className="bg-white rounded-lg shadow mb-8 border-l-4 border-blue-500">
          <div className="px-6 py-4 border-b border-gray-100">
            <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
              <Zap size={20} className="text-blue-600" />
              Reponse en 2 minutes
            </h2>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Conformité globale */}
              <div className="flex flex-col">
                <span className="text-sm text-gray-500 mb-2">Conformité globale</span>
                <div className="flex items-center gap-3">
                  <Badge statut={worstStatut} />
                  <div className="flex gap-2">
                    <span className="text-xs text-gray-500">Décret:</span>
                    <Badge statut={site.statut_decret_tertiaire} />
                  </div>
                </div>
                <div className="flex gap-2 mt-2">
                  <span className="text-xs text-gray-500">BACS:</span>
                  <Badge statut={site.statut_bacs} />
                </div>
              </div>

              {/* Risque financier */}
              <div className="flex flex-col">
                <span className="text-sm text-gray-500 mb-2">Risque financier</span>
                <div className="flex items-center gap-2">
                  <Euro size={24} className={site.risque_financier_euro > 0 ? 'text-red-500' : 'text-green-500'} />
                  <span className={`text-2xl font-bold ${site.risque_financier_euro > 0 ? 'text-red-600' : 'text-green-600'}`}>
                    {site.risque_financier_euro.toLocaleString('fr-FR')} EUR
                  </span>
                </div>
                {site.risque_financier_euro > 0 && (
                  <span className="text-xs text-red-500 mt-1">Penalites estimees</span>
                )}
              </div>

              {/* Action prioritaire */}
              <div className="flex flex-col">
                <span className="text-sm text-gray-500 mb-2">Action prioritaire</span>
                {actions.length > 0 ? (
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-3 py-2">
                    <span className="text-sm text-yellow-800 font-medium flex items-center gap-1">
                      <ChevronRight size={14} />
                      {actions[0]}
                    </span>
                  </div>
                ) : (
                  <span className="text-sm text-green-600 font-medium">Aucune action requise</span>
                )}
                {actions.length > 1 && (
                  <span className="text-xs text-gray-500 mt-1">+{actions.length - 1} autre(s) action(s)</span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* CTA inline */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-700 rounded-xl p-5 text-white mb-8 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Rocket size={24} />
            <div>
              <span className="font-semibold">Voir le plan d'action global</span>
              <p className="text-blue-200 text-xs mt-0.5">Actions priorisees pour tout le patrimoine</p>
            </div>
          </div>
          <button
            onClick={() => navigate('/action-plan')}
            className="bg-white text-indigo-700 px-4 py-2 rounded-lg text-sm font-semibold hover:bg-indigo-50 transition flex items-center gap-1 shrink-0"
          >
            Plan d'action <ArrowRight size={14} />
          </button>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-lg shadow">
          <div className="border-b border-gray-200">
            <nav className="flex">
              {tabs.map(tab => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.key;
                return (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key)}
                    className={`flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition ${
                      isActive
                        ? 'border-blue-600 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    <Icon size={16} />
                    {tab.label}
                    {tab.key === 'alertes' && site.anomalie_facture && (
                      <span className="ml-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">!</span>
                    )}
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Tab: Conformité */}
          {activeTab === 'conformite' && (
            <div className="p-6">
              {/* Explanations */}
              <h3 className="text-base font-semibold text-gray-800 mb-4">Diagnostic conformité</h3>
              <div className="space-y-3 mb-8">
                {explanations.map((exp, i) => (
                  <div key={i} className="flex items-start gap-3 bg-gray-50 rounded-lg p-4">
                    <div className="mt-0.5">
                      <Badge statut={exp.statut} />
                    </div>
                    <div className="flex-1">
                      <div className="font-medium text-gray-900 text-sm">{exp.label}</div>
                      <div className="text-sm text-gray-600 mt-0.5">{exp.why}</div>
                    </div>
                  </div>
                ))}
                {explanations.length === 0 && (
                  <p className="text-sm text-gray-500">Aucune obligation trouvee pour ce site.</p>
                )}
              </div>

              {/* Obligations table */}
              <h3 className="text-base font-semibold text-gray-800 mb-4">Obligations réglementaires</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Statut</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Echeance</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Avancement</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {obligations.map(ob => (
                      <tr key={ob.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className="text-sm font-medium text-gray-900">
                            {ob.type === 'decret_tertiaire' ? 'Decret Tertiaire' :
                             ob.type === 'bacs' ? 'BACS' : ob.type.toUpperCase()}
                          </span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <Badge statut={ob.statut} />
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                          {ob.echeance || '-'}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <div className="w-20 bg-gray-200 rounded-full h-2">
                              <div
                                className={`h-2 rounded-full ${
                                  ob.avancement_pct >= 80 ? 'bg-green-500' :
                                  ob.avancement_pct >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                                }`}
                                style={{ width: `${Math.min(ob.avancement_pct, 100)}%` }}
                              />
                            </div>
                            <span className="text-xs text-gray-600">{Math.round(ob.avancement_pct)}%</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600 max-w-xs truncate">
                          {ob.description || '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {obligations.length === 0 && (
                  <p className="text-sm text-gray-500 p-4">Aucune obligation.</p>
                )}
              </div>

              {/* Actions */}
              {actions.length > 0 && (
                <div className="mt-8">
                  <h3 className="text-base font-semibold text-gray-800 mb-4">Actions recommandees</h3>
                  <div className="space-y-2">
                    {actions.map((action, i) => (
                      <div key={i} className="flex items-center gap-3 bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-3">
                        <span className="flex items-center justify-center w-6 h-6 rounded-full bg-yellow-200 text-yellow-800 text-xs font-bold">
                          {i + 1}
                        </span>
                        <span className="text-sm text-yellow-900">{action}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Tab: Données (Evidences) */}
          {activeTab === 'donnees' && (
            <div className="p-6">
              <h3 className="text-base font-semibold text-gray-800 mb-4">
                Preuves de conformité ({evidences.length})
              </h3>
              {evidences.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {evidences.map(ev => (
                    <div key={ev.id} className="border rounded-lg p-4 hover:shadow-md transition">
                      <div className="flex items-start justify-between mb-2">
                        <span className="text-sm font-medium text-gray-900">
                          {EVIDENCE_TYPE_LABELS[ev.type] || ev.type}
                        </span>
                        <EvidenceBadge status={ev.statut} />
                      </div>
                      {ev.note && (
                        <p className="text-sm text-gray-600 mb-2">{ev.note}</p>
                      )}
                      {ev.file_url ? (
                        <a
                          href={ev.file_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:underline flex items-center gap-1"
                        >
                          <ExternalLink size={12} /> Voir le document
                        </a>
                      ) : (
                        <span className="text-xs text-gray-400">Aucun fichier joint</span>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500">Aucune preuve enregistree pour ce site.</p>
              )}
            </div>
          )}

          {/* Tab: Alertes */}
          {activeTab === 'alertes' && (
            <div className="p-6">
              <h3 className="text-base font-semibold text-gray-800 mb-4">Alertes</h3>

              {site.anomalie_facture && (
                <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-lg px-4 py-3 mb-4">
                  <AlertTriangle size={18} className="text-red-500" />
                  <div>
                    <span className="text-sm font-medium text-red-800">Anomalie de facturation détectée</span>
                    <p className="text-xs text-red-600 mt-0.5">Une incohérence a été identifiée sur les factures de ce site.</p>
                  </div>
                </div>
              )}

              {actions.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Actions en attente</h4>
                  {actions.map((action, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm text-gray-700 py-1">
                      <AlertTriangle size={14} className="text-orange-500" />
                      {action}
                    </div>
                  ))}
                </div>
              )}

              {!site.anomalie_facture && actions.length === 0 && (
                <div className="flex items-center gap-3 bg-green-50 border border-green-200 rounded-lg px-4 py-3">
                  <ShieldCheck size={18} className="text-green-500" />
                  <span className="text-sm text-green-800">Aucune alerte active sur ce site.</span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SiteDetail;
