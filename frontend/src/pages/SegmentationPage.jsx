import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { UserCheck, CheckCircle, ArrowLeft, Send } from 'lucide-react';
import {
  getSegmentationQuestions,
  getSegmentationProfile,
  submitSegmentationAnswers,
} from '../services/api';

const TYPO_LABELS = {
  tertiaire_prive: 'Tertiaire Prive',
  tertiaire_public: 'Tertiaire Public',
  industrie: 'Industrie',
  commerce_retail: 'Commerce / Retail',
  copropriete_syndic: 'Copropriete / Syndic',
  bailleur_social: 'Bailleur Social',
  collectivite: 'Collectivite',
  hotellerie_restauration: 'Hotellerie / Restauration',
  sante_medico_social: 'Sante / Medico-social',
  enseignement: 'Enseignement',
  mixte: 'Mixte (multi-activites)',
};

function ConfidenceBar({ score }) {
  const color = score >= 70 ? 'bg-green-500' : score >= 40 ? 'bg-amber-500' : 'bg-red-400';
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-3 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all duration-500`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-sm font-bold text-gray-700">{Math.round(score)}%</span>
    </div>
  );
}

export default function SegmentationPage() {
  const [questions, setQuestions] = useState([]);
  const [profile, setProfile] = useState(null);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    Promise.all([
      getSegmentationQuestions(),
      getSegmentationProfile(),
    ]).then(([qData, pData]) => {
      setQuestions(qData.questions || []);
      setProfile(pData);
      // Pre-fill existing answers
      if (pData.answers && Object.keys(pData.answers).length > 0) {
        setAnswers(pData.answers);
      }
    }).catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleAnswer = (questionId, value) => {
    setAnswers(prev => ({ ...prev, [questionId]: value }));
    setSubmitted(false);
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const result = await submitSegmentationAnswers(answers);
      setProfile(prev => ({
        ...prev,
        typologie: result.typologie,
        confidence_score: result.confidence_score,
        reasons: result.reasons,
      }));
      setSubmitted(true);
    } catch {
      // silent
    } finally {
      setSubmitting(false);
    }
  };

  const answeredCount = Object.values(answers).filter(v => v).length;

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/3" />
          <div className="h-4 bg-gray-200 rounded w-2/3" />
          {[1, 2, 3].map(i => (
            <div key={i} className="h-24 bg-gray-200 rounded" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="mb-6">
        <Link to="/" className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-3">
          <ArrowLeft size={14} /> Retour
        </Link>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <UserCheck size={24} className="text-blue-600" />
          Segmentation B2B
        </h1>
        <p className="text-gray-500 mt-1">
          Affinez votre profil pour des recommandations plus precises.
        </p>
      </div>

      {/* Current profile card */}
      {profile && profile.has_profile && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-5 mb-8 border border-blue-100">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-blue-700">Profil actuel</h2>
            {submitted && (
              <span className="flex items-center gap-1 text-xs text-green-600 font-medium">
                <CheckCircle size={14} /> Mis a jour
              </span>
            )}
          </div>
          <p className="text-xl font-bold text-gray-900 mb-3">
            {TYPO_LABELS[profile.typologie] || profile.typologie}
          </p>
          <ConfidenceBar score={profile.confidence_score} />
          {profile.reasons && profile.reasons.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {profile.reasons.map((r, i) => (
                <span key={i} className="text-xs bg-white/70 text-gray-600 px-2 py-1 rounded">
                  {r}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Questionnaire */}
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">
            Questionnaire ({answeredCount}/{questions.length})
          </h2>
        </div>

        {questions.map((q, idx) => (
          <div
            key={q.id}
            className={`bg-white rounded-lg shadow-sm p-5 border transition ${
              answers[q.id] ? 'border-blue-200 bg-blue-50/30' : 'border-gray-200'
            }`}
          >
            <p className="text-sm font-medium text-gray-800 mb-3">
              <span className="text-blue-600 font-bold mr-2">{idx + 1}.</span>
              {q.text}
            </p>
            <div className="flex flex-wrap gap-2">
              {q.options.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => handleAnswer(q.id, opt.value)}
                  className={`px-3 py-1.5 rounded-lg text-sm border transition ${
                    answers[q.id] === opt.value
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400 hover:text-blue-600'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Submit */}
      <div className="mt-8 flex items-center justify-between">
        <p className="text-sm text-gray-500">
          {answeredCount === 0
            ? 'Repondez aux questions pour affiner votre profil.'
            : `${answeredCount} reponse${answeredCount > 1 ? 's' : ''} sur ${questions.length}`}
        </p>
        <button
          onClick={handleSubmit}
          disabled={answeredCount === 0 || submitting}
          className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Send size={16} />
          {submitting ? 'Envoi...' : 'Mettre a jour le profil'}
        </button>
      </div>
    </div>
  );
}
