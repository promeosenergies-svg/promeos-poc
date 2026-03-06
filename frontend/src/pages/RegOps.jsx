/**
 * PROMEOS - RegOps Compliance Analysis Page
 * Dual panel: Audit (deterministic rules) vs IA (suggestions)
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  getRegOpsAssessment,
  getAiExplanation,
  getAiRecommendations,
  getAiDataQuality,
} from '../services/api';
import { useToast } from '../ui/ToastProvider';
import { fmtNum } from '../utils/format';
import {
  REGOPS_STATUS_LABELS,
  REGOPS_SEVERITY_LABELS,
  RULE_LABELS,
} from '../domain/compliance/complianceLabels.fr';
import { getComplianceScoreColor as _getComplianceScoreColor, COMPLIANCE_SCORE_THRESHOLDS } from '../lib/constants';
import { Coins } from 'lucide-react';

export default function RegOps() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [assessment, setAssessment] = useState(null);
  const [aiExplanation, setAiExplanation] = useState(null);
  const [aiRecommendations, setAiRecommendations] = useState(null);
  const [dataQuality, setDataQuality] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('audit'); // audit | ai

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [assessmentData, explanationData, recommendationsData, qualityData] = await Promise.all(
        [
          getRegOpsAssessment(id),
          getAiExplanation(id),
          getAiRecommendations(id),
          getAiDataQuality(id),
        ]
      );

      setAssessment(assessmentData);
      setAiExplanation(explanationData);
      setAiRecommendations(recommendationsData);
      setDataQuality(qualityData);
    } catch {
      toast('Erreur lors du chargement des données RegOps', 'error');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadgeColor = (status) => {
    const colors = {
      COMPLIANT: 'bg-green-100 text-green-800',
      AT_RISK: 'bg-yellow-100 text-yellow-800',
      NON_COMPLIANT: 'bg-red-100 text-red-800',
      UNKNOWN: 'bg-gray-100 text-gray-800',
      OUT_OF_SCOPE: 'bg-blue-100 text-blue-800',
      EXEMPTION_POSSIBLE: 'bg-purple-100 text-purple-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getSeverityBadgeColor = (severity) => {
    const colors = {
      CRITICAL: 'bg-red-600 text-white',
      HIGH: 'bg-orange-500 text-white',
      MEDIUM: 'bg-yellow-500 text-white',
      LOW: 'bg-blue-500 text-white',
    };
    return colors[severity] || 'bg-gray-500 text-white';
  };

  // A.2: use shared thresholds from constants
  const getComplianceScoreColor = _getComplianceScoreColor;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!assessment) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500 mb-4">Évaluation non disponible</p>
          <button
            onClick={() => navigate('/patrimoine')}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Retour au patrimoine
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate(`/sites/${id}`)}
          className="text-blue-500 hover:text-blue-700 mb-2 flex items-center"
        >
          ← Retour au site
        </button>
        <h1 className="text-3xl font-bold text-gray-800">Analyse RegOps - Site #{id}</h1>
      </div>

      {/* Compliance Score Card */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-700 mb-2">Score de Conformité</h2>
            <div className="flex items-baseline gap-2">
              <span
                className={`text-5xl font-bold ${getComplianceScoreColor(assessment.compliance_score)}`}
              >
                {fmtNum(assessment.compliance_score, 1)}
              </span>
              <span className="text-2xl text-gray-400">/100</span>
            </div>
          </div>
          <div className="text-right">
            <span
              className={`inline-block px-4 py-2 rounded-full text-sm font-semibold ${getStatusBadgeColor(assessment.global_status)}`}
            >
              {REGOPS_STATUS_LABELS[assessment.global_status] || assessment.global_status}
            </span>
            {assessment.next_deadline && (
              <p className="text-sm text-gray-600 mt-2">
                Prochaine échéance: {new Date(assessment.next_deadline).toLocaleDateString('fr-FR')}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-6">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('audit')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'audit'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              📋 Audit (Règles)
            </button>
            <button
              onClick={() => setActiveTab('ai')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'ai'
                  ? 'border-purple-500 text-purple-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              🤖 IA (Suggestions)
            </button>
          </nav>
        </div>
      </div>

      {/* Audit Panel (Deterministic) */}
      {activeTab === 'audit' && (
        <div className="space-y-6">
          {/* Obligations réglementaires */}
          <div className="bg-white rounded-lg shadow-md p-6" data-section="obligations">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">Obligations réglementaires</h2>
            {(() => {
              const obligationFindings = (assessment.findings || []).filter(f => f.category !== 'incentive');
              return obligationFindings.length > 0 ? (
                <div className="space-y-4">
                  {obligationFindings.map((finding, idx) => (
                    <div key={idx} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <h3 className="font-semibold text-gray-800">
                            {RULE_LABELS[finding.rule_id]?.title_fr || finding.regulation}
                          </h3>
                          <p className="text-sm text-gray-600">
                            {RULE_LABELS[finding.rule_id]?.why_fr || finding.rule_id}
                          </p>
                        </div>
                        <div className="flex gap-2">
                          <span
                            className={`px-3 py-1 rounded text-xs font-semibold ${getSeverityBadgeColor(finding.severity)}`}
                          >
                            {REGOPS_SEVERITY_LABELS[finding.severity] || finding.severity}
                          </span>
                          <span
                            className={`px-3 py-1 rounded text-xs font-semibold ${getStatusBadgeColor(finding.status)}`}
                          >
                            {REGOPS_STATUS_LABELS[finding.status] || finding.status}
                          </span>
                        </div>
                      </div>
                      <p className="text-gray-700 mb-2">{finding.explanation}</p>
                      {finding.legal_deadline && (
                        <p className="text-sm text-orange-600">
                          ⚠️ Échéance légale:{' '}
                          {new Date(finding.legal_deadline).toLocaleDateString('fr-FR')}
                        </p>
                      )}
                      {finding.inputs_used && finding.inputs_used.length > 0 && (
                        <details className="mt-2">
                          <summary className="text-sm text-gray-600 cursor-pointer">
                            Données utilisées
                          </summary>
                          <ul className="text-xs text-gray-500 mt-1 ml-4 list-disc">
                            {finding.inputs_used.map((input, i) => (
                              <li key={i}>{input}</li>
                            ))}
                          </ul>
                        </details>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500">Aucun constat réglementaire</p>
              );
            })()}
          </div>

          {/* Financements & opportunités (CEE) */}
          {(() => {
            const incentiveFindings = (assessment.findings || []).filter(f => f.category === 'incentive');
            if (incentiveFindings.length === 0) return null;
            return (
              <div className="bg-white rounded-lg shadow-md p-6" data-section="incentives">
                <h2 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
                  <Coins size={20} className="text-amber-500" />
                  Financements & opportunités
                </h2>
                <p className="text-sm text-gray-500 mb-4">
                  Certificats d'Économies d'Énergie (CEE) — mécanisme de financement, pas une obligation réglementaire.
                </p>
                <div className="space-y-4">
                  {incentiveFindings.map((finding, idx) => (
                    <div key={idx} className="border border-amber-200 bg-amber-50 rounded-lg p-4">
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <h3 className="font-semibold text-gray-800">
                            {RULE_LABELS[finding.rule_id]?.title_fr || finding.regulation}
                          </h3>
                          <p className="text-sm text-gray-600">
                            {RULE_LABELS[finding.rule_id]?.why_fr || finding.rule_id}
                          </p>
                        </div>
                        <div className="flex gap-2">
                          <span className="px-3 py-1 rounded text-xs font-semibold bg-green-100 text-green-700">
                            Éligible CEE
                          </span>
                        </div>
                      </div>
                      <p className="text-gray-700 mb-2">{finding.explanation}</p>
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}

          {/* Actions */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">Actions Recommandées</h2>
            {assessment.actions && assessment.actions.length > 0 ? (
              <div className="space-y-3">
                {assessment.actions
                  .filter((action) => !action.is_ai_suggestion)
                  .map((action, idx) => (
                    <div key={idx} className="flex items-start gap-3 p-3 bg-gray-50 rounded">
                      <span className="text-2xl">
                        {action.priority_score > 70
                          ? '🔴'
                          : action.priority_score > 50
                            ? '🟡'
                            : '🟢'}
                      </span>
                      <div className="flex-1">
                        <h4 className="font-semibold text-gray-800">{action.label}</h4>
                        {action.urgency_reason && (
                          <p className="text-sm text-gray-600">{action.urgency_reason}</p>
                        )}
                        <div className="flex gap-4 mt-1 text-xs text-gray-500">
                          <span>Priorité: {action.priority_score}/100</span>
                          {action.effort && <span>Effort: {action.effort}</span>}
                          {action.owner_role && <span>Responsable: {action.owner_role}</span>}
                        </div>
                      </div>
                    </div>
                  ))}
              </div>
            ) : (
              <p className="text-gray-500">Aucune action déterministe</p>
            )}
          </div>

          {/* Missing Data */}
          {assessment.missing_data && assessment.missing_data.length > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
              <h2 className="text-xl font-semibold text-yellow-800 mb-4">⚠️ Données Manquantes</h2>
              <ul className="list-disc list-inside space-y-1 text-gray-700">
                {assessment.missing_data.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* AI Panel (Suggestions) */}
      {activeTab === 'ai' && (
        <div className="space-y-6">
          {/* AI Brief */}
          {aiExplanation && (
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-6">
              <h2 className="text-xl font-semibold text-purple-800 mb-4">
                💡 Synthèse IA (2 minutes)
              </h2>
              <p className="text-gray-700 whitespace-pre-wrap">{aiExplanation.brief}</p>
              {aiExplanation.needs_human_review && (
                <div className="mt-4 text-sm text-purple-700">
                  ⚠️ Cette analyse nécessite une révision humaine
                </div>
              )}
            </div>
          )}

          {/* AI Recommendations */}
          {aiRecommendations &&
            aiRecommendations.suggestions &&
            aiRecommendations.suggestions.length > 0 && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <h2 className="text-xl font-semibold text-gray-800 mb-4">🤖 Suggestions IA</h2>
                <div className="space-y-3">
                  {aiRecommendations.suggestions.map((suggestion, idx) => (
                    <div key={idx} className="p-4 bg-purple-50 border border-purple-200 rounded-lg">
                      <div className="flex items-start gap-2">
                        <span className="text-purple-600 font-semibold">IA</span>
                        <div className="flex-1">
                          <p className="text-gray-800">{suggestion.label || suggestion}</p>
                          {typeof suggestion === 'object' && suggestion.reasoning && (
                            <p className="text-sm text-gray-600 mt-1">{suggestion.reasoning}</p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-gray-500 mt-4">
                  ℹ️ Les suggestions IA ne modifient jamais le statut de conformité déterministe
                </p>
              </div>
            )}

          {/* Data Quality */}
          {dataQuality && dataQuality.analysis && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold text-gray-800 mb-4">📊 Qualité des Données</h2>
              <pre className="text-sm text-gray-700 whitespace-pre-wrap bg-gray-50 p-4 rounded">
                {JSON.stringify(dataQuality.analysis, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
